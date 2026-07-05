# AEROS Rollout Playbook

Use this playbook when upgrading an existing project to the latest AEROS template.

The path is intentionally fixed:

1. Commit or otherwise preserve the target project's current work.
2. Run `tools/sync_aeros_latest.zsh <project_path>`.
3. Run `python3 checks/check_work_lanes.py` in the target project.
4. Recover or revalidate old completion receipts if the template changed receipt semantics.
5. Run `python3 checks/run_harness_checks.py --timeout 30` in the target project.
6. Write a rollout report in `agent_runs/`.
7. Update `CURRENT_STATE.md`.
8. Run `python3 -m aeros.cli next` and optionally `python3 -m aeros.cli next --write`.
9. Commit the target project rollout.

Rollout status labels:

- `CHECK_PASS`: sync/checks completed mechanically.
- `ROUTE_READY`: rollout blockers or human approvals are queued.
- `SUBSTANTIVE_PRODUCED`: the rollout changed a real project artifact, recovered a task, or validated a substantive artifact.

Rules:

- Do not hand-copy framework files into projects.
- Do not mark old tasks complete only because the new harness passes.
- Do not confuse route audits, approval queues, or rollout reports with data/literature/result progress.
- If the sync exposes old invalid receipts, report the failure honestly and recover them with task-specific checks.
