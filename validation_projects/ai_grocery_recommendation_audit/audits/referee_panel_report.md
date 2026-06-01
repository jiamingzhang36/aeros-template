# Referee Panel Report

## Status

Pass as a referee simulation for a pilot-stage measurement audit. The panel does not recommend treating the current pilot as a finished paper.

## Executive Summary

The project has a credible automation and audit-control structure: idea intake, data scouting, design selection, protocol, pipeline, provenance, claim audit, and bounded pilot outputs are all present. The main weakness is evidence scope. The current C002 claim is appropriately ambiguous and limited to a current-Codex-session pilot. A paper-quality version requires real model-output collection, validated scoring, and robustness execution.

## Reviewer 1: Methods / Measurement

### Main objection

The current pilot uses manually generated current-session outputs and a small prompt grid. It validates the pipeline but not the measurement properties of deployed AI systems.

### Required response

Pre-register a final prompt/persona grid, collect model outputs with timestamp/model metadata, and run the required robustness checklist before marking any claim supported.

### Specific requests

- Increase repetitions per persona/model/prompt cell.
- Report parser rules and unmatched/vague-item handling.
- Separate smoke, pilot, and final result IDs.
- Validate nutrition and affordability scoring against external sources.

## Reviewer 2: Food Policy / SNAP Context

### Main objection

SNAP relevance is plausible but not yet institutionally deep. The current personas are synthetic and do not fully encode benefit timing, local retailer access, household preferences, or eligibility rules.

### Required response

Add a persona-design memo that ties each persona to food policy constraints and explains which claims are about SNAP-relevant scenarios rather than SNAP participants.

### Specific requests

- Clarify whether recommendations are SNAP-eligible foods.
- Add local price/source rules before affordability claims.
- Avoid saying low-income households are harmed unless real-world validation exists.
- Use TFP/SNAP benchmarks as policy reference points, not observed household budgets.

## Reviewer 3: Algorithm Audit / AI Systems

### Main objection

The audit design is reasonable, but current outputs come from one Codex session. The paper cannot generalize to AI systems, grocery recommenders, or LLMs broadly.

### Required response

Define the audited system population: one model, multiple models, or an interface class. Without that, claims must remain limited to the audited session/model.

### Specific requests

- Record model/provider/version/date for every output.
- Add cross-model or cross-run comparison if making broader claims.
- Treat prompt sensitivity as a primary finding risk.
- Include a model/system card style appendix.

## Skeptical Editor

### Main objection

The paper risk is novelty and evidentiary strength. A pipeline demonstration alone is not enough for a publishable empirical paper unless framed as a methods/demo paper.

### Decision guidance

The project can proceed in one of two directions:

1. Methods/demo paper: emphasize AEROS-style human-gated audit automation and use the AI grocery pilot as a worked example.
2. Substantive empirical paper: collect real multi-model outputs, run robustness checks, and support measurement claims with stronger data.

## Required Before Claim Support

- Final prompt/persona protocol approved.
- Real model-output collection completed.
- Nutrition matching and price scoring validated.
- RB01-RB10 robustness checks either run or explicitly waived by human decision.
- Claim registry updated with supported/ambiguous/unsupported status based on final evidence.

## Recommended Next Action

Do not move directly to paper drafting as if the empirical claim is final. Either keep the project as an automation-method validation case, or run a real final measurement collection before manuscript drafting.
