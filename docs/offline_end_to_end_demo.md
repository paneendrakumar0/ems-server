# Offline End-To-End EMS Demo

This demo runs the full software chain without Docker, MQTT, Home Assistant, or hardware.

## Pipeline

```text
digital twin -> controller bridge -> hardware command adapter -> JSONL trace
```

## Run

```bash
make offline-demo
```

Or directly:

```bash
python3 scripts/run_offline_ems_demo.py \
  --steps 144 \
  --output results/offline_ems_demo.jsonl
```

## Output

The demo writes:

```text
results/offline_ems_demo.jsonl
```

Each line contains:

- Simulated telemetry.
- EMS controller command.
- Hardware adapter actions that would be sent to ESP32, KinCony, EV charger, or Home Assistant.

## Why This Matters

This is the safest complete-system proof before touching Professor Cecati's hardware. It verifies that the internal interfaces are aligned:

- Telemetry field names match the controller.
- Controller payloads match the hardware adapter.
- Adapter dry-run actions are visible and reviewable.

