import storage.database as database_module


def test_save_message_round_trips_roll_data(tmp_path):
    database_module.DB_PATH = str(tmp_path / "stories.db")
    db = database_module.Database()
    db.init()

    campaign_id = db.create_campaign(
        title="Goblin Menace",
        genre="sandpoint",
        hero_name="Pip",
        hero_sheet={"class": "Fighter", "ancestry": "Human", "ability_scores": {"strength": 10}},
        world_state={"setting": "", "time": {}},
    )
    session_id = db.create_session(campaign_id)

    db.save_message(
        session_id,
        "assistant",
        "The goblin stumbles back.",
        roll_data={"skill": "Attack", "roll": 17, "modifier": 4, "total": 21, "dc": 15, "degree": "success"},
        resolution_data={"narration_cue": "The goblin is forced back."},
        applied_delta={"xp_change": 20},
        scene_title="Goblin Driven Back",
    )

    messages = db.get_session_messages(session_id)

    assert messages[0]["roll_data"]["skill"] == "Attack"
    assert messages[0]["roll_data"]["total"] == 21
    assert messages[0]["resolution_data"]["narration_cue"] == "The goblin is forced back."
    assert messages[0]["applied_delta"]["xp_change"] == 20
    assert messages[0]["scene_title"] == "Goblin Driven Back"


def test_campaign_round_trips_story_state(tmp_path):
    database_module.DB_PATH = str(tmp_path / "stories.db")
    db = database_module.Database()
    db.init()

    campaign_id = db.create_campaign(
        title="Goblin Menace",
        genre="sandpoint",
        hero_name="Pip",
        hero_sheet={"class": "Fighter", "ancestry": "Human", "ability_scores": {"strength": 10}},
        world_state={"setting": "", "time": {}},
        story_state={"title": "Arc Title", "acts": [], "current_act_id": "", "current_beat_id": ""},
    )

    campaign = db.get_campaign(campaign_id)

    assert campaign["story_state"]["title"] == "Arc Title"


def test_campaign_without_story_state_stays_missing_until_runtime_generation(tmp_path):
    database_module.DB_PATH = str(tmp_path / "stories.db")
    db = database_module.Database()
    db.init()

    campaign_id = db.create_campaign(
        title="Goblin Menace",
        genre="sandpoint",
        hero_name="Pip",
        hero_sheet={"class": "Fighter", "ancestry": "Human", "ability_scores": {"strength": 10}},
        world_state={"setting": "", "time": {}},
        story_state=None,
    )

    campaign = db.get_campaign(campaign_id)

    assert campaign["story_state"] is None


def test_get_campaign_messages_returns_messages_across_sessions(tmp_path):
    database_module.DB_PATH = str(tmp_path / "stories.db")
    db = database_module.Database()
    db.init()

    campaign_id = db.create_campaign(
        title="Goblin Menace",
        genre="sandpoint",
        hero_name="Pip",
        hero_sheet={"class": "Fighter", "ancestry": "Human", "ability_scores": {"strength": 10}},
        world_state={"setting": "", "time": {}},
        story_state=None,
    )
    session_1 = db.create_session(campaign_id)
    db.save_message(session_1, "assistant", "Opening scene")
    session_2 = db.create_session(campaign_id)
    db.save_message(session_2, "user", "I search the room.")

    messages = db.get_campaign_messages(campaign_id)

    assert [message["content"] for message in messages] == ["Opening scene", "I search the room."]


def test_delete_campaign_removes_sessions_and_messages(tmp_path):
    database_module.DB_PATH = str(tmp_path / "stories.db")
    db = database_module.Database()
    db.init()

    campaign_id = db.create_campaign(
        title="Goblin Menace",
        genre="sandpoint",
        hero_name="Pip",
        hero_sheet={"class": "Fighter", "ancestry": "Human", "ability_scores": {"strength": 10}},
        world_state={"setting": "", "time": {}},
        story_state=None,
    )
    session_id = db.create_session(campaign_id)
    db.save_message(session_id, "assistant", "Opening scene")

    assert db.delete_campaign(campaign_id) is True
    assert db.get_campaign(campaign_id) is None
    assert db.get_session_messages(session_id) == []
    assert db.delete_campaign(campaign_id) is False
