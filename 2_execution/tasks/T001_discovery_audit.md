# T001 Discovery Audit

## Objective

Review the discovery layer and identify whether the idea, literature scope, data inventory, gap memo, and feasibility memo are internally consistent.

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: yes, if recommendation changes project status

## Files to Inspect

- `0_discovery/`
- `1_design/method_card.md`
- `3_evidence/claim_registry.md`
- `6_decisions/decision_log.md`

## Files Allowed to Modify

- `5_audits/discovery_audit_report.md`
- `4_agent_runs/`

## Files Forbidden to Modify

- `2_execution/data/raw/`
- `1_design/protected_definitions.yml`

## Constraints

- Do not rewrite the idea note.
- Do not claim the literature gap is real unless closest literature has been reviewed.

## Expected Output

An audit report with:

- missing discovery files
- unclear research question
- unsupported gap claims
- missing data feasibility evidence
- recommended decision: pursue, revise, pause, or drop

## Checks to Run

- `2_execution/checks/check_agent_run_report.py`

## Done When

- Discovery audit report is written.
- Run report is complete.
- Human decision items are listed.
