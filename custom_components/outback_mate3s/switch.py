"""Writable switches for OutBack MATE3s."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN
from .coordinator import OutbackMate3sCoordinator


class _Base(CoordinatorEntity[OutbackMate3sCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="OutBack Power",
            model="MATE3s / Radian",
            name="OutBack MATE3s",
        )


class GridUseSwitch(_Base, SwitchEntity):
    _attr_name = "Grid Use"
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_grid_use_control"

    @property
    def is_on(self) -> bool | None:
        radians = self.coordinator.data.get("radians", {})
        states = [
            radian.get("ac_input_state_raw")
            for radian in radians.values()
            if radian.get("ac_input_state_raw") is not None
        ]
        if not states:
            radian = self.coordinator.data.get("radian") or {}
            state = radian.get("ac_input_state_raw")
            return bool(state) if state is not None else None
        if all(state == states[0] for state in states):
            return bool(states[0])
        # A stacked system should normally agree. Show unknown rather than
        # claiming Grid Use/Drop when individual Radians disagree.
        return None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.async_set_grid_use(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.async_set_grid_use(False)
        await self.coordinator.async_request_refresh()


class RadianGridTieSwitch(_Base, SwitchEntity):
    _attr_name = "Grid Tie"
    _attr_icon = "mdi:transmission-tower-export"

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_grid_tie_control"

    @property
    def is_on(self) -> bool | None:
        control = self.coordinator.data.get("system_control") or {}
        return control.get("grid_tie_enabled")

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.async_set_grid_tie(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.async_set_grid_tie(False)
        await self.coordinator.async_request_refresh()


class CCGridTieSwitch(_Base, SwitchEntity):
    """Grid Tie Mode for one FM100/FM80."""

    def __init__(self, coordinator: OutbackMate3sCoordinator, port: int, label: str) -> None:
        super().__init__(coordinator)
        self._port = port
        self._attr_name = f"{label} Grid Tie Mode"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cc{port}_grid_tie_control"
        self._attr_icon = "mdi:solar-power-variant"

    @property
    def is_on(self) -> bool | None:
        config = self.coordinator.data.get("charge_controller_configs", {}).get(self._port, {})
        return config.get("grid_tie_mode")

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.async_set_charge_controller_grid_tie(self._port, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.async_set_charge_controller_grid_tie(self._port, False)
        await self.coordinator.async_request_refresh()


class GridUseIntervalSwitch(_Base, SwitchEntity):
    def __init__(self, coordinator: OutbackMate3sCoordinator, interval: int) -> None:
        super().__init__(coordinator)
        self._interval = interval
        self._attr_name = f"Grid Use Interval {interval}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_grid_use_interval_{interval}"
        self._attr_icon = "mdi:timer-cog"

    @property
    def is_on(self) -> bool | None:
        gateway = self.coordinator.data.get("gateway_control") or {}
        return gateway.get(f"interval_{self._interval}_enabled")

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.async_set_grid_use_interval_enabled(self._interval, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.async_set_grid_use_interval_enabled(self._interval, False)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry: OutbackConfigEntry, async_add_entities) -> None:
    """Set up OutBack switches."""
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = []

    if coordinator.data.get("radians") or coordinator.data.get("radian") is not None:
        entities.append(GridUseSwitch(coordinator))
    if coordinator.data.get("system_control") is not None:
        entities.append(RadianGridTieSwitch(coordinator))

    for port in sorted(coordinator.data.get("charge_controller_configs", {})):
        realtime = coordinator.data.get("charge_controllers", {}).get(port, {})
        label = realtime.get("label", f"Charge Controller Port {port}")
        entities.append(CCGridTieSwitch(coordinator, port, label))

    if coordinator.data.get("gateway_control") is not None:
        entities.extend((GridUseIntervalSwitch(coordinator, 1), GridUseIntervalSwitch(coordinator, 2)))

    async_add_entities(entities)
