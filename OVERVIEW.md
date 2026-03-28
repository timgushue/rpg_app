# Pathfinder Quest — Developer Overview

This document describes the project structure, data models, and key flows for developers and LLMs working on this codebase.

---

## What it does

A Pathfinder 2nd Edition storytelling app for children (ages 8–12). The player types actions; Claude acts as the Game Master and narrates outcomes; OpenAI TTS reads the narration aloud. Campaigns persist across sessions in SQLite. All Pathfinder 2e rules (skill checks, spell slots, inventory, XP, levelling) are enforced automatically.

**Tech stack:** Streamlit · Anthropic Claude (claude-sonnet-4-5) · OpenAI TTS (gpt-4o-mini-tts, fable voice) · SQLite · Poetry

---

## Package layout

```
rpg_app/
├── app.py                  Streamlit entry point — UI only, no game logic
│
├── game/                   Pathfinder 2e rules and data (no external dependencies)
│   ├── game_data.py        All PF2e tables: classes, ancestries, gear, spells, XP, gold, HP
│   ├── character.py        build_ability_scores(ancestry, class) → dict
│   ├── dice.py             Skill detection, d20 rolling, degree of success, modifiers
│   └── game_time.py        Golarion calendar: advance_time(), format_time(), initial_time()
│
├── ai/                     External AI API integrations
│   ├── engine.py           Engine class: story generation, DC assessment, resource tracking
│   ├── voice.py            Voice class: OpenAI TTS with VOICE_INSTRUCTIONS personality
│   └── prompts/
│       ├── narrator.py     NARRATOR_SYSTEM_PROMPT, OPENING_SCENE_PROMPT, RECAP_SCENE_PROMPT
│       ├── structured.py   SUMMARY_PROMPT, WORLD_UPDATE_PROMPT, RESOURCE_UPDATE_PROMPT
│       ├── context.py      build_context() — assembles full game state string for Claude
│       └── __init__.py     Re-exports everything; callers use `from ai.prompts import X`
│
├── storage/
│   └── database.py         Database class: SQLite CRUD + schema migrations
│
└── tests/
    ├── test_dice.py
    ├── test_game_time.py
    ├── test_character.py
    └── test_game_data.py
```

---

## Key data models

### `hero_sheet` (stored as JSON in `campaigns.hero_sheet`)

```python
{
    "ancestry": "Elf",
    "class": "Wizard",
    "level": 1,
    "xp": 0,                        # resets to 0 at each level-up
    "gold": 10,
    "hp": 14,
    "max_hp": 14,
    "ac": 14,
    "ability_scores": {
        "strength": 10, "dexterity": 16, "constitution": 12,
        "intelligence": 20, "wisdom": 10, "charisma": 10
    },
    "spell_slots": {"1": {"max": 2, "remaining": 2}},
    "focus_points": {"max": 0, "remaining": 0},
    "inventory": [{"name": "staff", "quantity": 1}, ...],
    "traits": ["curious", "studious"],
    "skills": [], "feats": [], "spells": []
}
```

Ability scores are computed at campaign creation by `game/character.py`:
- Key ability (e.g. INT for Wizard) → 18
- Two secondary abilities → 14
- Ancestry boosts/flaws (+2/−2) applied on top, clamped to [4, 20]

### `world_state` (stored as JSON in `campaigns.world_state`)

```python
{
    "setting": "The sleepy coastal town of Sandpoint...",  # adventure hook text
    "npcs": ["Ameiko Kaijitsu", "Sheriff Hemlock"],
    "locations": ["Rusty Dragon Inn", "Sandpoint Cathedral"],
    "quests": ["Drive the goblins out of Sandpoint"],
    "lore": "",
    "time": {
        "hour": 14, "minute": 30, "time_of_day": "afternoon",
        "day": 3, "day_of_week": 6, "season": "Spring"
    }
}
```

---

## Story beat flow

One player action triggers this sequence in `ai/engine.py`:

