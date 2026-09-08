"""Read-only OutBack MATE3s Modbus/SunSpec device model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from modbus_connection import ModbusUnit

from .const import (
    CHARGE_CONTROLLER_LABELS,
    DID_CHARGE_CONTROLLER_REALTIME,
    DID_FNDC_REALTIME,
    DID_RADIAN_SPLIT_REALTIME,
    SUNSPEC_BASE,
    SUNSPEC_END_DID,
    SUNSPEC_SIGNATURE,
)

DID_OUTBACK_SYSTEM_CONTROL = 64120


def _s16(value: int) -> int:
    """Convert one unsigned 16-bit register to signed int16."""
    return value - 0x10000 if value & 0x8000 else value


def _scaled(value: int, sf: int, *, signed: bool = False) -> float:
    """Apply a SunSpec/OutBack base-10 scale factor."""
    raw = _s16(value) if signed else value
    return raw * (10**sf)


def _u32(msw: int, lsw: int) -> int:
    """Combine two 16-bit registers into a 32-bit unsigned value."""
    return ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF)


def _utc_timestamp(msw: int, lsw: int) -> datetime | None:
    """Convert an OutBack uint32 UTC-seconds value to a datetime when plausible."""
    value = _u32(msw, lsw)
    if value == 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _decode_flags(value: int, mapping: dict[int, str]) -> str:
    """Decode a bitfield into a compact human-readable string."""
    active = [text for bit, text in mapping.items() if value & bit]
    return ", ".join(active) if active else "None"


@dataclass(frozen=True)
class Block:
    """One discovered SunSpec block."""

    address: int
    did: int
    length: int


RADIAN_MODES = {
    0: "Off",
    1: "Searching",
    2: "Inverting",
    3: "Charging",
    4: "Silent",
    5: "Float",
    6: "EQ",
    7: "Charger Off",
    8: "Support",
    9: "Selling",
    10: "Pass Through",
    14: "Offsetting",
}

CHARGER_STATES = {
    0: "Silent",
    1: "Float",
    2: "Bulk",
    3: "Absorb",
    4: "EQ",
}

RADIAN_ERROR_FLAGS = {
    0x0001: "Low AC output voltage",
    0x0002: "Stacking error",
    0x0004: "Over temperature error",
    0x0008: "Low battery voltage",
    0x0010: "Phase loss",
    0x0020: "High battery voltage",
    0x0040: "AC output shorted",
    0x0080: "AC backfeed",
}

RADIAN_WARNING_FLAGS = {
    0x0001: "AC input frequency too high",
    0x0002: "AC input frequency too low",
    0x0004: "AC input voltage too low",
    0x0008: "AC input voltage too high",
    0x0010: "AC input current exceeds max",
    0x0020: "Temperature sensor bad",
    0x0040: "Communications error",
    0x0080: "Cooling fan fault",
}

RADIAN_SELL_STATUS_FLAGS = {
    0x0001: "AC input frequency too high",
    0x0002: "AC input frequency too low",
    0x0004: "AC input voltage too low",
    0x0008: "AC input voltage too high",
    0x0010: "Awaiting sell delay",
    0x0020: "Sell disabled",
    0x0040: "Battery voltage less than target",
}

FNDC_STATUS_FLAGS = {
    0x0001: "AUX relay enabled",
    0x0002: "Charge parameters met",
}

AGS_STATES = {
    0: "Stopped",
    1: "Starting",
    2: "Running",
    3: "Warmup",
    4: "Cooldown",
    5: "Awaiting AC",
}


class OutbackProtocolError(Exception):
    """The connected Modbus device is not the expected MATE3s map."""


class OutbackMate3sDevice:
    """Read a MATE3s directly through a Home Assistant shared Modbus unit."""

    def __init__(self, unit: ModbusUnit) -> None:
        self.unit = unit
        self.blocks: list[Block] = []

    async def async_discover(self) -> list[Block]:
        """Discover the SunSpec chain without relying on pysunspec2."""
        signature = await self.unit.read_holding_registers(SUNSPEC_BASE, 4)
        if len(signature) < 4 or tuple(signature[:2]) != SUNSPEC_SIGNATURE:
            raise OutbackProtocolError(
                f"SunSpec signature not found at register {SUNSPEC_BASE}"
            )

        address = SUNSPEC_BASE + 2
        blocks: list[Block] = []

        for _ in range(128):
            header = await self.unit.read_holding_registers(address, 2)
            if len(header) != 2:
                raise OutbackProtocolError(
                    f"Short SunSpec block header at register {address}"
                )

            did, length = header
            blocks.append(Block(address=address, did=did, length=length))

            if did == SUNSPEC_END_DID:
                self.blocks = blocks
                return blocks

            next_address = address + 2 + length
            if length > 2048 or next_address <= address or next_address > 65535:
                raise OutbackProtocolError(
                    f"Invalid SunSpec block length {length} at register {address}"
                )
            address = next_address

        raise OutbackProtocolError("SunSpec end marker was not found")

    def _blocks(self, did: int) -> list[Block]:
        return [block for block in self.blocks if block.did == did]

    async def _read_block(self, block: Block) -> list[int]:
        """Read DID + length + block payload."""
        count = block.length + 2
        if count > 125:
            raise OutbackProtocolError(
                f"DID {block.did} is too large for one read ({count} registers)"
            )
        regs = await self.unit.read_holding_registers(block.address, count)
        if len(regs) != count:
            raise OutbackProtocolError(
                f"Short read for DID {block.did} at {block.address}"
            )
        if regs[0] != block.did:
            raise OutbackProtocolError(
                f"DID changed at {block.address}: expected {block.did}, got {regs[0]}"
            )
        return regs

    async def async_read_all(self) -> dict[str, Any]:
        """Read the useful real-time OutBack blocks."""
        if not self.blocks:
            await self.async_discover()

        data: dict[str, Any] = {
            "radian": None,
            "charge_controllers": {},
            "fndc": None,
            "system_control": None,
            "topology": [
                {"address": b.address, "did": b.did, "length": b.length}
                for b in self.blocks
            ],
        }

        radian_blocks = self._blocks(DID_RADIAN_SPLIT_REALTIME)
        if radian_blocks:
            data["radian"] = self._parse_radian(
                await self._read_block(radian_blocks[0])
            )

        for block in self._blocks(DID_CHARGE_CONTROLLER_REALTIME):
            cc = self._parse_charge_controller(await self._read_block(block))
            data["charge_controllers"][cc["port"]] = cc

        fndc_blocks = self._blocks(DID_FNDC_REALTIME)
        if fndc_blocks:
            data["fndc"] = self._parse_fndc(
                await self._read_block(fndc_blocks[0])
            )

        system_blocks = self._blocks(DID_OUTBACK_SYSTEM_CONTROL)
        if system_blocks:
            data["system_control"] = self._parse_system_control(
                await self._read_block(system_blocks[0])
            )

        return data

    @staticmethod
    def _parse_radian(r: list[int]) -> dict[str, Any]:
        """Decode OutBack DID 64115."""
        dc_voltage_sf = _s16(r[3])
        ac_current_sf = _s16(r[4])
        ac_voltage_sf = _s16(r[5])
        ac_freq_sf = _s16(r[6])
        energy_sf = _s16(r[42])

        mode_raw = r[21]
        ac_input_state_raw = r[38]
        ac_input_selection_raw = r[35]
        error_flags_raw = r[22]
        warning_flags_raw = r[23]
        sell_status_raw = r[41]

        l1_output_current = _scaled(r[7], ac_current_sf, signed=True)
        l1_charge_current = _scaled(r[8], ac_current_sf, signed=True)
        l1_buy_current = _scaled(r[9], ac_current_sf, signed=True)
        l1_sell_current = _scaled(r[10], ac_current_sf, signed=True)
        l2_output_current = _scaled(r[14], ac_current_sf, signed=True)
        l2_charge_current = _scaled(r[15], ac_current_sf, signed=True)
        l2_buy_current = _scaled(r[16], ac_current_sf, signed=True)
        l2_sell_current = _scaled(r[17], ac_current_sf, signed=True)

        house_l1_current = (
            l1_buy_current + l1_output_current - l1_sell_current - l1_charge_current
        )
        house_l2_current = (
            l2_buy_current + l2_output_current - l2_sell_current - l2_charge_current
        )

        return {
            "port": r[2],
            "mode_raw": mode_raw,
            "mode": RADIAN_MODES.get(mode_raw, f"Unknown ({mode_raw})"),
            "error_flags_raw": error_flags_raw,
            "error_flags": _decode_flags(error_flags_raw, RADIAN_ERROR_FLAGS),
            "warning_flags_raw": warning_flags_raw,
            "warning_flags": _decode_flags(warning_flags_raw, RADIAN_WARNING_FLAGS),
            "sell_status_raw": sell_status_raw,
            "sell_status": _decode_flags(sell_status_raw, RADIAN_SELL_STATUS_FLAGS),
            "ac_input_selection_raw": ac_input_selection_raw,
            "ac_input_selection": "Grid" if ac_input_selection_raw == 0 else "Generator",
            "ac_input_state_raw": ac_input_state_raw,
            "ac_input_state": "AC USE" if ac_input_state_raw == 1 else "AC DROP",
            "battery_voltage": _scaled(r[24], dc_voltage_sf, signed=True),
            "temp_comp_target_voltage": _scaled(r[25], dc_voltage_sf, signed=True),
            "aux_output_state": "On" if r[26] else "Off",
            "aux_relay_state": "On" if r[27] else "Off",
            "left_transformer_temperature": _s16(r[28]),
            "left_capacitor_temperature": _s16(r[29]),
            "left_fet_temperature": _s16(r[30]),
            "right_transformer_temperature": _s16(r[31]),
            "right_capacitor_temperature": _s16(r[32]),
            "right_fet_temperature": _s16(r[33]),
            "battery_temperature": _s16(r[34]),
            "frequency": _scaled(r[36], ac_freq_sf, signed=True),
            "selected_input_voltage": _scaled(r[37], ac_voltage_sf, signed=True),
            "minimum_input_voltage": _scaled(r[39], ac_voltage_sf, signed=True),
            "maximum_input_voltage": _scaled(r[40], ac_voltage_sf, signed=True),
            "l1_output_current": l1_output_current,
            "l1_charge_current": l1_charge_current,
            "l1_buy_current": l1_buy_current,
            "l1_sell_current": l1_sell_current,
            "l1_grid_voltage": _scaled(r[11], ac_voltage_sf, signed=True),
            "l1_generator_voltage": _scaled(r[12], ac_voltage_sf, signed=True),
            "l1_output_voltage": _scaled(r[13], ac_voltage_sf, signed=True),
            "l2_output_current": l2_output_current,
            "l2_charge_current": l2_charge_current,
            "l2_buy_current": l2_buy_current,
            "l2_sell_current": l2_sell_current,
            "l2_grid_voltage": _scaled(r[18], ac_voltage_sf, signed=True),
            "l2_generator_voltage": _scaled(r[19], ac_voltage_sf, signed=True),
            "l2_output_voltage": _scaled(r[20], ac_voltage_sf, signed=True),
            "house_l1_current": house_l1_current,
            "house_l2_current": house_l2_current,
            "today_ac1_l1_buy_energy": _scaled(r[43], energy_sf),
            "today_ac2_l1_buy_energy": _scaled(r[44], energy_sf),
            "today_ac1_l1_sell_energy": _scaled(r[45], energy_sf),
            "today_ac2_l1_sell_energy": _scaled(r[46], energy_sf),
            "today_l1_output_energy": _scaled(r[47], energy_sf),
            "today_ac1_l2_buy_energy": _scaled(r[48], energy_sf),
            "today_ac2_l2_buy_energy": _scaled(r[49], energy_sf),
            "today_ac1_l2_sell_energy": _scaled(r[50], energy_sf),
            "today_ac2_l2_sell_energy": _scaled(r[51], energy_sf),
            "today_l2_output_energy": _scaled(r[52], energy_sf),
            "today_charger_energy": _scaled(r[53], energy_sf),
            "output_power": _scaled(r[54], energy_sf),
            "buy_power": _scaled(r[55], energy_sf),
            "sell_power": _scaled(r[56], energy_sf),
            "charge_power": _scaled(r[57], energy_sf),
            "load_power": _scaled(r[58], energy_sf),
            "ac_couple_power": _scaled(r[59], energy_sf) if len(r) > 59 else None,
        }

    @staticmethod
    def _parse_charge_controller(r: list[int]) -> dict[str, Any]:
        """Decode OutBack DID 64111."""
        voltage_sf = _s16(r[3])
        current_sf = _s16(r[4])
        power_sf = _s16(r[5])
        ah_sf = _s16(r[6])
        kwh_sf = _s16(r[7])

        port = r[2]
        state_raw = r[12]
        temp_sf = _s16(r[25]) if len(r) > 25 else 0

        def temp(index: int) -> float | None:
            if len(r) <= index or r[index] in (0x7FFF, 0x8000, 0xFFFF):
                return None
            return _scaled(r[index], temp_sf, signed=True)

        return {
            "port": port,
            "label": CHARGE_CONTROLLER_LABELS.get(port, f"Charge Controller Port {port}"),
            "battery_voltage": _scaled(r[8], voltage_sf),
            "pv_voltage": _scaled(r[9], voltage_sf),
            "output_current": _scaled(r[10], current_sf),
            # The OutBack application note labels CC_Array_Current with CC_Power_SF.
            # Current firmware values are exposed here exactly using the documented
            # block position, while the current scale is used for an ampere sensor.
            "array_current": _scaled(r[11], current_sf),
            "charger_state_raw": state_raw,
            "charger_state": CHARGER_STATES.get(state_raw, f"Unknown ({state_raw})"),
            "output_power_w": _scaled(r[13], power_sf),
            "today_min_battery_voltage": _scaled(r[14], voltage_sf),
            "today_max_battery_voltage": _scaled(r[15], voltage_sf),
            "last_voc": _scaled(r[16], voltage_sf),
            "today_peak_voc": _scaled(r[17], voltage_sf),
            "today_energy_kwh": _scaled(r[18], kwh_sf),
            "today_ah": _scaled(r[19], ah_sf),
            "lifetime_energy_kwh": r[20],
            "lifetime_kah": _scaled(r[21], kwh_sf),
            "lifetime_max_power_w": _scaled(r[22], power_sf),
            "lifetime_max_battery_voltage": _scaled(r[23], voltage_sf),
            "lifetime_max_voc": _scaled(r[24], voltage_sf),
            "output_fet_temperature": temp(26),
            "enclosure_temperature": temp(27),
        }

    @staticmethod
    def _parse_fndc(r: list[int]) -> dict[str, Any]:
        """Decode OutBack DID 64118."""
        voltage_sf = _s16(r[3])
        current_sf = _s16(r[4])
        time_sf = _s16(r[5])
        kwh_sf = _s16(r[6])
        kw_sf = _s16(r[7])
        status_flags_raw = r[14]

        return {
            "port": r[2],
            "shunt_a_current": _scaled(r[8], current_sf, signed=True),
            "shunt_b_current": _scaled(r[9], current_sf, signed=True),
            "shunt_c_current": _scaled(r[10], current_sf, signed=True),
            "battery_voltage": _scaled(r[11], voltage_sf),
            "battery_current": _scaled(r[12], current_sf, signed=True),
            "battery_temperature": _s16(r[13]),
            "status_flags_raw": status_flags_raw,
            "status_flags": _decode_flags(status_flags_raw, FNDC_STATUS_FLAGS),
            "shunt_a_accumulated_ah": _s16(r[15]),
            "shunt_a_accumulated_kwh": _scaled(r[16], kwh_sf, signed=True),
            "shunt_b_accumulated_ah": _s16(r[17]),
            "shunt_b_accumulated_kwh": _scaled(r[18], kwh_sf, signed=True),
            "shunt_c_accumulated_ah": _s16(r[19]),
            "shunt_c_accumulated_kwh": _scaled(r[20], kwh_sf, signed=True),
            "input_current": _scaled(r[21], current_sf),
            "output_current": _scaled(r[22], current_sf),
            "input_power": _scaled(r[23], kw_sf),
            "output_power": _scaled(r[24], kw_sf),
            "net_power": _scaled(r[25], kw_sf, signed=True),
            "days_since_full": _scaled(r[26], time_sf),
            "soc": r[27],
            "today_min_soc": r[28],
            "today_max_soc": r[29],
            "today_net_input_ah": r[30],
            "today_net_input_kwh": _scaled(r[31], kwh_sf),
            "today_net_output_ah": r[32],
            "today_net_output_kwh": _scaled(r[33], kwh_sf),
            "today_net_battery_ah": _s16(r[34]),
            "today_net_battery_kwh": _scaled(r[35], kwh_sf, signed=True),
            "charge_factor_corrected_net_battery_ah": _s16(r[36]),
            "charge_factor_corrected_net_battery_kwh": _scaled(r[37], kwh_sf, signed=True),
            "today_min_battery_voltage": _scaled(r[38], voltage_sf),
            "today_min_battery_time": _utc_timestamp(r[39], r[40]),
            "today_max_battery_voltage": _scaled(r[41], voltage_sf),
            "today_max_battery_time": _utc_timestamp(r[42], r[43]),
            "cycle_charge_factor": r[44],
            "cycle_kwh_charge_efficiency": r[45],
            "total_days_at_100": _scaled(r[46], time_sf),
            "lifetime_kah_removed": r[47],
            "shunt_a_returned_ah": r[48],
            "shunt_a_returned_kwh": _scaled(r[49], kwh_sf),
            "shunt_a_removed_ah": r[50],
            "shunt_a_removed_kwh": _scaled(r[51], kwh_sf),
            "shunt_a_max_charge_current": _scaled(r[52], current_sf),
            "shunt_a_max_charge_power": _scaled(r[53], kw_sf),
            "shunt_a_max_discharge_current": _scaled(r[54], current_sf, signed=True),
            "shunt_a_max_discharge_power": _scaled(r[55], kw_sf, signed=True),
            "shunt_b_returned_ah": r[56],
            "shunt_b_returned_kwh": _scaled(r[57], kwh_sf),
            "shunt_b_removed_ah": r[58],
            "shunt_b_removed_kwh": _scaled(r[59], kwh_sf),
            "shunt_b_max_charge_current": _scaled(r[60], current_sf),
            "shunt_b_max_charge_power": _scaled(r[61], kw_sf),
            "shunt_b_max_discharge_current": _scaled(r[62], current_sf, signed=True),
            "shunt_b_max_discharge_power": _scaled(r[63], kw_sf, signed=True),
            "shunt_c_returned_ah": r[64],
            "shunt_c_returned_kwh": _scaled(r[65], kwh_sf),
            "shunt_c_removed_ah": r[66],
            "shunt_c_removed_kwh": _scaled(r[67], kwh_sf),
            "shunt_c_max_charge_current": _scaled(r[68], current_sf),
            "shunt_c_max_charge_power": _scaled(r[69], kw_sf),
            "shunt_c_max_discharge_current": _scaled(r[70], current_sf, signed=True),
            "shunt_c_max_discharge_power": _scaled(r[71], kw_sf, signed=True),
        }

    @staticmethod
    def _parse_system_control(r: list[int]) -> dict[str, Any]:
        """Decode useful read/status values from OutBack DID 64120."""
        dc_voltage_sf = _s16(r[2])
        ac_current_sf = _s16(r[3])
        time_sf = _s16(r[4])
        ags_raw = r[21]
        return {
            "control_status_raw": r[10],
            "sell_voltage": _scaled(r[11], dc_voltage_sf),
            "sell_current_limit": _scaled(r[12], ac_current_sf),
            "absorb_voltage": _scaled(r[13], dc_voltage_sf),
            "absorb_time": _scaled(r[14], time_sf),
            "float_voltage": _scaled(r[15], dc_voltage_sf),
            "float_time": _scaled(r[16], time_sf),
            "charger_current_limit": _scaled(r[17], ac_current_sf),
            "ac1_current_limit": _scaled(r[18], ac_current_sf),
            "ac2_current_limit": _scaled(r[19], ac_current_sf),
            "ags_mode_raw": r[20],
            "ags_mode": {0: "Off", 1: "On", 2: "Auto"}.get(r[20], f"Unknown ({r[20]})"),
            "ags_state_raw": ags_raw,
            "ags_state": AGS_STATES.get(ags_raw, f"Unknown ({ags_raw})"),
            "ags_state_timer": r[22],
            "generator_last_run_start": _utc_timestamp(r[23], r[24]),
            "generator_last_run_duration": _u32(r[25], r[26]),
        }
