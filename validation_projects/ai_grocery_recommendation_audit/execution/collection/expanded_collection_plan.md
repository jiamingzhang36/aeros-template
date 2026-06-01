# Expanded AI Output Collection Plan

## Purpose

This G11 plan expands the AI grocery recommendation audit beyond the current-Codex-session pilot. The goal is to create a larger, auditable collection grid that can test whether the measurement pipeline remains stable across personas, prompt variants, repeated runs, and model metadata.

This plan does not approve stronger claims. It prepares the collection needed to evaluate whether C002 should remain ambiguous or be proposed for a bounded measurement-claim upgrade after human review.

## Claim Ceiling

The claim ceiling remains measurement. The expanded collection may support a bounded measurement claim only after outputs are collected, validated, registered, and reviewed through a human gate.

The expanded collection cannot support claims about causal effects, real consumer behavior, health outcomes, legal discrimination, nutrition equity, or all deployed AI grocery systems.

## Unit of Observation

One observation is one model-output record for a unique prompt run. Each record must include:

- prompt_id
- persona
- prompt_variant
- model
- run_index
- collected_at
- prompt_text
- output_text
- collection_notes when needed

## Personas

The expanded grid uses four personas:

1. `low_income_snap_single_parent`: SNAP-relevant household with two children, tight weekly budget, limited time, and need for practical groceries.
2. `low_income_snap_senior`: Older adult on a constrained food budget, needs simple preparation and lower-sodium options.
3. `moderate_budget_family`: Moderate-budget household seeking affordable but flexible weekly groceries.
4. `student_low_time_low_budget`: Student with limited time, limited equipment, and a low weekly grocery budget.

These personas are synthetic measurement prompts, not claims about real households.

## Prompt Variants

The grid uses three prompt variants:

1. `A_budget_first`: explicitly prioritizes budget and SNAP-relevant affordability.
2. `B_nutrition_first`: explicitly prioritizes nutrition and meal balance while keeping budget fixed.
3. `C_feasibility_first`: explicitly prioritizes realistic preparation, item specificity, and low ambiguity.

The variants are intended to test prompt sensitivity, not to establish a best prompt.

## Model Scope

The initial expanded grid uses a single model label, `current_codex_session_model`, because this validation project is operating without external provider API keys. If later API collection is approved, the model field should be replaced with provider/model/version identifiers and collection timestamps.

## Repetitions

Each persona-variant cell has one planned run in this first G11 design, yielding 12 prompt-run rows. A later stronger empirical grid should increase repetitions per cell before any claim upgrade is considered.

## Collection Rules

1. Use only approved synthetic persona prompts.
2. Do not include private, restricted, or real household data.
3. Preserve the full prompt text and output text.
4. Preserve model label, timestamp, run index, and prompt variant.
5. Do not rewrite outputs after collection.
6. If a model refuses or returns malformed output, record the refusal or malformed output rather than replacing it silently.

## Exclusion Rules

Exclude a collected record from measurement summaries if:

1. prompt_id is missing or duplicated;
2. model metadata is missing;
3. prompt text is missing;
4. output text is empty;
5. the output cannot be parsed into grocery recommendation content;
6. the collection deviated from the approved prompt grid.

Excluded records should remain in the raw JSONL collection with an exclusion flag or audit note.

## Planned Outputs

The collection task should produce:

- `outputs/audit_runs/expanded_ai_outputs.jsonl`
- `audits/expanded_collection_run_report.md`
- provenance records under `outputs/.provenance/`

The validation task should produce:

- `outputs/tables/expanded_measurement_summary.csv`
- `outputs/tables/expanded_robustness_summary.csv`
- `audits/expanded_result_validation_report.md`
- new result index entries, expected as R004 and R005

## Human Gate Requirement

Completion of this design does not approve output collection. The next task may collect outputs only from this approved grid. Any change to personas, prompt variants, provider/model scope, or claim ceiling requires human review.

## Risks

1. Single-session outputs may still be too narrow for a supported claim.
2. Model identity may be insufficient if no external API/provider metadata is available.
3. Prompt phrasing can influence outputs and should be interpreted as measurement sensitivity.
4. Manual collection can introduce transcription risks.
5. Public release may be blocked by provider terms or uncertainty about generated-output redistribution.

## Recommended Interpretation

This plan is appropriate for moving from a tiny pilot toward a more formal measurement audit. It is not enough by itself to support a final empirical paper.
