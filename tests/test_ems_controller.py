import unittest

from controller.ems_controller import Command, EmsController, Telemetry


class EmsControllerTest(unittest.TestCase):
    def setUp(self):
        self.controller = EmsController()

    def test_protects_low_battery(self):
        decision = self.controller.decide(
            Telemetry(pv_power_w=9000, load_power_w=2000, battery_soc_pct=20)
        )

        self.assertEqual(Command.DISABLE, decision.flexible_load)
        self.assertEqual(Command.DISABLE, decision.ev_charger)
        self.assertEqual("protect_reserve", decision.battery_mode)

    def test_sheds_when_grid_import_is_high(self):
        decision = self.controller.decide(
            Telemetry(
                pv_power_w=1000,
                load_power_w=4500,
                battery_soc_pct=50,
                grid_power_w=800,
            )
        )

        self.assertEqual(Command.DISABLE, decision.flexible_load)
        self.assertEqual(Command.DISABLE, decision.ev_charger)
        self.assertEqual("reduce_grid_import", decision.battery_mode)

    def test_enables_ev_when_solar_surplus_is_strong(self):
        decision = self.controller.decide(
            Telemetry(pv_power_w=10000, load_power_w=2500, battery_soc_pct=72)
        )

        self.assertEqual(Command.ENABLE, decision.flexible_load)
        self.assertEqual(Command.ENABLE, decision.ev_charger)
        self.assertGreater(decision.target_ev_power_w, 0)

    def test_manual_override_holds(self):
        decision = self.controller.decide(
            Telemetry(
                pv_power_w=10000,
                load_power_w=2500,
                battery_soc_pct=72,
                manual_override=True,
            )
        )

        self.assertEqual(Command.HOLD, decision.flexible_load)
        self.assertEqual(Command.HOLD, decision.ev_charger)
        self.assertEqual("manual_override", decision.battery_mode)


if __name__ == "__main__":
    unittest.main()

