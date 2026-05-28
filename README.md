# AEROS: Applied Econ Research Operating System

AEROS is a lightweight AI-assisted workflow for empirical economics research.

It separates early-stage discovery from execution-stage reproducibility.

Its goal is not to let AI replace research judgment, but to make idea validation, data feasibility, empirical execution, claim auditing, and human decisions traceable.

## What AEROS Is

AEROS is a thin wrapper around existing reproducible research practices, agent instructions, data pipelines, and replication-package standards. It is designed for applied economics projects where the key risks are not only whether code runs, but whether the idea is worth pursuing, the literature gap is real, the data can support the design, and claims stay within the evidence.

## Workflow Layers

1. Research Judgment Layer

   Human-led decisions about the idea, literature gap, identification, claim boundaries, and go / pause / revise / drop choices.

2. Agent Execution Layer

   AI-assisted work on literature classification, data scouting, code execution, result checking, claim auditing, and report generation.

3. Mechanical Verification Layer

   Deterministic checks that protect raw data, protected definitions, paper numbers, and claim-evidence links.

## Directory Map

```text
0_discovery/      idea, literature scope, data feasibility, gap, and design options
1_design/         method card, data contract, protected definitions, robustness, language limits
2_execution/      code, data, outputs, task files, and validation checks
3_evidence/       claim registry, evidence ledger, and result index
4_agent_runs/     agent run reports and critic reports
5_audits/         discovery, data, design, result, and claim audit reports
6_decisions/      human decision, issue, and revision logs
examples/         starter examples for adapting the template to real projects
```

## First Use

1. Fill `0_discovery/00_idea_note.md`.
2. Fill `1_design/method_card.md`.
3. Fill `1_design/protected_definitions.yml`.
4. Fill `3_evidence/claim_registry.md`.
5. Record the first human decision in `6_decisions/decision_log.md`.
6. Run one task from `2_execution/tasks/`.
7. Save an agent report in `4_agent_runs/`.

## Core Principle

Agents may help execute and audit. Humans decide whether a research claim is valid.
