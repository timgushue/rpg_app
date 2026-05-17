from pathlib import Path

from app_service import AppService


class FakeDB:
    def __init__(self):
        self.updated_audio = []
        self.previous_messages = []
        self.latest_session = None

    def create_session(self, campaign_id):
        return 7 if campaign_id == 11 else 8

    def update_message_audio(self, message_id, audio_path):
        self.updated_audio.append((message_id, audio_path))

    def get_latest_session(self, campaign_id):
        return self.latest_session

    def get_session_messages(self, session_id):
        return self.previous_messages

    def get_campaign(self, campaign_id):
        return {"id": campaign_id, "hero_sheet": {"level": 1}, "world_state": {}}

    def list_campaigns(self):
        return [{"id": 11, "title": "Goblin Menace", "genre": "sandpoint"}]


class FakeEngine:
    def __init__(self):
        self.started_with = None
        self.summarized = None

    def start_campaign(self, **kwargs):
        self.started_with = kwargs
        return 11

    def generate_opening_scene(self, campaign_id, session_id, is_new):
        if is_new:
            return "Opening scene", 101
        return "Recap scene", 102

    def generate_story_beat(self, campaign_id, session_id, user_input):
        return "Story beat", {"dc": 15, "skill": "Perception", "roll": 12, "modifier": 3, "total": 15, "degree": "success"}, 103

    def summarize_session(self, campaign_id, session_id):
        self.summarized = (campaign_id, session_id)
        return "Chapter summary"


class FakeVoice:
    def __init__(self, audio_path):
        self.audio_path = audio_path
        self.calls = []

    def speak_to_persistent_file(self, text, message_id, audio_dir):
        self.calls.append((text, message_id, audio_dir))
        return self.audio_path


def test_start_new_adventure_returns_active_state(tmp_path):
    audio_path = tmp_path / "audio" / "message_101.mp3"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"mp3")

    db = FakeDB()
    engine = FakeEngine()
    voice = FakeVoice(str(audio_path))
    service = AppService(db, engine, voice, str(audio_path.parent))

    state = service.start_new_adventure(
        title="Goblin Menace",
        adventure_setting="sandpoint",
        hero_name="Pip",
        ancestry="Elf",
        hero_class="Wizard",
        level=1,
        traits_text="brave, curious",
    )

    assert engine.started_with["traits"] == ["brave", "curious"]
    assert state["campaign_id"] == 11
    assert state["session_id"] == 7
    assert state["story_started"] is True
    assert state["messages"][0]["audio_url"] == "/audio/message_101.mp3"
    assert db.updated_audio == [(101, str(audio_path))]


def test_continue_adventure_includes_previous_messages(tmp_path):
    old_audio_path = tmp_path / "audio" / "message_1.mp3"
    new_audio_path = tmp_path / "audio" / "message_102.mp3"
    old_audio_path.parent.mkdir()
    old_audio_path.write_bytes(b"old")
    new_audio_path.write_bytes(b"new")

    db = FakeDB()
    db.latest_session = {"id": 4}
    db.previous_messages = [{"id": 1, "role": "assistant", "content": "Earlier scene", "audio_path": str(old_audio_path)}]
    engine = FakeEngine()
    voice = FakeVoice(str(new_audio_path))
    service = AppService(db, engine, voice, str(new_audio_path.parent))

    state = service.continue_adventure(11)

    assert state["story_started"] is True
    assert len(state["messages"]) == 2
    assert state["messages"][0]["audio_url"] == "/audio/message_1.mp3"
    assert state["messages"][1]["content"] == "Recap scene"


def test_submit_turn_returns_new_messages_and_roll(tmp_path):
    audio_path = tmp_path / "audio" / "message_103.mp3"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"turn")

    db = FakeDB()
    engine = FakeEngine()
    voice = FakeVoice(str(audio_path))
    service = AppService(db, engine, voice, str(audio_path.parent))

    result = service.submit_turn(11, 7, "I look for traps.")

    assert [message["role"] for message in result["messages"]] == ["user", "assistant"]
    assert result["messages"][1]["audio_url"] == "/audio/message_103.mp3"
    assert result["latest_roll"]["dc"] == 15


def test_end_session_delegates_to_engine(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    summary = service.end_session(11, 7)

    assert summary == "Chapter summary"
    assert engine.summarized == (11, 7)
