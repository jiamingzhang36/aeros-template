# Design Proposal: Graph-Propagated Claim Impact (stale-triage v3)

**Status: PHASE 1 IMPLEMENTED & VALIDATED. PHASE 2 DEFERRED.** Backlog: AEROS-IMPROVE-011.

## Implementation status

- **Phase 1 — registrar production edge (IMPLEMENTED).** In
  `aeros/runtime/stale_triage.py::_output_claim_impact`: a task that writes a
  result/evidence registry (`evidence/result_index.csv`, `result_registry.csv`,
  `evidence_ledger.csv`) is the producer-of-record for the claims that registry
  links, so its impacted claims resolve to the concrete claim IDs instead of an
  unscoped `registry_unknown`. Conservative fallback preserved: if the registry
  links no claims, it stays `registry_unknown` (high but unscoped). Covered by
  `checks/check_stale_triage.py` (registrar-resolves and empty-registry-fallback
  cases). **Validated** on CMPD (read-only, 2026-06-21): `T004_main_execution`
  now resolves to `specific_claims [C1,C2,C3,C4]` (was unscoped); paper/audit/
  pipeline tasks unchanged (`paper_global_review`/`none`) — no regression, no
  over-attribution to T004's ancestors.
- **Phase 2 — transitive descendant propagation (DEFERRED).** Propagating claims
  to a stale task from a frontier-connected descendant that produces a bound
  result. Deferred because it carries the over-attribution risk (a foundational
  task "feeds everything") and needs the cap + frontier-band restriction below
  before it is safe to enable. The Phase-1 registrar edge already resolves the
  validated CMPD gap without that risk.

The original design follows.

## Motivation (grounded in a real test)

The 2026-06-21 read-only acid test on CMPD (at G10, 18 tasks) showed the tightened
stale-triage discriminates correctly — only 1/18 high, the paper task de-escalated
to `paper_global_review` — **but no task resolved to the precise `specific_claims`
scope.** Every claim-relevant task fell back to `registry_unknown`.

Root cause: `_output_claim_impact` attributes claims only when a task's *own*
`allowed_outputs` string-matches a registered result/evidence path. CMPD task
outputs are coarser (e.g. `outputs/`, `audits/...`, `data/final_csv/`) than the
specific result CSV paths, so the match never fires and it conservatively falls
back to "registry touched = high-unknown." Safe, but the sharp attribution we built
is dormant.

## Core idea

Resolve a stale task's impacted claims by **propagating through the production /
dependency graph**, not only by matching the task's own output strings:

> A stale task is claim-bound to claim C if a **result it (transitively) produces**
> is linked to C — even when the task's `allowed_outputs` don't literally contain
> the result's path.

So `T004_main_execution` would resolve to the *specific* claims its registered
results feed (e.g. C1/C4), instead of the coarse `registry_unknown`.

## How it plugs in (reuse, do not add a layer)

Extend the existing deterministic helpers in `aeros/runtime/stale_triage.py`:

1. **Build a result→producer map** in `_claim_links` (or a sibling): for each
   `result_index` row, record its `script_or_source` and `path`. Map each registered
   result to the task that produces it via the research-graph `result_generated_by`
   edge when present; else the deterministic fallback (the task whose
   `allowed_outputs`/script directory contains the result path or script).
2. **Add `_task_claim_impact(task_id, contract, ...)`** that resolves impacted claims
   from: (a) the task's own outputs matching result/evidence paths [existing], OR
   (b) results the task **produces** [new], OR (c) optionally, results produced by a
   frontier descendant that consumes this task's output [new, capped].
3. `triage_stale_tasks` calls `_task_claim_impact` instead of the output-only
   `_output_claim_impact`; the `_classify` buckets/levels are unchanged.

## Invariants kept (same as v1/v2)

- **Deterministic**: derived from `research_graph` + `result_index` + `claim_registry`
  only. No LLM, no heuristic "importance" guess.
- **Conservative fallback**: if the producer mapping is ambiguous/absent, keep the
  current `registry_unknown` (high-but-unscoped) — never invent specific claims.
- **Advisory + recommend-only**: ceiling raises and claim release stay human-gated.
- **Suppression unchanged**: still only suppress when frontier-disconnected AND
  output-fingerprint unchanged.

## Non-goals

- Does not change buckets, suppression, or the volatile-output handling.
- Does not make impact an LLM/fuzzy judgment.
- Does not remove the conservative `registry_unknown`/`paper_global_review` fallbacks.

## Validation (the acceptance test)

Re-run the CMPD read-only acid test. Expected after v3:
- Result-producing tasks (e.g. `T004_main_execution`, `T004_result_validation`)
  resolve to **specific claims** (C1/C2/C4) with scope `specific_claims`, not
  `registry_unknown`.
- Paper-only / registry-only tasks stay `paper_global_review` / `registry_unknown`.
- Total "high" count stays small (no regression to "everything high").

## Risk

Graph propagation can over-attribute (a foundational task transitively "feeds
everything"). Mitigation: attribute **direct production first** (task → results it
writes); make transitive-descendant propagation optional and **capped to the
frontier band**; keep the conservative fallback. If propagation would mark > N
claims, downgrade to `registry_unknown` rather than asserting all.
