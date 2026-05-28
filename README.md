# AEROS: Applied Empirical Research Harness

AEROS is a medium-weight AI-assisted research harness for empirical economics, applied micro, management, policy, and adjacent empirical research projects.

It separates early-stage discovery from execution-stage reproducibility.

Its goal is not to let AI replace research judgment, but to make idea validation, data feasibility, empirical execution, claim auditing, and human decisions traceable.

## What AEROS Is

AEROS is a thin wrapper around existing reproducible research practices, agent instructions, data pipelines, and replication-package standards. It is designed for empirical projects where the key risks are not only whether code runs, but whether the question is worth pursuing, the evidence gap is real, the data can support the design, and claims stay within the evidence.

## Workflow Layers

Start in `discovery/` unless the project already has a clear question, feasible data source, unit of analysis, candidate outcome, and empirical design.

1. Project Constitution

   `AGENTS.md`, `project_manifest.yml`, and `harness/permissions.yml` define the project contract.

2. Research Design Memory

   `docs/method_card.md`, `docs/language_constraints.md`, and `docs/robustness_checklist.md` preserve the research design.

3. Data Contract

   `docs/data_contract.yml`, `docs/data_dictionary.md`, and `docs/data_sources.md` define data structure and provenance.

4. Protected Definitions

   `docs/protected_definitions.yml` protects sample, exposure, outcome, model, and claim boundaries.

5. Task Specification

   `tasks/` turns open-ended requests into scoped issue-style work.

6. Execution Pipeline

   `code/`, `data/`, `outputs/`, `paper/`, and `Makefile` provide the reproducible project surface.

7. Verification Checks

   `checks/` runs deterministic checks for data, protected definitions, outputs, paper links, claims, and replication structure.

8. Agent Roles / Skills

   `harness/agent_roles.yml` separates worker, critic, and human-gate responsibilities. `harness/skill_registry.md`, `harness/skill_invocation_rules.md`, and `harness/external_skill_map.yml` map external economics skills into AEROS without letting them override evidence rules.

9. Critic Review

   `agent_runs/` and `harness/protocols/critic_protocol.md` keep worker output from reviewing itself.

10. Human Decision Log

   `decisions/` records accept, revise, reject, and defer decisions.

## Directory Map

```text
discovery/           idea, source-grounded literature review, data feasibility, gap, and design options
docs/                method card, data contract, protected definitions, robustness, language limits
data/                raw, intermediate, parquet, clean, and snapshot data
code/                setup, ingest, clean, construct, analysis, robustness, tables, and master scripts
outputs/             tables, figures, logs, and model outputs
paper/               manuscript, appendix, references, and paper build files
evidence/            claim registry, evidence ledger, and result index
tasks/               issue-style task contracts and gate tasks
checks/              deterministic harness checks
agent_runs/          worker run reports, critic reports, commands, and diffs
audits/              discovery, data, design, result, claim, and referee audit reports
decisions/           human decision, issue, and dated revision logs
harness/             permissions, worker protocol, critic protocol, hooks, and human gates
execution/           execution-stage agent rules
examples/            generic empirical project archetypes
```

## Skill Layer

Economics-specific agent skills are emerging for ideation, literature review, data cleaning, econometrics, LaTeX writing, visualization, and communication. AEROS treats them as optional modules.

Use the skill layer when a task would benefit from a specialized skill, but keep AEROS in charge:

- `harness/skill_registry.md` explains the local stage taxonomy.
- `harness/practical_skill_menu.md` gives a task-to-skill routing guide for common research work.
- `harness/skill_invocation_rules.md` defines how a task may invoke an external skill.
- `harness/external_skill_map.yml` maps examples such as research ideation, literature review assistant, R/Python/Stata econometrics, LaTeX tables, visualization, API data fetching, and economics writing.

External skills can accelerate work. They cannot invent citations, skip extraction cards, change protected definitions, choose preferred specifications by significance, or strengthen claims beyond the evidence registry.

## First Use

