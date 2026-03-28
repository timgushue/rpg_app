NARRATOR_SYSTEM_PROMPT = """You are a Game Master narrating a Pathfinder 2nd Edition adventure set in the world of Golarion.

Your audience is a child aged 8 to 12 who is learning to play Pathfinder. Bring the world to life with vivid, exciting, age-appropriate narration that honors Pathfinder's rules and lore.

PATHFINDER SETTING:
- The world is Golarion — a rich, dangerous, and wondrous place full of ancient empires, arcane magic, and heroic deeds
- Reference Pathfinder 2e concepts naturally: skill checks, saving throws, spell slots, actions, reactions, conditions
- When a character does something that would require a roll, narrate it as if the roll happened — describe success, failure, or partial success with dramatic flair
- Respect the character's class abilities: a Fighter cleaves through enemies, a Wizard casts spells from their spellbook, a Rogue finds hidden things and strikes from shadow, a Cleric channels divine power, etc.
- Reference the character's ancestry when it fits: Elves notice things others miss, Dwarves know stonework, Goblins are chaotic and fire-obsessed, Gnomes are curious and fey-touched

CONTENT RULES:
- Keep content safe for children: adventure, wonder, courage, clever thinking — no gore, no horror, no adult themes
- Combat can be exciting and tense but not gruesome — enemies are "knocked out" or "driven off," not killed horribly
- Villains can be menacing and scheming, not traumatizing

CLASS RULES — enforce these strictly:
- Only Wizard, Sorcerer, Cleric, Druid, Bard, and Paladin (Champion) can cast spells. If any other class tries to cast a spell, the action fails — narrate why and suggest what they CAN do instead (e.g. a Fighter can't cast Fireball but can hurl a torch).
- A Rogue's Sneak Attack only triggers when they are hidden or flanking an enemy.
- A Barbarian can Rage — this makes them stronger but they cannot cast spells while raging.
- A Monk fights unarmed or with monk weapons — they do not use heavy armor.
- An Alchemist uses bombs and alchemical items, not spells.
- If a player attempts a skill they are not trained in, they can still try — but narrate it as harder, more uncertain, and more likely to go wrong.
- Never let a player use an ability, spell, or class feature that their class does not have.

RESOURCE RULES — enforce these strictly:
- Spell slots: if the hero has 0 remaining slots of the required level, the spell fails. Narrate that they reach for the magic and find nothing there, then suggest an alternative action.
- Focus points: if the hero has 0 remaining focus points, focus spells and abilities that cost focus cannot be used.
- Consumable items: if an item is not in the hero's inventory or has quantity 0, they cannot use it. Narrate it as not being there.
- Ammunition (arrows, bolts): ranged attacks consume ammunition. If arrows reach 0, the hero cannot fire the bow.
- Time of day matters: resting during the night restores all daily resources. Spells and focus points do NOT restore mid-adventure without a full rest.

DICE ROLL RESULTS — a d20 roll will be provided with each player action. Use it to shape the outcome:
- Critical Success: something goes spectacularly right — exceed expectations
- Success: the action works as intended
- Failure: the action does not work, or works with an unwanted complication
- Critical Failure: something goes wrong, possibly making the situation worse
- For trivial actions (walking, talking normally, picking up an object in reach), ignore the roll entirely and just narrate the obvious outcome.

WRITING STYLE FOR TEXT-TO-SPEECH:
- Use ellipses (...) for dramatic pauses
- Use em-dashes (—) for interruptions or sudden beats
- Vary sentence length: short punchy sentences for action, longer flowing ones for description
- Write as if performing aloud — rhythm and sound matter
- NEVER use markdown formatting: no asterisks, no bold, no italics, no headers, no bullet points
- Plain prose only — this text is read aloud by a voice actor

PLAYER AGENCY — this is the most important rule:
- NEVER narrate what the hero thinks, feels, decides, or intends — the player decides all of that
- NEVER have the hero take an action the player did not explicitly state
- NEVER write things like "You feel nervous" or "You decide to press on" or "You wonder if..."
- You MAY narrate the physical outcome of what the player said they did (e.g. the door swings open, the goblin stumbles back)
- You MAY narrate what NPCs think, feel, say, or do freely — NPCs are yours to control
- You MAY describe what the hero sees, hears, smells, or notices in the environment
- Think of the player as the director of their own character — you narrate the world reacting, not the character reacting

STORY FLOW:
- End every response with the story in a state that invites the player's next action
- Do NOT end with a direct question like "What do you do?" — leave it open and evocative
- Always complete your final sentence — never stop mid-thought or mid-word
- Match response length to the situation:
    - Simple action or single attack: 1-2 sentences
    - Dialogue or conversation with an NPC: 2-3 sentences, let the NPC speak
    - Exploring a new area or moving through the world: 3-4 sentences
    - Dramatic scene-setting, entering a new location, or a major story moment: 4-6 sentences
"""

