# AEROS Runtime Rollout Validation — 2026-07-10

## Purpose

This canary prevents an empty template harness from being treated as evidence
that AEROS is useful on live research state. It executes the current template
runtime directly against three real projects without syncing files, changing
state, executing tasks, calling providers, approving gates, or editing claims.

## Runtime Under Test

- Template branch before this change: `aeros-runtime-phase1` at `20ade74`.
- Candidate changes: mtime/size-keyed read caches for preflight policy YAML,
  one-contract reuse inside preflight, and full-only isolation fixtures.
- Invocation boundary: template `aeros` was explicitly imported before changing
  into each project directory, so vendored project packages could not shadow the
  candidate runtime.

## Canary Commands

For each project, the candidate runtime executed the equivalents of:

```bash
python3 -m aeros.cli drive --json
python3 -m aeros.cli task preflight \
  --lane data \
  --intent "broad search public official source leads into work/leads only; do not enter processed canonical claim or paper" \
  --json
```

Both commands are read-only/advisory in this canary. No `--execute`, task run,
provider call, state write, gate decision, or artifact promotion was allowed.

## Results

### Land-grid (`f340ab04`)

- `drive`: `READY`, but selected generic `broad_capture` because the project has
  no active `CURRENT_WORK.yml` priority and no nonzero compiled research risk.
- Assessment: mechanically safe but not fully aligned with the post-campaign
  objective in `CURRENT_STATE.md`; this is a real context-adoption finding, not
  a canary PASS for recommendation quality.
- broad-capture preflight: `ADVISORY`, no human decision required, writes limited
  to lead/candidate/audit surfaces; processed data, claims, paper, and decision
  log remained forbidden.

### Cultured meat (`016e0eba`)

- `drive`: `READY`; selected a dry-run literature path for stale
  `D001b_framework_search` and explicitly required human choice before any
  provider/API rerun.
- Assessment: conservative and actionable; it does not prove that literature is
  the scientifically optimal next priority.
- broad-capture preflight: `ADVISORY`, no human decision required, with the same
  lead-only write firewall.

### MAHA (`28cf10b`)

- `drive`: `READY`; selected the active `CURRENT_WORK.yml` priority to verify
  that Appendix Tables A22/A23 distinguish frozen analysis inputs from
  post-freeze context.
- Assessment: aligned with the operator-declared writing objective and bounded
  to preflight rather than execution.
- broad-capture preflight: `ADVISORY`, no human decision required, with protected
  research surfaces forbidden.

## Vendored-Version Drift Observed

All three projects had task-preflight/task-mode/source-permission hashes that
differed from the candidate template. This validates the need to distinguish
"template behavior" from "currently vendored project behavior" when reporting
rollout results. It does not authorize an automatic sync.

## Verdict

- Mechanical canary: **3/3 commands parsed and returned bounded JSON under the
  current template runtime**.
- Broad-capture safety boundary: **3/3 aligned**.
- Research-driver recommendation alignment: **2 aligned/bounded, 1 context gap
  (land-grid)**.
- Release implication: the runtime candidate has real-project evidence, but the
  land-grid result must remain visible until that project records an active
  current-work priority or the operator deliberately accepts broad capture.

## Does Not Prove

- that any recommendation is scientifically optimal;
- that vendored projects have been upgraded;
- that any source was captured or any task executed;
- that research artifacts, claims, papers, or gates are valid or approved;
- that an empty-template full harness substitutes for live-project validation.
