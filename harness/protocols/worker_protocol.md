# Worker Protocol

Use this protocol for the agent that performs the task.

## Before Working

1. Read `AGENTS.md`.
2. Read `project_manifest.yml`.
3. Read the task file in `tasks/discovery/` or `tasks/execution/`.
4. Read `harness/permissions.yml`.
5. Read protected files named by the task.
6. Identify allowed files, forbidden files, required checks, and done conditions.

## During Work

- Stay within the allowed files.
- Do not modify raw data.
- Do not modify protected definitions without explicit human approval.
- Do not silently change sample, exposure, outcome, model, clustering, or claim type.
- Prefer adding a report or audit note over silently changing research definitions.
- Preserve failed checks in logs or the run report instead of hiding them.

## After Work

Write a run report in `agent_runs/` with:

- task ID
- files read
- files modified
- commands run
- outputs changed
- checks run and results
- protected definitions changed: yes / no
- claim changes: yes / no
- human decisions needed

Then run required checks, or explain why they could not run.
