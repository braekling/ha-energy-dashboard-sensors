"""Constants for the Energy Dashboard Sensors integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "energy_dashboard_sensors"

# Config / options keys
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
MIN_SCAN_INTERVAL_MINUTES = 1
MAX_SCAN_INTERVAL_MINUTES = 60

# Keys for the metrics produced by the coordinator. These match the values
# shown on the Home Assistant Energy Dashboard for the current day.
METRIC_TOTAL_CONSUMPTION = "total_consumption"
METRIC_SOLAR_PRODUCTION = "solar_production"
METRIC_NET_FROM_GRID = "net_from_grid"
METRIC_SOLAR_SELF_CONSUMPTION = "solar_self_consumption"
METRIC_SELF_SUFFICIENCY = "self_sufficiency"
METRIC_LOW_CARBON_CONSUMPTION = "low_carbon_consumption"
