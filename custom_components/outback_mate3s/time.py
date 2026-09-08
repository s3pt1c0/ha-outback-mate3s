"""Writable Grid Use Interval times for OutBack MATE3s."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN
from .coordinator import OutbackMate3sCoordinator


@dataclass(frozen=True)
class IntervalTimeSpec:
    interval: int
    field: str
    name: str


TIME_SPECS = (
    IntervalTimeSpec(1, "weekday_start", "Grid Use Interval 1 Weekday Start"),
    IntervalTimeSpec(1, "weekday_stop", "Grid Use Interval 1 Weekday Stop"),
    IntervalTimeSpec(1, "weekend_start", "Grid Use Interval 1 Weekend Start"),
    IntervalTimeSpec(1, "weekend_stop", "Grid Use Interval 1 Weekend Stop"),
    IntervalTimeSpec(2, "weekday_start", "Grid Use Interval 2 Weekday Start"),
    IntervalTimeSpec(2, "weekday_stop", "Grid Use Interval 2 Weekday Stop"),
)


class GridUseIntervalTime(CoordinatorEntity[OutbackMate3sCoordinator], TimeEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: OutbackMate3sCoordinator, spec: IntervalTimeSpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        entry = coordinator.config_entry
        self._attr_name = spec.name
        self._attr_unique_id = f"{entry.entry_id}_grid_use_interval_{spec.interval}_{spec.field}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="OutBack Power",
            model="MATE3s / Radian",
            name="OutBack MATE3s",
        )

    @property
    def native_value(self) -> time | None:
        gateway = self.coordinator.data.get("gateway_control") or {}
        return gateway.get(f"interval_{self._spec.interval}_{self._spec.field}")

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.device.async_set_grid_use_interval_time(
            self._spec.interval, self._spec.field, value
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry: OutbackConfigEntry, async_add_entities) -> None:
    """Set up Grid Use Interval time entities."""
    coordinator = entry.runtime_data
    if coordinator.data.get("gateway_control") is not None:
        async_add_entities([GridUseIntervalTime(coordinator, spec) for spec in TIME_SPECS])
