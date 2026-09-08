# Changelog

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
