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
        self._consecutive_failures = 0

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.device.async_read_all()
            self._consecutive_failures = 0
            return data
        except (ModbusError, OutbackProtocolError, TimeoutError) as err:
            self._consecutive_failures += 1
            # The MATE3s can occasionally miss one Modbus transaction. Preserve
            # the last-good data for up to two polling cycles so a single missed
            # response does not make every entity flap to unavailable. A real
            # outage still becomes unavailable on the third consecutive failure.
            if self.data is not None and self._consecutive_failures < 3:
                _LOGGER.warning(
                    "Transient MATE3s Modbus failure %s/3; keeping last data: %s",
                    self._consecutive_failures,
                    err,
                )
                return self.data
            raise UpdateFailed(str(err)) from err

    async def async_refresh_control_data(self) -> None:
        """Force an immediate refresh of writable/configuration values."""
        self.device.force_control_refresh()
        await self.async_request_refresh()
