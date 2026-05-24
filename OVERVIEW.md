# Pathfinder Quest — Developer Overview

This document describes the project structure, data models, and key flows for developers and LLMs working on this codebase.

---

## What it does

A Pathfinder 2nd Edition storytelling app for children. The player types free-form actions; Claude acts as the Game Master; Python performs dice rolls and applies structured game-state changes; OpenAI TTS can generate narration audio. Campaigns persist across sessions in SQLite. The app tracks hero stats, inventory, gold, XP, spell/focus resources, rolls, story beats, session summaries, and a hidden story arc used to keep the narrative focused.

**Tech stack:** NiceGUI · Anthropic Claude · OpenAI TTS · SQLite · Poetry

---

## Package layout

```
rpg_app/
├── nicegui_app.py          NiceGUI entry point
├── app_service.py          Framework-neutral UI workflow service
├── ui_kit/                 Inkwell theme helpers and CSS
│
├── game/                   Pathfinder 2e rules and data (no external dependencies)
│   ├── game_data.py        All PF2e tables: classes, ancestries, gear, spells, XP, gold, HP
│   ├── character.py        build_ability_scores(ancestry, class) → dict
│   ├── dice.py             Skill detection, d20 rolling, degree of success, modifiers
│   ├── game_time.py        Golarion calendar: advance_time(), format_time(), initial_time()
│   └── state_update.py     Story arc normalization and structured state mutation
│
├── ai/                     External AI API integrations
│   ├── engine.py           Engine class: story arcs, DC/skill assessment, rolls, narration
│   ├── voice.py            Voice class: OpenAI TTS with VOICE_INSTRUCTIONS personality
│   └── prompts/
│       ├── narrator.py     NARRATOR_SYSTEM_PROMPT, OPENING_SCENE_PROMPT, RECAP_SCENE_PROMPT
│       ├── structured.py   STORY_ARC_PROMPT, TURN_RESOLUTION_PROMPT, SUMMARY_PROMPT
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
    ├── test_game_data.py
    ├── test_state_update.py
    ├── test_database_rolls.py
    ├── test_app_service.py
    ├── test_prompt_context.py
    ├── test_prompt_templates.py
    └── test_engine_action_classification.py
```

---

## UI routes and screens

- `/` is the main NiceGUI app. It renders the campaign shelf, character creation, and active scene depending on client state.
- `/journal` shows saved chapters and prior messages for a selected campaign.
- `/client-error` receives browser-side error reports from the NiceGUI page.
- Campaign cards support resume, journal, and confirmed delete. Delete removes the campaign, sessions, messages, roll/debug data, and generated audio.
- Character creation previews ancestry/class-derived ability scores. The Attributes & Rolls card can be expanded in place during play to explain modifiers and buffs.

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

### `story_state` (stored as JSON in `campaigns.story_state`)

```python
{
    "arc": {
        "title": "Hidden GM-only campaign arc",
        "premise": "...",
        "acts": [...],
        "major_beats": [...]
    },
    "current_objective": "Short player-safe current lead",
    "recent_plot_points": ["What the player has already learned or changed"],
    "completed_beats": [],
    "active_threads": [],
    "risk_flags": [],
    "continuity": {
        "last_threat": "",
        "loop_count": 0,
        "scene_pressure": ""
    }
}
```

The full story arc is GM-only. The UI and player-facing prompt context expose only safe summaries such as current objective, recent plot points, and visible leads. If a legacy campaign is missing `story_state`, the engine creates a full arc the next time the campaign is loaded for play.

---

## Campaign startup flow

New campaigns are created in two phases:

1. `AppService.create_new_adventure_shell()` creates the campaign/session immediately, with the selected hero and setting persisted in SQLite.
2. NiceGUI transitions to the scene page right away, so inventory, stats, history, and loading state are visible instead of blocking on a blank page.
3. `AppService.generate_initial_scene()` builds or saves the story arc, asks Claude for the opening narration, saves the assistant message, and optionally generates opening audio.

The “Fresh Story Arc” setting is a real campaign option. It uses a broad Golarion prompt and explicitly asks Claude not to reuse canned Sandpoint or Swallowtail Festival openings.

---

## Story beat flow

One player action triggers this sequence in `ai/engine.py`:

