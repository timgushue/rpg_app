from pathlib import Path

from app_service import AppService


class FakeDB:
    def __init__(self):
        self.updated_audio = []
        self.previous_messages = []
        self.session_messages = {}
        self.latest_session = None
        self.created_sessions = []
        self.deleted_campaigns = []

    def create_session(self, campaign_id):
        self.created_sessions.append(campaign_id)
        return 7 if campaign_id == 11 else 8

    def update_message_audio(self, message_id, audio_path):
        self.updated_audio.append((message_id, audio_path))

    def get_latest_session(self, campaign_id):
        return self.latest_session

    def get_session_messages(self, session_id):
        return self.session_messages.get(session_id, [])

    def get_campaign_messages(self, campaign_id):
        return self.previous_messages

    def get_campaign(self, campaign_id):
        return {"id": campaign_id, "hero_sheet": {"level": 1}, "world_state": {}, "story_state": {}}

    def list_campaigns(self):
        return [{"id": 11, "title": "Goblin Menace", "genre": "sandpoint"}]

    def get_campaign_sessions(self, campaign_id):
        return [{"id": 7, "campaign_id": campaign_id, "session_number": 1, "summary": "The hero answered the call.", "created_at": "2026-05-17"}]

    def delete_campaign(self, campaign_id):
        self.deleted_campaigns.append(campaign_id)
        return campaign_id == 11


class FakeEngine:
    def __init__(self):
        self.started_with = None
        self.summarized = None
        self.ensured_campaign_id = None
        self.draft_with = None

    def start_campaign(self, **kwargs):
        self.started_with = kwargs
        return 11

    def generate_story_arc_draft(self, **kwargs):
        self.draft_with = kwargs
        return {"title": "Fresh Arc", "hero_goal": "Find the new path.", "acts": [], "current_act_id": "", "current_beat_id": ""}

    def generate_opening_scene(self, campaign_id, session_id, is_new):
        if is_new:
            return "Opening scene", 101
        return "Recap scene", 102

    def generate_story_beat(self, campaign_id, session_id, user_input):
        return {
            "story_beat": "Story beat",
            "roll_result": {"dc": 15, "skill": "Perception", "roll": 12, "modifier": 3, "total": 15, "degree": "success"},
            "message_id": 103,
            "resolution_data": {"narration_cue": "The hero spots the hidden danger."},
            "applied_delta": {"xp_change": 10},
            "scene_title": "Hidden Danger",
        }

    def summarize_session(self, campaign_id, session_id):
        self.summarized = (campaign_id, session_id)
        return "Chapter summary"

    def ensure_campaign_story_state(self, campaign_id):
        self.ensured_campaign_id = campaign_id
        return {"id": campaign_id, "hero_sheet": {"level": 1}, "world_state": {}, "story_state": {"title": "Arc"}}


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
    assert engine.started_with["story_state"] is None
    assert state["campaign_id"] == 11
    assert state["session_id"] == 7
    assert state["story_started"] is True
    assert state["messages"][0]["audio_url"] == "/audio/message_101.mp3"
    assert db.updated_audio == [(101, str(audio_path))]


def test_start_new_adventure_can_use_drafted_story_arc(tmp_path):
    audio_path = tmp_path / "audio" / "message_101.mp3"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"mp3")

    db = FakeDB()
    engine = FakeEngine()
    voice = FakeVoice(str(audio_path))
    service = AppService(db, engine, voice, str(audio_path.parent))

    service.start_new_adventure(
        title="Fresh Tale",
        adventure_setting="sandpoint",
        hero_name="Pip",
        ancestry="Elf",
        hero_class="Wizard",
        level=1,
        traits_text="brave",
        story_state={"title": "Fresh Arc", "hero_goal": "Find a different mystery."},
    )

    assert engine.started_with["story_state"]["title"] == "Fresh Arc"


