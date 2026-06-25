.PHONY: smoke check describe

smoke:
	python3 code/99_make_all.py --mode smoke

describe:
	python3 code/99_make_all.py --mode describe

check:
	python3 checks/check_replication_package.py
	python3 checks/check_pipeline_runs.py
	python3 checks/check_output_reproducibility.py
	python3 checks/check_provenance.py
	python3 checks/check_artifact_manifest.py
