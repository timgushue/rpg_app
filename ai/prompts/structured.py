"""
Structured-output prompts — Claude calls that return JSON for game state updates.
"""

STORY_ARC_PROMPT = """You are designing the full story arc for a child-friendly Pathfinder 2e campaign.

Create a focused adventure spine that the Game Master can use to guide every turn.
The story must stay age-appropriate, concrete, and easy to follow.
Return JSON only with this structure:
{{
  "title": "string",
  "premise": "string",
  "theme": "string",
  "hero_goal": "string",
  "main_threat": "string",
  "stakes": "string",
  "acts": [
    {{
      "id": "act-1",
      "title": "string",
      "summary": "string",
      "beats": [
        {{
          "id": "beat-1",
          "title": "string",
          "goal": "string",
          "required_progress": "string",
          "failure_risk": "string",
          "completion_signal": "string"
        }}
      ]
    }}
  ]
}}

Rules:
- Create exactly 3 acts.
- Create exactly 2 beats per act.
- Every beat must move the hero toward the main threat.
- Keep the plot direct and motivated, not meandering.
- The first beat must connect to the current setting immediately.
- The final beat must clearly resolve the main threat.

Hero:
{hero}

Current setting:
{setting}

If this is a replacement arc, continue from the current world and hero state instead of restarting.
Replacement reason:
{replacement_reason}

Previous arc summary:
{previous_arc}

Story variation request:
{variation_hint}
"""

TURN_RESOLUTION_PROMPT = """You are a Pathfinder 2e campaign state resolver.

You will be given the current campaign context, the player's action, and the exact dice result already rolled in Python.
Return JSON only with this structure:
{{
  "scene_title": "short title for this turn",
  "narration_cue": "short prose summary of what physically happened",
  "advancement_type": "information",
  "state_delta": {{
    "hp_change": 0,
    "xp_change": 0,
    "gold_change": 0,
    "inventory_add": [{{"name": "string", "quantity": 1}}],
    "inventory_remove": [{{"name": "string", "quantity": 1}}],
    "spell_slots_used": {{"1": 1}},
    "focus_points_used": 0,
    "minutes_elapsed": 0,
    "full_rest": false,
    "short_rest": false
  }},
  "world_updates": {{
    "npcs": ["string"],
    "locations": ["string"],
    "quests": ["string"],
    "lore": "string"
  }},
  "arc_progress": {{
    "beat_status": "stalled",
    "arc_status": "active",
    "next_story_focus": "string",
    "replacement_reason": "string"
  }},
  "continuity_update": {{
    "current_situation": "short hidden GM summary of the new immediate situation",
    "current_location": "short location label",
    "resolved_threads_add": ["string"],
    "resolved_threads_remove": ["string"],
    "active_constraints_add": ["string"],
    "active_constraints_remove": ["string"],
    "recent_complication": "short generic label for this turn's main complication",
    "last_meaningful_change": "short statement of what changed this turn"
  }}
}}

Allowed beat_status values:
- "stalled": the hero acted but did not meaningfully advance the beat
- "progress": the hero made progress but did not complete the beat
- "completed": the hero completed the current beat
- "failed": the beat is no longer possible in the current arc

Allowed arc_status values:
- "active"
- "broken"
- "completed"

Allowed advancement_type values:
- "location": the hero moved to a meaningfully different place
- "information": the hero learned or preserved useful information
- "resource": HP, inventory, gold, spell slots, focus, or time changed meaningfully
- "relationship": an NPC relationship, attitude, or social position changed
- "danger": the threat, pressure, alarm, or deadline changed
- "objective": the current beat or quest objective advanced
- "none": the action was trivial or purely repetitive

Rules:
- scene_title must be 2-6 words, player-safe, and should not reveal hidden plot details.
- Respect hidden continuity guardrails in the context. Do not undo resolved threads unless the player clearly creates a new cause.
- Do not reuse a recent complication while it is on cooldown. If danger remains, change its form instead of repeating the same problem.
- Failed rolls should fail forward: add cost, delay, partial information, changed danger, or a harder choice, but do not reset the scene to the same state.
- Every non-trivial turn should create at least one meaningful change: location, information, resource, relationship, danger, or objective.
- Only spend resources that are explicitly used.
- Only add XP or gold when the action earns it.
- XP must be an increment, never a new total.
- Use these XP bands:
  - 0 XP: trivial action, flavor action, repeated farming, or no real progress
  - 10 XP: useful clue, small exploration gain, or minor progress toward the current beat
  - 20 XP: meaningful obstacle progress, a solid success, or noticeable story advancement
  - 30-40 XP: major obstacle overcome, important discovery, or strong progress on the current beat
  - 50-100 XP: completing a beat, major quest milestone, or a decisive victory
- Prefer the smallest XP award that fits what actually happened.
- Use negative hp_change only when the hero clearly suffers harm.
- Use positive hp_change only for explicit healing or full-rest recovery.
- Prefer small, conservative deltas over dramatic guesses.
- If the hero is reduced to 0 HP or the story objective becomes impossible, set arc_status to "broken".
- Use quest/world updates only for meaningful changes.
- Fill continuity_update with hidden GM facts only. Do not put campaign-specific examples into these rules; derive specifics only from the campaign context.

Campaign context:
{context}

Player action:
{player_action}

Dice result:
{roll_result}
"""

