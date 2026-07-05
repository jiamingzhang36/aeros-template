---
status: filled
---
# Feasibility Matrix

## Overall Decision

Current Paper 1 is feasible as a measurement and ex-ante policy-rule microsimulation paper. A post-policy causal demand paper is not feasible with current 2022-2024 pre-policy NielsenIQ outputs.

## Minimum Viable Version

The minimum viable version is a public-document administrative chronology with policy taxonomy. The preferred feasible version adds aggregate NielsenIQ exposure and approval-risk diagnostics.

## Dimension Assessment

- **Importance**: High. Paper 1 is the project core — it measures a live, salient federal/state policy (SNAP food-restriction waivers) for which no ex-ante, document-coded policy-rule exposure measurement currently exists.
- **Literature gap**: Partially assessed. The literature lane in this wrapper is minimal (no formal synthesis yet); the substantive gap targeted is the absence of ex-ante policy-rule exposure measurement for these waivers, not a completed systematic review. Treat as a framing gap, not evidence.
- **Data availability**: Conditional. Public approval/policy documents are available (D001–D003); NielsenIQ aggregate exposure outputs are available for approved states excluding AK/HI (D004); controlled household-cluster CI is pending a controlled-DuckDB disk reconnect (precision upgrade, not a prerequisite).

## Decision

Decision: pursue

Pursue the measurement / ex-ante exposure Paper 1 (design O1). The post-policy causal demand paper is paused (not feasible with current 2022–2024 pre-policy outputs).

## Further Dimensions

- **Identification**: None causal — this is rule-based measurement (document-coded Policy_s,c vectors and pre-policy aggregate exposure; design O1) plus descriptive approval-risk concentration (exact counts / rare-event diagnostics; design O2). No causal identification is claimed; public entry, request quality, and federal selection are jointly determined.
- **Execution cost**: $0 marginal. Uses existing public documents and previously-produced NielsenIQ aggregate outputs; no new data purchase. Controlled household-cluster CI needs only compute on already-licensed data.

## Remaining Dimensions

- **Data engineering maturity**: Medium. Public documents (D001–D003) are located and coded; NielsenIQ aggregate outputs (D004) exist from the MAHA controlled workflow; the controlled household-cluster CI step is pending a DuckDB disk reconnect. Wrapper records discovery metadata and provenance hooks only — paper-facing derived outputs remain in the MAHA source repo until registered.
- **Measurement quality**: Document-grade. Policy-rule vectors and approval status are coded from public documents with no imputation (missing evidence held as missing/right-censored). Known boundary: ex-ante purchase-basket exposure measures spending share inside policy baskets, not actual SNAP/EBT transactions, consumption, or welfare; AK/HI not covered in current Nielsen outputs.
