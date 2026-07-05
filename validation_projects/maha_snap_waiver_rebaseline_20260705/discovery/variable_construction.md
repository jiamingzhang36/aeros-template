---
status: filled
variables:
  - name: policy_rule_vector
    role: treatment
    definition: "State-by-category indicator vector Policy_s,c describing which standardized food/beverage categories each approved or publicly visible SNAP waiver rule would restrict."
    source_data_id: D003
    construction: "Construct from MAHA processed policy taxonomy and public event-history files by mapping document-coded restriction tags to standardized category_main categories; retain strict and broad mappings where legal text is ambiguous."
    validity_concern: "Depends on policy-text coding and category mapping; requires second-coder/LLM-assisted validation and careful bounds for broad residual categories such as OTHER_FOOD."
    constructible: "yes"
  - name: public_approval_status
    role: outcome
    definition: "Indicator that a state in the public approval-risk window had a public USDA approval by the frozen roster date."
    source_data_id: D001
    construction: "Read USDA/FNS approval roster and approval letters; assign approval status within the snapshot/freeze date and preserve non-approved public-risk states as right-censored within the public snapshot."
    validity_concern: "Public approval is not the same as latent federal approval propensity; risk-set entry and request quality are jointly selected."
    constructible: "yes"
  - name: policy_specific_exposure
    role: outcome
    definition: "Share of pre-policy NielsenIQ-observed low-income proxy food and beverage spending falling inside each state's policy-rule basket."
    source_data_id: D004
    construction: "Compute ActualExposure_s = sum_c Policy_s,c * Share_s,c from aggregate NielsenIQ state-year/category outputs; compute RuleExposure_s with the common pooled basket for rule-scope comparison."
    validity_concern: "Measures ex-ante purchase-basket exposure, not actual SNAP/EBT transactions, consumption reduction, welfare, or post-policy response; Hawaii is not covered in current approved-state Nielsen outputs."
    constructible: "yes"
  - name: post_policy_purchase_response
    role: outcome
    definition: "Change in household or geography-level purchases after observed policy implementation."
    source_data_id: D004
    construction: "Would require 2026+ post-policy NielsenIQ/IRI/Circana purchase data and observed implementation dates; current 2022-2024 Nielsen outputs are pre-policy only."
    validity_concern: "Not constructible from current Paper 1 data; using it now would falsely convert an ex-ante measurement paper into a causal demand-response paper."
    constructible: "no"
  - name: governor_party
    role: control
    definition: "Governor party alignment used as a descriptive partition of the public approval-risk window."
    source_data_id: D005
    construction: "Merge state-quarter governor party/covariate file to public approval-risk rows by state and quarter/freeze timing."
    validity_concern: "Not a causal treatment; it indexes broader political-administrative alignment, request timing, coalition demand, and federal-side discretion."
    constructible: "yes"
  - name: request_document_grade
    role: moderator
    definition: "Evidence-grade indicator for whether an approved state has paired public request and approval documents sufficient to classify request-to-approval preservation."
    source_data_id: D002
    construction: "Classify states as paired full request/approval, USDA summary-only plus approval, or missing/partial request-side evidence from public document ledger."
    validity_concern: "Uneven public document availability can create denominator confusion; full-document claims must use the 15-state paired-document denominator while public-record claims use the broader approved-state denominator."
    constructible: "uncertain"
  - name: snap_eligible_proxy
    role: moderator
    definition: "Income/FPL-based proxy for SNAP-eligible or low-income households in NielsenIQ outputs."
    source_data_id: D004
    construction: "Use household income bracket, household size, year, and FPL mapping to flag baseline/conservative income-eligible proxies in aggregate outputs."
    validity_concern: "NielsenIQ does not observe actual SNAP participation or EBT tender at the item level; official income codebook and projection weights must be documented."
    constructible: "uncertain"
---

## policy_rule_vector

This is the central treatment-like measurement object for Paper 1. It is not a treatment assignment in a causal design; it is a rule vector that translates state policy text into standardized product categories and enables ex-ante exposure accounting.

## public_approval_status

This outcome supports the approval-risk-window concentration module. It must always be paired with language that the estimand is public approval concentration within a frozen snapshot, not a causal effect of state politics.

## policy_specific_exposure

This outcome supports the NielsenIQ microsimulation module. The denominator is NielsenIQ-observed food and beverage spending among low-income proxy households, and the estimate is pre-policy accounting exposure.

## post_policy_purchase_response

This variable is intentionally marked not constructible for current Paper 1. It belongs to a future post-implementation paper once 2026+ purchases and implementation timing are available.

## governor_party

This variable is a descriptive partition and benchmark control, not an exogenous treatment. It can be used in exact/Firth diagnostics if the text keeps the associational boundary.

## request_document_grade

This moderator guards claims about request-to-approval preservation. It prevents the paper from treating summary-only states as if full request text had been observed.

## snap_eligible_proxy

This moderator is useful for incidence and exposure heterogeneity, but it cannot be described as actual SNAP household or EBT transaction status.