```
1. _get_action_dc()        Fast Claude call (max_tokens=10) → int DC for the action
2. dice.roll_action()      d20 + skill modifier vs DC → {skill, roll, modifier, total, dc, degree}
3. build_context()         Assembles hero sheet + world state + summaries + session messages
4. Claude narration call   NARRATOR_SYSTEM_PROMPT + context + roll result → story beat
5. _try_update_world_state()  Claude extracts new NPCs/locations/quests → merges into world_state
6. _try_update_resources()    Claude extracts resource changes → updates hero_sheet + advances time
```

Steps 5 and 6 are best-effort (exceptions silently swallowed). All DB writes happen in steps 4–6.

---

## Dice and modifiers

`game/dice.py` handles all Pathfinder 2e roll mechanics:

- **Skill detection:** `detect_skill(action_text)` scans for keywords (e.g. "climb" → Athletics)
- **Modifier:** ability score modifier + proficiency bonus (+2) if the class is trained in the skill
- **Degree of success** (PF2e rules):
  - Natural 20 or total ≥ DC+10 → Critical Success
  - Natural 1 or total ≤ DC−10 → Critical Failure
  - total ≥ DC → Success
  - total < DC → Failure
- **DC=0** means no roll needed (trivial actions like walking)

---

## Prompts architecture

`ai/prompts/` contains three types of Claude calls:

| File | Purpose | Returns |
|---|---|---|
| `narrator.py` | GM voice and rules — system prompts for narration | Plain text (story) |
| `structured.py` | JSON extraction — resource changes, world updates, session summary | JSON or plain text |
| `context.py` | Assembles game state into a single prompt string | String passed to narration call |

All three are re-exported from `ai/prompts/__init__.py` so callers use `from ai.prompts import X`.

---

## Database schema

```sql
campaigns  (id, title, genre, hero_name, hero_sheet JSON, world_state JSON, created_at, updated_at)
sessions   (id, campaign_id, session_number, summary, created_at)
messages   (id, session_id, role, content, audio_path, timestamp)
```

`database.py` runs migrations on every startup:
- Adds `audio_path` column to `messages` if missing
- Converts legacy string inventories to `{name, quantity}` dicts
- Upgrades all-default (10/10/10/10/10/10) ability scores to ancestry+class values

Audio files are stored at `audio/message_{id}.mp3` and the path is saved in `messages.audio_path` for replay.

---

## Voice

`ai/voice.py` wraps OpenAI TTS:
- Model: `gpt-4o-mini-tts` · Voice: `fable`
- Narration personality is set via the `instructions` parameter (`VOICE_INSTRUCTIONS` constant)
- Markdown is stripped before synthesis (`_strip_markdown()`)
- `speak(text)` → `bytes | None`
- `speak_to_file(text)` → temp file path (used for opening scenes)
- `speak_to_persistent_file(text, message_id, audio_dir)` → named file for replay
- Returns `None` gracefully on any error — app falls back to text-only

---

## Environment variables

```
ANTHROPIC_API_KEY   Required. Powers the Game Master (Claude).
OPENAI_API_KEY      Optional. Powers narrator voice (OpenAI TTS). App runs text-only without it.
```

---

## Running tests

```bash
poetry run pytest tests/ -v
```

Tests cover `game/` only — pure logic with no API calls or mocking of external services:
- `test_dice.py` — skill detection, modifiers, degree of success, display formatting
- `test_game_time.py` — time advancement, day/season rollover, formatting
- `test_character.py` — ability score generation for all ancestry/class combinations
- `test_game_data.py` — data completeness: every class and ancestry has a full table entry

---

## Development notes

- `app.py` imports from all three packages (`game`, `ai`, `storage`) — it is the only file that does so
- `ai/engine.py` is the only file that calls both Claude and the database; keep it that way
- `game/` has no imports from `ai/` or `storage/` — keep it dependency-free
- `storage/database.py` only imports from `game/character.py` (for migrations)
- All Claude calls use `json.loads()` on structured responses — if Claude returns malformed JSON, the exception is caught and the update is skipped
- XP threshold is 1000 per level (PF2e standard); level-up is a `while` loop to handle multiple level-ups in one session
- Time advances by `minutes_elapsed` extracted from each story beat by `RESOURCE_UPDATE_PROMPT`; a full rest (480 min) restores all daily resources
