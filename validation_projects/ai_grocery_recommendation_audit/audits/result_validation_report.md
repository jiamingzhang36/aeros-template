# Result Validation Report

## Status

Pass for smoke result validation.

## Scope Reviewed

- `evidence/result_index.csv`
- `outputs/.provenance/R001.json`
- `outputs/tables/measurement_smoke_summary.csv`
- `evidence/claim_registry.md`
- `docs/method_card.md`
- `execution/protocol/main_execution_protocol.md`

## Registered Result Consistency

R001 is registered in `evidence/result_index.csv` and points to `outputs/tables/measurement_smoke_summary.csv`. A matching provenance record exists at `outputs/.provenance/R001.json`. The result is linked to C001.

## Provenance Consistency

The provenance record identifies the script source as `code/02_analysis/run_measurement_smoke.py`, records the output path, creation timestamp, and SHA-256 hash. Mechanical provenance checks pass.

## Claim Consistency

C001 is a descriptive draft claim linked to R001. It is not approved and is explicitly bounded as smoke validation only. This is consistent with the method card's measurement claim ceiling and the execution protocol's claim boundary.

## Publication-Facing Number Check

No paper draft currently uses R001 as a publication-facing empirical result. Therefore there are no manuscript number mismatches to resolve at this stage.

## Limitations

R001 is a toy smoke output and must not be interpreted as evidence about real AI grocery recommendations. No real model outputs, nutrition matches, or retailer prices have been validated.

## Decision

G6 can be approved for smoke-result validation only. Any future final empirical result must receive a new result ID, provenance record, result validation report, and claim audit before support language is allowed.
