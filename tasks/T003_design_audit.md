# T003 Design Audit

## Objective

Audit whether the proposed empirical design can support the intended claim type.

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

Critic required: yes

Human gate required: yes, if design or claim type changes

## Files to Inspect

- `docs/method_card.md`
- `docs/protected_definitions.yml`
- `docs/robustness_checklist.md`
- `docs/language_constraints.md`
- `evidence/claim_registry.md`

## Files Allowed to Modify

- `audits/design_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`

## Constraints

- Do not change `docs/protected_definitions.yml`.
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

- `checks/check_protected_definitions.py`
- `checks/check_claim_registry.py`
- `checks/check_agent_run_report.py`

## Done When

- Design audit report is written.
- Maximum supportable claim type is explicit.
- Run report is complete.
- Critic review is complete.
