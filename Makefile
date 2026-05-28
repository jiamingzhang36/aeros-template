.PHONY: all checks pipeline clean-logs

all: pipeline checks

pipeline:
	python3 code/99_make_all.py

checks:
	python3 checks/run_harness_checks.py

clean-logs:
	find outputs/logs -type f -name "*.log" -delete