1. Start with `discovery/idea_memo.md`.
2. Define literature boundaries in `discovery/01_literature_scope.md` and search rules in `discovery/literature/search_protocol.md`.
3. Register papers in `discovery/literature/paper_registry.csv`.
4. Verify citations in `discovery/literature/citation_audit.md`.
5. Create extraction cards before writing synthesis.
6. Fill `discovery/data_inventory.csv`.
7. Score `discovery/feasibility_matrix.md`.
8. Draft `discovery/design_sketch.md`.
9. Decide with `discovery/PROMOTE_TO_HARNESS.md`.
10. Only after promotion, fill `docs/method_card.md`, `docs/protected_definitions.yml`, and `evidence/claim_registry.md`.

## Core Principle

Agents may help execute and audit. Humans decide whether a research claim is valid.

## Discovery Before Execution

The full execution harness is not the first step. Early-stage projects should first answer:

- Is there a real literature gap?
- Is at least one usable data source available?
- Can the project measure key variables credibly?
- Is there credible variation or a clear non-causal contribution?
- How mature is the data-engineering path: located source, verified access path, inspected schema, verified variables, tested linkage, diagnosed coverage, or execution-ready?
- Is the minimum viable version feasible?

Use the discovery harness to decide whether to pursue, revise, pause, or drop the idea before investing in protected definitions, pipeline checks, and claim management.

Current discovery task order:

- `D001` Literature Search
- `D002` Data Scouting and Feasibility Probe, including former feasibility triage
- `D003` Design Sketch
- `D004` Literature Verification and Extraction, including former extraction
- `D005` Literature Synthesis
- `D006` Discovery Critic

Every task must complete a Mainline Alignment Gate:

- Project north star and active mechanism/hypothesis
- Task role (feasibility / measurement / evidence)
- What the task must not become
- Explicit stop rule and side-lead parking rule
- Any uncertainty that changes task direction must be flagged and sent to human before proceeding

## Exploration Policy

Flexible in discovery, strict in verification, conservative in claims.

Agents may brainstorm new angles, adjacent literatures, possible data sources, mechanisms, and designs. Those ideas must be labeled and tracked in `discovery/idea_bank.csv` until evidence promotes them.

Exploration is not evidence. Verification comes from real literature, extraction cards, real data sources, matrices, critic review, and human decisions.

Data-source existence is not the same as data feasibility. Early scouting should record provisional evidence grades and next probes. A project can be appropriate for a linked descriptive pilot while still being far from a national causal design; the feasibility memo must state that boundary instead of collapsing it into a final verdict.

Data feasibility also requires a skill-assisted probe pass. Agents should use or explicitly consider relevant data skills, record what was tried, and document blocked probes. A quick manual scan is not enough to support a final pursue, pause, or drop recommendation.

Initial materials should not evaporate. Before discovery synthesis or feasibility triage, map every nontrivial lead from intake materials to a registry, inventory, task, idea bank entry, or explicit deferral reason. Use `intake_ref` and `intake_priority` in `discovery/data_inventory.csv` and `discovery/idea_bank.csv`; high-priority data leads must be probed, blocked, or explicitly deferred before feasibility language is strengthened.

## Source-Grounded Literature Review

Do not ask an agent to write a literature review from memory. Use:

```text
search -> registry -> citation audit -> full-text status -> extraction cards -> synthesis
```

Only papers with extraction cards may support substantive synthesis claims. Abstract-only papers may be mentioned only as abstract-based leads.

DOI is optional and should be recorded whenever it exists. A paper does not need a DOI to become evidence, but before it is treated as full-text obtained, extracted, included, or used in synthesis, the registry must contain at least one stable source locator: DOI, official or publisher URL, working-paper page, database record, or private local PDF path.

Use `screening_decision=include` only for opened, verified, full-text sources with an extraction card that summarizes content, records an inclusion reason, and points to direct evidence notes. Use `maybe` for candidates still being verified, `exclude` for checked sources that should not support claims, and `defer` for plausible but lower-priority or out-of-scope sources.

Classify literature by function:

- `idea-inspiring`: inspiration only, not gap evidence
- `gap-verification`: closest literature for proving the gap
- `method-identification`: design recipes and assumptions
- `data-measurement`: data construction, validation, and measurement error
- `background-institutional`: policy, institutional, legal, market, or historical context
- `theory-mechanism`: mechanisms and interpretation

Gap claims require extracted `gap-verification` papers.

## Harness Principle

Do not let the worker agent be the only judge of its own output. A substantial task should have a task contract, a run report, mechanical checks, critic review when risk is high, and a human decision when protected definitions or claim boundaries are affected.
