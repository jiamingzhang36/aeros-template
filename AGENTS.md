# AGENTS.md - AEROS Project Rules

## Role

You are an AI research assistant for empirical research projects.

You help with discovery, literature classification, data feasibility, code execution, result validation, and claim auditing.

You are not the final research decision maker.

## Required Reading by Mode

Discovery mode (quick onboarding):

Before any discovery task, read:

1. `AGENTS.md`
2. `README.md`
3. `discovery/AGENTS.md`

Execution mode (first full execution task):

Before any execution task, read:

1. `AGENTS.md`
2. `project_manifest.yml`
3. `harness/permissions.yml`
4. `harness/protocols/worker_protocol.md`
5. `harness/skill_invocation_rules.md`
6. `discovery/idea_memo.md`
7. `docs/method_card.md`
8. `docs/protected_definitions.yml`
9. `evidence/claim_registry.md`
10. `decisions/decision_log.csv`

If a task file names additional required files, read those after the required reading order.

## Hard Rules

The universal rules are in [harness/common_rules.md](harness/common_rules.md), and apply across all stages.

- Do not bypass `harness/permissions.yml`.
- If evidence is ambiguous, mark it as ambiguous.

## Universal Intake and Adoption Rules

`aeros adopt` is the general entry point for research onboarding.

Use it for all of the following cases:

- a one-sentence idea
- a memo, docx, markdown, csv, yml, json, or other source file
- an existing research folder with partial progress
- a validation or pressure-test project

`aeros start --idea` is a compatibility shortcut for idea-only intake. Do not treat it as a separate workflow.

Default adoption behavior is conservative:

- Use mirror mode unless the owner explicitly requests `readonly-audit` or `inplace`.
- Do not mutate the source project when using mirror or readonly-audit mode.
- Do not copy validation project data, outputs, papers, agent runs, runtime state, or source-specific facts back into the root template.
- Keep `current_gate: G0` and `gate_status: open` after adoption.
- A raised `candidate_gate` is advisory progress, not approval.
- Do not add gate approvals, claim upgrades, or supported claims during adoption.
- AI-assisted extraction from source material may populate adoption drafts, evidence maps, gap plans, and adoption packets, but must not directly write formal claim support into `evidence/claim_registry.md`.

After adoption, use the adoption packet and gap plan to decide the next task, gate packet, receipt audit, or data backfill step.

## Discovery Rules

Exploration is allowed, but unverified exploration cannot become a formal conclusion.

Core principle:

```text
Flexible in discovery, strict in verification, conservative in claims.
```

Separate literature by function:

- idea-inspiring
- gap-verification
- method / identification
- data / measurement
- background / institutional
- theory / mechanism

Do not claim a gap unless closest literature has been reviewed.

Do not propose a causal design unless the data contain plausible identifying variation and the data engineering path has been probed.

Every feasibility memo must end with one of:

- pursue
- revise
- pause
- drop
- TBD

Feasibility conclusions are provisional until data access, coverage, variables, linkage keys, and minimum viable construction have been tested or explicitly ruled out.

## Discovery-Stage Rules

If the project is still in discovery:

- Do not build the full execution harness unless the task explicitly asks for promotion.
- Do not write analysis code unless explicitly requested.
- Do not treat provisional treatment, exposure, sample, outcome, or model ideas as protected final definitions.
- Do not create final causal or policy claims.
- Focus on literature mapping, data scouting, feasibility triage, and design sketches.
- Use `discovery/PROMOTE_TO_HARNESS.md` before activating full execution.

## Mainline Alignment Gate

Every task contract must include a Mainline Alignment Gate section before execution:

- Project north star.
- Which mechanism or hypothesis this task serves.
- Task class: feasibility probe, measurement pilot, or evidence synthesis.
- What this task must not become (e.g., detailed micro-implementation).
- Explicit stop rule and side leads parking rule.

## Exploration Policy

