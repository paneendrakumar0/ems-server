import unittest

from adapters.hardware_command_adapter import AdapterConfig, HardwareCommandAdapter


class HardwareCommandAdapterTest(unittest.TestCase):
    def test_enable_command_builds_relay_and_ev_actions(self):
        adapter = HardwareCommandAdapter(
            AdapterConfig(
                flexible_load_mqtt_topic="edge/relay",
                kincony_relay_topics=("kincony/r1", "kincony/r2"),
                ev_limit_mqtt_topic="ev/limit",
            )
        )

        actions = adapter.build_actions(
            {
                "flexible_load": "enable",
                "ev_charger": "enable",
                "target_ev_power_w": 3200,
            }
        )

        self.assertEqual(4, len(actions))
        self.assertEqual("edge/relay", actions[0].target)
        self.assertEqual("ON", actions[0].payload)
        self.assertEqual("kincony/r1", actions[1].target)
        self.assertEqual("ON", actions[1].payload)
        self.assertEqual("ev/limit", actions[-1].target)
        self.assertEqual(3200, actions[-1].payload)

    def test_disable_command_sets_relays_off_and_ev_zero(self):
        adapter = HardwareCommandAdapter(
            AdapterConfig(
                flexible_load_mqtt_topic="edge/relay",
                kincony_relay_topics=("kincony/r1",),
                ev_limit_mqtt_topic="ev/limit",
            )
        )

        actions = adapter.build_actions(
            {
                "flexible_load": "disable",
                "ev_charger": "disable",
                "target_ev_power_w": 3600,
            }
        )

        payloads = [action.payload for action in actions]
        self.assertEqual(["OFF", "OFF", 0], payloads)

    def test_hold_command_builds_no_actions(self):
        adapter = HardwareCommandAdapter(AdapterConfig())

        actions = adapter.build_actions(
            {
                "flexible_load": "hold",
                "ev_charger": "hold",
                "target_ev_power_w": 0,
            }
        )

        self.assertEqual([], actions)

    def test_home_assistant_actions_are_optional(self):
        adapter = HardwareCommandAdapter(
            AdapterConfig(
                home_assistant_flexible_entity="switch.flexible_load",
                home_assistant_ev_entity="number.ev_limit",
                kincony_relay_topics=(),
            )
        )

        actions = adapter.build_actions(
            {
                "flexible_load": "enable",
                "ev_charger": "enable",
                "target_ev_power_w": 2400,
            }
        )

        ha_actions = [action for action in actions if action.kind == "home_assistant"]
        self.assertEqual(2, len(ha_actions))
        self.assertEqual("switch/turn_on", ha_actions[0].target)
        self.assertEqual("number/set_value", ha_actions[1].target)


if __name__ == "__main__":
    unittest.main()

