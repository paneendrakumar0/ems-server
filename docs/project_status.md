# Project Status

Date: 2026-06-07

## Professor Cecati's Expected Outcome

Professor Cecati wants a smart-building EMS that coordinates local PV generation, battery storage, EV charging/V2G, and controllable household loads so that grid energy absorption is minimized.

The EMS should be practical, not only theoretical: it should connect to Home Assistant, ESP32 boards, relay hubs, Sungrow hardware, and commercial appliances where possible.

## What Has Been Built in This Package

- Organized Home Assistant configuration snippets for Sungrow telemetry, appliance automation, and research data logging.
- Complete ESPHome relay mapping for the KinCony KC868-A16 16-channel relay hub.
- ESP-IDF firmware skeleton for ESP32-C6 edge nodes with Wi-Fi, MQTT publishing, command subscription, and relay GPIO control.
- Digital-twin simulator that can publish PV, load, battery, EV, and grid telemetry to MQTT or run in dry-run mode.
- Rule-based EMS controller that converts telemetry into safe flexible-load and EV-charging decisions.
- Continuous stdin JSON-lines mode so the digital twin can feed the EMS controller as a local closed-loop demo.
- Local deployment support for Mosquitto, InfluxDB, and Grafana.
- Home Assistant supervisor dashboard for energy flow, storage, EV, controller decisions, relay states, and KPIs.
- Continuous MQTT controller bridge from telemetry topics to EMS command topics.
- Hardware command adapter for ESP32 relay, KinCony relay, EV target power, and optional Home Assistant services.
- Offline end-to-end demo from digital twin to controller bridge to hardware adapter actions.
- Makefile-based developer workflow.
- Home Assistant command-to-action automations with dry-run and manual safety gates.
- Documentation for hardware questions, test procedure, and a professor update email.

## Done

- Project structure created.
- Home Assistant supervisor path defined.
- MQTT topic convention defined.
- Sungrow Modbus integration drafted.
- KinCony relay integration drafted.
- Bosch/Home Connect solar-surplus automation drafted.
- InfluxDB research logging drafted.
- ESP32-C6 firmware baseline added.
- Digital twin baseline added.
- EMS controller layer added.
- Unit tests added for low battery, grid import, solar surplus, and manual override decisions.
- Local closed-loop simulation path added from digital twin telemetry to controller decisions.
- Full-day closed-loop CSV result workflow added.
- Markdown/SVG simulation report generation added.
- Home Assistant MQTT entity package added for digital-twin/controller state.
- Home Assistant dashboard YAML added for supervisor visualization.
- Continuous MQTT controller bridge added.
- Hardware command adapter added with dry-run support.
- Offline end-to-end demo added.
- Makefile and requirements file added.
- Home Assistant action automation package added.
- Local Docker Compose support added for the MQTT/data stack.

## Partially Done

- MPC/AI layer: workspace now contains a robust rule-based controller, but not yet the full SciPy/scikit-learn predictive optimizer.
- Sungrow integration: config exists, but register addresses and scaling must be verified against Professor Cecati's exact hardware/firmware.
- Bosch automation: logic exists, but Home Connect entity names and account capability must be verified.
- Relay control: full 16 relays are mapped, but physical load assignments are pending.

## Pending

- Test on actual ESP32-C6-WROOM-1 board.
- Test on actual KinCony/LC Tech relay board.
- Validate Sungrow Modbus values against the vendor/cloud/app readings.
- Connect real Home Assistant entities to the controller outputs.
- Add appliance-specific priority, minimum on/off time, and critical-load protection rules.
- Integrate a full predictive optimizer after real telemetry is available.

## Recommended Next Step

Next recommended engineering stage: add a formal project report with architecture, algorithms, safety design, test results, and hardware integration plan.