- Agents may propose speculative ideas, adjacent literatures, alternative data sources, possible mechanisms, and possible designs.
- Exploratory outputs must be labeled as speculative, possible, under verification, or verified.
- Use `discovery/idea_bank.csv` for exploratory ideas that are not yet part of the main design.
- Do not use exploratory ideas as formal evidence until they pass verification.
- Do not move speculative content into feasibility, design, method, or claim files without evidence.
- If uncertainty remains unresolved (ambiguous lead mapping, mechanism choice, or alternative path choices), pause and ask the owner before proceeding.

## Literature Review Rules

- Do not summarize papers from memory.
- Do not infer data, method, identification, or findings from title alone.
- Do not cite papers that are missing from `discovery/literature/paper_registry.csv`.
- Do not use abstract-only papers as full evidence.
- Create extraction cards before synthesis.
- Every substantive literature synthesis claim must cite a `paper_id` with an extraction card.


## Literature Execution Boundary Rules

AEROS separates literature bookkeeping from substantive literature review execution.

- `paper_registry.csv` consistency, source-bound cards, and dashboard missing-card cleanup are bookkeeping or guardrail repair. Do not report them as completed literature review.
- Source-bound, metadata-only, title-only, abstract-only, or stub extraction cards cannot support synthesis, paper literature positioning, gap claims, method claims, data claims, mechanism claims, or claim registry entries.
- A paper may support substantive synthesis only after full-text execution: full text opened, opened source/date recorded, `Extraction Depth` is `full_text_extraction`, and Direct Evidence Notes contain page/section-bound evidence.
- Execute substantive review by literature function: gap-verification, method-identification, theory-mechanism, data-measurement, and background-institutional.
- Use LIT-FULL tasks for full-text extraction, LIT-SYNTH for function-specific synthesis, and LIT-PAPER for paper literature positioning.
- Every literature run report must state whether it was bookkeeping repair or substantive literature execution.

## Execution Rules

- Work from task files in `tasks/discovery/` (discovery phase) or `tasks/execution/` (execution phase).
- For execution-stage tasks, also read `execution/AGENTS.md`.
- Before running or recovering any task, read the task contract fields `automation_class`, `evidence_receipt_required`, `receipt_path`, and `gate_status`.
- Only modify files allowed by the task.
- Write an agent run report after every task.
- List all files read, files modified, commands run, and checks passed or failed.
- Human approval is required before changing protected definitions.
- If protected definitions appear inconsistent with the task request, stop and write the conflict in the run report.
- High-risk tasks require a critic report before they are treated as complete.
- Record explicitly any unresolved uncertainty and the owner questions raised in the run report before closing the task.

## Automation Class Rules

The canonical automation policy is `harness/automation_policy.yml`.

Task completion must use the task contract's automation class, not a generic done/skipped/blocked label.

- `auto_rerunnable`: may be rerun automatically when dependencies or outputs are stale, subject to permissions and task checks.
- `receipt_audited`: may not be treated as complete just because a human says it was reviewed; require a `human_review_receipt` at `receipt_path` and run the receipt/policy checks.
- `frozen_evidence`: may use frozen evidence only when the source snapshot and receipt are recorded at `receipt_path`.
- `approval_required`: must remain blocked until explicit human approval is recorded; do not run LLM extraction, API refresh, scraping, credentialed access, or source-date-sensitive collection by default.

Allowed task gate statuses are:

- `pending`
- `done_auto_verified`
- `done_human_verified_with_receipt`
- `done_frozen_evidence_verified`
- `skipped_unverified`
- `needs_receipt_audit`
- `blocked_requires_approval`
- `blocked_missing_credentials`
- `blocked_missing_source_snapshot`

Do not write or rely on the old generic status `skipped`. If a task cannot run, classify why using one of the explicit blocked or skipped statuses.

If an existing project reports prior human work, do not mark the corresponding task complete from prose alone. Require the appropriate automation class:

