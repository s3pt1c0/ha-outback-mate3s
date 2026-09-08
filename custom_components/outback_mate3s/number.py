"""Writable numeric controls for OutBack MATE3s."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN
from .coordinator import OutbackMate3sCoordinator


@dataclass(frozen=True)
class SystemNumberSpec:
    field: str
    name: str
    unit: str
    minimum: float
    maximum: float
    step: float


SYSTEM_NUMBERS = (
    SystemNumberSpec("sell_voltage", "Sell Voltage", UnitOfElectricPotential.VOLT, 44.0, 64.0, 0.1),
    SystemNumberSpec("sell_current_limit", "Sell Current Limit", UnitOfElectricCurrent.AMPERE, 0.0, 30.0, 0.1),
    SystemNumberSpec("grid_input_current_limit", "Grid Input Current Limit", UnitOfElectricCurrent.AMPERE, 5.0, 55.0, 0.1),
    SystemNumberSpec("generator_input_current_limit", "Generator Input Current Limit", UnitOfElectricCurrent.AMPERE, 5.0, 55.0, 0.1),
    SystemNumberSpec("charger_current_limit", "Charger Current Limit", UnitOfElectricCurrent.AMPERE, 0.0, 30.0, 0.1),
)


@dataclass(frozen=True)
class CCNumberSpec:
    field: str
    name: str
    unit: str
    minimum: float
    maximum: float | None
    step: float


CC_NUMBERS = (
    CCNumberSpec("absorb_voltage", "Absorb Voltage", UnitOfElectricPotential.VOLT, 10.0, None, 0.1),
    CCNumberSpec("absorb_time", "Absorb Time", "h", 0.0, 24.0, 0.1),
    CCNumberSpec("absorb_end_amps", "Absorb End Amps", UnitOfElectricCurrent.AMPERE, 0.0, 55.0, 1.0),
    CCNumberSpec("rebulk_voltage", "Rebulk Voltage", UnitOfElectricPotential.VOLT, 10.0, None, 0.1),
    CCNumberSpec("float_voltage", "Float Voltage", UnitOfElectricPotential.VOLT, 10.0, None, 0.1),
    CCNumberSpec("bulk_current_limit", "Bulk Current Limit", UnitOfElectricCurrent.AMPERE, 5.0, None, 0.1),
)


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


class OutbackSystemNumber(_Base, NumberEntity):
    """One writable Radian/System Control numeric setting."""

    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: OutbackMate3sCoordinator, spec: SystemNumberSpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{spec.field}"
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_native_min_value = spec.minimum
        self._attr_native_max_value = spec.maximum
        self._attr_native_step = spec.step

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data.get("system_control") or {}
        value = data.get(self._spec.field)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.device.async_set_system_number(self._spec.field, value)
        await self.coordinator.async_request_refresh()


class OutbackCCNumber(_Base, NumberEntity):
    """One writable FM100/FM80 charger setting."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: OutbackMate3sCoordinator,
        port: int,
        label: str,
        spec: CCNumberSpec,
    ) -> None:
        super().__init__(coordinator)
        self._port = port
        self._spec = spec
        self._attr_name = f"{label} {spec.name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cc{port}_{spec.field}_control"
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_native_min_value = spec.minimum
        self._attr_native_step = spec.step

        if spec.maximum is not None:
            maximum = spec.maximum
        elif spec.field == "bulk_current_limit":
            maximum = 80.0 if label == "FM80" else 100.0
        else:
            maximum = 80.0 if label == "FM80" else 68.0
        self._attr_native_max_value = maximum

    @property
    def native_value(self) -> float | None:
        config = self.coordinator.data.get("charge_controller_configs", {}).get(self._port, {})
        value = config.get(self._spec.field)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.device.async_set_charge_controller_number(
            self._port, self._spec.field, value
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry: OutbackConfigEntry, async_add_entities) -> None:
    """Set up writable OutBack number entities."""
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = []

    if coordinator.data.get("system_control") is not None:
        entities.extend(OutbackSystemNumber(coordinator, spec) for spec in SYSTEM_NUMBERS)

    for port, config in sorted(coordinator.data.get("charge_controller_configs", {}).items()):
        realtime = coordinator.data.get("charge_controllers", {}).get(port, {})
        label = realtime.get("label", f"Charge Controller Port {port}")
        entities.extend(OutbackCCNumber(coordinator, port, label, spec) for spec in CC_NUMBERS)

    async_add_entities(entities)
