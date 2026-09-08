"""Read-only OutBack MATE3s Modbus/SunSpec device model."""

from __future__ import annotations

from dataclasses import dataclass
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


def _s16(value: int) -> int:
    """Convert one unsigned 16-bit register to signed int16."""
    return value - 0x10000 if value & 0x8000 else value


def _scaled(value: int, sf: int, *, signed: bool = False) -> float:
    """Apply a SunSpec/OutBack base-10 scale factor."""
    raw = _s16(value) if signed else value
    return raw * (10**sf)


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
        """Read the real-time Radian, charge controller and FNDC blocks."""
        if not self.blocks:
            await self.async_discover()

        data: dict[str, Any] = {
            "radian": None,
            "charge_controllers": {},
            "fndc": None,
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

        return data

    @staticmethod
    def _parse_radian(r: list[int]) -> dict[str, Any]:
        """Decode OutBack DID 64115."""
        dc_voltage_sf = _s16(r[3])
        ac_current_sf = _s16(r[4])
        ac_voltage_sf = _s16(r[5])
        ac_freq_sf = _s16(r[6])
        power_sf = _s16(r[42])

        mode_raw = r[21]
        ac_input_state_raw = r[38]

        return {
            "port": r[2],
            "mode_raw": mode_raw,
            "mode": RADIAN_MODES.get(mode_raw, f"Unknown ({mode_raw})"),
            "ac_input_state_raw": ac_input_state_raw,
            "ac_input_state": "AC USE" if ac_input_state_raw == 1 else "AC DROP",
            "battery_voltage": _scaled(r[24], dc_voltage_sf),
            "frequency": _scaled(r[36], ac_freq_sf),
            "l1_output_current": _scaled(r[7], ac_current_sf, signed=True),
            "l1_charge_current": _scaled(r[8], ac_current_sf, signed=True),
            "l1_buy_current": _scaled(r[9], ac_current_sf, signed=True),
            "l1_sell_current": _scaled(r[10], ac_current_sf, signed=True),
            "l1_grid_voltage": _scaled(r[11], ac_voltage_sf),
            "l1_output_voltage": _scaled(r[13], ac_voltage_sf),
            "l2_output_current": _scaled(r[14], ac_current_sf, signed=True),
            "l2_charge_current": _scaled(r[15], ac_current_sf, signed=True),
            "l2_buy_current": _scaled(r[16], ac_current_sf, signed=True),
            "l2_sell_current": _scaled(r[17], ac_current_sf, signed=True),
            "l2_grid_voltage": _scaled(r[18], ac_voltage_sf),
            "l2_output_voltage": _scaled(r[20], ac_voltage_sf),
            "output_power": _scaled(r[54], power_sf),
            "buy_power": _scaled(r[55], power_sf),
            "sell_power": _scaled(r[56], power_sf),
            "charge_power": _scaled(r[57], power_sf),
            "load_power": _scaled(r[58], power_sf),
            "ac_couple_power": _scaled(r[59], power_sf) if len(r) > 59 else None,
        }

    @staticmethod
    def _parse_charge_controller(r: list[int]) -> dict[str, Any]:
        """Decode OutBack DID 64111."""
        voltage_sf = _s16(r[3])
        current_sf = _s16(r[4])
        power_sf = _s16(r[5])
        kwh_sf = _s16(r[7])

        port = r[2]
        state_raw = r[12]
        return {
            "port": port,
            "label": CHARGE_CONTROLLER_LABELS.get(port, f"Charge Controller Port {port}"),
            "battery_voltage": _scaled(r[8], voltage_sf),
            "pv_voltage": _scaled(r[9], voltage_sf),
            "output_current": _scaled(r[10], current_sf),
            "charger_state_raw": state_raw,
            "charger_state": CHARGER_STATES.get(
                state_raw, f"Unknown ({state_raw})"
            ),
            "output_power_w": _scaled(r[13], power_sf),
            "today_energy_kwh": _scaled(r[18], kwh_sf),
        }

    @staticmethod
    def _parse_fndc(r: list[int]) -> dict[str, Any]:
        """Decode OutBack DID 64118."""
        voltage_sf = _s16(r[3])
        current_sf = _s16(r[4])
        time_sf = _s16(r[5])
        kw_sf = _s16(r[7])

        return {
            "port": r[2],
            "shunt_a_current": _scaled(r[8], current_sf, signed=True),
            "shunt_b_current": _scaled(r[9], current_sf, signed=True),
            "shunt_c_current": _scaled(r[10], current_sf, signed=True),
            "battery_voltage": _scaled(r[11], voltage_sf),
            "battery_current": _scaled(r[12], current_sf, signed=True),
            "net_power": _scaled(r[25], kw_sf, signed=True),
            "days_since_full": _scaled(r[26], time_sf),
            "soc": r[27],
        }
