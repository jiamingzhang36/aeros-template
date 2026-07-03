# AEROS Runtime Phase 1 Freeze

Date: 2026-07-03

Status: active freeze baseline

## Purpose

AEROS has reached a working authority-aware runtime baseline. The next phase is
not more horizontal policy surface. The next phase is consolidation, rollout,
and friction measurement.

North star:

```text
AEROS should reduce the cost of truthful research progress.
```

Truthful means no fake full text, no fake result, no fake claim, no fake
approval, and no staged artifact pretending to be canonical evidence.

Progress means leads can become candidates, data can be probed, full text can be
extracted, results can be reproduced, claims can be reviewed, and papers can be
released through human authority.

Cost means fewer unnecessary approvals, fewer false blocks, fewer manual pushes,
less check noise, and lower recovery time after agent drift.

## Freeze rule

Do not add new horizontal surfaces by default.

Frozen unless a real rollout blocker proves otherwise:

- New lane.
- New gate.
- New workflow preset.
- New execution mode.
- New task mode.
- New output intent.
- New permission tier.
- New skill obligation class.
- New dashboard.
- New agent role.

Admission rule for exceptions:

- It fixes a real downstream rollout blocker.
- It lowers control tax.
- It reduces fake progress.
- It reduces human pushes.
- It turns an important advisory boundary into an enforceable boundary.

Otherwise, put the idea in backlog and measure it in a real project first.

## Five-field compiled control model

Existing user-facing presets remain, but they should compile into five
orthogonal fields:

```yaml
artifact_level:
  lead
  candidate
  staging
  canonical_candidate
  canonical
  result
  claim
  paper
  release

effect_class:
  read_only
  local_write
  network_read
  credentialed_read
  external_write

authority_surface:
  none
  route
  resource
  claim
  paper
  release

execution_budget:
  smoke
  bounded
  expensive
  waiting

verification_strength:
  self_reported
  harness_observed
  machine_validated
  human_accepted
  externally_reproduced
```

Named presets such as `broad_capture`, `source_capture`, `bounded_probe`, and
`paper_release` are compatibility and usability handles. They are not separate
truth systems.

## Broad-capture rule

Broad capture is intentionally light:

```text
wide in, wide out, strict on promotion
```

Broad capture may produce leads, candidate queues, and batch audit notes. It
must not produce canonical data, results, claim support, paper text, release
materials, or approvals.

Promotion from `lead` or `candidate` into `staging`, `canonical_candidate`,
`canonical`, `result`, `claim`, `paper`, or `release` requires a separate action
with stronger verification and, when appropriate, human authority.

## Measurement focus

During the freeze window, measure:

- `control_tax`: control actions divided by total actions.
- `substantive_yield`: accepted substantive artifacts divided by total actions.
- `lead_to_candidate_rate`.
- `candidate_to_staging_rate`.
- `stale_lead_count`.
- `human_pushes_per_artifact`.
- `false_progress_blocks`.

If `control_tax` rises while `substantive_yield` stays low, AEROS is maintaining
itself rather than helping research.

## Near-term rollout targets

- CMPD broad-capture rollout.
- One real evidence sufficiency audit packet.
- One source promotion packet from lead/candidate to staging.
- One project sync-doctor run after template sync.

## Non-goals

- No automatic claim upgrade.
- No automatic paper-ready decision.
- No automatic release decision.
- No new gates during the freeze window.
- No new lanes during the freeze window.
- No claim that local hash chains are tamper-proof security.
- No claim that schema-valid evidence audits prove evidence sufficiency.
