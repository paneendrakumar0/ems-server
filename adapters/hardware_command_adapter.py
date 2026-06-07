#!/usr/bin/env python3
"""Translate high-level EMS decisions into hardware-specific actions."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdapterAction:
    kind: str
    target: str
    payload: dict[str, Any] | str | int | float | bool | None
    description: str


@dataclass(frozen=True)
class AdapterConfig:
    mqtt_broker: str = "127.0.0.1"
    mqtt_port: int = 1883
    command_topic: str = "ems/controller/command"
    status_topic: str = "ems/hardware_adapter/status"
    home_assistant_url: str | None = None
    home_assistant_token: str | None = None
    flexible_load_mqtt_topic: str = "ems/edge/esp32c6_load_01/cmd/relay"
    kincony_relay_topics: tuple[str, ...] = (
        "ems/kincony_a16/switch/kincony_relay_01/command",
    )
    ev_limit_mqtt_topic: str = "ems/ev_charger/cmd/limit_w"
    home_assistant_flexible_entity: str | None = None
    home_assistant_ev_entity: str | None = None


def load_adapter_config(path: Path) -> AdapterConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return AdapterConfig(
        mqtt_broker=data.get("mqtt_broker", AdapterConfig.mqtt_broker),
        mqtt_port=int(data.get("mqtt_port", AdapterConfig.mqtt_port)),
        command_topic=data.get("command_topic", AdapterConfig.command_topic),
        status_topic=data.get("status_topic", AdapterConfig.status_topic),
        home_assistant_url=data.get("home_assistant_url"),
        home_assistant_token=data.get("home_assistant_token"),
        flexible_load_mqtt_topic=data.get(
            "flexible_load_mqtt_topic",
            AdapterConfig.flexible_load_mqtt_topic,
        ),
        kincony_relay_topics=tuple(
            data.get("kincony_relay_topics", AdapterConfig.kincony_relay_topics)
        ),
        ev_limit_mqtt_topic=data.get("ev_limit_mqtt_topic", AdapterConfig.ev_limit_mqtt_topic),
        home_assistant_flexible_entity=data.get("home_assistant_flexible_entity"),
        home_assistant_ev_entity=data.get("home_assistant_ev_entity"),
    )


class HardwareCommandAdapter:
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    def build_actions(self, command: dict[str, Any]) -> list[AdapterAction]:
        actions: list[AdapterAction] = []
        flexible_load = command.get("flexible_load", "hold")
        ev_charger = command.get("ev_charger", "hold")
        target_ev_power_w = int(command.get("target_ev_power_w", 0) or 0)

        if flexible_load in {"enable", "disable"}:
            relay_payload = "ON" if flexible_load == "enable" else "OFF"
            actions.append(
                AdapterAction(
                    kind="mqtt",
                    target=self.config.flexible_load_mqtt_topic,
                    payload=relay_payload,
                    description=f"Set ESP32-C6 flexible-load relay {relay_payload}.",
                )
            )
            for topic in self.config.kincony_relay_topics:
                actions.append(
                    AdapterAction(
                        kind="mqtt",
                        target=topic,
                        payload=relay_payload,
                        description=f"Set KinCony relay topic {topic} {relay_payload}.",
                    )
                )

            if self.config.home_assistant_flexible_entity:
                service = "switch/turn_on" if flexible_load == "enable" else "switch/turn_off"
                actions.append(
                    AdapterAction(
                        kind="home_assistant",
                        target=service,
                        payload={"entity_id": self.config.home_assistant_flexible_entity},
                        description="Control Home Assistant flexible-load switch.",
                    )
                )

        if ev_charger in {"enable", "disable"}:
            ev_limit = target_ev_power_w if ev_charger == "enable" else 0
            actions.append(
                AdapterAction(
                    kind="mqtt",
                    target=self.config.ev_limit_mqtt_topic,
                    payload=ev_limit,
                    description=f"Set EV charger target limit to {ev_limit} W.",
                )
            )

            if self.config.home_assistant_ev_entity:
                service = "number/set_value"
                actions.append(
                    AdapterAction(
                        kind="home_assistant",
                        target=service,
                        payload={
                            "entity_id": self.config.home_assistant_ev_entity,
                            "value": ev_limit,
                        },
                        description="Set Home Assistant EV charging limit.",
                    )
                )

        return actions


def publish_mqtt(host: str, port: int, topic: str, payload: Any) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError("Install paho-mqtt to publish adapter actions.") from exc

    client = mqtt.Client()
    client.connect(host, port, 30)
    client.publish(topic, json.dumps(payload) if isinstance(payload, dict) else str(payload), qos=1)
    client.disconnect()


def call_home_assistant(base_url: str, token: str, service: str, payload: dict[str, Any]) -> None:
    domain, service_name = service.split("/", 1)
    url = f"{base_url.rstrip('/')}/api/services/{domain}/{service_name}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Home Assistant service call failed: {exc}") from exc


def execute_action(config: AdapterConfig, action: AdapterAction, dry_run: bool) -> None:
    if dry_run:
        print(json.dumps(action.__dict__, sort_keys=True))
        return

    if action.kind == "mqtt":
        publish_mqtt(config.mqtt_broker, config.mqtt_port, action.target, action.payload)
    elif action.kind == "home_assistant":
        if not config.home_assistant_url or not config.home_assistant_token:
            raise RuntimeError("Home Assistant URL/token required for Home Assistant actions.")
        if not isinstance(action.payload, dict):
            raise RuntimeError("Home Assistant action payload must be a JSON object.")
        call_home_assistant(config.home_assistant_url, config.home_assistant_token, action.target, action.payload)
    else:
        raise RuntimeError(f"Unknown adapter action kind: {action.kind}")


def adapt_once(command: dict[str, Any], config: AdapterConfig, dry_run: bool) -> list[AdapterAction]:
    adapter = HardwareCommandAdapter(config)
    actions = adapter.build_actions(command)
    for action in actions:
        execute_action(config, action, dry_run)
    return actions


def run_mqtt_adapter(config: AdapterConfig, dry_run: bool) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError("Install paho-mqtt to run the hardware adapter.") from exc

    adapter = HardwareCommandAdapter(config)

    def publish_status(client: mqtt.Client, status: str) -> None:
        client.publish(
            config.status_topic,
            json.dumps({"status": status, "ts": int(time.time())}),
            qos=1,
            retain=True,
        )

    def on_connect(client: mqtt.Client, userdata: object, flags: dict[str, Any], rc: int) -> None:
        if rc == 0:
            client.subscribe(config.command_topic, qos=1)
            publish_status(client, "online")
            print(f"hardware adapter subscribed {config.command_topic}")
        else:
            print(f"hardware adapter MQTT connection failed rc={rc}")

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        try:
            command = json.loads(msg.payload.decode("utf-8"))
            actions = adapter.build_actions(command)
            for action in actions:
                execute_action(config, action, dry_run)
        except Exception as exc:
            client.publish(
                config.status_topic,
                json.dumps({"status": "error", "error": str(exc), "ts": int(time.time())}),
                qos=1,
                retain=True,
            )
            print(f"hardware adapter error: {exc}")

    client = mqtt.Client(client_id="ems-hardware-adapter")
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set(
        config.status_topic,
        json.dumps({"status": "offline", "ts": int(time.time())}),
        qos=1,
        retain=True,
    )
    client.connect(config.mqtt_broker, config.mqtt_port, 60)
    client.loop_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/hardware_adapter.example.json"))
    parser.add_argument("--command-json", type=Path, help="Run once from a command JSON file.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_adapter_config(args.config)

    if args.command_json:
        command = json.loads(args.command_json.read_text(encoding="utf-8"))
        adapt_once(command, config, args.dry_run)
        return

    run_mqtt_adapter(config, args.dry_run)


if __name__ == "__main__":
    main()

