# Human Gate Decision Packet: G1

Generated: 2026-07-05T01:15:28+00:00
Stage: discovery
Current gate: G2 Measurement / Variable Construction
Gate status: auto_advanced
Candidate gate: execution / G10
Earned claim ceiling: none

## Recommendation

Do not approve G1 yet; revise, rerun, downgrade, block, or stop.

## Gate Criteria Status

| Gate | Status | Notes |
|---|---|---|
| G0 | PASS | all criteria satisfied |
| G1 | FAIL | 1 unmet criterion/criteria |

## Failed / Missing Criteria

### G1

- G1: check_data_diagnostics.py failed: missing discovery/data_diagnostics.yml - run the project data probe first

## Evidence Overview

### Registered Results

- None registered yet.

### Claim Registry Summary

- No claims registered yet.

## Artifact Excerpts — read the substance, not just the PASS marks

A check confirms a section *exists*; it cannot confirm it *says something*. Read these before approving — hollow, duplicated, or placeholder content here is a reason to block even when every check is green.

### Research question / idea — `discovery/idea_memo.md`

```
# Idea Memo

## Starting Idea

Study MAHA-related SNAP food restriction waiver policy design, approval timing, federal review, implementation friction, and related documentation.
```

### Anchor (4 components) — `discovery/anchor.yml`

```
# Research anchor: 4 components, set ONCE at intake and then frozen (anti-drift).
# Set status: locked once decided; after that it is a protected file.
anchor:
  status: draft            # draft | locked
  locked_at: ""
  topic: ""                # one-sentence research question
  claim_type: ""           # descriptive | associational | causal | mechanism | external_validity | policy_translation | forecast
  identification: ""       # identification / measurement strategy (or "descriptive: none")
  data: ""                 # dataset(s) and unit of analysis the anchor commits to
```

### Method card — `docs/method_card.md`

```
---
status: draft
---
# Method Card
```

## Five-Dimension Review (AutoResearch: novelty / validity / impact / reliability / provenance)

The mechanical layer already certifies the last three: **validity** (checks passed), **reliability** (staleness fingerprints / reproducibility), and **provenance** (numbers trace to result cells; results to data). The two a check CANNOT judge are yours to weigh here:
- **Novelty** — is the question/finding meaningfully new vs. prior work, or a restatement? (No machine check can adjudicate this.)
- **Impact** — does the result address something that matters, or is it technically clean but inconsequential?
Approve only if novelty and impact hold; the green checks cover the rest.

## Key Risks for Human Review

- Check whether the evidence actually supports the proposed claim strength.
- Check whether the selected design and data diagnostics match the project intent.
- Check whether any forced overrides, stale tasks, or missing provenance should block approval.

## Human Actions

- Approve: `aeros gate approve G1 --stage discovery --owner <name> --note <why>`
- Block: `aeros gate block G1 --stage discovery --owner <name> --reason <why>`
- Revise: edit the relevant artifacts or task contracts, then rerun `aeros iterate`.
- Stop: record the reason in `decisions/issue_log.csv` or the project log.
