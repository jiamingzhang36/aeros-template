---
task_class: standard
allowed_skills: []
---
# T004 Result Validation

## Objective

Validate that reported numbers, tables, figures, and paper language are consistent with outputs and protected definitions.

## Stop Rule

TBD

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if publication-facing text or claims change

- `AGENTS.md`
- `docs/protected_definitions.yml`
- `docs/language_constraints.md`
- `evidence/claim_registry.md`
- `evidence/result_index.csv`

## Files to Inspect

- `evidence/result_index.csv`
- `evidence/claim_registry.md`
- `outputs/`
- project paper or report files, if present

## Files Allowed to Modify

- `audits/result_validation_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`

## Constraints

- Do not edit the paper or results unless the task explicitly allows it.
- Do not change protected definitions.
- Do not reinterpret policy translation as forecast.
- Do not generalize to populations outside the protected sample.

## Expected Output

A result validation report with:

- numbers checked
- source output for each number
- mismatches found
- claim language issues
- unresolved questions requiring human judgment

## Checks to Run

- `checks/check_protected_definitions.py`
- `checks/check_number_registry.py`
- `checks/check_claim_registry.py`
- `checks/check_agent_run_report.py`

## Done When

- Result validation report is written.
- Each checked number is classified as matched, mismatched, unsupported, or not applicable.
- Run report is complete.
- Critic review is complete.
