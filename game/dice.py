import random
from typing import Optional

# Maps each skill to the ability score that governs it (Pathfinder 2e)
SKILL_TO_ABILITY = {
    "Acrobatics":   "dexterity",
    "Arcana":       "intelligence",
    "Athletics":    "strength",
    "Crafting":     "intelligence",
    "Deception":    "charisma",
    "Diplomacy":    "charisma",
    "Intimidation": "charisma",
    "Medicine":     "wisdom",
    "Nature":       "wisdom",
    "Occultism":    "intelligence",
    "Performance":  "charisma",
    "Perception":   "wisdom",
    "Religion":     "wisdom",
    "Society":      "intelligence",
    "Stealth":      "dexterity",
    "Survival":     "wisdom",
    "Thievery":     "dexterity",
    "Attack":       "strength",
}

# Skills each class is trained in at level 1
CLASS_TRAINED_SKILLS = {
    "Fighter":            ["Athletics", "Intimidation", "Perception"],
    "Wizard":             ["Arcana", "Occultism", "Perception"],
    "Rogue":              ["Stealth", "Thievery", "Deception", "Athletics", "Perception"],
    "Cleric":             ["Religion", "Medicine", "Perception"],
    "Ranger":             ["Nature", "Survival", "Athletics", "Stealth", "Perception"],
    "Barbarian":          ["Athletics", "Intimidation", "Perception"],
    "Paladin (Champion)": ["Religion", "Medicine", "Diplomacy", "Perception"],
    "Druid":              ["Nature", "Survival", "Medicine", "Perception"],
    "Bard":               ["Performance", "Occultism", "Diplomacy", "Deception", "Perception"],
    "Monk":               ["Athletics", "Acrobatics", "Perception"],
    "Sorcerer":           ["Arcana", "Occultism", "Perception"],
    "Alchemist":          ["Crafting", "Nature", "Arcana", "Perception"],
}

# Classes that can cast spells
SPELLCASTING_CLASSES = {
    "Wizard", "Sorcerer", "Cleric", "Druid", "Bard", "Paladin (Champion)",
}
# Ranger gets limited spells at level 2+, Alchemist uses infused items not spells

# Keywords in player text → detected skill
ACTION_KEYWORDS: dict[str, list[str]] = {
    "Athletics":    ["climb", "jump", "leap", "swim", "grapple", "push", "shove",
                     "force open", "break down", "lift", "pull", "drag"],
    "Stealth":      ["sneak", "hide", "creep", "move silently", "conceal myself",
                     "slip past", "shadow"],
    "Thievery":     ["pick the lock", "lockpick", "pick lock", "disarm the trap",
                     "disarm trap", "steal", "pickpocket", "filch", "palm"],
    "Deception":    ["lie", "bluff", "deceive", "trick", "disguise", "mislead",
                     "pretend", "fake"],
    "Diplomacy":    ["persuade", "convince", "negotiate", "befriend", "appeal",
                     "request", "ask nicely", "talk them into"],
    "Intimidation": ["intimidate", "threaten", "menace", "frighten", "bully",
                     "scare", "glare"],
    "Arcana":       ["recall knowledge", "identify the magic", "read the rune",
                     "analyze the spell", "arcana", "magical lore"],
    "Medicine":     ["heal", "treat wounds", "bandage", "tend to", "first aid",
                     "patch up", "medicine"],
    "Nature":       ["identify the creature", "nature check", "handle the animal",
                     "forage", "commune"],
    "Perception":   ["search", "look for", "look around", "notice", "investigate",
                     "examine", "scan", "detect", "spot", "listen", "check for traps"],
    "Survival":     ["track", "follow the trail", "navigate", "find north",
                     "forage for food", "survival"],
    "Acrobatics":   ["balance", "tumble", "flip", "squeeze through", "acrobatics",
                     "dodge past", "roll under"],
    "Performance":  ["perform", "sing", "play my instrument", "dance", "entertain"],
    "Attack":       ["attack", "strike", "hit", "swing", "slash", "stab", "shoot",
                     "fire my", "throw my", "cast", "charge at", "lunge"],
}

# Typical DCs by difficulty (Pathfinder 2e Simple DCs)
DC_TRIVIAL = 5
DC_EASY    = 10
DC_NORMAL  = 15
DC_HARD    = 20
DC_VERY_HARD = 25

PROFICIENCY_BONUS = 2  # trained proficiency at level 1


def _ability_modifier(score: int) -> int:
    return (score - 10) // 2


def detect_skill(action_text: str) -> Optional[str]:
    """Return the most likely Pathfinder skill for the described action."""
    text = action_text.lower()
    for skill, keywords in ACTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return skill
    return None


def get_modifier(hero_sheet: dict, skill: Optional[str]) -> int:
    """Calculate the total modifier for a skill check given the hero sheet."""
    if skill is None:
        return 0
    ability = SKILL_TO_ABILITY.get(skill, "strength")
    scores = hero_sheet.get("ability_scores", {})
    modifier = _ability_modifier(scores.get(ability, 10))
    hero_class = hero_sheet.get("class", "")
    if skill in CLASS_TRAINED_SKILLS.get(hero_class, []):
        modifier += PROFICIENCY_BONUS
    return modifier


def roll_action(hero_sheet: dict, action_text: str, dc: int = DC_NORMAL) -> dict:
    """
    Roll a d20 check for the given action and return full result details.
    Returns a dict with: skill, roll, modifier, total, dc, degree.
    """
    skill = detect_skill(action_text)
    modifier = get_modifier(hero_sheet, skill)
    roll = random.randint(1, 20)
    total = roll + modifier

    # Pathfinder 2e degrees of success
    if roll == 20 or total >= dc + 10:
        degree = "critical success"
    elif roll == 1 or total <= dc - 10:
        degree = "critical failure"
    elif total >= dc:
        degree = "success"
    else:
        degree = "failure"

    return {
        "skill":    skill,
        "roll":     roll,
        "modifier": modifier,
        "total":    total,
        "dc":       dc,
        "degree":   degree,
    }


def is_spellcasting_class(hero_class: str) -> bool:
    return hero_class in SPELLCASTING_CLASSES


def format_roll_for_display(result: dict) -> str:
    """Human-readable roll summary for the UI."""
    if result.get("dc", 0) == 0:
        return "🎲 No roll needed"

    skill_label = result["skill"] or "Check"
    mod = result["modifier"]
    mod_str = f"+{mod}" if mod >= 0 else str(mod)
    degree_emoji = {
        "critical success": "✨",
        "success":          "✅",
        "failure":          "❌",
        "critical failure": "💀",
    }.get(result["degree"], "🎲")
    return (
        f"🎲 {skill_label}  |  "
        f"Rolled {result['roll']} {mod_str} = **{result['total']}** vs DC {result['dc']}  |  "
        f"{degree_emoji} {result['degree'].title()}"
    )
