# Practical Skill Menu

Use this menu when choosing a skill for a concrete AEROS task.

This is not a list of required dependencies. It is a routing guide for optional local or external skills that can make the harness more useful.

## Discovery and Scoping

| Task | Useful skill type | AEROS output | Constraint |
| --- | --- | --- | --- |
| Turn a broad topic into researchable questions | research ideation, academic research suite, lead research assistant | `discovery/idea_bank.csv`, `discovery/idea_memo.md` | Ideas stay speculative until verified |
| Narrow a vague topic | Socratic research question / deep research skill | `discovery/idea_memo.md`, `discovery/design_options.md` | Do not write a proposal before data and literature checks |
| Build a literature search plan | literature review assistant, bib manager, Zotero | `discovery/01_literature_scope.md`, `discovery/literature/search_log.csv` | Search is not synthesis |
| Verify sources and citations | citation check, bib manager, Zotero | `discovery/literature/citation_audit.md` | No invented citations |

## Literature and Evidence

| Task | Useful skill type | AEROS output | Constraint |
| --- | --- | --- | --- |
| Create extraction cards | academic researcher, literature extraction skill, PDF skill | `discovery/literature/extraction_cards/` | Requires opened full text |
| Build closest-literature matrix | literature synthesis skill | `discovery/literature/synthesis/closest_literature_matrix.csv` | Gap claims require extracted gap-verification papers |
| Critique novelty | academic research agent, devil's advocate, referee skill | `audits/discovery_critic_report.md` | Critique cannot replace human go/no-go |
| Track citation integrity | citation audit / bibliography skill | `citation_audit.md`, `paper/references.bib` | Abstract-only is not full evidence |

## Data and Measurement

| Task | Useful skill type | AEROS output | Constraint |
| --- | --- | --- | --- |
| List possible datasets | data inventory, API data fetcher, lead research assistant | `discovery/data_inventory.csv` | Must include owner, access path, unit, coverage, and limits |
| Generate data dictionary | data-codebook skill | `docs/data_dictionary.md` | Must match actual data after execution begins |
| Audit data quality | data quality checker, describe-data | `audits/data_audit_report.md` | Never modify `data/raw/` |
| Audit merges | data merge audit | `audits/data_audit_report.md`, `outputs/logs/` | Merge keys and match rates must be logged |
| Build measurement protocol | data / measurement literature skill | `docs/data_contract.yml`, `docs/data_sources.md` | Measurement claims need validation evidence |

## Design and Identification

| Task | Useful skill type | AEROS output | Constraint |
| --- | --- | --- | --- |
| Review causal identification | causal ID review, DID checklist | `audits/design_audit_report.md`, `docs/method_card.md` | Design remains provisional until human approval |
| Design placebo tests | placebo-test skill | `docs/robustness_checklist.md` | Placebos cannot redefine the main model |
| Diagnose panel setup | diagnostics panel | `audits/design_audit_report.md`, `outputs/logs/` | Must respect protected sample and outcome definitions |
| Plan robustness checks | robustness suite | `docs/robustness_checklist.md`, `audits/robustness_audit_report.md` | Agent cannot choose preferred spec by significance |

## Execution and Replication

| Task | Useful skill type | AEROS output | Constraint |
| --- | --- | --- | --- |
| Run R/Python/Stata analysis | econometrics skill, Stata MCP, panel data skill | `code/`, `outputs/`, `outputs/logs/` | Must respect protected definitions |
| Review empirical code | code-review-econ, academic code review | `audits/code_review_report.md` | Review should prioritize reproducibility and empirical design risks |
| Check reproducibility | replication-check, referee2, project rigor check | `audits/replication_package_report.md` | Failure should block submission-facing claims |
| Clean technical debt | refactor pipeline, code simplifier | `code/`, `checks/` | Must not change empirical estimands or outputs silently |

## Writing and Communication

| Task | Useful skill type | AEROS output | Constraint |
| --- | --- | --- | --- |
| Draft economics prose | econ-write, paper-draft, academic writing skill | `paper/draft.md`, `paper/draft.tex` | Must follow claim registry and language constraints |
| Write results section | results narrator, econ-write | `paper/draft.md`, `audits/writing_audit_report.md` | Use economic significance, not only statistical significance |
| Make tables | regression-table, summary-stats-table, latex-tables | `outputs/tables/`, `paper/` | Table values must trace to outputs |
| Make figures | econ-plots, econ-visualization | `outputs/figures/` | Captions must preserve units and claim type |
| Compile manuscript | latex-compile-qa, paper writer | `paper/`, `outputs/logs/` | Compilation success is not claim validation |
| Pre-submission audit | pre-submission-audit, paper review, referee panel | `audits/referee_panel_report.md` | Reviewer simulation is advisory |
| Response letter | response-letter skill | `paper/response_letter.md` | Human decides concessions and claim changes |

## Rule of Thumb

Use specialized skills for speed and domain convention.

Use AEROS for admissibility.

If a skill makes the project sound better by weakening evidence standards, do not use that output as-is.
