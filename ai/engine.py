import json
import os
import re
import uuid

import anthropic

from ai.prompts import (
    ADVENTURE_STARTERS,
    CLASS_FOCUS_POINTS,
    CLASS_HP_PER_LEVEL,
    CLASS_SPELL_SLOTS,
    CLASS_STARTING_GEAR,
    CLASS_STARTING_GOLD,
    OPENING_SCENE_PROMPT,
    RECAP_SCENE_PROMPT,
    STORY_ARC_PROMPT,
    SUMMARY_PROMPT,
    NARRATOR_SYSTEM_PROMPT,
    TURN_RESOLUTION_PROMPT,
    build_context,
)
from game import dice as dice_module
from game.character import build_ability_scores
from game.game_time import initial_time
from game.state_update import (
    apply_turn_resolution,
    build_fallback_story_state,
    get_current_beat,
    normalize_story_state,
    summarize_story_state,
)
from storage.database import Database

MODEL = "claude-sonnet-4-5"
CLASSIFIER_MODEL = "claude-3-5-haiku-latest"
MAX_SCENE_TITLE_WORDS = 6


def _copy_slots(slot_dict: dict) -> dict:
    return {lvl: dict(data) for lvl, data in slot_dict.items()}


def _safe_json_loads(raw_text: str) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found")
    return json.loads(raw_text[start : end + 1])


def _fallback_scene_title(text: str) -> str:
    cleaned = " ".join((text or "").replace("\n", " ").split())
    if not cleaned:
        return "A New Scene"
    first_clause = re.split(r"[.!?;:—-]", cleaned, maxsplit=1)[0].strip()
    words = first_clause.split()[:MAX_SCENE_TITLE_WORDS]
    return " ".join(words).strip(" ,") or "A New Scene"


def _scene_title_from_resolution(resolution_data: dict, fallback_text: str) -> str:
    title = str(resolution_data.get("scene_title") or "").strip()
    if title:
        words = title.split()[:MAX_SCENE_TITLE_WORDS]
        return " ".join(words).strip(" ,")
    return _fallback_scene_title(fallback_text)


