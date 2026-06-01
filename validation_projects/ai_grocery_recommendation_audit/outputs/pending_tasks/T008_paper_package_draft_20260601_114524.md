# Manual AEROS Task Prompt

AEROS_AGENT_PROVIDER=manual wrote this prompt instead of calling an agent.

Fill the allowed output files, then run `aeros check <task-contract>`.

```text
You are an AEROS worker agent executing task T008_paper_package_draft (stage: execution).

## Goal
Create or audit the first paper/package draft after internal replication readiness. The draft must connect research question, design, evidence, claim boundary, limitations, and replication status without strengthening claims beyond the approved evidence ceiling.

## You may write ONLY these files
- paper/draft.md
- audits/paper_package_report.md
- agent_runs/

## Forbidden
- Do not strengthen claims beyond the claim registry.
- Do not present pilot outputs as final empirical evidence.
- Do not approve public replication release.
- Do not modify protected definitions or raw data.

## Inputs (read-only context)
--- discovery/idea_memo.md ---
# Idea Memo

## Working Title

Auditing AI Grocery Recommendations Under SNAP-Relevant Household Constraints

## One-Sentence Research Question

Do AI-generated grocery recommendations remain stable, affordable, nutritionally reasonable, and equitable when prompted with realistic low-income and SNAP-relevant household constraints?

## Starting Idea

We audit whether AI-generated grocery recommendations are stable, affordable, nutritionally reasonable, and equitable across realistic household constraints, with special attention to low-income and SNAP-relevant food choice environments.

## Notes

This project is currently approved only for a measurement-audit design. It does not claim causal effects on consumer behavior, health outcomes, or legal discrimination.


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


--- evidence/result_index.csv ---
result_id,output_type,path,script_or_source,description,created_date,linked_claims,notes
R001,table,outputs/tables/measurement_smoke_summary.csv,code/02_analysis/run_measurement_smoke.py,Offline smoke summary for AI grocery recommendation measurement audit pipeline.,2026-06-01,C001,Toy validation output; not final empirical evidence.
R002,table,outputs/tables/pilot_measurement_summary.csv,code/02_analysis/analyze_pilot_outputs.py,Pilot measurement summary for current Codex-session AI grocery recommendation outputs.,2026-06-01,C002,Pilot only; current Codex session; not platform-wide evidence.
R003,table,outputs/tables/pilot_robustness_summary.csv,code/02_analysis/analyze_pilot_outputs.py,Prompt-variant robustness summary for pilot current Codex-session outputs.,2026-06-01,C002,Pilot robustness only; not final robustness suite.


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


--- evidence/evidence_ledger.csv ---
evidence_id,claim_id,evidence_type,source_or_path,description,inspected_by,date_inspected,status,notes
E001,C002,result_bundle,"evidence/result_index.csv; outputs/.provenance/R002.json; outputs/.provenance/R003.json","R002/R003 pilot measurement and prompt-variant robustness outputs with provenance for current-Codex-session pilot.",codex,2026-06-01,inspected,"Supports only ambiguous pilot measurement claim; not final empirical evidence."
E002,C002,robustness_plan,docs/robustness_checklist.md,"Project-specific robustness checklist defining required checks before any real measurement claim can be supported.",codex,2026-06-01,inspected,"Checklist is planned/not executed; supports audit discipline, not substantive findings."
E003,C002,referee_simulation,audits/referee_panel_report.md,"Simulated reviewer objections and required next steps for turning pilot into methods/demo or substantive empirical paper.",codex,2026-06-01,inspected,"Supports human decision-making and limitation framing; not empirical evidence."


--- audits/replication_package_report.md ---
# Replication Package Audit Report

## Task

- Task ID: T007_replication_package
- Stage: execution
- Gate: G9 replication readiness
- Audit date: 2026-06-01
- Project: AI grocery recommendation audit pilot

## Bottom Line

The project has enough structure for an internal replication package audit, but it is not yet release-ready as a public replication package.

The current package can support internal reruns of the pilot measurement outputs because the core analysis scripts, registered outputs, and provenance files are present. However, the replication-facing documentation still contains template placeholders, and the package does not yet provide a finalized data availability statement, environment setup narrative, or public release instructions.

Recommended gate action: approve G9 only as an internal replication-readiness checkpoint, not as approval to publish or distribute the replication package.

## Files Reviewed

| Area | Reviewed artifact | Status | Notes |
|---|---|---|---|
| Replication README | `README_replication.md` | Needs revision before release | Contains multiple `TBD` fields and still describes `code/99_make_all.py` as a default placeholder. |
| Build entry point | `Makefile` | Present | Provides `pipeline`, `checks`, and related maintenance targets. Some targets assume local `checks/` are present, while this validation project currently relies on the root template checks via `PYTHONPATH` / harness configuration. |
| Environment | `environment.yml`, `requirements.txt` | Present | Minimal Python/PyYAML environment is sufficient for the current pilot scripts, but the release README should state OS, Python version, package manager, and expected runtime explicitly. |
| Master pipeline | `code/99_make_all.py` | Present | Generic delegated pipeline wrapper is present and syntactically checkable. Public release should document any configured delegated command. |
| Data documentation | `data/README_data.md` | Needs revision before release | Raw-data protection policy is present, but source log and rebuild instructions remain `TBD`. |
| Registered outputs | `evidence/result_index.csv` | Present | Registers R001, R002, and R003 with generating scripts and linked claims. |
| Provenance | `outputs/.provenance/R001.json`, `R002.json`, `R003.json` | Present | Each registered result has a matching provenance file. |
| Paper artifact | `paper/draft.md` | Present | Used only as an audit-facing draft artifact at this stage. |

## Reproducibility Assessment

### What is reproducible internally

1. R001 is traceable to `code/02_analysis/run_measurement_smoke.py` and `outputs/tables/measurement_smoke_summary.csv`.
2. R002 is traceable to `code/02_analysis/analyze_pilot_outputs.py` and `outputs/tables/pilot_measurement_summary.csv`.
3. R003 is traceable to `code/02_analysis/analyze_pilot_outputs.py` and `outputs/tables/pilot_robustness_summary.csv`.
4. The result index links outputs to claims and distinguishes toy smoke output from current-Codex-session pilot output.
5. Provenance files exist for all registered results, which supports audit trail reconstruction.

### What is not release-ready

1. `README_replication.md` still has placeholder fields for project overview, computational requirements, data availability, expected outputs, and limitations.
2. `data/README_data.md` still has placeholder fields in the source log and rebuild instructions.
3. The Makefile assumes a local `checks/` directory, but this validation project intentionally uses the root AEROS template engine/checks rather than carrying a copied local harness.
4. The current pilot evidence is bounded to the current Codex-session output collection and does not support claims about deployed AI systems, all grocery recommenders, real consumers, nutrition fairness, or platform-wide behavior.
5. Public replication would require a clearer statement about whether manual AI outputs can be redistributed, regenerated, or replaced by a scripted API collection protocol.

## Pipeline Entry Point Assessment

The project has a master pipeline entry point at `code/99_make_all.py`. This script delegates to a configured project pipeline via `project_manifest.yml` or environment variables. That is appropriate for the AEROS template architecture because it keeps `check_pipeline_runs.py` project-agnostic.

For this validation project, the main reproducible outputs are currently generated by the pilot analysis scripts rather than a fully locked, public one-command release pipeline. Before public release, the project should document one canonical command sequence, expected outputs, and expected runtime.

## Data Access and Release Risks

No restricted raw data were exposed or modified during this audit. The current project primarily uses manually collected AI recommendation outputs for a pilot measurement exercise.

Release blockers remain:

1. Data source log is incomplete.
2. Data access instructions are incomplete.
3. Redistribution status of manual AI outputs is not documented.
4. Replacement/regeneration protocol for AI outputs is not finalized.

## Claim Ceiling at G9

The replication package audit does not raise the claim ceiling.

Allowed claim after this checkpoint:

- The project has an internally auditable pilot replication structure for the current-Codex-session AI grocery recommendation audit outputs.

Not allowed after this checkpoint:

- The project is fully public-replication ready.
- The findings generalize to deployed AI systems or all grocery recommendation systems.
- The package supports final empirical claims about real consumer welfare, nutrition fairness, or platform behavior.

## Recommended Human Decision

Approve G9 if the intended meaning is:

- Internal replication structure is adequate for continuing toward paper/package drafting.
- Registered pilot outputs have provenance and generating scripts.
- Remaining release blockers are explicitly documented.

Block G9 if the intended meaning is:

- The replication package must already be public-release ready.
- All `TBD` fields in replication/data documentation must be resolved before proceeding.
- A one-command full regeneration pipeline must be finalized before paper drafting.

## Required Follow-Up Before Public Release

1. Replace `TBD` fields in `README_replication.md` with project-specific instructions.
2. Replace `TBD` fields in `data/README_data.md` with source, access, restriction, and rebuild details.
3. Decide whether manual AI outputs are release artifacts, private audit artifacts, or regenerated-only artifacts.
4. Add a documented one-command release workflow or explicitly explain why manual collection is part of the protocol.
5. Confirm that every manuscript table or claim cites a registered result ID with provenance.

## Audit Conclusion

G9 can be treated as passed for internal AEROS workflow purposes, with a clear boundary: this is a replication-readiness audit checkpoint, not public replication package approval.


--- outputs/tables/ (DIRECTORY) ---
- outputs/tables/.gitkeep
- outputs/tables/measurement_smoke_summary.csv
- outputs/tables/pilot_measurement_summary.csv
- outputs/tables/pilot_robustness_summary.csv

--- paper/ (DIRECTORY) ---
- paper/.gitkeep
- paper/draft.md

When done, the file(s) above must pass the AEROS checks. Do not explain; just produce conformant files.
```
