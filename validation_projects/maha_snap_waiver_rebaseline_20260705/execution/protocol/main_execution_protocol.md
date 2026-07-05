---
status: filled
earned_claim_ceiling: measurement
result_ids:
  - R001_policy_rule_measurement
  - R002_approval_risk_concentration
  - R003_nielsen_policy_rule_exposure
  - R004_boundary_and_feasibility_diagnostics
selected_design: O1
supports_causal_claims: false
---
# Main Execution Protocol

## Observation Unit

The execution protocol uses multiple linked units: approved-state policy rules, public approval-risk state or state-quarter records, approved-state NielsenIQ aggregate exposure records, and document-grade implementation/modification records. No household-level or purchase-level restricted NielsenIQ rows are exported through the wrapper.

## Collection or Construction Grid

The grid is organized by four result families. R001 records the state-by-category policy-rule vector and design taxonomy. R002 records public approval-risk concentration diagnostics. R003 records ex-ante NielsenIQ policy-rule exposure using aggregate category shares. R004 records boundary diagnostics including SNAP/EBT non-observation, 21/22 approved-state Nielsen coverage, and post-policy response non-constructibility.

## Inputs

Inputs are D001 USDA/FNS public approval materials, D002 state request/implementation/modification documents, D003 MAHA processed policy/event-history files, D004 aggregate NielsenIQ exposure outputs, and D005 state benchmark covariates. The wrapper reads or registers aggregate/public artifacts only.

## Outputs to Register

Register R001 through R004 in `evidence/result_index.csv` before claim audit. Each final claim in `evidence/claim_registry.md` must reference at least one result ID or evidence ID. Do not register post-policy purchase response as a current result.

## Exclusion Rules

Exclude actual SNAP/EBT transaction claims, post-policy demand effects, welfare/equivalent-variation estimates, and causal governor-party approval effects from the current execution protocol. Exclude Hawaii from approved-state Nielsen exposure claims unless a later Nielsen coverage refreeze includes it. Treat broad residual categories such as OTHER_FOOD as sensitivity/bounds rather than hidden preferred exposure.

## Provenance Requirements

Every registered result must identify the MAHA source output path, freeze or build date where available, and whether the output is public aggregate, project-derived, or restricted-data-derived aggregate. Restricted NielsenIQ microdata paths must not be copied into public evidence except as controlled workflow references.

## Claim Boundary

The maximum claim ceiling for current Paper 1 is measurement with supporting descriptive/associational approval-risk diagnostics. The protocol does not support causal policy effects, demand elasticities, welfare effects, or actual SNAP/EBT transaction statements.

## Human Approval Status

G3 was human-approved after review of the discovery/design packet. G4 is not yet approved; it requires execution protocol, pipeline instantiation, main execution, and result/claim provenance registration.
