# T004 Result Validation

## Objective

Validate that reported numbers, tables, figures, and paper language are consistent with outputs and protected definitions.

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if publication-facing text or claims change

## Required Reading

- `AGENTS.md`
- `1_design/protected_definitions.yml`
- `1_design/language_constraints.md`
- `3_evidence/claim_registry.md`
- `3_evidence/result_index.csv`

## Files to Inspect

- `3_evidence/result_index.csv`
- `3_evidence/claim_registry.md`
- `2_execution/outputs/`
- project paper or report files, if present

## Files Allowed to Modify

- `5_audits/result_validation_report.md`
- `4_agent_runs/`

## Files Forbidden to Modify

- `2_execution/data/raw/`
- `1_design/protected_definitions.yml`

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

- `2_execution/checks/check_protected_definitions.py`
- `2_execution/checks/check_paper_numbers.py`
- `2_execution/checks/check_claim_registry.py`
- `2_execution/checks/check_agent_run_report.py`

## Done When

- Result validation report is written.
- Each checked number is classified as matched, mismatched, unsupported, or not applicable.
- Run report is complete.
- Critic review is complete.
