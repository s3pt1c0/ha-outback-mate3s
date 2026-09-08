# OutBack MATE3s for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-blue)
![Version](https://img.shields.io/badge/version-1.1.3-green)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Modbus](https://img.shields.io/badge/Modbus-TCP-red)

A native Home Assistant custom integration for monitoring **OutBack Power MATE3 / MATE3s systems directly over Modbus TCP**.

It communicates directly with the MATE3s using Home Assistant's shared Modbus connection API. No external Raspberry Pi, MQTT bridge, REST/JSON polling, or additional daemon is required.

## Features

- Direct Modbus TCP communication with the MATE3s
- Uses Home Assistant's shared Modbus connection API
- Automatic SunSpec block discovery
- Native Home Assistant sensors
- Local polling
- Read-only operation
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
| C | 2 x FM100 |

## OutBack SunSpec blocks

The integration discovers the actual register locations dynamically and reads the OutBack vendor extensions used by the MATE3s:

| Device | DID |
|---|---:|
| Radian Split Phase Real-Time | `64115` |
| Charge Controller Real-Time | `64111` |
| FLEXnet-DC Real-Time | `64118` |

No fixed absolute register addresses are required.

## Sensors

### Radian / AC

- Radian Mode
- AC Input State
- AC Frequency
- Radian Battery Voltage
- Radian Output Power
- Radian Charge Power

### Grid

- Grid L1 Voltage
- Grid L2 Voltage
- Grid Buy Power
- Grid Sell Power
- Grid L1 Buy Current
- Grid L2 Buy Current
- Grid L1 Sell Current
- Grid L2 Sell Current

### House

- House Power
- House L1 Current
- House L2 Current

**House L1/L2 Current is derived**, because OutBack DID 64115 exposes inverter output, charge, buy, and sell current for each leg but does not expose a dedicated load-current register. The integration uses this current balance per leg:

```text
House Current = Buy Current + Inverter Output Current - Sell Current - Charge Current
```

This is important in Pass Through mode, where inverter output current may be zero while the house is powered directly from the grid.

### Charge controllers

For every detected controller:

- PV Voltage
- Battery Voltage
- Output Current
- Power
- Charger State
- Today Energy

Controllers on the initially tested system are labeled by HUB port as FM100 #1, FM100 #2, and FM80.

### Solar totals

- Solar Total Power
- Solar Today Energy

### FLEXnet-DC

- FNDC SOC
- FNDC Battery Voltage
- FNDC Battery Current
- FNDC Net Power
- FNDC Days Since Full
- Shunt A Current
- Shunt B Current
- Shunt C Current

## Requirements

- Home Assistant **2026.9.0 or newer**
- MATE3 / MATE3s with Modbus TCP enabled
- TCP connectivity from Home Assistant to the MATE3s, normally port `502`

Typical configuration:

```text
Host: 172.16.35.252
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

The integration is currently **read-only**. It does not write configuration values to the MATE3s, Radian, charge controllers, or FLEXnet-DC.

## Versioning

Tracked releases start at **1.1.3**. Patch releases will continue sequentially:

```text
1.1.3 -> 1.1.4 -> 1.1.5 -> 1.1.6 -> ...
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

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
