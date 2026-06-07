# Hardware Command Adapters

This stage translates high-level EMS commands into hardware-specific actions.

## Data Flow

```text
EMS command topic -> hardware adapter -> ESP32 / KinCony / EV / Home Assistant actions
```

Default EMS command topic:

```text
ems/controller/command
```

## Dry-Run Example

Enable actions:

```bash
python3 adapters/hardware_command_adapter.py \
  --config config/hardware_adapter.example.json \
  --command-json config/sample_ems_command_enable.json \
  --dry-run
```

Disable actions:

```bash
python3 adapters/hardware_command_adapter.py \
  --config config/hardware_adapter.example.json \
  --command-json config/sample_ems_command_disable.json \
  --dry-run
```

Dry-run mode prints the exact planned MQTT/Home Assistant actions without touching hardware.

## Continuous Mode

After Mosquitto is running:

```bash
python3 adapters/hardware_command_adapter.py \
  --config config/hardware_adapter.example.json \
  --dry-run
```

Remove `--dry-run` only after relay mapping and EV charging limits are confirmed.

## Supported Action Types

- ESP32-C6 flexible-load relay topic.
- KinCony relay MQTT command topics.
- EV charger target power topic.
- Optional Home Assistant service calls for switch and number entities.

## Safety Notes

- Keep dry-run enabled until Professor Cecati confirms physical relay-to-load mapping.
- Do not connect compressor, induction, oven, or EV hardware until contactors/interlocks are checked.
- Use low-voltage dummy loads for the first relay test.
- Keep manual override available in Home Assistant.

