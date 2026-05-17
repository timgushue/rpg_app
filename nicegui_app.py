import os

from dotenv import load_dotenv
from nicegui import app, run, ui

from ai.engine import Engine
from ai.prompts import ANCESTRIES, CLASSES, XP_PER_LEVEL
from ai.voice import Voice
from app_service import AppService
from game.dice import format_roll_for_display
from game.game_time import format_time
from storage.database import Database


load_dotenv(override=True)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

db = Database()
db.init()
engine = Engine(db)
voice = Voice()
service = AppService(db, engine, voice, AUDIO_DIR)

app.add_static_files("/audio", AUDIO_DIR)

SETTING_LABELS = {
    "sandpoint": "Sandpoint - Goblin Attack (Rise of the Runelords)",
    "absalom": "Absalom - City at the Center of the World",
    "stolen_lands": "Stolen Lands - Frontier Exploration (Kingmaker)",
    "osirion": "Osirion - Desert Tombs of the Pharaohs",
}


@ui.page("/")
def index() -> None:
    state = service.empty_state()
    env_status = service.get_environment_status()
    form_state = {
        "title": "",
        "setting": "sandpoint",
        "hero_name": "",
        "ancestry": ANCESTRIES[0],
        "hero_class": CLASSES[0],
        "level": 1,
        "traits": "",
        "selected_campaign_label": None,
        "user_input": "",
        "busy_message": None,
    }

    async def with_busy(message: str, func, *args):
        form_state["busy_message"] = message
        render_status.refresh()
        try:
            return await run.io_bound(func, *args)
        finally:
            form_state["busy_message"] = None
            render_status.refresh()

    def active_campaign() -> dict | None:
        return service.get_campaign(state["campaign_id"])

    def apply_active_state(new_state: dict) -> None:
        state.update(new_state)
        render_sidebar.refresh()
        render_main.refresh()

    @ui.refreshable
    def render_status() -> None:
        if env_status["error"]:
            with ui.card().classes("w-full border-l-4 border-red-500 bg-red-50"):
                ui.label(env_status["error"]).classes("text-red-700")
            return

        if env_status["warning"]:
            with ui.card().classes("w-full border-l-4 border-amber-500 bg-amber-50"):
                ui.label(env_status["warning"]).classes("text-amber-800")

        if form_state["busy_message"]:
            with ui.card().classes("w-full bg-slate-100"):
                with ui.row().classes("items-center gap-3"):
                    ui.spinner(size="lg")
                    ui.label(form_state["busy_message"]).classes("text-slate-700")

    @ui.refreshable
    def render_sidebar() -> None:
        with ui.column().classes("w-full gap-4"):
            with ui.card().classes("w-full"):
                ui.label("Pathfinder Quest").classes("text-xl font-bold")

                with ui.expansion("Start New Adventure", value=not state["story_started"]).classes("w-full"):
                    title_input = ui.input("Campaign title", value=form_state["title"])
                    title_input.bind_value(form_state, "title")

                    setting_input = ui.select(
                        options=SETTING_LABELS,
                        value=form_state["setting"],
                        label="Adventure setting",
                    )
                    setting_input.bind_value(form_state, "setting")

                    hero_input = ui.input("Hero name", value=form_state["hero_name"])
                    hero_input.bind_value(form_state, "hero_name")

                    ancestry_input = ui.select(options=ANCESTRIES, value=form_state["ancestry"], label="Ancestry")
                    ancestry_input.bind_value(form_state, "ancestry")

                    class_input = ui.select(options=CLASSES, value=form_state["hero_class"], label="Class")
                    class_input.bind_value(form_state, "hero_class")

                    level_input = ui.number("Level", value=form_state["level"], min=1, max=20, step=1)
                    level_input.bind_value(form_state, "level")

                    traits_input = ui.input("Personality (a few words)", placeholder="brave, curious, honorable")
                    traits_input.bind_value(form_state, "traits")

                    async def start_adventure() -> None:
                        if not form_state["title"].strip() or not form_state["hero_name"].strip():
                            ui.notify("Please fill in Campaign title and Hero name.", type="negative")
                            return

                        try:
                            new_state = await with_busy(
                                "The Game Master prepares the scene...",
                                service.start_new_adventure,
                                form_state["title"].strip(),
                                form_state["setting"],
                                form_state["hero_name"].strip(),
                                form_state["ancestry"],
                                form_state["hero_class"],
                                int(form_state["level"]),
                                form_state["traits"],
                            )
                        except Exception as exc:
                            ui.notify(f"Adventure start failed: {exc}", type="negative")
                            return

                        apply_active_state(new_state)

                    ui.button("Begin Adventure!", on_click=start_adventure).classes("w-full bg-emerald-700 text-white")

                campaign_options = service.list_campaign_options()
                if campaign_options:
                    with ui.expansion("Continue Adventure").classes("w-full"):
                        if form_state["selected_campaign_label"] not in campaign_options:
                            form_state["selected_campaign_label"] = next(iter(campaign_options))

                        continue_input = ui.select(
                            options=list(campaign_options.keys()),
                            value=form_state["selected_campaign_label"],
                            label="Choose campaign",
                        )
                        continue_input.bind_value(form_state, "selected_campaign_label")

                        async def continue_adventure() -> None:
                            selected_label = form_state["selected_campaign_label"]
                            if not selected_label:
                                ui.notify("Choose a campaign first.", type="negative")
                                return

                            try:
                                new_state = await with_busy(
                                    "The Game Master sets the scene...",
                                    service.continue_adventure,
                                    int(campaign_options[selected_label]),
                                )
                            except Exception as exc:
                                ui.notify(f"Continue failed: {exc}", type="negative")
                                return

                            apply_active_state(new_state)

                        ui.button("Continue", on_click=continue_adventure).classes("w-full")

            if state["story_started"] and state["campaign_id"]:
                campaign = active_campaign()
                if campaign:
                    hero = campaign["hero_sheet"]
                    world = campaign["world_state"]

                    with ui.card().classes("w-full"):
                        ui.label("Character Sheet").classes("text-sm uppercase tracking-wide text-slate-500")
                        ui.label(campaign["hero_name"]).classes("text-lg font-semibold")
                        ui.label(f"Level {hero.get('level', 1)} {hero.get('ancestry', '')} {hero.get('class', '')}")

                        time_state = world.get("time", {})
                        if time_state:
                            ui.label(format_time(time_state)).classes("text-sm text-slate-500")

                        hp = hero.get("hp", 0)
                        max_hp = max(hero.get("max_hp", 1), 1)
                        ui.linear_progress(value=hp / max_hp, show_value=False).classes("w-full")
                        ui.label(f"HP {hp} / {max_hp}").classes("text-sm")

                        xp = hero.get("xp", 0)
                        ui.linear_progress(value=min(xp / XP_PER_LEVEL, 1), show_value=False).classes("w-full")
                        ui.label(f"XP {xp} / {XP_PER_LEVEL} (Level {hero.get('level', 1)})").classes("text-sm")

                        ui.label(f"Gold: {hero.get('gold', 0)} gp").classes("text-sm")

                        scores = hero.get("ability_scores", {})
                        if scores:
                            with ui.expansion("Ability Scores").classes("w-full"):
                                labels = {
                                    "strength": "STR",
                                    "dexterity": "DEX",
                                    "constitution": "CON",
                                    "intelligence": "INT",
                                    "wisdom": "WIS",
                                    "charisma": "CHA",
                                }
                                for ability, short in labels.items():
                                    val = scores.get(ability, 10)
                                    mod = (val - 10) // 2
                                    mod_str = f"+{mod}" if mod >= 0 else str(mod)
                                    ui.label(f"{short} {val} ({mod_str})").classes("text-sm")

                        for level, slot_data in hero.get("spell_slots", {}).items():
                            rem = slot_data["remaining"]
                            max_slots = slot_data["max"]
                            ui.label(f"Spell slots Lv{level}: {'◆' * rem}{'◇' * (max_slots - rem)}").classes("text-sm")

                        focus_points = hero.get("focus_points", {})
                        if focus_points.get("max", 0) > 0:
                            rem = focus_points["remaining"]
                            max_points = focus_points["max"]
                            ui.label(f"Focus points: {'◆' * rem}{'◇' * (max_points - rem)}").classes("text-sm")

                        inventory = hero.get("inventory", [])
                        if inventory:
                            with ui.expansion("Inventory").classes("w-full"):
                                for item in inventory:
                                    if isinstance(item, dict):
                                        qty = item["quantity"]
                                        label = f"{item['name']} x{qty}" if qty != 1 else item["name"]
                                    else:
                                        label = item
                                    ui.label(label).classes("text-sm")

                        async def end_session() -> None:
                            try:
                                await with_busy(
                                    "Saving chapter...",
                                    service.end_session,
                                    state["campaign_id"],
                                    state["session_id"],
                                )
                            except Exception as exc:
                                ui.notify(f"Chapter save failed: {exc}", type="negative")
                                return

                            state.update(service.empty_state())
                            render_sidebar.refresh()
                            render_main.refresh()
                            ui.notify("Chapter saved!", type="positive")

                        ui.button("End Session & Save Chapter", on_click=end_session).classes("w-full")

    @ui.refreshable
    def render_main() -> None:
        with ui.column().classes("w-full gap-4"):
            with ui.card().classes("w-full"):
                ui.label("Pathfinder Quest").classes("text-3xl font-bold")
                if not state["story_started"]:
                    ui.label(
                        "Welcome to Golarion, adventurer! Create your hero and begin your Pathfinder journey from the sidebar."
                    ).classes("text-base text-slate-600")
                    return

                last_index = len(state["messages"]) - 1
                for index, message in enumerate(state["messages"]):
                    bubble_classes = "bg-emerald-50 border-emerald-200 self-end" if message["role"] == "user" else "bg-slate-50"
                    with ui.card().classes(f"w-full border {bubble_classes}"):
                        ui.label("Hero" if message["role"] == "user" else "Narrator").classes("text-xs uppercase tracking-wide text-slate-500")
                        ui.markdown(message["content"])
                        if message.get("roll_data"):
                            ui.markdown(format_roll_for_display(message["roll_data"])).classes("text-sm")
                        if message.get("audio_url"):
                            player = ui.audio(message["audio_url"], autoplay=(index == last_index))
                            player.props("controls")

                if state["latest_roll"]:
                    with ui.card().classes("w-full bg-amber-50"):
                        ui.markdown(format_roll_for_display(state["latest_roll"]))

                user_input = ui.textarea(
                    label="What do you do?",
                    placeholder="I draw my sword and charge at the goblin!",
                    value=form_state["user_input"],
                ).classes("w-full")
                user_input.bind_value(form_state, "user_input")

                async def submit_turn() -> None:
                    if not form_state["user_input"].strip():
                        return

                    try:
                        result = await with_busy(
                            "The Game Master narrates...",
                            service.submit_turn,
                            state["campaign_id"],
                            state["session_id"],
                            form_state["user_input"].strip(),
                        )
                    except Exception as exc:
                        ui.notify(f"Story generation failed: {exc}", type="negative")
                        return

                    state["messages"].extend(result["messages"])
                    state["latest_audio_path"] = result["latest_audio_path"]
                    state["latest_roll"] = result["latest_roll"]
                    form_state["user_input"] = ""
                    render_sidebar.refresh()
                    render_main.refresh()

                ui.button("Send", on_click=submit_turn).classes("bg-sky-700 text-white")

    with ui.column().classes("w-full max-w-7xl mx-auto gap-4 p-4"):
        render_status()
        with ui.row().classes("w-full items-start gap-4 max-md:flex-col"):
            with ui.column().classes("w-full md:max-w-sm"):
                render_sidebar()
            with ui.column().classes("w-full flex-1"):
                render_main()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Pathfinder Quest", storage_secret="pathfinder-quest-local", reload=False)
