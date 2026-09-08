"""Sensors for OutBack MATE3s."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import DOMAIN, SHUNT_LABELS
from .coordinator import OutbackMate3sCoordinator


@dataclass(frozen=True, kw_only=True)
class OutbackSensorDescription(SensorEntityDescription):
    """Describe a MATE3s sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


RADIAN_SENSORS: tuple[OutbackSensorDescription, ...] = (
    OutbackSensorDescription(
        key="radian_mode",
        name="Radian Mode",
        icon="mdi:solar-power-variant",
        value_fn=lambda d: d["radian"]["mode"],
    ),
    OutbackSensorDescription(
        key="ac_input_state",
        name="AC Input State",
        icon="mdi:transmission-tower",
        value_fn=lambda d: d["radian"]["ac_input_state"],
    ),
    OutbackSensorDescription(
        key="radian_battery_voltage",
        name="Radian Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["battery_voltage"],
    ),
    OutbackSensorDescription(
        key="ac_frequency",
        name="AC Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["frequency"],
    ),
    OutbackSensorDescription(
        key="grid_l1_voltage",
        name="Grid L1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["radian"]["l1_grid_voltage"],
    ),
    OutbackSensorDescription(
        key="grid_l2_voltage",
        name="Grid L2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["radian"]["l2_grid_voltage"],
    ),
    OutbackSensorDescription(
        key="grid_l1_buy_current",
        name="Grid L1 Buy Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["l1_buy_current"],
    ),
    OutbackSensorDescription(
        key="grid_l2_buy_current",
        name="Grid L2 Buy Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["l2_buy_current"],
    ),
    OutbackSensorDescription(
        key="grid_l1_sell_current",
        name="Grid L1 Sell Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["l1_sell_current"],
    ),
    OutbackSensorDescription(
        key="grid_l2_sell_current",
        name="Grid L2 Sell Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["l2_sell_current"],
    ),
    OutbackSensorDescription(
        key="house_l1_current",
        name="House L1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["house_l1_current"],
    ),
    OutbackSensorDescription(
        key="house_l2_current",
        name="House L2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["house_l2_current"],
    ),
    OutbackSensorDescription(
        key="house_power",
        name="House Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["load_power"],
    ),
    OutbackSensorDescription(
        key="grid_buy_power",
        name="Grid Buy Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["buy_power"],
    ),
    OutbackSensorDescription(
        key="grid_sell_power",
        name="Grid Sell Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["sell_power"],
    ),
    OutbackSensorDescription(
        key="radian_output_power",
        name="Radian Output Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["output_power"],
    ),
    OutbackSensorDescription(
        key="radian_charge_power",
        name="Radian Charge Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["radian"]["charge_power"],
    ),
)

FNDC_SENSORS: tuple[OutbackSensorDescription, ...] = (
    OutbackSensorDescription(
        key="fndc_soc",
        name="FNDC SOC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["fndc"]["soc"],
    ),
    OutbackSensorDescription(
        key="fndc_battery_voltage",
        name="FNDC Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["fndc"]["battery_voltage"],
    ),
    OutbackSensorDescription(
        key="fndc_battery_current",
        name="FNDC Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["fndc"]["battery_current"],
    ),
    OutbackSensorDescription(
        key="fndc_net_power",
        name="FNDC Net Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d["fndc"]["net_power"],
    ),
    OutbackSensorDescription(
        key="fndc_days_since_full",
        name="FNDC Days Since Full",
        native_unit_of_measurement="days",
        suggested_display_precision=1,
        value_fn=lambda d: d["fndc"]["days_since_full"],
    ),
    OutbackSensorDescription(
        key="shunt_a_inverter",
        name=f"Shunt A - {SHUNT_LABELS['a']}",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["fndc"]["shunt_a_current"],
    ),
    OutbackSensorDescription(
        key="shunt_b_fm80",
        name=f"Shunt B - {SHUNT_LABELS['b']}",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["fndc"]["shunt_b_current"],
    ),
    OutbackSensorDescription(
        key="shunt_c_fm100",
        name=f"Shunt C - {SHUNT_LABELS['c']}",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["fndc"]["shunt_c_current"],
    ),
)