def test_generate_story_arc_draft_delegates_to_engine(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    engine = FakeEngine()
    service = AppService(FakeDB(), engine, FakeVoice(None), str(audio_dir))

    draft = service.generate_story_arc_draft("sandpoint", "Pip", "Elf", "Wizard", 1, "brave, curious")

    assert draft["title"] == "Fresh Arc"
    assert engine.draft_with["traits"] == ["brave", "curious"]


def test_delete_campaign_removes_audio_files_under_audio_dir(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    audio_path = audio_dir / "message_1.mp3"
    audio_path.write_bytes(b"mp3")
    db = FakeDB()
    db.previous_messages = [{"id": 1, "role": "assistant", "content": "Scene", "audio_path": str(audio_path)}]
    service = AppService(db, FakeEngine(), FakeVoice(None), str(audio_dir))

    deleted = service.delete_campaign(11)

    assert deleted is True
    assert db.deleted_campaigns == [11]
    assert not audio_path.exists()


def test_continue_adventure_starts_new_session_with_recap_after_summarized_session(tmp_path):
    old_audio_path = tmp_path / "audio" / "message_1.mp3"
    new_audio_path = tmp_path / "audio" / "message_102.mp3"
    old_audio_path.parent.mkdir()
    old_audio_path.write_bytes(b"old")
    new_audio_path.write_bytes(b"new")

    db = FakeDB()
    db.previous_messages = [{"id": 1, "role": "assistant", "content": "Earlier scene", "audio_path": str(old_audio_path), "roll_data": None, "resolution_data": None, "applied_delta": None}]
    db.latest_session = {"id": 6, "campaign_id": 11, "session_number": 1, "summary": "Previous chapter"}
    engine = FakeEngine()
    voice = FakeVoice(str(new_audio_path))
    service = AppService(db, engine, voice, str(new_audio_path.parent))

    state = service.continue_adventure(11)

    assert state["story_started"] is True
    assert len(state["messages"]) == 2
    assert state["messages"][0]["audio_url"] == "/audio/message_1.mp3"
    assert state["messages"][1]["content"] == "Recap scene"


def test_resume_adventure_reuses_unsummarized_session_without_recap(tmp_path):
    old_audio_path = tmp_path / "audio" / "message_1.mp3"
    old_audio_path.parent.mkdir()
    old_audio_path.write_bytes(b"old")

    db = FakeDB()
    db.latest_session = {"id": 7, "campaign_id": 11, "session_number": 3, "summary": None}
    db.session_messages[7] = [
        {"id": 1, "role": "assistant", "content": "Current scene", "audio_path": str(old_audio_path), "roll_data": None, "resolution_data": None, "applied_delta": None},
        {"id": 2, "role": "user", "content": "I search the room", "audio_path": None, "roll_data": None, "resolution_data": None, "applied_delta": None},
    ]
    service = AppService(db, FakeEngine(), FakeVoice(None), str(old_audio_path.parent))

    state = service.resume_adventure(11)

    assert state["session_id"] == 7
    assert state["needs_recap"] is False
    assert [message["content"] for message in state["messages"]] == ["Current scene", "I search the room"]


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
    assert result["messages"][1]["audio_url"] is None
    assert result["message_id"] == 103
    assert result["story_beat"] == "Story beat"
    assert result["scene_title"] == "Hidden Danger"
    assert result["messages"][1]["scene_title"] == "Hidden Danger"
    assert result["latest_roll"]["dc"] == 15
    assert result["messages"][1]["resolution_data"]["narration_cue"] == "The hero spots the hidden danger."
    assert result["latest_applied_delta"]["xp_change"] == 10
    assert voice.calls == []


def test_generate_audio_for_message_updates_database(tmp_path):
    audio_path = tmp_path / "audio" / "message_103.mp3"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"turn")

    db = FakeDB()
    voice = FakeVoice(str(audio_path))
    service = AppService(db, FakeEngine(), voice, str(audio_path.parent))

    result = service.generate_audio_for_message(103, "Story beat")

    assert result["message_id"] == 103
    assert result["audio_url"] == "/audio/message_103.mp3"
    assert db.updated_audio == [(103, str(audio_path))]
    assert voice.calls == [("Story beat", 103, str(audio_path.parent))]


def test_end_session_delegates_to_engine(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    db.session_messages[7] = [{"id": 1, "role": "user", "content": "I act.", "audio_path": None, "roll_data": None, "resolution_data": None, "applied_delta": None}]
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    summary = service.end_session(11, 7)

    assert summary == "Chapter summary"
    assert engine.summarized == (11, 7)


def test_end_session_without_user_actions_does_not_summarize(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    db.session_messages[7] = [{"id": 1, "role": "assistant", "content": "Recap scene", "audio_path": None, "roll_data": None, "resolution_data": None, "applied_delta": None}]
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    summary = service.end_session(11, 7)

    assert summary == "No new player actions to summarize."
    assert engine.summarized is None


def test_resume_adventure_reuses_empty_recap_session(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    db.latest_session = {"id": 7, "campaign_id": 11, "session_number": 2}
    recap = {"id": 4, "role": "assistant", "content": "Existing recap", "audio_path": None, "roll_data": None, "resolution_data": None, "applied_delta": None}
    db.session_messages[7] = [recap]
    db.previous_messages = [recap]
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    state = service.resume_adventure(11)

    assert state["session_id"] == 7
    assert state["needs_recap"] is False
    assert state["messages"][0]["content"] == "Existing recap"
    assert db.created_sessions == []


def test_resume_adventure_creates_recap_needed_state_after_summarized_session(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    db.latest_session = {"id": 6, "campaign_id": 11, "session_number": 1, "summary": "Previous chapter"}
    db.session_messages[6] = [{"id": 2, "role": "user", "content": "I act.", "audio_path": None, "roll_data": None, "resolution_data": None, "applied_delta": None}]
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    state = service.resume_adventure(11)

    assert state["session_id"] == 7
    assert state["needs_recap"] is True
    assert db.created_sessions == [11]


def test_get_campaign_ensures_story_state(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    campaign = service.get_campaign(11)

    assert engine.ensured_campaign_id == 11
    assert campaign["story_state"]["title"] == "Arc"


def test_story_summary_uses_current_goal(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    campaign = {
        "title": "Goblin Menace",
        "hero_name": "Pip",
        "hero_sheet": {"level": 1},
        "story_state": {
            "title": "The Ember Crown",
            "premise": "A village is in danger.",
            "last_turn_summary": "The hero found a burned wagon.",
            "acts": [
                {
                    "id": "act-1",
                    "title": "The Hook",
                    "beats": [
                        {"id": "beat-1", "title": "Smoke on the Road", "goal": "Reach the wagon", "status": "active"}
                    ],
                }
            ],
            "current_act_id": "act-1",
            "current_beat_id": "beat-1",
        },
    }

    summary = service.story_summary(campaign)

    assert summary["chapter"] == "The Ember Crown"
    assert summary["objective"] == "Reach the wagon"
    assert summary["plot_so_far"] == "The hero found a burned wagon."


def test_get_journal_data_includes_messages_and_chapters(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    db = FakeDB()
    db.previous_messages = [{"id": 1, "role": "assistant", "content": "Earlier scene", "audio_path": None, "roll_data": None, "resolution_data": None, "applied_delta": None}]
    engine = FakeEngine()
    voice = FakeVoice(None)
    service = AppService(db, engine, voice, str(audio_dir))

    journal = service.get_journal_data(11)

    assert journal["chapters"][0]["summary"] == "The hero answered the call."
    assert journal["messages"][0]["content"] == "Earlier scene"
