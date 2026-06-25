---
status: filled
claim_type: descriptive
supported_claim_types:
  - descriptive
  - associational
identification_strategy: "Document-linked policy-rule measurement plus public approval-risk diagnostics and ex-ante NielsenIQ purchase-basket microsimulation; no post-policy causal demand design in current Paper 1."
design_supports_causal: false
data_refs:
  - D001
  - D002
  - D003
  - D004
  - D005
selected_option: O1
fallback_option: O_floor
---
# Method Card

## Research Object

Paper 1 measures how MAHA-era SNAP food restriction waivers differ in policy design, how public administrative progression is observed across request, approval, implementation, and modification stages, and what approved rules would cover in pre-policy low-income proxy purchase baskets.

## Research Question

How does the MAHA-era SNAP waiver regime convert a nationally uniform in-kind transfer program into heterogeneous state-specific product-restriction designs, where does public administrative selection appear, and what pre-policy low-income proxy purchase baskets would approved rules cover?

## Estimand

The main estimand is a linked measurement object: policy rules as written and coded, public approval concentration within a frozen approval-risk window, and ex-ante purchase-basket exposure from applying state policy-rule vectors to 2022-2024 NielsenIQ aggregate category spending.

## Treatment / Exposure / Shock / Key Variable

The key exposure is not a randomized treatment. It is the observed state policy-rule vector and its associated administrative status: public visibility, public USDA approval, target implementation/modification status, and the rule basket mapped to NielsenIQ aggregate category spending.

## Outcomes

The descriptive outcomes are design scope/specificity, public approval-risk concentration, observed approval-to-implementation frictions, and ex-ante purchase-basket exposure/incidence among low-income or SNAP-eligible proxy households.

## Sample

The sample combines approved-state waiver documents, public approval-risk-window state records, public/state implementation or modification records, and aggregate 2022-2024 NielsenIQ exposure outputs for approved states covered by the Nielsen data. Hawaii is excluded from current approved-state Nielsen exposure claims.

## Control or Comparison Group

For approval-risk diagnostics, comparison groups are public risk-window states partitioned by governor party and benchmark state characteristics. For Nielsen exposure, comparison objects are state-specific policy baskets, common-basket rule exposure, strict versus broad mapping bounds, and low-income proxy versus other household aggregates where available.

## Empirical Strategy

The strategy is document-linked policy-rule measurement plus descriptive approval-risk diagnostics and ex-ante policy-rule microsimulation. It registers result families and provenance before claim audit, with exact/sparse-model approval diagnostics and Nielsen aggregate exposure used as supporting descriptive evidence.

## Data Sources

The method uses public USDA/FNS approval materials, state request and implementation documents, MAHA processed policy taxonomy/event-history files, NielsenIQ aggregate exposure outputs, and state health/program/political benchmark covariates. Restricted Nielsen microdata are not exported through the AEROS wrapper.

## Measurement Strategy

Policy rules are represented as state-by-category vectors. Exposure is computed as an inner product between the policy vector and observed category spending shares, with strict and broad mappings used where legal text or scanner categories create ambiguity.

## Identification Boundary

The current design is not a causal policy-effect design. It cannot estimate actual SNAP/EBT transaction exposure, consumption reduction, health effects, welfare effects, or demand elasticities because current NielsenIQ outputs are pre-policy and do not observe item-level EBT tender.

## Approval-Risk Diagnostics

Approval concentration is treated as descriptive or associational. Governor party, quarter, obesity, SNAP participation, and related variables are benchmark partitions, not exogenous treatments.

## NielsenIQ Boundary

NielsenIQ outputs support ex-ante exposure and incidence among low-income or SNAP-eligible proxy households. They do not identify actual SNAP participants or actual SNAP dollars spent on restricted items.

## Current Selection

Given the available inventory and diagnostics, the preferred current design is O1: policy-rule measurement and ex-ante purchase-basket microsimulation. O2 is a supporting approval-risk diagnostic module. O3 is reserved for a future post-implementation paper if 2026+ purchase outcomes and credible controls become available.
