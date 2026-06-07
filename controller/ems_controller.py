#!/usr/bin/env python3
"""Rule-based EMS controller for smart-building hardware validation.

The controller consumes telemetry from the digital twin or Home Assistant,
applies conservative safety rules, and emits actuator commands. It can run in
dry-run mode for local validation or publish decisions to MQTT.
"""

from __future__ import annotations

import argparse
import sys
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class Command(str, Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    HOLD = "hold"


@dataclass(frozen=True)
class ControllerConfig:
    min_battery_soc_pct: float = 25.0
    preferred_battery_soc_pct: float = 45.0
    solar_surplus_enable_w: int = 2500
    grid_import_shed_w: int = 500
    ev_charge_enable_surplus_w: int = 4200
    max_ev_power_w: int = 3600
    min_command_interval_s: int = 180


@dataclass(frozen=True)
class Telemetry:
    pv_power_w: float
    load_power_w: float
    battery_soc_pct: float
    battery_power_w: float = 0.0
    ev_power_w: float = 0.0
    grid_power_w: float = 0.0
    manual_override: bool = False

    @property
    def solar_surplus_w(self) -> float:
        return max(self.pv_power_w - self.load_power_w, 0.0)

    @property
    def grid_import_w(self) -> float:
        return max(self.grid_power_w, 0.0)


@dataclass(frozen=True)
class Decision:
    flexible_load: Command
    ev_charger: Command
    battery_mode: str
    target_ev_power_w: int
    reason: str


class EmsController:
    def __init__(self, config: ControllerConfig | None = None) -> None:
        self.config = config or ControllerConfig()

    def decide(self, telemetry: Telemetry) -> Decision:
        cfg = self.config

        if telemetry.manual_override:
            return Decision(
                flexible_load=Command.HOLD,
                ev_charger=Command.HOLD,
                battery_mode="manual_override",
                target_ev_power_w=0,
                reason="Manual override active; no automatic command issued.",
            )

        if telemetry.battery_soc_pct <= cfg.min_battery_soc_pct:
            return Decision(
                flexible_load=Command.DISABLE,
                ev_charger=Command.DISABLE,
                battery_mode="protect_reserve",
                target_ev_power_w=0,
                reason="Battery is at or below reserve threshold.",
            )

        if telemetry.grid_import_w >= cfg.grid_import_shed_w:
            return Decision(
                flexible_load=Command.DISABLE,
                ev_charger=Command.DISABLE,
                battery_mode="reduce_grid_import",
                target_ev_power_w=0,
                reason="Grid import is above limit; shed non-critical loads.",
            )

        if (
            telemetry.solar_surplus_w >= cfg.ev_charge_enable_surplus_w
            and telemetry.battery_soc_pct >= cfg.preferred_battery_soc_pct
        ):
            target_ev_power = min(
                cfg.max_ev_power_w,
                int(telemetry.solar_surplus_w - cfg.solar_surplus_enable_w),
            )
            return Decision(
                flexible_load=Command.ENABLE,
                ev_charger=Command.ENABLE,
                battery_mode="solar_surplus",
                target_ev_power_w=max(target_ev_power, 0),
                reason="Strong solar surplus available; enable flexible loads and EV charging.",
            )

        if (
            telemetry.solar_surplus_w >= cfg.solar_surplus_enable_w
            and telemetry.battery_soc_pct >= cfg.preferred_battery_soc_pct
        ):
            return Decision(
                flexible_load=Command.ENABLE,
                ev_charger=Command.HOLD,
                battery_mode="self_consumption",
                target_ev_power_w=0,
                reason="Solar surplus available; enable flexible building load.",
            )

        return Decision(
            flexible_load=Command.HOLD,
            ev_charger=Command.HOLD,
            battery_mode="normal",
            target_ev_power_w=0,
            reason="No control action required.",
        )


def telemetry_from_mapping(data: dict[str, Any]) -> Telemetry:
    return Telemetry(
        pv_power_w=float(data.get("pv_power_w", data.get("pv", 0))),
        load_power_w=float(data.get("load_power_w", data.get("load", 0))),
        battery_soc_pct=float(data.get("battery_soc_pct", data.get("soc", 0))),
        battery_power_w=float(data.get("battery_power_w", 0)),
        ev_power_w=float(data.get("ev_power_w", 0)),
        grid_power_w=float(data.get("grid_power_w", 0)),
        manual_override=bool(data.get("manual_override", False)),
    )


def command_payload(decision: Decision) -> dict[str, Any]:
    return {
        "flexible_load": decision.flexible_load.value,
        "ev_charger": decision.ev_charger.value,
        "battery_mode": decision.battery_mode,
        "target_ev_power_w": decision.target_ev_power_w,
        "reason": decision.reason,
        "ts": int(time.time()),
    }


def publish_mqtt(host: str, topic: str, payload: dict[str, Any]) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError("Install paho-mqtt to publish MQTT commands.") from exc

    client = mqtt.Client()
    client.connect(host, 1883, 30)
    client.publish(topic, json.dumps(payload), qos=1, retain=False)
    client.disconnect()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, help="Telemetry JSON file for one-shot decisions.")
    parser.add_argument("--stdin-json-lines", action="store_true", help="Read telemetry JSON objects from stdin.")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--command-topic", default="ems/controller/command")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    controller = EmsController()

    if args.stdin_json_lines:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            telemetry = telemetry_from_mapping(json.loads(line))
            decision = controller.decide(telemetry)
            payload = command_payload(decision)

            if args.dry_run:
                print(json.dumps(payload, sort_keys=True), flush=True)
            else:
                publish_mqtt(args.broker, args.command_topic, payload)
                print(f"published {args.command_topic}: {json.dumps(payload, sort_keys=True)}", flush=True)
        return

    if not args.input_json:
        raise SystemExit("--input-json or --stdin-json-lines is required")

    telemetry = telemetry_from_mapping(load_json(args.input_json))
    decision = controller.decide(telemetry)
    payload = command_payload(decision)

    if args.dry_run:
        print(json.dumps(payload, sort_keys=True))
        return

    publish_mqtt(args.broker, args.command_topic, payload)
    print(f"published {args.command_topic}: {json.dumps(payload, sort_keys=True)}")


if __name__ == "__main__":
    main()
