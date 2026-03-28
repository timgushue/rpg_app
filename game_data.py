"""
Pathfinder 2e game data tables — ancestries, classes, gear, spells, XP, etc.
Pure data: no logic, no imports.
"""

ANCESTRIES = [
    "Human", "Elf", "Dwarf", "Gnome", "Halfling", "Half-Elf", "Half-Orc", "Goblin",
    "Leshy", "Catfolk", "Ratfolk", "Tengu",
]

CLASSES = [
    "Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Barbarian",
    "Paladin (Champion)", "Druid", "Bard", "Monk", "Sorcerer", "Alchemist",
]

# Ability score adjustments from ancestry (Pathfinder 2e fixed boosts + flaw)
# Positive = boost (+2), negative = flaw (-2)
ANCESTRY_ABILITY_BOOSTS: dict[str, dict[str, int]] = {
    "Human":    {},                                                          # 2 free boosts — applied via class secondary
    "Elf":      {"dexterity": 2, "intelligence": 2, "constitution": -2},
    "Dwarf":    {"constitution": 2, "wisdom": 2, "charisma": -2},
    "Gnome":    {"constitution": 2, "charisma": 2, "strength": -2},
    "Halfling": {"dexterity": 2, "wisdom": 2, "strength": -2},
    "Half-Elf": {"dexterity": 2, "intelligence": 2},
    "Half-Orc": {"strength": 2, "constitution": 2},
    "Goblin":   {"dexterity": 2, "charisma": 2, "wisdom": -2},
    "Leshy":    {"constitution": 2, "wisdom": 2, "intelligence": -2},
    "Catfolk":  {"dexterity": 2, "charisma": 2, "wisdom": -2},
    "Ratfolk":  {"dexterity": 2, "intelligence": 2, "strength": -2},
    "Tengu":    {"dexterity": 2, "intelligence": 2, "constitution": -2},
}

# Primary (key) ability for each class — boosted to 18 at character creation
CLASS_KEY_ABILITY: dict[str, str] = {
    "Fighter":            "strength",
    "Wizard":             "intelligence",
    "Rogue":              "dexterity",
    "Cleric":             "wisdom",
    "Ranger":             "dexterity",
    "Barbarian":          "strength",
    "Paladin (Champion)": "strength",
    "Druid":              "wisdom",
    "Bard":               "charisma",
    "Monk":               "strength",
    "Sorcerer":           "charisma",
    "Alchemist":          "intelligence",
}

# Secondary abilities boosted to 14 at character creation
CLASS_SECONDARY_ABILITIES: dict[str, list[str]] = {
    "Fighter":            ["constitution", "dexterity"],
    "Wizard":             ["dexterity", "constitution"],
    "Rogue":              ["intelligence", "charisma"],
    "Cleric":             ["wisdom", "constitution"],
    "Ranger":             ["constitution", "wisdom"],
    "Barbarian":          ["constitution", "dexterity"],
    "Paladin (Champion)": ["constitution", "wisdom"],
    "Druid":              ["constitution", "dexterity"],
    "Bard":               ["dexterity", "intelligence"],
    "Monk":               ["constitution", "wisdom"],
    "Sorcerer":           ["dexterity", "constitution"],
    "Alchemist":          ["constitution", "dexterity"],
}

XP_PER_LEVEL = 1000  # Pathfinder 2e standard

# Starting gold (gp) by class
CLASS_STARTING_GOLD = {
    "Fighter":            15,
    "Wizard":             10,
    "Rogue":              15,
    "Cleric":             10,
    "Ranger":             15,
    "Barbarian":          10,
    "Paladin (Champion)": 10,
    "Druid":              10,
    "Bard":               15,
    "Monk":               10,
    "Sorcerer":           10,
    "Alchemist":          10,
}

# HP gained per level (class hit points, no CON bonus assumed at level 1)
CLASS_HP_PER_LEVEL = {
    "Fighter":            10,
    "Wizard":              6,
    "Rogue":               8,
    "Cleric":              8,
    "Ranger":             10,
    "Barbarian":          12,
    "Paladin (Champion)": 10,
    "Druid":               8,
    "Bard":                8,
    "Monk":               10,
    "Sorcerer":            6,
    "Alchemist":           8,
}

