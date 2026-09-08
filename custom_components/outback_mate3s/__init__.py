"""OutBack MATE3s integration."""

from __future__ import annotations

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTcpParams

from .const import CONF_HOST, CONF_PORT, CONF_UNIT_ID
from .coordinator import OutbackMate3sCoordinator

PLATFORMS = [Platform.SENSOR]

type OutbackConfigEntry = ConfigEntry[OutbackMate3sCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OutbackConfigEntry,
) -> bool:
    """Set up OutBack MATE3s from a config entry."""
    params = ModbusTcpParams(
        host=str(entry.data[CONF_HOST]),
        port=int(entry.data[CONF_PORT]),
    )
    unit = async_get_unit(
        hass,
        entry,
        params,
        int(entry.data[CONF_UNIT_ID]),
    )

    coordinator = OutbackMate3sCoordinator(hass, entry, unit)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: OutbackConfigEntry,
) -> bool:
    """Unload the integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
