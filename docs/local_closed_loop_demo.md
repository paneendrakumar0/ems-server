# Local Closed-Loop Demo

This demo connects the digital twin to the EMS controller without hardware.

## Run

```bash
python3 simulator/digital_twin.py --dry-run --steps 24 --interval 0 \
  | python3 controller/ems_controller.py --stdin-json-lines --dry-run
```

The first process generates simulated PV, load, battery, EV, and grid telemetry. The second process converts each telemetry sample into an EMS command decision.

## What To Look For

- At night or during deficit, the controller should hold or shed non-critical loads.
- During high grid import, it should disable flexible load and EV charging.
- During strong solar surplus with healthy battery SoC, it should enable flexible loads and EV charging.
- If `manual_override` is present and true in telemetry, it should hold automatic commands.

## Why This Matters

This provides a local proof that the project is not only a dashboard/configuration package. It now has a closed-loop control path:

```text
telemetry -> EMS decision -> command payload
```

The same command payload can later be published to MQTT and mapped to Home Assistant, ESP32-C6 edge nodes, or KinCony relay switches.

