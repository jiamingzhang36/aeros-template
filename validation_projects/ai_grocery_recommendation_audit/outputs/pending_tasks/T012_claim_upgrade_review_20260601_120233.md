# Manual AEROS Task Prompt

AEROS_AGENT_PROVIDER=manual wrote this prompt instead of calling an agent.

Fill the allowed output files, then run `aeros check <task-contract>`.

```text
You are an AEROS worker agent executing task T012_claim_upgrade_review (stage: execution).

## Goal
Review whether the expanded G11 evidence can justify proposing a bounded upgrade to the active measurement claim. The task may recommend options, but it must not mark any claim supported or approve stronger paper language.

## You may write ONLY these files
- audits/claim_upgrade_review_report.md
- agent_runs/

## Forbidden
- Do not mark C002 supported.
- Do not edit the paper draft.
- Do not approve final conclusions or submission.
- Do not modify protected definitions.

## Inputs (read-only context)
--- evidence/claim_registry.md ---
# Claim Registry

## Claim Types

- descriptive
- measurement
- associational
- causal
- mechanism
- external-validity
- policy-translation
- forecast

## Registry

| Claim ID | Claim | Type | Status | Evidence ID(s) | Result ID(s) | Boundary / Limitation | Approved |
|---|---|---|---|---|---|---|---|
| C001 | The execution pipeline can produce a bounded measurement summary for an AI grocery recommendation audit using the selected O1 design. | descriptive | retired |  | R001 | Smoke validation only; retired before claim approval because R002/R003 supersede it for pilot validation. | no |
| C002 | In a small current-Codex-session pilot, the audit pipeline measured affordability, vagueness, and nutrition-flag summaries across low-income SNAP-relevant and moderate-budget personas. | measurement | ambiguous |  | R002;R003 | Pilot outputs from this Codex session only; not evidence about deployed AI systems, all models, or real consumers. Expanded G11 outputs may inform a future human-reviewed update but do not automatically upgrade this claim. | no |

## Status Values

- draft
- supported
- ambiguous
- unsupported
- retired

## Rules

- A claim cannot be marked supported without at least one evidence ID or result ID.
- A causal claim requires a method card that supports causal language.
- A forecast claim requires explicit forecast validation or must remain unsupported.
- Policy translation must stay within the protected sample, geography, period, and outcome definitions.


--- evidence/result_index.csv ---
result_id,output_type,path,script_or_source,description,created_date,linked_claims,notes
R001,table,outputs/tables/measurement_smoke_summary.csv,code/02_analysis/run_measurement_smoke.py,Offline smoke summary for AI grocery recommendation measurement audit pipeline.,2026-06-01,C001,Toy validation output; not final empirical evidence.
R002,table,outputs/tables/pilot_measurement_summary.csv,code/02_analysis/analyze_pilot_outputs.py,Pilot measurement summary for current Codex-session AI grocery recommendation outputs.,2026-06-01,C002,Pilot only; current Codex session; not platform-wide evidence.
R003,table,outputs/tables/pilot_robustness_summary.csv,code/02_analysis/analyze_pilot_outputs.py,Prompt-variant robustness summary for pilot current Codex-session outputs.,2026-06-01,C002,Pilot robustness only; not final robustness suite.
R004,table,outputs/tables/expanded_measurement_summary.csv,outputs/audit_runs/expanded_ai_outputs.jsonl,Expanded validation measurement summary for current Codex-session outputs.,2026-06-01,C002,Expanded validation collection only; no supported-claim upgrade without human approval.
R005,table,outputs/tables/expanded_robustness_summary.csv,outputs/audit_runs/expanded_ai_outputs.jsonl,Expanded prompt-variant robustness summary for current Codex-session outputs.,2026-06-01,C002,Expanded validation robustness only; not final robustness suite.


--- outputs/tables/expanded_measurement_summary.csv ---
persona,runs,mean_affordability_ratio,max_affordability_ratio,mean_vague_items,mean_nutrition_flags,within_budget_share
low_income_snap_senior,3,0.973,1.0,0.667,0.0,1.0
low_income_snap_single_parent,3,0.94,0.96,0.667,0.0,1.0
moderate_budget_family,3,0.96,0.99,1.333,0.0,1.0
student_low_time_low_budget,3,0.973,1.0,1.333,0.0,1.0


--- outputs/tables/expanded_robustness_summary.csv ---
persona,prompt_variant,runs,mean_affordability_ratio,mean_nutrition_flags,mean_vague_items
low_income_snap_senior,A_budget_first,1,0.96,0.0,1.0
low_income_snap_senior,B_nutrition_first,1,1.0,0.0,1.0
low_income_snap_senior,C_feasibility_first,1,0.96,0.0,0.0
low_income_snap_single_parent,A_budget_first,1,0.93,0.0,1.0
low_income_snap_single_parent,B_nutrition_first,1,0.93,0.0,1.0
low_income_snap_single_parent,C_feasibility_first,1,0.96,0.0,0.0
moderate_budget_family,A_budget_first,1,0.93,0.0,1.0
moderate_budget_family,B_nutrition_first,1,0.99,0.0,2.0
moderate_budget_family,C_feasibility_first,1,0.96,0.0,1.0
student_low_time_low_budget,A_budget_first,1,0.93,0.0,0.0
student_low_time_low_budget,B_nutrition_first,1,1.0,0.0,2.0
student_low_time_low_budget,C_feasibility_first,1,0.99,0.0,2.0


--- audits/expanded_result_validation_report.md ---
# Expanded Result Validation Report

## Task

- Task ID: T011_expanded_result_validation
- Stage: execution
- Gate: G11 expanded collection
- Validation date: 2026-06-01

## Bottom Line

The expanded current-Codex-session validation collection has been converted into two registered result artifacts: R004 and R005. These outputs improve the internal measurement workflow beyond the earlier tiny pilot, but they do not automatically upgrade C002 to a supported claim.

## Registered Results

| Result ID | Artifact | Role |
|---|---|---|
| R004 | `outputs/tables/expanded_measurement_summary.csv` | Persona-level expanded measurement summary |
| R005 | `outputs/tables/expanded_robustness_summary.csv` | Prompt-variant expanded robustness summary |

## Claim Ceiling

The claim ceiling remains measurement. C002 remains ambiguous until a human gate explicitly approves a claim update. The expanded collection is still bounded to current-Codex-session validation outputs and should not be described as evidence about deployed AI systems, all models, real consumers, or final nutrition outcomes.

## Human Approval Requirement

Human approval is required before any of the following actions:

1. Marking C002 as supported.
2. Rewriting the paper draft to make stronger empirical claims.
3. Treating R004/R005 as final manuscript evidence.
4. Publishing the collection as a public replication package.

## Validation Notes

The expanded output file contains 12 records matching the approved G11 prompt grid. Each record includes prompt ID, persona, prompt variant, model label, run index, timestamp, prompt text, and output text. R004 and R005 have provenance records and are registered in the result index.

## Recommendation

Approve G11 only if the intended meaning is that the expanded validation collection is internally registered and ready for human review. Do not approve G11 as a final claim upgrade.


--- paper/draft.md ---
# Auditing AI Grocery Recommendations Under SNAP-Relevant Household Constraints: Paper Package Draft v0

## Abstract

This draft describes a bounded measurement-audit pilot for AI-generated grocery recommendations under SNAP-relevant household constraints. The current evidence package is limited to a small current-Codex-session pilot and should be read as a method-demo artifact, not a final empirical paper. The active claim is C002: in this pilot, the audit pipeline measured affordability, vagueness, and nutrition-flag summaries across low-income SNAP-relevant and moderate-budget personas. The draft does not claim general behavior of production recommendation tools, household outcomes, legal discrimination, or broad platform performance.

## Research Question

The project asks whether AI-generated grocery recommendations can be audited for stability, affordability, nutritional reasonableness, and equity-relevant feasibility when prompts include realistic household constraints. The motivating case is grocery planning for low-income and SNAP-relevant food environments, where recommendations may look helpful in natural language while still failing budget, feasibility, or nutrition-screening checks.

At this stage, the research question is operational rather than definitive: can an AEROS-governed workflow turn the idea into a traceable measurement protocol, pilot outputs, registered results, and bounded claims without letting the paper outrun the evidence?

## Design and Method

The approved design is O1, a repeated black-box measurement audit. The unit of observation is a model-run/persona/repetition record. Personas encode budget pressure, household context, and food-access constraints. The protocol compares generated grocery recommendations across personas and prompt variants, then scores outputs using documented affordability and nutrition-flag measures.

The method card sets the earned claim ceiling at measurement. There is no causal identification design in this package. The current pilot uses two personas, `low_income_snap` and `moderate_budget`, two prompt variants, and repeated runs collected in the current Codex session. The analysis scripts parse the pilot outputs into registered summary tables.

## Evidence and Results

The registered result index contains three outputs. R001 is a smoke-test output used to confirm that the measurement pipeline can produce a bounded summary table. R002 is the main pilot measurement summary for current-Codex-session outputs. R003 is a prompt-variant robustness summary for the same pilot.

In R002, the low-income SNAP-relevant persona has four pilot runs, a mean affordability ratio of 0.992, a maximum affordability ratio of 1.018, a mean vague-item count of 0.0, a mean nutrition-flag count of 0.5, and a within-budget share of 0.75. The moderate-budget persona has four pilot runs, a mean affordability ratio of 0.915, a maximum affordability ratio of 0.940, a mean vague-item count of 0.0, a mean nutrition-flag count of 0.0, and a within-budget share of 1.00.

In R003, prompt-variant summaries show that the low-income SNAP-relevant persona differs across variants in mean affordability ratio and nutrition flags. Variant A has a mean affordability ratio of 1.004 and mean nutrition flags of 1.0, while Variant B has a mean affordability ratio of 0.980 and mean nutrition flags of 0.0. The moderate-budget persona is more stable in this tiny pilot, with mean affordability ratios of 0.917 and 0.913 across variants and no nutrition flags.

These numbers are useful for demonstrating measurement mechanics. They are not final findings. They show that the workflow can register outputs, preserve provenance, and maintain a clear claim boundary.

## Claim Boundary

The active claim is C002. Its status is ambiguous, not supported. It says that in a small current-Codex-session pilot, the audit pipeline measured affordability, vagueness, and nutrition-flag summaries across low-income SNAP-relevant and moderate-budget personas.

This draft does not treat C002 as a final claim. The result bundle supports internal review of the measurement workflow, not broad conclusions about AI recommendation quality. Any later claim upgrade would require a larger approved collection grid, locked parsing rules, documented model metadata, and completed robustness checks.

## Limitations and Scope

The pilot is intentionally small. It uses two personas, two prompt variants, and outputs generated within one Codex-session context. It does not establish population-level behavior, welfare effects, health outcomes, legal categories, or market-wide grocery recommendation performance.

The pilot also depends on current parsing and scoring rules. Price matching, nutrition matching, item specificity, and prompt phrasing remain important threats. The robustness checklist identifies additional checks that must be completed before stronger paper language would be appropriate.

## Replication and Package Status

The internal replication structure is adequate for continuing toward paper/package drafting. R001, R002, and R003 are registered in `evidence/result_index.csv`; each has a generating script and a provenance file under `outputs/.provenance/`. The G9 replication audit concludes that the package is internally auditable but not public-release ready.

Before a public replication package, the project still needs a completed replication README, a completed data README, a final data availability statement, and a clear rule for whether manual AI outputs are released, regenerated, or treated as private audit artifacts.

## Next Drafting Steps

The next version should decide whether the paper is primarily a methods/demo paper or an empirical audit paper. A methods/demo version can center the AEROS-governed workflow and claim discipline. An empirical version would need a larger pre-approved output collection, stronger robustness evidence, and a completed release plan.

For now, the responsible interpretation is narrow: AEROS has produced a traceable paper-package draft around C002 while keeping the evidence ceiling intact. This is a useful checkpoint, not the end of the research loop.


When done, the file(s) above must pass the AEROS checks. Do not explain; just produce conformant files.
```
