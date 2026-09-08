"""Writable selects for OutBack MATE3s."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN
from .coordinator import OutbackMate3sCoordinator


class InverterModeSelect(CoordinatorEntity[OutbackMate3sCoordinator], SelectEntity):
    """Command the Radian inverter mode."""

    _attr_has_entity_name = True
    _attr_name = "Inverter Mode"
    _attr_options = ["Off", "Search", "On"]
    _attr_icon = "mdi:power-settings"

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_inverter_mode_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="OutBack Power",
            model="MATE3s / Radian",
            name="OutBack MATE3s",
        )

    @property
    def current_option(self) -> str | None:
        control = self.coordinator.data.get("system_control") or {}
        value = control.get("inverter_mode")
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.device.async_set_inverter_mode(option)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry: OutbackConfigEntry, async_add_entities) -> None:
    """Set up OutBack selects."""
    coordinator = entry.runtime_data
    if coordinator.data.get("system_control") is not None:
        async_add_entities([InverterModeSelect(coordinator)])
