import pytest
from game.game_time import initial_time, advance_time, format_time, DAYS_OF_WEEK, SEASONS


# ---------------------------------------------------------------------------
# initial_time
# ---------------------------------------------------------------------------

def test_initial_time_is_morning():
    t = initial_time()
    assert t["time_of_day"] == "morning"
    assert t["hour"] == 8

def test_initial_time_is_fireday():
    t = initial_time()
    assert DAYS_OF_WEEK[t["day_of_week"]] == "Fireday"

def test_initial_time_is_spring():
    t = initial_time()
    assert t["season"] == "Spring"

def test_initial_time_is_day_one():
    t = initial_time()
    assert t["day"] == 1


# ---------------------------------------------------------------------------
# advance_time — same day
# ---------------------------------------------------------------------------

def test_advance_within_same_day():
    t = initial_time()  # 08:00
    new_t, did_rest = advance_time(t, 60)  # +1 hour
    assert new_t["hour"] == 9
    assert new_t["minute"] == 0
    assert did_rest is False

def test_advance_minutes_only():
    t = initial_time()
    new_t, did_rest = advance_time(t, 30)
    assert new_t["hour"] == 8
    assert new_t["minute"] == 30
    assert did_rest is False

def test_advance_to_midday():
    t = initial_time()  # 08:00
    new_t, _ = advance_time(t, 240)  # +4 hours → 12:00
    assert new_t["time_of_day"] == "midday"


# ---------------------------------------------------------------------------
# advance_time — day rollover
# ---------------------------------------------------------------------------

def test_advance_crosses_midnight_triggers_rest():
    t = initial_time()  # 08:00 day 1
    _, did_rest = advance_time(t, 480)  # +8 hours → 16:00 same day, no rest
    assert did_rest is False

    _, did_rest = advance_time(t, 960)  # +16 hours → 00:00 next day → rest
    assert did_rest is True

def test_advance_increments_day():
    t = initial_time()  # 08:00 day 1
    new_t, _ = advance_time(t, 960)  # crosses midnight
    assert new_t["day"] == 2

def test_advance_increments_day_of_week():
    t = initial_time()  # Fireday (index 4)
    new_t, _ = advance_time(t, 960)  # +1 day → Starday (index 5)
    assert DAYS_OF_WEEK[new_t["day_of_week"]] == "Starday"

def test_day_of_week_wraps_after_7():
    t = initial_time()  # Fireday (index 4)
    new_t, _ = advance_time(t, 4 * 24 * 60)  # +4 days → index (4+4)%7 = 1 → Toilday
    assert DAYS_OF_WEEK[new_t["day_of_week"]] == "Toilday"


# ---------------------------------------------------------------------------
# advance_time — season rollover
# ---------------------------------------------------------------------------

def test_season_changes_after_90_days():
    t = initial_time()  # Spring, day 1
    # Jump 90 days forward (90 * 24 * 60 minutes)
    new_t, _ = advance_time(t, 90 * 24 * 60)
    assert new_t["season"] == "Summer"

def test_season_cycles_all_four():
    t = initial_time()
    seasons_seen = set()
    for i in range(4):
        new_t, _ = advance_time(t, i * 90 * 24 * 60)
        seasons_seen.add(new_t["season"])
    assert seasons_seen == set(SEASONS)


# ---------------------------------------------------------------------------
# format_time
# ---------------------------------------------------------------------------

def test_format_time_contains_day_name():
    t = initial_time()
    assert "Fireday" in format_time(t)

def test_format_time_contains_season():
    t = initial_time()
    assert "Spring" in format_time(t)

def test_format_time_contains_hour():
    t = initial_time()
    assert "08:00" in format_time(t)

def test_format_time_contains_day_number():
    t = initial_time()
    assert "Day 1" in format_time(t)
