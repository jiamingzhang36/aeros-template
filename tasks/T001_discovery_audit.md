# T001 Discovery Audit

## Objective

Review the discovery layer and identify whether the idea, literature scope, data inventory, gap memo, and feasibility memo are internally consistent.

## Mainline Alignment Gate

- Project north star:
- Active mechanism / hypothesis:
- This task serves (feasibility / measurement / causal evidence / linkage probe / other):
- This task must not become:
- Stop rule:
- Side leads to park:
- Human escalation points: when uncertainty remains and requires owner confirmation.

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: yes, if recommendation changes project status

## Files to Inspect

- `discovery/`
- `docs/method_card.md`
- `evidence/claim_registry.md`
- `decisions/decision_log.md`

## Files Allowed to Modify

- `audits/discovery_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`

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

- `checks/check_agent_run_report.py`

## Done When

- Discovery audit report is written.
- Run report is complete.
- Human decision items are listed.
