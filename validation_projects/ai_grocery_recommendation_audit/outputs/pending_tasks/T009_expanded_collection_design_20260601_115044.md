# Manual AEROS Task Prompt

AEROS_AGENT_PROVIDER=manual wrote this prompt instead of calling an agent.

Fill the allowed output files, then run `aeros check <task-contract>`.

```text
You are an AEROS worker agent executing task T009_expanded_collection_design (stage: execution).

## Goal
Design the expanded AI-output collection that can move the project beyond the current-Codex-session pilot. Specify personas, prompt variants, models, repetitions, metadata, exclusion rules, and collection risks without running collection yet.

## You may write ONLY these files
- execution/collection/expanded_collection_plan.md
- outputs/audit_runs/expanded_prompt_grid.csv
- audits/expanded_collection_design_report.md
- agent_runs/

## Forbidden
- Do not collect new AI outputs in this design task.
- Do not strengthen claims beyond the claim registry.
- Do not modify raw data or protected definitions.

## Inputs (read-only context)
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


--- docs/method_card.md ---
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


--- execution/protocol/main_execution_protocol.md ---
---
status: filled
protocol_id: main_execution_protocol
approved_gate: G3
claim_ceiling: measurement
result_ids:
  - R001
  - R002
  - R003
---

# Main Execution Protocol

## Observation Unit

The smoke execution observation unit is a synthetic model-run/persona record. Each record represents one offline toy recommendation response associated with a household persona and repetition number. In a final execution run, the observation unit must become a real model/provider/prompt/persona/timestamp/repetition tuple.

## Collection or Construction Grid

The smoke grid uses two personas, `low_income_snap` and `moderate_budget`, with two repeated runs each. This grid is intentionally tiny and hard-coded to validate pipeline mechanics only. The final grid must be separately approved before collecting real AI outputs.

## Inputs

Inputs are the approved O1 measurement design, the filled method card, and the hard-coded toy response records in `code/02_analysis/run_measurement_smoke.py`. No raw data are downloaded or written.

## Outputs to Register

The execution records `R001` for smoke validation, plus `R002` and `R003` for the current-Codex-session pilot measurement and prompt-variant robustness summaries. Each registered result must have a CSV output, provenance JSON, and a bounded claim link in `evidence/claim_registry.md`.

## Exclusion Rules

Exclude smoke records from manuscript-facing empirical claims. Do not interpret toy values as real AI recommendation behavior. If any future run lacks model metadata, prompt text, persona id, timestamp, or parsing rule version, exclude it from supported claims.

## Provenance Requirements

Every registered output must have a result ID, an entry in `evidence/result_index.csv`, and a matching JSON record under `outputs/.provenance/`. The provenance record must identify the script or source and include a SHA-256 hash of the output file.

## Claim Boundary

Allowed claims are limited to smoke/pilot measurement statements. R001 can only support pipeline-smoke validation. R002/R003 can support an ambiguous pilot measurement claim about current-Codex-session outputs only. None can support platform-wide claims about deployed AI systems, real consumers, grocery affordability, nutrition quality, or equity.

## Human Approval Status

Status: approved for smoke execution after G3 design approval; not approved for final empirical collection.


--- docs/robustness_checklist.md ---
---
status: filled
---

# Robustness Checklist

## Status

filled

## Scope

This checklist applies to the selected O1 measurement audit of AI grocery recommendations. It defines checks required before any claim can move from `draft` to `supported`. The current R001 output is smoke validation only; these checks are not yet run.

## Required Before Supported Claims

| ID | Threat addressed | Rerun or sensitivity rule | Expected output | Required before supported claim? | Status |
|---|---|---|---|---|---|
| RB01 | Prompt sensitivity | Re-run the audit with at least two semantically equivalent prompt phrasings per persona while preserving the same constraint information. | Prompt-variant summary table with changes in affordability ratio, nutrition flags, vague item share, and stability. | yes | planned |
| RB02 | Stochastic output instability | Run at least five repetitions per persona/model/prompt cell or justify a smaller number if provider constraints apply. | Within-cell dispersion table for basket overlap and score variance. | yes | planned |
| RB03 | Item parsing ambiguity | Re-score outputs under strict parsing and permissive parsing rules; strict parsing drops vague items, permissive parsing maps them to closest plausible grocery items. | Parsing-sensitivity table showing outcome movement. | yes | planned |
| RB04 | Nutrition matching error | Match recommended items using FoodData Central primary mapping and an alternate Open Food Facts or manual-coded mapping where available. | Nutrition-score comparison table and unmatched-item log. | yes | planned |
| RB05 | Affordability benchmark sensitivity | Compute affordability ratio using TFP/SNAP benchmark and an alternate conservative budget threshold. | Affordability-threshold sensitivity table. | yes | planned |
| RB06 | Retail price source risk | If retailer prices are used, repeat scoring with a second store, ZIP code, or proxy price source when legally and technically feasible. | Price-source sensitivity table and source-access note. | yes for final affordability claims | planned |
| RB07 | Persona construction dependence | Re-run core summaries excluding any persona whose constraints are underspecified or not policy-relevant. | Persona-exclusion sensitivity table. | yes | planned |
| RB08 | Hidden model/version updates | Record model/provider/timestamp metadata and compare summaries across collection batches if collection spans multiple days. | Batch comparison table with version/timestamp notes. | yes for multi-day collection | planned |
| RB09 | Smoke/final contamination | Confirm that smoke rows are excluded from final result IDs and final claims. | Audit log showing smoke result IDs excluded from supported empirical claims. | yes | planned |
| RB10 | Claim overreach | Re-run claim audit after robustness outputs exist and verify no claim exceeds measurement ceiling. | Claim audit report with no overclaim findings. | yes | planned |

## Optional Diagnostic Checks

| ID | Threat addressed | Rerun or sensitivity rule | Expected output | Required before supported claim? | Status |
|---|---|---|---|---|---|
| RO01 | Model choice dependence | Run the same prompt/persona grid across multiple AI systems if access permits. | Cross-model comparison table. | no, unless making cross-model claims | planned |
| RO02 | Cultural food fit | Add a small set of culturally specific household preferences and inspect whether recommendations remain feasible. | Qualitative feasibility memo and coded flags. | no, unless making cultural-fit claims | planned |
| RO03 | Quantity/package-size uncertainty | Compare scoring when missing quantities are imputed low, medium, and high. | Quantity-imputation sensitivity table. | no, but recommended | planned |

## Reporting Discipline

- Robustness checks must be reported as robustness checks, not cherry-picked replacements for the main result.
- Null, ambiguous, or unfavorable robustness results must remain in the audit record.
- Smoke outputs must remain labeled as smoke and cannot support final empirical claims.
- Descriptive and measurement language must not be rewritten as causal language.

## Human Review Trigger

Human review is required before marking any claim `supported`, before using retailer price collection at scale, before adding a new model provider, or before changing the claim ceiling.


--- audits/paper_package_report.md ---
# Paper Package Audit Report

## Task

- Task ID: T008_paper_package_draft
- Stage: execution
- Gate: G10 paper package draft
- Audit date: 2026-06-01
- Project: AI grocery recommendation audit pilot

## Bottom Line

The first paper/package draft is adequate for an internal G10 checkpoint. It connects the research question, selected measurement design, registered evidence, claim boundary, limitations, and replication status without upgrading the active claim beyond the approved ceiling.

Recommended gate action: approve G10 if the intended meaning is that the project now has a bounded paper-package draft suitable for human review and next-stage revision planning. Do not approve G10 as final manuscript approval or public package release.

## Draft Coverage

| Required component | Status | Notes |
|---|---|---|
| Research question | Present | States the AI grocery recommendation audit question and frames the current checkpoint as operational. |
| Design/method | Present | Identifies O1 repeated black-box measurement audit and states that no causal identification design is claimed. |
| Evidence/results | Present | Summarizes R001/R002/R003 and reports pilot values from R002/R003. |
| Claim boundary | Present | References C002, states it is ambiguous, and says it is not final. |
| Limitations | Present | Notes tiny pilot size, current Codex-session scope, parsing/scoring threats, and need for robustness. |
| Replication status | Present | Carries forward G9 finding that internal auditability exists but public release is not approved. |

## Claim Discipline

The draft preserves the measurement claim ceiling. It does not mark C002 as supported and does not convert pilot numbers into final findings. The paper language describes the current artifact as a method-demo / internal review checkpoint.

The draft explicitly avoids stronger claims about broad recommendation systems, household outcomes, legal categories, or market-level performance.

## Evidence Mapping

| Result ID | Used in draft? | Use |
|---|---|---|
| R001 | Yes | Described as smoke-test output for pipeline mechanics. |
| R002 | Yes | Main pilot measurement summary with persona-level affordability, vagueness, nutrition-flag, and within-budget values. |
| R003 | Yes | Prompt-variant robustness summary for the same pilot. |

## Remaining Blockers Before Stronger Paper Claims

1. C002 remains ambiguous and unapproved as a supported claim.
2. The collection grid is too small for a substantive empirical paper.
3. Manual AI output collection needs a documented release/regeneration policy.
4. Replication and data README files still contain placeholder fields.
5. Robustness checks are planned but not sufficient for upgraded claims.

## Recommended Human Review Questions

1. Should the next paper version be framed as a methods/demo paper or as preparation for a larger empirical audit?
2. Is C002 acceptable as the central bounded claim for this draft stage?
3. Should G11 focus on manuscript revision, expanded data collection, or public replication-package hardening?

## Audit Conclusion

G10 can pass as a paper/package draft checkpoint. The draft is readable, traceable to registered results, and appropriately bounded. It should not be treated as final manuscript approval.


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
| C002 | In a small current-Codex-session pilot, the audit pipeline measured affordability, vagueness, and nutrition-flag summaries across low-income SNAP-relevant and moderate-budget personas. | measurement | ambiguous |  | R002;R003 | Pilot outputs from this Codex session only; not evidence about deployed AI systems, all models, or real consumers. | no |

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


When done, the file(s) above must pass the AEROS checks. Do not explain; just produce conformant files.
```
