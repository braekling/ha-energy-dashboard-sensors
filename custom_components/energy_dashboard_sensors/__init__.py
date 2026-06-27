"""The Energy Dashboard Sensors integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.energy.data import async_get_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import EnergyDashboardCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


def _resolve_update_interval(entry: ConfigEntry) -> timedelta:
    """Return the configured update interval, falling back to the default."""
    minutes = entry.options.get(CONF_SCAN_INTERVAL_MINUTES)
    if minutes:
        return timedelta(minutes=minutes)
    return DEFAULT_SCAN_INTERVAL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Dashboard Sensors from a config entry."""
    coordinator = EnergyDashboardCoordinator(hass, _resolve_update_interval(entry))
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Refresh immediately when the user changes their energy dashboard setup.
    manager = await async_get_manager(hass)
    manager.async_listen_updates(coordinator.async_request_refresh)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
