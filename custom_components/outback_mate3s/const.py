"""Constants for the OutBack MATE3s integration."""

from datetime import timedelta

DOMAIN = "outback_mate3s"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"

DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

# Options flow: display unit for temperature sensors.
CONF_TEMPERATURE_UNIT = "temperature_unit"
TEMPERATURE_UNIT_AUTO = "auto"
TEMPERATURE_UNIT_CELSIUS = "celsius"
TEMPERATURE_UNIT_FAHRENHEIT = "fahrenheit"
TEMPERATURE_UNIT_OPTIONS = (
    TEMPERATURE_UNIT_AUTO,
    TEMPERATURE_UNIT_CELSIUS,
    TEMPERATURE_UNIT_FAHRENHEIT,
)
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_UNIT_AUTO
DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)
CONTROL_SCAN_INTERVAL = timedelta(minutes=5)

SUNSPEC_BASE = 40000
SUNSPEC_SIGNATURE = (0x5375, 0x6E53)
SUNSPEC_END_DID = 65535
# SunSpec "not implemented" markers. A fixed DID register (Start 1) returning
# one of these means the gateway had no data for that block at that instant.
SUNSPEC_UNAVAILABLE = (0x8000, 0xFFFF)
# Real-time polls a block may reuse its last-good data while its DID reads as
# unavailable. 6 x 10 s = about one minute before the poll is failed.
MAX_STALE_BLOCK_POLLS = 6
BLOCK_RETRY_DELAY = 0.5

DID_OUTBACK_GATEWAY = 64110
DID_CHARGE_CONTROLLER_REALTIME = 64111
DID_CHARGE_CONTROLLER_CONFIG = 64112
DID_RADIAN_SPLIT_REALTIME = 64115
# Monitoring only (experimental): single-phase Radian / FXR (Table 12) and
# FX / VFX (Table 13). Their configuration blocks (64116 / 64114) are not read.
DID_FX_REALTIME = 64113
DID_RADIAN_SINGLE_REALTIME = 64117
DID_FNDC_REALTIME = 64118
DID_OUTBACK_SYSTEM_CONTROL = 64120

