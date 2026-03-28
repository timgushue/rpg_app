"""
Context builder — assembles current game state into a Claude prompt string.
"""

from game.game_data import XP_PER_LEVEL
from game.game_time import format_time


def build_context(campaign: dict, summaries: list, messages: list, roll_result: dict = None) -> str:
    hero_name = campaign["hero_name"]
    hero = campaign["hero_sheet"]
    world = campaign["world_state"]

    lines = []

    lines.append("=== YOUR HERO ===")
    lines.append(f"Name: {hero_name}")
    if hero.get("ancestry"):
        lines.append(f"Ancestry: {hero['ancestry']}")
    if hero.get("class"):
        lines.append(f"Class: {hero['class']}  |  Level: {hero.get('level', 1)}")
    if hero.get("hp") and hero.get("max_hp"):
        lines.append(f"HP: {hero['hp']}/{hero['max_hp']}  |  AC: {hero.get('ac', '—')}")
    if "xp" in hero:
        lines.append(f"XP: {hero['xp']}/{XP_PER_LEVEL}  |  Gold: {hero.get('gold', 0)} gp")
    if hero.get("ability_scores"):
        ab = hero["ability_scores"]
        lines.append(
            f"STR {ab.get('strength', 10)}  DEX {ab.get('dexterity', 10)}  "
            f"CON {ab.get('constitution', 10)}  INT {ab.get('intelligence', 10)}  "
            f"WIS {ab.get('wisdom', 10)}  CHA {ab.get('charisma', 10)}"
        )

    # Spell slots
    spell_slots = hero.get("spell_slots", {})
    if spell_slots:
        slot_parts = [
            f"Level {lvl}: {data['remaining']}/{data['max']}"
            for lvl, data in spell_slots.items()
        ]
        lines.append(f"Spell slots remaining — {', '.join(slot_parts)}")

    # Focus points
    fp = hero.get("focus_points", {})
    if fp.get("max", 0) > 0:
        lines.append(f"Focus points: {fp['remaining']}/{fp['max']}")

    if hero.get("spells"):
        lines.append(f"Spells known: {', '.join(hero['spells'])}")

    # Inventory with quantities
    inventory = hero.get("inventory", [])
    if inventory:
        if isinstance(inventory[0], dict):
            inv_parts = [
                f"{i['name']} x{i['quantity']}" if i['quantity'] != 1 else i['name']
                for i in inventory
            ]
        else:
            inv_parts = inventory  # legacy string format
        lines.append(f"Inventory: {', '.join(inv_parts)}")

    if hero.get("traits"):
        lines.append(f"Personality: {', '.join(hero['traits'])}")

    # Time
    time_state = world.get("time", {})
    if time_state:
        lines.append(f"Time: {format_time(time_state)}")

    lines.append("")
    lines.append("=== THE WORLD ===")
    if world.get("setting"):
        lines.append(world["setting"])
    if world.get("npcs"):
        lines.append(f"Characters met: {', '.join(world['npcs'])}")
    if world.get("locations"):
        lines.append(f"Places visited: {', '.join(world['locations'])}")
    if world.get("quests"):
        lines.append(f"Quests: {', '.join(world['quests'])}")
    if world.get("lore"):
        lines.append(f"Lore: {world['lore']}")

    lines.append("")
    lines.append("=== THE STORY SO FAR ===")
    if summaries:
        for i, summary in enumerate(summaries, 1):
            lines.append(f"Chapter {i}: {summary}")
    else:
        lines.append("This is the beginning of the adventure.")

    lines.append("")
    lines.append("=== THIS SESSION ===")
    if messages:
        for msg in messages:
            label = hero_name if msg["role"] == "user" else "Game Master"
            lines.append(f"{label}: {msg['content']}")
    else:
        lines.append("(Session just started)")

    if roll_result:
        skill = roll_result.get("skill") or "Check"
        mod = roll_result["modifier"]
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        lines.append("")
        lines.append("=== DICE ROLL ===")
        lines.append(
            f"{skill}: rolled {roll_result['roll']} {mod_str} = {roll_result['total']} "
            f"vs DC {roll_result['dc']} — {roll_result['degree'].upper()}"
        )

    return "\n".join(lines)
