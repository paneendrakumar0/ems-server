# Next Stage: EMS Controller Layer

This stage adds the local EMS decision layer between telemetry and actuation.

## Purpose

The controller converts measured or simulated states into conservative commands:

- Enable/disable flexible loads.
- Enable/disable EV charging.
- Protect battery reserve.
- Shed non-critical loads during grid import.
- Respect manual override.

## Dry-Run Examples

Solar-surplus decision:

```bash
python3 controller/ems_controller.py \
  --input-json controller/sample_telemetry_solar_surplus.json \
  --dry-run
```

Grid-import decision:

```bash
python3 controller/ems_controller.py \
  --input-json controller/sample_telemetry_grid_import.json \
  --dry-run
```

## MQTT Command Topic

Default command output:

```text
ems/controller/command
```

Example payload:

```json
{
  "flexible_load": "enable",
  "ev_charger": "enable",
  "battery_mode": "solar_surplus",
  "target_ev_power_w": 3600,
  "reason": "Strong solar surplus available; enable flexible loads and EV charging."
}
```

## Safety Philosophy

The current controller is intentionally conservative. It disables flexible load and EV charging when grid import is high or battery SoC is too low. Physical relay control should still be tested first with dummy loads before any real appliance or EV equipment is connected.

