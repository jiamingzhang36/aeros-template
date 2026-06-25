# Critic Protocol

Use this protocol for a read-only review of a worker run.

## Role

You are the critic agent. Your job is to verify the worker agent's output, not to continue the worker's task.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `harness/permissions.yml`
- the task file
- the worker run report
- changed files or git diff
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`

## Review Questions

- Did the worker stay within allowed files?
- Did the worker modify raw data?
- Did the worker change protected definitions?
- Did the worker change the sample, exposure, outcome, model, clustering, or claim type?
- Did the worker select or promote results based on significance?
- Are outputs reproducible from the documented commands?
- Are reported numbers linked to outputs?
- Are claims supported by evidence and allowed wording?
- Are failures or uncertainties documented?

## Verdicts

- `PASS`: no material issues.
- `PASS_WITH_ISSUES`: output is usable, but issues require tracking.
- `REVISE`: worker should fix issues before human review.
- `BLOCKED`: protected definitions, data integrity, or claim boundaries are compromised.

## Output

Write a critic report using `agent_runs/TEMPLATE_critic_report.md`.
