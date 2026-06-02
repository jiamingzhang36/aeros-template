# AEROS Automation Status

Date: 2026-06-02

## Summary

AEROS now functions as a human-gated research automation controller. It has been validated on the `ai_grocery_recommendation_audit` project from idea intake through discovery, execution, paper-package drafting, expanded validation collection, claim-upgrade review, and compliance/release review.

The system is not a fully autonomous paper factory. Its current north star is:

> automatic progress + automatic evidence + automatic constraints + human judgment.

## Current Capability

AEROS can currently:

- initialize an idea-driven project;
- run discovery and execution task contracts;
- maintain runtime state, candidate gates, and human-approved gates;
- stop at human gates instead of self-approving;
- detect stale tasks when inputs, outputs, or dependency artifacts change;
- recover manually completed tasks only after checks pass;
- generate gate decision packets;
- register results and provenance;
- enforce claim ceilings through claim registry checks;
- produce paper-package and claim-upgrade review artifacts;
- run mock provider batch collection from a prompt grid;
- check provider collection metadata;
- produce compliance/release gate artifacts with `internal-only` release status.

## Verified End-to-End Path

The grocery validation project reached:

- `G1` Data Readiness
- `G2` Measurement / Variable Construction
- `G3` Research Design
- `G4` Main Estimation / execution protocol
- `G5` Robustness planning
- `G6` Result Validation
- `G7` Claim Audit
- `G8` Referee Simulation
- `G9` Replication Package
- `G10` Paper Package Draft
- `G11` Expanded Collection
- `G12` Claim Upgrade Review
- `G13` Compliance / Release Gate

Current validation status:

```text
current gate : G13
gate status  : approved
candidate    : execution / G13
T001...T013  : passed / skip
```

## Provider Connector Status

`aeros collect` supports:

- `mock` provider without API keys;
- `openai` provider when `OPENAI_API_KEY` is explicitly set;
- prompt-grid batch collection;
- provider/model/request metadata;
- timestamps;
- prompt and output hashes;
- token/cost fields;
- collection-level provenance;
- dry-run preview mode.

Verified smoke path:

```bash
PYTHONPATH=/Users/jiamingzhang/aeros-template python3 -m aeros.cli collect --dry-run
AEROS_PROVIDER_COLLECTION_OUTPUT=outputs/audit_runs/provider_mock_test_outputs.jsonl \
PYTHONPATH=/Users/jiamingzhang/aeros-template \
python3 /Users/jiamingzhang/aeros-template/checks/check_provider_collection.py
```

## Compliance Gate Status

G13 is implemented as a Tier 3 advisory gate. It does not claim legal certainty and does not approve public release automatically.

Current grocery validation release status:

```text
release_status: internal-only
```

Public release remains blocked until provider/API terms, data licenses, IRB/privacy status, and package readiness receive explicit human review.

## What AEROS Does Not Yet Prove

AEROS has not yet proven that it can autonomously produce a submission-ready paper.

It also has not yet proven:

- high-quality literature review judged by an external expert;
- robust real-provider AI audit collection across stable model IDs;
- strong field-specific identification review;
- public replication-package readiness;
- third-party blind assessment of output quality;
- legal/IRB/compliance clearance.

## Current Claim Boundary

The grocery validation project must not be described as evidence about:

- all AI systems;
- deployed grocery recommendation systems;
- real consumers;
- nutrition fairness;
- legal discrimination;
- causal effects;
- public policy impacts.

Its evidence supports internal validation of the AEROS workflow and bounded measurement-audit mechanics only.

## Design Philosophy Confirmed

The validation project confirmed that AEROS should not behave like a paper factory. The system should make progress automatically, but gate-sensitive judgments must remain human-controlled.

The key rule is:

> machines may recommend strongly, but they must not silently cross gates.

## Recommended Next Priorities

1. Real provider collection trial

Run a small external-provider collection with explicit API key, stable model name, cost cap, and metadata capture. Keep it internal-only.

2. Third-party blind review

Ask an advisor or peer to judge a generated decision packet, paper package, and claim registry without seeing the development history.

3. Literature/citation quality validation

Stress-test the existing discovery/literature layer on a project where ground-truth citation quality can be externally evaluated.

4. Compliance hardening

Extend G13 with provider-specific terms templates, data license inventory, IRB decision categories, and public-release blockers.

5. Field-specific advisory reviewers

Add identification reviewers only as advisory risk memos, not pass/fail oracles.

## Current Repository Checkpoint

Recent commits:

```text
0e7b7af Build AEROS human-gated research automation loop
6751c3c Add provider connector collection plumbing
075e09b Add compliance release gate
```

The latest validation run confirmed that root template checks pass and the grocery validation project is clean at `G13/approved`.
