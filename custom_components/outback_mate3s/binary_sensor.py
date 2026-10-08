"""Binary sensors for OutBack MATE3s."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN, GRID_PRESENT_MIN_VOLTAGE
from .coordinator import OutbackMate3sCoordinator


def grid_present(radian: dict[str, Any] | None) -> bool | None:
    """Grid voltage on both legs of a split-phase Radian (DID 64115).

    True when Grid L1 Voltage (Start 12) and Grid L2 Voltage (Start 19) are both
    above GRID_PRESENT_MIN_VOLTAGE. None (unavailable) when the Radian has the
    generator input selected, or a voltage is missing or a SunSpec placeholder
    (a negative value).
    """
    if not radian or radian.get("ac_input_selection") != "Grid":
        return None
    l1 = radian.get("l1_grid_voltage")
    l2 = radian.get("l2_grid_voltage")
    if l1 is None or l2 is None or l1 < 0 or l2 < 0:
        return None
    return l1 > GRID_PRESENT_MIN_VOLTAGE and l2 > GRID_PRESENT_MIN_VOLTAGE


async def async_setup_entry(hass, entry: OutbackConfigEntry, async_add_entities) -> None:
    """Set up MATE3s binary sensors."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [OutbackModbusConnectedSensor(coordinator)]

    radians = coordinator.data.get("radians", {})
    if len(radians) <= 1 and coordinator.data.get("radian") is not None:
        entities.append(OutbackGridPresentSensor(coordinator, None))
    elif len(radians) > 1:
        entities.extend(OutbackGridPresentSensor(coordinator, port) for port in sorted(radians))

    async_add_entities(entities)


class _OutbackBinaryBase(CoordinatorEntity[OutbackMate3sCoordinator], BinarySensorEntity):
    """Base binary sensor on the OutBack MATE3s device."""

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


class OutbackModbusConnectedSensor(_OutbackBinaryBase):
    """On while the Modbus polls of the MATE3s succeed.

    The coordinator keeps the last data through two missed polls, so this turns
    off on the third consecutive failure (about 30 s), when the other entities
    become unavailable. It stays available itself so automations see 'off'.
    """

    _attr_name = "Modbus Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_modbus_connected"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.last_update_success)


class OutbackGridPresentSensor(_OutbackBinaryBase):
    """Grid voltage present on both legs (split-phase Radian, DID 64115)."""

    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: OutbackMate3sCoordinator, port: int | None) -> None:
        super().__init__(coordinator)
        self._port = port
        entry_id = coordinator.config_entry.entry_id
        if port is None:
            # Single Radian: same naming as the Radian sensors.
            self._attr_name = "Grid Present"
            self._attr_unique_id = f"{entry_id}_radian_grid_present"
        else:
            radian = coordinator.data.get("radians", {}).get(port, {})
            label = radian.get("label", f"Radian Port {port}")
            self._attr_name = f"{label} Grid Present"
            self._attr_unique_id = f"{entry_id}_radian{port}_grid_present"

    def _radian(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        if self._port is None:
            return data.get("radian")
        return data.get("radians", {}).get(self._port)

    @property
    def available(self) -> bool:
        return super().available and grid_present(self._radian()) is not None

    @property
    def is_on(self) -> bool | None:
        return grid_present(self._radian())
