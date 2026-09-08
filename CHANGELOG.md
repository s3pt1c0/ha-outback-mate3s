# Changelog

## 1.2.2 - 2026-09-08

### Write reliability and authentication

- Added MATE3s Modbus write authentication through DID 64110 `OutBack_Write_Password` before every exposed write operation.
- Existing installations default to the documented MATE3s installer password **1732**; integrations with a changed installer password can update it through the Home Assistant **Reconfigure** flow.
- The write password is stored in the config entry and is not exposed as an entity.
- Added a persistent DID/HUB-port block cache so charge-controller writes use the controller block already identified during normal polling instead of probing the HUB port again at write time.
- Improved write-verification errors when the read-back value is `0x8000`.
- Grid Use Interval time writes now authenticate before the FC16 multi-register write.
- Removed the 12 cumulative FNDC shunt history entities requested by the user: returned/removed Ah and returned/removed energy for Shunts A, B, and C.
- Retained Shunt A/B/C maximum charge/discharge current and power diagnostics.

## 1.2.1 - 2026-09-08

### Multi-device support

- Added dynamic discovery and telemetry for **multiple Radian GS8048A** inverters (all DID 64115 blocks), keyed by HUB port.
- Single-Radian installations keep the existing entity unique IDs for backward compatibility.
- Multi-Radian installations receive a separate sensor set for every discovered inverter, labeled by Radian number and HUB port.
- Added dynamic charge-controller model detection from DID 64112 model data; FM80/FM100 labels and numbering no longer depend on fixed HUB ports.
- Supports the additional validation topology: ports 1-2 = 2 x GS8048A, ports 3-5 = 3 x FM100, port 10 = FNDC.
- Charge-controller writes continue to target the controller's actual HUB port.
- Grid Use, Inverter Mode, Grid Tie and other DID 64120 controls remain system-level controls instead of being incorrectly duplicated per Radian.
- Grid Use state now checks all discovered Radians and reports unknown if stacked inverter states disagree.
- FNDC shunt names are now generic Shunt A/B/C because physical shunt assignments are installation-specific.
- No synthetic stacked-Radian total power sensors were added; per-inverter values are exposed until field validation confirms the correct aggregation behavior.

## 1.2.0 - 2026-09-08

### HACS / repository presentation

- Advanced versioning from 1.1.9 to **1.2.0**. Future patch progression continues as 1.2.1, 1.2.2, etc.
- Added root `brand/` assets for repository/HACS presentation while retaining the integration-local brand assets under `custom_components/outback_mate3s/brand/`.
- Added a three-step installation section with **My Home Assistant** buttons for opening the HACS repository and Home Assistant Integrations page.
- Added `.github/workflows/hacs.yaml` for HACS validation.
- Added `.github/workflows/hassfest.yaml` for Home Assistant hassfest validation.
- Retained `.github/workflows/release.yaml` for automatic semantic GitHub tag/release creation.
- No functional telemetry or write-control changes from 1.1.10.

## 1.1.10 - 2026-09-08

### Entity cleanup

- Removed selected low-value Radian diagnostic sensors: temperature-compensated target voltage, generator L1/L2 voltage, AC-couple power, AC2/generator daily energy, Radian battery temperature, AUX output state, and AUX relay state.
- Removed selected FNDC diagnostic/history sensors: battery temperature, status, days since full, charge-factor-corrected totals, min/max voltage timestamps, cycle charge factor/efficiency, total days at 100%, and lifetime kAh removed.
- Removed AC1/AC2 current-limit sensor duplicates and AGS/generator last-run sensor entities. Writable `number` controls remain available.
- Removed FM100/FM80 lifetime statistics, FET temperature, and enclosure temperature sensor entities.
- No changes to selected write controls, Grid Use intervals, 10-second realtime polling, 5-minute control-data polling, or `Refresh Control Data`.

## 1.1.9 - 2026-09-08

- Kept all functionality from 1.1.8 unchanged.
- Added `.github/workflows/release.yaml` to automatically create a GitHub tag and Release matching the version in `manifest.json`.
- Updated package and documentation version references to 1.1.9.

## 1.1.8 - 2026-09-08

- Added automated GitHub Release creation for semantic HACS versioning.
- The release workflow reads the integration version from `manifest.json` and creates the matching tag/release when missing.
- HACS/Home Assistant can therefore show versions such as `1.1.8` instead of short Git commit hashes.
- No telemetry or write-control behavior changed from 1.1.7.
- Retains the 10-second real-time polling, 5-minute configuration polling, manual **Refresh Control Data** button, and all L1/L2 amperage sensors.

