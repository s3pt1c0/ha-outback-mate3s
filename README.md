# OutBack MATE3s for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.7%2B-blue)
![Version](https://img.shields.io/badge/version-1.1.3-green)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Modbus](https://img.shields.io/badge/Modbus-TCP-red)

A native Home Assistant custom integration for monitoring **OutBack Power MATE3 / MATE3s systems directly over Modbus TCP**.

The integration communicates directly with the MATE3s using Home Assistant's modern shared Modbus connection API.

No external Raspberry Pi, MQTT bridge, REST/JSON polling, or additional daemon is required.

---

## Features

- Direct Modbus TCP communication with the MATE3s
- Uses Home Assistant's shared Modbus connection API
- Automatic SunSpec block discovery
- Native Home Assistant devices and sensors
- Local polling
- Read-only operation
- No cloud dependency
- No MQTT dependency
- No external scripts or computers required
- Home Assistant Energy Dashboard compatible sensors
- Local integration branding support

---

## Supported OutBack Devices

Currently tested with:

- **OutBack MATE3s**
- **OutBack Radian GS8048A**
- **OutBack FLEXnet DC (FNDC)**
- **OutBack FM100**
- **OutBack FM80**

The integration uses OutBack vendor-specific SunSpec / Modbus blocks exposed by the MATE3s.

### Currently Supported Real-Time Blocks

| Device | SunSpec DID |
|---|---:|
| Radian Split Phase Real-Time | `64115` |
| Charge Controller Real-Time | `64111` |
| FLEXnet-DC Real-Time | `64118` |

The integration discovers the actual register locations dynamically instead of relying on hard-coded absolute Modbus addresses.

This makes the integration more tolerant of firmware changes that alter the SunSpec block layout.

---

## Example System

The integration was initially developed and tested with the following system:

| HUB Port | Device |
|---:|---|
| 1 | OutBack Radian GS8048A |
| 2 | FM100 #1 |
| 3 | FM100 #2 |
| 4 | FM80 |
| 10 | FLEXnet-DC |

### FNDC Shunts

| Shunt | Assignment |
|---|---|
| A | Inverter |
| B | FM80 |
| C | 2 × FM100 |

---

## Available Sensors

### Radian

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

### Charge Controllers

For each detected charge controller:

- PV Voltage
- Battery Voltage
- Output Current
- Output Power
- Charger State
- Today Energy

Controllers are automatically identified by their OutBack HUB port.

Example:

- FM100 #1
- FM100 #2
- FM80

### Solar Totals

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

---

## Requirements

- Home Assistant **2026.7 or newer**
- MATE3 or MATE3s with Modbus TCP enabled
- Home Assistant must be able to reach the MATE3s over TCP port `502`


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

Example:

```text
MATE3s IP: 10.10.1.100
Modbus TCP Port: 502
Unit ID: 1