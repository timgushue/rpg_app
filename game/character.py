"""
Character creation helpers — ability score computation from ancestry and class.
"""

from .game_data import ANCESTRY_ABILITY_BOOSTS, CLASS_KEY_ABILITY, CLASS_SECONDARY_ABILITIES

VALID_ABILITIES = {
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
}


def build_ability_scores(ancestry: str, hero_class: str) -> dict:
    """
    Compute starting ability scores from ancestry boosts/flaws and class key/secondary abilities.
    Key ability starts at 18; secondaries start at 14; all others at 10.
    Ancestry adjustments (+2/-2) are applied on top, clamped to [4, 20].
    """
    scores = {
        "strength": 10, "dexterity": 10, "constitution": 10,
        "intelligence": 10, "wisdom": 10, "charisma": 10,
    }
    key = CLASS_KEY_ABILITY.get(hero_class)
    if key:
        scores[key] = 18
    for ability in CLASS_SECONDARY_ABILITIES.get(hero_class, []):
        if scores[ability] < 14:
            scores[ability] = 14
    for ability, delta in ANCESTRY_ABILITY_BOOSTS.get(ancestry, {}).items():
        scores[ability] = max(4, min(20, scores[ability] + delta))
    return scores


def apply_ability_bump(hero_sheet: dict, ability: str, amount: int = 2) -> dict:
    normalized = ability.strip().lower()
    if normalized not in VALID_ABILITIES:
        raise ValueError(f"Unknown ability: {ability}")

    scores = dict(hero_sheet.get("ability_scores", {}))
    current = int(scores.get(normalized, 10))
    scores[normalized] = max(4, min(20, current + amount))
    updated = dict(hero_sheet)
    updated["ability_scores"] = scores
    return updated