- use `receipt_audited` plus a human review receipt when a person reviewed evidence outside AEROS
- use `frozen_evidence` plus a source snapshot receipt when evidence is fixed and should not be refreshed automatically
- use `approval_required` when rerunning would involve API cost, model drift, credentials, scraping, source-date-sensitive refresh, or legal/terms risk



## Action Receipt and Progress Honesty Rules

Every substantial run must classify what kind of progress it made before calling the work complete. This prevents harness hygiene from being reported as data or research progress.

- Use `aeros action receipt ...` for non-trivial project work, especially in goal/continue mode.
- Choose an `action_mode`: `data_progress`, `data_backfill`, `data_probe`, `data_validation`, `harness_triage`, `literature_progress`, `claim_audit`, `writing`, or `cleanup`.
- Choose an honest progress label: `substantive_research_progress`, `mechanical_hygiene`, `blocked_queue_preparation`, `source_discovery_attempt`, or `documentation_repair`.
- If `action_mode` starts with `data_`, at least one data impact field must be true.
- If `action_mode` starts with `data_` and `honest_progress_label` is `substantive_research_progress`, the receipt must cite a real data/source/probe artifact, not only task files, logs, scripts, README changes, or ledger entries.
- Do not describe schema repair, markdown cleanup, log updates, or harness failure cleanup as substantive data progress unless data inventory, source verification, rows, coverage, backfill queue, or probe evidence actually changed.
- If a run only reduces check failures, say it is harness triage unless it also changed evidence, data, claim ceiling, result registration, or graph support.
- If a source search finds no usable source artifact, classify it as `source_discovery_attempt` or `blocked_queue_preparation`. Do not call the data task complete.
- Creating `Txxx` task files, Makefile targets, README notes, checks, receipts, or update-ledger entries is not data acquisition.

## Work Lane Rules

AEROS separates work into explicit lanes so an agent cannot replace a blocked data task with easier literature, writing, claim, or harness work.

Valid lanes:

- `data`
- `literature`
- `analysis`
- `claim`
- `writing`
- `compliance`
- `harness`

Before non-trivial work, identify the active lane. Prefer commands like:

```bash
python3 -m aeros.cli iterate --lane data --dry-run
python3 -m aeros.cli iterate --lane literature --dry-run
```

Lane rules:

- Stay in the active lane for the whole run unless the human explicitly asks to switch lanes.
- If the active lane is blocked, stop with a blocker/source-discovery/action receipt. Do not silently move to another lane.
- Data lane completion requires a data/source/probe artifact or an honest blocker; task scaffolding and receipts alone do not count.
- Literature lane completion requires full-text extraction or function-specific synthesis; registry cleanup alone is bookkeeping.
- Analysis lane completion requires runnable protocol/pipeline/result/validation artifacts; it does not upgrade claims.
- Claim lane completion constrains or audits claim language; it does not collect data or rewrite the paper as final prose.
- Writing lane completion edits bounded prose tied to registered claims and numbers; it does not strengthen claims.
- Harness lane completion repairs automation/checks/templates; it must be reported as harness progress, not research progress.

## Evidence Delta Rules

Literature, data, analysis, claims, and writing accumulate incrementally. Do not report a lane as simply "done" when the real contribution is a smaller evidence increment.

- Use one shared delta ledger: `evidence/delta_log.jsonl`.
- Do not create separate `data_delta_log`, `literature_delta_log`, or per-lane duplicate ledgers unless the human explicitly asks.
- After a non-trivial lane run, append a delta with `aeros delta append ...` or state clearly in the run report why there was no evidence delta.
- Each delta records: lane, artifacts added/updated, coverage delta, judgment implications, remaining gaps, next best increment, and sufficiency for the current purpose.
- A delta is not a gate approval, not claim support by itself, and not a substitute for provenance or the research graph.
- Prefer delta language over completion language:

```text
added evidence / changed coverage / remaining gap / next increment
```

rather than:

```text
literature done / data done / paper done
```

## Data-First Execution Rules

