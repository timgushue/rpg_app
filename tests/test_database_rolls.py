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
    )

    messages = db.get_session_messages(session_id)

    assert messages[0]["roll_data"]["skill"] == "Attack"
    assert messages[0]["roll_data"]["total"] == 21
