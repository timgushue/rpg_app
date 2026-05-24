import asyncio
import json
import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv
from fastapi import Request
from nicegui import app, run, ui

from ai.engine import Engine
from ai.prompts import ANCESTRIES, CLASSES, XP_PER_LEVEL
from ai.voice import Voice
from app_service import AppService
from game.character import build_ability_scores
from game.dice import CLASS_TRAINED_SKILLS, PROFICIENCY_BONUS, SKILL_TO_ABILITY, get_modifier
from game.game_data import CLASS_HP_PER_LEVEL, CLASS_STARTING_GEAR, CLASS_STARTING_GOLD
from storage.database import Database
from ui_kit import ABILITY_LABELS, icon_html, inject_inkwell_theme, ornamental_rule, roll_banner_html


load_dotenv(override=True)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
UI_ASSET_DIR = os.path.join(os.path.dirname(__file__), "ui_kit")
LOG_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "nicegui_app.log")),
    ],
)
logger = logging.getLogger(__name__)

db = Database()
db.init()
engine = Engine(db)
voice = Voice()
service = AppService(db, engine, voice, AUDIO_DIR)

app.add_static_files("/audio", AUDIO_DIR)
app.add_static_files("/ui_assets", UI_ASSET_DIR)


@app.post("/client-error")
async def client_error(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        payload = {"error": "client error payload was not valid JSON"}
    logger.error("Client-side error: %s", json.dumps(payload, default=str)[:4000])
    return {"ok": True}


SETTING_LABELS = {
    "fresh_story": "Fresh Story Arc",
    "sandpoint": "Sandpoint - Goblin Attack",
    "absalom": "Absalom - City at the Center of the World",
    "stolen_lands": "Stolen Lands - Frontier Exploration",
    "osirion": "Osirion - Desert Tombs of the Pharaohs",
}

ABILITY_OPTIONS = list(ABILITY_LABELS.keys())


def numeric_ability_modifier(score: object) -> int:
    try:
        numeric_score = int(score)
    except (TypeError, ValueError):
        numeric_score = 10
    return (numeric_score - 10) // 2


def signed_modifier(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def signed_modifier_from_value(value: object) -> str:
    if isinstance(value, bool):
        return ""
    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return ""
    return signed_modifier(numeric_value)


def ability_modifier(score: int) -> str:
    modifier = numeric_ability_modifier(score)
    return f"+{modifier}" if modifier >= 0 else str(modifier)


def character_effect_labels(hero: dict) -> list[str]:
    effect_values = []
    for key in ("active_buffs", "buffs", "effects", "conditions"):
        value = hero.get(key)
        if isinstance(value, list):
            effect_values.extend(value)
        elif isinstance(value, dict):
            for effect_name, effect in value.items():
                if isinstance(effect, dict):
                    normalized_effect = dict(effect)
                    normalized_effect.setdefault("name", effect_name)
                    effect_values.append(normalized_effect)
                else:
                    effect_values.append({"name": effect_name, "description": effect})

    labels = []
    for effect in effect_values:
        if isinstance(effect, str):
            label = effect.strip()
        elif isinstance(effect, dict):
            name = str(effect.get("name") or effect.get("title") or effect.get("condition") or "").strip()
            bonus = effect.get("modifier", effect.get("bonus"))
            duration = str(effect.get("duration") or "").strip()
            description = str(effect.get("description") or effect.get("effect") or "").strip()
            parts = [part for part in [name, signed_modifier_from_value(bonus), duration, description] if part]
            label = " - ".join(parts)
        else:
            label = str(effect).strip()
        if label:
            labels.append(label)
    return labels


def skill_modifier_rows(hero: dict) -> list[dict]:
    scores = hero.get("ability_scores", {})
    trained_skills = set(CLASS_TRAINED_SKILLS.get(hero.get("class", ""), []))
    rows = []
    for skill in sorted(SKILL_TO_ABILITY):
        ability = SKILL_TO_ABILITY[skill]
        ability_mod = numeric_ability_modifier(scores.get(ability, 10))
        trained_bonus = PROFICIENCY_BONUS if skill in trained_skills else 0
        rows.append(
            {
                "skill": skill,
                "ability": ability,
                "ability_mod": ability_mod,
                "trained": skill in trained_skills,
                "trained_bonus": trained_bonus,
                "total": get_modifier(hero, skill),
            }
        )
    return rows


def inventory_label(item) -> str:
    if isinstance(item, dict):
        quantity = int(item.get("quantity", 1))
        name = item.get("name", "Unknown item")
        return f"{name} x{quantity}" if quantity != 1 else name
    return str(item)


def inventory_count(items: list) -> int:
    total = 0
    for item in items:
        if isinstance(item, dict):
            total += max(0, int(item.get("quantity", 1)))
        else:
            total += 1
    return total


def nice_setting_label(setting_key: str) -> str:
    return SETTING_LABELS.get(setting_key, setting_key.replace("_", " ").title())


def story_message_label(message: dict) -> str:
    return "You" if message["role"] == "user" else "Narrator"


def scene_title_for_message(message: Optional[dict]) -> str:
    if not message:
        return "A new scene opens"
    persisted_title = (message.get("scene_title") or "").strip()
    if persisted_title:
        return persisted_title
    content = " ".join((message.get("content") or "").split())
    if not content:
        return "A new scene opens"
    first_clause = re.split(r"[.!?;:—-]", content, maxsplit=1)[0].strip()
    words = first_clause.split()[:6]
    return " ".join(words).strip(" ,") or "A new scene opens"


def public_objective_label(summary: dict) -> str:
    return summary.get("objective") or summary.get("plot_so_far") or "Follow the newest lead."


@ui.page("/")
def index(request: Request) -> None:
    inject_inkwell_theme()
    state = service.empty_state()
    env_status = service.get_environment_status()
    ui_state = {
        "screen": "landing",
        "drawer_open": True,
        "busy_message": None,
        "debug_mode": request.query_params.get("debug") == "1",
        "show_roll_overlay": False,
        "pending_level_up": None,
        "user_input": "",
        "audio_pending_message_ids": set(),
        "audio_failed_message_ids": set(),
        "scene_text_pending_message_ids": set(),
        "show_character_stats": False,
        "opening_error": None,
    }
    form_state = {
        "title": "",
        "setting": "sandpoint",
        "hero_name": "",
        "ancestry": ANCESTRIES[0],
        "hero_class": CLASSES[0],
        "level": 1,
        "traits": "",
        "fresh_story_arc": False,
    }
    initial_campaign_id = request.query_params.get("campaign_id")
    initial_session_id = request.query_params.get("session_id")
    if initial_campaign_id and initial_session_id:
        try:
            state.update(service.load_active_session(int(initial_campaign_id), int(initial_session_id)))
            ui_state["screen"] = "game"
        except Exception:
            state.update(service.empty_state())
    elif initial_campaign_id:
        try:
            state.update(service.resume_adventure(int(initial_campaign_id)))
            ui_state["screen"] = "game"
        except Exception:
            state.update(service.empty_state())

    def active_campaign() -> Optional[dict]:
        ensure_story_state = bool(state.get("messages"))
        return service.get_campaign(state["campaign_id"], ensure_story_state=ensure_story_state)

    def current_story_summary() -> dict:
        return service.story_summary(active_campaign())

    def current_hero() -> dict:
        campaign = active_campaign()
        return campaign["hero_sheet"] if campaign else {}

    def creator_preview_hero() -> dict:
        hero_class = form_state["hero_class"]
        ancestry = form_state["ancestry"]
        max_hp = CLASS_HP_PER_LEVEL.get(hero_class, 8) + 8
        return {
            "ability_scores": build_ability_scores(ancestry, hero_class),
            "hp": max_hp,
            "max_hp": max_hp,
            "gold": CLASS_STARTING_GOLD.get(hero_class, 10),
            "inventory": [
                {"name": name, "quantity": qty}
                for name, qty in CLASS_STARTING_GEAR.get(hero_class, [("adventurer's kit", 1)])
            ],
        }

    def select_setting(choice: str) -> None:
        form_state["setting"] = choice
        form_state["fresh_story_arc"] = False
        render_creator.refresh()
        render_landing.refresh()

    def select_fresh_story_arc() -> None:
        form_state["setting"] = "fresh_story"
        form_state["fresh_story_arc"] = True
        render_landing.refresh()

    def select_ancestry(choice: str) -> None:
        form_state["ancestry"] = choice
        render_creator.refresh()

    def select_hero_class(choice: str) -> None:
        form_state["hero_class"] = choice
        render_creator.refresh()

    def active_journal_url() -> str:
        if not state["campaign_id"]:
            return "/journal"
        url = f"/journal?campaign_id={state['campaign_id']}"
        if state.get("session_id"):
            url += f"&session_id={state['session_id']}"
        if ui_state["debug_mode"]:
            url += "&debug=1"
        return url

    def refresh_all() -> None:
        render_status.refresh()
        render_topbar.refresh()
        render_landing.refresh()
        render_creator.refresh()
        render_main_game.refresh()
        render_level_up_dialog.refresh()
        render_dice_dialog.refresh()

    def set_screen(screen: str) -> None:
        ui_state["screen"] = screen
        refresh_all()

    def refresh_busy_indicator() -> None:
        if ui_state["screen"] == "game" and state["story_started"]:
            render_main_game.refresh()
        elif ui_state["screen"] == "create":
            render_creator.refresh()
        else:
            render_status.refresh()

    async def with_busy(message: str, func, *args):
        ui_state["busy_message"] = message
        refresh_busy_indicator()
        try:
            return await run.io_bound(func, *args)
        finally:
            ui_state["busy_message"] = None
            refresh_busy_indicator()

    def open_roll_overlay() -> None:
        if not state.get("latest_roll"):
            return
        ui_state["show_roll_overlay"] = True
        render_dice_dialog.refresh()
        dice_dialog.open()

    def close_roll_overlay() -> None:
        ui_state["show_roll_overlay"] = False
        dice_dialog.close()

    def open_level_up_dialog() -> None:
        render_level_up_dialog.refresh()
        level_up_dialog.open()

    def apply_active_state(new_state: dict) -> None:
        state.update(new_state)
        ui_state["screen"] = "game"
        latest_delta = new_state.get("latest_applied_delta")
        ui_state["pending_level_up"] = latest_delta if latest_delta and latest_delta.get("level_up") else None
        refresh_all()
        if new_state.get("latest_roll") and new_state["latest_roll"].get("dc", 0):
            open_roll_overlay()
        if ui_state["pending_level_up"]:
            open_level_up_dialog()

    async def start_adventure() -> None:
        if env_status["error"]:
            return
        if ui_state["busy_message"]:
            return
        if not form_state["title"].strip() or not form_state["hero_name"].strip():
            ui.notify("Campaign title and hero name are required.", type="negative")
            return
        try:
            new_state = await run.io_bound(
                service.create_new_adventure_shell,
                form_state["title"].strip(),
                form_state["setting"],
                form_state["hero_name"].strip(),
                form_state["ancestry"],
                form_state["hero_class"],
                int(form_state["level"]),
                form_state["traits"],
                None,
            )
        except Exception as exc:
            logger.exception("Adventure shell creation failed")
            ui.notify(f"Adventure start failed: {exc}", type="negative")
            return
        ui_state["opening_error"] = None
        ui_state["busy_message"] = "The Game Master inks the opening chapter..."
        apply_active_state(new_state)
        await asyncio.sleep(0.1)
        try:
            opening_state = await run.io_bound(
                service.generate_initial_scene,
                new_state["campaign_id"],
                new_state["session_id"],
            )
        except Exception as exc:
            logger.exception(
                "Opening scene generation failed for campaign %s session %s",
                new_state["campaign_id"],
                new_state["session_id"],
            )
            ui_state["opening_error"] = f"Opening scene failed: {exc}"
            ui_state["busy_message"] = None
            refresh_all()
            return

        state["messages"].extend(opening_state["messages"])
        state["latest_audio_path"] = opening_state["latest_audio_path"]
        ui_state["busy_message"] = None
        refresh_all()

    async def continue_adventure(campaign_id: int) -> None:
        if env_status["error"]:
            return
        try:
            new_state = await run.io_bound(service.resume_adventure, campaign_id)
        except Exception as exc:
            logger.exception("Continue failed while resuming campaign %s", campaign_id)
            ui.notify(f"Continue failed: {exc}", type="negative")
            return
        apply_active_state(new_state)
        if not new_state.get("needs_recap"):
            return

        ui_state["busy_message"] = "The Game Master reopens the tome..."
        refresh_all()
        try:
            recap_state = await run.io_bound(service.generate_continue_recap, campaign_id, new_state["session_id"])
        except Exception as exc:
            logger.exception("Continue failed while generating recap for campaign %s", campaign_id)
            ui.notify(f"Continue failed: {exc}", type="negative")
            return
        finally:
            ui_state["busy_message"] = None
            refresh_all()

        state["messages"].extend(recap_state["messages"])
        state["latest_audio_path"] = recap_state["latest_audio_path"]
        state["needs_recap"] = False
        refresh_all()

    def open_delete_campaign(campaign: dict) -> None:
        target = {"id": int(campaign["id"]), "title": str(campaign["title"])}

        async def confirm_delete() -> None:
            dialog.close()
            try:
                deleted = await run.io_bound(service.delete_campaign, target["id"])
            except Exception as exc:
                logger.exception("Campaign delete failed for %s", target)
                ui.notify(f"Delete failed: {exc}", type="negative")
                return
            if not deleted:
                ui.notify("Campaign was already gone.", type="warning")
            else:
                ui.notify("Campaign deleted.", type="positive")
            if state.get("campaign_id") == target["id"]:
                state.update(service.empty_state())
                ui_state["screen"] = "landing"
            refresh_all()

        with ui.dialog().props("persistent seamless") as dialog:
            with ui.element("div").classes("ink ink-sheet ink-paper ink-overlay-card").style(
                "padding:24px;max-width:420px;background:var(--paper-0, #f7f1e6);"
                "color:var(--ink-1, #332820);border:1px solid var(--paper-edge, #b9a17f);"
                "box-shadow:0 18px 48px rgba(32,22,12,.36),0 2px 0 rgba(255,255,255,.5) inset;"
            ):
                ui.label("Delete Chronicle").classes("ink-stamp")
                ui.label(target["title"]).classes("ink-display").style("font-size:28px;margin:4px 0 0;overflow-wrap:anywhere;")
                ui.label("This removes the campaign, its sessions, journal beats, rolls, and generated narration audio.").style(
                    "font-size:14px;color:var(--ink-2);margin-top:8px;line-height:1.45;"
                )
                ui.label("Keep this chronicle?").style("font-size:13px;color:var(--ink-3);margin-top:14px;font-style:italic;")
                with ui.row().classes("w-full justify-end gap-2").style("margin-top:18px;"):
                    ui.button("No, Keep It", on_click=dialog.close).props("flat no-caps autofocus").classes("ink-btn").style(
                        "padding:7px 12px;font-size:12px;"
                    )
                    ui.button("Yes, Delete", on_click=confirm_delete).props("flat no-caps").classes("ink-btn ink-btn-ghost").style(
                        "padding:7px 12px;font-size:12px;color:var(--ember-deep) !important;border-color:var(--ember-deep) !important;"
                    )
        dialog.open()

    async def submit_turn() -> None:
        if not ui_state["user_input"].strip():
            return
        if ui_state["busy_message"]:
            return
        if not state["campaign_id"] or not state["session_id"]:
            ui.notify("Start or continue a campaign first.", type="negative")
            return
        try:
            result = await with_busy(
                "The Game Master considers your move...",
                service.submit_turn,
                state["campaign_id"],
                state["session_id"],
                ui_state["user_input"].strip(),
            )
        except Exception as exc:
            logger.exception("Story generation failed for campaign %s session %s", state["campaign_id"], state["session_id"])
            ui.notify(f"Story generation failed: {exc}", type="negative")
            return

        async def generate_audio_after_render(message_id: int, text: str) -> None:
            try:
                audio_result = await run.io_bound(service.generate_audio_for_message, message_id, text)
                ui_state["audio_pending_message_ids"].discard(message_id)
                if not audio_result:
                    ui_state["audio_failed_message_ids"].add(message_id)
                    refresh_all()
                    return
                ui_state["audio_failed_message_ids"].discard(message_id)
                state["latest_audio_path"] = audio_result["audio_path"]
                for message in state["messages"]:
                    if message.get("id") == audio_result["message_id"]:
                        message["audio_path"] = audio_result["audio_path"]
                        message["audio_url"] = audio_result["audio_url"]
                        break
                refresh_all()
            except Exception:
                logger.exception("Audio generation or UI audio update failed for message %s", message_id)
                ui_state["audio_pending_message_ids"].discard(message_id)
                ui_state["audio_failed_message_ids"].add(message_id)

        async def reveal_scene_text_after_delay(message_id: int) -> None:
            await asyncio.sleep(1)
            ui_state["scene_text_pending_message_ids"].discard(message_id)
            refresh_all()
            if ui_state["pending_level_up"]:
                open_level_up_dialog()

        try:
            state["messages"].extend(result["messages"])
            state["messages"] = state["messages"][-24:]
            state["latest_audio_path"] = result["latest_audio_path"]
            state["latest_roll"] = result["latest_roll"]
            state["latest_resolution_data"] = result.get("latest_resolution_data")
            state["latest_applied_delta"] = result.get("latest_applied_delta")
            ui_state["user_input"] = ""
            latest_delta = result.get("latest_applied_delta") or {}
            ui_state["pending_level_up"] = latest_delta if latest_delta.get("level_up") else None
            if result.get("message_id") and result.get("story_beat"):
                ui_state["scene_text_pending_message_ids"].add(result["message_id"])
                ui_state["audio_pending_message_ids"].add(result["message_id"])
            refresh_all()
            if result.get("message_id") and result.get("story_beat"):
                asyncio.create_task(reveal_scene_text_after_delay(result["message_id"]))
                asyncio.create_task(generate_audio_after_render(result["message_id"], result["story_beat"]))
            elif ui_state["pending_level_up"]:
                open_level_up_dialog()
        except Exception as exc:
            logger.exception("Post-submit UI update failed for campaign %s session %s", state["campaign_id"], state["session_id"])
            ui.notify(f"UI update failed: {exc}", type="negative")

    async def end_session() -> None:
        if not state["campaign_id"] or not state["session_id"]:
            return
        try:
            summary = await with_busy("Saving chapter to the journal...", service.end_session, state["campaign_id"], state["session_id"])
        except Exception as exc:
            ui.notify(f"Chapter save failed: {exc}", type="negative")
            return
        if summary == "No new player actions to summarize.":
            ui.notify("No new actions to save.", type="info")
        else:
            ui.notify("Chapter saved.", type="positive")
        state.update(service.empty_state())
        ui_state["screen"] = "landing"
        ui_state["pending_level_up"] = None
        ui_state["user_input"] = ""
        refresh_all()

    async def apply_level_choice(ability: str) -> None:
        if not state["campaign_id"]:
            return
        try:
            await with_busy("Inscribing your new talent...", service.apply_level_up_choice, state["campaign_id"], ability)
        except Exception as exc:
            ui.notify(f"Level-up failed: {exc}", type="negative")
            return
        ui_state["pending_level_up"] = None
        ui.notify(f"{ABILITY_LABELS[ability]} increased.", type="positive")
        level_up_dialog.close()
        refresh_all()

    def toggle_debug_shortcut(event) -> None:
        if getattr(event, "key", "") != ".":
            return
        modifiers = getattr(event, "modifiers", None)
        if not modifiers:
            return
        if getattr(modifiers, "ctrl", False) or getattr(modifiers, "meta", False):
            ui_state["debug_mode"] = not ui_state["debug_mode"]
            ui.notify("Debug view enabled." if ui_state["debug_mode"] else "Debug view hidden.", type="info")
            refresh_all()

    ui.keyboard(on_key=toggle_debug_shortcut)

    with ui.dialog().props("persistent") as level_up_dialog:
        pass

    @ui.refreshable
    def render_level_up_dialog() -> None:
        level_up_dialog.clear()
        with level_up_dialog:
            delta = ui_state.get("pending_level_up") or {}
            if not delta:
                return
            hero = current_hero()
            with ui.element("div").classes("ink ink-sheet ink-paper ink-overlay-card").style("padding:28px;"):
                ui.label("Level Up").classes("ink-stamp")
                ui.label(f"{hero.get('class', 'Hero')} advancement").classes("ink-display text-4xl")
                ui.html(ornamental_rule("220px"))
                ui.label(f"Level {delta.get('old_level', hero.get('level', 1))} -> {delta.get('new_level', hero.get('level', 1))}").classes("text-lg")
                ui.label(f"Max HP increased by {delta.get('hp_gain', 0)}").classes("text-base")
                ui.label(service.get_level_up_feature(hero.get("class", ""), delta.get("new_level", hero.get("level", 1)))).classes("text-base")
                ui.label("Choose one ability to increase by +2.").classes("ink-stamp mt-4")
                with ui.row().classes("w-full gap-2"):
                    for ability in ABILITY_OPTIONS:
                        ui.button(
                            f"{ABILITY_LABELS[ability]} +2",
                            on_click=lambda _, a=ability: apply_level_choice(a),
                        ).props("flat no-caps").classes("ink-btn ink-btn-ember")

    with ui.dialog().props("persistent") as dice_dialog:
        pass

    @ui.refreshable
    def render_dice_dialog() -> None:
        dice_dialog.clear()
        with dice_dialog:
            if not ui_state["show_roll_overlay"] or not state.get("latest_roll"):
                return
            with ui.element("div").classes("ink ink-sheet ink-paper ink-overlay-card cursor-pointer").style("padding:24px;").on("click", lambda _: close_roll_overlay()):
                ui.label("Dice Cast").classes("ink-stamp")
                ui.html(roll_banner_html(state["latest_roll"]))
                ui.label("Tap anywhere to dismiss.").classes("text-sm text-slate-500")

    @ui.refreshable
    def render_status() -> None:
        if env_status["error"]:
            with ui.element("div").classes("ink-sheet").style("padding:18px;border-left:4px solid var(--ember);"):
                ui.label(env_status["error"]).classes("text-base")
            return
        if env_status["warning"]:
            with ui.element("div").classes("ink-sheet").style("padding:18px;border-left:4px solid var(--gold-deep);"):
                ui.label(env_status["warning"]).classes("text-base")

    @ui.refreshable
    def render_topbar() -> None:
        return

    @ui.refreshable
    def render_landing() -> None:
        if ui_state["screen"] != "landing":
            return
        campaigns = service.list_campaign_cards()
        with ui.element("div").classes("ink ink-paper ink-landing-page").style(
            "width:100%;min-height:100vh;padding:clamp(20px,4vw,56px);box-sizing:border-box;"
            "display:flex;flex-direction:column;gap:clamp(22px,3vw,32px);"
        ):
            with ui.row().classes("w-full items-end justify-between ink-wrap-row").style("position:relative;z-index:1;gap:18px;"):
                with ui.column().classes("gap-0"):
                    ui.label("An RPG Storyteller").classes("ink-stamp")
                    ui.label("The Wayfarer's Chronicle").classes("ink-display").style("font-size:clamp(38px,6vw,64px);margin-top:8px;letter-spacing:-0.02em;")
                    ui.label(
                        "Every roll inked. Every choice yours. Pick up a quill and continue your story — or begin a new one."
                    ).style(
                        "font-family:var(--ink-body);font-size:17px;color:var(--ink-2);margin-top:10px;max-width:540px;font-style:italic;"
                    )
                with ui.row().classes("items-center gap-2"):
                    ui.html(f'<span class="ink-pill">{icon_html("dice", 12)} 4 d20s rolled today</span>')
                    ui.html(f'<span class="ink-pill">{icon_html("book", 12)} {len(campaigns)} chronicles</span>')

            with ui.element("div").classes("ink-landing-grid").style("flex:1;position:relative;z-index:1;min-height:0;"):
                with ui.column().classes("gap-4").style("min-height:0;"):
                    with ui.row().classes("items-center gap-3"):
                        ui.label("Continue a Chronicle").classes("ink-display").style("font-size:22px;margin:0;")
                        ui.html(ornamental_rule("100%"))
                    with ui.column().classes("ink-scroll gap-4").style("overflow:auto;width:100%;align-items:stretch;"):
                        for campaign in campaigns:
                            with ui.element("div").classes("ink-sheet ink-campaign-card").style(
                                "padding:20px 24px;display:grid;grid-template-columns:minmax(0,1fr) 132px;gap:16px;align-items:center;"
                                "width:100%;box-sizing:border-box;"
                            ):
                                with ui.column().classes("gap-0").style("min-width:0;"):
                                    with ui.row().classes("items-baseline gap-2"):
                                        ui.label(campaign["title"]).classes("ink-display").style("font-size:24px;margin:0;min-width:0;overflow-wrap:anywhere;")
                                        ui.label(f"· {campaign['hero_name']} · {campaign['hero_line']}").classes("ink-stamp").style("font-size:10px;white-space:normal;")
                                    ui.label(
                                        f"Current lead — \"{public_objective_label(campaign['story_summary'])}\""
                                    ).style("color:var(--ink-2);font-size:14px;font-style:italic;margin-top:6px;overflow-wrap:anywhere;")
                                    with ui.row().classes("items-center gap-3").style("margin-top:10px;"):
                                        with ui.element("div").classes("ink-bar").style("flex:1;max-width:220px;"):
                                            ui.element("div").classes("ink-bar-fill moss").style("width:24%;")
                                        ui.label(nice_setting_label(campaign["setting"])).style("font-family:var(--ink-mono);font-size:11px;color:var(--ink-3);")
                                with ui.column().classes("gap-2").style("width:132px;"):
                                    ui.button("Resume", on_click=lambda _, campaign_id=campaign["id"]: continue_adventure(campaign_id)).props("flat no-caps").classes("ink-btn").style("padding:8px 16px;font-size:13px;")
                                    ui.button(
                                        "Open Journal",
                                        on_click=lambda _, campaign_id=campaign["id"]: ui.navigate.to(f"/journal?campaign_id={campaign_id}"),
                                    ).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 12px;font-size:12px;")
                                    ui.button(
                                        "Delete",
                                        on_click=lambda _, campaign=campaign: open_delete_campaign(campaign),
                                    ).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 12px;font-size:12px;color:var(--ember-deep) !important;border-color:var(--ember-deep) !important;")

                with ui.element("div").classes("ink-sheet").style("padding:30px;display:flex;flex-direction:column;gap:20px;"):
                    ui.element("div").classes("ink-tape")
                    ui.label("Begin a New Tale").classes("ink-display").style("font-size:22px;margin:0;")
                    with ui.column().classes("gap-2 w-full"):
                        ui.label("Setting").classes("ink-label")
                        with ui.element("div").classes("ink-setting-grid w-full").style("margin-top:4px;width:100%;"):
                            for key, tag in [
                                ("sandpoint", "Goblin Raid · level 1–3"),
                                ("absalom", "City Intrigue · 1–4"),
                                ("stolen_lands", "Frontier Charter · 2–4"),
                                ("osirion", "Desert Tombs · 2–5"),
                            ]:
                                picked = form_state["setting"] == key and not form_state["fresh_story_arc"]
                                with ui.element("button").classes("ink-sheet ink-setting-option").style(
                                    f"padding:10px 12px;text-align:left;cursor:pointer;"
                                    f"background:{'var(--ember-soft)' if picked else 'var(--paper-0)'};"
                                    f"border-color:{'var(--ember-deep)' if picked else 'var(--paper-2)'};"
                                    f"color:{'var(--paper-0)' if picked else 'var(--ink-1)'};"
                                ).on("click", lambda _, choice=key: select_setting(choice)):
                                    ui.label(nice_setting_label(key).split(" - ")[0]).classes("ink-display").style("font-size:16px;white-space:normal;overflow-wrap:anywhere;")
                                    ui.label(tag).style("font-family:var(--ink-ui);font-size:10px;opacity:.8;margin-top:2px;letter-spacing:.05em;")
                            picked = form_state["fresh_story_arc"]
                            with ui.element("button").classes("ink-sheet ink-setting-option").style(
                                f"padding:10px 12px;text-align:left;cursor:pointer;"
                                f"background:{'var(--ember-soft)' if picked else 'var(--paper-0)'};"
                                f"border-color:{'var(--ember-deep)' if picked else 'var(--paper-2)'};"
                                f"color:{'var(--paper-0)' if picked else 'var(--ink-1)'};"
                            ).on("click", lambda _: select_fresh_story_arc()):
                                ui.label("Fresh Story Arc").classes("ink-display").style("font-size:16px;white-space:normal;overflow-wrap:anywhere;")
                                ui.label("New hidden quest · generated").style("font-family:var(--ink-ui);font-size:10px;opacity:.8;margin-top:2px;letter-spacing:.05em;")
                        if form_state["fresh_story_arc"]:
                            ui.label(
                                f"Fresh mode will use {nice_setting_label(form_state['setting']).split(' - ')[0]} as the world, but create a new hidden story spine."
                            ).style("font-size:12px;color:var(--ink-3);font-style:italic;margin-top:6px;")
                    title_input = ui.input("", value=form_state["title"], placeholder="A name for this tale")
                    title_input.bind_value(form_state, "title")
                    title_input.props("borderless")
                    title_input.classes("w-full")
                    title_input.style("font-family:var(--ink-body);font-size:18px;")
                    ui.html('<div class="ink-rule" style="color:var(--ink-4)"><span class="ink-stamp">Then →</span><span class="ink-rule-diamond"></span></div>')
                    with ui.column().classes("gap-2").style("margin-top:auto;"):
                        ui.button("Roll a New Hero", on_click=lambda: set_screen("create")).props("flat no-caps").classes("ink-btn ink-btn-ember").style("width:100%;")
                        ui.button("Import a Character Sheet", on_click=lambda: set_screen("create")).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("width:100%;")

    @ui.refreshable
    def render_creator() -> None:
        if ui_state["screen"] != "create":
            return
        with ui.element("div").classes("ink ink-paper").style(
            "width:100%;min-height:880px;padding:40px;box-sizing:border-box;display:flex;flex-direction:column;gap:20px;"
        ):
            with ui.row().classes("items-center justify-between w-full").style("position:relative;z-index:1;"):
                with ui.row().classes("items-center gap-3"):
                    ui.button("Back", on_click=lambda: set_screen("landing")).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 12px;font-size:12px;")
                    ui.label("A New Hero").classes("ink-stamp")
                with ui.row().classes("items-center gap-4"):
                    for step_no, step_name, active in [
                        (1, "Ancestry", True),
                        (2, "Class", True),
                        (3, "Abilities", False),
                        (4, "Identity", False),
                    ]:
                        with ui.row().classes("items-center gap-2"):
                            ui.html(
                                f'<span style="width:22px;height:22px;border-radius:50%;'
                                f'background:{"var(--ink-1)" if active else "var(--paper-0)"};'
                                f'color:{"var(--paper-0)" if active else "var(--ink-3)"};'
                                f'border:1.5px solid var(--ink-1);display:inline-flex;align-items:center;justify-content:center;'
                                f'font-family:var(--ink-display);font-size:12px;font-weight:700;">{step_no}</span>'
                            )
                            ui.label(step_name).classes("ink-stamp").style(f'color:{"var(--ink-1)" if active else "var(--ink-3)"};')

            with ui.element("div").style("display:grid;grid-template-columns:1.6fr 1fr;gap:28px;flex:1;position:relative;z-index:1;min-height:0;"):
                with ui.column().classes("ink-scroll gap-5").style("overflow:auto;padding-right:8px;"):
                    with ui.element("section"):
                        with ui.row().classes("items-center gap-3").style("margin-bottom:12px;"):
                            ui.label("Ancestry").classes("ink-display").style("font-size:22px;margin:0;")
                            ui.html(ornamental_rule("100%"))
                            ui.label(f"picked: {form_state['ancestry']}").classes("ink-stamp")
                        with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:10px;"):
                            for ancestry in ANCESTRIES:
                                picked = form_state["ancestry"] == ancestry
                                with ui.element("button").classes("ink-sheet").style(
                                    f"padding:12px 14px;text-align:left;cursor:pointer;"
                                    f"background:{'var(--paper-2)' if picked else 'var(--paper-0)'};"
                                    f"border-color:{'var(--ember-deep)' if picked else 'var(--paper-2)'};"
                                    f"border-width:{'2px' if picked else '1px'};"
                                ).on("click", lambda _, choice=ancestry: select_ancestry(choice)):
                                    ui.label(ancestry).classes("ink-display").style("font-size:17px;")
                    with ui.element("section"):
                        with ui.row().classes("items-center gap-3").style("margin-bottom:12px;"):
                            ui.label("Class").classes("ink-display").style("font-size:22px;margin:0;")
                            ui.html(ornamental_rule("100%"))
                            ui.label(f"picked: {form_state['hero_class']}").classes("ink-stamp")
                        with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:10px;"):
                            for hero_class in CLASSES:
                                picked = form_state["hero_class"] == hero_class
                                with ui.element("button").classes("ink-sheet").style(
                                    f"padding:12px 14px;text-align:left;cursor:pointer;"
                                    f"background:{'var(--paper-2)' if picked else 'var(--paper-0)'};"
                                    f"border-color:{'var(--ember-deep)' if picked else 'var(--paper-2)'};"
                                    f"border-width:{'2px' if picked else '1px'};"
                                ).on("click", lambda _, choice=hero_class: select_hero_class(choice)):
                                    ui.label(hero_class).classes("ink-display").style("font-size:17px;")
                    with ui.element("section").classes("ink-sheet").style("padding:22px;"):
                        with ui.row().classes("items-center gap-3").style("margin-bottom:14px;"):
                            ui.label("Identity").classes("ink-display").style("font-size:22px;margin:0;")
                            ui.html(ornamental_rule("100%"))
                        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:18px;"):
                            title_input = ui.input("Campaign title", value=form_state["title"], placeholder="A name for this tale")
                            title_input.bind_value(form_state, "title")
                            title_input.props("outlined")
                            hero_input = ui.input("Hero name", value=form_state["hero_name"], placeholder="Ito")
                            hero_input.bind_value(form_state, "hero_name")
                            hero_input.props("outlined")
                            traits_input = ui.textarea("A few words on personality", value=form_state["traits"], placeholder="Quick-fingered, slow to trust...")
                            traits_input.bind_value(form_state, "traits")
                            traits_input.props("outlined autogrow")
                            traits_input.style("grid-column:1 / -1;")
                        with ui.row().classes("w-full gap-3 items-center").style("margin-top:16px;"):
                            begin_button = ui.button(
                                "Sealing..." if ui_state["busy_message"] == "The Game Master inks the opening chapter..." else "Seal the Character & Begin",
                                on_click=start_adventure,
                            ).props("flat no-caps").classes("ink-btn ink-btn-ember")
                            if ui_state["busy_message"] == "The Game Master inks the opening chapter...":
                                begin_button.props("loading disable")
                                ui.label("Creating the campaign and opening scene...").style("font-size:12px;color:var(--ink-3);font-style:italic;")

                with ui.element("aside").classes("ink-sheet").style(
                    "padding:24px;display:flex;flex-direction:column;gap:16px;align-self:flex-start;position:sticky;top:0;"
                ):
                    ui.element("div").classes("ink-tape")
                    preview_hero = creator_preview_hero()
                    preview_scores = preview_hero["ability_scores"]
                    ui.label("Character Sheet · draft").classes("ink-stamp")
                    ui.label(form_state["hero_name"] or "Ito").classes("ink-display").style("font-size:32px;margin:4px 0 0;")
                    ui.label(f"Level {int(form_state['level'])} · {form_state['ancestry']} · {form_state['hero_class']}").style(
                        "font-family:var(--ink-body);font-style:italic;color:var(--ink-2);font-size:14px;"
                    )
                    ui.html(ornamental_rule("100%"))
                    with ui.element("div"):
                        with ui.row().classes("justify-between items-baseline"):
                            ui.html(f'<span class="ink-stamp">{icon_html("heart", 11, "var(--ember)")} Hit Points</span>')
                            ui.label(f"{preview_hero['hp']} / {preview_hero['max_hp']}").classes("ink-display").style("font-size:18px;font-weight:700;")
                        with ui.element("div").classes("ink-bar").style("margin-top:6px;"):
                            ui.element("div").classes("ink-bar-fill").style("width:100%;")
                    with ui.row().classes("justify-between items-baseline"):
                        ui.html(f'<span class="ink-stamp">{icon_html("coin", 11, "var(--gold-deep)")} Starting Gold</span>')
                        ui.label(f"{preview_hero['gold']} gp").classes("ink-display").style("font-size:18px;font-weight:700;")
                    with ui.element("div").classes("ink-statblock").style("padding:12px 14px;"):
                        ui.label("Ability Scores").classes("ink-stamp").style("margin-bottom:8px;")
                        with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:10px 14px;"):
                            for ability, short in ABILITY_LABELS.items():
                                score = preview_scores.get(ability, 10)
                                with ui.column().classes("items-center gap-0"):
                                    ui.label(short).classes("ink-stamp").style("font-size:10px;")
                                    ui.label(str(score)).classes("ink-display").style("font-size:22px;font-weight:600;line-height:1;")
                                    ui.label(ability_modifier(score)).style("font-family:var(--ink-mono);font-size:11px;color:var(--ember-deep);")
                    with ui.element("div").classes("ink-statblock").style("padding:12px 14px;"):
                        ui.label("Starting Gear").classes("ink-stamp").style("margin-bottom:8px;")
                        for item in preview_hero["inventory"][:6]:
                            ui.label(inventory_label(item)).style("font-size:12px;color:var(--ink-2);border-bottom:1px dotted var(--ink-4);padding:3px 0;")

    @ui.refreshable
    def render_main_game() -> None:
        if ui_state["screen"] != "game" or not state["story_started"]:
            return
        campaign = active_campaign()
        if not campaign:
            with ui.element("div").classes("ink-sheet").style("padding:24px;"):
                ui.label("The active campaign could not be loaded.").classes("text-lg")
            return

        hero = campaign["hero_sheet"]
        world = campaign["world_state"]
        summary = current_story_summary()
        previous_messages = state["messages"][-9:-1] if len(state["messages"]) > 1 else []
        latest_message = state["messages"][-1] if state["messages"] else None
        latest_text_pending = bool(
            latest_message
            and latest_message.get("id") in ui_state["scene_text_pending_message_ids"]
        )

        with ui.element("div").classes("ink ink-game-shell").style(
            "width:100%;height:100vh;min-height:0;"
            "display:flex;flex-direction:column;background:var(--paper-1);overflow:hidden;"
        ):
            with ui.element("div").classes("ink-game-body").style("display:flex;flex:1;min-height:0;overflow:hidden;"):
                if ui_state["drawer_open"]:
                    with ui.element("aside").classes("ink-game-drawer").style(
                        "width:clamp(260px,22vw,320px);transition:width .25s ease;border-right:1px solid var(--paper-2);"
                        "background:var(--paper-1);display:flex;flex-direction:column;padding:16px 12px;gap:10px;flex-shrink:0;"
                        "height:100%;overflow:auto;"
                    ):
                        with ui.element("div").classes("ink-sheet").style("padding:12px;display:flex;flex-direction:column;gap:10px;"):
                            with ui.row().classes("items-center justify-between gap-2"):
                                ui.label(campaign["title"]).classes("ink-stamp").style("font-size:10px;")
                                if ui_state["debug_mode"]:
                                    ui.label("Debug").classes("ink-pill")
                            ui.label(f"{campaign['hero_name']} · Lvl {hero.get('level',1)} {hero.get('class','')}").classes("ink-display").style("font-size:17px;line-height:1;")
                            with ui.row().classes("items-center gap-2").style("flex-wrap:wrap;"):
                                ui.button("Chronicles", on_click=lambda: set_screen("landing")).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 10px;font-size:12px;")
                                ui.button("Journal", on_click=lambda: ui.navigate.to(active_journal_url())).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 10px;font-size:12px;")
                                ui.button(
                                    "Hide Panel",
                                    on_click=lambda: (ui_state.__setitem__("drawer_open", False), refresh_all()),
                                ).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 10px;font-size:12px;")
                            ui.button("End Session", on_click=end_session).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:7px 10px;font-size:12px;width:100%;")
                        hp = hero.get("hp", 0)
                        max_hp = max(hero.get("max_hp", 1), 1)
                        xp = hero.get("xp", 0)
                        for title, icon, body in [
                            ("HP", "heart", f"{hp} / {max_hp}"),
                            ("XP", "star", f"{xp} / {XP_PER_LEVEL}"),
                            ("Coin", "coin", f"{hero.get('gold',0)} gp"),
                        ]:
                            with ui.element("div").classes("ink-sheet").style("padding:10px 12px;"):
                                with ui.row().classes("justify-between items-baseline"):
                                    ui.html(f'<span class="ink-stamp">{icon_html(icon, 11)}</span>')
                                    ui.label(body).style("font-family:var(--ink-display);font-weight:700;")
                                if title in {"HP", "XP"}:
                                    with ui.element("div").classes("ink-bar").style("margin-top:6px;"):
                                        fill = (hp / max_hp) if title == "HP" else min(xp / XP_PER_LEVEL, 1)
                                        cls = "ink-bar-fill moss" if title == "XP" else "ink-bar-fill"
                                        ui.element("div").classes(cls).style(f"width:{fill * 100}%;")
                        effects = character_effect_labels(hero)
                        with ui.element("div").classes("ink-sheet").style("padding:10px 12px;"):
                            with ui.row().classes("items-center justify-between gap-2"):
                                ui.html(f'<div class="ink-stamp">{icon_html("dice",11)} Attributes & Rolls</div>')
                                ui.button(
                                    "Collapse" if ui_state["show_character_stats"] else "Open",
                                    on_click=lambda: (
                                        ui_state.__setitem__("show_character_stats", not ui_state["show_character_stats"]),
                                        render_main_game.refresh(),
                                    ),
                                ).props("flat dense no-caps").classes("ink-btn ink-btn-ghost").style("padding:3px 8px;font-size:10px;")
                            if not ui_state["show_character_stats"]:
                                ui.label("Tap Open to show base scores, buffs, and roll bonuses.").style(
                                    "font-size:12px;color:var(--ink-3);font-style:italic;margin-top:2px;"
                                )
                            else:
                                ui.label("Base scores, derived modifiers, and the roll bonuses used by the app.").style(
                                    "font-size:12px;color:var(--ink-3);font-style:italic;margin-top:2px;"
                                )
                                with ui.element("div").style(
                                    "display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;"
                                ):
                                    scores = hero.get("ability_scores", {})
                                    for ability, short in ABILITY_LABELS.items():
                                        score = scores.get(ability, 10)
                                        with ui.element("div").style(
                                            "border:1px dotted var(--ink-4);padding:7px 6px;text-align:center;background:var(--paper-0);"
                                        ):
                                            ui.label(short).classes("ink-stamp").style("font-size:9px;")
                                            ui.label(str(score)).classes("ink-display").style("font-size:20px;line-height:1;font-weight:700;")
                                            ui.label(ability_modifier(score)).style("font-family:var(--ink-mono);font-size:11px;color:var(--ember-deep);")

                                with ui.element("div").style("margin-top:10px;border-top:1px dotted var(--ink-4);padding-top:8px;"):
                                    ui.label("Active buffs / effects").classes("ink-stamp").style("font-size:9px;")
                                    if effects:
                                        for effect in effects:
                                            ui.label(effect).style("font-size:12px;color:var(--ink-2);padding-top:3px;")
                                    else:
                                        ui.label("No active roll buffs are currently tracked.").style(
                                            "font-size:12px;color:var(--ink-3);font-style:italic;padding-top:3px;"
                                        )

                                with ui.expansion("Skill modifiers used by rolls", value=False).classes("w-full").style(
                                    "margin-top:8px;background:var(--paper-0);border:1px dashed var(--ink-4);border-radius:2px;padding:4px 8px;"
                                ):
                                    ui.label(f"Roll math: ability modifier + {PROFICIENCY_BONUS} when trained.").style(
                                        "font-size:11px;color:var(--ink-3);font-style:italic;margin-bottom:5px;"
                                    )
                                    for row in skill_modifier_rows(hero):
                                        trained_label = "trained" if row["trained"] else "untrained"
                                        ui.label(
                                            f"{row['skill']}: {signed_modifier(row['total'])} "
                                            f"({ABILITY_LABELS[row['ability']]} {signed_modifier(row['ability_mod'])}, {trained_label})"
                                        ).style("font-family:var(--ink-mono);font-size:10.5px;color:var(--ink-2);padding:2px 0;")
                        inventory = hero.get("inventory", [])
                        with ui.element("div").classes("ink-sheet").style("padding:10px 12px;"):
                            ui.html(f'<div class="ink-stamp">{icon_html("pack",11)} Inventory</div>')
                            if not inventory:
                                ui.label("Empty").style("font-size:13px;color:var(--ink-3);font-style:italic;padding:3px 0;")
                            else:
                                with ui.element("div").classes("ink-scroll").style("max-height:190px;overflow:auto;margin-top:4px;padding-right:4px;"):
                                    for item in inventory:
                                        ui.label(inventory_label(item)).style("font-size:13px;color:var(--ink-2);border-bottom:1px dotted var(--ink-4);padding:3px 0;")
                        with ui.element("div").classes("ink-sheet").style("padding:10px 12px;margin-top:auto;"):
                            ui.html(f'<div class="ink-stamp">{icon_html("scroll",11)} Current Lead</div>')
                            ui.label("What you know").style("font-family:var(--ink-display);font-size:14px;font-weight:600;")
                            ui.label(public_objective_label(summary)).style("font-size:12px;color:var(--ink-2);font-style:italic;margin-top:2px;")
                else:
                    with ui.element("aside").classes("ink-game-drawer ink-game-drawer-collapsed").style(
                        "width:76px;border-right:1px solid var(--paper-2);background:var(--paper-1);"
                        "padding:16px 12px;display:flex;flex-direction:column;gap:10px;height:100%;overflow:auto;"
                    ):
                        ui.button("Panel", on_click=lambda: (ui_state.__setitem__("drawer_open", True), refresh_all())).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:8px 4px;font-size:10px;")
                        for icon, text in [
                            ("heart", str(hero.get("hp", 0))),
                            ("star", str(hero.get("xp", 0))),
                            ("coin", str(hero.get("gold", 0))),
                            ("pack", f"×{inventory_count(hero.get('inventory', []))}"),
                            ("dice", "6/6"),
                            ("scroll", ""),
                        ]:
                            with ui.element("div").classes("ink-sheet").style("padding:10px 8px;"):
                                with ui.column().classes("items-center gap-0"):
                                    ui.html(icon_html(icon, 14, "var(--ember)" if icon == "heart" else "currentColor"))
                                    if text:
                                        ui.label(text).style("font-family:var(--ink-mono);font-size:10px;line-height:1.1;")

                with ui.element("main").classes("ink-paper ink-game-main").style("flex:1;display:flex;flex-direction:column;min-width:0;min-height:0;position:relative;overflow:hidden;"):
                    with ui.element("div").classes("ink-scroll ink-story-scroll").style(
                        "flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;"
                        "padding:clamp(18px,3vw,36px) clamp(20px,4vw,64px) 18px;position:relative;z-index:1;"
                    ):
                        with ui.column().classes("gap-4").style("width:min(1120px,100%);margin:0 auto;"):
                            with ui.element("div").style("text-align:center;margin-bottom:4px;"):
                                ui.label("Scene 4 of this chapter · 12 minutes in").classes("ink-stamp")
                                headline = "The dice tumble across the table" if latest_text_pending else (
                                    scene_title_for_message(latest_message)
                                )
                                ui.label(headline).classes("ink-display").style("font-size:clamp(26px,3.5vw,38px);margin-top:6px;letter-spacing:-0.01em;")
                                ui.html(ornamental_rule("220px"))
                            if previous_messages:
                                with ui.expansion("Earlier in the story", value=False).classes("w-full").style("background:var(--paper-0);border:1px dashed var(--ink-4);border-radius:2px;padding:10px 14px;"):
                                    for message in reversed(previous_messages):
                                        with ui.row().classes("w-full gap-3").style("margin-top:12px;color:var(--ink-3);font-size:13.5px;font-style:italic;"):
                                            ui.label(story_message_label(message)).classes("ink-stamp").style("flex:0 0 60px;font-size:9px;")
                                            ui.label(message["content"]).style("flex:1;")
                                            if message.get("roll_data"):
                                                roll = message["roll_data"]
                                                ui.label(f"d20 {roll.get('roll',0)}+{roll.get('modifier',0)}={roll.get('total',0)}").style(
                                                    f"flex:0 0 auto;font-family:var(--ink-mono);font-size:10px;color:{'var(--moss)' if roll.get('degree') in {'success','critical success'} else 'var(--ember)'};"
                                                )
                            if latest_message and latest_message.get("roll_data"):
                                ui.html(roll_banner_html(latest_message["roll_data"]))
                            if latest_message:
                                with ui.element("article").style("padding:8px 4px;"):
                                    if latest_text_pending:
                                        with ui.row().classes("items-center justify-center gap-2").style(
                                            "min-height:120px;color:var(--ink-3);font-style:italic;"
                                        ):
                                            ui.spinner(size="sm", color="orange")
                                            ui.label("The outcome settles into the story...")
                                    else:
                                        ui.markdown(latest_message["content"]).classes("ink-beat").style(
                                            "font-family:var(--ink-body);font-size:19px;line-height:1.65;color:var(--ink-1);margin:0;"
                                        )
                                        if latest_message.get("audio_url"):
                                            ui.audio(latest_message["audio_url"], autoplay=False).props("controls").style("margin-top:12px;width:100%;")
                                        elif latest_message.get("id") in ui_state["audio_pending_message_ids"]:
                                            with ui.row().classes("items-center gap-2").style("margin-top:12px;color:var(--ink-3);"):
                                                ui.spinner(size="sm", color="orange")
                                                ui.label("Narration audio is being prepared...").style("font-size:12px;font-style:italic;")
                                        elif latest_message.get("id") in ui_state["audio_failed_message_ids"]:
                                            ui.label("Narration audio is unavailable for this beat.").style("margin-top:12px;font-size:12px;color:var(--ink-3);font-style:italic;")
                                if not latest_text_pending and ui_state["debug_mode"] and (latest_message.get("resolution_data") or latest_message.get("applied_delta")):
                                    with ui.expansion("Debug turn data", value=True).classes("w-full"):
                                        if latest_message.get("resolution_data"):
                                            ui.code(json.dumps(latest_message["resolution_data"], indent=2), language="json").classes("w-full")
                                        if latest_message.get("applied_delta"):
                                            ui.code(json.dumps(latest_message["applied_delta"], indent=2), language="json").classes("w-full")
                            elif ui_state.get("opening_error"):
                                with ui.element("article").classes("ink-sheet").style(
                                    "padding:22px;border-left:4px solid var(--ember);background:var(--paper-0);"
                                ):
                                    ui.label("The opening scene could not be generated.").classes("ink-display").style("font-size:22px;margin:0;")
                                    ui.label(ui_state["opening_error"]).style("font-size:13px;color:var(--ink-2);margin-top:8px;")
                            elif ui_state["busy_message"]:
                                with ui.element("article").classes("ink-sheet").style(
                                    "padding:28px;text-align:center;background:var(--paper-0);"
                                ):
                                    with ui.row().classes("items-center justify-center gap-2"):
                                        ui.spinner(size="md", color="orange")
                                        ui.label("The Game Master is preparing the opening scene...").style(
                                            "font-size:14px;color:var(--ink-3);font-style:italic;"
                                        )
                                    ui.label("Your character sheet, inventory, and campaign shell are already saved.").style(
                                        "font-size:12px;color:var(--ink-3);margin-top:8px;"
                                    )
                    with ui.element("div").classes("ink-composer").style(
                        "flex-shrink:0;border-top:1px solid var(--paper-2);background:var(--paper-0);"
                        "padding:12px clamp(20px,4vw,64px);position:relative;z-index:2;"
                    ):
                        with ui.element("div").style("width:min(1120px,100%);margin:0 auto;"):
                            action_input = ui.textarea("What do you do?", value=ui_state["user_input"], placeholder="Tell the GM what you do next...")
                            action_input.bind_value(ui_state, "user_input")
                            action_input.props("outlined autogrow")
                            action_input.classes("w-full ink-action-textarea")
                            action_input.style("font-family:var(--ink-body);font-size:18px;background:var(--paper-0);")
                            with ui.row().classes("w-full items-center justify-between ink-composer-actions").style("margin-top:10px;gap:10px;flex-wrap:wrap;"):
                                if ui_state["busy_message"]:
                                    with ui.row().classes("items-center gap-2"):
                                        ui.spinner(size="sm", color="orange")
                                        ui.label("GM is writing the next beat...").style("font-size:12px;color:var(--ink-3);font-style:italic;")
                                else:
                                    ui.label("Free text only. No suggested actions.").style("font-size:12px;color:var(--ink-3);font-style:italic;")
                                with ui.row().classes("items-center gap-2"):
                                    ui.button("Send", on_click=submit_turn).props("flat no-caps").classes("ink-btn ink-btn-ember")

    with ui.element("div").classes("ink ink-paper ink-shell"):
        with ui.column().classes("w-full gap-0").style("max-width:none;margin:0;"):
            render_topbar()
            with ui.column().classes("w-full gap-0").style("min-height:0;"):
                render_status()
                render_landing()
                render_creator()
                render_main_game()


@ui.page("/journal")
def journal(request: Request) -> None:
    inject_inkwell_theme()
    campaign_id = request.query_params.get("campaign_id")
    session_id = request.query_params.get("session_id")
    debug_mode = request.query_params.get("debug") == "1"
    back_url = "/"
    if campaign_id and session_id:
        back_url = f"/?campaign_id={campaign_id}&session_id={session_id}"
    elif campaign_id:
        back_url = f"/?campaign_id={campaign_id}"

    journal_data = None
    campaign = None
    if campaign_id:
        journal_data = service.get_journal_data(int(campaign_id))
        campaign = journal_data["campaign"]

    with ui.element("div").classes("ink ink-paper ink-shell"):
        with ui.column().classes("w-full gap-4").style("max-width:none;margin:0;padding:20px 36px 24px;"):
            with ui.row().classes("items-center gap-4 w-full").style("position:relative;z-index:1;"):
                ui.button("Back to scene", on_click=lambda: ui.navigate.to(back_url)).props("flat no-caps").classes("ink-btn ink-btn-ghost").style("padding:6px 10px;font-size:12px;")
                with ui.column().classes("gap-0"):
                    ui.label("Chronicle").classes("ink-stamp")
                    ui.label(
                        f"{campaign['title']} · {campaign['hero_name']}'s tale" if campaign else "Campaign Journal"
                    ).classes("ink-display").style("font-size:28px;margin:0;")
                with ui.row().classes("items-center gap-2").style("margin-left:auto;"):
                    if campaign_id:
                        ui.html(f'<span class="ink-pill">{icon_html("book", 11)} Chronicle</span>')
                        ui.html(f'<span class="ink-pill">{icon_html("dice", 11)} Roll ledger</span>')

            if not campaign_id or not journal_data:
                with ui.element("div").classes("ink-sheet ink-paper").style("padding:28px;"):
                    ui.label("Choose a campaign from the ledger first.").classes("text-lg")
                return

            with ui.element("div").style("display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:28px;flex:1;min-height:0;position:relative;z-index:1;"):
                with ui.element("div").classes("ink-scroll").style("overflow:auto;padding-right:8px;"):
                    with ui.element("div").style("position:relative;padding-left:26px;"):
                        ui.element("div").style("position:absolute;left:8px;top:8px;bottom:60px;width:2px;background:var(--ink-4);")
                        for index, chapter in enumerate(journal_data["chapters"]):
                            current = index == len(journal_data["chapters"]) - 1
                            with ui.element("div").style("position:relative;margin-bottom:22px;"):
                                ui.element("div").style(
                                    f"position:absolute;left:-22px;top:16px;width:14px;height:14px;border-radius:50%;"
                                    f"background:{'var(--ember)' if current else 'var(--ink-1)'};border:2px solid var(--ink-1);"
                                )
                                with ui.element("article").classes("ink-sheet").style("padding:20px;background:var(--paper-0);"):
                                    with ui.row().classes("items-baseline gap-3").style("margin-bottom:6px;"):
                                        ui.label(f"Chapter {chapter['session_number']}").classes("ink-stamp").style(
                                            f"color:{'var(--ember-deep)' if current else 'var(--ink-3)'};"
                                        )
                                        if current:
                                            ui.html('<span class="ink-pill" style="background:var(--ember-soft);color:var(--paper-0);border-color:var(--ember-deep)">Current</span>')
                                    title = "Chapter Summary" if chapter.get("summary") else "Conversation Beats"
                                    ui.label(title).classes("ink-display").style("font-size:24px;margin:0;")
                                    if chapter.get("summary"):
                                        ui.label(chapter["summary"]).style("margin:10px 0 14px;color:var(--ink-2);font-size:14.5px;line-height:1.55;")
                                    if chapter.get("messages"):
                                        with ui.expansion(f"{len(chapter['messages'])} saved beats", value=current).classes("w-full").style(
                                            "margin-top:12px;background:var(--paper-1);border:1px dashed var(--ink-4);border-radius:2px;padding:8px 12px;"
                                        ):
                                            for message in chapter["messages"]:
                                                with ui.row().classes("w-full gap-3").style("margin-top:10px;align-items:flex-start;"):
                                                    ui.label(story_message_label(message)).classes("ink-stamp").style("flex:0 0 72px;font-size:9px;")
                                                    with ui.column().classes("gap-1").style("flex:1;min-width:0;"):
                                                        if message["role"] == "assistant":
                                                            ui.markdown(message["content"]).classes("ink-beat").style("font-size:14px;line-height:1.5;color:var(--ink-2);")
                                                        else:
                                                            ui.label(message["content"]).style("font-size:14px;line-height:1.5;color:var(--ink-2);font-style:italic;")
                                                        if message.get("roll_data"):
                                                            roll = message["roll_data"]
                                                            ui.label(f"d20 {roll.get('roll', 0)} + {roll.get('modifier', 0)} = {roll.get('total', 0)} vs DC {roll.get('dc', 0)} ({roll.get('degree', '')})").style(
                                                                "font-family:var(--ink-mono);font-size:10px;color:var(--ember-deep);"
                                                            )
                                    elif not chapter.get("summary"):
                                        ui.label("No saved beats in this chapter.").style("margin-top:10px;color:var(--ink-3);font-size:13px;font-style:italic;")

                with ui.element("aside").classes("ink-sheet ink-scroll").style(
                    "padding:22px;align-self:flex-start;position:sticky;top:0;max-height:100%;overflow:auto;"
                ):
                    ui.element("div").classes("ink-tape")
                    ui.label("Roll Ledger").classes("ink-stamp")
                    ui.label("Every die, recorded.").classes("ink-display").style("font-size:20px;margin:4px 0 12px;")
                    for message in journal_data["messages"]:
                        if not message.get("roll_data"):
                            continue
                        roll = message["roll_data"]
                        with ui.element("div").style(
                            "display:grid;grid-template-columns:1fr;gap:6px;padding-bottom:10px;border-bottom:1px dotted var(--ink-4);margin-bottom:10px;"
                        ):
                            ui.label(f"Chapter {message.get('session_number', '?')}").classes("ink-stamp").style("font-size:9px;")
                            ui.html(roll_banner_html(roll))
                            ui.label(message.get("content", "")[:160]).style("font-size:12px;line-height:1.35;color:var(--ink-3);")
                        if debug_mode and (message.get("resolution_data") or message.get("applied_delta")):
                            with ui.expansion("Debug turn data").classes("w-full"):
                                if message.get("resolution_data"):
                                    ui.code(json.dumps(message["resolution_data"], indent=2), language="json").classes("w-full")
                                if message.get("applied_delta"):
                                    ui.code(json.dumps(message["applied_delta"], indent=2), language="json").classes("w-full")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Pathfinder Quest", storage_secret="pathfinder-quest-local", reload=False)
