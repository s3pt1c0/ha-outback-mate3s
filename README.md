# OutBack MATE3s for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-blue)
![Version](https://img.shields.io/badge/version-1.2.0-green)
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
- Realtime telemetry every 10 seconds
- Writable/configuration data refresh every 5 minutes
- Manual **Refresh Control Data** button
- No cloud dependency
- No MQTT dependency
- No external scripts or computers required
- Local OutBack branding

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

### Radian / AC

Includes operating mode, AC input state/selection, grid/output voltages on L1/L2, inverter output/charge currents, grid buy/sell currents, derived house current on L1/L2, real-time power flows, daily energy values, and selected module/diagnostic telemetry.

### House current calculation

OutBack DID 64115 does not publish a dedicated per-leg load-current register. House current is derived from the documented current balance:

```text
House Current = Buy Current + Inverter Output Current - Sell Current - Charge Current
```

This works in Pass Through mode as well as inverter/selling modes.

### Charge controllers

For every detected FM100/FM80 controller the integration includes useful realtime telemetry such as PV/battery voltage, output and array current, watts, charger state, daily min/max battery voltage, VOC/peak VOC, and today kWh/Ah.

Lifetime statistics and controller-temperature entities that were judged low-value for the tested system are intentionally not exposed.

### Solar totals

- Solar Total Power
- Solar Today Energy

### FLEXnet-DC

Includes SOC, battery voltage/current, input/output/net current and power, daily SOC/energy statistics, accumulated shunt data, and selected historical maximum charge/discharge values.

Low-value FNDC history/diagnostic entities removed in 1.1.10 remain intentionally excluded.

## Writable controls

Write support is deliberately limited to the controls used on the tested system. R/W fields use read-back verification.

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

## Installation Instructions (3 Steps)

### Step 1. HACS: add the Integration

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=s3pt1c0&repository=ha-outback-mate3s&category=integration)

Until **OutBack MATE3s** is included in the default HACS store, add it as a custom repository:

1. Open **HACS**.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/s3pt1c0/ha-outback-mate3s`.
4. Select category **Integration**.
5. Install **OutBack MATE3s**.
6. Restart Home Assistant.

Once the repository is accepted into the default HACS store, you will be able to simply search for **OutBack MATE3s** in HACS and install it directly.

### Step 2. Setup the Integration

[![Open your Home Assistant instance and show your integrations.](https://my.home-assistant.io/badges/integrations.svg)](https://my.home-assistant.io/redirect/integrations/)

1. Go to **Settings > Devices & services**.
2. Select **Add Integration**.
3. Search for **OutBack MATE3s**.
4. Enter:
   - **Host**: IP address of your MATE3/MATE3s
   - **Port**: `502`
   - **Unit ID**: `1`
5. Submit.

### Step 3. Verify Communication

The integration automatically discovers the OutBack SunSpec blocks and creates the supported sensors and controls.

Default refresh behavior:

- Realtime telemetry: **10 seconds**
- Writable/configuration data: **5 minutes**
- Manual configuration refresh: **Refresh Control Data**
- Successful writes: immediate control-data refresh

Typical configuration:

```text
Host: 192.168.1.101
Port: 502
Unit ID: 1
```

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

## Safety

Write support is intentionally restricted to the controls listed above. Network settings, firmware-update registers, calibration values, model selection, serial-number fields, FNDC reset registers, and other potentially destructive settings remain unexposed.

Changing Grid Use to OFF commands **Grid Drop**. It does not open a physical utility breaker; it commands the Radian to stop using the grid input and the house must then be supported by the inverter/PV/battery system as configured.

## Versioning

The project uses semantic-style progression. After the last patch digit reaches 9, the middle digit advances:

```text
Current Release -> 1.2.0
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

## GitHub Releases / HACS version display

The repository includes `.github/workflows/release.yaml`. When `manifest.json` is updated on `main`, the workflow creates a matching GitHub tag and Release if one does not already exist. This lets HACS/Home Assistant display semantic versions such as `1.2.0` instead of short commit hashes.

## Repository validation

Version 1.2.0 adds automated validation workflows:

- `.github/workflows/hacs.yaml` — HACS repository validation
- `.github/workflows/hassfest.yaml` — Home Assistant hassfest validation
- `.github/workflows/release.yaml` — automatic GitHub release/tag creation

These help prepare the repository for eventual submission to the default HACS store.

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
