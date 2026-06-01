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
