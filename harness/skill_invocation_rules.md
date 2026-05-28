# Skill Invocation Rules

External economics skills can be useful, but AEROS only uses them through a task contract.

## Invocation Order

Before invoking or following an external skill, the agent must read:

1. `AGENTS.md`
2. the active stage `AGENTS.md`
3. the active task file in `tasks/`
4. `harness/skill_registry.md`
5. `harness/practical_skill_menu.md`
6. `harness/external_skill_map.yml`

The task file and AEROS rules define the allowed files, outputs, and checks.

## Skill Selection Rule

Choose the smallest useful skill for the task.

Default to `tier: core` skills.

Prefer:

- discovery skills before execution skills when the research question is still unsettled,
- read-only review skills before editing skills when the risk is high,
- source verification skills before writing skills when citations or literature claims are involved,
- diagnostics and audit skills before robustness or model-changing skills,
- writing skills only after claim boundaries are clear.

Do not invoke a full paper-writing or full research pipeline skill when the task only asks for one stage.

Use `tier: optional` skills only when the task clearly requires that specialized operation.

Use `tier: reference` skills only as inspiration or review framing unless the human explicitly asks to run that workflow.

## Discovery Skills

Discovery skills may:

- brainstorm research ideas,
- suggest literature strands,
- suggest possible data sources,
- propose mechanisms,
- propose possible designs.

Discovery skills must not:

- claim a gap without extracted closest literature,
- claim feasibility without a real data source in `discovery/data_inventory.csv`,
- propose a causal design without documented identifying variation and a probed data engineering path,
- move speculative ideas into formal memos without verification.

Exploratory outputs must be recorded in `discovery/idea_bank.csv` unless they are immediately rejected.

## Literature Skills

Literature skills may help search, organize, and summarize papers only under the source-grounded literature workflow.

Required order:

```text
search -> registry -> citation audit -> full-text status -> extraction card -> synthesis
```

Rules:

- Search outputs alone cannot support literature synthesis.
- Abstract-only papers can only support abstract-based notes.
- Full paper summaries require opened full text.
- DOI is optional, but if it exists it must be recorded.
- Papers promoted beyond search/screening require a stable source locator: DOI, official URL, working-paper page, database record, or private local PDF path.
- Gap claims require extracted `gap-verification` papers.
- Synthesis must cite `paper_id` values that have extraction cards.

## Data Skills

Data skills may fetch, clean, describe, or transform data only when the task permits those actions.

Rules:

- Never modify `data/raw/`.
- Record real source, owner, access path, unit, coverage, variables, restrictions, and limitations.
- Do not treat "possible data" as "available data".
- Early data scouting should produce provisional evidence grades and next probes, not final feasibility conclusions.
- Before a feasibility recommendation, consider relevant data skills and record use, non-use rationale, or blocked probes in `discovery/data_inventory.csv` and the feasibility memo.
- Do not create analysis-ready claims from unvalidated data.

## Econometrics and Analysis Skills

Analysis skills may run R, Python, Stata, or other empirical workflows only in execution-stage tasks.

Rules:

- Do not change protected definitions without human approval.
- Do not choose preferred specifications based on statistical significance.
- Do not overwrite main results with robustness results.
- Save logs and outputs in the paths required by the task.
- Run relevant checks after execution.

## Writing Skills

Writing skills may draft, rewrite, or audit economics prose.

Rules:

- Drafted text must preserve the claim type in `evidence/claim_registry.md`.
- Policy, causal, external-validity, and forecast language must follow `docs/language_constraints.md`.
- Unsupported claims must be marked as unsupported or converted to placeholders.
- Writing polish cannot hide uncertainty, sample limits, or identification limits.

## Review and Replication Skills

Review, code-audit, reproducibility, and pre-submission skills are useful late-stage checks.

Rules:

- Treat review outputs as findings, not automatic decisions.
- Do not let a review skill directly rewrite protected definitions, preferred specifications, or claim language.
- Convert review findings into `decisions/issue_log.csv` or an audit report.
- Human approval is required before accepting or rejecting major reviewer-style recommendations.

## Skill Conflict Rule

If an external skill suggests an action that conflicts with AEROS, the agent must:

1. follow AEROS,
2. record the conflict in the run report,
3. ask for human judgment if the conflict affects research design, data access, or claim strength.

## Run Report Requirement

When a task uses an external skill, the run report must list:

- skill name,
- source or local path,
- task phase,
- files read,
- files modified,
- outputs created,
- AEROS constraints applied,
- checks run,
- unresolved human decisions.
