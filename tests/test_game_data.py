"""
Data completeness tests — every class and ancestry must have a full set of entries
in every game data table. These catch typos and missing entries early.
"""
import pytest
from game.game_data import (
    CLASSES,
    ANCESTRIES,
    CLASS_KEY_ABILITY,
    CLASS_SECONDARY_ABILITIES,
    CLASS_STARTING_GOLD,
    CLASS_HP_PER_LEVEL,
    CLASS_STARTING_GEAR,
    CLASS_SPELL_SLOTS,
    CLASS_FOCUS_POINTS,
    ANCESTRY_ABILITY_BOOSTS,
    XP_PER_LEVEL,
    ADVENTURE_STARTERS,
)


# ---------------------------------------------------------------------------
# Every class has an entry in every class table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_key_ability(hero_class):
    assert hero_class in CLASS_KEY_ABILITY

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_secondary_abilities(hero_class):
    assert hero_class in CLASS_SECONDARY_ABILITIES
    assert len(CLASS_SECONDARY_ABILITIES[hero_class]) == 2

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_starting_gold(hero_class):
    assert hero_class in CLASS_STARTING_GOLD
    assert CLASS_STARTING_GOLD[hero_class] > 0

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_hp_per_level(hero_class):
    assert hero_class in CLASS_HP_PER_LEVEL
    assert CLASS_HP_PER_LEVEL[hero_class] >= 6

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_starting_gear(hero_class):
    assert hero_class in CLASS_STARTING_GEAR
    assert len(CLASS_STARTING_GEAR[hero_class]) > 0

@pytest.mark.parametrize("hero_class", CLASSES)
def test_starting_gear_entries_are_tuples(hero_class):
    for entry in CLASS_STARTING_GEAR[hero_class]:
        name, qty = entry
        assert isinstance(name, str) and len(name) > 0
        assert isinstance(qty, int) and qty > 0

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_spell_slots(hero_class):
    assert hero_class in CLASS_SPELL_SLOTS

@pytest.mark.parametrize("hero_class", CLASSES)
def test_spell_slot_entries_have_max_and_remaining(hero_class):
    for level, data in CLASS_SPELL_SLOTS[hero_class].items():
        assert "max" in data and "remaining" in data
        assert data["max"] >= data["remaining"] >= 0

@pytest.mark.parametrize("hero_class", CLASSES)
def test_class_has_focus_points(hero_class):
    assert hero_class in CLASS_FOCUS_POINTS
    fp = CLASS_FOCUS_POINTS[hero_class]
    assert "max" in fp and "remaining" in fp
    assert fp["max"] >= fp["remaining"] >= 0


# ---------------------------------------------------------------------------
# Every ancestry has an entry in the boosts table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ancestry", ANCESTRIES)
def test_ancestry_has_ability_boosts_entry(ancestry):
    assert ancestry in ANCESTRY_ABILITY_BOOSTS

@pytest.mark.parametrize("ancestry", ANCESTRIES)
def test_ancestry_boosts_are_valid_deltas(ancestry):
    for ability, delta in ANCESTRY_ABILITY_BOOSTS[ancestry].items():
        assert ability in {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}
        assert delta in {-2, 2}, f"{ancestry} has unexpected boost value {delta} for {ability}"


# ---------------------------------------------------------------------------
# Key ability and secondary abilities don't overlap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hero_class", CLASSES)
def test_key_ability_not_in_secondary(hero_class):
    key = CLASS_KEY_ABILITY[hero_class]
    secondary = CLASS_SECONDARY_ABILITIES[hero_class]
    assert key not in secondary, f"{hero_class}: key ability {key} is also listed as secondary"


# ---------------------------------------------------------------------------
# Global constants
# ---------------------------------------------------------------------------

def test_xp_per_level_is_positive():
    assert XP_PER_LEVEL > 0

def test_adventure_starters_not_empty():
    assert len(ADVENTURE_STARTERS) > 0
    for key, text in ADVENTURE_STARTERS.items():
        assert isinstance(text, str) and len(text) > 20
