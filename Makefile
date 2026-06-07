.PHONY: test compile simulate report offline-demo adapter-dry-run

test:
	python3 -m unittest discover -s tests

compile:
	python3 -m py_compile \
		adapters/hardware_command_adapter.py \
		bridge/mqtt_controller_bridge.py \
		controller/ems_controller.py \
		simulator/digital_twin.py \
		tools/run_closed_loop.py \
		tools/generate_report.py \
		scripts/run_offline_ems_demo.py

simulate:
	python3 tools/run_closed_loop.py --steps 144 --output results/closed_loop_day.csv

report: simulate
	python3 tools/generate_report.py --input results/closed_loop_day.csv

offline-demo:
	python3 scripts/run_offline_ems_demo.py --steps 144 --output results/offline_ems_demo.jsonl

adapter-dry-run:
	python3 adapters/hardware_command_adapter.py \
		--config config/hardware_adapter.example.json \
		--command-json config/sample_ems_command_enable.json \
		--dry-run

