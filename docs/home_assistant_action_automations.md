# Home Assistant Action Automations

This stage connects EMS command topics to Home Assistant actions in a controlled way.

## File

```text
home_assistant/packages/ems_action_automations.yaml
```

## Safety Gates

The package is safe by default:

- `input_boolean.ems_hardware_control_enabled` must be on.
- `input_boolean.ems_manual_override` must be off.
- `input_boolean.ems_action_dry_run` defaults to on.

With dry-run enabled, Home Assistant logs what it would do instead of switching hardware.

## Current Action Mapping

Flexible load:

```text
sensor.ems_flexible_load_command -> switch.kincony_relay_01
```

EV limit:

```text
sensor.ems_controller_ev_target -> input_number.ems_ev_target_limit_w
```

The EV action currently logs a placeholder when dry-run is off. Replace that placeholder with the Sungrow AC11E/Home Assistant wallbox service after Professor Cecati confirms the integration.

## Deployment

1. Add this package to Home Assistant packages.
2. Restart Home Assistant.
3. Keep `EMS Action Dry Run` on.
4. Turn on `EMS Hardware Control Enabled`.
5. Watch Logbook entries while controller commands arrive.
6. Replace placeholder entity IDs only after physical relay mapping is confirmed.

## Why This Matters

This closes the Home Assistant loop:

```text
EMS command MQTT sensors -> Home Assistant safety gates -> scripts -> relay/EV action
```

It prepares the project for physical testing without allowing accidental hardware switching.

