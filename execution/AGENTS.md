# Execution Agent Rules

## Purpose

The execution stage begins only after the discovery harness has produced a promotion decision.

The goal is to execute, reproduce, validate, audit, and package an empirical research project without changing the research design silently.

Execution-specific rules are layered on top of [AGENTS.md](../AGENTS.md) and [harness/common_rules.md](../harness/common_rules.md).

## Required Reading

Before execution tasks, read:

1. `AGENTS.md`
2. `discovery/PROMOTE_TO_HARNESS.md`
3. `execution/AGENTS.md`
4. `docs/method_card.md`
5. `docs/data_contract.yml`
6. `docs/protected_definitions.yml`
7. `docs/robustness_checklist.md`
8. `docs/language_constraints.md`
9. `evidence/claim_registry.md`
10. the relevant task file in `tasks/execution/`

## Stage Entry Rule

Do not treat the project as execution-ready unless `discovery/PROMOTE_TO_HARNESS.md` records a human decision to promote or the user explicitly overrides this gate.

If the gate is missing, incomplete, or says revise / pause / drop, write a blocker in the run report instead of starting execution.

## Protected Definitions

No additional protected-definition rule is introduced here; use root/common rules.
Execution work may only modify protected items through the documented approval process.

## Data Rules

- Derived data must be reproducible from code and documented inputs.
- Do not treat missing values as zero unless the data contract explicitly allows it.
- Do not drop observations for convenience without logging the rule and rationale.
- Do not use restricted data in outputs or reports unless access and sharing rules are documented.
- If a coverage, denominator, source, or variable gap appears, route it through `aeros data backfill --dry-run` before deciding whether to rerun, request approval, or write a receipt.
- Use `aeros data backfill --approve` for source-limited backfill approval and `aeros data backfill --receipt` for human-reviewed evidence; do not hand-edit queue status unless the CLI cannot express the decision.

## Code and Pipeline Rules

- Work from task files in `tasks/execution/`.
- Follow each task contract's `automation_class`, `evidence_receipt_required`, `receipt_path`, and `gate_status` before deciding whether to run, recover, or block it.
- Treat `harness/automation_policy.yml` as the canonical policy for automation classes and gate statuses.
- Prefer the project master workflow, currently `code/99_make_all.py` or `Makefile`.
- Preserve logs in `outputs/logs/` when running substantial commands.
- If code changes affect outputs, rerun relevant checks.
- Do not overwrite main outputs unless the task allows it.
- `approval_required` tasks, including LLM/API/source-refresh collection tasks, must not be run unless explicit human approval has cleared the blocked status.
- `receipt_audited` and `frozen_evidence` tasks require a receipt at `receipt_path` before they can be considered verified.

## Robustness Rules

- Run only robustness checks listed in `docs/robustness_checklist.md` or explicitly authorized by the task.
- Do not promote robustness results to the main result without human approval.
- Report null, ambiguous, and failed robustness checks honestly.

## Required Checks

Run relevant checks after execution work:

- `checks/check_no_raw_data_changes.py`
- `checks/check_data_contract.py`
- `checks/check_protected_definitions.py`
- `checks/check_pipeline_runs.py`
- `checks/check_output_reproducibility.py`
- `checks/check_paper_numbers.py`
- `checks/check_claim_registry.py`
- `checks/check_replication_package.py` when preparing release or replication materials

## Run Report

Every execution task must write an agent run report in `agent_runs/` with:

- task ID
- automation class
- gate status
- receipt path, if required
- files read
- files modified
- commands run
- outputs changed
- checks run
- protected definitions changed: yes / no
- claim changes: yes / no
- human decisions needed

## Critic and Human Gate

Critic review is required for:

- design changes
- code changes affecting main outputs
- robustness/specification changes
- publication-facing text changes
- claim changes
- replication package preparation

Human approval is required for:

- protected definition changes
- identification strategy changes
- primary outcome changes
- main specification changes
- final claim language
