"""
Structured-output prompts — Claude calls that return JSON for game state updates.
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
