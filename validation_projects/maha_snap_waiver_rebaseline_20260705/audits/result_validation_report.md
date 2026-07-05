---
status: filled
task_id: T004_result_validation
gate: G6
claim_ceiling: measurement_descriptive
validated_at: 2026-07-05
---
# Result Validation Report

## Scope

This report validates the clean rebaseline wrapper's registered result artifacts, provenance records, claim registry, and reproducibility metadata. It does not validate restricted NielsenIQ microdata, rerun the canonical MAHA empirical pipeline, edit paper text, or change manuscript claims.

## Registered Result Families

| Result ID | Validation status | Claim boundary |
|---|---|---|
| R001 | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Policy-rule measurement boundary only; no behavioral, health, welfare, or causal effect. |
| R002 | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Public approval-risk diagnostic boundary only; no causal governor-party or federal-selection effect. |
| R003 | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Ex-ante NielsenIQ low-income-proxy exposure boundary only; no actual SNAP/EBT tender or post-policy response claim. |
| R004 | Present in `evidence/result_index.csv`; output file exists; provenance JSON exists and hashes the registered output. | Feasibility and explicit non-claim boundary only; no demand, welfare, health, or forecast claim. |

## Claim Registry Consistency

The claim registry contains three supported claims. Each claim links to registered result IDs and includes a boundary/limitation statement. The active claim types are measurement/descriptive and remain consistent with the method card's non-causal design.

## Reproducibility Metadata

Each populated result-index row includes `script_or_source` metadata. The source metadata records that R001--R004 are manual AEROS execution-lock registry artifacts derived from the method card, variable-construction memo, data contract, audit reports, and execution protocol. These are gate-control artifacts, not final empirical output tables.

## Publication-Facing Number Boundary

The clean wrapper currently has no authored `paper/*.md` or `paper/*.tex` draft with number-injection tokens. Therefore `check_number_registry.py` and `check_number_scan.py` validate the wrapper result/provenance layer rather than the canonical MAHA manuscript. The canonical manuscript remains in the source MAHA repository and is outside this wrapper validation task.

## Checks Run

- `python3 checks/check_number_registry.py` passed.
- `python3 checks/check_number_scan.py` passed as advisory with no raw manuscript numbers scanned.
- `python3 checks/check_output_reproducibility.py` passed after result-index `script_or_source` metadata was added.
- `python3 checks/check_provenance.py` passed for four indexed / four provenance records.
- `python3 checks/check_agent_run_report.py` passed.

## Known Limits

- This is a wrapper-level validation, not a final empirical rerun.
- It does not validate raw NielsenIQ microdata or regenerate source MAHA paper tables.
- It does not complete the robustness checklist; G5 only defined the robustness plan.
- It does not satisfy the MG human second-coder reliability requirement.
- It does not authorize `T010`, provider/model output collection, claim upgrades, poster changes, manuscript edits, or stronger causal/demand/welfare/health claims.

## Verdict

The clean wrapper's registered outputs, provenance records, claim registry, and reproducibility metadata are mutually consistent for the current AEROS G6 validation task under the existing measurement/descriptive/ex-ante exposure boundary.
