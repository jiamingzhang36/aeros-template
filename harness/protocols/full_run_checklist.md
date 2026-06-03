# Full Run Checklist

Use this checklist when a task changes code, outputs, claims, or publication-facing materials.

## 1. Task Contract

- [ ] Task ID exists.
- [ ] Goal is specific.
- [ ] Mainline alignment gate is filled before execution.
- [ ] Files to inspect are listed.
- [ ] Files allowed to modify are listed.
- [ ] Files forbidden to modify are listed.
- [ ] Checks to run are listed.
- [ ] Done conditions are listed.
- [ ] Critic and human gate requirements are explicit.

## 2. Worker Run

- [ ] Worker read required context.
- [ ] Worker stayed within allowed files.
- [ ] Worker wrote an agent run report.
- [ ] Worker documented commands.
- [ ] Worker documented changed outputs.
- [ ] Worker documented check results.

## 3. Mechanical Checks

- [ ] Raw data unchanged.
- [ ] Protected definitions unchanged or explicitly approved.
- [ ] Claim registry valid.
- [ ] Paper numbers or output links checked when relevant.
- [ ] Task contract and run report templates valid.
- [ ] Pipeline or project master script runs when relevant.

## 4. Critic Review

- [ ] Critic reviewed diff or changed files.
- [ ] Critic reviewed run report.
- [ ] Critic checked protected definitions.
- [ ] Critic checked claim strength.
- [ ] Critic gave a verdict.

## 5. Human Gate

Gates are tiered: mechanical gates auto-advance; only human gates
(`gate_lifecycle.human_gates` / active `profile`) halt the loop. See
`harness/protocols/human_gate.md`.

- [ ] If the loop halted, it was at a human gate (not a mechanical one).
- [ ] Decision packet generated (`decisions/gates/<gate>_decision_packet.md`) and reviewed.
- [ ] The grant was committed by an `approver_identity`; the agent only *requested* it.
- [ ] Human decision logged when required.
- [ ] Unresolved uncertainty points are listed and explicitly deferred to owner input.
- [ ] Open issues carried to `decisions/issue_log.csv`.
- [ ] Follow-up tasks created when needed.
