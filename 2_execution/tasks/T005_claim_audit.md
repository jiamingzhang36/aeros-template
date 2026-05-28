# T005 Claim Audit

## Objective

Audit every major claim against the claim registry, evidence ledger, and method card.

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if claim status or wording changes

## Files to Inspect

- `3_evidence/claim_registry.md`
- `3_evidence/evidence_ledger.csv`
- `3_evidence/result_index.csv`
- `1_design/method_card.md`
- `1_design/language_constraints.md`

## Files Allowed to Modify

- `5_audits/claim_audit_report.md`
- `4_agent_runs/`

## Files Forbidden to Modify

- `2_execution/data/raw/`
- `1_design/protected_definitions.yml`

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

- `2_execution/checks/check_claim_registry.py`
- `2_execution/checks/check_protected_definitions.py`
- `2_execution/checks/check_agent_run_report.py`

## Done When

- Claim audit report is written.
- Unsupported and ambiguous claims are listed.
- Run report is complete.
- Critic review is complete.
