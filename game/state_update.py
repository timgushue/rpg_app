import copy
from typing import Optional

from .game_data import CLASS_HP_PER_LEVEL, XP_PER_LEVEL
from .game_time import advance_time, initial_time

MAX_XP_PER_TURN = 100
MAX_RECENT_COMPLICATIONS = 5
DEFAULT_COMPLICATION_COOLDOWN = 3
VALID_ADVANCEMENT_TYPES = {
    "location",
    "information",
    "resource",
    "relationship",
    "danger",
    "objective",
    "none",
}


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _as_int(value: object, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _unique_text_list(values: object) -> list[str]:
    result = []
    seen = set()
    source = [values] if isinstance(values, str) else _as_list(values)
    for value in source:
        text = _as_text(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _empty_continuity_state() -> dict:
    return {
        "current_situation": "",
        "current_location": "",
        "resolved_threads": [],
        "active_constraints": [],
        "recent_complications": [],
        "last_meaningful_change": "",
    }


def normalize_continuity_state(value: object) -> dict:
    continuity = _empty_continuity_state()
    raw = _as_dict(value)
    continuity["current_situation"] = _as_text(raw.get("current_situation"))
    continuity["current_location"] = _as_text(raw.get("current_location"))
    continuity["resolved_threads"] = _unique_text_list(raw.get("resolved_threads"))
    continuity["active_constraints"] = _unique_text_list(raw.get("active_constraints"))
    continuity["last_meaningful_change"] = _as_text(raw.get("last_meaningful_change"))

    recent = []
    seen = set()
    for entry in _as_list(raw.get("recent_complications")):
        if isinstance(entry, dict):
            label = _as_text(entry.get("label") or entry.get("name") or entry.get("complication"))
            cooldown = _as_int(entry.get("cooldown"), DEFAULT_COMPLICATION_COOLDOWN)
        else:
            label = _as_text(entry)
            cooldown = DEFAULT_COMPLICATION_COOLDOWN
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        recent.append({"label": label, "cooldown": max(1, min(cooldown, 10))})
    continuity["recent_complications"] = recent[-MAX_RECENT_COMPLICATIONS:]
    return continuity


def _normalize_advancement_type(value: object) -> str:
    text = _as_text(value).lower()
    return text if text in VALID_ADVANCEMENT_TYPES else "none"


def build_fallback_story_state(
    hero_name: str,
    world_state: dict,
    previous_story_state: Optional[dict] = None,
    reason: Optional[str] = None,
) -> dict:
    setting = world_state.get("setting", "A new danger is stirring in Golarion.")
    base_title = "The Ember Crown"
    if previous_story_state and previous_story_state.get("title"):
        base_title = f"After {previous_story_state['title']}"

    story_state = {
        "status": "active",
        "arc_id": f"arc-{len(previous_story_state.get('arc_history', [])) + 2}" if previous_story_state else "arc-1",
        "title": base_title,
        "premise": f"{hero_name} is drawn into a focused Pathfinder adventure rooted in the current setting.",
        "theme": "Courage and cleverness overcome danger.",
        "hero_goal": "Uncover the threat and stop it before it harms the people nearby.",
        "main_threat": "A hidden enemy is escalating the danger behind the scenes.",
        "stakes": "If the hero fails, innocent people will suffer and the region will fall deeper into peril.",
        "acts": [
            {
                "id": "act-1",
                "title": "The First Clue",
                "summary": "The hero is pulled into the central mystery and must understand what is truly wrong.",
                "status": "active",
                "beats": [
                    {
                        "id": "beat-1",
                        "title": "The Hook",
                        "goal": "Investigate the immediate disturbance and identify the first real lead.",
                        "required_progress": "The hero finds a concrete clue, witness, or trail worth following.",
                        "failure_risk": "If ignored, the threat grows bolder.",
                        "completion_signal": "The hero has a named clue, suspect, or destination.",
                        "status": "active",
                    },
                    {
                        "id": "beat-2",
                        "title": "Follow the Trail",
                        "goal": "Chase the clue into a new location or confrontation.",
                        "required_progress": "The hero reaches the next meaningful story location.",
                        "failure_risk": "The enemy gains time to prepare.",
                        "completion_signal": "The hero uncovers who or what is driving the danger.",
                        "status": "pending",
                    },
                ],
            },
            {
                "id": "act-2",
                "title": "The Threat Revealed",
                "summary": "The villain's plan becomes clearer and the hero must disrupt it.",
                "status": "pending",
                "beats": [
                    {
                        "id": "beat-3",
                        "title": "Disrupt the Scheme",
                        "goal": "Block a major part of the enemy plan.",
                        "required_progress": "The hero interferes with the threat in a visible way.",
                        "failure_risk": "The villain presses the advantage.",
                        "completion_signal": "The enemy is forced to react to the hero.",
                        "status": "pending",
                    },
                    {
                        "id": "beat-4",
                        "title": "Race to the Finale",
                        "goal": "Reach the place or moment where the final confrontation will happen.",
                        "required_progress": "The hero secures the final lead or route to the climax.",
                        "failure_risk": "The final challenge becomes harder.",
                        "completion_signal": "The hero stands on the edge of the final showdown.",
                        "status": "pending",
                    },
                ],
            },
            {
                "id": "act-3",
                "title": "The Final Showdown",
                "summary": "The hero confronts the main threat and resolves the adventure.",
                "status": "pending",
                "beats": [
                    {
                        "id": "beat-5",
                        "title": "Confront the Threat",
                        "goal": "Face the main enemy or obstacle directly.",
                        "required_progress": "The hero commits to the climax.",
                        "failure_risk": "The threat may escape or strike first.",
                        "completion_signal": "The conflict reaches its turning point.",
                        "status": "pending",
                    },
                    {
                        "id": "beat-6",
                        "title": "Secure the Victory",
                        "goal": "Resolve the danger and protect the setting.",
                        "required_progress": "The villain is stopped or the central danger is neutralized.",
                        "failure_risk": "The region remains unstable.",
                        "completion_signal": "The setting is safe enough for a new chapter to begin.",
                        "status": "pending",
                    },
                ],
            },
        ],
        "current_act_id": "act-1",
        "current_beat_id": "beat-1",
        "arc_history": [],
        "last_turn_summary": reason or f"The adventure begins in this setting: {setting}",
        "continuity": {
            **_empty_continuity_state(),
            "current_situation": reason or f"The adventure begins in this setting: {setting}",
        },
    }
    if previous_story_state:
        history = list(previous_story_state.get("arc_history", []))
        history.append(
            {
                "title": previous_story_state.get("title", "Unknown Arc"),
                "reason": reason or "The previous arc could no longer continue.",
            }
        )
        story_state["arc_history"] = history
    return normalize_story_state(story_state)


def normalize_story_state(story_state: Optional[dict]) -> dict:
    if not story_state:
        return build_fallback_story_state("Hero", {"setting": ""})

    normalized = copy.deepcopy(story_state)
    normalized.setdefault("status", "active")
    normalized.setdefault("arc_id", "arc-1")
    normalized.setdefault("title", "Unknown Arc")
    normalized.setdefault("premise", "")
    normalized.setdefault("theme", "")
    normalized.setdefault("hero_goal", "")
    normalized.setdefault("main_threat", "")
    normalized.setdefault("stakes", "")
    normalized.setdefault("acts", [])
    normalized.setdefault("current_act_id", "")
    normalized.setdefault("current_beat_id", "")
    normalized.setdefault("arc_history", [])
    normalized.setdefault("last_turn_summary", "")
    normalized["continuity"] = normalize_continuity_state(normalized.get("continuity"))

    first_act_id = None
    first_beat_id = None
    for act_index, act in enumerate(normalized["acts"], 1):
        act.setdefault("id", f"act-{act_index}")
        act.setdefault("title", f"Act {act_index}")
        act.setdefault("summary", "")
        act.setdefault("status", "pending")
        act.setdefault("beats", [])
        if first_act_id is None:
            first_act_id = act["id"]
        for beat_index, beat in enumerate(act["beats"], 1):
            beat.setdefault("id", f"{act['id']}-beat-{beat_index}")
            beat.setdefault("title", f"Beat {beat_index}")
            beat.setdefault("goal", "")
            beat.setdefault("required_progress", "")
            beat.setdefault("failure_risk", "")
            beat.setdefault("completion_signal", "")
            beat.setdefault("status", "pending")
            if first_beat_id is None:
                first_beat_id = beat["id"]

    normalized["current_act_id"] = normalized["current_act_id"] or first_act_id or "act-1"
    normalized["current_beat_id"] = normalized["current_beat_id"] or first_beat_id or "beat-1"

    if normalized["acts"] and not get_current_beat(normalized):
        first_act = normalized["acts"][0]
        first_beat = first_act["beats"][0] if first_act.get("beats") else {"id": "beat-1"}
        normalized["current_act_id"] = first_act["id"]
        normalized["current_beat_id"] = first_beat["id"]
        first_act["status"] = "active"
        if first_act.get("beats"):
            first_act["beats"][0]["status"] = "active"

    return normalized


def get_current_beat(story_state: Optional[dict]) -> Optional[dict]:
    if not story_state:
        return None
    for act in story_state.get("acts", []):
        if act.get("id") != story_state.get("current_act_id"):
            continue
        for beat in act.get("beats", []):
            if beat.get("id") == story_state.get("current_beat_id"):
                return beat
    return None


def get_current_act(story_state: Optional[dict]) -> Optional[dict]:
    if not story_state:
        return None
    for act in story_state.get("acts", []):
        if act.get("id") == story_state.get("current_act_id"):
            return act
    return None


def summarize_story_state(story_state: Optional[dict]) -> str:
    story_state = normalize_story_state(story_state)
    current_act = get_current_act(story_state)
    current_beat = get_current_beat(story_state)
    parts = [f"Arc: {story_state.get('title', 'Unknown Arc')}"]
    if story_state.get("hero_goal"):
        parts.append(f"Goal: {story_state['hero_goal']}")
    if current_act:
        parts.append(f"Act: {current_act.get('title', '')}")
    if current_beat:
        parts.append(f"Beat: {current_beat.get('title', '')} - {current_beat.get('goal', '')}")
    return " | ".join(parts)


def apply_turn_resolution(campaign: dict, resolution_data: dict) -> tuple[dict, dict]:
    hero = copy.deepcopy(campaign["hero_sheet"])
    world = copy.deepcopy(campaign["world_state"])
    story_state = normalize_story_state(campaign.get("story_state"))
    resolution_data = _as_dict(resolution_data)
    state_delta = copy.deepcopy(_as_dict(resolution_data.get("state_delta")))
    world_updates = copy.deepcopy(_as_dict(resolution_data.get("world_updates")))
    arc_progress = copy.deepcopy(_as_dict(resolution_data.get("arc_progress")))
    advancement_type = _normalize_advancement_type(resolution_data.get("advancement_type"))
    continuity_update = copy.deepcopy(_as_dict(resolution_data.get("continuity_update")))

    applied = {
        "hp_change": 0,
        "xp_change": 0,
        "gold_change": 0,
        "inventory_add": [],
        "inventory_remove": [],
        "spell_slots_used": {},
        "focus_points_used": 0,
        "minutes_elapsed": 0,
        "full_rest": False,
        "short_rest": False,
        "world_updates": {},
        "arc_status": story_state.get("status", "active"),
        "current_act_id": story_state.get("current_act_id"),
        "current_beat_id": story_state.get("current_beat_id"),
        "need_new_arc": False,
        "replacement_reason": "",
        "hero_defeated": False,
        "level_up": False,
        "old_level": hero.get("level", 1),
        "new_level": hero.get("level", 1),
        "hp_gain": 0,
        "advancement_type": advancement_type,
        "continuity_update": {},
    }

    hp_change = _as_int(state_delta.get("hp_change"))
    max_hp = max(hero.get("max_hp", 1), 1)
    old_hp = hero.get("hp", max_hp)
    hero["hp"] = max(0, min(max_hp, old_hp + hp_change))
    applied["hp_change"] = hero["hp"] - old_hp
    applied["hero_defeated"] = hero["hp"] <= 0

    for level_str, used in _as_dict(state_delta.get("spell_slots_used")).items():
        if level_str in hero.get("spell_slots", {}):
            slot = hero["spell_slots"][level_str]
            old_remaining = slot["remaining"]
            slot["remaining"] = max(0, old_remaining - _as_int(used))
            spent = old_remaining - slot["remaining"]
            if spent:
                applied["spell_slots_used"][level_str] = spent

    if hero.get("focus_points"):
        old_focus = hero["focus_points"].get("remaining", 0)
        focus_used = max(0, _as_int(state_delta.get("focus_points_used")))
        hero["focus_points"]["remaining"] = max(0, old_focus - focus_used)
        applied["focus_points_used"] = old_focus - hero["focus_points"]["remaining"]

    full_rest = bool(state_delta.get("full_rest"))
    short_rest = bool(state_delta.get("short_rest"))
    if full_rest:
        for slot in hero.get("spell_slots", {}).values():
            slot["remaining"] = slot["max"]
        if hero.get("focus_points"):
            hero["focus_points"]["remaining"] = hero["focus_points"]["max"]
    elif short_rest and hero.get("focus_points"):
        hero["focus_points"]["remaining"] = hero["focus_points"]["max"]
    applied["full_rest"] = full_rest
    applied["short_rest"] = short_rest

    inventory = hero.get("inventory", [])
    inventory_map = {}
    for item in inventory:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            inventory_map[item["name"].lower()] = item

    for entry in _as_list(state_delta.get("inventory_remove")):
        entry = _as_dict(entry)
        name = _as_text(entry.get("name"))
        if not name:
            continue
        item = inventory_map.get(name.lower())
        if not item:
            continue
        old_quantity = _as_int(item.get("quantity"))
        item["quantity"] = max(0, old_quantity - _as_int(entry.get("quantity")))
        removed = old_quantity - item["quantity"]
        if removed:
            applied["inventory_remove"].append({"name": item["name"], "quantity": removed})

    for entry in _as_list(state_delta.get("inventory_add")):
        entry = _as_dict(entry)
        name = _as_text(entry.get("name"))
        quantity = max(0, _as_int(entry.get("quantity")))
        if not name or quantity <= 0:
            continue
        item = inventory_map.get(name.lower())
        if item:
            item["quantity"] += quantity
            canonical_name = item["name"]
        else:
            item = {"name": name, "quantity": quantity}
            inventory.append(item)
            inventory_map[name.lower()] = item
            canonical_name = name
        applied["inventory_add"].append({"name": canonical_name, "quantity": quantity})

    hero["inventory"] = [
        item for item in inventory
        if not isinstance(item, dict) or item.get("quantity", 0) > 0
    ]

    gold_change = _as_int(state_delta.get("gold_change"))
    old_gold = hero.get("gold", 0)
    hero["gold"] = max(0, old_gold + gold_change)
    applied["gold_change"] = hero["gold"] - old_gold

    xp_change = max(0, min(_as_int(state_delta.get("xp_change")), MAX_XP_PER_TURN))
    old_xp = hero.get("xp", 0)
    old_level = hero.get("level", 1)
    old_max_hp = hero.get("max_hp", 8)
    hero["xp"] = old_xp + xp_change
    applied["xp_change"] = xp_change
    while hero["xp"] >= XP_PER_LEVEL:
        hero["xp"] -= XP_PER_LEVEL
        hero["level"] = hero.get("level", 1) + 1
        hp_gain = CLASS_HP_PER_LEVEL.get(hero.get("class", ""), 8)
        hero["max_hp"] = hero.get("max_hp", 8) + hp_gain
        hero["hp"] = hero["max_hp"]
    applied["old_level"] = old_level
    applied["new_level"] = hero.get("level", old_level)
    applied["level_up"] = applied["new_level"] > old_level
    applied["hp_gain"] = hero.get("max_hp", old_max_hp) - old_max_hp

    minutes_elapsed = max(0, _as_int(state_delta.get("minutes_elapsed")))
    time_state = world.get("time") or initial_time()
    if minutes_elapsed:
        new_time, did_full_rest = advance_time(time_state, minutes_elapsed)
        world["time"] = new_time
        applied["minutes_elapsed"] = minutes_elapsed
        if did_full_rest:
            for slot in hero.get("spell_slots", {}).values():
                slot["remaining"] = slot["max"]
            if hero.get("focus_points"):
                hero["focus_points"]["remaining"] = hero["focus_points"]["max"]
            applied["full_rest"] = True

    applied["world_updates"] = _merge_world_updates(world, world_updates)
    _advance_story_state(story_state, arc_progress)
    applied["continuity_update"] = _apply_continuity_update(story_state, continuity_update, advancement_type)
    applied["arc_status"] = story_state.get("status", "active")
    applied["current_act_id"] = story_state.get("current_act_id")
    applied["current_beat_id"] = story_state.get("current_beat_id")

    if applied["hero_defeated"]:
        story_state["status"] = "broken"
        applied["need_new_arc"] = True
        applied["replacement_reason"] = "The hero was defeated and the current arc can no longer continue as planned."
    elif story_state.get("status") in {"broken", "completed"}:
        applied["need_new_arc"] = True
        applied["replacement_reason"] = arc_progress.get("replacement_reason") or (
            "The arc is complete." if story_state["status"] == "completed" else "The current arc has become impossible."
        )

    updated_campaign = {
        **campaign,
        "hero_sheet": hero,
        "world_state": world,
        "story_state": story_state,
    }
    return updated_campaign, applied


def _merge_world_updates(world: dict, world_updates: dict) -> dict:
    applied = {}
    for key in ("npcs", "locations", "quests"):
        additions = []
        for value in _as_list(world_updates.get(key)):
            if value and value not in world.setdefault(key, []):
                world[key].append(value)
                additions.append(value)
        if additions:
            applied[key] = additions

    lore_update = _as_text(world_updates.get("lore"))
    if lore_update:
        existing = world.get("lore", "").strip()
        world["lore"] = f"{existing}\n{lore_update}".strip() if existing else lore_update
        applied["lore"] = lore_update
    return applied


def _append_unique_text(values: list[str], additions: object) -> list[str]:
    result = list(values)
    seen = {value.casefold() for value in result}
    for text in _unique_text_list(additions):
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _remove_text(values: list[str], removals: object) -> list[str]:
    remove_keys = {value.casefold() for value in _unique_text_list(removals)}
    if not remove_keys:
        return values
    return [value for value in values if value.casefold() not in remove_keys]


def _decay_recent_complications(recent: list[dict]) -> list[dict]:
    decayed = []
    for entry in recent:
        label = _as_text(entry.get("label"))
        cooldown = _as_int(entry.get("cooldown"), DEFAULT_COMPLICATION_COOLDOWN) - 1
        if label and cooldown > 0:
            decayed.append({"label": label, "cooldown": cooldown})
    return decayed


def _apply_continuity_update(story_state: dict, continuity_update: dict, advancement_type: str) -> dict:
    continuity = normalize_continuity_state(story_state.get("continuity"))
    applied = {
        "current_situation": "",
        "current_location": "",
        "resolved_threads_add": [],
        "resolved_threads_remove": [],
        "active_constraints_add": [],
        "active_constraints_remove": [],
        "recent_complication": "",
        "last_meaningful_change": "",
    }

    continuity["recent_complications"] = _decay_recent_complications(continuity["recent_complications"])

    current_situation = _as_text(continuity_update.get("current_situation"))
    if current_situation:
        continuity["current_situation"] = current_situation
        applied["current_situation"] = current_situation

    current_location = _as_text(continuity_update.get("current_location"))
    if current_location:
        continuity["current_location"] = current_location
        applied["current_location"] = current_location

    resolved_add = _unique_text_list(continuity_update.get("resolved_threads_add"))
    resolved_remove = _unique_text_list(continuity_update.get("resolved_threads_remove"))
    continuity["resolved_threads"] = _remove_text(continuity["resolved_threads"], resolved_remove)
    continuity["resolved_threads"] = _append_unique_text(continuity["resolved_threads"], resolved_add)
    applied["resolved_threads_add"] = resolved_add
    applied["resolved_threads_remove"] = resolved_remove

    constraints_add = _unique_text_list(continuity_update.get("active_constraints_add"))
    constraints_remove = _unique_text_list(continuity_update.get("active_constraints_remove"))
    continuity["active_constraints"] = _remove_text(continuity["active_constraints"], constraints_remove)
    continuity["active_constraints"] = _append_unique_text(continuity["active_constraints"], constraints_add)
    applied["active_constraints_add"] = constraints_add
    applied["active_constraints_remove"] = constraints_remove

    complication = _as_text(continuity_update.get("recent_complication"))
    if complication:
        existing = [
            entry for entry in continuity["recent_complications"]
            if entry["label"].casefold() != complication.casefold()
        ]
        existing.append({"label": complication, "cooldown": DEFAULT_COMPLICATION_COOLDOWN})
        continuity["recent_complications"] = existing[-MAX_RECENT_COMPLICATIONS:]
        applied["recent_complication"] = complication

    last_change = _as_text(continuity_update.get("last_meaningful_change"))
    if not last_change and advancement_type != "none":
        last_change = f"The turn advanced the story through {advancement_type}."
    if last_change:
        continuity["last_meaningful_change"] = last_change
        applied["last_meaningful_change"] = last_change

    story_state["continuity"] = continuity
    return applied


def _advance_story_state(story_state: dict, arc_progress: dict) -> None:
    current_act = get_current_act(story_state)
    current_beat = get_current_beat(story_state)
    if not current_act or not current_beat:
        return

    beat_status = _as_text(arc_progress.get("beat_status")) or "progress"
    replacement_reason = _as_text(arc_progress.get("replacement_reason"))
    story_state["last_turn_summary"] = _as_text(arc_progress.get("next_story_focus"))

    if beat_status == "failed":
        current_beat["status"] = "failed"
        story_state["status"] = "broken"
        if replacement_reason:
            story_state["last_turn_summary"] = replacement_reason
        return

    if beat_status in {"progress", "stalled"}:
        current_beat["status"] = "active"
    elif beat_status == "completed":
        current_beat["status"] = "completed"
        beats = current_act.get("beats", [])
        beat_index = next((index for index, beat in enumerate(beats) if beat.get("id") == current_beat.get("id")), -1)
        if 0 <= beat_index < len(beats) - 1:
            next_beat = beats[beat_index + 1]
            next_beat["status"] = "active"
            story_state["current_beat_id"] = next_beat["id"]
        else:
            current_act["status"] = "completed"
            acts = story_state.get("acts", [])
            act_index = next((index for index, act in enumerate(acts) if act.get("id") == current_act.get("id")), -1)
            if 0 <= act_index < len(acts) - 1:
                next_act = acts[act_index + 1]
                next_act["status"] = "active"
                story_state["current_act_id"] = next_act["id"]
                if next_act.get("beats"):
                    next_act["beats"][0]["status"] = "active"
                    story_state["current_beat_id"] = next_act["beats"][0]["id"]
            else:
                story_state["status"] = "completed"

    arc_status = _as_text(arc_progress.get("arc_status")) or "active"
    if arc_status in {"broken", "completed"}:
        story_state["status"] = arc_status
        if replacement_reason:
            story_state["last_turn_summary"] = replacement_reason
