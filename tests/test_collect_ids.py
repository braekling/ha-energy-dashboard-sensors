"""Regression tests for parsing energy preferences into statistic ids.

Requires Home Assistant to be importable (it is in any HA environment).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "custom_components")
)

from energy_dashboard_sensors.coordinator import (  # noqa: E402
    _collect_statistic_ids,
)


def test_grid_source_without_flows_does_not_raise():
    """A grid source missing flow_from/flow_to must be handled gracefully."""
    prefs = {
        "energy_sources": [
            {"type": "grid"},  # no flow_from / flow_to keys at all
            {"type": "grid", "flow_to": [{"stat_energy_to": "sensor.feed_in"}]},
        ],
        "device_consumption": [],
    }
    ids = _collect_statistic_ids(prefs)
    assert ids.from_grid == []
    assert ids.to_grid == ["sensor.feed_in"]


def test_new_flat_grid_format_is_parsed():
    """HA 2025+ stores grid import/export directly on the source."""
    prefs = {
        "energy_sources": [
            {
                "type": "grid",
                "stat_energy_from": "sensor.stromzaehler",
                "stat_energy_to": "sensor.stromzaehler_einspeisung",
            },
            {"type": "solar", "stat_energy_from": "sensor.dtu"},
            {"type": "solar", "stat_energy_from": "sensor.solakon"},
            {
                "type": "battery",
                "stat_energy_to": "sensor.bat_charge",
                "stat_energy_from": "sensor.bat_discharge",
            },
        ],
        "device_consumption": [],
    }
    ids = _collect_statistic_ids(prefs)
    assert ids.from_grid == ["sensor.stromzaehler"]
    assert ids.to_grid == ["sensor.stromzaehler_einspeisung"]
    assert ids.solar == ["sensor.dtu", "sensor.solakon"]
    assert ids.to_battery == ["sensor.bat_charge"]
    assert ids.from_battery == ["sensor.bat_discharge"]


def test_full_source_set_is_parsed():
    """All source types contribute their statistic ids."""
    prefs = {
        "energy_sources": [
            {
                "type": "grid",
                "flow_from": [{"stat_energy_from": "sensor.import"}],
                "flow_to": [{"stat_energy_to": "sensor.export"}],
            },
            {"type": "solar", "stat_energy_from": "sensor.pv"},
            {
                "type": "battery",
                "stat_energy_to": "sensor.bat_charge",
                "stat_energy_from": "sensor.bat_discharge",
            },
            {"type": "gas", "stat_energy_from": "sensor.gas"},  # ignored
        ],
        "device_consumption": [],
    }
    ids = _collect_statistic_ids(prefs)
    assert ids.from_grid == ["sensor.import"]
    assert ids.to_grid == ["sensor.export"]
    assert ids.solar == ["sensor.pv"]
    assert ids.to_battery == ["sensor.bat_charge"]
    assert ids.from_battery == ["sensor.bat_discharge"]


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
