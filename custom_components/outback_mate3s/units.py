"""Temperature display-unit handling for OutBack MATE3s sensors.

OutBack reports every temperature in degrees Celsius. The integration keeps
Celsius as the native unit and lets Home Assistant convert for display. The
user's choice in the integration options is applied through the entity
registry's standard ``sensor`` unit override, the same setting written by the
per-entity *Unit of measurement* dropdown.

This module has no Home Assistant imports so the planning logic can be tested
on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CELSIUS = "°C"
FAHRENHEIT = "°F"

SENSOR_OPTIONS_DOMAIN = "sensor"
UNIT_KEY = "unit_of_measurement"
APPLIED_KEY = "temperature_unit_applied"


def target_unit(choice: str) -> str | None:
    """Map an options-flow choice to a unit; None means Home Assistant decides."""
    return {"celsius": CELSIUS, "fahrenheit": FAHRENHEIT}.get(choice)


def plan_registry_updates(
    options: Mapping[str, Mapping[str, Any]],
    choice: str,
    domain: str,
) -> dict[str, dict[str, Any] | None]:
    """Return the registry option domains to write for one temperature entity.

    ``options`` is the entity's current registry options. The result maps an
    option domain to its new dict, or None to remove that domain. An empty
    result means nothing needs to change.

    - Celsius/Fahrenheit: set the ``sensor`` unit override and remember it.
    - Automatic: remove the override only if this integration set it, so a
      unit the user picked by hand is never discarded.
    """
    sensor_opts = dict(options.get(SENSOR_OPTIONS_DOMAIN) or {})
    own_opts = dict(options.get(domain) or {})
    applied = own_opts.get(APPLIED_KEY)
    target = target_unit(choice)
    updates: dict[str, dict[str, Any] | None] = {}

    if target is not None:
        if sensor_opts.get(UNIT_KEY) != target:
            sensor_opts[UNIT_KEY] = target
            updates[SENSOR_OPTIONS_DOMAIN] = sensor_opts
        if applied != target:
            own_opts[APPLIED_KEY] = target
            updates[domain] = own_opts
        return updates

    if applied is not None:
        if sensor_opts.get(UNIT_KEY) == applied:
            sensor_opts.pop(UNIT_KEY)
            updates[SENSOR_OPTIONS_DOMAIN] = sensor_opts or None
        own_opts.pop(APPLIED_KEY)
        updates[domain] = own_opts or None
    return updates
