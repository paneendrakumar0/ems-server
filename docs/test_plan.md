# Test Plan

## Phase 1: Offline Validation

1. Run the simulator in dry-run mode:

   ```bash
   python3 simulator/digital_twin.py --dry-run
   ```

2. Check that PV, load, battery SoC, EV power, and grid import/export values are plausible.
3. Review MQTT topic names and match them with Home Assistant entities.
4. Run the full offline demo:

   ```bash
   make offline-demo
   ```

5. Confirm `results/offline_ems_demo.jsonl` contains telemetry, commands, and adapter actions.

## Phase 2: Home Assistant Validation

1. Add package files from `home_assistant/packages/`.
2. Add automations from `home_assistant/automations/`.
3. Restart Home Assistant.
4. Confirm that placeholder values are replaced before enabling live control.
5. Verify entity creation and logs.
6. Add the dashboard YAML from `home_assistant/dashboards/ems_supervisor_dashboard.yaml`.
7. Confirm that demo MQTT entities and relay entities render without missing-card errors.
8. Add `home_assistant/packages/ems_action_automations.yaml`.
9. Keep `EMS Action Dry Run` enabled and verify action logs before touching hardware.

## Phase 3: Controller Validation

1. Run controller unit tests:

   ```bash
   python3 -m unittest discover -s tests
   ```

2. Inspect a solar-surplus decision:

   ```bash
   python3 controller/ems_controller.py --input-json controller/sample_telemetry_solar_surplus.json --dry-run
   ```

3. Inspect a grid-import decision:

   ```bash
   python3 controller/ems_controller.py --input-json controller/sample_telemetry_grid_import.json --dry-run
   ```

4. Publish commands to MQTT only after the dry-run output is correct.

5. Test the continuous MQTT bridge:

   ```bash
   python3 -m unittest discover -s tests
   python3 bridge/mqtt_controller_bridge.py --broker 127.0.0.1
   ```

6. Test hardware adapter dry-run:

   ```bash
   python3 adapters/hardware_command_adapter.py \
     --config config/hardware_adapter.example.json \
     --command-json config/sample_ems_command_enable.json \
     --dry-run
   ```

## Phase 4: Relay Hub Validation

1. Flash `esphome/kincony_kc868_a16.yaml` to the KinCony board.
2. Confirm all 16 relays appear in Home Assistant.
3. Switch each relay with no load connected first.
4. Map each relay to a physical load only after safe wiring is confirmed.

## Phase 5: ESP32-C6 Edge Node Validation

1. Configure Wi-Fi/MQTT settings in ESP-IDF menuconfig or source constants.
2. Build:

   ```bash
   idf.py set-target esp32c6
   idf.py build
   ```

3. Flash and monitor:

   ```bash
   idf.py flash monitor
   ```

4. Confirm telemetry appears on MQTT topic `ems/edge/<node_id>/telemetry`.
5. Send an override command to `ems/edge/<node_id>/cmd/relay`.

## Phase 6: Real Sungrow Telemetry

1. Enable Sungrow Modbus TCP.
2. Replace placeholder IP/unit/register details.
3. Compare Home Assistant values with Sungrow cloud/app readings.
4. Correct scale factors and register addresses.

## Phase 7: EMS Control

1. Enable monitoring-only mode first.
2. Enable relay commands for non-critical loads only.
3. Add priority and minimum-runtime rules.
4. Enable EV charging optimization after load telemetry is stable.
