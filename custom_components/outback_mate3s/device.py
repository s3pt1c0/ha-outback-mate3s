"""OutBack MATE3s Modbus/SunSpec device model with read/write controls."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import datetime, time as dt_time, timezone
from time import monotonic
from typing import Any

from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)


from .const import (
    CONTROL_SCAN_INTERVAL,
    DID_CHARGE_CONTROLLER_CONFIG,
    DID_CHARGE_CONTROLLER_REALTIME,
    DID_FNDC_REALTIME,
    DID_OUTBACK_GATEWAY,
    DID_OUTBACK_SYSTEM_CONTROL,
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


def _decode_sunspec_string(registers: list[int]) -> str:
    """Decode a SunSpec fixed-length string from 16-bit registers."""
    raw = bytearray()
    for value in registers:
        raw.extend(((value >> 8) & 0xFF, value & 0xFF))
    return raw.decode("ascii", errors="ignore").replace("\x00", "").strip()


def _encode_sunspec_string(value: str, register_count: int) -> list[int]:
    """Encode ASCII as a null-padded SunSpec string."""
    raw = value.encode("ascii", errors="strict")
    max_bytes = register_count * 2
    if len(raw) > max_bytes:
        raise ValueError(
            f"SunSpec string is too long ({len(raw)} bytes; max {max_bytes})"
        )
    raw = raw.ljust(max_bytes, b"\x00")
    return [
        (raw[index] << 8) | raw[index + 1]
        for index in range(0, max_bytes, 2)
    ]


def _controller_type_from_model(model: str | None) -> str:
    """Return a stable controller family name from the OutBack model string."""
    text = (model or "").upper().replace("-", " ")
    compact = text.replace(" ", "")
    if "FM100" in compact or "FLEXMAX100" in compact:
        return "FM100"
    if "FM80" in compact or "FLEXMAX80" in compact:
        return "FM80"
    return "Charge Controller"


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

    def __init__(self, unit: ModbusUnit, *, write_password: str = "1732") -> None:
        self.unit = unit
        self.write_password = str(write_password).strip()
        self.blocks: list[Block] = []
        # Cache DID/HUB-port block locations once they have been positively
        # identified. Writes then use the known block instead of probing every
        # controller again at the instant a user changes a setting.
        self._block_by_port: dict[tuple[int, int], Block] = {}
        # Writable/configuration blocks change infrequently. Keep a last-good
        # cache and refresh those blocks every five minutes, on manual request,
        # or immediately after a write. Real-time telemetry stays at 10 seconds.
        self._control_cache: dict[str, Any] = {
            "system_control": None,
            "charge_controller_configs": {},
            "gateway_control": None,
        }
        self._last_control_refresh: float | None = None
        self._force_control_refresh = True

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
        """Read real-time data and periodically refresh writable settings."""
        if not self.blocks:
            await self.async_discover()

        data: dict[str, Any] = {
            # ``radian`` is kept for backward compatibility with single-inverter
            # installations. ``radians`` contains every discovered Radian keyed
            # by HUB port and is used for stacked / multi-Radian systems.
            "radian": None,
            "radians": {},
            "charge_controllers": {},
            "charge_controller_configs": dict(
                self._control_cache.get("charge_controller_configs", {})
            ),
            "fndc": None,
            "system_control": self._control_cache.get("system_control"),
            "gateway_control": self._control_cache.get("gateway_control"),
            "topology": [
                {"address": b.address, "did": b.did, "length": b.length}
                for b in self.blocks
            ],
        }

        # Real-time blocks remain on the normal 10-second coordinator cadence.
        radian_blocks = self._blocks(DID_RADIAN_SPLIT_REALTIME)
        for block in radian_blocks:
            radian = self._parse_radian(await self._read_block(block))
            data["radians"][radian["port"]] = radian
            self._block_by_port[
                (DID_RADIAN_SPLIT_REALTIME, int(radian["port"]))
            ] = block

        # Give every Radian a deterministic label by HUB-port order. Keep the
        # legacy single-Radian data key so existing installations retain their
        # entity IDs and dashboards. Multi-Radian installations get per-port
        # entities instead of an unsafe synthetic system total.
        radian_ports = sorted(data["radians"])
        for index, port in enumerate(radian_ports, start=1):
            radian = data["radians"][port]
            radian["label"] = (
                "Radian"
                if len(radian_ports) == 1
                else f"Radian #{index} (Port {port})"
            )
        if radian_ports:
            data["radian"] = data["radians"][radian_ports[0]]

        for block in self._blocks(DID_CHARGE_CONTROLLER_REALTIME):
            cc = self._parse_charge_controller(await self._read_block(block))
            data["charge_controllers"][cc["port"]] = cc
            self._block_by_port[
                (DID_CHARGE_CONTROLLER_REALTIME, int(cc["port"]))
            ] = block

        fndc_blocks = self._blocks(DID_FNDC_REALTIME)
        if fndc_blocks:
            data["fndc"] = self._parse_fndc(
                await self._read_block(fndc_blocks[0])
            )
            self._block_by_port[
                (DID_FNDC_REALTIME, int(data["fndc"]["port"]))
            ] = fndc_blocks[0]

        # Configuration/control data is intentionally much slower than real-time
        # telemetry. These settings normally do not change day-to-day, so poll
        # them every five minutes. A manual Home Assistant button and every
        # successful write can force an immediate refresh.
        now = monotonic()
        refresh_controls = (
            self._force_control_refresh
            or self._last_control_refresh is None
            or now - self._last_control_refresh
            >= CONTROL_SCAN_INTERVAL.total_seconds()
        )

        if refresh_controls:
            system_blocks = self._blocks(DID_OUTBACK_SYSTEM_CONTROL)
            if system_blocks:
                try:
                    # Starts 1..27 are enough for every value currently exposed.
                    regs = await self.unit.read_holding_registers(
                        system_blocks[0].address, 27
                    )
                    if len(regs) == 27 and regs[0] == DID_OUTBACK_SYSTEM_CONTROL:
                        self._control_cache["system_control"] = (
                            self._parse_system_control(regs)
                        )
                except Exception as err:  # optional control telemetry
                    _LOGGER.warning("System-control refresh failed: %s", err)

            configs: dict[int, dict[str, Any]] = dict(
                self._control_cache.get("charge_controller_configs", {})
            )
            for block in self._blocks(DID_CHARGE_CONTROLLER_CONFIG):
                try:
                    # We only expose Starts 3..24. Reading 24 registers instead
                    # of the entire 90-register configuration block is gentler
                    # on the MATE3s and is enough for every current control.
                    regs = await self.unit.read_holding_registers(block.address, 24)
                    if len(regs) == 24 and regs[0] == DID_CHARGE_CONTROLLER_CONFIG:
                        config = self._parse_charge_controller_config(regs)
                        # Starts 82..90 contain the 18-character controller model.
                        # Read this small range only on the slow control cadence so
                        # FM80/FM100 labels can be generated without fixed HUB ports.
                        try:
                            model_regs = await self.unit.read_holding_registers(
                                block.address + 81, 9
                            )
                            if len(model_regs) == 9:
                                config["model"] = _decode_sunspec_string(model_regs)
                        except Exception as err:
                            _LOGGER.debug(
                                "Controller model read failed at %s: %s",
                                block.address,
                                err,
                            )
                        config["controller_type"] = _controller_type_from_model(
                            config.get("model")
                        )
                        configs[config["port"]] = config
                        self._block_by_port[
                            (DID_CHARGE_CONTROLLER_CONFIG, int(config["port"]))
                        ] = block
                except Exception as err:  # optional control telemetry
                    _LOGGER.warning(
                        "Charge-controller config refresh failed at %s: %s",
                        block.address,
                        err,
                    )
            self._control_cache["charge_controller_configs"] = configs

            gateway_blocks = self._blocks(DID_OUTBACK_GATEWAY)
            if gateway_blocks:
                try:
                    # Grid Use Interval section only: Starts 337..350.
                    regs = await self.unit.read_holding_registers(
                        gateway_blocks[0].address + 336, 14
                    )
                    if len(regs) == 14:
                        self._control_cache["gateway_control"] = (
                            self._parse_gateway_control(regs)
                        )
                except Exception as err:  # optional control telemetry
                    _LOGGER.warning("Grid Use Interval refresh failed: %s", err)

            self._force_control_refresh = False
            self._last_control_refresh = now

        data["system_control"] = self._control_cache.get("system_control")
        data["charge_controller_configs"] = dict(
            self._control_cache.get("charge_controller_configs", {})
        )
        data["gateway_control"] = self._control_cache.get("gateway_control")
        self._apply_charge_controller_labels(data)
        return data

    @staticmethod
    def _apply_charge_controller_labels(data: dict[str, Any]) -> None:
        """Label discovered controllers by model family and HUB-port order."""
        controllers = data.get("charge_controllers", {})
        configs = data.get("charge_controller_configs", {})
        if not controllers:
            return

        type_by_port: dict[int, str] = {}
        for port in sorted(controllers):
            config = configs.get(port, {})
            controller_type = config.get("controller_type") or _controller_type_from_model(
                config.get("model")
            )
            type_by_port[port] = controller_type
            controllers[port]["model"] = config.get("model")
            controllers[port]["controller_type"] = controller_type

        totals: dict[str, int] = {}
        for controller_type in type_by_port.values():
            totals[controller_type] = totals.get(controller_type, 0) + 1

        seen: dict[str, int] = {}
        generic_index = 0
        for port in sorted(controllers):
            controller_type = type_by_port[port]
            seen[controller_type] = seen.get(controller_type, 0) + 1
            if controller_type == "Charge Controller":
                generic_index += 1
                label = f"Charge Controller #{generic_index}"
            elif totals[controller_type] > 1:
                label = f"{controller_type} #{seen[controller_type]}"
            else:
                label = controller_type
            controllers[port]["label"] = label
            controllers[port]["hub_port"] = port

    def force_control_refresh(self) -> None:
        """Refresh writable settings on the next coordinator update."""
        self._force_control_refresh = True

    async def _async_block_for_port(self, did: int, port: int | None = None) -> Block:
        """Find one discovered block, optionally matching its HUB port."""
        blocks = self._blocks(did)
        if not blocks:
            raise OutbackProtocolError(f"Required DID {did} was not discovered")
        if port is None:
            return blocks[0]

        cached = self._block_by_port.get((did, int(port)))
        if cached is not None:
            return cached

        # Fallback only if the block was not already indexed during the normal
        # poll. Successful fallback discovery is cached for future writes.
        for block in blocks:
            value = await self.unit.read_holding_registers(block.address + 2, 1)
            if value and value[0] == port:
                self._block_by_port[(did, int(port))] = block
                return block
        raise OutbackProtocolError(f"DID {did} for HUB port {port} was not discovered")

    async def _async_unlock_writes(self) -> None:
        """Send the MATE3s write/installer password before a write operation."""
        password = self.write_password.strip()
        if not password:
            raise OutbackProtocolError(
                "MATE3s write password is not configured. "
                "Use Reconfigure on the integration and enter the current "
                "installer/write password."
            )

        # DID 64110 Starts 14..21 are the 16-character write-password field.
        # It is write-only, so there is intentionally no read-back verification.
        gateway = await self._async_block_for_port(DID_OUTBACK_GATEWAY)
        password_registers = _encode_sunspec_string(password, 8)
        await self.unit.write_registers(
            gateway.address + 14 - 1,
            password_registers,
        )

    async def _async_write_raw(
        self,
        did: int,
        start: int,
        raw_value: int,
        *,
        port: int | None = None,
        verify: bool = True,
    ) -> None:
        """Write one 16-bit field using a SunSpec Start number."""
        if not 0 <= raw_value <= 0xFFFF:
            raise ValueError(f"Raw register value out of range: {raw_value}")
        block = await self._async_block_for_port(did, port)
        address = block.address + start - 1
        await self._async_unlock_writes()
        await self.unit.write_register(address, raw_value)
        self.force_control_refresh()
        if verify:
            check = await self.unit.read_holding_registers(address, 1)
            if len(check) != 1 or check[0] != raw_value:
                got = check[0] if check else None
                hint = (
                    " (0x8000 can indicate an unavailable/rejected value; "
                    "verify the MATE3s installer/write password)"
                    if got == 0x8000
                    else ""
                )
                raise OutbackProtocolError(
                    f"Write verification failed for DID {did} Start {start}: "
                    f"wrote {raw_value}, read {got}{hint}"
                )

    async def _async_write_scaled(
        self,
        did: int,
        start: int,
        sf_start: int,
        value: float,
        *,
        port: int | None = None,
    ) -> None:
        """Scale and write one unsigned OutBack register, then verify it."""
        block = await self._async_block_for_port(did, port)
        sf_regs = await self.unit.read_holding_registers(block.address + sf_start - 1, 1)
        if len(sf_regs) != 1:
            raise OutbackProtocolError(
                f"Unable to read scale factor for DID {did} Start {sf_start}"
            )
        sf = _s16(sf_regs[0])
        raw = int(round(float(value) / (10**sf)))
        await self._async_write_raw(did, start, raw, port=port, verify=True)

    async def async_set_system_number(self, field: str, value: float) -> None:
        """Set one approved Radian/System Control numeric setting."""
        mapping = {
            "sell_voltage": (12, 3),
            "sell_current_limit": (13, 4),
            "charger_current_limit": (18, 4),
            "grid_input_current_limit": (19, 4),
            "generator_input_current_limit": (20, 4),
        }
        if field not in mapping:
            raise ValueError(f"Unsupported system setting: {field}")
        start, sf_start = mapping[field]
        await self._async_write_scaled(
            DID_OUTBACK_SYSTEM_CONTROL, start, sf_start, value
        )

    async def async_set_charge_controller_number(
        self, port: int, field: str, value: float
    ) -> None:
        """Set one approved FM100/FM80 charger parameter."""
        scaled = {
            "absorb_voltage": (11, 4),
            "absorb_time": (12, 6),
            "rebulk_voltage": (14, 4),
            "float_voltage": (15, 4),
            "bulk_current_limit": (16, 5),
        }
        if field == "absorb_end_amps":
            await self._async_write_raw(
                DID_CHARGE_CONTROLLER_CONFIG, 13, int(round(value)), port=port
            )
            return
        if field not in scaled:
            raise ValueError(f"Unsupported charge-controller setting: {field}")
        start, sf_start = scaled[field]
        await self._async_write_scaled(
            DID_CHARGE_CONTROLLER_CONFIG, start, sf_start, value, port=port
        )

    async def async_set_charge_controller_grid_tie(
        self, port: int, enabled: bool
    ) -> None:
        """Enable or disable Grid Tie Mode on one charge controller."""
        await self._async_write_raw(
            DID_CHARGE_CONTROLLER_CONFIG, 24, 1 if enabled else 0, port=port
        )

    async def async_set_grid_use(self, enabled: bool) -> None:
        """Command the inverter AC input to Grid Use or Grid Drop."""
        # DID 64120 Start 7 is write-only: 1=Use, 2=Drop.
        await self._async_write_raw(
            DID_OUTBACK_SYSTEM_CONTROL, 7, 1 if enabled else 2, verify=False
        )

    async def async_set_inverter_mode(self, mode: str) -> None:
        """Command inverter mode Off/Search/On."""
        values = {"Off": 1, "Search": 2, "On": 3}
        if mode not in values:
            raise ValueError(f"Unsupported inverter mode: {mode}")
        await self._async_write_raw(
            DID_OUTBACK_SYSTEM_CONTROL, 8, values[mode], verify=False
        )

    async def async_set_grid_tie(self, enabled: bool) -> None:
        """Enable or disable Radian Grid Tie mode."""
        # DID 64120 Start 9 is write-only: 1=Enable, 2=Disable.
        await self._async_write_raw(
            DID_OUTBACK_SYSTEM_CONTROL, 9, 1 if enabled else 2, verify=False
        )

    async def async_set_grid_use_interval_enabled(
        self, interval: int, enabled: bool
    ) -> None:
        """Enable or disable MATE3s Grid Use Interval 1 or 2."""
        starts = {1: 337, 2: 346}
        if interval not in starts:
            raise ValueError("Only Grid Use Interval 1 and 2 are supported")
        await self._async_write_raw(
            DID_OUTBACK_GATEWAY, starts[interval], 1 if enabled else 0
        )

    async def async_set_grid_use_interval_time(
        self, interval: int, field: str, value: dt_time
    ) -> None:
        """Write one Grid Use start/stop time as hour + minute registers."""
        starts = {
            (1, "weekday_start"): 338,
            (1, "weekday_stop"): 340,
            (1, "weekend_start"): 342,
            (1, "weekend_stop"): 344,
            (2, "weekday_start"): 347,
            (2, "weekday_stop"): 349,
        }
        key = (interval, field)
        if key not in starts:
            raise ValueError(f"Unsupported Grid Use Interval time: {key}")
        block = await self._async_block_for_port(DID_OUTBACK_GATEWAY)
        address = block.address + starts[key] - 1
        values = [value.hour, value.minute]
        await self._async_unlock_writes()
        await self.unit.write_registers(address, values)
        self.force_control_refresh()
        check = await self.unit.read_holding_registers(address, 2)
        if check != values:
            raise OutbackProtocolError(
                f"Grid Use Interval write verification failed: wrote {values}, read {check}"
            )

    @staticmethod
    def _parse_charge_controller_config(r: list[int]) -> dict[str, Any]:
        """Decode the approved writable fields from DID 64112."""
        voltage_sf = _s16(r[3])
        current_sf = _s16(r[4])
        hours_sf = _s16(r[5])
        return {
            "port": r[2],
            "absorb_voltage": _scaled(r[10], voltage_sf),
            "absorb_time": _scaled(r[11], hours_sf),
            "absorb_end_amps": r[12],
            "rebulk_voltage": _scaled(r[13], voltage_sf),
            "float_voltage": _scaled(r[14], voltage_sf),
            "bulk_current_limit": _scaled(r[15], current_sf),
            "grid_tie_mode": bool(r[23]),
        }

    @staticmethod
    def _parse_gateway_control(r: list[int]) -> dict[str, Any]:
        """Decode DID 64110 Start 337..350 Grid Use Interval values."""
        def make_time(hour: int, minute: int) -> dt_time | None:
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return dt_time(hour, minute)
            return None

        return {
            "interval_1_enabled": bool(r[0]),
            "interval_1_weekday_start": make_time(r[1], r[2]),
            "interval_1_weekday_stop": make_time(r[3], r[4]),
            "interval_1_weekend_start": make_time(r[5], r[6]),
            "interval_1_weekend_stop": make_time(r[7], r[8]),
            "interval_2_enabled": bool(r[9]),
            "interval_2_weekday_start": make_time(r[10], r[11]),
            "interval_2_weekday_stop": make_time(r[12], r[13]),
        }

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
            "label": f"Charge Controller Port {port}",
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
        control_status = r[10]
        if control_status & 0x0008:
            inverter_mode = "Off"
        elif control_status & 0x0010:
            inverter_mode = "Search"
        elif control_status & 0x0020:
            inverter_mode = "On"
        else:
            inverter_mode = None

        return {
            "control_status_raw": control_status,
            "inverter_mode": inverter_mode,
            "grid_tie_enabled": bool(control_status & 0x0040),
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
