---
status: filled
diagnostics_status: stub
selected_design: O2
earned_claim_ceiling: associational
ratcheted_from: ['O1']
---
# Design Selection / Claim Adjudication

Adjudicated: 2026-05-30T03:43:25+00:00

> NOTE: diagnostics are STUBBED — this selection does not earn a real claim until data_diagnostics.yml status is 'measured'.

## Candidate adjudication

| Priority | Design | Max claim | Viable? | Why |
| --- | --- | --- | --- | --- |
| 1 | O1 Staggered DiD on state ban timing | causal | ✗ | n_ban_states_with_firm_presence=0 >= 5 -> FAIL |
| 2 | O2 Bill-text cosine-similarity / model-legislation diffusion instrument | associational | ✓ | bill_text_extractable_states=6 >= 5 -> PASS |
| 3 | O3 Synthetic control for national regulatory approval events | causal | ✓ | donor_pool_size=9 >= 8 -> PASS |
| 9 | O_floor Descriptive cross-jurisdiction regulatory event-study | descriptive | ✓ | always viable |

## Selected design

**O2 — Bill-text cosine-similarity / model-legislation diffusion instrument** (lowest-priority viable design).

## Earned claim ceiling

**associational** — the claim may not exceed this. Ratcheted DOWN from the stronger ambition of O1 (pruned by the data).