```
1. ensure_campaign_story_state()    Creates/normalizes the hidden story arc if needed
2. _get_action_dc()                 Cheap Claude classifier → integer DC, 0 means no roll
3. _classify_action_skill()         Cheap Claude classifier → PF2e skill name
4. _roll_action()                   Python d20 roll + hero modifier + PF2e degree of success
5. build_context()                  Hero, inventory, resources, world, history, safe story state
6. _resolve_turn()                  Claude JSON: state deltas, XP, inventory, gold, arc progress
7. apply_turn_resolution()          Python validates/applies HP, XP, inventory, gold, time, flags
8. _refresh_story_arc()             Creates a new arc if the resolver says the current arc broke
9. _narrate_turn()                  Claude writes the player-facing story beat using final state
10. save_message_pair()             Saves user + assistant text, roll_data, resolution_data, deltas
```

The app never lets Claude directly mutate the database. Claude proposes structured deltas; Python validates, clamps, and applies them in `game/state_update.py`. Roll details, resolver output, applied deltas, scene titles, and narration are all persisted for debugging.

---

## Dice and modifiers

`game/dice.py` handles all Pathfinder 2e roll mechanics:

- **Skill selection:** the engine first asks the cheap Claude classifier for the PF2e skill; `detect_skill(action_text)` remains the keyword fallback.
- **Modifier:** ability score modifier + proficiency bonus (+2) if the class is trained in the skill
- **Degree of success** (PF2e rules):
  - Natural 20 or total ≥ DC+10 → Critical Success
  - Natural 1 or total ≤ DC−10 → Critical Failure
  - total ≥ DC → Success
  - total < DC → Failure
- **DC=0** means no roll needed (trivial actions like walking)

---

## Prompts architecture

`ai/prompts/` contains the prompt templates used by the engine:

| File | Purpose | Returns |
|---|---|---|
| `narrator.py` | GM voice, opening scene, recap scene, and player-facing narration rules | Plain text story |
| `structured.py` | Story arc generation, turn resolution, and session summaries | JSON for arc/resolution; text for summaries |
| `context.py` | Assembles hero state, visible story state, world state, summaries, and recent messages | String passed to Claude |

Current model usage:

- Main story/structured calls use `claude-sonnet-4-5`.
- DC and skill classification use `claude-3-5-haiku-latest`.
- `WORLD_UPDATE_PROMPT` and `RESOURCE_UPDATE_PROMPT` are still exported for compatibility, but the active turn path uses `TURN_RESOLUTION_PROMPT` plus `apply_turn_resolution()`.

All prompt constants are re-exported from `ai/prompts/__init__.py` so callers use `from ai.prompts import X`.

---

## Database schema

```sql
campaigns  (id, title, genre, hero_name, hero_sheet JSON, story_state JSON, world_state JSON, created_at, updated_at)
sessions   (id, campaign_id, session_number, summary, created_at)
messages   (id, session_id, role, content, roll_data JSON, resolution_data JSON, applied_delta JSON, scene_title, audio_path, timestamp)
```

`database.py` runs migrations on every startup:
- Adds `story_state` to `campaigns` if missing
- Adds `audio_path`, `roll_data`, `resolution_data`, `applied_delta`, and `scene_title` to `messages` if missing
- Converts legacy string inventories to `{name, quantity}` dicts
- Upgrades all-default (10/10/10/10/10/10) ability scores to ancestry+class values
- Seeds missing `gold`, `xp`, resources, and normalized story state fields

Audio files are stored at `audio/message_{id}.mp3` and the path is saved in `messages.audio_path` for replay. Normal turn audio is generated after text is saved so the page can update before TTS finishes.

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
poetry run pytest -q
```

Tests cover pure game logic plus database migrations, prompt context, app-service workflows, state resolution, and action classification fallbacks. External API calls are mocked or avoided.

---

## Development notes

- `nicegui_app.py` owns rendering and client state; `app_service.py` holds framework-neutral UI workflows.
- `ui_kit/` owns the Inkwell visual theme and CSS helpers.
- `ai/engine.py` is the orchestration boundary for Claude + database work; keep UI details out of it.
- `game/` has no imports from `ai/` or `storage/`; keep it dependency-free except for standard library.
- `storage/database.py` imports `game.character` and `game.state_update` only for migrations and normalization.
- Structured Claude responses must be treated as proposals. Validate and apply them through Python, especially inventory, XP, HP, gold, resources, time, and story-arc progress.
- XP threshold is 1000 per level. Level-up uses a `while` loop to handle multiple level-ups in one turn.
- Full rests restore daily resources. Other resource changes come from `TURN_RESOLUTION_PROMPT` and are applied by `apply_turn_resolution()`.
- The full story arc should not be rendered to the player. Show only current objective, visible leads, or short plot summaries.