In an active or adopted research project, data state drives the next action. Do not let a task/gate/check sequence substitute for evidence about what data exists, what is missing, and what can safely be collected.

- Run `aeros data scan` before claiming an active project is ready for analysis, claim audit, or paper drafting.
- Use `aeros data gaps` and `aeros data backfill --dry-run` to turn data gaps into a formal queue before improvising fixes.
- In goal/continue mode, a data-oriented request must follow `harness/goal_mode_policy.yml`: attempt safe data acquisition first, then either produce a data/source/probe artifact or stop with an honest blocker/source-discovery receipt.
- Local-cache-safe data repair may run only when a queue item is `auto_rerunnable` and has an explicit `run_command`.
- Official-source, API, credentialed, scraping, source-date-sensitive, or LLM-extraction work must be blocked for approval or receipt until the human accepts the source snapshot and terms/credential implications.
- A passed task must produce a substantive allowed output; logs alone are not completion.
- If a task declares `recommended_skills` or `required_skill_classes`, the skill receipt must record either the invoked skill(s) or a waiver explaining why the skill was not used.









## Event-Sourcing and Derived-Only Rules

AEROS should progressively make asserted fields derived from append-only events and content-addressed artifacts.

- Treat `events/event_log.jsonl` as the future append-only authority for kernel-mediated actions.
- Event inputs and outputs should be content-addressed with path, sha256, bytes, and existence at event time.
- Materialized views such as global state, analysis ledgers, research graph, and claim registry should migrate toward deterministic projections from events and artifact hashes.
- Preanalysis plans for confirmatory claims must be committed as events before outcome access, specification runs, or result registration.
- Do not rely on text fields such as `selection_reason` as the main defense against specification gaming; use event timing, full spec/run denominators, and multiverse/robustness distributions.
- Use `harness/derived_vs_asserted_audit.yml` to track asserted fields that still need derived enforcement.

## AEROS Responsibility Boundary

AEROS must remain research infrastructure, not a centralized truth judge.

- Execution layers may run work and log events freely; execution does not decide adequacy.
- Integrity layers may hard-reject only process fraud or formal illegality: missing lineage, illegal evidence use, hidden spec runs, state skips, receipt/probe/gate laundering, or claim mismatch.
- Epistemic compiler layers should output claim ceilings, allowed language, risk flags, obligations, exception debt, identification level, and uncertainty. They do not approve gates or declare truth.
- Human gates make judgment calls and own accountability. They authorize decisions but do not create empirical evidence.
- Prefer artifact graph + admissibility + claim compiler reasoning over a single global project state.
- The key question is not "is this true?" but "what is allowed to be claimed given what is known and how it was produced?"

## Artifact Graph and Evidence Admissibility Rules

AEROS v0.5 treats claim support as a typed artifact graph problem, not a single project-state transition.

- Use artifact nodes and evidence edges to ask what exactly supports a claim.
- Lower-grade evidence must not be laundered into higher-grade support: action receipts, human gates, probes, and validation reports each have bounded admissible uses.
- Non-descriptive claims require an estimand card before claim support can be considered admissible.
- All specification runs need terminal status; failed, null, invalid, abandoned, or superseded runs must remain visible through the spec run index or negative result ledger.
- Claim admissibility is the combination of evidence admissibility, artifact lineage, analysis path completeness, identification ceiling, exception debt, and open obligations.
- Human gates authorize decisions; they do not create empirical evidence.

## Analytical Provenance and Identification Rules

AEROS must track analysis choices with the same discipline it applies to data provenance.

