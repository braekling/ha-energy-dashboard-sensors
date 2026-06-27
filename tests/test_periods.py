"""Unit tests for the period helpers."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "energy_dashboard_sensors",
    ),
)

from periods import (  # noqa: E402
    PERIOD_DAILY,
    PERIOD_MONTHLY,
    PERIOD_WEEKLY,
    PERIOD_YEARLY,
    PERIODS,
    period_start,
)

# Saturday, 2026-06-27 14:30 UTC.
NOW = datetime(2026, 6, 27, 14, 30, tzinfo=timezone.utc)


def test_resolution_matches_dashboard_suggested_period():
    resolutions = {p.key: p.resolution for p in PERIODS}
    assert resolutions[PERIOD_DAILY] == "hour"
    assert resolutions[PERIOD_WEEKLY] == "day"
    assert resolutions[PERIOD_MONTHLY] == "day"
    assert resolutions[PERIOD_YEARLY] == "month"


def test_period_start_daily():
    start = period_start(PERIOD_DAILY, NOW)
    assert (start.year, start.month, start.day) == (2026, 6, 27)
    assert (start.hour, start.minute, start.second) == (0, 0, 0)


def test_period_start_weekly_is_monday():
    start = period_start(PERIOD_WEEKLY, NOW)
    # The Monday of that week is 2026-06-22.
    assert (start.year, start.month, start.day) == (2026, 6, 22)
    assert start.weekday() == 0
    assert (start.hour, start.minute) == (0, 0)


def test_period_start_monthly():
    start = period_start(PERIOD_MONTHLY, NOW)
    assert (start.year, start.month, start.day) == (2026, 6, 1)
    assert (start.hour, start.minute) == (0, 0)


def test_period_start_yearly():
    start = period_start(PERIOD_YEARLY, NOW)
    assert (start.year, start.month, start.day) == (2026, 1, 1)
    assert (start.hour, start.minute) == (0, 0)


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"PASS {name}")
            except AssertionError as err:
                failures += 1
                print(f"FAIL {name}: {err}")
    sys.exit(1 if failures else 0)
