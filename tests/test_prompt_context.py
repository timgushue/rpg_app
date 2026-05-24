from ai.prompts.context import build_context


def test_build_context_injects_hidden_continuity_guardrails():
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {
            "class": "Rogue",
            "level": 1,
            "hp": 8,
            "max_hp": 8,
            "xp": 0,
            "gold": 0,
            "ability_scores": {},
            "inventory": [],
        },
        "world_state": {"setting": "Test setting"},
        "story_state": {
            "title": "Arc",
            "premise": "Premise",
            "hero_goal": "Find the answer.",
            "main_threat": "A hidden danger.",
            "acts": [],
            "current_act_id": "",
            "current_beat_id": "",
            "continuity": {
                "current_situation": "The hero is safe enough to read.",
                "current_location": "Quiet shore",
                "resolved_threads": ["The chase ended."],
                "active_constraints": ["Do not immediately restart the chase without a new trigger."],
                "recent_complications": [{"label": "pursuit", "cooldown": 2}],
                "last_meaningful_change": "The hero reached shore.",
            },
        },
    }

    context = build_context(campaign, [], [])

    assert "=== HIDDEN CONTINUITY GUARDRAILS ===" in context
    assert "The chase ended." in context
    assert "Do not immediately restart the chase without a new trigger." in context
    assert "pursuit (2 turns)" in context
