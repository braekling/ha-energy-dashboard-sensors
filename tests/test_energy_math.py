"""Unit tests for the pure energy calculations.

These tests do not require Home Assistant. Run with: python -m pytest tests/
or simply: python tests/test_energy_math.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "energy_dashboard_sensors",
    ),
)

from energy_math import (  # noqa: E402
    PeriodFlows,
    fossil_energy,
    low_carbon_consumption_percent,
    net_from_grid,
    self_sufficiency_percent,
    solar_self_consumption_percent,
    summarize_day,
    total_home_consumption,
)

APPROX = 1e-6


def _close(a: float, b: float) -> bool:
    return abs(a - b) < 1e-4


def test_dashboard_daily_totals_match_screenshot():
    """Reproduce the daily aggregate figures from the example dashboard."""
    day = [
        PeriodFlows(
            from_grid=0.97,
            to_grid=0.46,
            solar=7.46,
            to_battery=3.77,
            from_battery=1.27,
        )
    ]
    summary = summarize_day(day)

    assert _close(total_home_consumption(summary), 5.47)
    assert _close(summary.total_solar, 7.46)
    assert _close(net_from_grid(summary), 0.51)

    self_suff = self_sufficiency_percent(summary)
    assert self_suff is not None and round(self_suff) == 82


def test_net_from_grid_can_be_negative():
    """Net export produces a negative net-from-grid value."""
    summary = summarize_day([PeriodFlows(from_grid=1.0, to_grid=3.0, solar=5.0)])
    assert _close(net_from_grid(summary), -2.0)


def test_self_sufficiency_none_without_consumption():
    """Self-sufficiency is undefined when there is no home consumption."""
    summary = summarize_day([PeriodFlows()])
    assert self_sufficiency_percent(summary) is None


def test_solar_self_consumption_without_battery():
    """Without a battery the ratio is used_solar / solar."""
    # solar 10, export 4 -> 6 used at home, used_solar = 6 -> 60%.
    summary = summarize_day([PeriodFlows(from_grid=0.0, to_grid=4.0, solar=10.0)])
    assert not summary.has_battery
    value = solar_self_consumption_percent(summary)
    assert value is not None and _close(value, 60.0)


def test_solar_self_consumption_none_without_solar():
    """Solar self-consumption is undefined without any production."""
    summary = summarize_day([PeriodFlows(from_grid=2.0)])
    assert solar_self_consumption_percent(summary) is None


def test_solar_self_consumption_battery_lifo_credits_stored_solar():
    """Solar charged into the battery and later discharged counts as consumed.

    Period A: 4 kWh solar, 3 kWh into battery, 1 kWh used directly.
    Period B: 3 kWh discharged from the battery and fully consumed.
    A naive used_solar/solar ratio would report 25%, but the LIFO tracking
    correctly credits the stored solar, giving 100%.
    """
    day = [
        PeriodFlows(solar=4.0, to_battery=3.0),
        PeriodFlows(from_battery=3.0),
    ]
    summary = summarize_day(day)
    assert summary.has_battery
    value = solar_self_consumption_percent(summary)
    assert value is not None and _close(value, 100.0)


def test_solar_self_consumption_battery_lifo_excludes_grid_charge():
    """Battery charged from the grid does not inflate solar self-consumption.

    Period A (night): 2 kWh imported, all into the battery.
    Period B (day): 5 kWh solar, 1 kWh exported, 2 kWh battery discharge.
    Solar consumed = 4 (direct), solar returned = 1 -> 4 / 5 = 80%. The 2 kWh
    battery discharge is grid-sourced and must be ignored.
    """
    day = [
        PeriodFlows(from_grid=2.0, to_battery=2.0),
        PeriodFlows(to_grid=1.0, solar=5.0, from_battery=2.0),
    ]
    summary = summarize_day(day)
    value = solar_self_consumption_percent(summary)
    assert value is not None and _close(value, 80.0)


def test_fossil_energy_weighting():
    """Fossil energy is grid import weighted by the fossil percentage."""
    # 1 kWh at 50% fossil + 2 kWh at 25% fossil = 0.5 + 0.5 = 1.0 kWh.
    assert _close(fossil_energy([1.0, 2.0], [50.0, 25.0]), 1.0)
    # Missing percentage assumes 100% fossil.
    assert _close(fossil_energy([1.0, 1.0], [0.0]), 1.0)


def test_low_carbon_consumption_percent():
    """Low-carbon percentage uses from_grid + max(0, solar - to_grid)."""
    summary = summarize_day([PeriodFlows(from_grid=0.97, to_grid=0.46, solar=7.46)])
    # total_energy_consumed = 0.97 + (7.46 - 0.46) = 7.97
    # fossil 0.558 -> (1 - 0.558/7.97)*100 = 93.0%
    value = low_carbon_consumption_percent(summary, 0.558)
    assert value is not None and round(value) == 93


def test_low_carbon_none_without_signal():
    """Low-carbon consumption is undefined without a fossil value."""
    summary = summarize_day([PeriodFlows(from_grid=1.0, solar=2.0)])
    assert low_carbon_consumption_percent(summary, None) is None


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
