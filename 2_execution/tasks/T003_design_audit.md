# T003 Design Audit

## Objective

Audit whether the proposed empirical design can support the intended claim type.

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if design or claim type changes

## Files to Inspect

- `1_design/method_card.md`
- `1_design/protected_definitions.yml`
- `1_design/robustness_checklist.md`
- `1_design/language_constraints.md`
- `3_evidence/claim_registry.md`

## Files Allowed to Modify

- `5_audits/design_audit_report.md`
- `4_agent_runs/`

## Files Forbidden to Modify

- `2_execution/data/raw/`
- `1_design/protected_definitions.yml`

## Constraints

- Do not change `1_design/protected_definitions.yml`.
- Do not choose a preferred specification based on significance.
- Do not convert descriptive designs into causal language.

## Expected Output

A design audit report with:

- design summary
- identifying variation
- required assumptions
- threats to validity
- robustness priorities
- maximum supportable claim type

## Checks to Run

- `2_execution/checks/check_protected_definitions.py`
- `2_execution/checks/check_claim_registry.py`
- `2_execution/checks/check_agent_run_report.py`

## Done When

- Design audit report is written.
- Maximum supportable claim type is explicit.
- Run report is complete.
- Critic review is complete.
