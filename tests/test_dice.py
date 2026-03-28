from unittest.mock import patch
import pytest
from dice import detect_skill, get_modifier, roll_action, format_roll_for_display


# ---------------------------------------------------------------------------
# detect_skill
# ---------------------------------------------------------------------------

def test_detect_skill_athletics():
    assert detect_skill("I try to climb the wall") == "Athletics"

def test_detect_skill_stealth():
    assert detect_skill("I sneak past the guard") == "Stealth"

def test_detect_skill_thievery():
    assert detect_skill("I pick the lock on the door") == "Thievery"

def test_detect_skill_deception():
    assert detect_skill("I lie to the merchant") == "Deception"

def test_detect_skill_perception():
    assert detect_skill("I search the room for hidden doors") == "Perception"

def test_detect_skill_attack():
    assert detect_skill("I attack the goblin with my sword") == "Attack"

def test_detect_skill_case_insensitive():
    assert detect_skill("I CLIMB the cliff") == "Athletics"

def test_detect_skill_unknown_returns_none():
    assert detect_skill("I stand here and wait") is None


# ---------------------------------------------------------------------------
# get_modifier
# ---------------------------------------------------------------------------

HERO_FIGHTER = {
    "class": "Fighter",
    "ability_scores": {
        "strength": 18,   # +4
        "dexterity": 14,  # +2
        "constitution": 14,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
    },
}

def test_get_modifier_trained_skill():
    # Fighter is trained in Athletics (STR-based) → +4 ability + 2 proficiency = +6
    assert get_modifier(HERO_FIGHTER, "Athletics") == 6

def test_get_modifier_untrained_skill():
    # Fighter is not trained in Arcana (INT-based, score 10) → +0
    assert get_modifier(HERO_FIGHTER, "Arcana") == 0

def test_get_modifier_trained_perception():
    # All classes are trained in Perception (WIS-based, score 10) → +0 + 2 = +2
    assert get_modifier(HERO_FIGHTER, "Perception") == 2

def test_get_modifier_none_skill():
    assert get_modifier(HERO_FIGHTER, None) == 0

def test_get_modifier_negative_ability():
    hero = {
        "class": "Fighter",
        "ability_scores": {"strength": 8, "dexterity": 10, "constitution": 10,
                           "intelligence": 10, "wisdom": 10, "charisma": 10},
    }
    # STR 8 → -1, trained in Athletics → -1 + 2 = +1
    assert get_modifier(hero, "Athletics") == 1


# ---------------------------------------------------------------------------
# roll_action — degree of success
# ---------------------------------------------------------------------------

DC = 15

def _roll(fixed_roll, hero=None, action="attack the goblin", dc=DC):
    if hero is None:
        hero = {"class": "Fighter", "ability_scores": {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }}
    with patch("dice.random.randint", return_value=fixed_roll):
        return roll_action(hero, action, dc=dc)

def test_natural_20_is_critical_success():
    assert _roll(20)["degree"] == "critical success"

def test_natural_1_is_critical_failure():
    assert _roll(1)["degree"] == "critical failure"

def test_total_10_above_dc_is_critical_success():
    # roll=16, modifier=0, total=16, dc=5 → total >= dc+10 (15) → crit success
    result = _roll(16, dc=5)
    assert result["degree"] == "critical success"

def test_total_10_below_dc_is_critical_failure():
    # roll=4, modifier=0, total=4, dc=15 → total <= dc-10 (5) → crit failure
    result = _roll(4, dc=15)
    assert result["degree"] == "critical failure"

def test_success():
    # roll=15, modifier=0, total=15 vs DC 15 → success
    assert _roll(15, dc=15)["degree"] == "success"

def test_failure():
    # roll=10, modifier=0, total=10 vs DC 15 → failure
    assert _roll(10, dc=15)["degree"] == "failure"

def test_result_contains_expected_keys():
    result = _roll(10)
    assert {"skill", "roll", "modifier", "total", "dc", "degree"} <= result.keys()

def test_total_is_roll_plus_modifier():
    result = _roll(12)
    assert result["total"] == result["roll"] + result["modifier"]


# ---------------------------------------------------------------------------
# format_roll_for_display
# ---------------------------------------------------------------------------

def test_format_no_roll_when_dc_zero():
    result = {"dc": 0, "skill": None, "roll": 10, "modifier": 0, "total": 10, "degree": "success"}
    assert format_roll_for_display(result) == "🎲 No roll needed"

def test_format_positive_modifier():
    result = {"dc": 15, "skill": "Athletics", "roll": 12, "modifier": 4, "total": 16, "degree": "success"}
    display = format_roll_for_display(result)
    assert "+4" in display
    assert "16" in display
    assert "DC 15" in display

def test_format_negative_modifier():
    result = {"dc": 15, "skill": "Arcana", "roll": 10, "modifier": -2, "total": 8, "degree": "failure"}
    display = format_roll_for_display(result)
    assert "-2" in display

def test_format_none_skill_shows_check():
    result = {"dc": 15, "skill": None, "roll": 10, "modifier": 0, "total": 10, "degree": "failure"}
    display = format_roll_for_display(result)
    assert "Check" in display
