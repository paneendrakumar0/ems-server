#!/usr/bin/env python3
"""Generate a lightweight Markdown/SVG report from closed-loop EMS CSV output."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def make_svg(rows: list[dict[str, str]], output: Path) -> None:
    width = 960
    height = 420
    pad_l = 60
    pad_r = 24
    pad_t = 24
    pad_b = 52
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    hours = [as_float(row, "hour") for row in rows]
    series = {
        "PV": ("pv_power_w", "#f5a623"),
        "Load": ("load_power_w", "#2f6fed"),
        "Grid": ("grid_power_w", "#d94f45"),
        "EV target": ("target_ev_power_w", "#1f9d55"),
    }
    max_y = max(max(as_float(row, key) for row in rows) for key, _ in series.values())
    max_y = max(max_y, 1.0)

    def x_for(hour: float) -> float:
        return pad_l + (hour / 24.0) * chart_w

    def y_for(value: float) -> float:
        return pad_t + chart_h - (value / max_y) * chart_h

    lines = []
    for label, (key, color) in series.items():
        pts = [(x_for(hour), y_for(as_float(row, key))) for hour, row in zip(hours, rows)]
        lines.append(
            f'<polyline points="{polyline(pts)}" fill="none" stroke="{color}" '
            f'stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" />'
        )

    legend = []
    for idx, (label, (_, color)) in enumerate(series.items()):
        x = pad_l + idx * 145
        y = height - 20
        legend.append(f'<rect x="{x}" y="{y - 10}" width="14" height="4" fill="{color}" />')
        legend.append(f'<text x="{x + 20}" y="{y - 5}" font-size="13">{label}</text>')

    x_ticks = []
    for hour in range(0, 25, 6):
        x = x_for(hour)
        x_ticks.append(f'<line x1="{x}" y1="{pad_t}" x2="{x}" y2="{pad_t + chart_h}" stroke="#eeeeee" />')
        x_ticks.append(f'<text x="{x - 10}" y="{height - 34}" font-size="12">{hour}h</text>')

    y_ticks = []
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        value = max_y * frac
        y = y_for(value)
        y_ticks.append(f'<line x1="{pad_l}" y1="{y}" x2="{pad_l + chart_w}" y2="{y}" stroke="#eeeeee" />')
        y_ticks.append(f'<text x="8" y="{y + 4}" font-size="12">{int(value)} W</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="{pad_l}" y="18" font-size="16" font-weight="700">Closed-loop EMS simulation</text>
  {''.join(x_ticks)}
  {''.join(y_ticks)}
  <rect x="{pad_l}" y="{pad_t}" width="{chart_w}" height="{chart_h}" fill="none" stroke="#222222" />
  {''.join(lines)}
  {''.join(legend)}
</svg>
"""
    output.write_text(svg, encoding="utf-8")


def write_markdown(rows: list[dict[str, str]], chart_path: Path, output: Path) -> None:
    modes = Counter(row["battery_mode"] for row in rows)
    flexible = Counter(row["flexible_load_command"] for row in rows)
    ev = Counter(row["ev_charger_command"] for row in rows)

    total_pv_kwh = sum(as_float(row, "pv_power_w") for row in rows) / 6.0 / 1000.0
    total_load_kwh = sum(as_float(row, "load_power_w") for row in rows) / 6.0 / 1000.0
    total_grid_kwh = sum(as_float(row, "grid_power_w") for row in rows) / 6.0 / 1000.0
    final_soc = as_float(rows[-1], "battery_soc_pct")

    rel_chart = chart_path.relative_to(output.parent)
    mode_lines = "\n".join(f"- `{key}`: {value} steps" for key, value in sorted(modes.items()))

    md = f"""# Closed-loop EMS Simulation Report

## Summary

- Steps simulated: `{len(rows)}`
- Approximate PV energy: `{total_pv_kwh:.2f} kWh`
- Approximate load energy: `{total_load_kwh:.2f} kWh`
- Approximate grid import: `{total_grid_kwh:.2f} kWh`
- Final battery SoC: `{final_soc:.2f}%`
- Flexible-load commands: `{dict(flexible)}`
- EV-charger commands: `{dict(ev)}`

## Controller Modes

{mode_lines}

## Plot

![Closed-loop EMS plot]({rel_chart})

## Interpretation

The rule-based EMS enables flexible load and EV charging during strong solar surplus, keeps commands neutral during ordinary operation, and remains structured for later hardware mapping through MQTT/Home Assistant. This report is generated from simulated data and should be repeated with real Sungrow/Home Assistant telemetry after hardware configuration details are available.
"""
    output.write_text(md, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/closed_loop_day.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/closed_loop_report.md"))
    parser.add_argument("--chart", type=Path, default=Path("reports/closed_loop_chart.svg"))
    args = parser.parse_args()

    rows = read_rows(args.input)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.chart.parent.mkdir(parents=True, exist_ok=True)
    make_svg(rows, args.chart)
    write_markdown(rows, args.chart, args.report)
    print(f"wrote {args.report} and {args.chart}")


if __name__ == "__main__":
    main()
