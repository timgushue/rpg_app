import os
from dotenv import load_dotenv

load_dotenv(override=True)

import streamlit as st

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")

from storage.database import Database
from ai.engine import Engine
from ai.voice import Voice
from ai.prompts import ANCESTRIES, CLASSES, ADVENTURE_STARTERS, XP_PER_LEVEL
from game.dice import format_roll_for_display
from game.game_time import format_time

st.set_page_config(
    page_title="Pathfinder Quest",
    page_icon="⚔️",
    layout="wide",
)

# --- Validate keys ---
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")
    st.stop()

if not os.environ.get("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY is not set. The app will run in text-only mode (no audio).")

# --- Init singletons ---
db = Database()
db.init()
engine = Engine(db)
voice = Voice()

# --- Session state defaults ---
if "campaign_id" not in st.session_state:
    st.session_state.campaign_id = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "story_started" not in st.session_state:
    st.session_state.story_started = False
if "latest_audio_path" not in st.session_state:
    st.session_state.latest_audio_path = None
if "latest_roll" not in st.session_state:
    st.session_state.latest_roll = None

# --- Sidebar ---
with st.sidebar:
    st.header("⚔️ Pathfinder Quest")

    # Start new adventure
    with st.expander("Start New Adventure", expanded=not st.session_state.story_started):
        new_title = st.text_input("Campaign title", key="new_title")

        setting_labels = {
            "sandpoint": "Sandpoint — Goblin Attack (Rise of the Runelords)",
            "absalom": "Absalom — City at the Center of the World",
            "stolen_lands": "Stolen Lands — Frontier Exploration (Kingmaker)",
            "osirion": "Osirion — Desert Tombs of the Pharaohs",
        }
        new_setting = st.selectbox(
            "Adventure setting",
            list(setting_labels.keys()),
            format_func=lambda k: setting_labels[k],
            key="new_setting",
        )

        new_hero = st.text_input("Hero name", key="new_hero")
        new_ancestry = st.selectbox("Ancestry", ANCESTRIES, key="new_ancestry")
        new_class = st.selectbox("Class", CLASSES, key="new_class")
        new_level = st.number_input("Level", min_value=1, max_value=20, value=1, key="new_level")
        new_traits = st.text_input(
            "Personality (a few words)",
            placeholder="e.g. brave, curious, honorable",
            key="new_traits",
        )

        if st.button("Begin Adventure!", key="btn_begin"):
            if not new_title or not new_hero:
                st.error("Please fill in Campaign title and Hero name.")
            else:
                traits = [t.strip() for t in new_traits.split(",") if t.strip()]
                with st.spinner("The Game Master prepares the scene..."):
                    campaign_id = engine.start_campaign(
                        title=new_title,
                        adventure_setting=new_setting,
                        hero_name=new_hero,
                        ancestry=new_ancestry,
                        hero_class=new_class,
                        level=int(new_level),
                        traits=traits,
                    )
                    session_id = db.create_session(campaign_id)
                    beat, msg_id = engine.generate_opening_scene(campaign_id, session_id, is_new=True)
                    audio_path = voice.speak_to_persistent_file(beat, msg_id, AUDIO_DIR)
                    if audio_path:
                        db.update_message_audio(msg_id, audio_path)

                st.session_state.campaign_id = campaign_id
                st.session_state.session_id = session_id
                st.session_state.messages = [{"role": "assistant", "content": beat, "audio_path": audio_path, "id": msg_id}]
                st.session_state.story_started = True
                st.session_state.latest_audio_path = audio_path
                st.rerun()

    # Continue adventure
    campaigns = db.list_campaigns()
    if campaigns:
        with st.expander("Continue Adventure"):
            campaign_options = {f"{c['title']} — {c['genre']}": c["id"] for c in campaigns}
            selected_label = st.selectbox("Choose campaign", list(campaign_options.keys()), key="sel_campaign")

            if st.button("Continue", key="btn_continue"):
                campaign_id = campaign_options[selected_label]

                # Load all past messages for display (with their saved audio paths)
                prev_session = db.get_latest_session(campaign_id)
                past_messages = db.get_session_messages(prev_session["id"]) if prev_session else []

                session_id = db.create_session(campaign_id)

                with st.spinner("The Game Master sets the scene..."):
                    recap, msg_id = engine.generate_opening_scene(campaign_id, session_id, is_new=False)
                    audio_path = voice.speak_to_persistent_file(recap, msg_id, AUDIO_DIR)
                    if audio_path:
                        db.update_message_audio(msg_id, audio_path)

                st.session_state.campaign_id = campaign_id
                st.session_state.session_id = session_id
                st.session_state.messages = past_messages + [{"role": "assistant", "content": recap, "audio_path": audio_path, "id": msg_id}]
                st.session_state.story_started = True
                st.session_state.latest_audio_path = audio_path
                st.rerun()

    # Character sheet panel
    if st.session_state.story_started and st.session_state.campaign_id:
        st.divider()
        campaign = db.get_campaign(st.session_state.campaign_id)
        if campaign:
            hero = campaign["hero_sheet"]
            world = campaign["world_state"]

            st.caption("CHARACTER SHEET")

            # Identity
            hero_ancestry = hero.get("ancestry", "")
            hero_class    = hero.get("class", "")
            hero_level    = hero.get("level", 1)
            st.caption(f"**{campaign['hero_name']}**")
            st.caption(f"Level {hero_level}  {hero_ancestry}  {hero_class}")

            # Time
            time_state = world.get("time", {})
            if time_state:
                st.caption(format_time(time_state))

            # HP and XP bars
            hp = hero.get("hp", 0)
            max_hp = hero.get("max_hp", 1)
            st.progress(hp / max_hp, text=f"HP  {hp} / {max_hp}")

            xp = hero.get("xp", 0)
            st.progress(xp / XP_PER_LEVEL, text=f"XP  {xp} / {XP_PER_LEVEL}  (Level {hero_level})")

            gold = hero.get("gold", 0)
            st.caption(f"💰 {gold} gp")

            # Ability scores
            scores = hero.get("ability_scores", {})
            if scores:
                with st.expander("Ability Scores", expanded=False):
                    labels = {
                        "strength": "STR", "dexterity": "DEX", "constitution": "CON",
                        "intelligence": "INT", "wisdom": "WIS", "charisma": "CHA",
                    }
                    for ability, short in labels.items():
                        val = scores.get(ability, 10)
                        mod = (val - 10) // 2
                        mod_str = f"+{mod}" if mod >= 0 else str(mod)
                        st.caption(f"{short}  {val}  ({mod_str})")

            # Spell slots
            spell_slots = hero.get("spell_slots", {})
            for lvl, data in spell_slots.items():
                rem = data["remaining"]
                mx = data["max"]
                filled = "◆" * rem + "◇" * (mx - rem)
                st.caption(f"Spell slots Lv{lvl}  {filled}")

            # Focus points
            fp = hero.get("focus_points", {})
            if fp.get("max", 0) > 0:
                rem = fp["remaining"]
                mx = fp["max"]
                filled = "◆" * rem + "◇" * (mx - rem)
                st.caption(f"Focus points  {filled}")

            # Inventory
            inventory = hero.get("inventory", [])
            if inventory:
                with st.expander("Inventory", expanded=False):
                    for item in inventory:
                        if isinstance(item, dict):
                            qty = item["quantity"]
                            label = f"{item['name']}  ×{qty}" if qty != 1 else item["name"]
                        else:
                            label = item
                        st.write(label)

    # End session
    if st.session_state.story_started:
        st.divider()
        if st.button("End Session & Save Chapter", key="btn_end"):
            with st.spinner("Saving chapter..."):
                engine.summarize_session(
                    st.session_state.campaign_id,
                    st.session_state.session_id,
                )
            st.toast("Chapter saved!")
            st.session_state.campaign_id = None
            st.session_state.session_id = None
            st.session_state.messages = []
            st.session_state.story_started = False
            st.session_state.latest_audio_path = None
            st.session_state.latest_roll = None
            st.rerun()

