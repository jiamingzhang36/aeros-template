---
task_class: standard
work_lane: data   # data | literature | analysis | claim | writing | compliance | harness
allowed_skills:
  - data-inventory
  - data-quality-checker
  - data-merge-audit
recommended_skills:
  - data-inventory
required_skill_classes:
  - data_source
skill_obligations:
  - data_source
skill_waivers: []
---
# Task Template

## Task ID

T000

## Task Name

TBD

## Harness Mode

Worker required: yes

Critic required: yes / no

Human gate required: yes / no

Recommended work mode: branch_or_isolated_worktree

## Objective

TBD

## Stop Rule

TBD

- `AGENTS.md`
- `project_manifest.yml`
- `harness/permissions.yml`
- `harness/protocols/worker_protocol.md`
- `docs/protected_definitions.yml`
- `evidence/claim_registry.md`

## Files to Inspect

List files the agent must inspect.

## Files Allowed to Modify

List files the agent may modify.

## Files Forbidden to Modify

- `data/raw/`

## Constraints

- Do not modify `data/raw/`.
- Do not change protected definitions.
- Do not strengthen claims without evidence.

## Expected Output

TBD

## Checks to Run

TBD

## Done When

- Expected output exists.
- Required checks pass or failures are documented.
- Skill obligations are satisfied by `skills_used` or an explicit waiver/blocker.
- Agent run report is complete.
- Version-2 completion receipt exists and passes.
- Completion receipt records substantive allowed outputs, output hashes for files, check commands, exit codes, and `does_not_prove` boundaries.
- Critic report is complete when required.
- Human decision is logged when required.

## Human Approval Required For

- Protected definition changes
- Preferred specification changes
- Claim strengthening
- Publication-facing output changes

## Agent Run Report

Save a completed report to `agent_runs/`.
