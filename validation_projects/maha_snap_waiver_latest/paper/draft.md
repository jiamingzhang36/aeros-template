---
status: wrapper_paper_package_draft
canonical_manuscript: /Users/jiamingzhang/Desktop/MAHA/docs/manuscript/paper_manuscript_draft.md
claim_ceiling: measurement_and_descriptive_association
final_claim_status: not_final
---
# SNAP Food Restriction Waivers: Policy-Rule Measurement, Administrative Selection, and Ex-Ante Purchase-Basket Exposure

This AEROS wrapper draft is not the canonical manuscript. It is a paper-package checkpoint that records the current research question, method, evidence chain, claim boundaries, limitations, and replication status for Paper 1. The canonical writing file remains in the MAHA repository.

## Research Question

Paper 1 asks how MAHA-era SNAP food restriction waivers vary in design, pass through public administrative selection, and translate into ex-ante exposure over low-income proxy grocery baskets. The object is a linked measurement problem: state policy rules as written, public approval progression as observed, and pre-policy purchase-basket exposure implied by approved rule vectors.

The paper does not treat a waiver as a single national treatment. It treats each waiver as a state-specific policy-rule vector whose categories, definitions, target implementation timing, and post-approval changes can differ across states.

## Design and Method

The design combines three descriptive modules.

First, the project measures policy-rule design from public USDA/FNS and state waiver documents. The design object is a state-by-category rule vector plus a scope-and-specificity taxonomy. This module supports claim `C001`.

Second, the project studies public approval-risk concentration using public request and approval records. Governor party and state covariates are descriptive partitions and benchmarks, not exogenous treatments. This module supports claim `C002`.

Third, the project maps approved policy-rule vectors to aggregate NielsenIQ Consumer Panel category-spending outputs for the pre-policy window. Exposure is an ex-ante accounting measure over low-income or SNAP-eligible proxy baskets, not observed SNAP tender and not a post-policy response. This module supports claim `C003`.

## Evidence and Results

The registered evidence chain contains four result families.

`R001` records the policy-rule measurement and design-taxonomy artifact. It supports the claim that MAHA-era waivers are heterogeneous state-specific product-restriction designs rather than one soda-or-candy policy.

`R002` records public approval-risk concentration diagnostics. It supports descriptive approval-concentration language within the frozen risk window while preserving the boundary that approval concentration is not a separable treatment effect of governor party.

`R003` records aggregate NielsenIQ ex-ante exposure outputs. It supports purchase-basket exposure and incidence claims for currently covered approved states, with Hawaii excluded from the approved-state Nielsen exposure claim.

`R004` records boundary and feasibility diagnostics. It supports explicit limits around SNAP/EBT non-observation, target implementation timing, scanner-category ambiguity, and future data needs.

## Claim Boundary and Claim Ceiling

The current maximum claim ceiling is measurement with supporting descriptive or associational diagnostics. The wrapper claim registry marks `C001`, `C002`, `C003`, and `C004` as supported and bounded.

The paper package does not support statements about post-policy consumption changes, health outcomes, welfare effects, demand elasticities, or actual SNAP/EBT transaction incidence. It also does not support a statement that governor party causes approval. Any such claim would require a new evidence package and a later gate review.

## Limitations and Scope

The current evidence is strongest for policy measurement, public-process description, and ex-ante exposure accounting. It is weaker for mechanisms that require latent proposal quality, federal internal decision records, household-level payment tender, or post-implementation purchase outcomes.

NielsenIQ outputs in the wrapper are aggregate-only. The current exposure estimates are over observed low-income proxy purchases and not actual SNAP purchases. They should be interpreted as what approved rules would cover in observed pre-policy baskets before any behavioral response.

Implementation dates in the source materials are target or planned implementation dates unless separately observed as realized rollout. Approval is therefore not the same object as realized restriction.

## Replication and Reproducibility

The wrapper replication package is smoke-safe. It verifies registered result paths, provenance records, claim boundaries, and the master pipeline entry point without copying raw or restricted data. The public wrapper can reproduce the artifact chain and check that no registered result exports restricted microdata.

Full reruns of NielsenIQ raw purchase, trip, panelist, product, household-month, and household-cluster bootstrap routines require a controlled Nielsen data environment. Public release of those restricted microdata is not approved by this package.

## Paper Package Status

This is not a final submission manuscript. It is a bounded AEROS paper-package draft aligned to the current claim registry, replication report, and result index. The remaining substantive submission blockers are external to this wrapper checkpoint: independent MG human second-coder reliability, controlled-DuckDB uncertainty intervals after disk reconnect if required for the final version, and journal-specific formatting or release approval.
