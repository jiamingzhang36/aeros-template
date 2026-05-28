# AEROS: Applied Empirical Research Operating System

AEROS is a lightweight AI-assisted workflow for empirical research projects.

It separates early-stage discovery from execution-stage reproducibility.

Its goal is not to let AI replace research judgment, but to make idea validation, data feasibility, empirical execution, claim auditing, and human decisions traceable.

## What AEROS Is

AEROS is a thin wrapper around existing reproducible research practices, agent instructions, data pipelines, and replication-package standards. It is designed for empirical projects where the key risks are not only whether code runs, but whether the question is worth pursuing, the evidence gap is real, the data can support the design, and claims stay within the evidence.

## Workflow Layers

1. Research Judgment Layer

   Human-led decisions about the idea, literature gap, identification, claim boundaries, and go / pause / revise / drop choices.

2. Agent Execution Layer

   AI-assisted work on literature classification, data scouting, code execution, result checking, claim auditing, and report generation.

3. Mechanical Verification Layer

   Deterministic checks that protect raw data, protected definitions, paper numbers, and claim-evidence links.

4. Harness Layer

   Task contracts, permission policies, worker / critic protocols, run traces, and human approval gates that constrain agent work.

## Directory Map

```text
0_discovery/      idea, literature scope, data feasibility, gap, and design options
1_design/         method card, data contract, protected definitions, robustness, language limits
2_execution/      code, data, outputs, task files, and validation checks
3_evidence/       claim registry, evidence ledger, and result index
4_agent_runs/     agent run reports and critic reports
5_audits/         discovery, data, design, result, and claim audit reports
6_decisions/      human decision, issue, and revision logs
harness/          permissions, worker protocol, critic protocol, hooks, and human gates
examples/         generic empirical project archetypes
```

## First Use

1. Fill `0_discovery/00_idea_note.md`.
2. Fill `1_design/method_card.md`.
3. Fill `1_design/protected_definitions.yml`.
4. Fill `3_evidence/claim_registry.md`.
5. Record the first human decision in `6_decisions/decision_log.md`.
6. Run one task from `2_execution/tasks/`.
7. Save an agent report in `4_agent_runs/`.
8. For high-risk tasks, run the critic protocol in `harness/protocols/critic_protocol.md`.

## Core Principle

Agents may help execute and audit. Humans decide whether a research claim is valid.

## Harness Principle

Do not let the worker agent be the only judge of its own output. A substantial task should have a task contract, a run report, mechanical checks, critic review when risk is high, and a human decision when protected definitions or claim boundaries are affected.