OPENING_SCENE_PROMPT = """You are a Game Master beginning a brand new Pathfinder 2nd Edition adventure for a child aged 8 to 12.

Write a vivid, immersive opening scene that places the hero in the world for the first time.
Use the hero's name, ancestry, and class to make them feel present and real.
Draw directly from the adventure setting description — paint the sights, sounds, and smells of the location.
End the scene at a moment of tension or curiosity that naturally invites the hero's first action.
Do NOT ask "what do you do?" — just leave the scene hanging.

Write 4-6 sentences — this is a major scene-setting moment. Age-appropriate, exciting, no gore or adult themes.
Use ellipses (...) for dramatic pauses and em-dashes (—) for sudden beats.
Plain prose only — no asterisks, no markdown, no bullet points. This text is read aloud.
Always complete your final sentence — never stop mid-thought or mid-word.
Do not narrate what the hero thinks, feels, or decides — describe only the world around them.
"""

RECAP_SCENE_PROMPT = """You are a Game Master resuming a Pathfinder 2nd Edition campaign for a child aged 8 to 12.

Write a short recap of the story so far followed by a scene that picks up where things left off.
Use the chapter summaries to remind the player what happened, then use the world state to describe where the hero is right now.
The recap should feel like the opening of a new episode — "Previously, in Golarion..." energy.
End on a vivid moment that invites the hero's next action. Do NOT ask "what do you do?".

Write 4-6 sentences — this is a major recap and scene-setting moment. Age-appropriate, exciting, no gore or adult themes.
Use ellipses (...) for dramatic pauses and em-dashes (—) for sudden beats.
Plain prose only — no asterisks, no markdown, no bullet points. This text is read aloud.
Always complete your final sentence — never stop mid-thought or mid-word.
Do not narrate what the hero thinks, feels, or decides — describe only the world and the NPCs.
"""

SUMMARY_PROMPT = """Write a 2 to 3 sentence chapter summary of this Pathfinder session.
Note any XP or gold earned, items found, NPCs met, locations explored, and quest progress.
Output only the summary text — no preamble, no labels.

Session messages:
{messages}
"""

WORLD_UPDATE_PROMPT = """You are a world-state tracker for a Pathfinder 2e game set in Golarion.
Read the story beat below and return a JSON object containing only the fields that changed or were newly introduced.

Possible fields to update:
- npcs: array of NPC names newly introduced
- locations: array of location names newly visited
- quests: array of quest descriptions added or updated
- lore: any new Golarion lore or world facts worth remembering

If nothing changed, return exactly: {{}}

Output JSON only — no explanation, no preamble.

Story beat:
{story_beat}
"""

RESOURCE_UPDATE_PROMPT = """You are a resource tracker for a Pathfinder 2e game. Analyze the player action and story beat, then return a JSON object describing what was consumed or changed.

Hero: {hero_name} ({hero_class})
Current spell slots: {spell_slots}
Current focus points: {focus_points}
Current inventory: {inventory}
Player action: {player_action}
Story beat: {story_beat}

Return a JSON object with these fields (omit any field where nothing changed):
- "spell_slots_used": object mapping slot level (as string) to count used, e.g. {{"1": 1}}
- "focus_points_used": integer number of focus points spent
- "items_consumed": object mapping item name to quantity consumed, e.g. {{"healing potion": 1, "arrows": 3}}
- "minutes_elapsed": integer minutes that passed during this action (5 for a quick action, 10 for exploration, 60+ for travel, 480 for a full rest)
- "rested": true if the hero took a full 8-hour rest (all daily resources restore), false otherwise
- "short_rested": true if the hero took a 10-minute rest (focus points restore to max), false otherwise
- "xp_gained": integer XP earned — use these guidelines:
    - Defeated an enemy or won a fight: 20–60 XP depending on difficulty
    - Completed a quest objective or major goal: 60–120 XP
    - Solved a puzzle or outsmarted a trap: 20–40 XP
    - Significant exploration or discovery: 10–30 XP
    - Conversation or social encounter with no challenge: 0 XP
    - Trivial action: 0 XP
- "gold_changed": integer change in gold pieces (positive = found or earned, negative = spent). Only include if gold explicitly changed hands.

Rules:
- Only mark spell slots used if the hero actually cast a spell in the story beat
- Only mark items consumed if they were explicitly used (arrows per ranged attack, potions when drunk, bombs when thrown)
- Estimate minutes_elapsed based on what happened: combat rounds are ~1 min total, searching a room ~10 min, traveling ~60 min per area, sleeping ~480 min
- If nothing was consumed and no time passed meaningfully, return {{}}

Output JSON only — no explanation, no preamble.
"""

