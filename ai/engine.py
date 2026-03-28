import json
import os
import anthropic

from storage.database import Database
from game import dice as dice_module
from game import game_time
from ai.prompts import (
    NARRATOR_SYSTEM_PROMPT,
    OPENING_SCENE_PROMPT,
    RECAP_SCENE_PROMPT,
    SUMMARY_PROMPT,
    WORLD_UPDATE_PROMPT,
    RESOURCE_UPDATE_PROMPT,
    ADVENTURE_STARTERS,
    CLASS_STARTING_GEAR,
    CLASS_STARTING_GOLD,
    CLASS_SPELL_SLOTS,
    CLASS_FOCUS_POINTS,
    CLASS_HP_PER_LEVEL,
    XP_PER_LEVEL,
    build_context,
)
from game.character import build_ability_scores

MODEL = "claude-sonnet-4-5"


def _copy_slots(slot_dict: dict) -> dict:
    """Deep-copy spell slot structure."""
    return {lvl: dict(data) for lvl, data in slot_dict.items()}


class Engine:
    def __init__(self, db: Database):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # ------------------------------------------------------------------
    # Opening scene
    # ------------------------------------------------------------------

    def generate_opening_scene(self, campaign_id: int, session_id: int, is_new: bool) -> str:
        campaign = self.db.get_campaign(campaign_id)
        summaries = self.db.get_recent_summaries(campaign_id, n=5)
        hero = campaign["hero_sheet"]
        world = campaign["world_state"]

        if is_new:
            system = OPENING_SCENE_PROMPT
            prompt = (
                f"Hero: {campaign['hero_name']}, a level {hero.get('level', 1)} "
                f"{hero.get('ancestry', '')} {hero.get('class', '')}\n"
                f"Personality: {', '.join(hero.get('traits', []))}\n\n"
                f"Adventure setting:\n{world.get('setting', '')}"
            )
        else:
            system = RECAP_SCENE_PROMPT
            recap_lines = [
                f"Hero: {campaign['hero_name']}, a level {hero.get('level', 1)} "
                f"{hero.get('ancestry', '')} {hero.get('class', '')}"
            ]
            if summaries:
                recap_lines.append("\nChapter summaries (oldest to most recent):")
                for i, s in enumerate(summaries, 1):
                    recap_lines.append(f"  Chapter {i}: {s}")
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

    # ------------------------------------------------------------------
    # DC assessment
    # ------------------------------------------------------------------

    def _get_action_dc(self, campaign: dict, messages: list, user_input: str) -> int:
        """Ask Claude to set the appropriate DC for this action given the current scene."""
        hero = campaign["hero_sheet"]

        recent = messages[-4:] if len(messages) >= 4 else messages
        scene_lines = [f"{m['role'].title()}: {m['content']}" for m in recent]
        scene_summary = "\n".join(scene_lines) if scene_lines else "Session just started."

        prompt = f"""You are a Pathfinder 2e Game Master setting a Difficulty Class (DC) for an action.

Hero: {campaign['hero_name']}, Level {hero.get('level', 1)} {hero.get('ancestry', '')} {hero.get('class', '')}
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

Consider the specific situation — a rusty lock is easier than a vault, a startled goblin is easier to intimidate than a veteran soldier.
If the action is purely descriptive and requires no roll (walking, talking casually, picking something up), reply with 0.

Reply with a single integer only."""

        try:
            response = self.client.messages.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            return int(response.content[0].text.strip())
        except Exception:
            return 15  # safe fallback

    # ------------------------------------------------------------------
    # Story beat
    # ------------------------------------------------------------------

    def generate_story_beat(self, campaign_id: int, session_id: int, user_input: str) -> tuple:
        campaign = self.db.get_campaign(campaign_id)
        summaries = self.db.get_recent_summaries(campaign_id, n=5)
        messages = self.db.get_session_messages(session_id)

        dc = self._get_action_dc(campaign, messages, user_input)
        roll_result = dice_module.roll_action(campaign["hero_sheet"], user_input, dc=dc)
        context = build_context(campaign, summaries, messages, roll_result=roll_result)
        full_prompt = f"{context}\n\nHero: {user_input}"

        response = self.client.messages.create(
            model=MODEL,
            system=NARRATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=500,
        )
        story_beat = response.content[0].text

        self.db.save_message(session_id, "user", user_input)
        assistant_msg_id = self.db.save_message(session_id, "assistant", story_beat)

        try:
            self._try_update_world_state(campaign_id, story_beat)
        except Exception:
            pass

        try:
            self._try_update_resources(campaign_id, user_input, story_beat)
        except Exception:
            pass

        return story_beat, roll_result, assistant_msg_id

    # ------------------------------------------------------------------
    # Resource tracking
    # ------------------------------------------------------------------

    def _try_update_resources(self, campaign_id: int, player_action: str, story_beat: str) -> None:
        campaign = self.db.get_campaign(campaign_id)
        hero = campaign["hero_sheet"]
        world = campaign["world_state"]

        inventory = hero.get("inventory", [])
        if inventory and isinstance(inventory[0], dict):
            inv_str = ", ".join(
                f"{i['name']} x{i['quantity']}" if i['quantity'] != 1 else i['name']
                for i in inventory
            )
        else:
            inv_str = ", ".join(inventory)

        spell_slots = hero.get("spell_slots", {})
        slots_str = ", ".join(
            f"Level {lvl}: {d['remaining']}/{d['max']}" for lvl, d in spell_slots.items()
        ) or "none"

        fp = hero.get("focus_points", {})
        fp_str = f"{fp.get('remaining', 0)}/{fp.get('max', 0)}" if fp.get("max", 0) > 0 else "none"

        prompt = RESOURCE_UPDATE_PROMPT.format(
            hero_name=campaign["hero_name"],
            hero_class=hero.get("class", ""),
            spell_slots=slots_str,
            focus_points=fp_str,
            inventory=inv_str,
            player_action=player_action,
            story_beat=story_beat,
        )

        response = self.client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        raw = response.content[0].text.strip()
        updates = json.loads(raw)

        if not updates:
            return

        for lvl_str, count in updates.get("spell_slots_used", {}).items():
            if lvl_str in hero.get("spell_slots", {}):
                slot = hero["spell_slots"][lvl_str]
                slot["remaining"] = max(0, slot["remaining"] - int(count))

        fp_used = updates.get("focus_points_used", 0)
        if fp_used and hero.get("focus_points"):
            hero["focus_points"]["remaining"] = max(
                0, hero["focus_points"]["remaining"] - int(fp_used)
            )

        items_consumed = updates.get("items_consumed", {})
        if items_consumed and inventory and isinstance(inventory[0], dict):
            for item_name, qty in items_consumed.items():
                for item in inventory:
                    if item["name"].lower() == item_name.lower():
                        item["quantity"] = max(0, item["quantity"] - int(qty))
            hero["inventory"] = [i for i in inventory if i["quantity"] > 0]

        if updates.get("rested"):
            for slot_data in hero.get("spell_slots", {}).values():
                slot_data["remaining"] = slot_data["max"]
            if hero.get("focus_points"):
                hero["focus_points"]["remaining"] = hero["focus_points"]["max"]
        elif updates.get("short_rested"):
            if hero.get("focus_points"):
                hero["focus_points"]["remaining"] = hero["focus_points"]["max"]

        xp_gained = int(updates.get("xp_gained", 0))
        if xp_gained > 0:
            hero["xp"] = hero.get("xp", 0) + xp_gained
            while hero["xp"] >= XP_PER_LEVEL:
                hero["xp"] -= XP_PER_LEVEL
                hero["level"] = hero.get("level", 1) + 1
                hp_gain = CLASS_HP_PER_LEVEL.get(hero.get("class", ""), 8)
                hero["max_hp"] = hero.get("max_hp", 20) + hp_gain
                hero["hp"] = hero["max_hp"]

        gold_changed = int(updates.get("gold_changed", 0))
        if gold_changed != 0:
            hero["gold"] = max(0, hero.get("gold", 0) + gold_changed)

        minutes = int(updates.get("minutes_elapsed", 5))
        time_state = world.get("time", game_time.initial_time())
        new_time, _ = game_time.advance_time(time_state, minutes)
        world["time"] = new_time

        self.db.update_hero_sheet(campaign_id, hero)
        self.db.update_world_state(campaign_id, world)

    # ------------------------------------------------------------------
    # World state
    # ------------------------------------------------------------------

    def _try_update_world_state(self, campaign_id: int, story_beat: str) -> None:
        prompt = WORLD_UPDATE_PROMPT.format(story_beat=story_beat)
        response = self.client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        raw = response.content[0].text.strip()
        updates = json.loads(raw)
        if updates:
            campaign = self.db.get_campaign(campaign_id)
            world = campaign["world_state"]
            for key, value in updates.items():
                if key == "time":
                    continue
                if isinstance(value, list) and isinstance(world.get(key), list):
                    for item in value:
                        if item not in world[key]:
                            world[key].append(item)
                else:
                    world[key] = value
            self.db.update_world_state(campaign_id, world)

    # ------------------------------------------------------------------
    # Session summary
    # ------------------------------------------------------------------

    def summarize_session(self, campaign_id: int, session_id: int) -> str:
        messages = self.db.get_session_messages(session_id)
        formatted = "\n".join(
            f"{'Hero' if m['role'] == 'user' else 'Narrator'}: {m['content']}"
            for m in messages
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

    # ------------------------------------------------------------------
    # Campaign creation
    # ------------------------------------------------------------------

    def start_campaign(
        self,
        title: str,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits: list,
    ) -> int:
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
        world_state = {
            "setting": ADVENTURE_STARTERS.get(adventure_setting, ""),
            "npcs": [],
            "locations": [],
            "quests": [],
            "lore": "",
            "time": game_time.initial_time(),
        }
        return self.db.create_campaign(title, adventure_setting, hero_name, hero_sheet, world_state)
