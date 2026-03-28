# Pathfinder Quest

A storytelling app for young adventurers (ages 8–12) set in the Pathfinder 2nd Edition world of Golarion. Type what your hero does, and your Game Master (powered by Claude) narrates what happens next — then reads it aloud in a dramatic narrator voice. Your campaign is saved automatically so every quest continues where you left off.

---

## How to Play

### Creating your hero

Fill out the character sheet in the sidebar:

| Field | What to put |
|---|---|
| Campaign title | A name for your adventure, like "The Goblin Menace" |
| Adventure setting | Where your story takes place — pick one of four Golarion locations |
| Hero name | Whatever you want to be called |
| Ancestry | Your hero's people — Human, Elf, Dwarf, Gnome, Halfling, Goblin, and more |
| Class | Your hero's skills and fighting style (see table below) |
| Level | Start at 1 |
| Personality | Two or three words: "brave, curious, loyal" |

**Classes:**

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

Your hero's ability scores are set automatically from your ancestry and class — no number-crunching needed. You can see them in the sidebar under **Ability Scores**.

Click **Begin Adventure!** and the Game Master will describe your opening scene.

---

### Playing

Type what your hero does in the chat bar and press Enter. The Game Master narrates what happens.

**Examples:**
- *I draw my sword and charge at the goblin!*
- *I search the room carefully for hidden doors.*
- *I try to persuade the merchant to lower his price.*
- *I cast Burning Hands at the web blocking the corridor.*
- *I climb the wall to get a better look at the camp below.*

**Dice rolls** appear below the chat after each action — they show which skill was used, your roll, your modifier, and whether you got a Critical Success, Success, Failure, or Critical Failure. The difficulty is set by the Game Master based on the situation.

**Tips:**
- Be specific — "I leap onto the table and swing my axe at the hobgoblin's shield arm" is more fun than "I attack"
- Your class matters — a Wizard might identify a magic rune while a Rogue notices a tripwire
- Resources track automatically — spell slots, arrows, potions, and focus points deplete as you use them and restore after a full rest

---

### Your character sheet

| Element | What it shows |
|---|---|
| HP bar | Your health |
| XP bar | Earn 1,000 XP to level up |
| Gold | Earned by looting and completing quests |
| Spell slots / Focus points | ◆ filled · ◇ empty — restore after a full night's rest |
| Ability Scores | Your six core stats and their modifiers |
| Inventory | Items you carry, quantities tracked automatically |

---

### Saving and continuing

**End a session:** Click **End Session & Save Chapter** in the sidebar. The Game Master writes a chapter summary and saves it.

**Continue later:** Choose **Continue Adventure**, select your campaign, and click **Continue**. The Game Master recaps the story and picks up where you left off.

Your campaign lives in `stories.db` — don't delete it.

---

### Adventure settings

| Setting | What it's like |
|---|---|
| Sandpoint — Goblin Attack | A cozy coastal town under siege during the harvest festival |
| Absalom — City at the Center of the World | The greatest city in Golarion — something has been stolen from its most secure vault |
| Stolen Lands — Frontier Exploration | Uncharted wilderness — your charter grants you the right to explore, but something ancient stirs in the ruins |
| Osirion — Desert Tombs | Ancient pharaohs and deadly traps — a newly discovered tomb holds world-changing secrets |

---

## Setup

### Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- [Anthropic API key](https://console.anthropic.com/) — required (powers the Game Master)
- [OpenAI API key](https://platform.openai.com/) — optional (powers the narrator voice; app runs text-only without it)

### Install

```bash
git clone https://github.com/timgushue/rpg_app.git
cd rpg_app
poetry install
cp .env.example .env
# Edit .env and add your API keys
```

### Run

```bash
poetry run streamlit run app.py
```

Opens at `http://localhost:8501`. The database and audio folder are created automatically on first run.

### Tests

```bash
poetry run pytest tests/ -v
```

---

For a full description of the code structure, data models, and design decisions see [OVERVIEW.md](OVERVIEW.md).
