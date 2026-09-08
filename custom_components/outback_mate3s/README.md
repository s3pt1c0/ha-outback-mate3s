# OutBack MATE3s custom integration — v0.3.0

Changes from v0.2:
- Added local Home Assistant brand assets under `brand/`.
- Uses the user-supplied OutBack Power artwork.
- Square integration icon uses the first stylized OutBack `O` so it remains readable in the integration list.
- Full OutBack wordmark is included as the integration logo.
- Includes normal, dark-mode, and @2x variants.

Install by replacing `/config/custom_components/outback_mate3s` and restarting Home Assistant.
If the old placeholder remains, hard-refresh/reopen the frontend because brand images are cached.

# OutBack MATE3s custom integration — v0.2.0

## Changes from v0.1
- Renamed all user-facing sensors to English.
- Replaced `Casa` with `House`.
- Replaced `LUMA` with `Grid`.
- Added a few explicit Material Design icons for better presentation.

## Important note about logos
Home Assistant does **not** reliably load the integration logo from a local custom
component folder. The "logo not available" tile is usually controlled by the
Home Assistant brands pipeline, not by a simple local `logo.png` in the custom
component.

So:
- Entity icons: yes, we can control those locally.
- Integration/logo tile in the UI: normally requires a brands submission or a frontend workaround.

## Install
Replace the folder:

    /config/custom_components/outback_mate3s

with the one from this zip, then restart Home Assistant.

## Reconfiguration
No need to delete the config entry. Just restart Home Assistant after replacing
the files and the entity names should update.
