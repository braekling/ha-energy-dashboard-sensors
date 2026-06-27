"""Sensor platform for the Energy Dashboard Sensors integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
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


@dataclass(frozen=True, kw_only=True)
class EnergyDashboardSensorDescription(SensorEntityDescription):
    """Describes an energy dashboard sensor and whether it resets daily."""

    # When True the value is reported with state_class TOTAL and a last_reset
    # at the start of the local day (used for values that can decrease, like
    # the net grid balance). When False a daily-resetting total_increasing
    # value is assumed.
    resets_daily: bool = False


SENSOR_DESCRIPTIONS: tuple[EnergyDashboardSensorDescription, ...] = (
    EnergyDashboardSensorDescription(
        key=METRIC_TOTAL_CONSUMPTION,
        translation_key=METRIC_TOTAL_CONSUMPTION,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        icon="mdi:home-lightning-bolt",
    ),
    EnergyDashboardSensorDescription(
        key=METRIC_SOLAR_PRODUCTION,
        translation_key=METRIC_SOLAR_PRODUCTION,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        icon="mdi:solar-power",
    ),
    EnergyDashboardSensorDescription(
        key=METRIC_NET_FROM_GRID,
        translation_key=METRIC_NET_FROM_GRID,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        icon="mdi:transmission-tower",
        resets_daily=True,
    ),
    EnergyDashboardSensorDescription(
        key=METRIC_SOLAR_SELF_CONSUMPTION,
        translation_key=METRIC_SOLAR_SELF_CONSUMPTION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:solar-power-variant",
    ),
    EnergyDashboardSensorDescription(
        key=METRIC_SELF_SUFFICIENCY,
        translation_key=METRIC_SELF_SUFFICIENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:home-battery",
    ),
    EnergyDashboardSensorDescription(
        key=METRIC_LOW_CARBON_CONSUMPTION,
        translation_key=METRIC_LOW_CARBON_CONSUMPTION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:leaf",
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
        EnergyDashboardSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class EnergyDashboardSensor(
    CoordinatorEntity[EnergyDashboardCoordinator], SensorEntity
):
    """A single value derived from the Home Assistant Energy Dashboard."""

    _attr_has_entity_name = True
    entity_description: EnergyDashboardSensorDescription

    def __init__(
        self,
        coordinator: EnergyDashboardCoordinator,
        entry: ConfigEntry,
        description: EnergyDashboardSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Energy Dashboard",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value of the metric."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def last_reset(self) -> datetime | None:
        """Return the start of the local day for daily-resetting totals."""
        if self.entity_description.resets_daily:
            return dt_util.start_of_local_day()
        return None