# Starting gear as (item_name, quantity) tuples
CLASS_STARTING_GEAR = {
    "Fighter":            [("longsword", 1), ("chain mail", 1), ("shield", 1),
                           ("adventurer's kit", 1), ("torch", 5)],
    "Wizard":             [("staff", 1), ("spellbook", 1), ("component pouch", 1),
                           ("scholar's kit", 1), ("torch", 5)],
    "Rogue":              [("shortsword", 1), ("shortbow", 1), ("arrows", 20),
                           ("leather armor", 1), ("thieves' tools", 1),
                           ("burglar's kit", 1), ("torch", 5)],
    "Cleric":             [("mace", 1), ("wooden shield", 1), ("chain mail", 1),
                           ("healer's kit", 1), ("religious symbol", 1), ("torch", 5)],
    "Ranger":             [("longbow", 1), ("arrows", 20), ("longsword", 1),
                           ("leather armor", 1), ("adventurer's kit", 1), ("torch", 5)],
    "Barbarian":          [("greataxe", 1), ("hide armor", 1),
                           ("adventurer's kit", 1), ("torch", 5)],
    "Paladin (Champion)": [("longsword", 1), ("full plate", 1), ("shield", 1),
                           ("religious symbol", 1), ("healer's kit", 1), ("torch", 5)],
    "Druid":              [("staff", 1), ("leather armor", 1), ("holly and mistletoe", 1),
                           ("adventurer's kit", 1), ("torch", 5)],
    "Bard":               [("rapier", 1), ("leather armor", 1), ("musical instrument", 1),
                           ("entertainer's kit", 1), ("torch", 5)],
    "Monk":               [("staff", 1), ("padded armor", 1),
                           ("adventurer's kit", 1), ("torch", 5)],
    "Sorcerer":           [("staff", 1), ("component pouch", 1),
                           ("scholar's kit", 1), ("torch", 5)],
    "Alchemist":          [("alchemist's tools", 1), ("leather armor", 1),
                           ("adventurer's kit", 1), ("alchemist's fire", 3),
                           ("healing potion (minor)", 2), ("torch", 5)],
}

# Spell slots at level 1 by class: {slot_level_str: {max, remaining}}
CLASS_SPELL_SLOTS = {
    "Wizard":             {"1": {"max": 2, "remaining": 2}},
    "Sorcerer":           {"1": {"max": 2, "remaining": 2}},
    "Cleric":             {"1": {"max": 2, "remaining": 2}},
    "Druid":              {"1": {"max": 2, "remaining": 2}},
    "Bard":               {"1": {"max": 2, "remaining": 2}},
    "Paladin (Champion)": {},
    "Ranger":             {},
    "Fighter":            {},
    "Rogue":              {},
    "Barbarian":          {},
    "Monk":               {},
    "Alchemist":          {},
}

# Focus points at level 1 by class
CLASS_FOCUS_POINTS = {
    "Wizard":             {"max": 0, "remaining": 0},
    "Sorcerer":           {"max": 1, "remaining": 1},
    "Cleric":             {"max": 1, "remaining": 1},
    "Druid":              {"max": 1, "remaining": 1},
    "Bard":               {"max": 1, "remaining": 1},
    "Paladin (Champion)": {"max": 1, "remaining": 1},
    "Ranger":             {"max": 0, "remaining": 0},
    "Fighter":            {"max": 0, "remaining": 0},
    "Rogue":              {"max": 0, "remaining": 0},
    "Barbarian":          {"max": 0, "remaining": 0},
    "Monk":               {"max": 1, "remaining": 1},
    "Alchemist":          {"max": 0, "remaining": 0},
}

# Golarion adventure settings
ADVENTURE_STARTERS = {
    "sandpoint": (
        "The sleepy coastal town of Sandpoint is celebrating its annual Swallowtail Festival "
        "when a horn blast cuts through the festivities — goblins are pouring in from the woods, "
        "singing their horrible little songs and setting fire to everything they can reach."
    ),
    "absalom": (
        "Absalom, the City at the Center of the World, never sleeps. You've just arrived at the "
        "Grand Bazaar when a frantic merchant grabs your sleeve — someone has stolen the Starstone "
        "Key from the Vault of the Concordance, and the city's arcane wards are already failing."
    ),
    "stolen_lands": (
        "The Stolen Lands stretch wild and unmapped before you, a vast frontier where no kingdom "
        "has held for long. Your charter grants you the right to explore and settle this territory, "
        "but something ancient stirs in the ruins to the north — and the locals are frightened."
    ),
    "osirion": (
        "The desert sun hammers down on the Osirian sands as your expedition reaches the entrance "
        "of a newly discovered tomb. The hieroglyphs above the door are a warning, your guide says, "
        "but the treasures inside once belonged to a Pharaoh whose secrets could reshape the world."
    ),
}
