---
status: filled
diagnostics_status: measured
selected_design: O2
earned_claim_ceiling: causal
ratcheted_from: []
---
# Design Selection / Claim Adjudication

Adjudicated: 2026-05-31T07:02:07+00:00

Diagnostics are measured; this selection earns the claim ceiling below.

## Candidate adjudication

| Priority | Design | Max claim | Viable? | Why |
| --- | --- | --- | --- | --- |
| 1 | O1 Staggered DiD on state ban timing | causal | ✗ | n_ban_states_with_firm_presence=0 >= 5 -> FAIL |
| 2 | O2 Bill-text reuse / model-legislation diffusion as IV | causal | ✓ | bill_text_extractable_states=5 >= 5 -> PASS |
| 3 | O3 Synthetic control for national regulatory approval events | causal | ✓ | donor_pool_size=12 >= 8 -> PASS |
| 4 | O4 Regulatory-uncertainty index and investment panel | associational | ✗ | diagnostic 'n_regulatory_events_coded_per_year_avg' not measured |
| 9 | O_floor Descriptive cross-jurisdiction regulatory event chronicle | descriptive | ✓ | always viable |

## Selected design

**O2 — Bill-text reuse / model-legislation diffusion as IV** (lowest-priority viable design).

## Earned claim ceiling

**causal** — the claim may not exceed this. No stronger design was pruned.