TURN_RESULT_PROMPT = """You are resolving and narrating one Pathfinder 2e campaign turn for a child aged 8 to 12.

You will be given the current campaign context, the player's action, and the exact dice result already rolled in Python.
Return JSON only with this structure:
{{
  "story_beat": "plain prose narration for the player",
  "resolution_data": {{
    "scene_title": "short title for this turn",
    "narration_cue": "short prose summary of what physically happened",
    "advancement_type": "information",
    "state_delta": {{
      "hp_change": 0,
      "xp_change": 0,
      "gold_change": 0,
      "inventory_add": [{{"name": "string", "quantity": 1}}],
      "inventory_remove": [{{"name": "string", "quantity": 1}}],
      "spell_slots_used": {{"1": 1}},
      "focus_points_used": 0,
      "minutes_elapsed": 0,
      "full_rest": false,
      "short_rest": false
    }},
    "world_updates": {{
      "npcs": ["string"],
      "locations": ["string"],
      "quests": ["string"],
      "lore": "string"
    }},
    "arc_progress": {{
      "beat_status": "stalled",
      "arc_status": "active",
      "next_story_focus": "string",
      "replacement_reason": "string"
    }},
    "continuity_update": {{
      "current_situation": "short hidden GM summary of the new immediate situation",
      "current_location": "short location label",
      "resolved_threads_add": ["string"],
      "resolved_threads_remove": ["string"],
      "active_constraints_add": ["string"],
      "active_constraints_remove": ["string"],
      "recent_complication": "short generic label for this turn's main complication",
      "last_meaningful_change": "short statement of what changed this turn"
    }}
  }}
}}

Allowed beat_status values:
- "stalled": the hero acted but did not meaningfully advance the beat
- "progress": the hero made progress but did not complete the beat
- "completed": the hero completed the current beat
- "failed": the beat is no longer possible in the current arc

Allowed arc_status values:
- "active"
- "broken"
- "completed"

Allowed advancement_type values:
- "location": the hero moved to a meaningfully different place
- "information": the hero learned or preserved useful information
- "resource": HP, inventory, gold, spell slots, focus, or time changed meaningfully
- "relationship": an NPC relationship, attitude, or social position changed
- "danger": the threat, pressure, alarm, or deadline changed
- "objective": the current beat or quest objective advanced
- "none": the action was trivial or purely repetitive

State update rules:
- scene_title must be 2-6 words, player-safe, and should not reveal hidden plot details.
- Respect hidden continuity guardrails in the context. Do not undo resolved threads unless the player clearly creates a new cause.
- Do not reuse a recent complication while it is on cooldown. If danger remains, change its form instead of repeating the same problem.
- Failed rolls should fail forward: add cost, delay, partial information, changed danger, or a harder choice, but do not reset the scene to the same state.
- Every non-trivial turn should create at least one meaningful change: location, information, resource, relationship, danger, or objective.
- Only spend resources that are explicitly used.
- Only add XP or gold when the action earns it.
- XP must be an increment, never a new total.
- Use these XP bands:
  - 0 XP: trivial action, flavor action, repeated farming, or no real progress
  - 10 XP: useful clue, small exploration gain, or minor progress toward the current beat
  - 20 XP: meaningful obstacle progress, a solid success, or noticeable story advancement
  - 30-40 XP: major obstacle overcome, important discovery, or strong progress on the current beat
  - 50-100 XP: completing a beat, major quest milestone, or a decisive victory
- Prefer the smallest XP award that fits what actually happened.
- Use negative hp_change only when the hero clearly suffers harm.
- Use positive hp_change only for explicit healing or full-rest recovery.
- Prefer small, conservative deltas over dramatic guesses.
- If the hero is reduced to 0 HP or the story objective becomes impossible, set arc_status to "broken".
- Use quest/world updates only for meaningful changes.
- Fill continuity_update with hidden GM facts only. Do not put campaign-specific examples into these rules; derive specifics only from the campaign context.

Narration rules:
- Narrate the exact outcome implied by the dice result.
- Respect hidden continuity guardrails; do not expose JSON, cooldowns, or planning terms to the player.
- Critical Success: something goes spectacularly right.
- Success: the action works as intended.
- Failure: the action fails or works with an unwanted complication.
- Critical Failure: something goes wrong and may worsen the situation.
- For trivial actions with DC 0, ignore the roll and narrate the obvious outcome.
- Keep content safe for children: exciting, tense, and adventurous, but not gruesome.
- Never narrate what the hero thinks, feels, decides, or intends.
- You may describe what the hero sees, hears, smells, and what physically happens.
- End with the world in a state that invites the player's next action.
- Do not end with a direct question like "What do you do?"
- Use plain prose only inside story_beat: no markdown, headers, bullets, or formatting.
- Use ellipses (...) and em-dashes (—) naturally for text-to-speech rhythm.
- Always complete the final sentence.
- Target length:
  - Simple action or single attack: 1-2 sentences
  - Dialogue or NPC interaction: 2-3 sentences
  - Exploration or meaningful scene movement: 3-4 sentences
  - Major story moment: 4-6 sentences

Campaign context:
{context}

Player action:
{player_action}

Dice result:
{roll_result}
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
