# OutBack MATE3s for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-blue)
![Version](https://img.shields.io/badge/version-1.1.8-green)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Modbus](https://img.shields.io/badge/Modbus-TCP-red)

A native Home Assistant custom integration for monitoring and controlling **OutBack Power MATE3 / MATE3s systems directly over Modbus TCP**.

It communicates directly with the MATE3s using Home Assistant's shared Modbus connection API. No external Raspberry Pi, MQTT bridge, REST/JSON polling, or additional daemon is required.

## Features

- Direct Modbus TCP communication with the MATE3s
- Uses Home Assistant's shared Modbus connection API
- Automatic SunSpec block discovery
- Native Home Assistant sensors and controls
- Local polling
- Selected write/control support with read-back verification
- No cloud dependency
- No MQTT dependency
- No external scripts or computers required
- Local integration branding support on Home Assistant 2026.3+

## Tested system

Initially developed and tested with:

| HUB Port | Device |
|---:|---|
| 1 | OutBack Radian GS8048A |
| 2 | FM100 #1 |
| 3 | FM100 #2 |
| 4 | FM80 |
| 10 | FLEXnet-DC |

FNDC shunts in the initial test system:

| Shunt | Assignment |
|---|---|
| A | Inverter |
| B | FM80 |
| C | FM100 |

## OutBack SunSpec blocks

The integration discovers the actual register locations dynamically and reads the OutBack vendor extensions used by the MATE3s:

| Device | DID |
|---|---:|
| OutBack Gateway / Grid Use timers | `64110` |
| Charge Controller Real-Time | `64111` |
| Charge Controller Configuration | `64112` |
| Radian Split Phase Real-Time | `64115` |
| FLEXnet-DC Real-Time | `64118` |
| OutBack System Control / AGS | `64120` |

No fixed absolute register addresses are required.

## Sensors

Version 1.1.4 expands the integration to expose nearly all useful **read/status telemetry** available in the documented OutBack real-time blocks. Diagnostic and historical values are marked as diagnostic entities in Home Assistant where appropriate.

### Radian / AC

Includes operating mode, AC input state/selection, error/warning/sell status, battery and temperature-compensated target voltage, AC frequency, grid/generator/output voltages on L1/L2, inverter output/charge currents, grid buy/sell currents, derived house current on L1/L2, real-time power flows, daily buy/sell/output/charger energy, AUX states, and left/right module temperatures.

### House current calculation

OutBack DID 64115 does not publish a dedicated per-leg load-current register. House current is derived from the documented current balance:

```text
House Current = Buy Current + Inverter Output Current - Sell Current - Charge Current
```

This works in Pass Through mode as well as inverter/selling modes.

### Charge controllers

For every detected FM100/FM80 controller the integration includes PV/battery voltage, battery output and array current, watts, charger state, daily min/max battery voltage, VOC and peak VOC, today kWh/Ah, lifetime energy, lifetime maximum watts/voltage/VOC, and available controller temperature telemetry.

### Solar totals

- Solar Total Power
- Solar Today Energy

### FLEXnet-DC

Includes SOC, battery voltage/current/temperature, status flags, input/output/net current and power, days since full, daily min/max SOC, daily input/output/net battery Ah and kWh, charge-factor-corrected totals, min/max battery voltage and timestamps, cycle charge factor/efficiency, total days at 100%, lifetime removed capacity, accumulated shunt data, and historical returned/removed energy plus maximum charge/discharge rates for Shunts A/B/C.

### OutBack System Control / AGS

Read-only sensors include current global sell/absorb/float values, charger and AC input current limits, AGS mode/state/timer, and generator last-run start/duration.

### Polling efficiency

The large number of Home Assistant entities does **not** result in one Modbus request per entity. The coordinator reads each OutBack real-time block once per polling cycle and all entities use the same cached data.


## Writable controls (1.1.8)

Version 1.1.8 includes a deliberately limited write surface for the settings requested for the tested system. Writes use the same Home Assistant shared Modbus connection, and R/W fields are read back after each write for verification.

Writable/configuration values are automatically refreshed every **5 minutes** instead of every real-time polling cycle. Home Assistant also exposes a **Refresh Control Data** button to immediately re-read all currently exposed writable settings. Successful writes force an immediate settings refresh as well.

### Radian / system controls

- Grid Use switch: ON = Grid Use, OFF = Grid Drop
- Inverter Mode select: Off / Search / On
- Grid Tie switch
- Sell Voltage
- Sell Current Limit
- Grid Input Current Limit
- Generator Input Current Limit
- Charger Current Limit

### Charge-controller controls

For each detected FM100/FM80:

- Absorb Voltage
- Absorb Time
- Absorb End Amps
- Rebulk Voltage
- Float Voltage
- Bulk Current Limit
- Grid Tie Mode

### Grid Use timers

- Grid Use Interval 1 enable/disable
- Interval 1 weekday start/stop
- Interval 1 weekend start/stop
- Grid Use Interval 2 enable/disable
- Interval 2 weekday start/stop

The documented OutBack map does not expose separate weekend times for Grid Use Interval 2, so they are not invented here.

## Requirements

- Home Assistant **2026.9.0 or newer**
- MATE3 / MATE3s with Modbus TCP enabled
- TCP connectivity from Home Assistant to the MATE3s, normally port `502`

Typical configuration:

```text
Host: 192.168.10.100
Port: 502
Unit ID: 1
```

## HACS installation

Add this repository as a custom HACS integration:

1. Open **HACS**.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/s3pt1c0/ha-outback-mate3s`.
4. Select **Integration**.
5. Install **OutBack MATE3s**.
6. Restart Home Assistant.
7. Go to **Settings > Devices & services > Add integration**.
8. Search for **OutBack MATE3s**.

## Manual installation

Copy:

```text
custom_components/outback_mate3s
```

to:

```text
/config/custom_components/outback_mate3s
```

Restart Home Assistant, then add **OutBack MATE3s** from **Settings > Devices & services**.

## Polling

The default polling interval is 10 seconds.

## Safety

Write support is intentionally restricted to the controls listed above. Network settings, firmware-update registers, calibration values, model selection, serial-number fields, FNDC reset registers, and other potentially destructive settings remain unexposed.

Changing Grid Use to OFF commands **Grid Drop**. It does not open a physical utility breaker; it commands the Radian to stop using the grid input and the house must then be supported by the inverter/PV/battery system as configured.

## Versioning

Tracked releases start at **1.1.3**. Patch releases will continue sequentially:

```text
Current Release -> 1.1.8.
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

### HACS release versions

Starting with **1.1.8**, the repository includes a GitHub Actions release workflow. When a new version is committed to the default branch, the workflow reads the version from `manifest.json` and creates a matching GitHub Release/tag if it does not already exist. This allows HACS/Home Assistant to display semantic versions such as `1.1.8` instead of short commit hashes.

## Troubleshooting

Check TCP connectivity from Home Assistant:

```bash
nc -vz MATE3S_IP 502
```

View integration logs:

```bash
ha core logs | grep -i outback_mate3s
```

## Disclaimer

This is an independent community integration and is not affiliated with or endorsed by OutBack Power Technologies or the SunSpec Alliance.

OutBack, MATE3s, Radian, FLEXnet-DC, FM80, and FM100 are trademarks or product names of their respective owners.

## License

MIT License.
