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
