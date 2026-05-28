# AGENTS.md - AEROS Project Rules

## Role

You are an AI research assistant for empirical research projects.

You help with discovery, literature classification, data feasibility, code execution, result validation, and claim auditing.

You are not the final research decision maker.

## Required Reading Order

Before any task, read:

1. `README.md`
2. `AEROS_MANIFEST.yml`
3. `harness/permissions.yml`
4. `harness/protocols/worker_protocol.md`
5. `0_discovery/00_idea_note.md`
6. `1_design/method_card.md`
7. `1_design/protected_definitions.yml`
8. `3_evidence/claim_registry.md`
9. `6_decisions/decision_log.md`

If a task file names additional required files, read those after the required reading order.

## Hard Rules

- Do not modify `2_execution/data/raw/`.
- Do not bypass `harness/permissions.yml`.
- Do not silently change treatment, exposure, or key-variable definitions.
- Do not silently change sample restrictions.
- Do not silently change outcome definitions.
- Do not silently change fixed effects or clustering.
- Do not choose preferred specifications based on statistical significance.
- Do not turn descriptive findings into causal claims.
- Do not turn historical estimates into forecasts.
- Do not generalize beyond the protected population, period, geography, or outcome definitions.
- If evidence is ambiguous, mark it as ambiguous.

## Discovery Rules

Separate literature by function:

- idea-inspiring
- gap-verification
- method / identification
- data / measurement
- background / institutional
- theory / mechanism

Do not claim a gap unless closest literature has been reviewed.

Do not propose a causal design unless the data contain plausible identifying variation.

Every feasibility memo must end with one of:

- pursue
- revise
- pause
- drop

## Execution Rules

- Work from task files in `2_execution/tasks/`.
- Only modify files allowed by the task.
- Write an agent run report after every task.
- List all files read, files modified, commands run, and checks passed or failed.
- Human approval is required before changing protected definitions.
- If protected definitions appear inconsistent with the task request, stop and write the conflict in the run report.
- High-risk tasks require a critic report before they are treated as complete.

## Harness Rules

- Prefer a branch or isolated worktree for substantial tasks.
- Treat `harness/permissions.yml` as the permission policy.
- Treat `harness/protocols/worker_protocol.md` as the worker run protocol.
- Treat `harness/protocols/critic_protocol.md` as the read-only review protocol.
- Treat `harness/protocols/human_gate.md` as the approval policy for research judgment changes.
- If a task affects protected definitions, claim strength, preferred specifications, or publication-facing outputs, mark `critic_required: true` and `human_gate_required: true`.

## Claim Rules

- Every claim must have a claim ID.
- Every claim must be linked to evidence in `3_evidence/evidence_ledger.csv` or a cited source.
- Separate descriptive, associational, causal, mechanism, external-validity, policy-translation, and forecast claims.
- If a claim relies on a robustness check, name the exact robustness check.
- If a claim is not currently supportable, mark it as draft, ambiguous, or unsupported.

## Done Means

- The requested output exists.
- The run report is complete.
- Protected definitions were not changed, or changes were explicitly flagged.
- Open issues requiring human judgment are listed.
- Mechanical checks were run when relevant, or skipped with a reason.
