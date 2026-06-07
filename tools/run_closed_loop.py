#!/usr/bin/env python3
"""Run a complete digital-twin + EMS-controller simulation and save CSV output."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from controller.ems_controller import EmsController, Telemetry, command_payload
from simulator.digital_twin import simulate_step


def run(steps: int, peak_pv_w: int, output: Path) -> dict[str, int]:
    controller = EmsController()
    soc = 55.0
    decisions: Counter[str] = Counter()

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "step",
            "hour",
            "pv_power_w",
            "load_power_w",
            "battery_soc_pct",
            "battery_power_w",
            "ev_power_w",
            "grid_power_w",
            "relay_recommendation",
            "flexible_load_command",
            "ev_charger_command",
            "battery_mode",
            "target_ev_power_w",
            "reason",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for step in range(steps):
            state, soc = simulate_step(step, soc, peak_pv_w)
            decision = controller.decide(
                telemetry=Telemetry(
                    pv_power_w=state.pv_power_w,
                    load_power_w=state.load_power_w,
                    battery_soc_pct=state.battery_soc_pct,
                    battery_power_w=state.battery_power_w,
                    ev_power_w=state.ev_power_w,
                    grid_power_w=state.grid_power_w,
                )
            )
            payload = command_payload(decision)
            decisions[payload["battery_mode"]] += 1

            writer.writerow(
                {
                    "step": state.step,
                    "hour": state.hour,
                    "pv_power_w": state.pv_power_w,
                    "load_power_w": state.load_power_w,
                    "battery_soc_pct": state.battery_soc_pct,
                    "battery_power_w": state.battery_power_w,
                    "ev_power_w": state.ev_power_w,
                    "grid_power_w": state.grid_power_w,
                    "relay_recommendation": state.relay_recommendation,
                    "flexible_load_command": payload["flexible_load"],
                    "ev_charger_command": payload["ev_charger"],
                    "battery_mode": payload["battery_mode"],
                    "target_ev_power_w": payload["target_ev_power_w"],
                    "reason": payload["reason"],
                }
            )

    return dict(decisions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=144)
    parser.add_argument("--peak-pv-w", type=int, default=25000)
    parser.add_argument("--output", type=Path, default=Path("results/closed_loop_day.csv"))
    args = parser.parse_args()

    summary = run(args.steps, args.peak_pv_w, args.output)
    print(json.dumps({"output": str(args.output), "decision_counts": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
