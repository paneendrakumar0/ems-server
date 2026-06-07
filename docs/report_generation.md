# Report Generation

After running the closed-loop simulation, generate a professor-ready report:

```bash
python3 tools/run_closed_loop.py --steps 144 --output results/closed_loop_day.csv
python3 tools/generate_report.py --input results/closed_loop_day.csv
```

Outputs:

- `reports/closed_loop_report.md`
- `reports/closed_loop_chart.svg`

These files summarize the controller decisions and provide a simple plot of PV, load, grid import, and EV target power.

