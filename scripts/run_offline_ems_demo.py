#!/usr/bin/env python3
"""Run the complete EMS chain without external services.

Pipeline:
digital twin telemetry -> controller bridge decision -> hardware adapter actions
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapters.hardware_command_adapter import AdapterConfig, HardwareCommandAdapter
from bridge.mqtt_controller_bridge import ControllerBridge
from simulator.digital_twin import simulate_step


def run_demo(steps: int, peak_pv_w: int, output: Path, seed: int = 42) -> dict[str, Any]:
    random.seed(seed)
    controller_bridge = ControllerBridge(min_command_interval_s=0)
    hardware_adapter = HardwareCommandAdapter(AdapterConfig())
    soc = 55.0
    modes: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    command_count = 0

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for step in range(steps):
            state, soc = simulate_step(step, soc, peak_pv_w)
            telemetry = asdict(state)
            command = controller_bridge.build_command(telemetry, now=float(step))
            if command:
                command["ts"] = step
            actions = hardware_adapter.build_actions(command) if command else []

            if command:
                command_count += 1
                modes[command["battery_mode"]] += 1
            for action in actions:
                action_counts[action.kind] += 1

            event = {
                "step": step,
                "telemetry": telemetry,
                "command": command,
                "actions": [asdict(action) for action in actions],
            }
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    return {
        "steps": steps,
        "commands": command_count,
        "modes": dict(modes),
        "actions": dict(action_counts),
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=144)
    parser.add_argument("--peak-pv-w", type=int, default=25000)
    parser.add_argument("--output", type=Path, default=Path("results/offline_ems_demo.jsonl"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    summary = run_demo(args.steps, args.peak_pv_w, args.output, args.seed)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