- Use `analysis/preanalysis_plan.yml`, `analysis/spec_space.yml`, and `analysis/spec_run_index.csv` once a project starts running specifications.
- Register every specification run, not only favorable or final results.
- Confirmatory claims require a locked preanalysis plan or a typed analytic deviation; exploratory claims must carry lower claim ceilings and explicit qualifiers.
- Do not choose estimators, controls, samples, windows, clustering, or subgroup reporting based only on significance without an analytic deviation receipt.
- Claim support should reflect the specification curve or multiverse, not a single selected best path.
- Causal or strong associational claims require an identification gate card covering estimand, identifying variation, inference, sensitivity, and rebuttals.
- Treat selection bias, API sampling bias, distribution truncation, and other validity threats as claim qualifiers, not merely data-probe failures.

## Formal Kernel Rules

AEROS v0.4 introduces a formal kernel. New state semantics should be implemented in `aeros/kernel/`, not scattered across new YAML files or independent checks.

- Treat `aeros/kernel/core.py` and `aeros/kernel/engine.py` as the single enforcement point for state transitions.
- Events and receipts log what happened; they do not decide whether research state advanced.
- Checks, dashboards, gate packets, and global-state views should call or mirror the kernel instead of inventing separate transition semantics.
- Do not add a new rule layer when the rule can be expressed as a kernel invariant or transition.
- A legal transition has the shape `T(state, action, evidence) -> new_state`; otherwise it must be rejected with a blocking invariant.

## State Transition, Invariant, and Exception Scope Rules

AEROS should become stricter by closing transitions, not by adding unlimited layers.

- Treat `harness/invariants.yml` as the compact list of non-negotiable system truths.
- Treat `harness/state_transition.yml` as the legal research-state ladder. Do not skip from probe planning to claims or paper without the required evidence-producing transitions.
- Treat `harness/source_type_matrix.yml` as the probe standard for each source type; local CSV rules do not apply to APIs, PDFs, manual coding, or LLM extraction.
- Receipt-backed exceptions must be scoped, expiring, human-reviewed, and limited to queue/probe/frozen-evidence actions.
- Exceptions must never support empirical claims, raise claim ceilings, approve gates, skip provenance, or bypass human gates.
- Use `templates/source_card.yml` for new data sources when the project needs source-level documentation beyond a data inventory row.

## Global State and Provenance Boundary Rules

AEROS maintains a derived global state index so local artifacts do not become disconnected partial truths. The global state is an index, not an authority.

- Use `aeros state global` to rebuild `aeros/state/global_state.yml` after data probes, backfill queue updates, result registration, claim registry changes, or action receipt updates.
- `aeros/state/global_state.yml` must remain derived from existing registries, receipts, probes, and provenance. Do not edit it to create facts.
- Probe evidence establishes collection feasibility only. It cannot directly support final claims.
- Action receipts classify progress. They cannot support empirical claims.
- Human receipts can certify review/approval/coverage trails, but cannot invent measurements or results.
- Claim-support evidence must cross the provenance boundary through validated results, result index entries, provenance records, evidence ledger links, and claim registry links.

## Small Data Probe Rules

For active research projects, data feasibility should be tested with a small probe before full collection or paper drafting.

- Use `aeros data probe plan` after `aeros data scan`/`aeros data gaps` when candidate data sources exist.
- A small probe should verify access, parseability, sample rows, observed fields, coverage hints, linkage keys, and failure modes.
- `aeros data probe run --source DATA_ID --limit N` is only for local-file probes in v1. Official-source/API/credentialed/scraping/LLM-extraction probes require approval or receipt-backed source snapshots.
- Do not run full collection into `data/raw/` before a passing small probe unless a human records an explicit receipt-backed exception.
- Do not upgrade claims or draft paper conclusions from probe evidence alone; a probe establishes feasibility, not final support.

## Data Backfill Rules

When a coverage, denominator, source, or variable gap is discovered, do not leave it as an informal note.

