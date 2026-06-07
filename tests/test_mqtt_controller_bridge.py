import unittest

from bridge.mqtt_controller_bridge import ControllerBridge
from controller.ems_controller import EmsController


class ControllerBridgeTest(unittest.TestCase):
    def test_publishes_first_decision(self):
        bridge = ControllerBridge(EmsController(), min_command_interval_s=180)

        payload = bridge.build_command(
            {
                "pv_power_w": 9000,
                "load_power_w": 2500,
                "battery_soc_pct": 70,
                "grid_power_w": 0,
            },
            now=1000,
        )

        self.assertIsNotNone(payload)
        self.assertEqual("enable", payload["flexible_load"])
        self.assertEqual("enable", payload["ev_charger"])

    def test_suppresses_repeated_unchanged_decision_inside_interval(self):
        bridge = ControllerBridge(EmsController(), min_command_interval_s=180)
        telemetry = {
            "pv_power_w": 9000,
            "load_power_w": 2500,
            "battery_soc_pct": 70,
            "grid_power_w": 0,
        }

        first = bridge.build_command(telemetry, now=1000)
        second = bridge.build_command(telemetry, now=1010)

        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_publishes_changed_decision_immediately(self):
        bridge = ControllerBridge(EmsController(), min_command_interval_s=180)

        bridge.build_command(
            {
                "pv_power_w": 9000,
                "load_power_w": 2500,
                "battery_soc_pct": 70,
                "grid_power_w": 0,
            },
            now=1000,
        )
        changed = bridge.build_command(
            {
                "pv_power_w": 500,
                "load_power_w": 5000,
                "battery_soc_pct": 70,
                "grid_power_w": 900,
            },
            now=1010,
        )

        self.assertIsNotNone(changed)
        self.assertEqual("disable", changed["flexible_load"])
        self.assertEqual("reduce_grid_import", changed["battery_mode"])

    def test_republishes_unchanged_decision_after_interval(self):
        bridge = ControllerBridge(EmsController(), min_command_interval_s=180)
        telemetry = {
            "pv_power_w": 9000,
            "load_power_w": 2500,
            "battery_soc_pct": 70,
            "grid_power_w": 0,
        }

        bridge.build_command(telemetry, now=1000)
        repeated = bridge.build_command(telemetry, now=1181)

        self.assertIsNotNone(repeated)
        self.assertEqual("solar_surplus", repeated["battery_mode"])


if __name__ == "__main__":
    unittest.main()

