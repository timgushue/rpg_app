from game.game_time import initial_time
from game.state_update import apply_turn_resolution, build_fallback_story_state, normalize_story_state


def test_normalize_story_state_adds_hidden_continuity_defaults():
    story = normalize_story_state({"title": "Arc Title", "acts": [], "current_act_id": "", "current_beat_id": ""})

    assert story["continuity"]["current_situation"] == ""
    assert story["continuity"]["resolved_threads"] == []
    assert story["continuity"]["active_constraints"] == []
    assert story["continuity"]["recent_complications"] == []


def test_apply_turn_resolution_updates_resources_and_progression():
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {
            "class": "Fighter",
            "level": 1,
            "xp": 990,
            "gold": 5,
            "hp": 12,
            "max_hp": 18,
            "spell_slots": {},
            "focus_points": {"max": 0, "remaining": 0},
            "inventory": [{"name": "arrows", "quantity": 3}],
        },
        "world_state": {"setting": "Test", "npcs": [], "locations": [], "quests": [], "lore": "", "time": initial_time()},
        "story_state": build_fallback_story_state("Pip", {"setting": "Test"}),
    }
    resolution = {
        "state_delta": {
            "hp_change": -4,
            "xp_change": 20,
            "gold_change": 7,
            "inventory_add": [{"name": "healing potion", "quantity": 1}],
            "inventory_remove": [{"name": "arrows", "quantity": 2}],
            "spell_slots_used": {},
            "focus_points_used": 0,
            "minutes_elapsed": 10,
            "full_rest": False,
            "short_rest": False,
        },
        "world_updates": {"locations": ["Hidden Tower"], "quests": ["Find the tower key"]},
        "arc_progress": {"beat_status": "completed", "arc_status": "active", "next_story_focus": "Press deeper into the tower."},
    }

    updated_campaign, applied = apply_turn_resolution(campaign, resolution)

    assert updated_campaign["hero_sheet"]["hp"] == updated_campaign["hero_sheet"]["max_hp"]
    assert updated_campaign["hero_sheet"]["gold"] == 12
    assert updated_campaign["hero_sheet"]["level"] == 2
    assert updated_campaign["hero_sheet"]["xp"] == 10
    assert {"name": "healing potion", "quantity": 1} in updated_campaign["hero_sheet"]["inventory"]
    assert updated_campaign["hero_sheet"]["inventory"][0]["quantity"] == 1
    assert "Hidden Tower" in updated_campaign["world_state"]["locations"]
    assert applied["xp_change"] == 20
    assert applied["current_beat_id"] != "beat-1"
    assert applied["level_up"] is True
    assert applied["old_level"] == 1
    assert applied["new_level"] == 2
    assert applied["hp_gain"] > 0


def test_apply_turn_resolution_marks_broken_arc_when_hero_defeated():
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {
            "class": "Fighter",
            "level": 1,
            "xp": 0,
            "gold": 0,
            "hp": 3,
            "max_hp": 18,
            "spell_slots": {},
            "focus_points": {"max": 0, "remaining": 0},
            "inventory": [],
        },
        "world_state": {"setting": "Test", "npcs": [], "locations": [], "quests": [], "lore": "", "time": initial_time()},
        "story_state": build_fallback_story_state("Pip", {"setting": "Test"}),
    }
    resolution = {
        "state_delta": {
            "hp_change": -10,
            "xp_change": 0,
            "gold_change": 0,
            "inventory_add": [],
            "inventory_remove": [],
            "spell_slots_used": {},
            "focus_points_used": 0,
            "minutes_elapsed": 1,
            "full_rest": False,
            "short_rest": False,
        },
        "world_updates": {},
        "arc_progress": {"beat_status": "failed", "arc_status": "broken", "replacement_reason": "The hero was overwhelmed."},
    }

    updated_campaign, applied = apply_turn_resolution(campaign, resolution)

    assert updated_campaign["hero_sheet"]["hp"] == 0
    assert updated_campaign["story_state"]["status"] == "broken"
    assert applied["need_new_arc"] is True


def test_apply_turn_resolution_clamps_xp_per_turn():
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {
            "class": "Fighter",
            "level": 1,
            "xp": 0,
            "gold": 0,
            "hp": 18,
            "max_hp": 18,
            "spell_slots": {},
            "focus_points": {"max": 0, "remaining": 0},
            "inventory": [],
        },
        "world_state": {"setting": "Test", "npcs": [], "locations": [], "quests": [], "lore": "", "time": initial_time()},
        "story_state": build_fallback_story_state("Pip", {"setting": "Test"}),
    }
    resolution = {
        "state_delta": {
            "hp_change": 0,
            "xp_change": 250,
            "gold_change": 0,
            "inventory_add": [],
            "inventory_remove": [],
            "spell_slots_used": {},
            "focus_points_used": 0,
            "minutes_elapsed": 5,
            "full_rest": False,
            "short_rest": False,
        },
        "world_updates": {},
        "arc_progress": {"beat_status": "completed", "arc_status": "active", "next_story_focus": "Keep moving."},
    }

    updated_campaign, applied = apply_turn_resolution(campaign, resolution)

    assert applied["xp_change"] == 100
    assert updated_campaign["hero_sheet"]["xp"] == 100