class Engine:
    def __init__(self, db: Database):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def ensure_campaign_story_state(self, campaign_id: int) -> dict:
        campaign = self.db.get_campaign(campaign_id)
        if campaign is None:
            return None
        if campaign.get("story_state"):
            return campaign

        story_state = self._generate_story_arc(
            campaign["hero_name"],
            campaign["hero_sheet"],
            campaign["world_state"],
        )
        world_state = dict(campaign["world_state"])
        if story_state.get("hero_goal") and story_state["hero_goal"] not in world_state.get("quests", []):
            world_state.setdefault("quests", []).append(story_state["hero_goal"])
            self.db.update_world_state(campaign_id, world_state)
        self.db.update_story_state(campaign_id, story_state)
        campaign["world_state"] = world_state
        campaign["story_state"] = story_state
        return campaign

    def generate_opening_scene(self, campaign_id: int, session_id: int, is_new: bool) -> tuple[str, int]:
        campaign = self.ensure_campaign_story_state(campaign_id)
        summaries = self.db.get_recent_summaries(campaign_id, n=5)
        hero = campaign["hero_sheet"]
        world = campaign["world_state"]
        story = normalize_story_state(campaign.get("story_state"))
        current_beat = get_current_beat(story)

        if is_new:
            system = OPENING_SCENE_PROMPT
            prompt = (
                f"Hero: {campaign['hero_name']}, a level {hero.get('level', 1)} "
                f"{hero.get('ancestry', '')} {hero.get('class', '')}\n"
                f"Personality: {', '.join(hero.get('traits', []))}\n"
                f"Story arc: {story.get('title', '')}\n"
                f"Hero goal: {story.get('hero_goal', '')}\n"
                f"Current beat: {current_beat.get('goal', '') if current_beat else ''}\n\n"
                f"Adventure setting:\n{world.get('setting', '')}"
            )
        else:
            system = RECAP_SCENE_PROMPT
            recap_lines = [
                f"Hero: {campaign['hero_name']}, a level {hero.get('level', 1)} "
                f"{hero.get('ancestry', '')} {hero.get('class', '')}",
                f"Current story arc: {summarize_story_state(story)}",
            ]
            if summaries:
                recap_lines.append("\nChapter summaries (oldest to most recent):")
                for i, summary in enumerate(summaries, 1):
                    recap_lines.append(f"  Chapter {i}: {summary}")
            else:
                recap_lines.append("\nNo previous sessions recorded yet.")
            recap_lines.append(f"\nCurrent world state:\n{world.get('setting', '')}")
            if world.get("locations"):
                recap_lines.append(f"Locations visited: {', '.join(world['locations'])}")
            if world.get("npcs"):
                recap_lines.append(f"Characters met: {', '.join(world['npcs'])}")
            if world.get("quests"):
                recap_lines.append(f"Active quests: {', '.join(world['quests'])}")
            prompt = "\n".join(recap_lines)

        response = self.client.messages.create(
            model=MODEL,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        scene = response.content[0].text.strip()
        msg_id = self.db.save_message(session_id, "assistant", scene)
        return scene, msg_id

    def _get_action_dc(self, campaign: dict, messages: list, user_input: str) -> int:
        hero = campaign["hero_sheet"]
        story = normalize_story_state(campaign.get("story_state"))
        current_beat = get_current_beat(story)
        recent = messages[-4:] if len(messages) >= 4 else messages
        scene_lines = [f"{message['role'].title()}: {message['content']}" for message in recent]
        scene_summary = "\n".join(scene_lines) if scene_lines else "Session just started."

        prompt = f"""You are a Pathfinder 2e Game Master setting a Difficulty Class (DC) for an action.

Hero: {campaign['hero_name']}, Level {hero.get('level', 1)} {hero.get('ancestry', '')} {hero.get('class', '')}
Story arc: {story.get('title', '')}
Current beat goal: {current_beat.get('goal', '') if current_beat else ''}
Current scene:
{scene_summary}

Player action: {user_input}

What DC should this action require? Use Pathfinder 2e guidelines:
- Trivial / no real challenge: 5-8
- Easy: 10-12
- Moderate: 14-16
- Hard: 18-22
- Very Hard: 24-26
- Extreme: 28+

If the action is purely descriptive and requires no roll, reply with 0.
Reply with a single integer only."""

        try:
            response = self.client.messages.create(
                model=CLASSIFIER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            return int(response.content[0].text.strip())
        except Exception:
            return 15

    def _classify_action_skill(self, campaign: dict, messages: list, user_input: str) -> str | None:
        hero = campaign["hero_sheet"]
        recent = messages[-4:] if len(messages) >= 4 else messages
        scene_lines = [f"{message['role'].title()}: {message['content']}" for message in recent]
        scene_summary = "\n".join(scene_lines) if scene_lines else "Session just started."
        prompt = f"""Classify this Pathfinder 2e action into exactly one skill or combat action.

Return JSON only in this shape:
{{"skill": "Athletics"}}

Allowed skills:
Acrobatics, Arcana, Athletics, Crafting, Deception, Diplomacy, Intimidation, Medicine, Nature, Occultism, Performance, Perception, Religion, Society, Stealth, Survival, Thievery, Attack

Rules:
- Choose Attack for weapon strikes, unarmed strikes, spell attacks, or obvious offensive combat actions.
- Choose the single best matching skill for exploration, social, knowledge, stealth, or utility actions.
- If no listed skill fits clearly, return {{"skill": null}}.

Hero: {campaign['hero_name']} the level {hero.get('level', 1)} {hero.get('ancestry', '')} {hero.get('class', '')}
Current scene:
{scene_summary}

Player action:
{user_input}
"""

        try:
            response = self.client.messages.create(
                model=CLASSIFIER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
            )
            raw = _safe_json_loads(response.content[0].text.strip())
            skill = dice_module.normalize_skill(raw.get("skill"))
            return skill or dice_module.detect_skill(user_input)
        except Exception:
            return dice_module.detect_skill(user_input)

    def generate_story_beat(self, campaign_id: int, session_id: int, user_input: str) -> dict:
        campaign = self.ensure_campaign_story_state(campaign_id)
        summaries = self.db.get_recent_summaries(campaign_id, n=5)
        messages = self.db.get_session_messages(session_id)

        dc = self._get_action_dc(campaign, messages, user_input)
        classified_skill = self._classify_action_skill(campaign, messages, user_input)
        roll_result = self._roll_action(campaign["hero_sheet"], user_input, dc, classified_skill)
        base_context = build_context(campaign, summaries, messages, roll_result=roll_result)
        resolution_data = self._resolve_turn(base_context, user_input, roll_result)
        updated_campaign, applied_delta = apply_turn_resolution(campaign, resolution_data)

        if applied_delta.get("need_new_arc"):
            updated_campaign = self._refresh_story_arc(updated_campaign, applied_delta.get("replacement_reason", ""))
            applied_delta["arc_status"] = updated_campaign["story_state"]["status"]
            applied_delta["current_act_id"] = updated_campaign["story_state"]["current_act_id"]
            applied_delta["current_beat_id"] = updated_campaign["story_state"]["current_beat_id"]

        self.db.update_hero_sheet(campaign_id, updated_campaign["hero_sheet"])
        self.db.update_world_state(campaign_id, updated_campaign["world_state"])
        self.db.update_story_state(campaign_id, updated_campaign["story_state"])

        narration_context = build_context(updated_campaign, summaries, messages, roll_result=roll_result)
        story_beat = self._narrate_turn(narration_context, user_input, roll_result, resolution_data)
        scene_title = _scene_title_from_resolution(resolution_data, story_beat)

        self.db.save_message(session_id, "user", user_input)
        assistant_msg_id = self.db.save_message(
            session_id,
            "assistant",
            story_beat,
            roll_data=roll_result,
            resolution_data=resolution_data,
            applied_delta=applied_delta,
            scene_title=scene_title,
        )

        return {
            "story_beat": story_beat,
            "roll_result": roll_result,
            "message_id": assistant_msg_id,
            "resolution_data": resolution_data,
            "applied_delta": applied_delta,
            "scene_title": scene_title,
        }

    def summarize_session(self, campaign_id: int, session_id: int) -> str:
        messages = self.db.get_session_messages(session_id)
        formatted = "\n".join(
            f"{'Hero' if message['role'] == 'user' else 'Narrator'}: {message['content']}"
            for message in messages
        )
        prompt = SUMMARY_PROMPT.format(messages=formatted)
        response = self.client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        summary = response.content[0].text.strip()
        self.db.save_session_summary(session_id, summary)
        return summary

    def start_campaign(
        self,
        title: str,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits: list,
        story_state: dict | None = None,
    ) -> int:
        hero_sheet = self._build_initial_hero_sheet(ancestry, hero_class, level, traits)
        world_state = self._build_initial_world_state(adventure_setting)
        story_state = normalize_story_state(story_state) if story_state else self._generate_story_arc(hero_name, hero_sheet, world_state)
        if story_state.get("hero_goal"):
            world_state["quests"].append(story_state["hero_goal"])
        return self.db.create_campaign(title, adventure_setting, hero_name, hero_sheet, world_state, story_state=story_state)

    def generate_story_arc_draft(
        self,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits: list,
    ) -> dict:
        hero_sheet = self._build_initial_hero_sheet(ancestry, hero_class, level, traits)
        world_state = self._build_initial_world_state(adventure_setting)
        variation_hint = (
            "Create a fresh alternate story arc for this setting and hero. "
            "Avoid reusing the most obvious/default premise, inciting incident, clue chain, and final location. "
            f"Variation seed: {uuid.uuid4().hex[:10]}."
        )
        return self._generate_story_arc(hero_name or "The hero", hero_sheet, world_state, variation_hint=variation_hint)

    def _build_initial_hero_sheet(self, ancestry: str, hero_class: str, level: int, traits: list) -> dict:
        inventory = [
            {"name": name, "quantity": qty}
            for name, qty in CLASS_STARTING_GEAR.get(hero_class, [("adventurer's kit", 1)])
        ]
        starting_max_hp = CLASS_HP_PER_LEVEL.get(hero_class, 8) + 8
        ability_scores = build_ability_scores(ancestry, hero_class)
        hero_sheet = {
            "ancestry": ancestry,
            "class": hero_class,
            "level": level,
            "xp": 0,
            "gold": CLASS_STARTING_GOLD.get(hero_class, 10),
            "hp": starting_max_hp,
            "max_hp": starting_max_hp,
            "ac": 14,
            "ability_scores": ability_scores,
            "skills": [],
            "feats": [],
            "spells": [],
            "spell_slots": _copy_slots(CLASS_SPELL_SLOTS.get(hero_class, {})),
            "focus_points": dict(CLASS_FOCUS_POINTS.get(hero_class, {"max": 0, "remaining": 0})),
            "inventory": inventory,
            "traits": traits,
        }
        return hero_sheet

    def create_campaign_shell(
        self,
        title: str,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits: list,
        story_state: dict | None = None,
    ) -> int:
        hero_sheet = self._build_initial_hero_sheet(ancestry, hero_class, level, traits)
        world_state = self._build_initial_world_state(adventure_setting)
        normalized_story = normalize_story_state(story_state) if story_state else None
        if normalized_story and normalized_story.get("hero_goal"):
            world_state["quests"].append(normalized_story["hero_goal"])
        return self.db.create_campaign(
            title,
            adventure_setting,
            hero_name,
            hero_sheet,
            world_state,
            story_state=normalized_story,
        )

    def _build_initial_world_state(self, adventure_setting: str) -> dict:
        return {
            "setting": ADVENTURE_STARTERS.get(adventure_setting, ""),
            "npcs": [],
            "locations": [],
            "quests": [],
            "lore": "",
            "time": initial_time(),
        }

    def _generate_story_arc(
        self,
        hero_name: str,
        hero_sheet: dict,
        world_state: dict,
        previous_story_state: dict | None = None,
        replacement_reason: str = "",
        variation_hint: str = "",
    ) -> dict:
        hero_summary = (
            f"{hero_name}, level {hero_sheet.get('level', 1)} "
            f"{hero_sheet.get('ancestry', '')} {hero_sheet.get('class', '')}"
        )
        previous_arc = summarize_story_state(previous_story_state) if previous_story_state else "None"
        prompt = STORY_ARC_PROMPT.format(
            hero=hero_summary,
            setting=world_state.get("setting", ""),
            replacement_reason=replacement_reason or "None",
            previous_arc=previous_arc,
            variation_hint=variation_hint or "Use the campaign context naturally.",
        )
        try:
            response = self.client.messages.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
            )
            raw_story = _safe_json_loads(response.content[0].text.strip())
            raw_story["status"] = "active"
            raw_story["arc_history"] = list(previous_story_state.get("arc_history", [])) if previous_story_state else []
            if previous_story_state:
                raw_story["arc_history"].append(
                    {
                        "title": previous_story_state.get("title", "Unknown Arc"),
                        "reason": replacement_reason or "The previous arc ended.",
                    }
                )
                previous_id = previous_story_state.get("arc_id", "arc-0").replace("arc-", "")
                raw_story["arc_id"] = f"arc-{int(previous_id) + 1}"
            else:
                raw_story["arc_id"] = "arc-1"
            raw_story["last_turn_summary"] = replacement_reason or raw_story.get("premise", "")
            return normalize_story_state(raw_story)
        except Exception:
            return build_fallback_story_state(hero_name, world_state, previous_story_state, replacement_reason)

    def _refresh_story_arc(self, campaign: dict, replacement_reason: str) -> dict:
        hero = campaign["hero_sheet"]
        if hero.get("hp", 0) <= 0:
            hero["hp"] = hero.get("max_hp", 1)
        story_state = self._generate_story_arc(
            campaign["hero_name"],
            hero,
            campaign["world_state"],
            previous_story_state=campaign.get("story_state"),
            replacement_reason=replacement_reason or "The story needed a new direction.",
        )
        world = campaign["world_state"]
        if story_state.get("hero_goal") and story_state["hero_goal"] not in world.get("quests", []):
            world.setdefault("quests", []).append(story_state["hero_goal"])
        return {
            **campaign,
            "hero_sheet": hero,
            "world_state": world,
            "story_state": story_state,
        }

    def _resolve_turn(self, context: str, user_input: str, roll_result: dict) -> dict:
        prompt = TURN_RESOLUTION_PROMPT.format(
            context=context,
            player_action=user_input,
            roll_result=json.dumps(roll_result),
        )
        try:
            response = self.client.messages.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=900,
            )
            resolution_data = _safe_json_loads(response.content[0].text.strip())
            resolution_data.setdefault("scene_title", "")
            resolution_data.setdefault("narration_cue", "")
            resolution_data.setdefault("advancement_type", "none")
            resolution_data.setdefault("state_delta", {})
            resolution_data.setdefault("world_updates", {})
            resolution_data.setdefault("arc_progress", {})
            resolution_data.setdefault("continuity_update", {})
            return resolution_data
        except Exception:
            return {
                "scene_title": "A Small Change",
                "narration_cue": "The hero changes the scene, but only in a small and uncertain way.",
                "advancement_type": "none",
                "state_delta": {
                    "hp_change": 0,
                    "xp_change": 10 if roll_result.get("degree") in {"success", "critical success"} else 0,
                    "gold_change": 0,
                    "inventory_add": [],
                    "inventory_remove": [],
                    "spell_slots_used": {},
                    "focus_points_used": 0,
                    "minutes_elapsed": 10 if roll_result.get("dc", 0) else 5,
                    "full_rest": False,
                    "short_rest": False,
                },
                "world_updates": {},
                "arc_progress": {
                    "beat_status": "progress" if roll_result.get("degree") in {"success", "critical success"} else "stalled",
                    "arc_status": "active",
                    "next_story_focus": "Keep pushing toward the current story objective.",
                    "replacement_reason": "",
                },
                "continuity_update": {
                    "last_meaningful_change": "The situation changes only slightly.",
                },
            }

    def _narrate_turn(self, context: str, user_input: str, roll_result: dict, resolution_data: dict) -> str:
        prompt = (
            f"{context}\n\n"
            f"Player action:\n{user_input}\n\n"
            f"Dice result:\n{json.dumps(roll_result)}\n\n"
            f"Resolved state changes:\n{json.dumps(resolution_data)}\n\n"
            "Narrate this one turn for the player. Follow the dice result exactly. "
            "Use the resolved state changes and hidden continuity guardrails only as GM guidance. "
            "Do not expose JSON, state keys, cooldowns, continuity rules, or story-arc planning."
        )
        try:
            response = self.client.messages.create(
                model=MODEL,
                system=NARRATOR_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=650,
            )
            story_beat = response.content[0].text.strip()
            return story_beat or resolution_data.get("narration_cue") or "The scene changes, but only a little."
        except Exception:
            resolution_data = self._fallback_resolution(roll_result)
            return resolution_data["narration_cue"]

    def _fallback_resolution(self, roll_result: dict) -> dict:
        return {
            "scene_title": "A Small Change",
            "narration_cue": "The hero changes the scene, but only in a small and uncertain way.",
            "advancement_type": "none",
            "state_delta": {
                "hp_change": 0,
                "xp_change": 10 if roll_result.get("degree") in {"success", "critical success"} else 0,
                "gold_change": 0,
                "inventory_add": [],
                "inventory_remove": [],
                "spell_slots_used": {},
                "focus_points_used": 0,
                "minutes_elapsed": 10 if roll_result.get("dc", 0) else 5,
                "full_rest": False,
                "short_rest": False,
            },
            "world_updates": {},
            "arc_progress": {
                "beat_status": "progress" if roll_result.get("degree") in {"success", "critical success"} else "stalled",
                "arc_status": "active",
                "next_story_focus": "Keep pushing toward the current story objective.",
                "replacement_reason": "",
            },
            "continuity_update": {
                "last_meaningful_change": "The situation changes only slightly.",
            },
        }

    def _roll_action(self, hero_sheet: dict, user_input: str, dc: int, skill_override: str | None = None) -> dict:
        if dc == 0:
            skill = dice_module.normalize_skill(skill_override) or dice_module.detect_skill(user_input)
            modifier = dice_module.get_modifier(hero_sheet, skill)
            return {
                "skill": skill,
                "roll": 0,
                "modifier": modifier,
                "total": modifier,
                "dc": 0,
                "degree": "success",
            }
        return dice_module.roll_action(hero_sheet, user_input, dc=dc, skill_override=skill_override)