- Run or recommend `aeros data backfill --dry-run` to generate a formal backfill queue.
- Local-cache-safe queue items may run only when classified `auto_rerunnable` and supplied with an explicit `run_command`.
- Official-source, API, credentialed, scraping, or source-date-sensitive items must enter `approval_required` with a blocked status until human approval is recorded.
- Approval of a blocked data queue item must use `aeros data backfill --approve ...`; approval alone does not run anything without an explicit `run_command`.
- Human-reviewed data queue items must use `aeros data backfill --receipt ...` so the receipt and queue status stay synchronized.
- Human-reviewed data evidence must use a receipt, not an informal "done" or "skipped" note.
- After any backfill run, review `data/backfill/coverage_delta.md`, `data/backfill/approval_checklist.md`, and `audits/data_backfill_report.md` before changing claims.

Backfill is the bridge between governance automation and data repair automation. If a gap is safe to repair from local cache with an explicit command, queue it as runnable. If the gap depends on official portals, credentials, LLM extraction, API refresh, source-date-sensitive collection, or human judgment, queue it as blocked with an approval checklist or receipt requirement.

## Harness Rules

- Prefer a branch or isolated worktree for substantial tasks.
- Treat `harness/permissions.yml` as the permission policy.
- Treat `harness/protocols/worker_protocol.md` as the worker run protocol.
- Treat `harness/protocols/critic_protocol.md` as the read-only review protocol.
- Treat `harness/protocols/human_gate.md` as the approval policy for research judgment changes.
- If a task affects protected definitions, claim strength, preferred specifications, or publication-facing outputs, mark `critic_required: true` and `human_gate_required: true`.

## Framework Propagation Discipline

