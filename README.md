# AEROS: Applied Empirical Research Harness

AEROS is a medium-weight AI-assisted research harness for empirical economics, applied micro, management, policy, and adjacent empirical research projects.

It separates early-stage discovery from execution-stage reproducibility.

Its goal is not to let AI replace research judgment, but to make idea validation, data feasibility, empirical execution, claim auditing, and human decisions traceable.

## What AEROS Is

AEROS is a thin wrapper around existing reproducible research practices, agent instructions, data pipelines, and replication-package standards. It is designed for empirical projects where the key risks are not only whether code runs, but whether the question is worth pursuing, the evidence gap is real, the data can support the design, and claims stay within the evidence.

## Workflow Layers

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
docs/discovery/      idea, literature scope, data feasibility, gap, and design options
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
examples/            generic empirical project archetypes
```

## First Use

1. Fill `docs/discovery/00_idea_note.md`.
2. Fill `docs/method_card.md`.
3. Fill `docs/protected_definitions.yml`.
4. Fill `evidence/claim_registry.md`.
5. Record the first human decision in `decisions/decision_log.md`.
6. Run one task from `tasks/`.
7. Save an agent report in `agent_runs/`.
8. For high-risk tasks, run the critic protocol in `harness/protocols/critic_protocol.md`.

## Core Principle

Agents may help execute and audit. Humans decide whether a research claim is valid.

## Harness Principle

Do not let the worker agent be the only judge of its own output. A substantial task should have a task contract, a run report, mechanical checks, critic review when risk is high, and a human decision when protected definitions or claim boundaries are affected.
