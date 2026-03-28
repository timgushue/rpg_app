"""Golarion time tracking for Pathfinder Quest."""

DAYS_OF_WEEK = [
    "Moonday", "Toilday", "Wealday", "Oathday", "Fireday", "Starday", "Sunday",
]

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]

# Season names in Golarion months (3 months per season, ~30 days each)
SEASON_MONTHS = {
    "Spring": ["Pharast", "Gozran", "Desnus"],
    "Summer": ["Sarenith", "Erastus", "Arodus"],
    "Autumn": ["Rova", "Lamashan", "Neth"],
    "Winter": ["Kuthona", "Abadius", "Calistril"],
}


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 12:
        return "morning"
    if 12 <= hour < 14:
        return "midday"
    if 14 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 20:
        return "dusk"
    return "night"


def initial_time() -> dict:
    """Start campaigns on a Fireday morning in Spring."""
    return {
        "hour": 8,
        "minute": 0,
        "time_of_day": "morning",
        "day": 1,
        "day_of_week": 4,  # Fireday
        "season": "Spring",
    }


def advance_time(time_state: dict, minutes: int) -> tuple:
    """
    Advance the clock by `minutes`. Returns (new_time_state, did_full_rest).
    A full rest occurs when the clock crosses through the night period (22:00–06:00).
    """
    t = dict(time_state)
    total_minutes = t["hour"] * 60 + t.get("minute", 0) + minutes

    old_day = t.get("day", 1)
    new_absolute_hour = total_minutes // 60
    new_minute = total_minutes % 60
    days_advanced = new_absolute_hour // 24
    new_hour = new_absolute_hour % 24

    did_full_rest = days_advanced > 0

    t["hour"] = new_hour
    t["minute"] = new_minute
    t["time_of_day"] = _time_of_day(new_hour)

    if days_advanced:
        t["day"] = old_day + days_advanced
        t["day_of_week"] = (t.get("day_of_week", 4) + days_advanced) % 7
        # Season cycles every 90 campaign days
        season_idx = ((t["day"] - 1) // 90) % 4
        t["season"] = SEASONS[season_idx]

    return t, did_full_rest


def format_time(time_state: dict) -> str:
    """Return a human-readable Golarion time string."""
    hour = time_state.get("hour", 8)
    minute = time_state.get("minute", 0)
    tod = time_state.get("time_of_day", "morning").title()
    day_name = DAYS_OF_WEEK[time_state.get("day_of_week", 4)]
    day_num = time_state.get("day", 1)
    season = time_state.get("season", "Spring")
    return f"{day_name}, Day {day_num}  •  {tod}  ({hour:02d}:{minute:02d})  •  {season}"
