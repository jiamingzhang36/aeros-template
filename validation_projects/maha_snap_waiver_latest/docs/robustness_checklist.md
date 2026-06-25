---
status: filled
stage: G5_robustness_plan
claim_ceiling: descriptive_or_associational
do_not_strengthen_claims: true
---
# Robustness Checklist

This checklist defines robustness and sensitivity work for Paper 1. It does not
run checks, choose specifications based on significance, or upgrade the claim
ceiling. Current claims remain descriptive or associational.

## Required Before Submission Claims

| ID | Result family | Threat addressed | Exact rerun or sensitivity rule | Expected output | Required before supported claim? |
| --- | --- | --- | --- | --- | --- |
| RB01 | R001 policy-rule measurement | Single-coder subjectivity in Layer 1/Layer 2 waiver coding | MG second-coder independently codes approved-state Layer 1 features and/or Layer 2 dimensions using the same codebook; report agreement, weighted kappa/alpha where feasible, disagreements, and adjudication rule | `outputs/intercoder/second_coder_reliability.*` plus appendix disagreement log | Yes for strong policy-measurement claims |
| RB02 | R001 policy-rule measurement | Composite index arbitrariness | Recompute design rankings under component-only reporting, equal-weight index, and leave-one-dimension-out index; compare rank correlations and identify states that move materially | `outputs/design_sensitivity/design_index_weight_sensitivity.*` | Yes for claims using design_index ranks |
| RB03 | R001 policy-rule measurement | Request-document missingness may overstate request-to-approval preservation | Report evidence-grade denominators separately: full paired request/approval documents, USDA-summary-only cases, and full 22-state public approval record; provide worst/best-case preservation bounds for missing request-side definitions | `outputs/stage_models/request_document_bounds.*` | Yes for approval-stage preservation claims |
| RB04 | R002 approval-risk concentration | Federal-side endogeneity and state-side selection confound governor-party partition | Keep exact 2x2 approval-risk table as headline; rerun sparse/Firth diagnostics with quarter, obesity/SNAP participation, timing/document-availability benchmarks; label all as descriptive diagnostics | `outputs/stage_models/approval_concentration_diagnostics.*` | Yes for approval concentration language |
| RB05 | R002 approval-risk concentration | Sparse events and unstable Wald intervals | Prefer exact/Fisher results and profile-likelihood or penalized-likelihood intervals where available; do not headline unstable Wald intervals | `outputs/stage_models/profile_likelihood_or_exact_ci.*` | Yes if model-based ORs are displayed |
| RB06 | R003 Nielsen exposure | Scanner-category ambiguity for broad/taxable/residual food language | Report strict/preferred and broad-inclusive exposure as bounds; explicitly flag Iowa/Tennessee/other broad-policy states where residual categories shift exposure materially | `outputs/nielsen_exposure/exposure_bounds_sensitivity.*` | Yes for Nielsen headline exposure claims |
| RB07 | R003 Nielsen exposure | Low-income proxy is not actual SNAP/EBT participation | Report baseline income-eligible, conservative income-eligible, and low-income-alt exposure; label all as proxy exposure and never as observed SNAP transaction incidence | `outputs/nielsen_exposure/proxy_definition_sensitivity.*` | Yes for all Nielsen claims |
| RB08 | R003 Nielsen exposure | 21/22 approved-state Nielsen coverage may be misread as full approved-state coverage | Reproduce all approved-state Nielsen tables with explicit coverage column and footnote excluding Hawaii; avoid approved-state denominators that silently imply 22 Nielsen-covered states | `outputs/nielsen_exposure/coverage_denominator_check.*` | Yes for all approved-state Nielsen claims |
| RB09 | R003 Nielsen exposure | Household-level sampling uncertainty is not yet reported | When controlled Nielsen DuckDB is available, run household-cluster bootstrap for aggregate exposure/incidence intervals without exporting household rows | `outputs/nielsen_exposure/table_nielsen_uncertainty_ci.*` | Yes before journal submission of precise exposure estimates |
| RB10 | R003 Nielsen exposure | External validity of UPC/category mapping | Compare pooled category shares to public benchmarks such as USDA/FNS Foods Typically Purchased by SNAP Households, FoodAPS, WIC/Nielsen Homescan, and relevant RCT baskets; treat as construct-validity check only | `outputs/nielsen_exposure/table_nielsen_external_benchmark.*` | Medium priority; required if benchmark claims remain in text |
| RB11 | R004 boundary diagnostics | Target implementation dates may be misread as observed rollout | Rename or caption timing outputs as target/planned implementation unless observed implementation is verified; add state-level realization status where available | `outputs/implementation/target_vs_observed_implementation_check.*` | Yes for implementation timing claims |
| RB12 | R004 boundary diagnostics | Future demand/welfare language may leak into Paper 1 | Search manuscript/poster/appendix for prohibited phrases: causal effect, demand elasticity, welfare effect, actual SNAP transaction, observed EBT incidence; revise to ex-ante/descriptive language | `outputs/logs/claim_boundary_language_scan.*` | Yes before submission package |

## Recommended But Not Claim-Critical

| ID | Result family | Threat addressed | Exact rerun or sensitivity rule | Expected output | Required before supported claim? |
| --- | --- | --- | --- | --- | --- |
| RB13 | R002 approval-risk concentration | Timing may mechanically drive approval concentration | Add request/public-visibility quarter partitions and leave-one-quarter diagnostics; keep exact table primary | `outputs/stage_models/quarter_sensitivity.*` | No; useful robustness |
| RB14 | R003 Nielsen exposure | Projection-factor weighting may alter exposure level | Report unweighted household-panel and projection-weighted aggregate exposure side by side; explain which is headline and why | `outputs/nielsen_exposure/weighted_unweighted_comparison.*` | Recommended for journal version |
| RB15 | R003 Nielsen exposure | One broad state could drive design-exposure association | Leave-one-approved-state-out correlation between design scope and strict exposure; do not interpret as causal validation | `outputs/nielsen_exposure/design_exposure_leave_one_out.*` | Recommended for appendix |
| RB16 | R004 future extension | Substitution/leakage appendix could be misread as causal demand | Keep historical co-movement/leakage-risk profile in appendix only; do not call it elasticity or policy response | `outputs/nielsen_exposure/historical_leakage_profile.*` | No for Paper 1 main claims |

## Language Rules

- Descriptive: "rules differ", "public approvals are concentrated", "ex-ante exposure would cover".
- Associational: "approval concentration is associated with governor-party partition within the approval-risk window".
- Prohibited for current Paper 1: "causes approval", "reduces purchases", "demand effect", "welfare effect", "actual SNAP/EBT transaction incidence".

## Gate Status

G5 can proceed once this checklist is filed. The checklist is a plan, not a
completed robustness package. Items RB01, RB03, RB04, RB06, RB07, RB08, RB09,
and RB12 are the highest-return pre-submission blockers.
