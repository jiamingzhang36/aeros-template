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
| Analysis | `code/`, `outputs/`, and `checks/` | R, Python, or Stata econometrics skill | Must respect protected definitions and task contracts |
| Writing | `paper/`, `docs/language_constraints.md`, `evidence/claim_registry.md` | economics writing skill | Must not strengthen claims beyond registered evidence |
| Communication | `outputs/`, `paper/`, presentations | visualization / Beamer / policy writing skill | Must preserve units, uncertainty, and evidence boundaries |
| Engineering | `harness/`, `tasks/discovery/`, `tasks/execution/`, `checks/` | spec-driven or maintenance skill | Must not weaken AEROS permissions or checks |

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

## Practical Skill Menu

Use `harness/practical_skill_menu.md` as the human-readable routing guide.

It maps common tasks to useful skill types:

- research question refinement
- literature search and citation verification
- full-text extraction and novelty critique
- data inventory, codebook, quality checks, and merge audit
- causal identification, DID, panel diagnostics, placebo, and robustness
- replication checks and economics code review
- paper drafting, results narration, tables, figures, LaTeX QA, pre-submission audit, and response letters

The menu is advisory. `harness/skill_map_core.yml` is the machine-readable core map, and `harness/skill_map_reference.md` stores the optional/reference catalog.

## External Economics Advisory Tools

The following external tools are registered in `harness/external_tool_registry.yml` as advisory/reference capabilities, not hard gates:

- `Econometrics-Agent`: may suggest econometric workflow risks or specification review notes, but may not certify identification, approve a gate, or replace reproducible code/results.
- `Causal-Copilot`: may suggest causal-identification risks, alternative explanations, or claim-ceiling concerns, but may not upgrade a claim or approve G3/G7/G12.
- `CausalAgent`: may suggest graph/assumption/robustness concerns, but may not certify causality, certify identification, or replace human judgment.
- `Econstellar`: is a design reference for reproducible endpoints and result lineage; AEROS records endpoint/command metadata in the result registry without treating endpoint availability as scientific truth.

Use these tools only through advisory notes or future adapter candidates. Their output must be cited as advisory material and routed through the relevant AEROS evidence, result, claim, or gate checks before it affects the paper.

## Skill Use Status

Each skill should be classified as:

- `allowed`: may be used under AEROS rules.
- `allowed_with_constraints`: useful, but only with additional AEROS evidence or permission checks.
- `review_only`: may produce suggestions or audits, but not modify files.
- `not_recommended`: conflicts with AEROS evidence, privacy, or human-gate rules.

## Skill Tiers

AEROS keeps the operational skill set small.

- `core`: default shortlist for common empirical research work. Keep this at 8 or fewer skills.
- `optional`: task-specific tools used only when the task clearly needs them.
- `reference`: external inspiration or heavy workflows; do not invoke by default.

Only `core` skills may have `default_use: true`.

The default shortlist is:

1. `research-ideation`
2. `lit-review-assistant`
3. `academic-research-suite`
4. `data-inventory`
5. `causal-id-review`
6. `did-checklist`
7. `code-review-econ`
8. `econ-write`

## Minimum Metadata

Any skill listed in `harness/skill_map_core.yml` should record:

- `name`
- `source`
- `external_stage`
- `aeros_stage`
- `use_status`
- `tier`
- `default_use`
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
