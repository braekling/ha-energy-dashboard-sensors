"""Sensor platform for the Energy Dashboard Sensors integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
from .coordinator import EnergyDashboardCoordinator
from .periods import PERIODS, period_start


@dataclass(frozen=True, kw_only=True)
class MetricDefinition:
    """Static description of a metric, independent of the time period."""

    key: str
    icon: str
    device_class: SensorDeviceClass | None = None
    native_unit_of_measurement: str | None = None
    suggested_display_precision: int = 0
    # Energy balances can decrease (net export), so they are reported as a
    # resetting TOTAL with last_reset instead of TOTAL_INCREASING.
    is_balance: bool = False


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        key=METRIC_TOTAL_CONSUMPTION,
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    MetricDefinition(
        key=METRIC_SOLAR_PRODUCTION,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    MetricDefinition(
        key=METRIC_NET_FROM_GRID,
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        is_balance=True,
    ),
    MetricDefinition(
        key=METRIC_SOLAR_SELF_CONSUMPTION,
        icon="mdi:solar-power-variant",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    MetricDefinition(
        key=METRIC_SELF_SUFFICIENCY,
        icon="mdi:home-battery",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    MetricDefinition(
        key=METRIC_LOW_CARBON_CONSUMPTION,
        icon="mdi:leaf",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the energy dashboard sensors from a config entry."""
    coordinator: EnergyDashboardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EnergyDashboardSensor(coordinator, entry, metric, period.key)
        for metric in METRIC_DEFINITIONS
        for period in PERIODS
    )


class EnergyDashboardSensor(
    CoordinatorEntity[EnergyDashboardCoordinator], SensorEntity
):
    """A single energy dashboard metric for a given time period."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyDashboardCoordinator,
        entry: ConfigEntry,
        metric: MetricDefinition,
        period_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._metric = metric
        self._period_key = period_key

        self._attr_unique_id = f"{entry.entry_id}_{metric.key}_{period_key}"
        self._attr_translation_key = f"{metric.key}_{period_key}"
        self._attr_icon = metric.icon
        self._attr_device_class = metric.device_class
        self._attr_native_unit_of_measurement = metric.native_unit_of_measurement
        self._attr_suggested_display_precision = metric.suggested_display_precision

        if metric.device_class == SensorDeviceClass.ENERGY:
            self._attr_state_class = (
                SensorStateClass.TOTAL
                if metric.is_balance
                else SensorStateClass.TOTAL_INCREASING
            )
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Energy Dashboard",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value of the metric for this period."""
        if self.coordinator.data is None:
            return None
        period_data = self.coordinator.data.get(self._period_key, {})
        return period_data.get(self._metric.key)

    @property
    def last_reset(self) -> datetime | None:
        """Return the start of the period for resetting balance totals."""
        if self._metric.is_balance:
            return period_start(self._period_key, dt_util.now())
        return None
