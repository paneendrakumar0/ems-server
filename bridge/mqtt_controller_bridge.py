#!/usr/bin/env python3
"""Continuous MQTT bridge for the EMS controller.

Subscribes to telemetry JSON, applies the EMS controller, and publishes command
JSON for Home Assistant, ESP32 edge nodes, or relay hubs.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any

from controller.ems_controller import (
    ControllerConfig,
    EmsController,
    Telemetry,
    command_payload,
    telemetry_from_mapping,
)


@dataclass
class BridgeConfig:
    broker: str = "127.0.0.1"
    port: int = 1883
    telemetry_topic: str = "ems/digital_twin/state"
    command_topic: str = "ems/controller/command"
    status_topic: str = "ems/controller/status"
    client_id: str = "ems-controller-bridge"
    publish_retain: bool = False
    qos: int = 1


class ControllerBridge:
    def __init__(
        self,
        controller: EmsController | None = None,
        min_command_interval_s: int | None = None,
    ) -> None:
        self.controller = controller or EmsController()
        self.min_command_interval_s = (
            min_command_interval_s
            if min_command_interval_s is not None
            else self.controller.config.min_command_interval_s
        )
        self.last_payload: dict[str, Any] | None = None
        self.last_publish_ts = 0.0

    def build_command(self, telemetry_data: dict[str, Any], now: float | None = None) -> dict[str, Any] | None:
        now = time.time() if now is None else now
        telemetry: Telemetry = telemetry_from_mapping(telemetry_data)
        decision = self.controller.decide(telemetry)
        payload = command_payload(decision)

        comparable_payload = dict(payload)
        comparable_payload.pop("ts", None)

        comparable_last = dict(self.last_payload or {})
        comparable_last.pop("ts", None)

        changed = comparable_payload != comparable_last
        interval_elapsed = (now - self.last_publish_ts) >= self.min_command_interval_s

        if not changed and not interval_elapsed:
            return None

        self.last_payload = payload
        self.last_publish_ts = now
        return payload


def run_mqtt_bridge(config: BridgeConfig, controller_config: ControllerConfig) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError("Install paho-mqtt to run the MQTT bridge.") from exc

    bridge = ControllerBridge(EmsController(controller_config))

    def publish_status(client: mqtt.Client, status: str) -> None:
        client.publish(
            config.status_topic,
            json.dumps({"status": status, "ts": int(time.time())}),
            qos=config.qos,
            retain=True,
        )

    def on_connect(client: mqtt.Client, userdata: object, flags: dict[str, Any], rc: int) -> None:
        if rc == 0:
            client.subscribe(config.telemetry_topic, qos=config.qos)
            publish_status(client, "online")
            print(f"subscribed {config.telemetry_topic}")
        else:
            print(f"MQTT connection failed rc={rc}")

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        try:
            telemetry_data = json.loads(msg.payload.decode("utf-8"))
            payload = bridge.build_command(telemetry_data)
        except Exception as exc:
            error_payload = {"status": "error", "error": str(exc), "ts": int(time.time())}
            client.publish(config.status_topic, json.dumps(error_payload), qos=config.qos, retain=True)
            print(f"bridge error: {exc}")
            return

        if payload is None:
            return

        client.publish(
            config.command_topic,
            json.dumps(payload),
            qos=config.qos,
            retain=config.publish_retain,
        )
        print(f"published {config.command_topic}: {json.dumps(payload, sort_keys=True)}")

    client = mqtt.Client(client_id=config.client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set(
        config.status_topic,
        json.dumps({"status": "offline", "ts": int(time.time())}),
        qos=config.qos,
        retain=True,
    )
    client.connect(config.broker, config.port, 60)
    client.loop_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--telemetry-topic", default="ems/digital_twin/state")
    parser.add_argument("--command-topic", default="ems/controller/command")
    parser.add_argument("--status-topic", default="ems/controller/status")
    parser.add_argument("--min-command-interval-s", type=int, default=180)
    parser.add_argument("--retain", action="store_true")
    args = parser.parse_args()

    bridge_config = BridgeConfig(
        broker=args.broker,
        port=args.port,
        telemetry_topic=args.telemetry_topic,
        command_topic=args.command_topic,
        status_topic=args.status_topic,
        publish_retain=args.retain,
    )
    controller_config = ControllerConfig(min_command_interval_s=args.min_command_interval_s)
    run_mqtt_bridge(bridge_config, controller_config)


if __name__ == "__main__":
    main()