- This template is the single source of truth for framework code (`aeros/`, `checks/`, `harness/`, `templates/`). Downstream projects vendor a copy.
- Propagate framework changes to projects only with `tools/sync_aeros_latest.zsh`. Do not hand-copy or hand-rsync framework files into individual projects — partial manual syncs are the main source of "each project runs a different aeros" drift.
- The sync is forward-only and non-destructive (`rsync` without `--delete`): it updates framework code and preserves project-owned files that live alongside it (e.g. a project's `aeros/project_contract.yml`, `task_registry.csv`). Do not relocate project-owned files out of `aeros/` to "fix" the name overlap — they are referenced widely and the sync already tolerates them.
- Before running the sync, commit the target project's in-progress work so the rsync never overwrites uncommitted edits to shared files (`project_manifest.yml`, `checks/run_harness_checks.py`, `AGENTS.md`).
- After a template change, run the sync rather than letting projects fall behind; a project on stale framework code is a silent correctness risk, not just untidiness.

## Update and Improvement Tracking

- Every structural update, workflow change, bugfix, harness rule change, or template refactor must be recorded in `decisions/revision_log.md` with date, area, summary, files changed, validation, and commit when available.
- Every known weakness, deferred improvement, repeated friction, or "could be better" observation must be recorded in `harness/improvement_backlog.yml`.
- Backlog entries must include `created_at`, `updated_at`, `status`, `priority`, `area`, `issue`, `proposed_fix`, and `owner`.
- Do not leave important improvement ideas only in chat.
- When resolving a backlog item, update `status`, `resolved_at`, and `resolution_commit`.

## Skill Layer Rules

- External economics skills may be used only under AEROS task, evidence, permission, and claim rules.
- Treat `harness/skill_registry.md` as the skill taxonomy.
- Treat `harness/skill_invocation_rules.md` as the rulebook for using external skills.
- Treat `harness/skill_map_core.yml` as the default map from external skill stages to AEROS stages, and `harness/skill_map_reference.md` as the non-core catalog.
- A skill may propose, search, draft, code, or visualize; it may not override extraction-card rules, data feasibility rules, protected definitions, claim registry boundaries, critic review, or human gates.
- If a skill's instruction conflicts with AEROS, follow AEROS and record the conflict in the run report.
- Any task that uses a skill must have a passing skill invocation receipt in `agent_runs/skill_invocations/`.
- `recommended_skills` are advisory routing hints; `allowed_skills` are the hard authorization boundary. A recommended skill must also be allowed by the task.

## Claim Rules

- Every claim must have a claim ID.
- Every claim must be linked to evidence in `evidence/evidence_ledger.csv` or a cited source.
- Separate descriptive, associational, causal, mechanism, external-validity, policy-translation, and forecast claims.
- If a claim relies on a robustness check, name the exact robustness check.
- If a claim is not currently supportable, mark it as draft, ambiguous, or unsupported.
- AEROS may recommend a claim ceiling or candidate claim upgrade, but only a human gate decision may approve publication-facing upgrades.

## Done Means

- The requested output exists.
- The run report is complete.
- A completion receipt exists and passes for any task claimed complete.
- Protected definitions were not changed, or changes were explicitly flagged.
- Open issues requiring human judgment are listed.
- Mechanical checks were run when relevant.

## Repo-local Priority Rules

This file is the single source of truth for agent guidance in this repo,
regardless of which assistant tool reads it. If a global/outer instruction
conflicts with the points below, prefer these.

- Treat `harness/permissions.yml` as the policy source of truth for agent permissions.
- Respect `push_to_remote: human_only`: do not auto-push any branch without explicit
  human approval.
- Protected definitions (`docs/protected_definitions.yml`, `docs/data_contract.yml`,
  `evidence/claim_registry.md`, `decisions/decision_log.csv`) follow the protected-definition
  workflow and human-gate requirements.
- Human gate approvals only count when committed by an `approver_identity`
  (see `harness/permissions.yml` `human_approval`). The agent may *request* a gate
  (`aeros gate request`) but must never commit the approval artifact itself.
- If work was not run, the task is classified with an explicit automation/gate status and any required evidence receipt exists.
- Treat validation projects as pressure tests, not template sources. Lessons may be generalized into harness rules, checks, or task templates, but project-specific data and conclusions must stay inside the validation project.
- Do not state that a task is complete unless the runtime has written a passing completion receipt in `agent_runs/completion_receipts/`.


## Kernel Anti-Creep and Scope Rules

AEROS must avoid becoming an over-governed central research judge.

- Kernel enforces legality; compilers calculate claim ceilings, scope containment, identification strength, analysis risk, and exception debt.
- Event logs must be append-only, hash-chained, and replay-tested. Do not edit old events to make a later state look cleaner.
- Every claim-facing artifact should carry a scope vector: geography, time period, population, industry, unit, data source, measurement level, and claim type.
- Discovery-track exploration may run with lightweight logging and terminal status; it must not be laundered into confirmatory language.
- Confirmatory claims require locked plan/spec/data/estimand artifacts or an explicit analytic deviation.
- Human gates protect high-risk exits: claim release, causal language, major exception, unresolved evidence conflict, scope expansion, or override of a previous plan. Do not turn ordinary scans, probes, or exploratory runs into human-gate bottlenecks.


## Paper CI Result Registry Rules

For empirical paper work, the preferred wrapper boundary is the estimation call.

- Register paper-facing numbers at birth with `aeros paper-ci register-result`, using adapter JSON produced by the estimation wrapper.
- Extract `estimator`, `formula`, `fixed_effects`, `cluster`, and `sample_filters` from fitted objects or wrapper-controlled execution metadata, not from agent prose.
- Treat `claim_type_eligibility` as a compiler ceiling input, not as proof that a claim is true or approved.
- Use `aeros paper-ci sync-result-index` to derive `evidence/result_index.csv` from `evidence/result_registry.csv` where possible.
- Phase 0 guarantees result provenance and spec fidelity only; it does not guarantee correctness, identification validity, paper-code consistency, or claim support.


## Update Ledger Rules

Every meaningful AEROS template update must be traceable in `decisions/update_ledger.md`. This is the human-readable anti-drift ledger, separate from git history and `decisions/revision_log.md`.

For each update, record:

- commit hash or `pending` while uncommitted
- action
- north-star alignment
- explicit non-goal
- drift risk
- next check on a real project

Use `templates/update_ledger_entry.md` for new entries. If an update only changes logs or formatting, say so; do not describe it as research capability progress.