def test_apply_turn_resolution_ignores_malformed_ai_fields():
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {
            "class": "Fighter",
            "level": 1,
            "xp": 0,
            "gold": 3,
            "hp": 18,
            "max_hp": 18,
            "spell_slots": {"1": {"max": 2, "remaining": 2}},
            "focus_points": {"max": 1, "remaining": 1},
            "inventory": [{"name": "torch", "quantity": 2}, {"quantity": 99}],
        },
        "world_state": {"setting": "Test", "npcs": [], "locations": [], "quests": [], "lore": "", "time": initial_time()},
        "story_state": build_fallback_story_state("Pip", {"setting": "Test"}),
    }
    resolution = {
        "state_delta": {
            "hp_change": None,
            "xp_change": "not a number",
            "gold_change": "",
            "inventory_add": "healing potion",
            "inventory_remove": [{"name": "torch", "quantity": None}, "bad entry"],
            "spell_slots_used": [],
            "focus_points_used": "nope",
            "minutes_elapsed": None,
        },
        "world_updates": {"locations": "not a list", "lore": None},
        "arc_progress": {"beat_status": None, "arc_status": None, "next_story_focus": None},
    }

    updated_campaign, applied = apply_turn_resolution(campaign, resolution)

    assert updated_campaign["hero_sheet"]["hp"] == 18
    assert updated_campaign["hero_sheet"]["xp"] == 0
    assert updated_campaign["hero_sheet"]["gold"] == 3
    assert updated_campaign["hero_sheet"]["inventory"][0]["quantity"] == 2
    assert applied["xp_change"] == 0
    assert applied["gold_change"] == 0
    assert applied["minutes_elapsed"] == 0


def test_apply_turn_resolution_updates_hidden_continuity_and_decays_cooldowns():
    story_state = build_fallback_story_state("Pip", {"setting": "Test"})
    story_state["continuity"] = {
        "current_situation": "The hero is outside.",
        "current_location": "Old Road",
        "resolved_threads": ["The locked gate is open."],
        "active_constraints": ["The gate should not relock without a new cause."],
        "recent_complications": [
            {"label": "pursuit", "cooldown": 2},
            {"label": "bad weather", "cooldown": 1},
        ],
        "last_meaningful_change": "The gate opened.",
    }
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {
            "class": "Fighter",
            "level": 1,
            "xp": 0,
            "gold": 0,
            "hp": 18,
            "max_hp": 18,
            "spell_slots": {},
            "focus_points": {"max": 0, "remaining": 0},
            "inventory": [],
        },
        "world_state": {"setting": "Test", "npcs": [], "locations": [], "quests": [], "lore": "", "time": initial_time()},
        "story_state": story_state,
    }
    resolution = {
        "advancement_type": "information",
        "state_delta": {"xp_change": 10},
        "world_updates": {},
        "arc_progress": {"beat_status": "progress", "arc_status": "active", "next_story_focus": "Use the clue."},
        "continuity_update": {
            "current_situation": "The hero has a clue and a choice.",
            "current_location": "Old Shrine",
            "resolved_threads_add": ["The hidden clue was found."],
            "active_constraints_add": ["Do not make the same guard appear again without a new trigger."],
            "recent_complication": "lost time",
            "last_meaningful_change": "A clue was found, but time was lost.",
        },
    }

    updated_campaign, applied = apply_turn_resolution(campaign, resolution)
    continuity = updated_campaign["story_state"]["continuity"]

    assert continuity["current_situation"] == "The hero has a clue and a choice."
    assert continuity["current_location"] == "Old Shrine"
    assert "The locked gate is open." in continuity["resolved_threads"]
    assert "The hidden clue was found." in continuity["resolved_threads"]
    assert "The gate should not relock without a new cause." in continuity["active_constraints"]
    assert "Do not make the same guard appear again without a new trigger." in continuity["active_constraints"]
    assert continuity["recent_complications"] == [
        {"label": "pursuit", "cooldown": 1},
        {"label": "lost time", "cooldown": 3},
    ]
    assert continuity["last_meaningful_change"] == "A clue was found, but time was lost."
    assert applied["advancement_type"] == "information"
    assert applied["continuity_update"]["recent_complication"] == "lost time"
