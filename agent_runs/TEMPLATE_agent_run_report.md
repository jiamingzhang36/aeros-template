# Agent Run Report

## Run Metadata

Task ID:

Task name:

Agent:

Date:

Branch / commit:

Start commit:

End commit:

Work mode:

Critic required:

Human gate required:

Active work lane:

Lane switch requested?

## Objective

TBD

## Skills Used

- TBD

## Skill Invocation Receipt

Path: `agent_runs/skill_invocations/<task_id>_skill_invocations.yml`

Status: TBD

## Files Read

TBD

## Files Modified

TBD

## Commands Run

TBD

## Outputs Changed

TBD

## Checks Run

| Check | Result | Notes |
|---|---|---|
| TBD | TBD | TBD |

## Protected Definitions

Were protected definitions changed?

- [ ] No
- [ ] Yes, flagged for human approval

## Claim Changes

Were any claims added, removed, strengthened, weakened, or reworded?

- [ ] No
- [ ] Yes, claim registry updated or flagged

## Permission Exceptions

List any attempted or approved deviations from `harness/permissions.yml`.

TBD

## Findings

TBD

## Open Issues for Human Judgment

TBD

## Human Decisions Needed

TBD

## Completion Status

Choose one:

- complete
- partial
- blocked

## Completion Receipt

Path: `agent_runs/completion_receipts/<task_id>_completion_receipt.yml`

Status: TBD

## Action Receipt

Every non-trivial run must either write `agent_runs/action_receipts/<action_id>.yml` with `aeros action receipt ...` or explain why no action receipt was needed.

- action_mode:
- honest_progress_label:
- why_this_now:
- data_impact:
  - inventory_changed:
  - source_verified:
  - data_rows_changed:
  - coverage_changed:
  - backfill_queue_changed:
  - probe_completed:
- research_impact:
  - claim_ceiling_changed:
  - gate_candidate_changed:
  - evidence_graph_changed:
  - result_registered:
- evidence_paths:

## Goal-Mode Data Progress Check

Complete this section when the user asked to collect, backfill, validate, refresh, or verify data/source material.

- Was this a data-oriented run?
  - [ ] No
  - [ ] Yes
- If yes, did the run acquire or verify at least one real data/source/probe artifact?
  - [ ] Yes, artifact path(s):
  - [ ] No, this is an honest blocker/source-discovery attempt
- Data/source/probe artifact path(s), if any:
  - TBD
- If no artifact was acquired, choose one:
  - [ ] `source_discovery_attempt`
  - [ ] `blocked_queue_preparation`
  - [ ] other:
- Paperwork-only changes that do not count as data acquisition:
  - task files, run reports, receipts, README/Makefile edits, checks, logs, ledgers
