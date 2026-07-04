# CONTEXT_BRIEF

generated_at: TEMPLATE
lane: project
principle: Context is not storage. Context is active attention allocation.

## Goal Context
- current_goal: Initialize or continue the project with a high-signal context brief.
- acceptance_signal: Stop before switching lanes or claiming substantive progress without evidence.
- must_not_do:
  - do not treat route-ready work as substantive evidence
  - do not approve gates or upgrade claims from context
  - do not bulk-read raw outputs unless the next action requires them
  - do not switch lanes silently when context and user request conflict

## State Context
- current_gate: G0
- candidate_gate: G0
- gate_status: open
- current_blocker: None recorded.
- last_validation: Not run.
- lane_snapshot: {}

## Evidence Context
- latest_substantive_artifact: None recorded.
- evidence_rule: Only source-anchored files, hashes, extraction cards, receipts, result records, or official artifacts may support judgments.
- recent_evidence_deltas:
  - none
- source_anchors:
  - none

## Decision Context
- latest_revision: TEMPLATE
- decision_rule: Past decisions constrain next actions but do not certify new evidence.
- open_human_gate_items:
  - none

## Noise Context
- context_stale: false
- context_stale_reason: TEMPLATE brief; run `aeros context compile --write` to generate source hashes.
- raw_output_policy: Raw tool output, failed logs, broad search dumps, and temporary files stay out of main context until compressed into claims, evidence, uncertainty, blockers, or next action.
- files_to_read_if_needed:
  - CURRENT_STATE.md
  - NEXT_ACTION.md
  - AGENTS.md
- excluded_by_default:
  - raw command logs
  - large source dumps
  - duplicate search results
  - failed fetch bodies
  - unreviewed staging files

## Next Action
- recommended_next_action: Run `python3 -m aeros.cli context compile` and `python3 -m aeros.cli next`.
- why_this_next: Build a compact attention layer before reading or acting.
- status_label: ROUTE_READY
- command: python3 -m aeros.cli next
- stop_condition: Stop before switching lanes, approving gates, or claiming substantive progress.
- action_spec_kind: next_action_preview
- action_spec_effect_class: read_only

## Attention Contract
- main_context_admits:
  - current goal and stop condition
  - verified state summary
  - source-anchored evidence pointers
  - human decisions and blockers
  - deterministic next action
- ledger_only:
  - raw check output
  - full command transcripts
  - bulk search results
  - intermediate failures after compression
- requires_reverification:
  - stale source hashes
  - network-derived facts
  - official status pages
  - claim-affecting artifacts

## Communication Budget
- mode: dense
- principle: Compress communication, not evidence.
- target: output_only
- applies_to:
  - status updates
  - final summaries
  - context briefs
  - review comments
- preserve_exact:
  - code
  - commands
  - errors
  - paths/URLs/DOIs
  - claim/evidence/result IDs
  - hashes
  - direct quotes
- do_not_compress:
  - source evidence
  - methodological caveats
  - human gate decisions
  - legal or compliance boundaries
  - uncertainty statements
- risk_note: Output brevity can reduce reading cost, but input/context compression can be net-negative and can distort meaning. Keep source files intact and compress only derived communication surfaces.

## Does Not Prove
- data access
- full-text literature review
- empirical validity
- claim support
- paper readiness
- gate approval
- task completion

This brief is compiled context, not storage, evidence, completion, gate approval, or claim support.
