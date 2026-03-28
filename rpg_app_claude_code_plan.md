# RPG Storytelling App — Claude Code Build Plan

Paste this entire document into a Claude Code session to build the app.

---

## What we're building

A desktop RPG storytelling app for a child (age 8–12). The child types their actions,
Claude generates the next story beat, and ElevenLabs speaks it aloud in a narrator voice.
All story history is persisted in SQLite so campaigns continue across sessions with no
context loss — old sessions are summarized and injected into every Claude call.

Runs locally on Linux and Mac via `streamlit run app.py`.

---

## Project structure to create

```
rpg_app/
├── app.py           # Streamlit UI
├── engine.py        # Context assembly + Claude API calls
├── database.py      # SQLite setup and all DB operations
├── voice.py         # ElevenLabs TTS
├── prompts.py       # All system prompts and templates
├── pyproject.toml   # Poetry project config
├── poetry.lock      # Auto-generated, commit this
└── .env.example
```

---

## Dependencies

### Poetry setup

First verify Poetry is installed:
```bash
poetry --version
```

If not installed:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Initialise the project with Poetry and add all dependencies:
```bash
poetry init --name rpg-app --python "^3.11" --no-interaction
poetry add streamlit anthropic elevenlabs python-dotenv
```

This creates `pyproject.toml` and `poetry.lock`. All subsequent commands must run
inside the Poetry environment:
```bash
poetry run streamlit run app.py
poetry run python database.py
```

Or activate the shell once for the session:
```bash
poetry shell
# then run commands normally
streamlit run app.py
```

### pyproject.toml (reference — Poetry generates this, do not create manually)
```toml
[tool.poetry]
name = "rpg-app"
version = "0.1.0"
description = "RPG storytelling app for kids"
authors = []

[tool.poetry.dependencies]
python = "^3.11"
streamlit = ">=1.35.0"
anthropic = ">=0.25.0"
elevenlabs = ">=1.0.0"
python-dotenv = ">=1.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### .env.example
```
ANTHROPIC_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=
```

The user will copy `.env.example` to `.env` and fill in their API keys.
`ELEVENLABS_VOICE_ID` is intentionally left blank — the app handles voice
selection on first run (see voice.py and app.py below).

---

## database.py

Create a `Database` class using Python's built-in `sqlite3`. The DB file is
`stories.db` in the project root. Call `db.init()` on startup to create tables
if they don't exist.

### Schema

```sql
CREATE TABLE IF NOT EXISTS campaigns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    genre       TEXT NOT NULL,          -- 'fantasy' | 'sci-fi' | 'mystery'
    hero_name   TEXT NOT NULL,
    hero_sheet  TEXT NOT NULL,          -- JSON: {traits, inventory, abilities}
    world_state TEXT NOT NULL,          -- JSON: {locations, npcs, quests, lore}
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES campaigns(id),
    session_number  INTEGER NOT NULL,
    summary         TEXT,               -- Claude-generated chapter summary
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL,          -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Methods to implement

```python
class Database:
    def init(self) -> None
    def create_campaign(self, title, genre, hero_name, hero_sheet, world_state) -> int
    def get_campaign(self, campaign_id) -> dict
    def list_campaigns(self) -> list[dict]
    def update_world_state(self, campaign_id, world_state: dict) -> None
    def update_hero_sheet(self, campaign_id, hero_sheet: dict) -> None

    def create_session(self, campaign_id) -> int          # auto-increments session_number
    def get_session(self, session_id) -> dict
    def get_latest_session(self, campaign_id) -> dict     # None if no sessions yet
    def save_session_summary(self, session_id, summary: str) -> None
    def get_recent_summaries(self, campaign_id, n=5) -> list[str]  # last n summaries, oldest first

    def save_message(self, session_id, role, content) -> None
    def get_session_messages(self, session_id) -> list[dict]  # [{role, content}, ...]
```

---

## prompts.py

Define all prompts as module-level constants and functions. No logic here.

### NARRATOR_SYSTEM_PROMPT

A system prompt that:
- Establishes Claude as a warm, dramatic, age-appropriate narrator for a child aged 8–12
- Keeps content safe: no gore, no terror, no adult themes — adventure and wonder only
- Instructs Claude to write in a way that performs well with TTS:
  - Use ellipses (`...`) for dramatic pauses
  - Use em-dashes (`—`) for interruptions or sudden beats
  - Vary sentence length for rhythm
  - Short punchy sentences for action, longer flowing ones for description
- Each response should be 3–6 sentences — enough to advance the story, short enough to listen to comfortably
- End every response with the story in a state that invites the child's next action
- Do NOT end with a direct question like "What do you do?" — leave it open

### CONTEXT_TEMPLATE

A function `build_context(campaign, summaries, messages)` that returns a string:

```
=== YOUR HERO ===
Name: {hero_name}
{hero_sheet formatted as readable text}

=== THE WORLD ===
{world_state formatted as readable text}

=== THE STORY SO FAR ===
{each summary as "Chapter N: {summary}"}

=== THIS SESSION ===
(empty if first turn, otherwise the messages formatted as:)
{Hero}: {content}
{Narrator}: {content}
```

