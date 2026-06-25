---
status: filled
options:
  - id: O1
    name: "Policy-rule measurement and ex-ante purchase-basket microsimulation"
    project_type: measurement
    identification: "Rule-based measurement using document-coded Policy_s,c vectors from D001-D003 and pre-policy NielsenIQ aggregate outputs from D004; follows F06-F08 and does not require post-policy behavior."
    viability_condition: "D002/D005 wrapper diagnostics show the MAHA source inventory is present and includes D001-D004 with public or granted aggregate access; controlled household bootstrap CI remains a later precision upgrade, not a prerequisite for measurement."
    viability_test:
      metric: inventory_rows
      op: ">="
      threshold: 5
    max_claim: measurement
    threats_addressed: [F04, F09]
    priority: 1
    is_fallback_floor: false
    claim_boundary: "Can claim audited policy design heterogeneity and ex-ante exposure over observed low-income proxy purchase baskets; cannot claim actual SNAP/EBT exposure, welfare effects, or post-policy consumption response."
  - id: O2
    name: "Approval-risk window concentration diagnostics"
    project_type: descriptive
    identification: "Exact transition tables and sparse-event/Firth diagnostics within the public approval-risk window using D001-D003 and state covariate benchmarks from D005; grounded in F03-F05."
    viability_condition: "D003 contains approved and non-approved public-risk states and D005 contains benchmark covariates; the paper can report descriptive approval concentration even when causal identification is not viable."
    viability_test:
      metric: public_sources
      op: ">="
      threshold: 3
    max_claim: associational
    threats_addressed: [F04, F09]
    priority: 2
    is_fallback_floor: false
    claim_boundary: "Can claim approval concentration in the observed public risk set; cannot isolate a causal effect of governor party, federal preference, request quality, or proposal timing."
  - id: O3
    name: "Post-implementation household purchase response design"
    project_type: causal
    identification: "Future difference-in-differences or event-study design comparing treated geographies to comparable controls after observed implementation, with outcomes from 2026+ NielsenIQ/IRI/Circana or equivalent household/retail scanner data; motivated by F10 and constrained by F04/F09."
    viability_condition: "D004 or a successor source must include post-policy purchase outcomes, observed implementation dates, comparable controls, and enough treated units after policy rollout."
    viability_test:
      metric: post_policy_purchase_years
      op: ">="
      threshold: 1
    max_claim: causal
    threats_addressed: [F04, F09]
    priority: 3
    is_fallback_floor: false
    claim_boundary: "Could support causal purchase-response claims only after post-policy data and credible controls exist; current 2022-2024 pre-policy data cannot support this claim."
  - id: O_floor
    name: "Document-linked descriptive administrative chronology"
    project_type: descriptive
    identification: "Always-viable descriptive audit of public waiver texts, approval letters, target implementation dates, modifications, and source-grade availability from D001-D003."
    viability_condition: "always viable (descriptive public-document floor)"
    viability_test:
      metric: always
      op: "always"
      threshold: 1
    max_claim: descriptive
    threats_addressed: [F04, F09]
    priority: 9
    is_fallback_floor: true
    claim_boundary: "Can document what the public record shows and where documents are missing; cannot quantify exposure, selection associations, or behavior if processed datasets are unavailable."
---

## Selection Rule

After diagnostics, select the lowest-priority option whose machine-adjudicable viability test holds. If O1 holds, Paper 1 should be framed as a policy-measurement and ex-ante microsimulation paper, with O2 as a supporting descriptive association module and O3 explicitly reserved for future post-implementation work. If O1 fails but O2 holds, downgrade to an approval-risk-window administrative selection paper without NielsenIQ exposure as a main result. If only O_floor holds, report a public-document chronology and do not make quantitative exposure or selection claims.

## Option O1

O1 is the preferred current design because the audited inventory already contains public waiver documents, processed MAHA design/event-history files, and aggregate NielsenIQ exposure outputs. The estimand is a linked measurement object: approved policy rules as coded, public administrative progression as observed, and pre-policy purchase-basket exposure implied by applying those rules to low-income proxy purchase baskets. This option directly avoids the two main identification threats in F04 and F09 by defining the object as ex-ante accounting exposure rather than realized causal response.

## Option O2

O2 studies whether public approvals are concentrated across observable political-administrative partitions within the approval-risk window. The strongest version uses exact counts and rare-event diagnostics rather than overfit state-quarter causal models. It is useful for Paper 1, but it must be narrated as descriptive/associational because public entry, request quality, state demand, and federal-side selection are jointly determined.

## Option O3

O3 is a future causal design, not a current Paper 1 design. It becomes viable only after post-policy purchase data and observed implementation dates are available. If those conditions hold, the staged-policy literature suggests separately estimating announcement, implementation, and modification/repeal margins; until then, including demand or welfare estimates in Paper 1 would exceed the available data.

## Option O_floor

O_floor is the fallback floor that preserves value even if processed data or NielsenIQ outputs become unavailable. It provides an auditable public chronology of state requests, USDA approvals, target implementation dates, and modifications. Its claim ceiling is purely descriptive.
