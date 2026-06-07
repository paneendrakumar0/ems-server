#!/usr/bin/env python3
"""Lightweight EMS digital twin for local MQTT/Home Assistant testing."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import dataclass, asdict


@dataclass
class EmsState:
    step: int
    hour: float
    pv_power_w: int
    load_power_w: int
    battery_soc_pct: float
    battery_power_w: int
    ev_power_w: int
    grid_power_w: int
    relay_recommendation: str


def solar_curve(hour: float, peak_w: int) -> int:
    daylight = math.sin(math.pi * (hour - 6.0) / 12.0)
    cloud_factor = random.uniform(0.82, 1.0)
    return max(0, int(peak_w * daylight * cloud_factor))


def load_curve(hour: float) -> int:
    base = 850
    morning = 1000 if 7 <= hour <= 9 else 0
    evening = 1800 if 18 <= hour <= 22 else 0
    random_load = random.randint(0, 450)
    return base + morning + evening + random_load


def simulate_step(step: int, soc: float, peak_pv_w: int) -> tuple[EmsState, float]:
    hour = (step % 144) / 6.0
    pv = solar_curve(hour, peak_pv_w)
    load = load_curve(hour)
    surplus = pv - load

    ev_power = 0
    relay = "hold"
    battery_power = 0

    if surplus > 3000 and soc > 45:
        ev_power = min(3600, surplus - 1200)
        relay = "enable_flexible_load"
    elif surplus < 0 and soc > 25:
        battery_power = max(-3000, surplus)
        relay = "shed_low_priority_load"
    elif soc <= 25:
        relay = "protect_battery"

    net_after_control = load + ev_power + battery_power - pv
    grid_power = max(0, int(net_after_control))

    if battery_power < 0:
        soc = max(10.0, soc + battery_power / 40000.0 * 100.0 / 6.0)
    elif surplus > ev_power and soc < 95:
        charge_w = min(3500, surplus - ev_power)
        battery_power = charge_w
        soc = min(95.0, soc + charge_w / 40000.0 * 100.0 / 6.0)

    state = EmsState(
        step=step,
        hour=round(hour, 2),
        pv_power_w=pv,
        load_power_w=load,
        battery_soc_pct=round(soc, 2),
        battery_power_w=int(battery_power),
        ev_power_w=int(ev_power),
        grid_power_w=grid_power,
        relay_recommendation=relay,
    )
    return state, soc


def publish_mqtt(host: str, topic: str, payload: dict) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError("Install paho-mqtt or run with --dry-run") from exc

    client = mqtt.Client()
    client.connect(host, 1883, 30)
    client.publish(topic, json.dumps(payload), qos=1, retain=False)
    client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--topic", default="ems/digital_twin/state")
    parser.add_argument("--steps", type=int, default=144)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--peak-pv-w", type=int, default=25000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    soc = 55.0
    for step in range(args.steps):
        state, soc = simulate_step(step, soc, args.peak_pv_w)
        payload = asdict(state)
        line = json.dumps(payload, sort_keys=True)

        if args.dry_run:
            print(line)
        else:
            publish_mqtt(args.broker, args.topic, payload)
            print(f"published {args.topic}: {line}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()

