---
status: filled
claim_type: descriptive
supported_claim_types:
  - descriptive
  - associational
identification_strategy: "Bill-text reuse and model-legislation diffusion design is selected as the strongest feasible causal candidate, while currently registered headline claims remain descriptive or associational unless separately approved as causal."
design_supports_causal: false
---

# Method Card

## Research Question

Why do US states regulate cultivated meat before broad market formation, and what political-economy mechanisms predict timing, stringency, and legislator political supply?

## Claim Type

Choose the strongest currently supportable type:

- descriptive
- associational
- causal
- mechanism
- policy-translation
- forecast

## Treatment / Exposure / Shock / Key Variable

CW policy ideology index (state-level); log cattle inventory (sector exposure proxy); Republican party affiliation (legislator-level).

## Control or Comparison Group

States without CM bills (Stage 1); states with agenda entry but no escalation (Stage 2); non-sponsoring legislators (bill-level).

## Outcomes

State response (any CM bill introduced), maximum stringency, bill-level severity score, legislator sponsorship/cosponsorship indicator.

## Sample

50 US states, 2019–2025; 140-bill corpus; legislator-bill panel (21,748 rows, 7,270 legislators).

## Empirical Strategy

Cross-sectional OLS/logit (state-level); discrete-time hazard (state-year, Stage 1/2); bill fixed-effects logit (legislator-bill). Predominantly descriptive/associational. Hazard models are timing diagnostics, not headline causal estimates.

## Fixed Effects

State-level specifications use no preferred fixed effects in the cross-sectional models. State-year timing diagnostics may include year indicators where the outcome panel supports them. Bill-level legislator models use bill fixed effects to compare sponsors/cosponsors and non-sponsors within the same bill context.

## Clustering / Standard Errors

State-level models report robust standard errors where applicable. Bill-level legislator models cluster standard errors at the bill or state-bill level when repeated legislator observations create within-bill dependence. Small-sample limitations are reported rather than treated as solved by clustering.

## Identifying Assumption

The currently registered descriptive and associational claims require no causal exclusion restriction. The selected causal candidate, O2, would require model-legislation or bill-text diffusion to shift regulatory language through policy-network exposure rather than through unobserved state demand for cultivated-meat restrictions. That assumption is not used to upgrade current approved claims without human approval and additional causal-result registration.

## Main Threats

Main threats are endogenous agenda entry, selective bill drafting, incomplete measurement of agricultural political economy, unobserved state ideology or industry lobbying, limited firm-presence variation, and sparse state-level event counts. Legislator-level results may also reflect party and committee selection rather than independent treatment effects.

## Robustness Checks

Robustness priorities are alternative ideology and agriculture-exposure measures, exclusion of states with unusual bill clusters, model variants for any-bill versus stringency outcomes, sensitivity of legislator results to committee membership and party controls, and separate reporting of descriptive chronicle results from associational models.

## What This Design Cannot Show

The current registered design cannot estimate effects on firm entry, investment, prices, quantities, consumer demand, welfare, or national market formation. It also cannot generalize beyond US state cultivated-meat bills in 2019-2025, and it should not convert correlational political-economy patterns into causal language unless an approved causal specification is separately registered and validated.

## Human Approval Status

Status: draft

Date:

Approver:
