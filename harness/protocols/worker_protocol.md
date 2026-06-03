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

## Gates and Human Approval

The runtime tiers gates: mechanical gates (a check can adjudicate their exit
criteria) auto-advance; human gates halt the loop. See
`gate_lifecycle.human_gates` / the active `profile` in `project_manifest.yml`
and `harness/protocols/human_gate.md`.

- You may **request** a human gate (`aeros gate request "<gate>"`) and you may
  do the work that *earns* a gate. You may **not grant** one.
- A grant counts only when the approval artifact (`decisions/approvals/<gate>.md`)
  is committed by an `approver_identity` (`harness/permissions.yml`
  `human_approval`). Never commit that artifact yourself; never run
  `git config user.*` to assume the approver identity; never run
  `aeros gate approve` on the human's behalf.
- When the loop halts at a human gate it writes a decision packet
  (`decisions/gates/<gate>_decision_packet.md`). Make sure your run report and
  outputs give that packet real evidence to summarize.

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
