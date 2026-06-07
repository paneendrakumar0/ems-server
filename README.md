# Smart Building EMS for PV, Battery, EV, and Flexible Loads

This repository contains the current implementation package for Professor Carlo Cecati's collaborative smart-building Energy Management System (EMS).

The project objective is to reduce grid energy absorption by coordinating:

- Sungrow SH20T PV inverter and battery telemetry.
- Sungrow AC11E EV wallbox telemetry/control path.
- ESP32-C6 embedded load controllers.
- KinCony/LC Tech relay boards used as PLC-style load hubs.
- Home Assistant as the supervisory console.
- MQTT for local device communication.
- InfluxDB/Grafana-ready research data logging.
- Forecasting and control logic for scheduling flexible loads.

## Current Contents

- `home_assistant/packages/sungrow_modbus.yaml` - Home Assistant Modbus TCP sensors for Sungrow inverter/wallbox telemetry.
- `home_assistant/packages/ems_mqtt_entities.yaml` - MQTT entities for demo telemetry and EMS controller decisions.
- `home_assistant/automations/bosch_solar_automation.yaml` - Solar-surplus appliance scheduling example through Home Connect.
- `home_assistant/dashboards/ems_supervisor_dashboard.yaml` - Supervisor dashboard for operator monitoring.
- `home_assistant/packages/research_datalogger.yaml` - InfluxDB logging configuration for research data.
- `esphome/kincony_kc868_a16.yaml` - Full 16-channel relay mapping for the KinCony KC868-A16.
- `firmware/esp32_c6_edge_node/` - ESP-IDF firmware skeleton for ESP32-C6 MQTT edge nodes.
- `simulator/digital_twin.py` - Lightweight local digital-twin simulator for PV, load, battery, EV, and relay topics.
- `controller/ems_controller.py` - EMS decision layer for flexible-load, EV, grid-import, and battery-reserve actions.
- `bridge/mqtt_controller_bridge.py` - Continuous MQTT bridge from telemetry to EMS command topics.
- `deployment/docker-compose.yml` - Local Mosquitto, InfluxDB, and Grafana support stack.
- `tools/run_closed_loop.py` - Full-day simulation runner that exports controller decisions to CSV.
- `tools/generate_report.py` - Markdown/SVG report generator for simulation results.
- `docs/` - Status, test plan, hardware questions, and email update draft.

## Integration Architecture

```text
Sungrow SH20T / AC11E
        |
        | Modbus TCP
        v
Home Assistant  <---- MQTT ----> ESP32-C6 edge load nodes
        |
        | Native API / MQTT
        v
KinCony KC868-A16 relay hub
        |
        v
Flexible loads, appliance relays, experiments

Home Assistant --> InfluxDB --> Grafana / CSV export

Telemetry --> EMS Controller --> MQTT commands --> Home Assistant / ESP32 / relays
```

## Setup Checklist

1. Replace all placeholder IPs, Wi-Fi credentials, MQTT credentials, and Home Assistant entity IDs.
2. Confirm Sungrow Modbus register addresses against the exact SH20T/AC11E firmware documentation.
3. Flash the KinCony board using ESPHome.
4. Build and flash the ESP32-C6 edge-node firmware with ESP-IDF.
5. Start Home Assistant, Mosquitto, InfluxDB, and Grafana.
6. Run `python3 simulator/digital_twin.py --dry-run` to inspect expected telemetry.
7. Run `python3 controller/ems_controller.py --input-json controller/sample_telemetry_solar_surplus.json --dry-run` to inspect a control decision.
8. Run a closed-loop local demo:

   ```bash
   python3 simulator/digital_twin.py --dry-run --steps 24 --interval 0 \
     | python3 controller/ems_controller.py --stdin-json-lines --dry-run
   ```

9. Connect real hardware one device at a time and compare telemetry with Sungrow/Home Connect apps.

## Dashboard

The Home Assistant supervisor dashboard is defined in:

```text
home_assistant/dashboards/ems_supervisor_dashboard.yaml
```

It displays PV/load/grid power, battery SoC, EV target power, EMS mode, flexible-load command, relay states, and research KPIs.

## Generate A Result CSV

```bash
python3 tools/run_closed_loop.py --steps 144 --output results/closed_loop_day.csv
python3 tools/generate_report.py --input results/closed_loop_day.csv
```

## Continuous MQTT Bridge

```bash
python3 bridge/mqtt_controller_bridge.py --broker 127.0.0.1
```

In another terminal, publish simulated telemetry:

```bash
python3 simulator/digital_twin.py --broker 127.0.0.1 --topic ems/digital_twin/state
```

## Immediate Pending Inputs From Professor Cecati

- Local IP address and Modbus unit/slave IDs for SH20T and AC11E.
- Confirmed Modbus register map for PV power, battery SoC, load power, grid power, and wallbox power.
- Exact KinCony/LC Tech board revision and relay-to-load assignments.
- ESP32-C6 custom load pinouts.
- Whether Bosch/Siemens devices are accessible through Home Connect in his account/region.
- Preferred MQTT broker credentials and Home Assistant network details.