### SUMMARY_PROMPT

A prompt used at end-of-session to ask Claude to write a 2–3 sentence chapter summary
of what happened. Include instructions to note any changes to hero inventory, new NPCs
met, locations visited, and quest progress. Output just the summary text, no preamble.

### WORLD_UPDATE_PROMPT

A prompt used after each story beat to ask Claude to return a JSON object of any updates
to world_state (new NPCs, discovered locations, quest changes). If nothing changed,
return an empty JSON object `{}`. Output JSON only, no preamble.

### GENRE_STARTERS

A dict of genre → opening scene text used when creating a new campaign:
- `fantasy`: a village on the edge of an ancient forest, a mysterious rumor
- `sci-fi`: a space station with a flickering power grid, strange signals
- `mystery`: a foggy seaside town, a disappearance nobody will talk about

---

## engine.py

Create an `Engine` class that takes a `Database` instance and handles all LLM calls.

```python
class Engine:
    def __init__(self, db: Database)
```

### Methods

#### `generate_story_beat(campaign_id, session_id, user_input) -> str`

1. Load campaign from DB
2. Load last 5 session summaries from DB
3. Load all messages from current session
4. Build context string using `prompts.build_context()`
5. Append user_input as the latest user message
6. Call Claude API:
   - Model: `claude-sonnet-4-5`
   - System: `NARRATOR_SYSTEM_PROMPT`
   - Messages: one user message containing the full context string + the user's action
   - Max tokens: 300
7. Save user message to DB
8. Save assistant response to DB
9. Optionally (async or deferred): call `_try_update_world_state()` — see below
10. Return the assistant response text

#### `_try_update_world_state(campaign_id, story_beat) -> None`

Call Claude with `WORLD_UPDATE_PROMPT` + the story beat. If Claude returns valid JSON
with any keys, merge those into the existing world_state and save to DB. Swallow any
exceptions — this is best-effort enrichment.

#### `summarize_session(campaign_id, session_id) -> str`

1. Load all messages from session
2. Call Claude with `SUMMARY_PROMPT` + the formatted messages
3. Save summary to the session record in DB
4. Return the summary string

#### `start_campaign(title, genre, hero_name, traits) -> int`

1. Build initial `hero_sheet` dict from traits (list of 2–3 trait strings)
   Add `inventory: ["a worn backpack"]` and `abilities: []`
2. Build initial `world_state` from `GENRE_STARTERS[genre]` — just `{setting: ..., npcs: [], locations: [], quests: []}`
3. Call `db.create_campaign()` and return the campaign_id

---

## voice.py

Create a `Voice` class using the ElevenLabs Python SDK.

```python
class Voice:
    def __init__(self)   # reads ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID from env
```

### Voice ID resolution

On `__init__`, resolve the voice ID in this order:

1. If `ELEVENLABS_VOICE_ID` is set and non-empty in env, use it directly
2. Otherwise, call the ElevenLabs API to fetch all available voices and store
   them as `self.available_voices` — a list of `{name, voice_id, category}` dicts,
   sorted alphabetically by name
3. Set `self.voice_id = None` and `self.needs_voice_selection = True`

If `ELEVENLABS_API_KEY` is missing entirely, set `self.enabled = False` and
return early — all methods should be no-ops when `enabled` is False.

### Methods

#### `list_voices() -> list[dict]`

Return `self.available_voices` (already fetched in `__init__`).
Each dict: `{name: str, voice_id: str, category: str}`.
Filter to only include `default` and `professional` voices — these are
ElevenLabs' own high-quality voices, not random community uploads.

#### `set_voice(voice_id: str) -> None`

Set `self.voice_id = voice_id` and `self.needs_voice_selection = False`.
Write the chosen voice ID back to the `.env` file so it persists across
restarts. Use `python-dotenv`'s `set_key()` function for this.

#### `speak(text) -> bytes`

Call ElevenLabs TTS:
- Model: `eleven_turbo_v2` (low latency)
- Voice: `self.voice_id`
- Return raw audio bytes (mp3)
- Return `None` if `enabled` is False or `voice_id` is None

#### `speak_to_file(text) -> str | None`

Call `speak()` and write to a temp `.mp3` file using Python's `tempfile` module.
Return the file path, or `None` on any failure.
Swallow all exceptions so the app degrades gracefully to text-only.

---

## app.py

A Streamlit app. Keep the UI clean and child-friendly.

### Page config

```python
st.set_page_config(
    page_title="Story Quest",
    page_icon="⚔️",
    layout="wide"
)
```

### Session state keys

```python
st.session_state.campaign_id    # int or None
st.session_state.session_id     # int or None
st.session_state.messages       # list of {role, content} for display
st.session_state.story_started  # bool
```

### Layout

**Sidebar** — campaign management:
- "Start New Adventure" expander:
  - Text input: Adventure title
  - Selectbox: Genre (Fantasy / Sci-Fi / Mystery)
  - Text input: Hero name
  - Text input: "Describe your hero in a few words" (e.g. "brave, quick, loves animals")
  - Button: "Begin!"
  - On click: call `engine.start_campaign()`, create first session, generate opening
    story beat using `"The adventure begins."` as the first user input, store in
    session state