## 1.1.7 - 2026-09-08

- Changed writable/configuration polling from approximately 1 minute to **5 minutes**.
- Added a Home Assistant **Refresh Control Data** button for on-demand refresh of all currently exposed writable settings.
- Successful writes still force an immediate control-data refresh so the UI reflects the new value without waiting five minutes.
- Real-time Radian/FM/FNDC telemetry remains on the 10-second polling cadence.
- Keeps the transient Modbus failure protection introduced in 1.1.6.

## 1.1.6

- Stability hotfix for intermittent `unavailable` entities.
- Keep the 10-second real-time polling cadence.
- Poll writable/configuration values approximately once per minute instead of every 10 seconds.
- Read only the required controller configuration registers (24 instead of the full 90-register block).
- Keep last-good writable/configuration values if an optional control refresh fails.
- Tolerate up to two consecutive transient real-time Modbus failures before marking the integration unavailable.
- Force an immediate configuration refresh after a successful write.
- Keeps all L1/L2 buy, sell, inverter and calculated house-current sensors introduced in 1.1.4/1.1.5.

All tracked changes to this project will be documented in this file.

## 1.1.5 - 2026-09-08

### Added

- Initial selected Modbus write/control support.
- Radian Grid Use / Grid Drop switch.
- Radian Inverter Mode select: Off, Search, On.
- Radian Grid Tie enable/disable switch.
- Writable Sell Voltage, Sell Current Limit, Grid Input Current Limit, Generator Input Current Limit, and Charger Current Limit.
- Per-controller FM100/FM80 writable Absorb Voltage, Absorb Time, Absorb End Amps, Rebulk Voltage, Float Voltage, Bulk Current Limit, and Grid Tie Mode.
- Grid Use Interval 1 enable plus weekday/weekend start and stop time controls.
- Grid Use Interval 2 enable plus weekday start and stop time controls.
- Read-back verification for R/W register changes.

### Fixed

- Restores the L1/L2 amperage entities that were documented for 1.1.3 but were not present in the GitHub copy that Home Assistant downloaded: Grid L1/L2 Buy Current, Grid L1/L2 Sell Current, Inverter L1/L2 Output Current, Inverter L1/L2 Charge Current, and House L1/L2 Current.
- Carries forward the full expanded read-only telemetry prepared in 1.1.4.

### Safety

- Write support is limited to the explicitly approved controls above. Network, firmware, calibration, model-selection and reset registers remain unexposed.

## 1.1.4 - 2026-09-08

### Added

- Full Radian L1/L2 grid, generator, output-voltage and AC-current telemetry.
- Radian error, warning, sell-status, AUX state, module-temperature and daily energy sensors.
- Expanded FM100/FM80 telemetry: array current, min/max voltage, VOC, Ah, lifetime and temperature sensors.
- Major FLEXnet-DC expansion including daily SOC/energy, battery temperature, status, input/output flows, cycle efficiency, accumulated shunt telemetry, historical returned/removed energy, and maximum charge/discharge rates.
- OutBack System Control / AGS read-only status sensors from DID 64120.
- Diagnostic categorization for historical and troubleshooting-oriented entities.

### Changed

- Version bumped to 1.1.4.
- Expanded README sensor documentation.
- Polling remains block-based: additional entities do not create additional per-entity Modbus requests.

### Safety

- Still read-only. No Modbus write operations were added.

## 1.1.3 - 2026-09-08

First tracked release.

### Added

- Direct MATE3s communication through Home Assistant's shared Modbus connection API.
- Dynamic SunSpec block discovery.
- OutBack Radian split-phase real-time support (DID 64115).
- OutBack charge-controller real-time support (DID 64111).
- FLEXnet-DC real-time support (DID 64118).
- FM100 #1, FM100 #2, and FM80 sensor labeling by HUB port for the initial tested system.
- Radian operating mode, AC input state, battery voltage, frequency, and power sensors.
- Grid L1/L2 voltage sensors.
- Grid Buy/Sell power sensors.
- Grid L1/L2 Buy Current sensors.
- Grid L1/L2 Sell Current sensors.
- House Power sensor.
- House L1/L2 Current sensors derived from the per-leg AC current balance.
- Charge-controller PV voltage, battery voltage, output current, output power, charger state, and daily energy sensors.
- Solar Total Power and Solar Today Energy sensors.
- FLEXnet-DC SOC, battery voltage/current, net power, days-since-full, and shunt current sensors.
- English entity names.
- Local Home Assistant brand asset support in the integration package.
- HACS custom repository metadata.

### Safety

- Read-only release. No Modbus write operations are implemented.
