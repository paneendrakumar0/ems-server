# Home Assistant EMS Dashboard

This stage adds a supervisor dashboard for the smart-building EMS.

## Files

- `home_assistant/packages/ems_mqtt_entities.yaml`
- `home_assistant/dashboards/ems_supervisor_dashboard.yaml`

## Install Package

Copy or mount `home_assistant/packages/ems_mqtt_entities.yaml` into the Home Assistant `packages` directory and ensure packages are enabled:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Restart Home Assistant after adding the package.

## Add Dashboard

In Home Assistant, create a new dashboard in YAML mode and paste the contents of:

```text
home_assistant/dashboards/ems_supervisor_dashboard.yaml
```

## Feed Demo Data

Start the MQTT support stack:

```bash
cd deployment
docker compose up -d
```

Publish digital-twin telemetry:

```bash
python3 simulator/digital_twin.py --broker 127.0.0.1 --steps 144 --interval 1
```

Publish controller decisions from sample telemetry:

```bash
python3 controller/ems_controller.py \
  --input-json controller/sample_telemetry_solar_surplus.json \
  --broker 127.0.0.1
```

## Real Hardware Transition

When Sungrow and KinCony hardware is available, keep the dashboard layout but replace the demo entities with real entities:

- `sensor.sungrow_pv_power`
- `sensor.sungrow_load_power`
- `sensor.sungrow_battery_soc`
- `sensor.sungrow_grid_power`
- KinCony relay switches from ESPHome

