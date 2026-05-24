import sqlite3
import json
import re
from typing import Optional

from game.character import build_ability_scores
from game.state_update import normalize_story_state


DB_PATH = "stories.db"


class Database:
    def init(self) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT NOT NULL,
                    genre       TEXT NOT NULL,
                    hero_name   TEXT NOT NULL,
                    hero_sheet  TEXT NOT NULL,
                    story_state TEXT,
                    world_state TEXT NOT NULL,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id     INTEGER NOT NULL REFERENCES campaigns(id),
                    session_number  INTEGER NOT NULL,
                    summary         TEXT,
                    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  INTEGER NOT NULL REFERENCES sessions(id),
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    roll_data   TEXT,
                    resolution_data TEXT,
                    applied_delta TEXT,
                    scene_title TEXT,
                    audio_path  TEXT,
                    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                conn.execute("ALTER TABLE campaigns ADD COLUMN story_state TEXT")
            except sqlite3.OperationalError:
                pass
            # Migration: add audio_path to existing databases that predate this column
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN audio_path TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN roll_data TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN resolution_data TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN applied_delta TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN scene_title TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists

        # Migration: normalise hero sheets that predate the gold/xp/inventory-dict format
        self._migrate_hero_sheets()
        self._migrate_story_state()

    def _migrate_hero_sheets(self) -> None:
        """Convert legacy string inventories, extract gp strings, seed missing gold/xp fields."""
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT id, hero_sheet FROM campaigns").fetchall()
            for campaign_id, raw in rows:
                hero = json.loads(raw)
                changed = False

                inventory = hero.get("inventory", [])
                gold = hero.get("gold", None)

                # Convert string inventory to dicts and extract "N gp" entries
                if inventory and isinstance(inventory[0], str):
                    new_inventory = []
                    for item in inventory:
                        m = re.match(r"^(\d+)\s*gp$", item.strip())
                        if m:
                            if gold is None:
                                gold = int(m.group(1))
                        else:
                            new_inventory.append({"name": item, "quantity": 1})
                    hero["inventory"] = new_inventory
                    changed = True

                if gold is None:
                    gold = 0
                if hero.get("gold") != gold:
                    hero["gold"] = gold
                    changed = True

                if "xp" not in hero:
                    hero["xp"] = 0
                    changed = True

                # Migrate all-default ability scores to ancestry+class-derived scores
                scores = hero.get("ability_scores", {})
                if scores and all(v == 10 for v in scores.values()):
                    hero["ability_scores"] = build_ability_scores(
                        hero.get("ancestry", "Human"),
                        hero.get("class", "Fighter"),
                    )
                    changed = True

                if changed:
                    conn.execute(
                        "UPDATE campaigns SET hero_sheet = ? WHERE id = ?",
                        (json.dumps(hero), campaign_id),
                    )

    def _migrate_story_state(self) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT id, story_state FROM campaigns WHERE story_state IS NOT NULL").fetchall()
            for campaign_id, raw_story in rows:
                normalized = normalize_story_state(json.loads(raw_story))
                conn.execute("UPDATE campaigns SET story_state = ? WHERE id = ?", (json.dumps(normalized), campaign_id))

    def create_campaign(self, title, genre, hero_name, hero_sheet, world_state, story_state=None) -> int:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "INSERT INTO campaigns (title, genre, hero_name, hero_sheet, story_state, world_state) VALUES (?, ?, ?, ?, ?, ?)",
                (title, genre, hero_name, json.dumps(hero_sheet), json.dumps(story_state) if story_state is not None else None, json.dumps(world_state))
            )
            return cur.lastrowid

    def get_campaign(self, campaign_id) -> dict:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["hero_sheet"] = json.loads(d["hero_sheet"])
            d["story_state"] = normalize_story_state(json.loads(d["story_state"])) if d.get("story_state") else None
            d["world_state"] = json.loads(d["world_state"])
            return d

    def list_campaigns(self) -> list:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM campaigns ORDER BY updated_at DESC").fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["hero_sheet"] = json.loads(d["hero_sheet"])
                d["story_state"] = normalize_story_state(json.loads(d["story_state"])) if d.get("story_state") else None
                d["world_state"] = json.loads(d["world_state"])
                result.append(d)
            return result

    def update_world_state(self, campaign_id, world_state: dict) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE campaigns SET world_state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(world_state), campaign_id)
            )

    def update_hero_sheet(self, campaign_id, hero_sheet: dict) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE campaigns SET hero_sheet = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(hero_sheet), campaign_id)
            )

    def update_story_state(self, campaign_id, story_state: dict) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE campaigns SET story_state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(story_state), campaign_id)
            )

    def delete_campaign(self, campaign_id) -> bool:
        with sqlite3.connect(DB_PATH) as conn:
            exists = conn.execute("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
            if not exists:
                return False
            conn.execute(
                "DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE campaign_id = ?)",
                (campaign_id,),
            )
            conn.execute("DELETE FROM sessions WHERE campaign_id = ?", (campaign_id,))
            conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
            return True

    def create_session(self, campaign_id) -> int:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(session_number), 0) + 1 FROM sessions WHERE campaign_id = ?",
                (campaign_id,)
            ).fetchone()
            next_num = row[0]
            cur = conn.execute(
                "INSERT INTO sessions (campaign_id, session_number) VALUES (?, ?)",
                (campaign_id, next_num)
            )
            return cur.lastrowid

    def get_session(self, session_id) -> dict:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def get_latest_session(self, campaign_id) -> Optional[dict]:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE campaign_id = ? ORDER BY session_number DESC LIMIT 1",
                (campaign_id,)
            ).fetchone()
            return dict(row) if row else None

    def save_session_summary(self, session_id, summary: str) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE sessions SET summary = ? WHERE id = ?",
                (summary, session_id)
            )

    def get_recent_summaries(self, campaign_id, n=5) -> list:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """SELECT summary FROM sessions
                   WHERE campaign_id = ? AND summary IS NOT NULL
                   ORDER BY session_number DESC LIMIT ?""",
                (campaign_id, n)
            ).fetchall()
            return [row[0] for row in reversed(rows)]

    def get_campaign_sessions(self, campaign_id) -> list:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, campaign_id, session_number, summary, created_at
                FROM sessions
                WHERE campaign_id = ?
                ORDER BY session_number ASC
                """,
                (campaign_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_message(
        self,
        session_id,
        role,
        content,
        roll_data: Optional[dict] = None,
        resolution_data: Optional[dict] = None,
        applied_delta: Optional[dict] = None,
        scene_title: Optional[str] = None,
    ) -> int:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "INSERT INTO messages (session_id, role, content, roll_data, resolution_data, applied_delta, scene_title) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    role,
                    content,
                    json.dumps(roll_data) if roll_data is not None else None,
                    json.dumps(resolution_data) if resolution_data is not None else None,
                    json.dumps(applied_delta) if applied_delta is not None else None,
                    scene_title,
                )
            )
            return cur.lastrowid

    def update_message_audio(self, message_id: int, audio_path: str) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE messages SET audio_path = ? WHERE id = ?",
                (audio_path, message_id)
            )

    def get_session_messages(self, session_id) -> list:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, role, content, roll_data, resolution_data, applied_delta, scene_title, audio_path FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ).fetchall()
            return self._deserialize_messages(rows)

    def get_campaign_messages(self, campaign_id) -> list:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    messages.id,
                    messages.session_id,
                    sessions.session_number,
                    messages.role,
                    messages.content,
                    messages.roll_data,
                    messages.resolution_data,
                    messages.applied_delta,
                    messages.scene_title,
                    messages.audio_path
                FROM messages
                JOIN sessions ON sessions.id = messages.session_id
                WHERE sessions.campaign_id = ?
                ORDER BY sessions.session_number ASC, messages.id ASC
                """,
                (campaign_id,),
            ).fetchall()
            return self._deserialize_messages(rows)

    def _deserialize_messages(self, rows) -> list:
            messages = []
            for row in rows:
                message = dict(row)
                if message.get("roll_data"):
                    message["roll_data"] = json.loads(message["roll_data"])
                else:
                    message["roll_data"] = None
                if message.get("resolution_data"):
                    message["resolution_data"] = json.loads(message["resolution_data"])
                else:
                    message["resolution_data"] = None
                if message.get("applied_delta"):
                    message["applied_delta"] = json.loads(message["applied_delta"])
                else:
                    message["applied_delta"] = None
                messages.append(message)
            return messages


if __name__ == "__main__":
    db = Database()
    db.init()
    print("Database initialized successfully. Tables created in stories.db.")
