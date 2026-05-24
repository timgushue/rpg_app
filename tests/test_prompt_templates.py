from ai.prompts.structured import STORY_ARC_PROMPT, TURN_RESOLUTION_PROMPT, TURN_RESULT_PROMPT


def test_story_arc_prompt_formats_without_key_errors():
    rendered = STORY_ARC_PROMPT.format(
        hero="Pip the Fighter",
        setting="Sandpoint is in danger.",
        replacement_reason="None",
        previous_arc="None",
        variation_hint="Use a fresh premise.",
    )

    assert '"title": "string"' in rendered
    assert "Pip the Fighter" in rendered
    assert "Use a fresh premise." in rendered


def test_turn_resolution_prompt_formats_without_key_errors():
    rendered = TURN_RESOLUTION_PROMPT.format(
        context="Context",
        player_action="I search the room.",
        roll_result='{"dc": 15}',
    )

    assert '"state_delta"' in rendered
    assert '"scene_title"' in rendered
    assert '"advancement_type"' in rendered
    assert '"continuity_update"' in rendered
    assert "Failed rolls should fail forward" in rendered
    assert "I search the room." in rendered


def test_turn_result_prompt_formats_without_key_errors():
    rendered = TURN_RESULT_PROMPT.format(
        context="Context",
        player_action="I sneak past the guard.",
        roll_result='{"dc": 15, "degree": "success"}',
    )

    assert '"story_beat"' in rendered
    assert '"resolution_data"' in rendered
    assert '"scene_title"' in rendered
    assert '"continuity_update"' in rendered
    assert "I sneak past the guard." in rendered
