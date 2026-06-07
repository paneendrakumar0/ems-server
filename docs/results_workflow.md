# Results Workflow

This stage generates a repeatable CSV result from the digital twin and EMS controller.

## Run A Simulated Day

```bash
python3 tools/run_closed_loop.py --steps 144 --output results/closed_loop_day.csv
```

The output CSV combines:

- PV/load/battery/EV/grid telemetry.
- Digital-twin relay recommendation.
- EMS controller command.
- Battery mode.
- Human-readable command reason.

## Why This Is Useful

Before hardware access, this gives a concrete artifact for discussion:

- When does the controller enable flexible loads?
- When does it prevent EV charging?
- How often does it protect the battery?
- Are grid-import decisions conservative enough?

The same workflow can later be repeated with real telemetry exported from Home Assistant/InfluxDB.