# --- Main area ---
st.title("⚔️ Pathfinder Quest")

if not st.session_state.story_started:
    st.markdown(
        "Welcome to Golarion, adventurer! Create your hero and begin your Pathfinder journey from the sidebar."
    )
else:
    # Render chat history — autoplay only on the last message
    last_idx = len(st.session_state.messages) - 1
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            audio_path = msg.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                with open(audio_path, "rb") as f:
                    st.audio(f.read(), format="audio/mp3", autoplay=(i == last_idx))

    # Dice roll result
    if st.session_state.latest_roll:
        st.markdown(format_roll_for_display(st.session_state.latest_roll))

    # Chat input
    user_input = st.chat_input("What do you do?")
    if user_input:
        with st.spinner("The Game Master narrates..."):
            try:
                beat, roll, msg_id = engine.generate_story_beat(
                    st.session_state.campaign_id,
                    st.session_state.session_id,
                    user_input,
                )
                audio_path = voice.speak_to_persistent_file(beat, msg_id, AUDIO_DIR)
                if audio_path:
                    db.update_message_audio(msg_id, audio_path)
            except Exception as e:
                st.error(f"Story generation failed: {e}")
                st.stop()

        st.session_state.messages.append({"role": "user", "content": user_input, "audio_path": None})
        st.session_state.messages.append({"role": "assistant", "content": beat, "audio_path": audio_path, "id": msg_id})
        st.session_state.latest_audio_path = audio_path
        st.session_state.latest_roll = roll
        st.rerun()
