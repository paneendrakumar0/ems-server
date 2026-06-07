# Hardware Details Needed From Professor Cecati

Please confirm these items before physical deployment.

## Sungrow SH20T / Battery / AC11E

- Local IP address of the inverter.
- Whether Modbus TCP is enabled.
- Modbus port, usually `502`.
- Unit/slave ID for inverter and wallbox.
- Confirmed registers for:
  - Total PV power.
  - Battery SoC.
  - Battery charge/discharge power.
  - House load power.
  - Grid import/export power.
  - EV wallbox active power.
  - Wallbox charging status.
- Any required authentication or network restrictions.

## KinCony / Relay Boards

- Exact board model and revision.
- Whether the target board is KC868-A16 or another relay board.
- I2C pins and expander addresses.
- Relay-to-load mapping.
- Which loads are safe to switch directly and which require contactors/interlocks.
- Manual override requirements.

## ESP32-C6 Edge Nodes

- Board model and flash size.
- GPIO pinout for controlled devices.
- Sensor inputs, if any.
- Relay/driver circuit type.
- Local power supply details.
- Required Wi-Fi SSID/security mode.

## Appliances

- Bosch/Siemens model names.
- Whether Home Connect is available and enabled.
- Home Assistant entity IDs after integration.
- Which programs can be started remotely.

## Safety Rules

- Critical loads that must never be disconnected.
- Maximum allowed EV charging current.
- Battery minimum SoC reserve.
- Load priority order.
- Minimum runtime/offtime for motor/compressor loads.