async def async_setup_entry(
    hass,
    entry: OutbackConfigEntry,
    async_add_entities,
) -> None:
    """Set up MATE3s sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    if coordinator.data.get("radian") is not None:
        entities.extend(OutbackSensor(coordinator, desc) for desc in RADIAN_SENSORS)

    if coordinator.data.get("fndc") is not None:
        entities.extend(OutbackSensor(coordinator, desc) for desc in FNDC_SENSORS)

    for port in sorted(coordinator.data.get("charge_controllers", {})):
        cc = coordinator.data["charge_controllers"][port]
        entities.extend(
            (
                OutbackChargeControllerSensor(
                    coordinator, port, "pv_voltage",
                    f"{cc['label']} PV Voltage",
                    UnitOfElectricPotential.VOLT,
                    SensorDeviceClass.VOLTAGE,
                    SensorStateClass.MEASUREMENT, 1
                ),
                OutbackChargeControllerSensor(
                    coordinator, port, "battery_voltage",
                    f"{cc['label']} Battery Voltage",
                    UnitOfElectricPotential.VOLT,
                    SensorDeviceClass.VOLTAGE,
                    SensorStateClass.MEASUREMENT, 1
                ),
                OutbackChargeControllerSensor(
                    coordinator, port, "output_current",
                    f"{cc['label']} Output Current",
                    UnitOfElectricCurrent.AMPERE,
                    SensorDeviceClass.CURRENT,
                    SensorStateClass.MEASUREMENT, 1
                ),
                OutbackChargeControllerSensor(
                    coordinator, port, "output_power_w",
                    f"{cc['label']} Power",
                    UnitOfPower.WATT,
                    SensorDeviceClass.POWER,
                    SensorStateClass.MEASUREMENT, 0
                ),
                OutbackChargeControllerSensor(
                    coordinator, port, "today_energy_kwh",
                    f"{cc['label']} Today Energy",
                    UnitOfEnergy.KILO_WATT_HOUR,
                    SensorDeviceClass.ENERGY,
                    SensorStateClass.TOTAL_INCREASING, 1
                ),
                OutbackChargeControllerTextSensor(
                    coordinator, port, "charger_state",
                    f"{cc['label']} Charger State"
                ),
            )
        )

    entities.extend((OutbackSolarTotalPowerSensor(coordinator), OutbackSolarTodayEnergySensor(coordinator)))
    async_add_entities(entities)


class _OutbackBase(CoordinatorEntity[OutbackMate3sCoordinator]):
    """Base entity."""

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


class OutbackSensor(_OutbackBase, SensorEntity):
    """Static Radian or FNDC sensor."""

    entity_description: OutbackSensorDescription

    def __init__(self, coordinator: OutbackMate3sCoordinator, description: OutbackSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except (KeyError, TypeError):
            return None


class OutbackChargeControllerSensor(_OutbackBase, SensorEntity):
    """Numeric charge controller sensor."""

    def __init__(
        self,
        coordinator: OutbackMate3sCoordinator,
        port: int,
        field: str,
        name: str,
        unit: str,
        device_class: SensorDeviceClass,
        state_class: SensorStateClass,
        precision: int,
    ) -> None:
        super().__init__(coordinator)
        self._port = port
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cc{port}_{field}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_suggested_display_precision = precision

    @property
    def native_value(self):
        return self.coordinator.data.get("charge_controllers", {}).get(self._port, {}).get(self._field)


class OutbackChargeControllerTextSensor(_OutbackBase, SensorEntity):
    """Text charge controller sensor."""

    def __init__(self, coordinator: OutbackMate3sCoordinator, port: int, field: str, name: str) -> None:
        super().__init__(coordinator)
        self._port = port
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cc{port}_{field}"

    @property
    def native_value(self):
        return self.coordinator.data.get("charge_controllers", {}).get(self._port, {}).get(self._field)


class OutbackSolarTotalPowerSensor(_OutbackBase, SensorEntity):
    """Sum all charge-controller power."""

    _attr_name = "Solar Total Power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_solar_total_power"

    @property
    def native_value(self):
        controllers = self.coordinator.data.get("charge_controllers", {})
        return sum(float(cc.get("output_power_w") or 0) for cc in controllers.values())


class OutbackSolarTodayEnergySensor(_OutbackBase, SensorEntity):
    """Sum today's charge-controller energy."""

    _attr_name = "Solar Today Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:solar-panel"

    def __init__(self, coordinator: OutbackMate3sCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_solar_today_energy"

    @property
    def native_value(self):
        controllers = self.coordinator.data.get("charge_controllers", {})
        return round(sum(float(cc.get("today_energy_kwh") or 0) for cc in controllers.values()), 1)
