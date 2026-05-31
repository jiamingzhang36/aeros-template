---
schema_version: 1
required_sections:
  - ## Promotion Criteria
  - ## Decision
---
# Promote to Execution Harness

Use this gate before activating the full execution harness.

## Promotion Criteria

- [ ] Main literature gap is clear enough to justify continued work.
- [ ] At least one feasible data source is identified with access evidence.
- [ ] Data engineering maturity is high enough for the proposed project type.
- [ ] Unit of analysis is approximately clear.
- [ ] Candidate outcome can be constructed or measured.
- [ ] Candidate treatment, exposure, shock, variation, or non-causal contribution is clear.
- [ ] Project type is classified as causal, descriptive, measurement, prediction, policy translation, mechanism, or replication.
- [ ] Minimum viable version is written.
- [ ] Major data, measurement, design, and execution risks are listed.

For a causal design, do not promote unless access, schema, key variables, linkage keys, coverage, and identifying variation have been probed or the remaining uncertainty is explicitly accepted by the human owner.

## Decision

Choose one:

- promote
- revise discovery
- pause
- drop

Decision: TBD

## If Promoted

Create or update:

- `docs/method_card.md`
- `docs/data_contract.yml`
- `docs/protected_definitions.yml`
- `docs/robustness_checklist.md`
- `evidence/claim_registry.md`
- relevant `tasks/discovery/` (and `tasks/execution/` after promotion)
- relevant `checks/`

## Human Rationale

TBD
