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
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OutbackConfigEntry
from .const import CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT, DOMAIN
from .coordinator import OutbackMate3sCoordinator
from .units import plan_registry_updates


@dataclass(frozen=True, kw_only=True)
class OutbackSensorDescription(SensorEntityDescription):
    """Describe a MATE3s sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _desc(
    section: str,
    field: str,
    name: str,
    *,
    unit: str | None = None,
    device_class: SensorDeviceClass | None = None,
    state_class: SensorStateClass | None = None,
    precision: int | None = None,
    icon: str | None = None,
    category: EntityCategory | None = None,
) -> OutbackSensorDescription:
    return OutbackSensorDescription(
        key=f"{section}_{field}",
        name=name,
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=state_class,
        suggested_display_precision=precision,
        icon=icon,
        entity_category=category,
        value_fn=lambda d, s=section, f=field: d[s][f],
    )


MEAS = SensorStateClass.MEASUREMENT
TOTAL = SensorStateClass.TOTAL
TOTAL_INC = SensorStateClass.TOTAL_INCREASING
DIAG = EntityCategory.DIAGNOSTIC

RADIAN_SENSORS: tuple[OutbackSensorDescription, ...] = (
    _desc("radian", "mode", "Radian Mode", icon="mdi:solar-power-variant"),
    _desc("radian", "ac_input_state", "AC Input State", icon="mdi:transmission-tower"),
    _desc("radian", "ac_input_selection", "AC Input Selection", category=DIAG),
    _desc("radian", "error_flags", "Radian Errors", icon="mdi:alert-circle", category=DIAG),
    _desc("radian", "warning_flags", "Radian Warnings", icon="mdi:alert", category=DIAG),
    _desc("radian", "sell_status", "Radian Sell Status", icon="mdi:transmission-tower-export", category=DIAG),
    _desc("radian", "battery_voltage", "Radian Battery Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1),
    _desc("radian", "frequency", "AC Frequency", unit=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=MEAS, precision=1),
    _desc("radian", "selected_input_voltage", "Selected AC Input Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "minimum_input_voltage", "Minimum AC Input Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "maximum_input_voltage", "Maximum AC Input Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0, category=DIAG),

    _desc("radian", "l1_grid_voltage", "Grid L1 Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0),
    _desc("radian", "l2_grid_voltage", "Grid L2 Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0),
    _desc("radian", "l1_output_voltage", "Output L1 Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0),
    _desc("radian", "l2_output_voltage", "Output L2 Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=0),

    _desc("radian", "l1_buy_current", "Grid L1 Buy Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l2_buy_current", "Grid L2 Buy Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l1_sell_current", "Grid L1 Sell Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l2_sell_current", "Grid L2 Sell Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l1_output_current", "Inverter L1 Output Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l2_output_current", "Inverter L2 Output Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l1_charge_current", "Inverter L1 Charge Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "l2_charge_current", "Inverter L2 Charge Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "house_l1_current", "House L1 Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("radian", "house_l2_current", "House L2 Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),

    _desc("radian", "load_power", "House Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=1),
    _desc("radian", "buy_power", "Grid Buy Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=1),
    _desc("radian", "sell_power", "Grid Sell Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=1),
    _desc("radian", "grid_power", "Grid Power", unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=0, icon="mdi:transmission-tower"),
    _desc("radian", "output_power", "Radian Output Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=1),
    _desc("radian", "charge_power", "Radian Charge Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=1),

    _desc("radian", "today_ac1_l1_buy_energy", "Today Grid L1 Buy Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_ac1_l2_buy_energy", "Today Grid L2 Buy Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_ac1_l1_sell_energy", "Today Grid L1 Sell Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_ac1_l2_sell_energy", "Today Grid L2 Sell Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_l1_output_energy", "Today L1 Output Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_l2_output_energy", "Today L2 Output Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_charger_energy", "Today Charger Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1),
    _desc("radian", "today_grid_import_energy", "Grid Import Today Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1, icon="mdi:transmission-tower-import"),
    _desc("radian", "today_grid_export_energy", "Grid Export Today Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=1, icon="mdi:transmission-tower-export"),

    _desc("radian", "left_transformer_temperature", "Left Transformer Temperature", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "left_capacitor_temperature", "Left Capacitor Temperature", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "left_fet_temperature", "Left FET Temperature", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "right_transformer_temperature", "Right Transformer Temperature", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "right_capacitor_temperature", "Right Capacitor Temperature", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, precision=0, category=DIAG),
    _desc("radian", "right_fet_temperature", "Right FET Temperature", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, precision=0, category=DIAG),
)

# Single-phase Radian / FXR (DID 64117) and FX / VFX (DID 64113), one set per
# HUB port. Monitoring only; experimental until validated on real hardware.
SP = ("single_phase",)
FX = ("fx",)
BOTH = ("single_phase", "fx")
V = UnitOfElectricPotential.VOLT
A = UnitOfElectricCurrent.AMPERE
KW = UnitOfPower.KILO_WATT
KWH = UnitOfEnergy.KILO_WATT_HOUR
C = UnitOfTemperature.CELSIUS
SDC = SensorDeviceClass

# (field, name, unit, device_class, state_class, precision, category, icon, types)
INVERTER_SENSOR_SPECS: tuple[tuple, ...] = (
    ("mode", "Mode", None, None, None, None, None, "mdi:solar-power-variant", BOTH),
    ("ac_input_state", "AC Input State", None, None, None, None, None, "mdi:transmission-tower", BOTH),
    ("ac_input_selection", "AC Input Selection", None, None, None, None, DIAG, None, SP),
    ("error_flags", "Errors", None, None, None, None, DIAG, "mdi:alert-circle", BOTH),
    ("warning_flags", "Warnings", None, None, None, None, DIAG, "mdi:alert", BOTH),
    ("sell_status", "Sell Status", None, None, None, None, DIAG, "mdi:transmission-tower-export", BOTH),
    ("battery_voltage", "Battery Voltage", V, SDC.VOLTAGE, MEAS, 1, None, None, BOTH),
    ("frequency", "AC Frequency", UnitOfFrequency.HERTZ, SDC.FREQUENCY, MEAS, 1, None, None, BOTH),
    ("selected_input_voltage", "AC Input Voltage", V, SDC.VOLTAGE, MEAS, 0, None, None, BOTH),
    ("grid_voltage", "Grid Voltage", V, SDC.VOLTAGE, MEAS, 0, None, None, SP),
    ("output_voltage", "Output Voltage", V, SDC.VOLTAGE, MEAS, 0, None, None, BOTH),
    ("minimum_input_voltage", "Minimum AC Input Voltage", V, SDC.VOLTAGE, MEAS, 0, DIAG, None, BOTH),
    ("maximum_input_voltage", "Maximum AC Input Voltage", V, SDC.VOLTAGE, MEAS, 0, DIAG, None, BOTH),
    ("buy_current", "Grid Buy Current", A, SDC.CURRENT, MEAS, 1, None, None, BOTH),
    ("sell_current", "Grid Sell Current", A, SDC.CURRENT, MEAS, 1, None, None, BOTH),
    ("output_current", "Inverter Output Current", A, SDC.CURRENT, MEAS, 1, None, None, BOTH),
    ("charge_current", "Inverter Charge Current", A, SDC.CURRENT, MEAS, 1, None, None, BOTH),
    ("house_current", "House Current", A, SDC.CURRENT, MEAS, 1, None, None, BOTH),
    ("load_power", "House Power", KW, SDC.POWER, MEAS, 1, None, None, BOTH),
    ("buy_power", "Grid Buy Power", KW, SDC.POWER, MEAS, 1, None, None, BOTH),
    ("sell_power", "Grid Sell Power", KW, SDC.POWER, MEAS, 1, None, None, BOTH),
    ("grid_power", "Grid Power", UnitOfPower.WATT, SDC.POWER, MEAS, 0, None, "mdi:transmission-tower", BOTH),
    ("output_power", "Output Power", KW, SDC.POWER, MEAS, 1, None, None, BOTH),
    ("charge_power", "Charge Power", KW, SDC.POWER, MEAS, 1, None, None, BOTH),
    ("today_grid_import_energy", "Grid Import Today Energy", KWH, SDC.ENERGY, TOTAL_INC, 1, None, "mdi:transmission-tower-import", BOTH),
    ("today_grid_export_energy", "Grid Export Today Energy", KWH, SDC.ENERGY, TOTAL_INC, 1, None, "mdi:transmission-tower-export", BOTH),
    ("today_output_energy", "Today Output Energy", KWH, SDC.ENERGY, TOTAL_INC, 1, None, None, BOTH),
    ("today_charger_energy", "Today Charger Energy", KWH, SDC.ENERGY, TOTAL_INC, 1, None, None, BOTH),
    ("left_transformer_temperature", "Left Transformer Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, SP),
    ("left_capacitor_temperature", "Left Capacitor Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, SP),
    ("left_fet_temperature", "Left FET Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, SP),
    ("right_transformer_temperature", "Right Transformer Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, SP),
    ("right_capacitor_temperature", "Right Capacitor Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, SP),
    ("right_fet_temperature", "Right FET Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, SP),
    ("transformer_temperature", "Transformer Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, FX),
    ("capacitor_temperature", "Capacitor Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, FX),
    ("fet_temperature", "FET Temperature", C, SDC.TEMPERATURE, MEAS, 0, DIAG, None, FX),
)

FNDC_SENSORS: tuple[OutbackSensorDescription, ...] = (
    _desc("fndc", "soc", "FNDC SOC", unit=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=MEAS),
    _desc("fndc", "battery_voltage", "FNDC Battery Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1),
    _desc("fndc", "battery_current", "FNDC Battery Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("fndc", "net_power", "FNDC Net Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=2),
    _desc("fndc", "input_power", "FNDC Input Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=2),
    _desc("fndc", "output_power", "FNDC Output Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=2),
    _desc("fndc", "input_current", "FNDC Input Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("fndc", "output_current", "FNDC Output Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("fndc", "today_min_soc", "FNDC Today Minimum SOC", unit=PERCENTAGE, state_class=MEAS),
    _desc("fndc", "today_max_soc", "FNDC Today Maximum SOC", unit=PERCENTAGE, state_class=MEAS),
    _desc("fndc", "today_net_input_ah", "FNDC Today Net Input Ah", unit="Ah", state_class=TOTAL, precision=0),
    _desc("fndc", "today_net_input_kwh", "FNDC Today Net Input Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=2),
    _desc("fndc", "today_net_output_ah", "FNDC Today Net Output Ah", unit="Ah", state_class=TOTAL, precision=0),
    _desc("fndc", "today_net_output_kwh", "FNDC Today Net Output Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC, precision=2),
    _desc("fndc", "today_net_battery_ah", "FNDC Today Net Battery Ah", unit="Ah", state_class=TOTAL, precision=0),
    _desc("fndc", "today_net_battery_kwh", "FNDC Today Net Battery Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL, precision=2),
    _desc("fndc", "today_min_battery_voltage", "FNDC Today Minimum Battery Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1),
    _desc("fndc", "today_max_battery_voltage", "FNDC Today Maximum Battery Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1),

    _desc("fndc", "shunt_a_current", "Shunt A Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("fndc", "shunt_b_current", "Shunt B Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("fndc", "shunt_c_current", "Shunt C Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1),
    _desc("fndc", "shunt_a_accumulated_ah", "Shunt A Accumulated Ah", unit="Ah", state_class=TOTAL, category=DIAG),
    _desc("fndc", "shunt_a_accumulated_kwh", "Shunt A Accumulated Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL, precision=2, category=DIAG),
    _desc("fndc", "shunt_b_accumulated_ah", "Shunt B Accumulated Ah", unit="Ah", state_class=TOTAL, category=DIAG),
    _desc("fndc", "shunt_b_accumulated_kwh", "Shunt B Accumulated Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL, precision=2, category=DIAG),
    _desc("fndc", "shunt_c_accumulated_ah", "Shunt C Accumulated Ah", unit="Ah", state_class=TOTAL, category=DIAG),
    _desc("fndc", "shunt_c_accumulated_kwh", "Shunt C Accumulated Energy", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=TOTAL, precision=2, category=DIAG),
)

# Historical maximum shunt telemetry from the FNDC real-time block.
# Cumulative returned/removed Ah and kWh entities are intentionally not exposed.
for _letter in ("a", "b", "c"):
    _upper = _letter.upper()
    FNDC_SENSORS += (
        _desc("fndc", f"shunt_{_letter}_max_charge_current", f"Shunt {_upper} Maximum Charge Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1, category=DIAG),
        _desc("fndc", f"shunt_{_letter}_max_charge_power", f"Shunt {_upper} Maximum Charge Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=2, category=DIAG),
        _desc("fndc", f"shunt_{_letter}_max_discharge_current", f"Shunt {_upper} Maximum Discharge Current", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1, category=DIAG),
        _desc("fndc", f"shunt_{_letter}_max_discharge_power", f"Shunt {_upper} Maximum Discharge Power", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=MEAS, precision=2, category=DIAG),
    )

SYSTEM_SENSORS: tuple[OutbackSensorDescription, ...] = (
    _desc("system_control", "sell_voltage", "Global Sell Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1, category=DIAG),
    _desc("system_control", "sell_current_limit", "Radian Sell Current Limit", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1, category=DIAG),
    _desc("system_control", "absorb_voltage", "Global Absorb Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1, category=DIAG),
    _desc("system_control", "absorb_time", "Global Absorb Time", unit="h", precision=1, category=DIAG),
    _desc("system_control", "float_voltage", "Global Float Voltage", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, precision=1, category=DIAG),
    _desc("system_control", "float_time", "Global Float Time", unit="h", precision=1, category=DIAG),
    _desc("system_control", "charger_current_limit", "Inverter Charger Current Limit", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=MEAS, precision=1, category=DIAG),
)

CC_SENSOR_SPECS = (
    ("pv_voltage", "PV Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, MEAS, 1, None),
    ("battery_voltage", "Battery Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, MEAS, 1, None),
    ("output_current", "Output Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, MEAS, 1, None),
    ("array_current", "Array Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, MEAS, 1, None),
    ("output_power_w", "Power", UnitOfPower.WATT, SensorDeviceClass.POWER, MEAS, 0, None),
    ("today_min_battery_voltage", "Today Minimum Battery Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, MEAS, 1, DIAG),
    ("today_max_battery_voltage", "Today Maximum Battery Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, MEAS, 1, DIAG),
    ("last_voc", "Last VOC", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, MEAS, 1, DIAG),
    ("today_peak_voc", "Maximum VOC Today", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, MEAS, 1, DIAG),
    ("peak_amps_today", "Peak Amps Today", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, MEAS, 1, DIAG),
    ("peak_watts_today", "Peak Watts Today", UnitOfPower.WATT, SensorDeviceClass.POWER, MEAS, 0, DIAG),
    ("today_energy_kwh", "Today Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, TOTAL_INC, 1, None),
    ("today_ah", "Today Amp Hours", "Ah", None, TOTAL_INC, 0, None),
)


async def async_setup_entry(hass, entry: OutbackConfigEntry, async_add_entities) -> None:
    """Set up MATE3s sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    radians = coordinator.data.get("radians", {})
    if len(radians) <= 1 and coordinator.data.get("radian") is not None:
        # Preserve the original entity unique IDs on existing single-Radian
        # installations.
        entities.extend(OutbackSensor(coordinator, desc) for desc in RADIAN_SENSORS)
    elif len(radians) > 1:
        for port in sorted(radians):
            entities.extend(
                OutbackRadianSensor(coordinator, port, desc)
                for desc in RADIAN_SENSORS
            )

    inverters = coordinator.data.get("inverters", {})
    for port in sorted(inverters):
        inverter_type = inverters[port]["type"]
        entities.extend(
            OutbackInverterSensor(coordinator, port, spec)
            for spec in INVERTER_SENSOR_SPECS
            if inverter_type in spec[-1]
        )

    if coordinator.data.get("fndc") is not None:
        entities.extend(OutbackSensor(coordinator, desc) for desc in FNDC_SENSORS)

    if coordinator.data.get("system_control") is not None:
        entities.extend(OutbackSensor(coordinator, desc) for desc in SYSTEM_SENSORS)

    for port in sorted(coordinator.data.get("charge_controllers", {})):
        cc = coordinator.data["charge_controllers"][port]
        entities.append(OutbackChargeControllerTextSensor(coordinator, port, "charger_state", f"{cc['label']} Charger State"))
        for field, suffix, unit, device_class, state_class, precision, category in CC_SENSOR_SPECS:
            entities.append(
                OutbackChargeControllerSensor(
                    coordinator, port, field, f"{cc['label']} {suffix}", unit,
                    device_class, state_class, precision, category
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


class _TemperatureUnitMixin:
    """Apply the integration's temperature-unit option to this entity."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()  # type: ignore[misc]
        if self.device_class == SensorDeviceClass.TEMPERATURE:  # type: ignore[attr-defined]
            self._async_apply_temperature_unit()

    @callback
    def _async_apply_temperature_unit(self) -> None:
        entry = self.registry_entry  # type: ignore[attr-defined]
        if entry is None:
            return
        choice = self.coordinator.config_entry.options.get(  # type: ignore[attr-defined]
            CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT
        )
        updates = plan_registry_updates(entry.options, choice, DOMAIN)
        if not updates:
            return
        registry = er.async_get(self.hass)  # type: ignore[attr-defined]
        for options_domain, options in updates.items():
            registry.async_update_entity_options(entry.entity_id, options_domain, options)


class OutbackSensor(_TemperatureUnitMixin, _OutbackBase, SensorEntity):
    """Static Radian, FNDC or system sensor."""

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


class OutbackRadianSensor(_TemperatureUnitMixin, _OutbackBase, SensorEntity):
    """One per-Radian sensor for stacked/multi-inverter systems."""

    entity_description: OutbackSensorDescription

    def __init__(
        self,
        coordinator: OutbackMate3sCoordinator,
        port: int,
        description: OutbackSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._port = port
        self.entity_description = description
        self._field = description.key.removeprefix("radian_")
        radian = coordinator.data.get("radians", {}).get(port, {})
        label = radian.get("label", f"Radian Port {port}")
        self._attr_name = f"{label} {description.name}"
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_radian{port}_{self._field}"
        )

    @property
    def native_value(self):
        return (
            self.coordinator.data.get("radians", {})
            .get(self._port, {})
            .get(self._field)
        )


class OutbackInverterSensor(_TemperatureUnitMixin, _OutbackBase, SensorEntity):
    """Single-phase Radian / FXR (DID 64117) or FX / VFX (DID 64113) sensor."""

    def __init__(self, coordinator: OutbackMate3sCoordinator, port: int, spec: tuple) -> None:
        super().__init__(coordinator)
        field, name, unit, device_class, state_class, precision, category, icon, _types = spec
        self._port = port
        self._field = field
        label = coordinator.data["inverters"][port]["label"]
        self._attr_name = f"{label} {name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_inv{port}_{field}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_suggested_display_precision = precision
        self._attr_entity_category = category
        if icon:
            self._attr_icon = icon

    @property
    def native_value(self):
        return self.coordinator.data.get("inverters", {}).get(self._port, {}).get(self._field)


class OutbackChargeControllerSensor(_OutbackBase, SensorEntity):
    """Numeric charge controller sensor."""

    def __init__(
        self,
        coordinator: OutbackMate3sCoordinator,
        port: int,
        field: str,
        name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        precision: int | None,
        category: EntityCategory | None,
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
        self._attr_entity_category = category

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
        values = [cc.get("output_power_w") for cc in controllers.values()]
        # Never publish a partial total: a missing controller makes it unknown.
        if any(value is None for value in values):
            return None
        return sum(float(value) for value in values)


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
        values = [cc.get("today_energy_kwh") for cc in controllers.values()]
        # A partial sum would look like a meter reset to the Energy dashboard
        # and double-count when the missing controller returns.
        if any(value is None for value in values):
            return None
        return round(sum(float(value) for value in values), 1)
