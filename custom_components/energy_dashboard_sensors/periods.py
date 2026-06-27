"""Time period definitions for the energy dashboard sensors.

Each period mirrors a selectable range on the Home Assistant Energy Dashboard
(today, this week, this month, this year). The statistics resolution per period
follows the dashboard's own ``getSuggestedPeriod`` logic so the computed values
stay consistent with what the dashboard shows:
    range > 35 days -> "month", range > 2 days -> "day", otherwise "hour".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
PERIOD_MONTHLY = "monthly"
PERIOD_YEARLY = "yearly"


@dataclass(frozen=True)
class Period:
    """Describes a sensor time period."""

    key: str
    # Statistics resolution passed to the recorder for this period.
    resolution: str


PERIODS: tuple[Period, ...] = (
    Period(PERIOD_DAILY, "hour"),
    Period(PERIOD_WEEKLY, "day"),
    Period(PERIOD_MONTHLY, "day"),
    Period(PERIOD_YEARLY, "month"),
)


def period_start(period_key: str, now: datetime | None = None) -> datetime:
    """Return the local start datetime for the given period."""
    if now is None:
        now = dt_util.now()

    start_of_today = dt_util.start_of_local_day(now)

    if period_key == PERIOD_DAILY:
        return start_of_today
    if period_key == PERIOD_WEEKLY:
        return start_of_today - timedelta(days=now.weekday())
    if period_key == PERIOD_MONTHLY:
        return dt_util.start_of_local_day(now.replace(day=1))
    if period_key == PERIOD_YEARLY:
        return dt_util.start_of_local_day(now.replace(month=1, day=1))

    raise ValueError(f"Unknown period: {period_key}")
