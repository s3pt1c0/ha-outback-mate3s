# OutBack MATE3s

Home Assistant custom integration for direct OutBack MATE3s Modbus TCP telemetry and selected controls.

Current version: **1.1.9**

See the repository README for supported sensors, controls, installation and safety notes.


## Control-data refresh

Writable/configuration values are polled every 5 minutes. Use the **Refresh Control Data** button in Home Assistant to request an immediate settings refresh. Successful writes also trigger an immediate refresh.
