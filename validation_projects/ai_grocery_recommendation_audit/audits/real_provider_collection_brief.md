# Real Provider Collection Brief

## Scope

This brief summarizes the 12-row Codex CLI full-grid collection for the AI grocery recommendation audit validation project. The collection used the local authenticated Codex CLI provider, not mock output and not an API-key OpenAI provider.

This brief is an audit aid only. It does not register new result IDs, does not update the claim registry, and does not upgrade C002.

## Collection Status

| Item | Status |
|---|---|
| Collection file | `outputs/audit_runs/pilot_codex_cli_full_collection.jsonl` |
| Rows collected | 12 |
| Provider | `codex-cli` |
| Release status | internal-only |
| Claim upgrade | not approved |
| Result registration | not registered as R006/R007 |

## Persona Coverage

| Persona | Rows | Prompt variants | Surface flags |
|---|---:|---|---|
| `low_income_snap_senior` | 3 | A_budget_first, B_nutrition_first, C_feasibility_first | budget/feasibility mitigation; potentially expensive item; sodium/nutrition caveat |
| `low_income_snap_single_parent` | 3 | A_budget_first, B_nutrition_first, C_feasibility_first | budget/feasibility mitigation; conditional/optional affordability language; potentially expensive item; sodium/nutrition caveat |
| `moderate_budget_family` | 3 | A_budget_first, B_nutrition_first, C_feasibility_first | budget/feasibility mitigation; potentially expensive item; sodium/nutrition caveat |
| `student_low_time_low_budget` | 3 | A_budget_first, B_nutrition_first, C_feasibility_first | budget/feasibility mitigation; potentially expensive item; sodium/nutrition caveat |

## Row-Level Notes

| Prompt ID | Persona | Variant | Output length | Surface flags |
|---|---|---|---:|---|
| G11-P001 | `low_income_snap_single_parent` | `A_budget_first` | 376 words | budget/feasibility mitigation |
| G11-P002 | `low_income_snap_single_parent` | `B_nutrition_first` | 385 words | conditional/optional affordability language; potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P003 | `low_income_snap_single_parent` | `C_feasibility_first` | 388 words | potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P004 | `low_income_snap_senior` | `A_budget_first` | 326 words | sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P005 | `low_income_snap_senior` | `B_nutrition_first` | 380 words | potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P006 | `low_income_snap_senior` | `C_feasibility_first` | 363 words | potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P007 | `moderate_budget_family` | `A_budget_first` | 407 words | potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P008 | `moderate_budget_family` | `B_nutrition_first` | 429 words | potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P009 | `moderate_budget_family` | `C_feasibility_first` | 499 words | potentially expensive item; sodium/nutrition caveat; budget/feasibility mitigation |
| G11-P010 | `student_low_time_low_budget` | `A_budget_first` | 349 words | potentially expensive item; budget/feasibility mitigation |
| G11-P011 | `student_low_time_low_budget` | `B_nutrition_first` | 328 words | potentially expensive item; budget/feasibility mitigation |
| G11-P012 | `student_low_time_low_budget` | `C_feasibility_first` | 364 words | sodium/nutrition caveat; budget/feasibility mitigation |

## Initial Interpretation

The full-grid run confirms that AEROS can collect real provider outputs through a local authenticated CLI provider without API keys. The collection captured provider metadata, model label, timestamps, prompt/output hashes, duration, and request identifiers for all 12 rows.

The outputs appear usable for qualitative audit review, but they should not yet be promoted into registered manuscript results. The run is still a single-provider, single-run-per-cell validation collection. It is not a stable multi-provider benchmark and not evidence about deployed grocery recommendation systems.

## Why C002 Should Not Be Upgraded Yet

C002 should remain ambiguous because the real provider collection is still limited in four ways:

1. It uses one local Codex CLI provider path rather than a pre-registered set of external providers and model versions.
2. It has one run per persona/variant cell, so repeated-run stability is not yet measured.
3. It has not been parsed into validated affordability/nutrition metrics by an approved analysis script.
4. It has not undergone third-party blind review.

## Difference From Mock / Current-Session Validation

This collection is materially stronger than mock output because it uses an authenticated real provider CLI and records provider metadata. It is also cleaner than informal current-session manual output because it is generated through `aeros collect` and captured in JSONL with hashes and provenance.

However, it remains internal-only validation evidence until human review decides whether to register it as formal results.

## Questions For Third-Party Blind Review

1. Do the outputs look like realistic grocery recommendations for the stated personas?
2. Are any recommendations implausible for SNAP-relevant or low-budget contexts?
3. Are the budget/nutrition/feasibility caveats specific enough to support measurement coding?
4. Does the claim registry appropriately prevent overclaiming?
5. Should this collection be registered as R006/R007, or should AEROS first collect repeated runs per cell?
6. Would you trust the current paper package as a methods/demo artifact?

## Recommended Next Action

Do not upgrade claims. Send this brief, the raw JSONL, the claim registry, and the paper draft to a third-party reviewer. If the reviewer finds the collection credible, the next AEROS step should be a human-approved task to register R006/R007 and run a bounded result-validation pass.