- "Continue Adventure" expander:
  - List existing campaigns from DB as selectbox
  - Button: "Continue"
  - On click: load campaign, create a new session (don't summarize yet), restore
    messages from latest session for display context

**Main area**:
- Title: "⚔️ Story Quest" in large text
- Story display: render `st.session_state.messages` as a chat — use
  `st.chat_message("user")` for hero actions and `st.chat_message("assistant")`
  for narrator responses
- If voice is available, auto-play the latest assistant audio using `st.audio()`
  with `autoplay=True` after each new story beat
- At the bottom: `st.chat_input("What do you do?")` — on submit:
  1. Add user message to display
  2. Show a spinner: "The narrator thinks..."
  3. Call `engine.generate_story_beat()`
  4. Add assistant message to display
  5. Call `voice.speak_to_file()` and play with `st.audio(..., autoplay=True)`
  6. Rerun

**End Session button** in sidebar (visible when a session is active):
- Call `engine.summarize_session()`
- Show a toast: "Chapter saved!"
- Clear session state so they can start or continue another campaign

### Voice picker (first-run experience)

At the top of the main area, before anything else renders, check
`voice.needs_voice_selection`. If True:

- Show a friendly heading: "Choose your narrator voice"
- Show a short explanation: "Pick a voice for your story narrator. You can change
  this any time by editing the .env file."
- Render a selectbox populated from `voice.list_voices()`, displayed as
  `"{name} ({category})"` with the voice_id as the underlying value
- Show a preview button: "Preview voice" — when clicked, generate a short sample
  phrase ("Welcome, brave adventurer. Your quest begins now...") using
  `voice.speak_to_file()` and play it with `st.audio()`
- Show a confirm button: "Use this voice" — when clicked, call `voice.set_voice()`
  with the selected voice_id, then `st.rerun()` to reload into the normal app UI
- Do NOT render the rest of the app UI until a voice is selected

### Error handling
- If `ANTHROPIC_API_KEY` is not set, show `st.error()` and `st.stop()`
- If `ELEVENLABS_API_KEY` is not set, show `st.warning()` (app still works, just no audio)
- Wrap the story beat generation in try/except and show `st.error()` on failure

---

## Wiring it all together

At the top of `app.py`:

```python
from dotenv import load_dotenv
load_dotenv()

db = Database()
db.init()
engine = Engine(db)
voice = Voice()
```

Instantiate once at module level. Streamlit reruns the whole script on each interaction
but these are lightweight objects — DB connections are opened/closed per query.

---

## Build order

Build and verify each file in this sequence:

1. **Poetry init** — run `poetry init` and `poetry add` as described above; confirm
   `poetry env info` shows a valid virtualenv before writing any code
2. **`database.py`** — run `poetry run python database.py` to verify tables create cleanly
3. **`prompts.py`** — no dependencies, just constants
4. **`engine.py`** — test `start_campaign()` and `generate_story_beat()` with a
   quick standalone script: `poetry run python engine.py`
5. **`app.py`** — text-only first, comment out all voice calls:
   `poetry run streamlit run app.py`
6. **`voice.py`** — add last, test standalone: `poetry run python voice.py`

---

## Testing checklist

- [ ] `poetry env info` shows a valid virtualenv path
- [ ] `poetry run python database.py` creates `stories.db` with correct schema
- [ ] Can create a campaign via engine and see it in DB
- [ ] Can generate a story beat and see messages saved to DB
- [ ] Streamlit app starts with `streamlit run app.py`
- [ ] Can start a new Fantasy campaign end-to-end
- [ ] Can end session and see summary saved
- [ ] Can continue the campaign in a new session and see old summaries in context
- [ ] On first run with blank ELEVENLABS_VOICE_ID, voice picker screen appears
- [ ] Voice list is populated with default/professional voices only
- [ ] Preview button plays sample audio
- [ ] Confirming a voice writes it to .env and reloads the app
- [ ] On subsequent runs, voice picker is skipped and app loads directly
- [ ] ElevenLabs audio plays after each story beat
- [ ] App works gracefully without ELEVENLABS_API_KEY (text only, no voice picker shown)

---

## Notes for Claude Code

- Use `python-dotenv` for all secrets — never hardcode keys
- SQLite only, no external DB setup required
- All ElevenLabs and Anthropic calls should have try/except with clear error messages
- The Streamlit `st.audio()` autoplay may require `format="audio/mp3"` — set it explicitly
- Keep all story content strictly age-appropriate (8–12) — the NARRATOR_SYSTEM_PROMPT
  is the primary guardrail but engine.py should also pass `max_tokens=300` to keep
  responses concise and listenable
- Use `anthropic` SDK (not raw HTTP) for all Claude calls
- Use `elevenlabs` SDK (not raw HTTP) for all TTS calls
- All commands use `poetry run <cmd>` or are run inside `poetry shell` — never
  install packages with pip directly into the system Python