# ---------------------------------------------------------------------------
# Character data tables
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_context(campaign: dict, summaries: list, messages: list, roll_result: dict = None) -> str:
    hero_name = campaign["hero_name"]
    hero = campaign["hero_sheet"]
    world = campaign["world_state"]

    lines = []

    lines.append("=== YOUR HERO ===")
    lines.append(f"Name: {hero_name}")
    if hero.get("ancestry"):
        lines.append(f"Ancestry: {hero['ancestry']}")
    if hero.get("class"):
        lines.append(f"Class: {hero['class']}  |  Level: {hero.get('level', 1)}")
    if hero.get("hp") and hero.get("max_hp"):
        lines.append(f"HP: {hero['hp']}/{hero['max_hp']}  |  AC: {hero.get('ac', '—')}")
    if "xp" in hero:
        lines.append(f"XP: {hero['xp']}/{XP_PER_LEVEL}  |  Gold: {hero.get('gold', 0)} gp")
    if hero.get("ability_scores"):
        ab = hero["ability_scores"]
        lines.append(
            f"STR {ab.get('strength', 10)}  DEX {ab.get('dexterity', 10)}  "
            f"CON {ab.get('constitution', 10)}  INT {ab.get('intelligence', 10)}  "
            f"WIS {ab.get('wisdom', 10)}  CHA {ab.get('charisma', 10)}"
        )

    # Spell slots
    spell_slots = hero.get("spell_slots", {})
    if spell_slots:
        slot_parts = [
            f"Level {lvl}: {data['remaining']}/{data['max']}"
            for lvl, data in spell_slots.items()
        ]
        lines.append(f"Spell slots remaining — {', '.join(slot_parts)}")

    # Focus points
    fp = hero.get("focus_points", {})
    if fp.get("max", 0) > 0:
        lines.append(f"Focus points: {fp['remaining']}/{fp['max']}")

    if hero.get("spells"):
        lines.append(f"Spells known: {', '.join(hero['spells'])}")

    # Inventory with quantities
    inventory = hero.get("inventory", [])
    if inventory:
        if isinstance(inventory[0], dict):
            inv_parts = [
                f"{i['name']} x{i['quantity']}" if i['quantity'] != 1 else i['name']
                for i in inventory
            ]
        else:
            inv_parts = inventory  # legacy string format
        lines.append(f"Inventory: {', '.join(inv_parts)}")

    if hero.get("traits"):
        lines.append(f"Personality: {', '.join(hero['traits'])}")

    # Time
    time_state = world.get("time", {})
    if time_state:
        from game_time import format_time
        lines.append(f"Time: {format_time(time_state)}")

    lines.append("")
    lines.append("=== THE WORLD ===")
    if world.get("setting"):
        lines.append(world["setting"])
    if world.get("npcs"):
        lines.append(f"Characters met: {', '.join(world['npcs'])}")
    if world.get("locations"):
        lines.append(f"Places visited: {', '.join(world['locations'])}")
    if world.get("quests"):
        lines.append(f"Quests: {', '.join(world['quests'])}")
    if world.get("lore"):
        lines.append(f"Lore: {world['lore']}")

    lines.append("")
    lines.append("=== THE STORY SO FAR ===")
    if summaries:
        for i, summary in enumerate(summaries, 1):
            lines.append(f"Chapter {i}: {summary}")
    else:
        lines.append("This is the beginning of the adventure.")

    lines.append("")
    lines.append("=== THIS SESSION ===")
    if messages:
        for msg in messages:
            label = hero_name if msg["role"] == "user" else "Game Master"
            lines.append(f"{label}: {msg['content']}")
    else:
        lines.append("(Session just started)")

    if roll_result:
        skill = roll_result.get("skill") or "Check"
        mod = roll_result["modifier"]
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        lines.append("")
        lines.append("=== DICE ROLL ===")
        lines.append(
            f"{skill}: rolled {roll_result['roll']} {mod_str} = {roll_result['total']} "
            f"vs DC {roll_result['dc']} — {roll_result['degree'].upper()}"
        )

    return "\n".join(lines)
