# Changelog

All tracked changes to this project will be documented in this file.

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
