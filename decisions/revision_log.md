# Revision Log

Use this file to track template or project-level changes that alter workflow, evidence standards, task contracts, checks, or file structure. Record local date/time with timezone and the commit when available.

## Revisions

| Date/time | Revision ID | Commit | Change type | Files changed | Reason | Checks | Notes |
|---|---|---|---|---|---|---|---|
| 2026-06-19 00:00 +0800 | REV031 | 99937bd | external economics tool integration | `harness/external_tool_registry.yml`, `harness/econ_literature_discovery_policy.yml`, `harness/aea_replication_policy.yml`, `templates/aea_data_package_manifest.yml`, `checks/check_external_tool_registry.py`, `checks/check_aea_replication_alignment.py`, `aeros/paper_ci/result_registry.py`, `templates/result_registry_record.json`, `harness/result_adapter_contract.yml`, `AGENTS.md`, `harness/skill_registry.md`, `harness/practical_skill_menu.md`, `discovery/literature/literature_rules.md`, `project_manifest.yml`, `checks/run_harness_checks.py`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `decisions/update_ledger.md` | Register economics tools as reference/advisory/adapter candidates, align replication packages to AEA guidance, and record optional endpoint/command reproducibility metadata | py_compile, external tool registry check, AEA replication alignment check, result registry check, full harness | External tools remain advisory; they cannot approve gates, certify identification, strengthen claims, or replace extraction/provenance checks. |
| 2026-06-19 00:00 +0800 | REV030 | 8559333 | evidence delta ledger | `aeros/runtime/evidence_delta.py`, `checks/check_evidence_delta_log.py`, `templates/evidence_delta_record.json`, `aeros/cli.py`, `AGENTS.md`, `agent_runs/TEMPLATE_agent_run_report.md`, `project_manifest.yml`, `checks/run_harness_checks.py`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `harness/derived_vs_asserted_audit.yml`, `decisions/update_ledger.md` | Track incremental evidence growth across lanes with one shared delta log instead of per-lane ledgers | py_compile, delta check, delta CLI dry-run, full harness | Delta records progress increments; they do not approve gates or support claims by themselves. |
| 2026-06-19 00:00 +0800 | REV029 | 18c2e34 | work-lane routing | `aeros/runtime/work_lane.py`, `checks/check_work_lanes.py`, `harness/work_lane_policy.yml`, `aeros/runtime/controller.py`, `aeros/runtime/kernel.py`, `aeros/runtime/contract.py`, `aeros/cli.py`, `AGENTS.md`, `agent_runs/TEMPLATE_agent_run_report.md`, `tasks/TEMPLATE_task.md`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `decisions/update_ledger.md` | Separate data, literature, analysis, claim, writing, compliance, and harness work surfaces so blocked work cannot silently become a different lane | py_compile, lane check, lane dry-runs, full harness after hash backfill | `aeros iterate --lane <lane>` is a focus control; it does not weaken gate/check semantics. |
| 2026-06-19 00:00 +0800 | REV028 | 04f3925 + ebaecaa | harness side-effect reduction | `checks/build_agent_runs_index.py`, `checks/check_pipeline_runs.py`, `decisions/update_ledger.md` | Prevent validation from rewriting unchanged index files or creating pycache artifacts | full harness after hash backfill | Keeps harness checks closer to observe-only behavior in restricted workspaces. |
| 2026-06-19 00:00 +0800 | REV027 | c9953b1 | goal-mode data honesty | `aeros/runtime/action_receipt.py`, `checks/check_goal_mode_data_progress.py`, `harness/goal_mode_policy.yml`, `AGENTS.md`, `agent_runs/TEMPLATE_agent_run_report.md`, `checks/run_harness_checks.py`, `project_manifest.yml`, `harness/invariants.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `decisions/update_ledger.md` | Prevent goal/continue mode from reporting data acquisition when only task/report/receipt/scaffolding files changed | py_compile, action receipt check, goal-mode data-progress check, fault injection | Data searches that find no source must be labeled `source_discovery_attempt` or `blocked_queue_preparation`, not complete substantive data progress. |
| 2026-06-14 00:00 +0800 | REV015 | this commit | update/improvement tracking | `AGENTS.md`, `harness/improvement_backlog.yml`, `checks/check_improvement_backlog.py`, `checks/run_harness_checks.py`, `project_manifest.yml`, `decisions/revision_log.md` | Add dated improvement backlog and require structural updates/future improvements to be tracked outside chat | `checks/run_harness_checks.py --timeout 30` pass | Backlog starts with skill-router auto-invocation and external evaluation follow-ups. |
| 2026-05-28 22:47 +0800 | REV014 | this commit | task compatibility & docs cleanup | `execution/AGENTS.md`, `examples/tasks/execution/T004_result_validation.md`, `tasks/discovery/*.md`, `tasks/execution/*.md`, `decisions/revision_log.md` | Fix broken `tasks/` compatibility links, normalize T004 task section order, and finalize execution-rules/task-example cleanup with verification | `checks/run_harness_checks.py` pass | `tasks/` now resolves to example-backed task files, including D001 and T004, and the full harness suite passes. |
| 2026-05-28 20:57 +0800 | REV011 | this commit | task governance | `tasks/discovery/*.md`, `tasks/execution/*.md`, `AGENTS.md`, `README.md`, `harness/protocols/human_gate.md`, `harness/protocols/full_run_checklist.md` | Require explicit human escalation on unresolved uncertainty | not run (requested change only) | Prevents blind continuation when task direction is ambiguous. |
| 2026-05-28 20:42 +0800 | REV010 | this commit | task governance | `tasks/discovery/*.md`, `tasks/execution/*.md`, `checks/check_task_contract.py`, `AGENTS.md`, `README.md`, `harness/protocols/full_run_checklist.md` | Add Mainline Alignment Gate to every task contract as anti-drift control | not run (requested change only) | Prevents partial task execution from replacing project mainline and hardens stop-rule discipline. |
| 2026-05-28 18:39 +0800 | REV009 | this commit | terminology | `data_inventory.csv`, `idea_bank.csv`, task docs | Generalize source memo tracing to intake tracing | `checks/run_harness_checks.py` pass | Use `intake_ref` and `intake_priority` for any initial material, not only memos. |
| 2026-05-28 18:31 +0800 | REV008 | 39ab92c | task structure | `tasks/discovery/D*.md`, `README.md` | Renumber discovery tasks sequentially after consolidation | `checks/run_harness_checks.py` pass | Current discovery sequence is D001-D006. |
| 2026-05-28 18:26 +0800 | REV007 | 39aff96 | task structure | `tasks/discovery/D002*`, `tasks/discovery/D005*`, removed former D003/D006 | Merge overlapping discovery tasks | `checks/run_harness_checks.py` pass | Data scouting absorbed feasibility triage; literature verification absorbed extraction. |
| 2026-05-28 18:21 +0800 | REV006 | a659ff8 | simplification | `data_inventory.csv`, `idea_bank.csv`, checks, `tasks/discovery/*.md`, `tasks/execution/*.md` | Merge source memo tracing into existing discovery tables | `checks/run_harness_checks.py` pass | Removed separate source memo trace file/check. |
| 2026-05-28 17:09 +0800 | REV005 | 6151190 | data feasibility | `data_inventory.csv`, `feasibility_memo.md`, D002/D003/T002, README | Require skill-assisted data probing before feasibility conclusions | `checks/run_harness_checks.py` pass | Records skills considered, used, blocked, and next probes. |
| 2026-05-28 17:07 +0800 | REV004 | 9ecc9af | data feasibility | `feasibility_memo.md`, `feasibility_matrix.md`, D002/D003/T002, README | Add provisional data feasibility gates | `checks/run_harness_checks.py` pass | Separates source existence from data feasibility and causal readiness. |
| 2026-05-28 16:56 +0800 | REV003 | e333f63 | literature evidence | literature checks, D007, citation audit, extraction template, README | Tighten literature evidence workflow | `checks/run_harness_checks.py` pass | DOI preferred but not required; stable locator and extraction chain required for evidence use. |
| 2026-05-28 15:26 +0800 | REV002 | f45c5af | skill governance | skill menu / related docs | Tier research skills by default use | not recorded | Establishes core/optional/reference skill handling. |
| TBD | REV001 | TBD | project setup | TBD | Initial setup | TBD | Fill this row when instantiating a project from the template. |
| 2026-05-28 22:34 +0800 | REV013 | this commit | workflow & governance cleanup | `checks/check_literature_tools.py`, `checks/check_git_guardrails.py`, `checks/check_agent_runs_tools.py`, `checks/run_harness_checks.py`, `project_manifest.yml`, `tasks/TEMPLATE_task.md`, `tasks/discovery`, `tasks/execution`, `examples/tasks/TEMPLATE_task.md`, `examples/tasks/discovery`, `examples/tasks/execution`, `examples/tasks/README.md`, `AGENTS.md`, `discovery/AGENTS.md`, `discovery/literature/AGENTS.md`, `discovery/literature/literature_rules.md`, `execution/AGENTS.md`, `harness/common_rules.md`, `README.md` | not run (requested change only) | Consolidate checks into 3 aggregate entries, relocate templates under `examples/tasks/` with compatibility links, and de-duplicate repeated AGENTS rules to reduce maintenance drift. |

## REV025 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: event sourcing / derived-only audit
- summary: Added content-addressed event primitives, deterministic replay, preregistration happens-before checks, a derived-vs-asserted attack surface audit, and CLI event append/replay commands.
- files:
  - aeros/kernel/events.py
  - aeros/kernel/event_replay.py
  - checks/check_event_log_replay.py
  - checks/check_preanalysis_happens_before.py
  - checks/check_derived_vs_asserted_audit.py
  - harness/derived_vs_asserted_audit.yml
  - harness/event_sourcing_policy.yml
  - aeros/cli.py
  - checks/run_harness_checks.py
  - project_manifest.yml
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This does not migrate old ledgers yet; it establishes the event-sourcing foundation required to turn asserted fields into deterministic derived views.

## REV024 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: architecture semantic correction
- summary: Clarified AEROS v0.5 responsibility boundaries: execution logs work, integrity rejects process fraud/formal illegality, the epistemic compiler emits claim ceilings and allowed language, and human gates make judgment calls.
- files:
  - docs/architecture_v0_5.md
  - aeros/kernel/README.md
  - aeros/kernel/artifact_graph.py
  - aeros/kernel/engine.py
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This is a semantic correction, not a new module. AEROS should decide what is allowed to be claimed, not what is scientifically true.

## REV023 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: typed artifact graph / evidence admissibility
- summary: Added the v0.5 typed artifact graph kernel, evidence type lattice, admissibility matrix, estimand cards, negative result ledger, and checks for artifact admissibility, estimands, and failed/abandoned spec visibility.
- files:
  - aeros/kernel/artifact_graph.py
  - harness/evidence_type_lattice.yml
  - harness/admissibility_matrix.yml
  - templates/estimand_card.yml
  - templates/negative_result_ledger.csv
  - checks/check_artifact_admissibility.py
  - checks/check_estimand_cards.py
  - checks/check_negative_result_ledger.py
  - checks/run_harness_checks.py
  - project_manifest.yml
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This shifts the north star from a linear project FSM toward claim-level admissibility over a typed artifact graph with obligations and exception debt.

## REV022 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: analytical provenance / identification integrity
- summary: Added an analysis integrity policy, preanalysis/specification templates, spec-run ledger checks, Toulmin claim-card schema checks, identification gate checks, and a circuit-breaker meta-monitor to close the analytical provenance gap.
- files:
  - harness/analysis_integrity.yml
  - harness/claim_toulmin_schema.yml
  - templates/preanalysis_plan.yml
  - templates/spec_space.yml
  - templates/spec_run_index.csv
  - templates/claim_card.yml
  - templates/analytic_deviation.yml
  - templates/identification_gate.yml
  - checks/check_analysis_ledger.py
  - checks/check_claim_toulmin_schema.py
  - checks/check_identification_gate.py
  - checks/check_meta_monitor.py
  - aeros/kernel/constraints.py
  - harness/provenance_boundary.yml
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This closes the largest remaining research-CI gap: a provenance-valid result is not automatically analytically valid unless specification search, deviations, and identification assumptions are visible.

## REV021 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: v0.4 formal kernel scaffold
- summary: Added the AEROS formal kernel with typed State, Action, Evidence, transition enforcement, executable invariants, event log primitives, and adversarial tests for fake progress, probe bypass, and receipt laundering attacks.
- files:
  - aeros/kernel/__init__.py
  - aeros/kernel/core.py
  - aeros/kernel/constraints.py
  - aeros/kernel/engine.py
  - aeros/kernel/events.py
  - aeros/kernel/README.md
  - tests/adversarial/test_kernel_attacks.py
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This is the compatibility-first v0.4 kernel foundation. Existing v0.3 YAML/check/receipt layers remain in place and should be migrated to kernel projections over time.

## REV020 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: state machine constraints / exception hardening
- summary: Added invariants, legal state transitions, a source-type probe matrix, scoped exception validation, and a source-card template so AEROS v0.3 can behave like a constrained research CI rather than a growing checklist.
- files:
  - harness/invariants.yml
  - harness/state_transition.yml
  - harness/source_type_matrix.yml
  - checks/check_exception_scope.py
  - templates/source_card.yml
  - harness/provenance_boundary.yml
  - checks/run_harness_checks.py
  - project_manifest.yml
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: Receipt-backed exceptions are intentionally narrow: they may allow a scoped queue/probe/frozen-evidence action but cannot support claims, raise claim ceilings, approve gates, or bypass provenance/human gates.

## REV019 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: formal state / provenance boundary
- summary: Added a derived global state index, probe failure taxonomy, action-receipt causal attribution, and provenance boundary rules to make AEROS constraints more explicit and composable.
- files:
  - aeros/runtime/global_state.py
  - checks/check_global_state.py
  - checks/check_provenance_boundary.py
  - harness/probe_failure_taxonomy.yml
  - harness/provenance_boundary.yml
  - aeros/runtime/action_receipt.py
  - aeros/runtime/data_probe.py
  - aeros/cli.py
  - project_manifest.yml
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: The global state is derived only; it is not a new authority and must not approve gates, change claims, or substitute for provenance.

## REV018 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: action receipts / small data probes
- summary: Added action-progress receipts and a small data probe layer so AEROS distinguishes substantive data/research progress from harness hygiene and requires probe evidence before full collection.
- files:
  - aeros/runtime/action_receipt.py
  - aeros/runtime/data_probe.py
  - checks/check_action_receipts.py
  - checks/check_data_probe.py
  - aeros/cli.py
  - checks/run_harness_checks.py
  - project_manifest.yml
  - AGENTS.md
  - agent_runs/TEMPLATE_agent_run_report.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: Both layers are conservative: they validate and classify progress but do not approve gates, downgrade claims, or alter runtime gate state.

## REV017 - 2026-06-16 00:00 +0800

- commit: pending
- change_type: data-first automation / no-op prevention
- summary: Added a data-first runtime layer so active projects scan data state, materialize data gaps, plan backfill, and prevent task completion from becoming empty process.
- files:
  - aeros/runtime/data_first.py
  - aeros/cli.py
  - checks/check_data_first_readiness.py
  - checks/check_noop_runs.py
  - aeros/runtime/contract.py
  - aeros/runtime/skill_receipt.py
  - checks/run_harness_checks.py
  - project_manifest.yml
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested; intended smoke commands are `python3 -m aeros.cli data plan`, `python3 -m aeros.cli data scan --dry-run`, and `python3 checks/run_harness_checks.py --timeout 30`.
- notes: This is intentionally data-first and conservative: graph/gate/claim state is not changed by scan, gaps, or plan commands.

## REV016 - 2026-06-14 00:00 +0800

- commit: this commit
- change_type: tooling / synchronization
- summary: Promoted the AEROS desktop synchronization script into the versioned template tooling layer so synchronization behavior is tracked with the harness.
- files:
  - tools/sync_aeros_latest.zsh
- checks:
  - zsh syntax check for tools/sync_aeros_latest.zsh
  - script retains targeted project_manifest wiring for improvement backlog checks
- notes: The script remains conservative: it syncs framework files and injects required manifest wiring without overwriting project-specific manifests wholesale.

## 2026-06-16 - REV026 Paper CI Phase 0 result registry

- Added `aeros.paper_ci.result_registry` as the estimation-call result registry layer.
- Added `aeros paper-ci register-result`, `sync-result-index`, and `schema` CLI entry points.
- Added `harness/result_adapter_contract.yml`, `templates/result_registry_record.json`, and `checks/check_result_registry.py`.
- Clarified that result registry guarantees result-born provenance/spec extraction, not estimate correctness or claim approval.
