# Expanded Collection Design Report

## Task

- Task ID: T009_expanded_collection_design
- Stage: execution
- Gate: G11 expanded collection
- Audit date: 2026-06-01

## Bottom Line

The expanded collection design is ready for human review as a G11 design checkpoint. It defines a 12-row prompt grid across four synthetic personas and three prompt variants, with explicit model labeling, run identifiers, timestamp policy, exclusion rules, and claim-ceiling limits.

This report does not approve collection results because no expanded AI outputs have been collected yet.

## Design Summary

| Component | Decision |
|---|---|
| Personas | 4 synthetic personas covering SNAP-relevant, moderate-budget, senior, and low-time/low-budget contexts |
| Prompt variants | 3 variants: budget-first, nutrition-first, feasibility-first |
| Planned rows | 12 unique prompt-run rows |
| Model label | `current_codex_session_model` for this validation setting |
| Claim ceiling | Measurement only |
| Human gate | Required before claim upgrade or public interpretation |

## Why This Is Better Than The Pilot

The earlier pilot had two personas and a smaller prompt/run structure. The G11 design expands the audit surface by adding more household contexts and prompt sensitivities. This should make the measurement workflow more informative while still avoiding overclaiming.

## Why This Is Still Limited

The design remains too small for broad empirical claims. It also uses a local model label rather than stable external provider metadata. If the project later shifts toward a formal empirical paper, the grid should add more repetitions, more model/provider identifiers, and pre-approved collection windows.

## Checks Expected To Pass

- `check_expanded_collection_design.py`
- `check_claim_registry.py`
- `check_agent_run_report.py`

## Human Decision Needed Next

Approve T009/G11 design if the intended next step is to collect or import outputs only from this approved grid.

Block or revise the design if the next stage should instead prioritize a larger provider-comparison design, more repetitions per cell, public release constraints, or a different paper framing.
