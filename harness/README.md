# Research Harness

The harness is the contract around AI-assisted empirical research work.

It defines how an agent receives a task, what it may read or change, what it must report, what checks must run, how a critic reviews the run, and where human approval is required.

## Harness Components

1. Project constitution: `AGENTS.md` and `project_manifest.yml`
2. Task contract: `tasks/TEMPLATE_task.md`
3. Protected definitions: `docs/protected_definitions.yml`
4. Permission policy: `harness/permissions.yml`
5. Verification checks: `checks/`
6. Worker run report: `agent_runs/TEMPLATE_agent_run_report.md`
7. Critic protocol: `harness/protocols/critic_protocol.md`
8. Human decision gate: `harness/protocols/human_gate.md`

## Default Run Flow

```text
issue or task file
-> worker agent reads required context
-> worker agent operates within allowed files
-> worker agent writes run report
-> mechanical checks run
-> critic agent reviews diff, report, checks, and claims
-> human records accept / revise / reject / defer decision
```

## Harness Principle

The worker agent should never be the only judge of its own work.

Every meaningful run should leave:

- a task file
- a diff or changed-file list
- a run report
- check results
- a critic report for high-risk tasks
- a human decision when protected definitions, claims, or preferred specifications are affected
