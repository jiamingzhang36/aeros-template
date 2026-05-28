# Skill Invocation Rules

External economics skills can be useful, but AEROS only uses them through a task contract.

## Invocation Order

Before invoking or following an external skill, the agent must read:

1. `AGENTS.md`
2. the active stage `AGENTS.md`
3. the active task file in `tasks/`
4. `harness/skill_registry.md`
5. `harness/external_skill_map.yml`

The task file and AEROS rules define the allowed files, outputs, and checks.

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
- propose a causal design without documented identifying variation,
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
- Gap claims require extracted `gap-verification` papers.
- Synthesis must cite `paper_id` values that have extraction cards.

## Data Skills

Data skills may fetch, clean, describe, or transform data only when the task permits those actions.

Rules:

- Never modify `data/raw/`.
- Record real source, owner, access path, unit, coverage, variables, restrictions, and limitations.
- Do not treat "possible data" as "available data".
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
