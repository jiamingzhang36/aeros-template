# Revision Log

Use this file to track template or project-level changes that alter workflow, evidence standards, task contracts, checks, or file structure. Record local date/time with timezone and the commit when available.

## Revisions

| Date/time | Revision ID | Commit | Change type | Files changed | Reason | Checks | Notes |
|---|---|---|---|---|---|---|---|
| 2026-06-22 00:00 +0800 | REV045 | 8690197 | controller loop semantics tightening | `aeros/runtime/controller_loop.py`, `aeros/cli.py`, `AGENTS.md`, `harness/improvement_backlog.yml`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Rename misleading budget stop to max-steps, distinguish artifact_changed from substantive_changed, and clarify IMPROVE-012 now tracks only framework graceful-degradation after CMPD upgrade | PASS: py_compile; PASS: run-until max-steps/no-progress dry-runs; PASS: check_next_action.py; PASS: check_improvement_backlog.py; PASS: full harness 82 checks | Keeps safety conservative while reducing mental-model drift around `aeros run --until`. |
| 2026-06-22 00:00 +0800 | REV045 | 0c380a0 | controller / literature routing | `aeros/runtime/next_action.py`, `checks/check_next_action.py`, `harness/improvement_backlog.yml`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Stop literature controller runs on explicit `blocked_fulltext` records before stale discovery previews, and restore lane-scoped fallback so explicit data/claim requests cannot drift to literature | `python3 checks/check_next_action.py`; CMPD target `python3 -m aeros.cli run --until no-progress --dry-run --lane literature`; full harness after sync | Routes P013/P016/P030-style blockers honestly; does not fetch, OCR, extract full text, or upgrade synthesis/claims. |
| 2026-06-22 00:00 +0800 | REV044 | 5b37c42 | bounded controller loop | `aeros/runtime/controller_loop.py`, `aeros/cli.py`, `checks/check_next_action.py`, `AGENTS.md`, `harness/improvement_backlog.yml`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Add `aeros run --until human-gate|blocked|no-progress|max-steps` so AEROS can safely continue deterministic next actions until authority, blocker, no-progress, or step-count stop | PASS: py_compile; PASS: run-until dry-runs; PASS: check_next_action.py; PASS: check_improvement_backlog.py; PASS: full harness 82 checks | Default controller executes only allowlisted safe preview/check commands; real task runs require explicit `--allow-task-runs` and still do not approve gates or upgrade claims. |
| 2026-06-22 00:00 +0800 | REV043 | bb0db72 | literature fulltext candidate verification | `aeros/runtime/literature_adapter.py`, `checks/check_literature_adapters.py`, `harness/econ_literature_discovery_policy.yml`, `harness/improvement_backlog.yml`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Prevent OA metadata, DOI/repository URLs, Cloudflare/security pages, SPA shells, and unrelated cache files from being mistaken for readable target-paper full text | PASS: check_literature_adapters.py; PASS: check_improvement_backlog.py; PASS: OpenAlex dry-run; PASS: full harness 82 checks | Adds route/blocker semantics only; does not fetch full text, OCR PDFs, write extraction cards, synthesize literature, or support claims. |
| 2026-06-22 00:00 +0800 | REV042 | 5fe6eb8 | Zotero fulltext semantics tightening | `aeros/runtime/literature_adapter.py`, `checks/check_literature_adapters.py`, `harness/econ_literature_discovery_policy.yml`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Reserve `full_text_available=yes` for indexed/readable Zotero text, keep PDF-only items as extraction/OCR-ready queue entries, and add deterministic parser fixtures | PASS: check_literature_adapters.py; PASS: Zotero dry-run; PASS: full harness 82 checks | Prevents PDF-on-disk from being confused with readable full text while keeping PDF-only routes actionable. |
| 2026-06-22 00:00 +0800 | REV041 | 170b042 | Zotero literature adapter bridge | `aeros/runtime/literature_adapter.py`, `aeros/cli.py`, `checks/check_literature_adapters.py`, `discovery/literature/fulltext_ready_queue.csv`, `discovery/literature/missing_fulltext_queue.csv`, `harness/econ_literature_discovery_policy.yml`, `aeros/runtime/init_project.py`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Add Zotero local-library search as a literature adapter that routes candidates into paper registry plus full-text-ready and missing-fulltext queues | py_compile, adapter check, Zotero dry-run, full harness PASS | Zotero availability is ROUTE_READY only; it does not complete full-text extraction, synthesis, gap claims, or claim support. |
| 2026-06-21 00:00 +0800 | REV040 | 196f37a | stale impact scope tightening | `aeros/runtime/stale_triage.py`, `aeros/runtime/next_action.py`, `checks/check_stale_triage.py`, `harness/stale_triage_policy.yml`, `aeros/runtime/init_project.py`, `decisions/update_ledger.md`, `decisions/revision_log.md` | Prevent paper/claim-registry stale outputs from being expanded into all active claims without deterministic links; add impact_scope and volatile-output free revalidation | py_compile, stale triage check, CMPD dry-run, full harness PASS | Keeps stale triage conservative while making impact attribution more precise: specific claims only when derived, unknown scope when not localizable. |
| 2026-06-21 00:00 +0800 | REV039 | pending | deterministic stale impact triage | `aeros/runtime/stale_triage.py`, `checks/check_stale_triage.py`, `harness/stale_triage_policy.yml`, `aeros/runtime/next_action.py`, `aeros/cli.py`, `checks/run_harness_checks.py`, `harness/check_profiles.yml`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `AGENTS.md`, `harness/improvement_backlog.yml` | Add three-bucket stale triage so stale tasks become rerun_required, revalidate_free, or suppress_as_irrelevant by deterministic DAG/fingerprint/claim-link evidence | pending targeted smoke and CMPD acid test | Triage is advisory and conservative: no LLM ranking, no state mutation, no claim downgrade, and suppression only when irrelevance is proven. |
| 2026-06-21 00:00 +0800 | REV038 | pending | efficiency cockpit / fast profiles | `harness/check_profiles.yml`, `aeros/runtime/context_graph.py`, `aeros/runtime/cockpit.py`, `checks/check_harness_profiles.py`, `checks/check_context_graph.py`, `checks/check_cockpit.py`, `checks/run_harness_checks.py`, `aeros/runtime/context_bundle.py`, `aeros/runtime/next_action.py`, `aeros/cli.py`, `AGENTS.md`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `harness/context_budget.yml`, `harness/context_graph_policy.yml`, `harness/improvement_backlog.yml`, `checks/check_update_ledger.py`, `checks/check_paper_package.py`, `checks/check_compliance_gate.py`, `harness/econ_literature_discovery_policy.yml` | Add a light daily cockpit over the heavy internal kernel: fast check profiles, stale context detection, context graph navigation, and lane-specific next actions | targeted smoke/full harness pass; hardcoded Python path removed; next-action iterate recommendations now default to dry-run | Profiles and cockpit are views/selection mechanisms only; they do not approve gates, weaken criteria, certify claims, or replace full harness for release. |
| 2026-06-21 00:00 +0800 | REV037 | pending | context engineering bundle | `aeros/runtime/context_bundle.py`, `checks/check_context_bundle.py`, `harness/context_budget.yml`, `templates/CONTEXT_BUNDLE.md`, `CONTEXT_BUNDLE.md`, `aeros/cli.py`, `AGENTS.md`, `checks/run_harness_checks.py`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `harness/improvement_backlog.yml` | Add `aeros context` as a compact source-anchored context layer so agents start with lane, next action, stop rule, blockers, recent deltas, and source hashes instead of rereading the whole project | not run | Context bundles are deterministic summaries only; they do not execute tasks, approve gates, certify claims, or prove substantive progress. |
| 2026-06-21 00:00 +0800 | REV036 | pending | literature/method fusion adapters | `aeros/runtime/literature_adapter.py`, `checks/check_literature_adapters.py`, `checks/check_citation_audit.py`, `aeros/cli.py`, `aeros/runtime/next_action.py`, `harness/econ_literature_discovery_policy.yml`, `harness/econ_method_advisory_policy.yml`, `harness/external_tool_registry.yml`, `discovery/literature/citation_audit.md`, `discovery/literature/citation_snowball_queue.csv`, `AGENTS.md`, `checks/run_harness_checks.py`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py` | Fuse existing literature/tool/skill pieces into deterministic lane routing without turning metadata into synthesis | not run | Literature adapter output is ROUTE_READY only; citation faithfulness checks structure, not scientific truth; method skills remain advisory and cannot certify identification or approve gates. |
| 2026-06-21 00:00 +0800 | REV035 | pending | deterministic next-action engine | `aeros/runtime/next_action.py`, `checks/check_next_action.py`, `templates/NEXT_ACTION.md`, `aeros/cli.py`, `CURRENT_STATE.md`, `AGENTS.md`, `harness/rollout_playbook.md`, `checks/run_harness_checks.py`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py` | Add `aeros next` as a deterministic recommendation layer so Codex does not need a human to manually decide the next lane/action every turn | syntax parse, `python3 -m aeros.cli next`, `checks/check_next_action.py`, full harness | `aeros next` recommends only; it does not execute tasks, approve gates, change state, certify claim support, or turn route readiness into substantive progress. |
| 2026-06-20 00:00 +0800 | REV034 | pending | operating dashboard / project state discipline | `CURRENT_STATE.md`, `templates/CURRENT_STATE.md`, `harness/status_label_policy.yml`, `decisions/human_gate_queue.yml`, `harness/rollout_playbook.md`, `checks/check_operating_dashboard.py`, `AGENTS.md`, `harness/completion_attestation_policy.yml`, `checks/run_harness_checks.py`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py` | Add a lightweight per-project state dashboard, three honest outcome labels, a unified human-gate queue, and a fixed AEROS rollout playbook so long threads do not blur route readiness, checks, and substantive progress | pending | The dashboard is operational state only; it does not certify research quality, data access, literature extraction, claim support, or gate approval. |
| 2026-06-20 00:00 +0800 | REV033 | pending | skill governance / data-first routing | `harness/skill_invocation_rules.md`, `harness/practical_skill_menu.md`, `harness/skill_registry.md`, `AGENTS.md`, `aeros/runtime/skill_router.py`, `checks/check_skill_layer.py`, `tasks/discovery/D004_variable_construction.yml`, `tasks/execution/T002_data_feasibility.yml` | Tighten the existing skill layer without adding duplicate policy files: data-lane tasks now have an explicit source-first skill chain, skill receipts are bounded to routing compliance, and data-lane contracts must authorize/recommend data skills | syntax parse, `checks/check_skill_layer.py`, `checks/check_skill_invocations.py` | This preserves skills as accelerators while preventing skill use from being reported as substantive data, literature, empirical, claim, or gate progress. |
| 2026-06-19 00:00 +0800 | REV032 | 203f9c0 | completion attestation | `aeros/runtime/completion.py`, `aeros/runtime/checks.py`, `harness/completion_attestation_policy.yml`, `templates/completion_attestation.yml`, `AGENTS.md`, `agent_runs/TEMPLATE_agent_run_report.md`, `examples/tasks/TEMPLATE_task.md`, `project_manifest.yml`, `tools/sync_aeros_latest.zsh`, `aeros/runtime/init_project.py`, `decisions/update_ledger.md` | Make task completion mechanically attest outputs, hashes, check commands, exit codes, and boundaries without adding a bulky parallel system | py_compile, completion receipt check, update ledger check, full harness, temp receipt smoke | Completion remains process evidence only; it does not prove scientific validity, identification quality, claim support, or human gate approval. |
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

- commit: 1376748
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

- commit: 1376748
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

- commit: 1376748
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

- commit: 1376748
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

- commit: 3b16b2d
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

- commit: ff63b77
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

- commit: ff63b77
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

## REV027 - 2026-06-22 00:00 +0800

- commit: pending
- change_type: controller kernel / typed action spec
- summary: Added typed ActionSpec v0 so deterministic next-action output has a controller-facing action object instead of treating the rendered command string as the main authority surface.
- files:
  - aeros/runtime/action_spec.py
  - aeros/runtime/next_action.py
  - aeros/runtime/controller_loop.py
  - checks/check_next_action.py
  - templates/NEXT_ACTION.md
  - templates/action_spec.yml
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: ActionSpec is a control-plane shrink step. It does not migrate state to SQLite, delete older CLI commands, approve gates, execute task runs without `--allow-task-runs`, certify scientific validity, or replace human decisions.

## REV028 - 2026-06-22 00:00 +0800

- commit: pending
- change_type: controller kernel / semantic progress
- summary: Tightened bounded controller safety with always-on action/wall-time/provider/cost limits, semantic progress hashes, frontier/action cycle detection, primary stop reasons, and orthogonal completion receipt fields.
- files:
  - aeros/runtime/controller_loop.py
  - aeros/cli.py
  - aeros/runtime/completion.py
  - aeros/runtime/next_action.py
  - checks/check_next_action.py
  - checks/check_cockpit.py
  - checks/check_context_bundle.py
  - checks/check_operating_dashboard.py
  - templates/completion_attestation.yml
  - templates/NEXT_ACTION.md
  - harness/status_label_policy.yml
  - harness/completion_attestation_policy.yml
  - harness/check_profiles.yml
  - harness/rollout_playbook.md
  - aeros/runtime/init_project.py
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
  - AGENTS.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: `SUBSTANTIVE_PRODUCED` is the preferred substantive-progress label. `SUBSTANTIVE_DONE` remains accepted only as a deprecated compatibility alias. Existing v2 completion receipts are still accepted; newly written receipts are version 3 with orthogonal outcome/contract/verification/progress/authority fields.

## REV029 - 2026-06-22 00:00 +0800

- commit: pending
- change_type: controller kernel / ActionSpec phase tracking
- summary: Added direct ActionSpec invariant checks, corrected completion progress_class taxonomy, and documented ActionSpec Phase 2 inversion so the current derived-shim implementation does not become the resting command-string authority.
- files:
  - checks/check_action_spec.py
  - checks/run_harness_checks.py
  - project_manifest.yml
  - harness/check_profiles.yml
  - aeros/runtime/completion.py
  - templates/completion_attestation.yml
  - aeros/runtime/init_project.py
  - harness/completion_attestation_policy.yml
  - docs/design/action_spec_inversion_plan.md
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This keeps ActionSpec Phase 1 honest. Producers still infer specs from rendered commands today; AEROS-IMPROVE-018 tracks the required Phase 2 inversion where next-action branches construct typed specs first and commands become renderings.

## REV030 - 2026-06-22 00:00 +0800

- commit: pending
- change_type: controller kernel / ActionSpec producer inversion
- summary: Implemented ActionSpec Phase 2 producer inversion so next-action branches declare typed ActionSpecs directly and computed actions must carry `producer_mode: declared`.
- files:
  - aeros/runtime/action_spec.py
  - aeros/runtime/next_action.py
  - checks/check_next_action.py
  - checks/check_action_spec.py
  - templates/NEXT_ACTION.md
  - templates/action_spec.yml
  - NEXT_ACTION.md
  - docs/design/action_spec_inversion_plan.md
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: `_infer_kind()` remains only as inferred-compat fallback for old/bare NextAction callers. Executor argv parsing is still present for compatibility and is tracked separately as AEROS-IMPROVE-019.

## REV031 - 2026-06-22 00:00 +0800

- commit: aff9ec9
- change_type: pipeline reconciliation / runtime environment
- summary: Added `aeros reconcile` as a low-authority post-pipeline derived-sync command and made pipeline run checks honor delegated command/runtime Python configuration.
- files:
  - aeros/runtime/reconcile.py
  - aeros/cli.py
  - checks/check_reconcile.py
  - checks/check_pipeline_runs.py
  - checks/run_harness_checks.py
  - harness/check_profiles.yml
  - project_manifest.yml
  - aeros/runtime/init_project.py
  - AGENTS.md
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: Reconcile refreshes derived projections only. It does not approve gates, recover tasks, upgrade claims, validate scientific correctness, or install project dependencies.

## REV032 - 2026-06-22 00:00 +0800

- commit: 849632f
- change_type: conversation guard / lane scope
- summary: Added session scope guard so chat-driven work can declare one active lane/objective and audit changed files for off-scope drift.
- files:
  - aeros/runtime/session_guard.py
  - aeros/cli.py
  - checks/check_session_scope.py
  - checks/run_harness_checks.py
  - harness/session_scope.yml
  - harness/check_profiles.yml
  - templates/session_contract.yml
  - project_manifest.yml
  - aeros/runtime/init_project.py
  - AGENTS.md
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: Session scope guard reports `SCOPE_DRIFT` but does not revert files, approve cross-lane work, certify research validity, or replace human judgment.

## REV033 - 2026-06-22 00:00 +0800

- commit: e783c77
- change_type: contract runtime consolidation
- summary: Added ExecutionProfile v1, ActionSpec authority/progress/hook fields, automatic reconcile post-run hooks, and semantic session-scope audit verdicts.
- files:
  - aeros/runtime/execution_profile.py
  - aeros/runtime/action_spec.py
  - aeros/runtime/controller_loop.py
  - aeros/runtime/session_guard.py
  - checks/check_execution_profiles.py
  - checks/check_pipeline_runs.py
  - checks/check_action_spec.py
  - checks/check_session_scope.py
  - checks/run_harness_checks.py
  - templates/action_spec.yml
  - templates/session_contract.yml
  - harness/session_scope.yml
  - harness/check_profiles.yml
  - project_manifest.yml
  - aeros/runtime/init_project.py
  - AGENTS.md
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - `python -m py_compile aeros/runtime/readiness.py aeros/runtime/init_project.py aeros/cli.py checks/check_readiness_vector.py checks/check_estimand_data_contract.py checks/check_evidence_units.py checks/check_parser_benchmark.py checks/check_adversarial_benchmark.py checks/check_execution_profiles.py`
  - `python checks/check_execution_profiles.py`
  - `python checks/check_action_spec.py`
  - `python checks/check_session_scope.py`
  - `python checks/check_pipeline_runs.py --mode smoke`
  - `python -m aeros.cli check --profile smoke --timeout 20`
- notes: This consolidates existing controls into typed contracts. It does not add a new research lane, migrate state to a database, approve gates, upgrade claims, or certify scientific validity.

## REV034 - 2026-06-22 00:00 +0800

- commit: e783c77
- change_type: research contracts / readiness projection
- summary: Added second-batch lightweight scaffolds for EstimandDataContract, EvidenceUnit, parser benchmark, adversarial benchmark, and readiness vector.
- files:
  - aeros/runtime/readiness.py
  - aeros/cli.py
  - checks/check_readiness_vector.py
  - checks/check_estimand_data_contract.py
  - checks/check_evidence_units.py
  - checks/check_parser_benchmark.py
  - checks/check_adversarial_benchmark.py
  - checks/run_harness_checks.py
  - templates/evidence_unit.yml
  - templates/parser_benchmark_case.yml
  - templates/adversarial_scenario.yml
  - harness/parser_benchmark.yml
  - harness/adversarial_benchmark.yml
  - harness/check_profiles.yml
  - project_manifest.yml
  - docs/data_contract.yml
  - aeros/runtime/init_project.py
  - AGENTS.md
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - `python -m py_compile aeros/runtime/readiness.py aeros/runtime/init_project.py aeros/cli.py checks/check_readiness_vector.py checks/check_estimand_data_contract.py checks/check_evidence_units.py checks/check_parser_benchmark.py checks/check_adversarial_benchmark.py checks/check_execution_profiles.py`
  - `python checks/check_readiness_vector.py`
  - `python checks/check_estimand_data_contract.py`
  - `python checks/check_evidence_units.py`
  - `python checks/check_parser_benchmark.py`
  - `python checks/check_adversarial_benchmark.py`
  - `python checks/check_harness_profiles.py`
  - `python -m aeros.cli readiness`
  - `python -m aeros.cli check --profile smoke --timeout 20`
  - `python -m aeros.cli init /private/tmp/aeros_second_batch_init_check --force`
  - `cd /private/tmp/aeros_second_batch_init_check && python /Users/jiamingzhang/aeros-template/checks/check_estimand_data_contract.py`
  - `cd /private/tmp/aeros_second_batch_init_check && python /Users/jiamingzhang/aeros-template/checks/check_parser_benchmark.py`
  - `cd /private/tmp/aeros_second_batch_init_check && python /Users/jiamingzhang/aeros-template/checks/check_adversarial_benchmark.py`
  - `cd /private/tmp/aeros_second_batch_init_check && python /Users/jiamingzhang/aeros-template/checks/check_readiness_vector.py`
- notes: This is scaffolding and deterministic checking only. It does not prove data availability, full-text review quality, parser correctness outside fixtures, scientific validity, claim support, gate approval, or release readiness.

## REV035 - 2026-06-22 00:00 +0800

- commit: e783c77
- change_type: action-spec / machine-readable next action
- summary: Added `aeros next --json` so the primary next-action producer exposes the full declared ActionSpec, and extended `check_next_action.py` to exercise the CLI JSON surface.
- files:
  - aeros/cli.py
  - aeros/runtime/next_action.py
  - checks/check_next_action.py
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - `python -m py_compile aeros/cli.py aeros/runtime/next_action.py checks/check_next_action.py`
  - `python -m aeros.cli next --json`
  - `python -m aeros.cli next`
  - `python checks/check_next_action.py`
  - `python -m aeros.cli check --profile smoke --timeout 20`
- notes: This is a contract-surface fix. It does not change execution dispatch, approve gates, run task commands, remove legacy inferred compatibility, or certify recommendation quality.

## REV036 - 2026-06-22 00:00 +0800

- commit: 3b16b2d
- change_type: adversarial benchmark / executable fixture
- summary: Added the first executable adversarial benchmark slice for `exit_zero_no_output` and labeled draft/parser scaffold-only checks honestly.
- files:
  - checks/check_adversarial_benchmark.py
  - tests/adversarial/exit_zero_no_output.py
  - harness/adversarial_benchmark.yml
  - aeros/runtime/init_project.py
  - checks/check_estimand_data_contract.py
  - checks/check_parser_benchmark.py
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - `python -m py_compile checks/check_adversarial_benchmark.py tests/adversarial/exit_zero_no_output.py aeros/runtime/init_project.py checks/check_estimand_data_contract.py checks/check_parser_benchmark.py`
  - `python checks/check_adversarial_benchmark.py`
  - `python checks/check_estimand_data_contract.py`
  - `python checks/check_parser_benchmark.py`
  - `python -m aeros.cli check --profile smoke --timeout 20`
  - `python -m aeros.cli init /private/tmp/aeros_adversarial_init_check --force`
  - `cd /private/tmp/aeros_adversarial_init_check && python /Users/jiamingzhang/aeros-template/checks/check_adversarial_benchmark.py`
- notes: This makes one benchmark scenario behavioral, not merely named. Other adversarial scenarios, parser benchmark cases, and project-specific EstimandDataContracts remain scaffold-only until real fixtures or evidence-bound contracts are added.

## REV037 - 2026-06-23 00:00 +0800

- commit: pending
- change_type: adversarial benchmark / session-scope semantics
- summary: Added executable stale-registry detection and semantic session-scope drift fixtures for `CLAIM_SCOPE_DRIFT` and `AUTHORITY_DRIFT`.
- files:
  - checks/check_adversarial_benchmark.py
  - tests/adversarial/stale_registry.py
  - harness/adversarial_benchmark.yml
  - checks/check_session_scope.py
  - aeros/runtime/init_project.py
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - `python -m py_compile checks/check_adversarial_benchmark.py checks/check_session_scope.py tests/adversarial/stale_registry.py tests/adversarial/exit_zero_no_output.py aeros/runtime/init_project.py`
  - `python checks/check_session_scope.py`
  - `python checks/check_adversarial_benchmark.py`
  - `python -m aeros.cli check --profile smoke --timeout 20`
  - `python -m aeros.cli init /private/tmp/aeros_fixture_check_20260623 --force`
  - `cd /private/tmp/aeros_fixture_check_20260623 && python /Users/jiamingzhang/aeros-template/checks/check_adversarial_benchmark.py`
  - `cd /private/tmp/aeros_fixture_check_20260623 && python /Users/jiamingzhang/aeros-template/checks/check_session_scope.py`
- notes: This adds two more behavioral fixtures. It does not implement all adversarial scenarios, prove absence of unknown failures, sync CMPD, or certify any claim/gate decision.

## REV038 - 2026-06-23 00:00 +0800

- commit: pending
- change_type: smoke profile / next-action check performance
- summary: Made `check_next_action.py` skip expensive lane-matrix traversal in instantiated projects while retaining full matrix coverage in the root template.
- files:
  - checks/check_next_action.py
  - harness/improvement_backlog.yml
  - decisions/update_ledger.md
  - decisions/revision_log.md
- checks:
  - Not run in this edit pass unless explicitly requested.
- notes: This is a fast-profile fix for real projects. It does not change next-action recommendations or weaken ActionSpec/controller safety checks.
