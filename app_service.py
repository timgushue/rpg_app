import os
from typing import Optional

from game.character import apply_ability_bump
from game.game_data import CLASS_LEVEL_FEATURES, XP_PER_LEVEL
from game.state_update import get_current_beat, normalize_story_state


class AppService:
    def __init__(self, db, engine, voice, audio_dir: str):
        self.db = db
        self.engine = engine
        self.voice = voice
        self.audio_dir = audio_dir

    def empty_state(self) -> dict:
        return {
            "campaign_id": None,
            "session_id": None,
            "messages": [],
            "story_started": False,
            "latest_audio_path": None,
            "latest_roll": None,
            "latest_resolution_data": None,
            "latest_applied_delta": None,
            "needs_recap": False,
        }

    def get_environment_status(self) -> dict:
        return {
            "error": None if os.environ.get("ANTHROPIC_API_KEY") else "ANTHROPIC_API_KEY is not set. Please add it to your .env file.",
            "warning": None if os.environ.get("OPENAI_API_KEY") else "OPENAI_API_KEY is not set. The app will run in text-only mode (no audio).",
        }

    def list_campaign_options(self) -> dict[str, int]:
        campaigns = self.db.list_campaigns()
        return {f"{campaign['title']} - {campaign['genre']}": campaign["id"] for campaign in campaigns}

    def list_campaign_cards(self) -> list[dict]:
        cards = []
        for campaign in self.db.list_campaigns():
            hero = campaign["hero_sheet"]
            story = normalize_story_state(campaign.get("story_state"))
            cards.append(
                {
                    "id": campaign["id"],
                    "title": campaign["title"],
                    "setting": campaign["genre"],
                    "hero_name": campaign["hero_name"],
                    "hero_line": f"Level {hero.get('level', 1)} {hero.get('ancestry', '')} {hero.get('class', '')}".strip(),
                    "story_summary": self.story_summary(campaign),
                    "updated_at": campaign.get("updated_at"),
                }
            )
        return cards

    def get_campaign(self, campaign_id: Optional[int], ensure_story_state: bool = True) -> Optional[dict]:
        if not campaign_id:
            return None
        if ensure_story_state:
            return self.engine.ensure_campaign_story_state(campaign_id)
        return self.db.get_campaign(campaign_id)

    def delete_campaign(self, campaign_id: int) -> bool:
        messages = self.db.get_campaign_messages(campaign_id)
        deleted = self.db.delete_campaign(campaign_id)
        if not deleted:
            return False
        audio_root = os.path.abspath(self.audio_dir)
        for message in messages:
            audio_path = message.get("audio_path")
            if not audio_path:
                continue
            absolute_path = os.path.abspath(audio_path)
            if not absolute_path.startswith(audio_root + os.sep):
                continue
            try:
                os.remove(absolute_path)
            except FileNotFoundError:
                pass
        return True

    def story_summary(self, campaign: Optional[dict]) -> dict:
        if not campaign:
            return {"chapter": "", "objective": "", "plot_so_far": ""}
        story = normalize_story_state(campaign.get("story_state"))
        current_beat = get_current_beat(story)
        chapter = story.get("title", "")
        objective = current_beat.get("goal", "") if current_beat else story.get("hero_goal", "")
        plot_so_far = story.get("last_turn_summary") or ""
        return {
            "chapter": chapter,
            "objective": objective,
            "plot_so_far": plot_so_far,
        }

    def get_journal_data(self, campaign_id: int) -> dict:
        campaign = self.get_campaign(campaign_id)
        sessions = self.db.get_campaign_sessions(campaign_id)
        messages = [self._build_message_from_record(message) for message in self.db.get_campaign_messages(campaign_id)]
        messages_by_session = {}
        for message in messages:
            messages_by_session.setdefault(message.get("session_id"), []).append(message)
        chapters = []
        for session in sessions:
            session_messages = messages_by_session.get(session["id"], [])
            if not session.get("summary") and not session_messages:
                continue
            chapters.append(
                {
                    "id": session["id"],
                    "session_number": session["session_number"],
                    "summary": session.get("summary"),
                    "created_at": session.get("created_at"),
                    "messages": session_messages,
                }
            )
        return {
            "campaign": campaign,
            "story_summary": self.story_summary(campaign),
            "chapters": chapters,
            "messages": messages,
        }

    def apply_level_up_choice(self, campaign_id: int, ability: str) -> dict:
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        hero = apply_ability_bump(campaign["hero_sheet"], ability)
        self.db.update_hero_sheet(campaign_id, hero)
        campaign["hero_sheet"] = hero
        return campaign

    def get_level_up_feature(self, hero_class: str, level: int) -> str:
        return CLASS_LEVEL_FEATURES.get(hero_class, {}).get(level, "Your hero grows stronger and more capable.")

    def load_active_session(self, campaign_id: int, session_id: int) -> dict:
        state = self.empty_state()
        records = self.db.get_campaign_messages(campaign_id)
        if not records:
            records = self.db.get_session_messages(session_id)
        messages = [self._build_message_from_record(message) for message in records]
        recent_messages = messages[-24:]
        state.update(
            {
                "campaign_id": campaign_id,
                "session_id": session_id,
                "messages": recent_messages,
                "story_started": True,
                "latest_audio_path": self._latest_audio_path(recent_messages),
                "needs_recap": False,
            }
        )
        return state

    def resume_adventure(self, campaign_id: int) -> dict:
        self.get_campaign(campaign_id)
        latest_session = self.db.get_latest_session(campaign_id)
        if latest_session:
            latest_messages = self.db.get_session_messages(latest_session["id"])
            if latest_session.get("summary") is None:
                state = self.load_active_session(campaign_id, latest_session["id"])
                state["needs_recap"] = not any(message["role"] == "assistant" for message in latest_messages)
                return state

        session_id = self.db.create_session(campaign_id)
        state = self.load_active_session(campaign_id, session_id)
        state["needs_recap"] = True
        return state

    def start_new_adventure(
        self,
        title: str,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits_text: str,
        story_state: Optional[dict] = None,
    ) -> dict:
        traits = [trait.strip() for trait in traits_text.split(",") if trait.strip()]
        campaign_id = self.engine.start_campaign(
            title=title,
            adventure_setting=adventure_setting,
            hero_name=hero_name,
            ancestry=ancestry,
            hero_class=hero_class,
            level=level,
            traits=traits,
            story_state=story_state,
        )
        session_id = self.db.create_session(campaign_id)
        opening_state = self.generate_initial_scene(campaign_id, session_id)

        state = self.empty_state()
        state.update(
            {
                "campaign_id": campaign_id,
                "session_id": session_id,
                "messages": opening_state["messages"],
                "story_started": True,
                "latest_audio_path": opening_state["latest_audio_path"],
            }
        )
        return state

    def create_new_adventure_shell(
        self,
        title: str,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits_text: str,
        story_state: Optional[dict] = None,
    ) -> dict:
        traits = [trait.strip() for trait in traits_text.split(",") if trait.strip()]
        campaign_id = self.engine.create_campaign_shell(
            title=title,
            adventure_setting=adventure_setting,
            hero_name=hero_name,
            ancestry=ancestry,
            hero_class=hero_class,
            level=level,
            traits=traits,
            story_state=story_state,
        )
        session_id = self.db.create_session(campaign_id)
        state = self.empty_state()
        state.update(
            {
                "campaign_id": campaign_id,
                "session_id": session_id,
                "messages": [],
                "story_started": True,
                "latest_audio_path": None,
            }
        )
        return state

    def generate_initial_scene(self, campaign_id: int, session_id: int) -> dict:
        beat, msg_id = self.engine.generate_opening_scene(campaign_id, session_id, is_new=True)
        audio_path = self.voice.speak_to_persistent_file(beat, msg_id, self.audio_dir)
        if audio_path:
            self.db.update_message_audio(msg_id, audio_path)
        return {
            "messages": [self._build_message("assistant", beat, audio_path, msg_id)],
            "latest_audio_path": audio_path,
        }

    def generate_story_arc_draft(
        self,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits_text: str,
    ) -> dict:
        traits = [trait.strip() for trait in traits_text.split(",") if trait.strip()]
        return self.engine.generate_story_arc_draft(
            adventure_setting=adventure_setting,
            hero_name=hero_name or "The hero",
            ancestry=ancestry,
            hero_class=hero_class,
            level=level,
            traits=traits,
        )

    def continue_adventure(self, campaign_id: int) -> dict:
        state = self.resume_adventure(campaign_id)
        if not state["needs_recap"]:
            return state
        recap_state = self.generate_continue_recap(campaign_id, state["session_id"])
        state["messages"].extend(recap_state["messages"])
        state["latest_audio_path"] = recap_state["latest_audio_path"]
        state["needs_recap"] = False
        return state

    def generate_continue_recap(self, campaign_id: int, session_id: int) -> dict:
        session_messages = self.db.get_session_messages(session_id)
        if not self._has_user_actions(session_messages):
            assistant_messages = [message for message in session_messages if message["role"] == "assistant"]
            if assistant_messages:
                latest = self._build_message_from_record(assistant_messages[-1])
                return {
                    "messages": [latest],
                    "latest_audio_path": latest.get("audio_path"),
                    "needs_recap": False,
                }

        recap, msg_id = self.engine.generate_opening_scene(campaign_id, session_id, is_new=False)
        audio_path = self.voice.speak_to_persistent_file(recap, msg_id, self.audio_dir)
        if audio_path:
            self.db.update_message_audio(msg_id, audio_path)

        return {
            "messages": [self._build_message("assistant", recap, audio_path, msg_id)],
            "latest_audio_path": audio_path,
            "needs_recap": False,
        }

    def submit_turn(self, campaign_id: int, session_id: int, user_input: str) -> dict:
        result = self.engine.generate_story_beat(campaign_id, session_id, user_input)
        beat = result["story_beat"]
        roll = result["roll_result"]
        msg_id = result["message_id"]
        resolution_data = result.get("resolution_data")
        applied_delta = result.get("applied_delta")
        scene_title = result.get("scene_title")

        return {
            "messages": [
                self._build_message("user", user_input, None),
                self._build_message(
                    "assistant",
                    beat,
                    None,
                    msg_id,
                    roll_data=roll,
                    resolution_data=resolution_data,
                    applied_delta=applied_delta,
                    scene_title=scene_title,
                ),
            ],
            "latest_audio_path": None,
            "latest_roll": roll,
            "latest_resolution_data": resolution_data,
            "latest_applied_delta": applied_delta,
            "message_id": msg_id,
            "story_beat": beat,
            "scene_title": scene_title,
        }

    def generate_audio_for_message(self, message_id: int, text: str) -> Optional[dict]:
        if not message_id:
            return None
        audio_path = self.voice.speak_to_persistent_file(text, message_id, self.audio_dir)
        if not audio_path:
            return None
        self.db.update_message_audio(message_id, audio_path)
        return {
            "message_id": message_id,
            "audio_path": audio_path,
            "audio_url": self._audio_url(audio_path),
        }

    def end_session(self, campaign_id: int, session_id: int) -> str:
        messages = self.db.get_session_messages(session_id)
        if not self._has_user_actions(messages):
            return "No new player actions to summarize."
        return self.engine.summarize_session(campaign_id, session_id)

    def _has_user_actions(self, messages: list[dict]) -> bool:
        return any(message.get("role") == "user" for message in messages)

    def _latest_audio_path(self, messages: list[dict]) -> Optional[str]:
        for message in reversed(messages):
            if message.get("audio_path"):
                return message["audio_path"]
        return None

    def _build_message(
        self,
        role: str,
        content: str,
        audio_path: Optional[str],
        message_id: Optional[int] = None,
        roll_data: Optional[dict] = None,
        resolution_data: Optional[dict] = None,
        applied_delta: Optional[dict] = None,
        scene_title: Optional[str] = None,
    ) -> dict:
        return {
            "id": message_id,
            "role": role,
            "content": content,
            "roll_data": roll_data,
            "resolution_data": resolution_data,
            "applied_delta": applied_delta,
            "scene_title": scene_title,
            "audio_path": audio_path,
            "audio_url": self._audio_url(audio_path),
        }

    def _build_message_from_record(self, message: dict) -> dict:
        built = self._build_message(
            role=message["role"],
            content=message["content"],
            audio_path=message.get("audio_path"),
            message_id=message.get("id"),
            roll_data=message.get("roll_data"),
            resolution_data=message.get("resolution_data"),
            applied_delta=message.get("applied_delta"),
            scene_title=message.get("scene_title"),
        )
        if message.get("session_id") is not None:
            built["session_id"] = message["session_id"]
        if message.get("session_number") is not None:
            built["session_number"] = message["session_number"]
        return built

    def _audio_url(self, audio_path: Optional[str]) -> Optional[str]:
        if not audio_path or not os.path.exists(audio_path):
            return None
        return f"/audio/{os.path.basename(audio_path)}"
