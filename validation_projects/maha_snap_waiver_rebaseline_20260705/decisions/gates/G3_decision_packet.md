# Human Gate Decision Packet: G3

Generated: 2026-07-05T01:43:04+00:00
Stage: discovery
Current gate: G3 Research Design
Gate status: approved
Candidate gate: discovery / G3
Earned claim ceiling: none

## Recommendation

G3 is already human-approved and current criteria still pass.

## Gate Criteria Status

| Gate | Status | Notes |
|---|---|---|
| G0 | PASS | all criteria satisfied |
| G1 | PASS | all criteria satisfied |
| G2 | PASS | all criteria satisfied |
| G3 | PASS | all criteria satisfied |

## Failed / Missing Criteria

None. All criteria through the target gate passed.

## Evidence Overview

### Passed Runtime Tasks

- D001a_framing
- D001b_framework_search
- D002_data_scouting
- D003_design_options
- D004_variable_construction
- D005_data_probe

### Registered Results

- None registered yet.

### Claim Registry Summary

- No claims registered yet.

## Artifact Excerpts — read the substance, not just the PASS marks

A check confirms a section *exists*; it cannot confirm it *says something*. Read these before approving — hollow, duplicated, or placeholder content here is a reason to block even when every check is green.

### Research question / idea — `discovery/idea_memo.md`

```
# Idea Memo

## Starting Idea

Study MAHA-related SNAP food restriction waiver policy design, approval timing, federal review, implementation friction, and related documentation.
```

### Anchor (4 components) — `discovery/anchor.yml`

```
# Research anchor: 4 components, set ONCE at intake and then frozen (anti-drift).
# Set status: locked once decided; after that it is a protected file.
anchor:
  status: locked           # draft | locked
  locked_at: "2026-07-05"
  topic: "How does the MAHA-era SNAP waiver regime convert a nationally uniform in-kind transfer into heterogeneous state-specific product restrictions, and what public approval and pre-policy purchase-basket exposure patterns are observable?"
  claim_type: "descriptive"
  identification: "Document-linked policy-rule measurement, public approval-risk-window diagnostics, and ex-ante NielsenIQ policy-rule microsimulation; no post-policy causal demand, welfare, health, or actual SNAP/EBT transaction effect is identified in Paper 1."
  data: "USDA/FNS and state waiver documents, public state-quarter event history, approved-state implementation/modification records, state benchmark covariates, and aggregate 2022-2024 NielsenIQ Consumer Panel exposure outputs."
```

### Method card — `docs/method_card.md`

```
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

... (29 more line(s); open the file)
```

### Variable construction — `discovery/variable_construction.md`

```
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
... (51 more line(s); open the file)
```

## Five-Dimension Review (AutoResearch: novelty / validity / impact / reliability / provenance)

The mechanical layer already certifies the last three: **validity** (checks passed), **reliability** (staleness fingerprints / reproducibility), and **provenance** (numbers trace to result cells; results to data). The two a check CANNOT judge are yours to weigh here:
- **Novelty** — is the question/finding meaningfully new vs. prior work, or a restatement? (No machine check can adjudicate this.)
- **Impact** — does the result address something that matters, or is it technically clean but inconsequential?
Approve only if novelty and impact hold; the green checks cover the rest.

## Key Risks for Human Review

- Check whether the evidence actually supports the proposed claim strength.
- Check whether the selected design and data diagnostics match the project intent.
- Check whether any forced overrides, stale tasks, or missing provenance should block approval.

## Human Actions

- Approve: `aeros gate approve G3 --stage discovery --owner <name> --note <why>`
- Block: `aeros gate block G3 --stage discovery --owner <name> --reason <why>`
- Revise: edit the relevant artifacts or task contracts, then rerun `aeros iterate`.
- Stop: record the reason in `decisions/issue_log.csv` or the project log.
