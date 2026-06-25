---
status: filled
task_id: T004_result_validation
gate: G6
claim_ceiling: descriptive_or_associational
validated_at: 2026-06-15
---
# Result Validation Report

## Scope

This report validates the AEROS wrapper's registered result artifacts, provenance
records, claim registry, and reproducibility metadata. It does not validate
restricted NielsenIQ microdata, rerun the canonical MAHA empirical pipeline, or
change paper text/results.

## Registered Result Families

| Result ID | Validation status | Claim boundary |
| --- | --- | --- |
| R001 / R001_policy_rule_measurement | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Descriptive policy-rule measurement only; no behavioral/health/welfare effect. |
| R002 / R002_approval_risk_concentration | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Descriptive/associational approval-risk concentration only; no causal governor-party effect. |
| R003 / R003_nielsen_policy_rule_exposure | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Ex-ante aggregate NielsenIQ exposure only; no actual SNAP/EBT transaction or post-policy response claim. |
| R004 / R004_boundary_and_feasibility_diagnostics | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Boundary and feasibility diagnostics only; no demand, welfare, health, or forecast claim. |

## Claim Registry Consistency

The claim registry contains four supported claims. Each claim is linked to at
least one registered result family and has a boundary/limitation statement. The
active claim types are descriptive and associational, consistent with the method
card's non-causal design.

## Reproducibility Metadata

Each populated result-index row now includes `script_or_source = code/99_make_all.py`.
The registered path exists for every row. The current wrapper pipeline is
smoke-safe: it verifies the manifest and writes `outputs/logs/pipeline_smoke_report.json`
without touching raw data or exporting restricted NielsenIQ microdata.

## Publication-Facing Number Boundary

The wrapper currently has no authored `paper/*.md` or `paper/*.tex` draft with
number-injection tokens. Therefore `check_number_registry.py` and
`check_number_scan.py` validate the result registry/provenance layer rather than
the canonical MAHA manuscript. The canonical manuscript remains in the source
MAHA project and is outside this wrapper validation task.

## Known Limits

- This is a wrapper-level validation, not a final empirical rerun.
- Controlled NielsenIQ household-cluster CI remains waiting for controlled
  DuckDB/external-disk access.
- MG human second-coder reliability remains the largest submission-grade
  policy-coding blocker.
- G6 validation does not upgrade claims beyond descriptive/associational
  evidence.

## Verdict

The registered wrapper outputs, provenance records, claim registry, and
reproducibility metadata are mutually consistent for the current AEROS gate.
Proceed to the G6 decision packet only under the existing non-causal claim
boundary.
