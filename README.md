# Pathfinder Quest

A storytelling app for young adventurers (ages 8–12) set in the Pathfinder 2nd Edition world of Golarion. Type what your hero does, and your Game Master (powered by Claude) narrates what happens next — then reads it aloud in a dramatic narrator voice. Your campaign is saved automatically so every quest continues where you left off.

---

## How to Play

### Creating your hero

When you start a new adventure, you'll fill out a short character sheet in the sidebar:

| Field | What to put |
|---|---|
| Campaign title | A name for your whole adventure, like "The Goblin Menace" or "Secrets of the Tomb" |
| Adventure setting | Where your story takes place — pick one of four Golarion locations |
| Hero name | Whatever you want to be called |
| Ancestry | Your hero's people — Human, Elf, Dwarf, Gnome, Halfling, Goblin, and more |
| Class | Your hero's skills and fighting style (see below) |
| Level | Start at 1. You can increase this when continuing a campaign as your hero grows |
| Personality | Two or three words that describe your hero, like "brave, curious, loyal" |

**Choosing a class:**

| Class | What they're good at |
|---|---|
| Fighter | Hitting things hard with weapons and shields |
| Wizard | Casting powerful spells from a spellbook |
| Rogue | Sneaking, picking locks, and striking from the shadows |
| Cleric | Healing allies and channeling divine power |
| Ranger | Tracking, archery, and surviving in the wild |
| Barbarian | Raging into battle with incredible strength |
| Paladin (Champion) | Protecting allies with holy power and heavy armor |
| Druid | Commanding nature, animals, and the elements |
| Bard | Inspiring allies with music and casting enchantments |
| Monk | Fighting without weapons using speed and discipline |
| Sorcerer | Casting spells from raw magical power in the blood |
| Alchemist | Crafting bombs, potions, and experimental elixirs |

Your hero's ability scores (Strength, Dexterity, etc.) are set automatically based on your ancestry and class — no number-crunching required. You can see them in the sidebar under **Ability Scores**.

Click **Begin Adventure!** — the Game Master will describe your opening scene.

---

### Playing the game

The Game Master narrates everything that happens in the story. You respond by typing what your hero does in the chat bar at the bottom of the screen and pressing Enter.

**You can say things like:**

- *I draw my sword and charge at the goblin!*
- *I search the room carefully for any hidden doors.*
- *I try to talk to the merchant and ask what she knows about the missing shipment.*
- *I cast Burning Hands at the spider webs blocking the corridor.*
- *I climb up the wall to get a better look at the camp below.*

There are no wrong answers. The Game Master will decide what happens based on your hero's class and the situation — just describe what you want to do and see what unfolds.

**Dice rolls:** Every action that matters gets a dice roll shown below the chat. You'll see which skill was used, what you rolled, your modifier, and whether you got a Critical Success, Success, Failure, or Critical Failure. The difficulty of the roll is set by the Game Master based on the situation — picking a rusty padlock is much easier than cracking a vault.

**Tips:**
- Be specific — "I attack" works, but "I leap onto the table and swing my axe at the hobgoblin's shield arm" is more fun
- You can try anything — sneaking, persuading, running away, picking up objects, asking NPCs questions
- Your class matters — a Wizard might identify a magic rune, while a Rogue might notice a tripwire the others missed
- If the narrator describes something interesting nearby, you can interact with it
- Resources are tracked automatically — spell slots, arrows, potions, and focus points will deplete as you use them

---

### Your character sheet

The sidebar shows your hero's current status at a glance:

- **HP bar** — your health. Reaches 0 and you're in trouble
- **XP bar** — earn XP by defeating enemies, completing quests, and clever thinking. Hit 1,000 XP to level up
- **Gold** — earned by looting and completing quests
- **Spell slots / Focus points** — shown as filled (◆) and empty (◇) pips. These restore after a full night's rest
- **Ability Scores** — your six core stats with their modifiers. These affect every roll you make
- **Inventory** — items you're carrying, with quantities tracked automatically

---

### Saving and continuing

**Ending a session:** When you're done playing, click **End Session & Save Chapter** in the sidebar. The Game Master writes a short summary of everything that happened and saves it. This summary is used next time so the story picks up seamlessly.

**Continuing later:** Open the app, choose **Continue Adventure** in the sidebar, select your campaign, and click **Continue**. The Game Master will recap the story so far and drop you back into the action.

Your campaign is saved automatically in a file called `stories.db` — don't delete it or your adventures will be lost.

---

### Adventure settings

| Setting | What it's like |
|---|---|
| Sandpoint — Goblin Attack | A cozy coastal town under siege. Goblins are running wild, setting fires and causing chaos during the harvest festival. |
| Absalom — City at the Center of the World | The greatest city in Golarion, full of intrigue, magic, and mystery. Something has been stolen from the city's most secure vault. |
| Stolen Lands — Frontier Exploration | Uncharted wilderness at the edge of the known world. Your charter grants you the right to explore — but something ancient is stirring in the ruins. |
| Osirion — Desert Tombs | Scorching desert sands and ancient pharaohs. A newly discovered tomb holds secrets that could change the world — if you survive the traps. |

---

## Setup (for parents / technical setup)

### Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- An [Anthropic API key](https://console.anthropic.com/) (required — powers the Game Master)
- An [OpenAI API key](https://platform.openai.com/) (optional — powers the narrator voice; app runs text-only without it)

### Install

```bash
# Install Poetry if needed
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# Clone and install dependencies
git clone https://github.com/timgushue/rpg_app.git
cd rpg_app
poetry install

# Configure API keys
cp .env.example .env
# Edit .env and fill in your keys
```

### Configure `.env`

```
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

The `stories.db` database and `audio/` folder are created automatically on first run. Do not commit them to git.

### Run

```bash
poetry run streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`.

### Running tests

```bash
poetry run pytest tests/ -v
```

---

### Project layout

```
rpg_app/
├── app.py                  Entry point — Streamlit UI
│
├── game/                   Pathfinder 2e rules and data
│   ├── dice.py             Dice rolling, skill detection, degree of success
│   ├── game_time.py        Golarion calendar and time advancement
│   ├── character.py        Ability score generation from ancestry + class
│   └── game_data.py        All PF2e tables: classes, gear, spells, XP, etc.
│
├── ai/                     AI API integrations
│   ├── engine.py           Claude: story generation, DC assessment, resource tracking
│   ├── voice.py            OpenAI TTS: text-to-speech narration
│   └── prompts/
│       ├── narrator.py     GM system prompts (opening, recap, narration)
│       ├── structured.py   JSON-extraction prompts (resources, world state, summary)
│       └── context.py      Assembles game state into a Claude prompt
│
├── storage/
│   └── database.py         SQLite: campaigns, sessions, messages
│
├── tests/
│   ├── test_dice.py
│   ├── test_game_time.py
│   ├── test_character.py
│   └── test_game_data.py
│
├── pyproject.toml          Poetry project config and dependencies
├── .env.example            Template for API keys
└── stories.db              Auto-created — do not delete or commit
```
