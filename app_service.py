import os
from typing import Optional


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
        }

    def get_environment_status(self) -> dict:
        return {
            "error": None if os.environ.get("ANTHROPIC_API_KEY") else "ANTHROPIC_API_KEY is not set. Please add it to your .env file.",
            "warning": None if os.environ.get("OPENAI_API_KEY") else "OPENAI_API_KEY is not set. The app will run in text-only mode (no audio).",
        }

    def list_campaign_options(self) -> dict[str, int]:
        campaigns = self.db.list_campaigns()
        return {f"{campaign['title']} - {campaign['genre']}": campaign["id"] for campaign in campaigns}

    def get_campaign(self, campaign_id: Optional[int]) -> Optional[dict]:
        if not campaign_id:
            return None
        return self.db.get_campaign(campaign_id)

    def start_new_adventure(
        self,
        title: str,
        adventure_setting: str,
        hero_name: str,
        ancestry: str,
        hero_class: str,
        level: int,
        traits_text: str,
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
        )
        session_id = self.db.create_session(campaign_id)
        beat, msg_id = self.engine.generate_opening_scene(campaign_id, session_id, is_new=True)
        audio_path = self.voice.speak_to_persistent_file(beat, msg_id, self.audio_dir)
        if audio_path:
            self.db.update_message_audio(msg_id, audio_path)

        state = self.empty_state()
        state.update(
            {
                "campaign_id": campaign_id,
                "session_id": session_id,
                "messages": [self._build_message("assistant", beat, audio_path, msg_id)],
                "story_started": True,
                "latest_audio_path": audio_path,
            }
        )
        return state

    def continue_adventure(self, campaign_id: int) -> dict:
        previous_session = self.db.get_latest_session(campaign_id)
        past_messages = self.db.get_session_messages(previous_session["id"]) if previous_session else []
        session_id = self.db.create_session(campaign_id)
        recap, msg_id = self.engine.generate_opening_scene(campaign_id, session_id, is_new=False)
        audio_path = self.voice.speak_to_persistent_file(recap, msg_id, self.audio_dir)
        if audio_path:
            self.db.update_message_audio(msg_id, audio_path)

        state = self.empty_state()
        state.update(
            {
                "campaign_id": campaign_id,
                "session_id": session_id,
                "messages": [self._build_message_from_record(message) for message in past_messages]
                + [self._build_message("assistant", recap, audio_path, msg_id)],
                "story_started": True,
                "latest_audio_path": audio_path,
            }
        )
        return state

    def submit_turn(self, campaign_id: int, session_id: int, user_input: str) -> dict:
        beat, roll, msg_id = self.engine.generate_story_beat(campaign_id, session_id, user_input)
        audio_path = self.voice.speak_to_persistent_file(beat, msg_id, self.audio_dir)
        if audio_path:
            self.db.update_message_audio(msg_id, audio_path)

        return {
            "messages": [
                self._build_message("user", user_input, None),
                self._build_message("assistant", beat, audio_path, msg_id, roll_data=roll),
            ],
            "latest_audio_path": audio_path,
            "latest_roll": roll,
        }

    def end_session(self, campaign_id: int, session_id: int) -> str:
        return self.engine.summarize_session(campaign_id, session_id)

    def _build_message(
        self,
        role: str,
        content: str,
        audio_path: Optional[str],
        message_id: Optional[int] = None,
        roll_data: Optional[dict] = None,
    ) -> dict:
        return {
            "id": message_id,
            "role": role,
            "content": content,
            "roll_data": roll_data,
            "audio_path": audio_path,
            "audio_url": self._audio_url(audio_path),
        }

    def _build_message_from_record(self, message: dict) -> dict:
        return self._build_message(
            role=message["role"],
            content=message["content"],
            audio_path=message.get("audio_path"),
            message_id=message.get("id"),
            roll_data=message.get("roll_data"),
        )

    def _audio_url(self, audio_path: Optional[str]) -> Optional[str]:
        if not audio_path or not os.path.exists(audio_path):
            return None
        return f"/audio/{os.path.basename(audio_path)}"
