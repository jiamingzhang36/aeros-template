# Manual AEROS Task Prompt

AEROS_AGENT_PROVIDER=manual wrote this prompt instead of calling an agent.

Fill the allowed output files, then run `aeros check <task-contract>`.

```text
You are an AEROS worker agent executing task T007_replication_package (stage: execution).

## Goal
Check whether the project can be packaged for replication. Audit environment, data access rules, pipeline entry points, registered outputs, provenance, and unresolved release blockers.

## You may write ONLY these files
- audits/replication_package_report.md
- agent_runs/

## Forbidden
- Do not expose restricted data.
- Do not edit publication-facing files unless explicitly instructed.
- Do not change protected definitions or data-sharing rules.

## Inputs (read-only context)
--- README_replication.md ---
# Replication Package README

## Project

TBD

## Overview

This replication package should explain how to rebuild the analysis from protected raw data or public sources through final outputs.

## Computational Requirements

Operating system:

Software:

Package manager:

Estimated runtime:

## Data Availability

| Data ID | Public? | Access instructions | Restrictions |
|---|---|---|---|
| D001 | TBD | TBD | TBD |

## Reproduction Steps

1. Confirm access to required data.
2. Review `docs/protected_definitions.yml`.
3. Run the project master script or project-specific workflow.
4. Verify outputs using checks in `checks/`.
5. Compare manuscript numbers against `evidence/result_index.csv`.

## Master Script

`code/99_make_all.py` is the default placeholder. Replace or wrap it with the project-specific master workflow.

## Expected Outputs

TBD

## Known Limitations

TBD


--- Makefile ---
.PHONY: all checks pipeline clean-logs lock-definitions index-agent-runs promote-discovery-execution

all: pipeline checks

pipeline:
	python3 code/99_make_all.py

checks:
	python3 checks/build_agent_runs_index.py
	python3 checks/run_harness_checks.py

index-agent-runs:
	python3 checks/build_agent_runs_index.py

lock-definitions:
	python3 - <<'PY'
from pathlib import Path

path = Path("docs/protected_definitions.yml")
text = path.read_text(encoding="utf-8")
text = text.replace('status: "draft"', 'status: "locked"')
text = text.replace("status: 'draft'", "status: 'locked'")
path.write_text(text, encoding="utf-8")
print("Updated docs/protected_definitions.yml: status -> locked")
PY

clean-logs:
	find outputs/logs -type f -name "*.log" -delete

promote-discovery-execution:
	python3 checks/create_promotion_tag.py --from-stage discovery --to-stage execution


--- environment.yml ---
name: aeros-project
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pyyaml=6.0.2
  - pip
  - pip:
      - -r requirements-min.txt


--- requirements.txt ---
# AEROS harness/runtime requirements
PyYAML==6.0.2


--- code/ (DIRECTORY) ---
- code/.gitkeep
- code/00_setup/.gitkeep
- code/00_setup/README.md
- code/01_ingest/.gitkeep
- code/01_ingest/README.md
- code/01_ingest/fetch_public_data.py
- code/01_ingest/probe_data_diagnostics.py
- code/02_analysis/analyze_pilot_outputs.py
- code/02_analysis/run_measurement_smoke.py
- code/02_clean/.gitkeep
- code/02_clean/README.md
- code/03_construct/.gitkeep
- code/03_construct/README.md
- code/04_analysis/.gitkeep
- code/04_analysis/README.md
- code/05_robustness/.gitkeep
- code/05_robustness/README.md
- code/06_tables/.gitkeep
- code/06_tables/README.md
- code/06_tables/TEMPLATE_make_table.py
- code/07_figures/.gitkeep
- code/07_figures/README.md
- code/07_figures/TEMPLATE_make_figure.py
- code/99_make_all.py
- code/__pycache__/99_make_all.cpython-310.pyc
- code/utils/provenance.py

--- data/README_data.md ---
# Data README

## Data Policy

Raw data are protected. Agents and scripts should not modify files in `data/raw/`.

## Directories

- `raw/`: original source data, never modified in place
- `intermediate/`: temporary derived files
- `parquet/`: columnar data for larger or queryable derived datasets
- `clean/`: analysis-ready files
- `snapshots/`: dated data snapshots for review, release, or reproducibility checkpoints

## Source Log

| Data ID | Source | Date accessed | Local path | License / restriction | Notes |
|---|---|---|---|---|---|
| D001 | TBD | TBD | TBD | TBD | TBD |

## Rebuild Instructions

TBD


--- evidence/result_index.csv ---
result_id,output_type,path,script_or_source,description,created_date,linked_claims,notes
R001,table,outputs/tables/measurement_smoke_summary.csv,code/02_analysis/run_measurement_smoke.py,Offline smoke summary for AI grocery recommendation measurement audit pipeline.,2026-06-01,C001,Toy validation output; not final empirical evidence.
R002,table,outputs/tables/pilot_measurement_summary.csv,code/02_analysis/analyze_pilot_outputs.py,Pilot measurement summary for current Codex-session AI grocery recommendation outputs.,2026-06-01,C002,Pilot only; current Codex session; not platform-wide evidence.
R003,table,outputs/tables/pilot_robustness_summary.csv,code/02_analysis/analyze_pilot_outputs.py,Prompt-variant robustness summary for pilot current Codex-session outputs.,2026-06-01,C002,Pilot robustness only; not final robustness suite.


--- outputs/.provenance/ (DIRECTORY) ---
- outputs/.provenance/R001.json
- outputs/.provenance/R002.json
- outputs/.provenance/R003.json

--- paper/ (DIRECTORY) ---
- paper/.gitkeep
- paper/draft.md

When done, the file(s) above must pass the AEROS checks. Do not explain; just produce conformant files.
```
