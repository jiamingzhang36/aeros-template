---
task_class: standard
allowed_skills: []
---
# T005 Claim Audit

## Objective

Audit every major claim against the claim registry, evidence ledger, and method card.

## Stop Rule

TBD

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if claim status or wording changes

## Files to Inspect

- `evidence/claim_registry.md`
- `evidence/evidence_ledger.csv`
- `evidence/result_index.csv`
- `docs/method_card.md`
- `docs/language_constraints.md`

## Files Allowed to Modify

- `audits/claim_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`

## Constraints

- Do not strengthen claims.
- Do not add evidence that has not been inspected.
- Do not remove ambiguity flags without a reason.

## Expected Output

A claim audit report with:

- supported claims
- unsupported claims
- overclaims
- ambiguous claims
- recommended wording changes

## Checks to Run

- `checks/check_claim_registry.py`
- `checks/check_protected_definitions.py`
- `checks/check_agent_run_report.py`

## Done When

- Claim audit report is written.
- Unsupported and ambiguous claims are listed.
- Run report is complete.
- Critic review is complete.
