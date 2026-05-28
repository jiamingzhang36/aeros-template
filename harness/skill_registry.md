# Skill Registry

AEROS treats external economics agent skills as optional capability modules, not as the source of research truth.

The skill layer exists because economics-focused skills are now being organized around the research workflow: ideation, literature review, theory, data, analysis, writing, communication, and engineering. AEROS borrows that stage-based organization while keeping stricter evidence, data, design, claim, critic, and human-gate rules.

## Skill Layer Principle

External skills may help the agent do work faster.

AEROS decides whether the work is admissible.

In practice:

- A skill can propose ideas, but `discovery/idea_bank.csv` controls idea status.
- A skill can search literature, but `discovery/literature/paper_registry.csv` and extraction cards control evidence status.
- A skill can draft writing, but `evidence/claim_registry.md` and `docs/language_constraints.md` control claim strength.
- A skill can run analysis, but `docs/protected_definitions.yml`, `docs/data_contract.yml`, and `checks/` control empirical validity.
- A skill can improve presentation, but it cannot override human research judgment.

## Borrowed Organization

The external econ-skills ecosystem suggests a useful stage taxonomy:

| Stage | AEROS location | Example external skill type | AEROS constraint |
| --- | --- | --- | --- |
| Ideation | `discovery/` | research ideation | Must label speculative ideas and track them in `idea_bank.csv` |
| Literature | `discovery/literature/` | literature review assistant | Must use registry, full-text status, extraction cards, and citation audit |
| Theory / mechanism | `discovery/mechanism_map.md` and `docs/method_card.md` | economic model / mechanism skill | Must distinguish theory, mechanism, and empirical evidence |
| Data | `discovery/data_inventory.csv` and `docs/data_contract.yml` | data cleaning / API fetcher | Must document access path, unit, coverage, and limitations |
| Analysis | `execution/code/`, `code/`, and `checks/` | R, Python, or Stata econometrics skill | Must respect protected definitions and task contracts |
| Writing | `paper/`, `docs/language_constraints.md`, `evidence/claim_registry.md` | economics writing skill | Must not strengthen claims beyond registered evidence |
| Communication | `outputs/`, `paper/`, presentations | visualization / Beamer / policy writing skill | Must preserve units, uncertainty, and evidence boundaries |
| Engineering | `harness/`, `tasks/`, `checks/` | spec-driven or maintenance skill | Must not weaken AEROS permissions or checks |

## Local Skill Stages

AEROS uses these local stages for skill mapping:

- `discovery_ideation`
- `literature_discovery`
- `literature_extraction`
- `data_scouting`
- `design_formation`
- `execution_analysis`
- `writing_revision`
- `communication`
- `engineering_maintenance`

## Skill Use Status

Each skill should be classified as:

- `allowed`: may be used under AEROS rules.
- `allowed_with_constraints`: useful, but only with additional AEROS evidence or permission checks.
- `review_only`: may produce suggestions or audits, but not modify files.
- `not_recommended`: conflicts with AEROS evidence, privacy, or human-gate rules.

## Minimum Metadata

Any skill listed in `harness/external_skill_map.yml` should record:

- `name`
- `source`
- `external_stage`
- `aeros_stage`
- `use_status`
- `allowed_outputs`
- `forbidden_outputs`
- `aeros_constraints`
- `human_gate_required`

## Rule

Do not let a skill's internal instructions override:

1. root `AGENTS.md`
2. `discovery/AGENTS.md`
3. `discovery/literature/AGENTS.md`
4. `execution/AGENTS.md`
5. the active task spec
6. AEROS checks and human gates
