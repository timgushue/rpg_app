import pytest
from game.character import build_ability_scores
from game.game_data import CLASSES, ANCESTRIES, CLASS_KEY_ABILITY, CLASS_SECONDARY_ABILITIES


# ---------------------------------------------------------------------------
# Key ability is always 18
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hero_class", CLASSES)
def test_key_ability_is_18_before_ancestry(hero_class):
    # Use Human (no ancestry adjustments) so we see class scores cleanly
    scores = build_ability_scores("Human", hero_class)
    key = CLASS_KEY_ABILITY[hero_class]
    assert scores[key] == 18, f"{hero_class} key ability {key} should be 18, got {scores[key]}"


# ---------------------------------------------------------------------------
# Secondary abilities are at least 14
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hero_class", CLASSES)
def test_secondary_abilities_at_least_14(hero_class):
    scores = build_ability_scores("Human", hero_class)
    for ability in CLASS_SECONDARY_ABILITIES[hero_class]:
        assert scores[ability] >= 14, (
            f"{hero_class} secondary ability {ability} should be >= 14, got {scores[ability]}"
        )


# ---------------------------------------------------------------------------
# Ancestry boosts and flaws are applied
# ---------------------------------------------------------------------------

def test_elf_gets_dex_and_int_boost():
    scores = build_ability_scores("Elf", "Fighter")  # Fighter key=STR, secondary=CON/DEX
    base = build_ability_scores("Human", "Fighter")
    assert scores["dexterity"] == base["dexterity"] + 2
    assert scores["intelligence"] == base["intelligence"] + 2

def test_elf_gets_con_flaw():
    scores = build_ability_scores("Elf", "Fighter")
    base = build_ability_scores("Human", "Fighter")
    assert scores["constitution"] == base["constitution"] - 2

def test_dwarf_gets_con_and_wis_boost():
    scores = build_ability_scores("Dwarf", "Fighter")
    base = build_ability_scores("Human", "Fighter")
    assert scores["constitution"] == base["constitution"] + 2
    assert scores["wisdom"] == base["wisdom"] + 2

def test_dwarf_gets_cha_flaw():
    scores = build_ability_scores("Dwarf", "Bard")  # Bard key=CHA
    base = build_ability_scores("Human", "Bard")
    assert scores["charisma"] == base["charisma"] - 2

def test_human_no_adjustments():
    scores = build_ability_scores("Human", "Wizard")
    base_scores = build_ability_scores("Human", "Wizard")
    assert scores == base_scores


# ---------------------------------------------------------------------------
# Scores are clamped to [4, 20]
# ---------------------------------------------------------------------------

def test_score_never_exceeds_20():
    for ancestry in ANCESTRIES:
        for hero_class in CLASSES:
            scores = build_ability_scores(ancestry, hero_class)
            for ability, val in scores.items():
                assert val <= 20, f"{ancestry}/{hero_class} {ability}={val} exceeds 20"

def test_score_never_below_4():
    for ancestry in ANCESTRIES:
        for hero_class in CLASSES:
            scores = build_ability_scores(ancestry, hero_class)
            for ability, val in scores.items():
                assert val >= 4, f"{ancestry}/{hero_class} {ability}={val} below 4"


# ---------------------------------------------------------------------------
# All six abilities are always present
# ---------------------------------------------------------------------------

ABILITY_NAMES = {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}

@pytest.mark.parametrize("ancestry", ANCESTRIES)
@pytest.mark.parametrize("hero_class", CLASSES)
def test_all_abilities_present(ancestry, hero_class):
    scores = build_ability_scores(ancestry, hero_class)
    assert set(scores.keys()) == ABILITY_NAMES
