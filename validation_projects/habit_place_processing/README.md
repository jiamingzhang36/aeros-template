# Habit, Place and Processing Validation Project

Instantiated AEROS project for the residential-move / brand-history study.

Working repository: `~/Desktop/Habit_Place_Processing`
Remote: https://github.com/jiamingzhang36/Habit_Place_Processing (private)

**Onboarded mid-flight on 2026-09-01.** The project ran from 2026-07-08 to
2026-09-01 with only the AEROS heavy-job runner attached (`.aeros/heavy_jobs.yml`),
so this instance holds no pipeline telemetry: there are no `agent_calls_total`
or `cost_usd_total` figures, because no AEROS task contract produced them.
`aeros_state.yml` records the gate position inferred from the artifacts that
exist in the working repository, not from runs.

Before onboarding, `aeros status` run inside the repository reported
`discovery / G0` — the default for an unattached tree — for a project that
already holds two manuscript directories, a replicated holdout, and 145
quality-report entries. Correcting that mismatch is the point of this instance.

Research artifacts stay in the working repository. This folder holds the AEROS
state, manifest and gate record only.

## Structural note recorded at onboarding

This repository carries **two paper lines at different gates**:

- Paper 1, *Not a Clean Slate* — furthest along, blocked on a measurement
  freeze and one missing independent validator;
- Paper 2, *digital portability* — outcomes deliberately closed, blocked on a
  human estimand decision after repeated overlap/balance failures.

AEROS models one gate per project. `aeros_state.yml` therefore records the
**binding** (lower) gate and breaks the two lines out under `gate_rationale`.
If the two lines diverge further, splitting them into separate AEROS instances
is the cleaner fix; that is a human decision and has not been taken.
