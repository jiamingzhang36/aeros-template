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
