# Practical Skill Menu

Use this menu when choosing a skill for a concrete AEROS task.

AEROS keeps the active skill set deliberately small. Start with Core. Use Optional only for clear task-specific needs. Treat Reference as inspiration or review framing.

## Core Skills

These are the default shortlist. They cover the common research lifecycle without overwhelming the agent.

| Skill | Best used for | AEROS stage | Main constraint |
| --- | --- | --- | --- |
| `research-ideation` | Turn a broad phenomenon into candidate questions | discovery ideation | Ideas stay speculative until verified |
| `lit-review-assistant` | Structure search and register candidate papers | literature discovery | Search is not synthesis |
| `academic-research-suite` | Source-grounded research, extraction, and narrowing | literature discovery | Do not run full paper pipeline before promotion |
| `data-inventory` | Identify and document real data sources | data scouting | Feasibility requires access path and limitations |
| `causal-id-review` | Review whether a causal design is plausible | design formation | Review only; human approves design |
| `did-checklist` | Check DiD/event-study assumptions and risks | design formation | Do not approve design automatically |
| `code-review-econ` | Review empirical code for research risks | engineering maintenance | Review only; no silent fixes |
| `econ-write` | Draft or revise economics prose | writing revision | Must follow claim registry and language constraints |

## Optional Skills

Use these only when a task clearly needs the specialized operation.

| Need | Optional skills |
| --- | --- |
| Bibliography and library work | `bib-manager`, `zotero` |
| Data documentation | `data-codebook`, `describe-data` |
| Data linkage risks | `data-merge-audit` |
| Panel diagnostics | `diagnostics-panel` |
| Robustness and falsification | `robustness-suite`, `placebo-test` |
| Regression outputs | `regression-table`, `summary-stats-table`, `latex-tables` |
| Figures and visualization | `econ-plots`, `econ-visualization` |
| Manuscript build / LaTeX | `latex-compile-qa` |
| Results prose | `results-narrator`, `econ-plots` |
| Later-stage submission work | `pre-submission-audit`, `response-letter`, `journal-adapt` |
| Policy background | `policy-timeline` |
| Repository hygiene | `project-rigor-check` |
| Specific analysis stack | `r-econometrics`, `python-panel-data`, `stata-regression` |

## Reference Skills

These are useful patterns, but they should not be default operational choices.

| Skill | Use as |
| --- | --- |
| `sdd` | Engineering workflow inspiration |
| `paper-review` | Review framework inspiration |
| `referee2` | Reproducibility audit inspiration |
| `academic-research-agent` | Human-gated research workflow reference |
| `paper-writer-skill` | Stage-gated writing pipeline reference |

## Rule of Thumb

Use specialized skills for speed and convention.

Use AEROS for admissibility.

If a skill makes the project sound better by weakening evidence standards, do not use that output as-is.

For data feasibility, do not skip the skill pass. Use or explicitly consider `data-inventory` first, then add `data-quality-checker`, `data-codebook`, `describe-data`, or `data-merge-audit` when sample data, schema, or linkage keys are available. If the skill cannot run, record the blocker and the next probe instead of making a final feasibility call.

## Economics data-mining and paper-stage skill clusters

AEROS keeps these skills available through `harness/skill_map_core.yml`, but task
contracts decide which skills are allowed and recommended. Data and audit skills
may inspect and summarize evidence; method and writing skills may advise, draft,
or flag risks; none may approve gates, strengthen claims, or bypass registries.

- Data mining: `describe-data`, `data-codebook`, `data-quality-checker`,
  `data-merge-audit`, `summary-stats-table`, `quick-stats`, `feature-engineering`,
  `policy-timeline`.
- Economics method and robustness: `causal-id-review`, `did-checklist`,
  `robustness-suite`, `placebo-test`, `regression-table`, `econ-principles-check`.
- Writing and paper package: `econ-write`, `paper-draft`, `results-narrator`,
  `journal-adapt`, `response-letter`.
- Final review and release: `code-review-econ`, `replication-check`,
  `pre-submission-audit`, `bib-manager`, `zotero:Zotero`.
