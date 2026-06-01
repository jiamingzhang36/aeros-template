---
status: filled
claim_type: measurement
supported_claim_types:
  - descriptive
  - measurement
identification_strategy: "Repeated black-box audit of AI-generated grocery recommendations across pre-registered household personas; no causal identification is claimed."
design_supports_causal: false
selected_design: O1
earned_claim_ceiling: measurement
---

# Method Card

## Research Question

Do AI-generated grocery recommendations remain stable, affordable, nutritionally reasonable, and equitable when prompted with realistic household constraints, especially low-income and SNAP-relevant food choice environments?

## Claim Type

The strongest currently supportable claim type is `measurement`. The study can measure recommendation quality under a documented audit protocol, but it cannot yet make causal claims about model behavior, consumer outcomes, or platform-wide effects.

## Treatment / Exposure / Shock / Key Variable

The key exposure is the pre-registered household persona used in the prompt. Personas vary budget pressure, household size, dietary constraints, food-access context, and SNAP-relevant constraints.

## Control or Comparison Group

The comparison is across persona categories and repeated runs for the same persona. There is no natural control group and no causal treatment assignment.

## Outcomes

Primary outcomes are recommendation basket structure, nutrition score, affordability ratio, and recommendation stability. Secondary outcomes may include feasibility flags such as vague items, missing quantities, culturally or institutionally infeasible suggestions, and reliance on restricted/expensive foods.

## Sample

The sample will be generated AI recommendation outputs collected under a fixed prompt grid. Each observation is a model-run/persona/repetition tuple identified by `model_run_id`.

## Empirical Strategy

The selected design is O1, a measurement audit. The project will collect repeated black-box outputs, parse grocery recommendations into structured baskets, match items to nutrition and affordability sources where possible, and compare scores across personas and repetitions.

## Fixed Effects

No fixed-effects design is currently claimed. If the later execution dataset includes multiple models or time periods, model and prompt-template indicators may be used descriptively.

## Clustering / Standard Errors

No causal standard-error strategy is claimed at discovery stage. For measurement summaries, uncertainty should be reported across repeated runs within persona and model cells.

## Identifying Assumption

The measurement claim assumes only that the prompt grid, parsing rules, and scoring rules are documented and applied consistently. It does not assume exogenous treatment variation or causal comparability.

## Main Threats

The main threats are prompt sensitivity, hidden model updates, retailer price measurement error, vague or non-purchasable recommendations, nutrition matching ambiguity, and synthetic personas that may not represent real households.

## Robustness Checks

Robustness checks should include repeated runs per persona, alternate prompt phrasings, sensitivity to item matching rules, nutrition-score variants, affordability thresholds based on TFP/SNAP benchmarks, and exclusion of vague recommendations.

## What This Design Cannot Show

This design cannot show that AI recommendations cause changes in household purchases, nutrition, or food security. It cannot establish legal discrimination, platform-wide bias, or precise local affordability until retailer price capture and sampling protocols are validated.

## Human Approval Status

Status: ready for G3 review

Date: 2026-06-01

Approver:
