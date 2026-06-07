# Closed-loop EMS Simulation Report

## Summary

- Steps simulated: `144`
- Approximate PV energy: `173.29 kWh`
- Approximate load energy: `35.04 kWh`
- Approximate grid import: `0.02 kWh`
- Final battery SoC: `60.27%`
- Flexible-load commands: `{'hold': 82, 'enable': 62}`
- EV-charger commands: `{'hold': 83, 'enable': 61}`

## Controller Modes

- `normal`: 82 steps
- `self_consumption`: 1 steps
- `solar_surplus`: 61 steps

## Plot

![Closed-loop EMS plot](closed_loop_chart.svg)

## Interpretation

The rule-based EMS enables flexible load and EV charging during strong solar surplus, keeps commands neutral during ordinary operation, and remains structured for later hardware mapping through MQTT/Home Assistant. This report is generated from simulated data and should be repeated with real Sungrow/Home Assistant telemetry after Professor Cecati provides hardware details.
