# Continuous MQTT Controller Bridge

This stage turns the EMS decision logic into a continuously running service.

## Data Flow

```text
telemetry MQTT topic -> bridge -> EMS controller -> command MQTT topic
```

Default topics:

- Telemetry input: `ems/digital_twin/state`
- Command output: `ems/controller/command`
- Bridge status: `ems/controller/status`

## Run Mosquitto

```bash
cd deployment
docker compose up -d mosquitto
```

## Run The Bridge

```bash
python3 bridge/mqtt_controller_bridge.py \
  --broker 127.0.0.1 \
  --telemetry-topic ems/digital_twin/state \
  --command-topic ems/controller/command
```

## Feed Digital Twin Telemetry

In another terminal:

```bash
python3 simulator/digital_twin.py \
  --broker 127.0.0.1 \
  --topic ems/digital_twin/state \
  --steps 144 \
  --interval 1
```

## Expected Result

The bridge publishes JSON command payloads such as:

```json
{
  "flexible_load": "enable",
  "ev_charger": "enable",
  "battery_mode": "solar_surplus",
  "target_ev_power_w": 3600,
  "reason": "Strong solar surplus available; enable flexible loads and EV charging."
}
```

Home Assistant can consume these through `home_assistant/packages/ems_mqtt_entities.yaml`, and ESP32/KinCony actions can later subscribe to the same command topic.

