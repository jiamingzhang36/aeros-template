---
task_class: standard
allowed_skills: []
---
# T006 Referee Panel

## Task ID

T006

## Task Name

Referee Panel

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: yes, if proposed revisions affect research design or claim strength

Recommended work mode: read_only_or_report_only

## Objective

Simulate methods, domain, policy, and skeptical-editor objections after the core design, results, and claim audits exist.

## Stop Rule

TBD

- `AGENTS.md`
- `project_manifest.yml`
- `harness/permissions.yml`
- `docs/method_card.md`
- `docs/protected_definitions.yml`
- `docs/language_constraints.md`
- `evidence/claim_registry.md`
- `audits/`

## Files to Inspect

- `paper/`
- `docs/method_card.md`
- `docs/protected_definitions.yml`
- `evidence/claim_registry.md`
- `audits/`

## Files Allowed to Modify

- `audits/referee_panel_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `paper/`

## Constraints

- Do not rewrite the paper.
- Do not decide which referee objection should be accepted.
- Separate methods, domain, policy, and editor objections.

## Expected Output

A referee panel report with prioritized objections, evidence needed, and proposed response options.

## Checks to Run

- `checks/check_protected_definitions.py`
- `checks/check_agent_run_report.py`

## Done When

- Referee panel report exists.
- Major objections are grouped by reviewer role.
- Human decisions needed are listed.
- Run report is complete.

## Human Approval Required For

- Any design change
- Any claim-strength change
- Any manuscript edit
