"""Config flow for OutBack MATE3s."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow
from modbus_connection import ModbusError, ModbusTcpParams

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from .device import OutbackMate3sDevice, OutbackProtocolError


async def _async_validate(
    hass,
    host: str,
    port: int,
    unit_id: int,
) -> None:
    """Validate the connection and confirm the OutBack blocks exist."""
    params = ModbusTcpParams(host=host, port=port)

    async with async_get_temporary_unit(hass, params, unit_id) as unit:
        device = OutbackMate3sDevice(unit)
        blocks = await device.async_discover()

    dids = {block.did for block in blocks}
    required = {64115, 64111, 64118}
    missing = required - dids
    if missing:
        raise OutbackProtocolError(
            "Expected OutBack real-time DIDs not found: "
            + ", ".join(str(v) for v in sorted(missing))
        )


class OutbackMate3sConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an OutBack MATE3s config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            unit_id = int(user_input[CONF_UNIT_ID])

            try:
                await _async_validate(self.hass, host, port, unit_id)
            except (ModbusError, TimeoutError):
                errors["base"] = "cannot_connect"
            except OutbackProtocolError:
                errors["base"] = "not_outback"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                    }
                )
                return self.async_create_entry(
                    title=f"OutBack MATE3s {host}",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=(user_input.get(CONF_HOST, "") if user_input else ""),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=(
                        user_input.get(CONF_PORT, DEFAULT_PORT)
                        if user_input
                        else DEFAULT_PORT
                    ),
                ): int,
                vol.Required(
                    CONF_UNIT_ID,
                    default=(
                        user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
                        if user_input
                        else DEFAULT_UNIT_ID
                    ),
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
