"""Entity-registry migrations for OutBack MATE3s.

No Home Assistant imports, so the planning logic can be tested on its own.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

# 1.3.3: "Selected AC Input Voltage" was renamed "Grid AC Input Voltage".
# The unique ID is unchanged; only the default entity ID is migrated.
_RENAMES: tuple[tuple[str, str, str], ...] = (
    # (unique_id suffix, old entity_id suffix, new entity_id suffix)
    (
        "_selected_input_voltage",
        "_selected_ac_input_voltage",
        "_grid_ac_input_voltage",
    ),
)


def plan_entity_id_renames(entries: Iterable[Any]) -> list[tuple[str, str]]:
    """Return (old_entity_id, new_entity_id) pairs to apply.

    ``entries`` are entity-registry entries with ``domain``, ``unique_id`` and
    ``entity_id``. An entity ID the user changed by hand no longer ends with
    the old default suffix, so it is left alone.
    """
    renames: list[tuple[str, str]] = []
    for entry in entries:
        if entry.domain != "sensor":
            continue
        for unique_suffix, old_suffix, new_suffix in _RENAMES:
            if entry.unique_id.endswith(unique_suffix) and entry.entity_id.endswith(
                old_suffix
            ):
                new_id = entry.entity_id[: -len(old_suffix)] + new_suffix
                renames.append((entry.entity_id, new_id))
    return renames
