"""Data update coordinator for the Energy Dashboard Sensors integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.energy.data import EnergyPreferences, async_get_manager
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    METRIC_LOW_CARBON_CONSUMPTION,
    METRIC_NET_FROM_GRID,
    METRIC_SELF_SUFFICIENCY,
    METRIC_SOLAR_PRODUCTION,
    METRIC_SOLAR_SELF_CONSUMPTION,
    METRIC_TOTAL_CONSUMPTION,
)
from .periods import PERIODS, period_start
from .energy_math import (
    PeriodFlows,
    fossil_energy,
    low_carbon_consumption_percent,
    net_from_grid,
    self_sufficiency_percent,
    solar_self_consumption_percent,
    summarize_day,
    total_home_consumption,
)

_LOGGER = logging.getLogger(__name__)

CO2_SIGNAL_PLATFORM = "co2signal"


class StatisticIds:
    """Statistic ids referenced by the configured energy sources."""

    def __init__(self) -> None:
        """Initialize empty id collections."""
        self.from_grid: list[str] = []
        self.to_grid: list[str] = []
        self.solar: list[str] = []
        self.to_battery: list[str] = []
        self.from_battery: list[str] = []

    @property
    def all_ids(self) -> set[str]:
        """Return every referenced statistic id."""
        return set(
            self.from_grid
            + self.to_grid
            + self.solar
            + self.to_battery
            + self.from_battery
        )


def _collect_statistic_ids(prefs: EnergyPreferences) -> StatisticIds:
    """Extract grid/solar/battery statistic ids from energy preferences.

    The preferences are user-editable storage and individual keys may be
    missing (e.g. a grid source with only a feed-in or only a consumption
    meter), so every access is defensive and empty ids are skipped.
    """
    ids = StatisticIds()
    for source in prefs["energy_sources"]:
        source_type = source.get("type")
        if source_type == "solar":
            _append_if_present(ids.solar, source.get("stat_energy_from"))
        elif source_type == "battery":
            _append_if_present(ids.to_battery, source.get("stat_energy_to"))
            _append_if_present(ids.from_battery, source.get("stat_energy_from"))
        elif source_type == "grid":
            for flow in source.get("flow_from") or []:
                _append_if_present(ids.from_grid, flow.get("stat_energy_from"))
            for flow in source.get("flow_to") or []:
                _append_if_present(ids.to_grid, flow.get("stat_energy_to"))
    return ids


def _append_if_present(target: list[str], stat_id: str | None) -> None:
    """Append a statistic id to the target list when it is set."""
    if stat_id:
        target.append(stat_id)


class EnergyDashboardCoordinator(
    DataUpdateCoordinator[dict[str, dict[str, float | None]]]
):
    """Coordinator that recomputes the energy dashboard metrics per period.

    ``data`` is keyed by period (daily/weekly/monthly/yearly), each holding a
    mapping of metric key to value.
    """

    def __init__(self, hass: HomeAssistant, update_interval: timedelta) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    def _find_co2_signal_entity(self) -> str | None:
        """Return the co2signal percentage entity id, mirroring the frontend."""
        registry = er.async_get(self.hass)
        for entry in registry.entities.values():
            if entry.platform != CO2_SIGNAL_PLATFORM:
                continue
            state = self.hass.states.get(entry.entity_id)
            if state is None:
                continue
            if state.attributes.get("unit_of_measurement") != "%":
                continue
            return entry.entity_id
        return None

    async def _async_update_data(self) -> dict[str, dict[str, float | None]]:
        """Fetch statistics for each period and compute the metrics."""
        manager = await async_get_manager(self.hass)
        prefs = manager.data
        if not prefs or not prefs["energy_sources"]:
            raise UpdateFailed(
                "Energy dashboard is not configured. Set up the Energy "
                "Dashboard in Settings before using this integration."
            )

        ids = _collect_statistic_ids(prefs)
        if not ids.from_grid and not ids.solar:
            raise UpdateFailed(
                "No grid or solar sources found in the energy preferences."
            )

        co2_entity = self._find_co2_signal_entity()
        recorder = get_instance(self.hass)
        now = dt_util.now()

        result: dict[str, dict[str, float | None]] = {}
        for period in PERIODS:
            start = period_start(period.key, now)

            energy_stats = await recorder.async_add_executor_job(
                statistics_during_period,
                self.hass,
                start,
                now,
                ids.all_ids,
                period.resolution,
                {"energy": UnitOfEnergy.KILO_WATT_HOUR},
                {"change"},
            )

            co2_stats: dict = {}
            if co2_entity:
                co2_stats = await recorder.async_add_executor_job(
                    statistics_during_period,
                    self.hass,
                    start,
                    now,
                    {co2_entity},
                    period.resolution,
                    None,
                    {"mean"},
                )

            result[period.key] = self._compute_metrics(
                ids, energy_stats, co2_entity, co2_stats
            )

        return result

    def _compute_metrics(
        self,
        ids: StatisticIds,
        energy_stats: dict,
        co2_entity: str | None,
        co2_stats: dict,
    ) -> dict[str, float | None]:
        """Build per-period flows and derive the dashboard metrics."""
        change_by_id: dict[str, dict[float, float]] = {}
        timestamps: set[float] = set()
        for stat_id, rows in energy_stats.items():
            per_period: dict[float, float] = {}
            for row in rows:
                change = row.get("change")
                if change is None:
                    continue
                start_ts = row["start"]
                per_period[start_ts] = per_period.get(start_ts, 0.0) + change
                timestamps.add(start_ts)
            change_by_id[stat_id] = per_period

        def _sum_for(stat_ids: list[str], start_ts: float) -> float:
            return sum(
                change_by_id.get(stat_id, {}).get(start_ts, 0.0)
                for stat_id in stat_ids
            )

        ordered_timestamps = sorted(timestamps)
        periods: list[PeriodFlows] = [
            PeriodFlows(
                from_grid=_sum_for(ids.from_grid, ts),
                to_grid=_sum_for(ids.to_grid, ts),
                solar=_sum_for(ids.solar, ts),
                to_battery=_sum_for(ids.to_battery, ts),
                from_battery=_sum_for(ids.from_battery, ts),
            )
            for ts in ordered_timestamps
        ]

        summary = summarize_day(periods)

        fossil_grid_energy: float | None = None
        if co2_entity:
            co2_mean_by_ts: dict[float, float] = {}
            for row in co2_stats.get(co2_entity, []):
                mean = row.get("mean")
                if mean is not None:
                    co2_mean_by_ts[row["start"]] = mean

            grid_from_series = [
                _sum_for(ids.from_grid, ts) for ts in ordered_timestamps
            ]
            co2_percent_series = [
                co2_mean_by_ts.get(ts, 100.0) for ts in ordered_timestamps
            ]
            fossil_grid_energy = fossil_energy(grid_from_series, co2_percent_series)

        return {
            METRIC_TOTAL_CONSUMPTION: total_home_consumption(summary),
            METRIC_SOLAR_PRODUCTION: summary.total_solar,
            METRIC_NET_FROM_GRID: net_from_grid(summary),
            METRIC_SOLAR_SELF_CONSUMPTION: solar_self_consumption_percent(summary),
            METRIC_SELF_SUFFICIENCY: self_sufficiency_percent(summary),
            METRIC_LOW_CARBON_CONSUMPTION: low_carbon_consumption_percent(
                summary, fossil_grid_energy
            ),
        }
