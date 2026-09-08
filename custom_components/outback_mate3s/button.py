"""Manual refresh button for OutBack MATE3s control/configuration data."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN
from .coordinator import OutbackMate3sCoordinator


class RefreshControlDataButton(
    CoordinatorEntity[OutbackMate3sCoordinator], ButtonEntity
):
    """Immediately re-read all currently exposed writable settings."""

    _attr_has_entity_name = True
    _attr_name = "Refresh Control Data"
    _attr_icon = "mdi:database-refresh"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_refresh_control_data"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="OutBack Power",
            model="MATE3s / Radian",
            name="OutBack MATE3s",
        )

    async def async_press(self) -> None:
        """Force a fresh read of control/configuration registers now."""
        await self.coordinator.async_refresh_control_data()


async def async_setup_entry(
    hass, entry: OutbackConfigEntry, async_add_entities
) -> None:
    """Set up the manual control-data refresh button."""
    async_add_entities([RefreshControlDataButton(entry.runtime_data)])
