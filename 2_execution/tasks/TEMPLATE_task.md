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

## Required Reading

- `AGENTS.md`
- `AEROS_MANIFEST.yml`
- `harness/permissions.yml`
- `harness/protocols/worker_protocol.md`
- `1_design/protected_definitions.yml`
- `3_evidence/claim_registry.md`

## Files to Inspect

List files the agent must inspect.

## Files Allowed to Modify

List files the agent may modify.

## Files Forbidden to Modify

- `2_execution/data/raw/`

## Constraints

- Do not modify `2_execution/data/raw/`.
- Do not change protected definitions.
- Do not strengthen claims without evidence.

## Expected Output

TBD

## Checks to Run

TBD

## Done When

- Expected output exists.
- Required checks pass or failures are documented.
- Agent run report is complete.
- Critic report is complete when required.
- Human decision is logged when required.

## Human Approval Required For

- Protected definition changes
- Preferred specification changes
- Claim strengthening
- Publication-facing output changes

## Agent Run Report

Save a completed report to `4_agent_runs/`.
