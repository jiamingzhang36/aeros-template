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

   `harness/agent_roles.yml` separates worker, critic, and human-gate responsibilities.

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
decisions/           human decision, issue, and revision logs
harness/             permissions, worker protocol, critic protocol, hooks, and human gates
execution/           execution-stage agent rules
examples/            generic empirical project archetypes
```

## First Use

1. Start with `discovery/idea_memo.md`.
2. Search literature using `discovery/literature/search_protocol.md`.
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
- Is the minimum viable version feasible?

Use the discovery harness to decide whether to pursue, revise, pause, or drop the idea before investing in protected definitions, pipeline checks, and claim management.

## Source-Grounded Literature Review

Do not ask an agent to write a literature review from memory. Use:

```text
search -> registry -> citation audit -> full-text status -> extraction cards -> synthesis
```

Only papers with extraction cards may support substantive synthesis claims. Abstract-only papers may be mentioned only as abstract-based leads.

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
