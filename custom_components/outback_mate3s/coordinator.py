"""Data coordinator for OutBack MATE3s."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusUnit

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .device import OutbackMate3sDevice, OutbackProtocolError

_LOGGER = logging.getLogger(__name__)


class OutbackMate3sCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the MATE3s real-time blocks."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unit: ModbusUnit,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.config_entry = entry
        self.device = OutbackMate3sDevice(unit)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.device.async_read_all()
        except (ModbusError, OutbackProtocolError, TimeoutError) as err:
            raise UpdateFailed(str(err)) from err
