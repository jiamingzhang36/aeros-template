"""Create a minimal AEROS project scaffold."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess


DIRS = [
    "agent_runs",
    "audits",
    "checks",
    "code/00_setup",
    "code/01_ingest",
    "code/02_clean",
    "code/03_construct",
    "code/04_analysis",
    "code/05_robustness",
    "code/06_tables",
    "code/07_figures",
    "data/raw",
    "data/intermediate",
    "data/clean",
    "data/parquet",
    "data/snapshots",
    "data/probes",
    "data/source_snapshots",
    "data/backfill",
    "decisions/escalations",
    "discovery/literature",
    "docs",
    "evidence",
    "evidence/receipts",
    "execution",
    "harness/protocols",
    "outputs/logs",
    "outputs/harness_receipts",
    "outputs/context",
    "outputs/source_snapshots",
    "outputs/tables",
    "outputs/figures",
    "outputs/model_outputs",
    "paper",
    "tasks/discovery",
    "tasks/execution",
    "templates",
    "tools/hooks",
]


FILES = {
    "CONTEXT_BUNDLE.md": """# CONTEXT_BUNDLE

generated_at: TEMPLATE
lane: project
current_goal: Initialize or continue the project with a compact, source-anchored context.
current_gate: G0
candidate_gate: G0
gate_status: open
recommended_next_action: Run `python3 -m aeros.cli context --brief` and `python3 -m aeros.cli next`.
status_label: ROUTE_READY
next_command: python3 -m aeros.cli next
current_blocker: None recorded.
latest_substantive_artifact: None recorded.
last_validation: Not run.
does_not_prove: This context bundle does not prove data access, literature extraction, empirical validity, claim support, paper readiness, or gate approval.
context_stale: false
context_stale_reason: TEMPLATE bundle; run `aeros cockpit --write` to generate source hashes.
stop_rule: Stop before switching lanes or claiming substantive progress without evidence.
latest_revision: TEMPLATE

## Lane Snapshot
- none

## Open Human Gate Items
- none

## Files To Read If Needed
- CURRENT_STATE.md
- NEXT_ACTION.md
- AGENTS.md

This bundle is context, not completion evidence, gate approval, claim support, or validation.
""",
    "CURRENT_STATE.md": """# CURRENT_STATE

current_goal: Initialize the project and decide the first data/literature route.
latest_substantive_artifact: None yet.
current_blocker: None.
next_command: `python3 -m aeros.cli next`
does_not_prove: Project initialization does not prove data access, literature extraction, results, claims, paper readiness, or gate approval.
last_validation: Not run yet.
""",
    "project_manifest.yml": """project:
  name: "AEROS project"
  status: "draft"
research:
  current_stage: "discovery"
gate_lifecycle:
  current_gate: "G0"
  # Start simple. 'lite' runs a descriptive minimal ring and stops for you at
  # only two gates (design, claim audit). Switch to 'full' for the complete
  # G0-G13 ladder. A profile only selects which gates' tasks run; the runtime
  # pulls in any dependency, so a slim profile cannot break the task DAG.
  profile: lite
  profiles:
    lite: {active_gates: [G0, G1, G3, G4, G6, G7, G10], human_gates: [G3, G7]}
    full: {active_gates: all, human_gates: [G3, G7, G12, G13]}
automation:
  pipeline:
    profile: smoke
    cwd: "."
    command: []
    runtime:
      python: "python3"
    post_run_hooks:
      - reconcile
    key_outputs: []
execution_profiles:
  smoke:
    cwd: "."
    python: "python3"
    command: []
    env_policy: no_secrets
    post_run_hooks:
      - reconcile
""",
    "harness/econ_method_advisory_policy.yml": """version: "0.1"
policy: AEROS-ECON-METHOD-ADVISORY-001
principle: Advisory method skills cannot certify identification, claims, or gates.
""",
    "harness/task_mode_policy.yml": """version: "0.1"
policy: AEROS-TASK-MODE-001
principle: Classify task shape before work starts; task mode is advisory and cannot approve gates, admit evidence, or certify claim support.
modes:
  general_guardrail: {workflow_preset: "", execution_mode: bounded_probe, allowed_output_intents: [audit_note, probe_only]}
  broad_capture: {workflow_preset: broad_capture_leads, execution_mode: broad_capture, allowed_output_intents: [lead_queue, candidate_queue, audit_note]}
  source_capture: {workflow_preset: recapture_source_pool, execution_mode: source_capture, allowed_output_intents: [probe_only, staging_artifact, audit_note]}
  data_repair: {workflow_preset: source_promotion_queue, execution_mode: bounded_probe, allowed_output_intents: [probe_only, canonical_candidate, audit_note]}
  claim_audit: {workflow_preset: claim_audit, execution_mode: bounded_probe, allowed_output_intents: [audit_note, canonical_candidate]}
  writing_sync: {workflow_preset: writing_guardrail, execution_mode: paper_release, allowed_output_intents: [audit_note, canonical_candidate, canonical_update]}
  submission_readiness: {workflow_preset: submission_release_preflight, execution_mode: paper_release, allowed_output_intents: [audit_note, canonical_candidate]}
  route_recovery: {workflow_preset: source_promotion_queue, execution_mode: waiting_on_external_input, allowed_output_intents: [audit_note, probe_only]}
does_not_prove: [task execution, output admissibility, claim support, human gate approval]
""",
    "harness/output_intent_policy.yml": """version: "0.1"
policy: AEROS-OUTPUT-INTENT-001
valid_output_intents: [probe_only, lead_queue, candidate_queue, staging_artifact, canonical_candidate, canonical_update, audit_note]
does_not_prove: [output existence, evidence admissibility, release readiness, claim support]
""",
    "harness/source_capture_permission_policy.yml": """version: "0.1"
policy: AEROS-SOURCE-CAPTURE-PERMISSION-001
tiers:
  green_public_staging: {approval_required: none_for_staging_public_capture}
  green_broad_capture: {approval_required: none_for_broad_lead_capture}
  yellow_route_level: {approval_required: route_level}
  red_human_required: {approval_required: human_required}
non_goals: [does not fetch sources, does not admit evidence, does not approve gates or canonical promotion]
""",
    "harness/execution_mode_policy.yml": """version: "0.1"
policy: AEROS-EXECUTION-MODE-001
principle: Right-size governance before running; modes advise/check scope but do not approve gates or certify research substance.
modes:
  smoke_test: {profile: smoke, max_actions: 1, requires_human_decision: false, allowed_progress_label: CHECK_PASS}
  bounded_probe: {profile: lane:data, max_actions: 3, requires_human_decision: false, allowed_progress_label: ROUTE_READY}
  broad_capture: {profile: lane:data, max_actions: 5, requires_human_decision: false, allowed_progress_label: CAPTURE_LOGGED, receipt_level: lightweight, audit_level: batch_only, claim_surface: none_by_construction}
  source_capture: {profile: lane:data, max_actions: 5, requires_human_decision: false, allowed_progress_label: ROUTE_READY}
  paper_release: {profile: full, max_actions: 1, requires_human_decision: true, allowed_progress_label: DECISION_RECORDED}
  expensive_api_run: {profile: lane:data, max_actions: 1, requires_human_decision: true, allowed_progress_label: ROUTE_READY}
  waiting_on_external_input: {profile: smoke, max_actions: 0, requires_human_decision: true, allowed_progress_label: ROUTE_READY}
does_not_prove: [scientific validity, claim support, gate approval, release readiness]
""",
    "harness/skill_obligation_policy.yml": """version: "0.1"
policy: AEROS-SKILL-OBLIGATION-001
principle: Ordinary tasks may dynamically use zero or more skills without a waiver; use-or-waive applies only to explicit required_skill_classes.
default_requirement: optional_record_if_used
use_or_waive_trigger: explicit_required_skill_classes
classes:
  data_source: {skills: [data-inventory, data-quality-checker, data-merge-audit], triggers: [data, source, probe, capture, inventory, denominator, gdp, schema]}
  literature: {skills: [academic-research-suite, lit-review-assistant], triggers: [literature, citation, paper_registry, full-text, fulltext, synthesis]}
  writing: {skills: [econ-write, pre-submission-audit], triggers: [paper, draft, writing, submission, referee, response]}
  causal_identification: {skills: [causal-id-review, did-checklist], triggers: [identification, causal, did, event study, method_card, design]}
  replication: {skills: [code-review-econ, replication-check], triggers: [replication, reproduc, provenance, pipeline, result_validation, code_review]}
allowed_waiver_classes: [ledger_hash_only, typo_only, mechanical_revalidation, single_line_parser_patch]
required_waiver_fields: [skill_class, reason, scope, progress_label]
does_not_prove: [skill invocation, skill output correctness, scientific validity, claim support, human gate approval]
""",
    "harness/research_profiles.yml": """version: "0.1"
policy: AEROS-RESEARCH-PROFILES-001
default_profile: research
status: mapping_only
immutable_invariants:
  - {id: no_forged_human_decision, rule: Agent cannot generate or apply a human decision.}
  - {id: external_authority_required, rule: Credentials paid access external writes and release require human authority.}
  - {id: observed_artifact_required, rule: Completion requires an observed expected artifact.}
  - {id: result_lineage_required, rule: Admitted results trace to data code environment and run.}
  - {id: claim_self_upgrade_forbidden, rule: Claim producers cannot upgrade claim admission.}
  - {id: paper_number_binding_required, rule: Paper numbers bind to Result Specification and Exhibit.}
  - {id: claim_citation_locator_required, rule: Claim-bearing citations require locator-backed evidence.}
  - {id: bounded_loop_required, rule: Autonomous loops enforce time cost resource and repetition limits.}
profiles:
  explore: {workspace: isolated_candidate_worktree, check_strategy: minimal_pre_drive_plus_artifact_selected_post_action, skill_policy: dynamic_optional, promotion_authority: unchanged}
  research: {workspace: isolated_candidate_worktree, check_strategy: adaptive_post_action, skill_policy: dynamic_optional, promotion_authority: unchanged}
  submit: {workspace: isolated_candidate_worktree, check_strategy: submit_plus_full_release_candidate, skill_policy: contract_required_or_dynamic_optional, promotion_authority: unchanged}
  regulated: {workspace: isolated_candidate_worktree, check_strategy: full, skill_policy: contract_required_use_or_waive, promotion_authority: unchanged}
does_not_prove: [scientific validity, provider sandboxing, promotion approval]
""",
    "harness/protected_path_commit_policy.yml": """version: "0.1"
policy: AEROS-PROTECTED-PATH-COMMIT-001
principle: Protected research-authority paths must not be committed by default from an agent run.
protected_paths:
  exact: [docs/protected_definitions.yml, docs/data_contract.yml, evidence/claim_registry.md, decisions/decision_log.csv, harness/permissions.yml]
  prefixes: [data/raw/, decisions/approvals/]
override:
  env_var: AEROS_ALLOW_PROTECTED_COMMIT
  allowed_value: "1"
installation:
  template: tools/hooks/pre-commit-aeros-protected-paths
  installer: tools/install_aeros_git_hooks.zsh
  auto_installed: false
does_not_prove: [scientific validity, claim support, human approval, release readiness]
""",
    "harness/update_ledger_hash_chain_policy.yml": """version: "0.1"
policy: AEROS-UPDATE-LEDGER-HASH-CHAIN-001
chain_file: decisions/update_ledger_chain.jsonl
genesis: GENESIS
record_required_fields: [version, seq, entry_id, subject, subject_sha256, prev_hash, payload, entry_hash]
protected_subjects: [decisions/update_ledger.md]
verification_strength: local_hash_chain_over_observed_subject_file
does_not_prove: [malicious actor cannot rewrite both ledger and chain, scientific validity, claim support, gate approval, external transparency]
""",
    "harness/evidence_sufficiency_audit_policy.yml": """version: "0.1"
policy: AEROS-EVIDENCE-SUFFICIENCY-AUDIT-001
required_dimensions: [actor, authority, action, policy, decision_basis, resource_access, lifecycle, verification_strength]
allowed_verification_strength: [self_attested, schema_valid, file_exists, hash_observed, source_identity_matched, independent_rerun, human_reviewed]
minimum_for_gate_packet: [actor, authority, action, policy, decision_basis, verification_strength]
minimum_for_completion_claim: [actor, action, decision_basis, lifecycle, verification_strength]
does_not_prove: [scientific validity, identification quality, claim support, data truth, publication readiness]
""",
    "harness/context_budget.yml": """version: "0.1"
policy: AEROS-CONTEXT-BUDGET-001
brief_max_lines: 40
lane_max_lines: 80
max_recent_deltas: 5
max_human_gate_items: 3
max_source_hashes: 12
""",
    "harness/check_profiles.yml": """version: "0.1"
default_profile: full
profiles:
  smoke: {checks: [check_next_action.py, check_action_spec.py, check_session_scope.py, check_skill_coverage.py, check_execution_mode.py, check_task_mode.py, check_task_preflight.py, check_source_capture_permission.py, check_discovery_route_decision.py, check_execution_profiles.py, check_source_id_consistency.py, check_artifact_stage.py, check_output_intent.py, check_route_early_gate.py, check_improve_harvest.py, check_sync_doctor.py, check_update_ledger_hash_chain.py, check_harness_observed_receipts.py, check_protected_path_hook.py, check_evidence_sufficiency_audit.py, check_context_bundle.py, check_context_graph.py, check_cockpit.py, check_harness_profiles.py]}
  full: {checks: all}
""",
    "tools/hooks/pre-commit-aeros-protected-paths": """#!/usr/bin/env python3
\"\"\"AEROS protected-path pre-commit guard. AEROS-PROTECTED-PATH-HOOK-001\"\"\"
from __future__ import annotations
import os, subprocess, sys
PROTECTED_EXACT = {"docs/protected_definitions.yml", "docs/data_contract.yml", "evidence/claim_registry.md", "decisions/decision_log.csv", "harness/permissions.yml"}
PROTECTED_PREFIXES = ("data/raw/", "decisions/approvals/")
def git(args):
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL)
def is_protected(path):
    return path in PROTECTED_EXACT or any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES)
def main():
    staged = [line.strip() for line in git(["diff", "--cached", "--name-only"]).splitlines()]
    hits = [path for path in staged if path and is_protected(path)]
    if not hits:
        return 0
    if os.environ.get("AEROS_ALLOW_PROTECTED_COMMIT") == "1":
        print("AEROS protected-path hook: human override accepted.", file=sys.stderr)
        return 0
    print("AEROS protected-path hook blocked protected staged file(s):", file=sys.stderr)
    for path in hits:
        print(f"  - {path}", file=sys.stderr)
    print("Set AEROS_ALLOW_PROTECTED_COMMIT=1 only after explicit human approval/gate review.", file=sys.stderr)
    return 1
if __name__ == "__main__":
    raise SystemExit(main())
""",
    "tools/install_aeros_git_hooks.zsh": """#!/bin/zsh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/tools/hooks/pre-commit-aeros-protected-paths"
DEST="$ROOT/.git/hooks/pre-commit"
MARKER="AEROS-PROTECTED-PATH-HOOK-001"
if [ -f "$DEST" ] && ! grep -q "$MARKER" "$DEST"; then
  print -u2 "refusing to overwrite existing non-AEROS pre-commit hook: $DEST"
  exit 1
fi
cp "$SRC" "$DEST"
chmod +x "$DEST"
echo "installed AEROS protected-path pre-commit hook -> $DEST"
""",
    "harness/stale_triage_policy.yml": """version: "0.1"
policy: AEROS-STALE-TRIAGE-001
principle: Deterministic stale triage only; no LLM ranking and no state mutation.
impact_scopes:
  specific_claims: "High impact only when a deterministic path localizes affected claim IDs."
  claim_registry_unknown: "High-risk unknown scope; do not invent affected claim IDs."
  registry_unknown: "High-risk unknown scope; run registry/graph consistency checks."
  paper_global_review: "Paper review needed, but not all claims are assumed affected."
  none: "No deterministic claim/paper impact path."
volatile_outputs:
  examples: [agent_runs/, outputs/logs/, outputs/context/, decisions/revision_log.md]
rule: "If only volatile allowed outputs changed, route to recover --check before provider/API rerun."
""",
    "harness/session_scope.yml": """version: "0.1"
policy: AEROS-SESSION-SCOPE-001
principle: Chat-driven work must declare one active lane and audit changed files against lane scope.
common_allowed_prefixes: [SESSION_CONTRACT.yml, CURRENT_STATE.md, NEXT_ACTION.md, CONTEXT_BUNDLE.md, agent_runs/, outputs/logs/, outputs/context/, evidence/delta_log.jsonl, aeros/state/global_state.yml, decisions/revision_log.md, decisions/update_ledger.md, harness/improvement_backlog.yml]
lanes:
  data: {allowed_prefixes: [data/, discovery/data_inventory.csv, discovery/feasibility_matrix.md, docs/data_contract.yml, docs/data_dictionary.md, code/00_setup/, code/01_ingest/, code/02_clean/, code/03_construct/], forbidden_prefixes: [paper/, discovery/literature/, evidence/claim_registry.md]}
  literature: {allowed_prefixes: [discovery/literature/, docs/related_work, paper/references], forbidden_prefixes: [data/raw/, data/clean/, evidence/claim_registry.md, paper/draft]}
  method: {allowed_prefixes: [design/, docs/method, code/04_analysis/, code/05_robustness/, templates/estimand, evidence/estimand], forbidden_prefixes: [data/raw/, paper/draft, evidence/claim_registry.md]}
  analysis: {allowed_prefixes: [code/04_analysis/, code/05_robustness/, code/06_tables/, code/07_figures/, outputs/tables/, outputs/figures/, outputs/model_outputs/, evidence/result_index.csv, evidence/result_registry.csv, outputs/.provenance/], forbidden_prefixes: [paper/draft, evidence/claim_registry.md]}
  claim: {allowed_prefixes: [evidence/, audits/, decisions/gates/, docs/design/falsification], forbidden_prefixes: [data/raw/, paper/draft]}
  writing: {allowed_prefixes: [paper/, docs/, outputs/tables/, outputs/figures/], forbidden_prefixes: [data/raw/, evidence/claim_registry.md]}
  compliance: {allowed_prefixes: [replication/, compliance/, docs/data_availability, paper/supplement, outputs/logs/], forbidden_prefixes: [data/raw/, evidence/claim_registry.md]}
  harness: {allowed_prefixes: [aeros/, checks/, harness/, templates/, tools/, docs/design/, project_manifest.yml, AGENTS.md], forbidden_prefixes: [data/raw/, paper/draft.md, evidence/claim_registry.md]}
workflow_presets:
  broad_capture_leads: {description: Wide early lead capture into isolated queues; not evidence or claim-supporting., allowed_prefixes: [work/leads/, data/backfill/, audits/broad_capture/, quality_reports/broad_capture/, outputs/logs/, evidence/delta_log.jsonl], allowed_actions: [broad search, lead sweep, source group probe, candidate queue update], forbidden_prefixes: [data/raw/, data/intermediate/, data/processed/, paper/, evidence/claim_registry.md, decisions/approvals/]}
  recapture_source_pool: {description: Recover and review candidate source pools without promoting them to canonical evidence., allowed_prefixes: [work/recapture_, audits/source_recapture/, quality_reports/source_recapture/, source_snapshots/, evidence/delta_log.jsonl], allowed_actions: [source recapture, chrome-assisted review, source-promotion queue], forbidden_prefixes: [evidence/claim_registry.md, decisions/approvals/]}
  claim_audit: {description: Audit claim support and deltas without collecting new raw data., allowed_prefixes: [audits/claim/, audits/advisory/, evidence/research_graph.yml, evidence/delta_log.jsonl, quality_reports/claim_audit/], allowed_actions: [claim audit, support-chain review, delta audit], forbidden_prefixes: [data/raw/, decisions/approvals/]}
  writing_guardrail: {description: Bounded paper/TeX edits and guardrail reports tied to existing claims and numbers., allowed_prefixes: [paper/, output/tex/, outputs/tex/, quality_reports/writing/, audits/writing/, evidence/delta_log.jsonl], allowed_actions: [bounded writing edit, number/claim guardrail, tex compile review], forbidden_prefixes: [data/raw/, evidence/claim_registry.md, decisions/approvals/]}
  chrome_assisted_review: {description: Browser-assisted source review that produces staging notes, screenshots, or queues., allowed_prefixes: [work/chrome_review/, work/recapture_, audits/chrome_assisted_review/, quality_reports/chrome_assisted_review/, source_snapshots/, evidence/delta_log.jsonl], allowed_actions: [chrome-assisted review, source locator check, manual page audit], forbidden_prefixes: [evidence/claim_registry.md, decisions/approvals/]}
  source_promotion_queue: {description: Promote reviewed staging sources into explicit queues without claiming final evidence., allowed_prefixes: [work/source_promotion/, audits/source_promotion/, quality_reports/source_promotion/, data/backfill/, discovery/data_inventory.csv, docs/data_sources.md, evidence/delta_log.jsonl, aeros/state/global_state.yml], allowed_actions: [source promotion queue, backfill queue update, global state refresh], forbidden_prefixes: [paper/, evidence/claim_registry.md, decisions/approvals/]}
semantic_verdicts:
  expected_lane_change: Changed files match the declared lane.
  supporting_cross_lane_change: Allowed support file changed outside the lane.
  bookkeeping_only: Only context/log/ledger surfaces changed.
  SCOPE_DRIFT: Changed files fall outside the declared lane scope.
  CLAIM_SCOPE_DRIFT: A non-writing/non-claim session touched paper claim-language surfaces.
  AUTHORITY_DRIFT: A session touched claim, gate, release, or runtime authority surfaces outside its authority.
""",
    "templates/session_contract.yml": """version: "0.1"
policy: AEROS-SESSION-SCOPE-001
active: true
active_lane: data
active_workflow: ""
objective: "One concrete objective for this chat/run."
max_actions: 2
allowed_actions: [aeros cockpit, aeros next, lane-scoped action]
allowed_prefixes: [SESSION_CONTRACT.yml, agent_runs/, outputs/logs/, decisions/revision_log.md]
forbidden_prefixes: [paper/, evidence/claim_registry.md]
stop_condition: "Stop at human gate, blocker, no-progress, max_actions, or first off-scope diff."
completion_label_rule: "Use CHECK_PASS, ROUTE_READY, or SUBSTANTIVE_PRODUCED."
semantic_audit_outputs: [changed_artifacts, owner_lane, artifact_type, semantic_class, authority_risk, verdict]
does_not_prove: [task completion, research validity, claim support, gate approval, off-scope acceptance]
""",
    "harness/context_graph_policy.yml": """version: "0.1"
policy: AEROS-CONTEXT-GRAPH-001
principle: Context graph is derived navigation only, not research evidence.
""",
    "harness/parser_benchmark.yml": """version: "0.1"
policy: AEROS-PARSER-BENCHMARK-001
principle: Parser benchmarks measure extraction reliability; they do not certify full-text review or claim support.
metrics:
  - identity_match
  - false_fulltext_rate
  - parse_latency
  - human_correction_minutes
  - page_addressability
  - table_recovery
corpus_buckets:
  - bucket: econ_pdf
    target_count: 50
  - bucket: scanned_pdf
    target_count: 10
  - bucket: tables
    target_count: 10
  - bucket: appendix_formula
    target_count: 10
  - bucket: policy_report
    target_count: 10
  - bucket: html_working_paper
    target_count: 10
cases: []
does_not_prove:
  - literature synthesis quality
  - citation support
  - full-text availability for all registry rows
  - claim support
""",
    "harness/adversarial_benchmark.yml": """version: "0.1"
policy: AEROS-ADVERSARIAL-BENCHMARK-001
principle: Adversarial fixtures test whether AEROS blocks known failure modes; they do not prove the system has no failures.
scenarios:
  - id: false_fulltext
    attack: "PDF/URL is login, CAPTCHA, metadata, SPA shell, or unrelated cache."
    expected_detection: "full-text verifier blocks EvidenceUnit or synthesis use"
  - id: exit_zero_no_output
    attack: "script exits 0 but registered output is absent or unchanged"
    expected_detection: "result/provenance/output checks fail"
    executable_fixture: tests/adversarial/exit_zero_no_output.py
    detection_check: checks/check_noop_runs.py
  - id: stale_registry
    attack: "result file hash changes but registry/provenance/graph are not synced"
    expected_detection: "provenance/reconcile/readiness checks flag drift"
    executable_fixture: tests/adversarial/stale_registry.py
    detection_check: checks/check_provenance.py
  - id: claim_ceiling_escape
    attack: "paper or claim uses stronger language than evidence ceiling permits"
    expected_detection: "claim ceiling/method consistency checks fail"
  - id: stale_human_approval
    attack: "human approval references an artifact hash that has since changed"
    expected_detection: "gate/approval freshness check blocks authority reuse"
  - id: session_scope_drift
    attack: "data session silently edits paper claim language"
    expected_detection: "session audit returns CLAIM_SCOPE_DRIFT"
    executable_fixture: checks/check_session_scope.py
    detection_check: checks/check_session_scope.py
  - id: wrong_python_runtime
    attack: "pipeline uses generic python instead of declared project runtime"
    expected_detection: "ExecutionProfile/pipeline check exposes runtime mismatch"
  - id: undeclared_credential
    attack: "provider/API/source access needs credentials but ActionSpec omits them"
    expected_detection: "ActionSpec authority/precondition check blocks execution"
does_not_prove:
  - absence of unknown failure modes
  - scientific validity
  - external reproducibility
  - paper readiness
""",
    "harness/status_label_policy.yml": """version: "0.1"
policy: AEROS-STATUS-LABELS-001
principle: "Distinguish mechanical checks, route readiness, and substantive progress."
labels:
  CHECK_PASS: {meaning: "Mechanical checks passed."}
  CAPTURE_LOGGED: {meaning: "Early lead/candidate capture was logged without evidence admission."}
  ROUTE_READY: {meaning: "A route, packet, queue, or plan is ready."}
  SUBSTANTIVE_PRODUCED: {meaning: "A real research artifact changed project substance."}
final_response_rule:
  required: true
""",
    "harness/rollout_playbook.md": """# AEROS Rollout Playbook

1. Preserve target project work.
2. Run `tools/sync_aeros_latest.zsh <project_path>`.
3. Run `python3 checks/check_work_lanes.py`.
4. Recover or revalidate old completion receipts.
5. Run `python3 -m aeros.cli reconcile --dry-run` to confirm post-pipeline derived sync wiring.
6. Run `python3 checks/run_harness_checks.py --timeout 30`.
7. Write a rollout report in `agent_runs/`.
8. Update `CURRENT_STATE.md`.
9. Commit the rollout.
""",
    "decisions/human_gate_queue.yml": """version: "0.1"
policy: AEROS-HUMAN-GATE-QUEUE-001
items: []
schema:
  required_fields: [project, request, why_human_needed, after_approval_codex_can, risk_boundary, status]
  allowed_statuses: [pending, approved, blocked, superseded, done]
""",
    "harness/permissions.yml": """# Minimal permission policy. See the root template for the full version.
version: "0.1"
defaults:
  push_to_remote: "human_only"   # never auto-push without explicit human approval
  raw_data_write: "deny"
# Human-gate trust anchor. Sensitive decisions fail closed until the first
# signer is bootstrapped; git author names alone are provenance, not identity.
human_approval:
  enforcement: "git_committer"
  approver_identity: []          # e.g. ["your-git-author-name"]
  agent_identity: ["aeros-agent"]
  approval_artifact_dir: "decisions/approvals"
  minimum_authority:
    campaign_release: "signed_commit"
    gate_approval: "signed_commit"
    gate_apply: "signed_commit"
  trusted_signers: []
""",
    "aeros_state.yml": """current_stage: discovery
current_gate: G0
gate_status: open
candidate_stage: discovery
candidate_gate: G0
tasks: {}
gate_history: []
candidate_gate_history: []
gate_decisions: []
""",
    "decisions/decision_log.csv": (
        "Date,Decision ID,Task ID,Agent Recommendation,Critic Verdict,"
        "Human Decision,Rationale,Owner,Follow-up\n"
    ),
    "discovery/literature/paper_registry.csv": """paper_id,citation_key,title,authors,year,source,doi,url,pdf_url,primary_function,secondary_functions,reading_depth,status,full_text_available,opened_source,opened_date,evidence_basis,screening_decision,extraction_card,used_in_synthesis,notes
""",
    "discovery/literature/citation_audit.md": """# Citation Audit

| Paper ID | Requires audit | Verification basis | Stable locator | Citation exists | Metadata faithful | Claim support checked | Evidence level | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
""",
    "discovery/literature/citation_snowball_queue.csv": """queued_at,source_paper_id,related_locator,relation,source,status,notes
""",
    "discovery/literature/fulltext_ready_queue.csv": """queued_at,paper_id,zotero_item_key,zotero_attachment_key,title,availability,indexed_fulltext_chars,pdf_path_or_url,status,next_action,notes
""",
    "discovery/literature/missing_fulltext_queue.csv": """queued_at,paper_id,zotero_item_key,title,reason,status,next_action,notes
""",
    "discovery/anchor.yml": """# Research anchor: 4 components, set ONCE at intake and then frozen (anti-drift).
# Set status: locked once decided; after that it is a protected file.
anchor:
  status: draft            # draft | locked
  locked_at: ""
  topic: ""                # one-sentence research question
  claim_type: ""           # descriptive | associational | causal | mechanism | external_validity | policy_translation | forecast
  identification: ""       # identification / measurement strategy (or "descriptive: none")
  data: ""                 # dataset(s) and unit of analysis the anchor commits to
""",
    "docs/method_card.md": """---
status: draft
---
# Method Card
""",
    "docs/protected_definitions.yml": """protected_definitions:
  version: "0.1"
  status: "draft"
""",
    "docs/data_contract.yml": """data_contract:
  status: draft
estimand_data_contract:
  version: "0.1"
  status: draft
  research_question: ""
  unit_of_observation: ""
  population: ""
  treatment_or_exposure: []
  outcome: []
  comparison: ""
  time_window: ""
  required_variation: ""
  target_population: ""
  estimand: ""
  required_fields: []
  required_variables: []
  linkage_keys: []
  join_keys: []
  minimum_coverage: ""
  maximum_missingness: ""
  quality_thresholds: {}
  probe_sampling_strategy: ""
  probe_success_condition: ""
  probe_stop_condition: ""
  source_access_class: ""
  license_class: ""
  credential_requirement: ""
  estimated_cost: ""
  fallback_source: ""
  minimum_probe_requirements: []
  does_not_prove:
    - data availability
    - identification quality
    - claim support
""",
    "evidence/claim_registry.md": """# Claim Registry
""",
    "templates/evidence_delta_record.json": """{
  "version": 1,
  "policy": "AEROS-EVIDENCE-DELTA-001",
  "delta_id": "DATA-DELTA-001",
  "created_at": "2026-06-19T00:00:00+00:00",
  "lane": "data",
  "task_id": "D005_data_probe",
  "run_ref": "agent_runs/example.md",
  "summary": "One short sentence describing the evidence increment.",
  "artifacts_added": ["data/probes/example_probe.json"],
  "artifacts_updated": [],
  "coverage_delta": {"units": "+10"},
  "judgment_implications": ["Feasibility improved but claim support remains insufficient."],
  "remaining_gaps": ["Official source snapshot still missing."],
  "next_best_increment": "Probe linkage quality for the newly added source.",
  "sufficiency_for_current_purpose": "inventory_started"
}
""",
    "templates/evidence_unit.yml": """version: "0.1"
policy: AEROS-EVIDENCE-UNIT-001
evidence_unit_id: EU-000
paper_id: P000
source_artifact_sha256: ""
locator:
  page: ""
  section: ""
  span: ""
literature_function: gap_verification
extracted_proposition: ""
limitation: ""
verifier_status: unverified
binding:
  claim_id: ""
  section_id: ""
does_not_prove:
  - "claim support until verified and bound through the claim/evidence registry"
  - "full paper synthesis"
  - "citation truth beyond the addressed source span"
""",
    "templates/parser_benchmark_case.yml": """version: "0.1"
policy: AEROS-PARSER-BENCHMARK-001
case_id: PARSE-000
bucket: econ_pdf
source_path_or_url: ""
expected_identity:
  title: ""
  doi: ""
expected_outputs:
  page_addressability: true
  table_recovery: unknown
  citation_recovery: unknown
metrics:
  page_addressability: null
  table_recovery: null
  identity_match: null
  false_fulltext_rate: null
  parse_latency_seconds: null
  human_correction_minutes: null
notes: ""
""",
    "templates/adversarial_scenario.yml": """version: "0.1"
policy: AEROS-ADVERSARIAL-BENCHMARK-001
id: false_fulltext
description: "A candidate full-text URL returns login/CAPTCHA/metadata HTML instead of article text."
target_check: check_literature_fulltext_execution.py
expected_detection: true
false_positive_risk: ""
fixture_path: ""
does_not_prove:
  - "overall scientific validity"
  - "all future attacks are covered"
""",
    "tests/adversarial/exit_zero_no_output.py": '''#!/usr/bin/env python3
"""Adversarial fixture: exits successfully while producing no declared output."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--declared-output", required=True)
    args = parser.parse_args()
    Path(args.declared_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "tests/adversarial/stale_registry.py": '''#!/usr/bin/env python3
"""Adversarial fixture: mutate a registered output without syncing provenance."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--content", default="mutated-after-provenance\\n")
    args = parser.parse_args()
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(args.content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "templates/completion_attestation.yml": """version: 5
task_id: T000
generated_at: ""
completion_mode: agent_run
declared_outcome: complete
outcome_kind: complete
contract_status: failed
verification_level: failed_attestation
progress_domain: research
progress_class: none
progress_label: CHECK_PASS
authority_status: no_new_authority
work_lane: data
allowed_outputs_expected: []
actual_outputs: []
staging_artifact_paths: []
substantive_evidence_paths: []
checks_required: []
check_attestations: []
evidence_delta_ref: ""
substantive_progress: false
does_not_prove:
  - scientific validity
  - identification quality
  - claim support
  - human gate approval
completion_verdict: fail
""",
    "templates/CONTEXT_BUNDLE.md": """# CONTEXT_BUNDLE

generated_at: TEMPLATE
lane: project
current_goal: Initialize or continue the project with a compact, source-anchored context.
current_gate: G0
candidate_gate: G0
gate_status: open
recommended_next_action: Run `python3 -m aeros.cli context --brief` and `python3 -m aeros.cli next`.
status_label: ROUTE_READY
next_command: python3 -m aeros.cli next
current_blocker: None recorded.
latest_substantive_artifact: None recorded.
last_validation: Not run.
does_not_prove: This context bundle does not prove data access, literature extraction, empirical validity, claim support, paper readiness, or gate approval.
context_stale: false
context_stale_reason: TEMPLATE bundle; run `aeros cockpit --write` to generate source hashes.
stop_rule: Stop before switching lanes or claiming substantive progress without evidence.
latest_revision: TEMPLATE

## Lane Snapshot
- none

## Open Human Gate Items
- none

## Files To Read If Needed
- CURRENT_STATE.md
- NEXT_ACTION.md
- AGENTS.md

This bundle is context, not completion evidence, gate approval, claim support, or validation.
""",
    "templates/NEXT_ACTION.md": """# NEXT_ACTION

recommended_next_action: The deterministic next step AEROS recommends.
why_this_next: Why this step outranks checks, human gates, data, literature, analysis, claim, writing, or compliance alternatives.
lane: data | literature | analysis | claim | writing | compliance | harness | human_gate | discovery | project
status_label: CHECK_PASS | ROUTE_READY | SUBSTANTIVE_PRODUCED
command: The next command to run, or the human decision needed.
stop_condition: The exact condition where Codex must stop rather than drift into another lane.
source: deterministic
blocked: false

This is a recommendation, not an execution record, gate approval, or claim-support artifact.
""",
    "templates/evidence_sufficiency_audit.yml": """version: "0.1"
audit_id: ESA-TEMPLATE
artifact_id: ""
artifact_path: ""
artifact_type: ""
dimensions:
  actor: {value: "", note: "Who or what produced, reviewed, or approved this artifact."}
  authority: {value: "", note: "The authority level: agent, harness, human gate, external source, or journal/data editor."}
  action: {value: "", note: "The action performed, observed, or approved."}
  policy: {value: "", note: "The AEROS policy/check/gate/external standard that governs this record."}
  decision_basis: {value: "", note: "The source files, outputs, hashes, checks, or human evidence used as the basis."}
  resource_access: {value: "", note: "Credentials, licenses, source access, data-use constraints, or public-access status."}
  lifecycle: {value: "", note: "Draft, candidate, validated, admitted, superseded, blocked, or released."}
  verification_strength: {value: self_attested, note: "How strong the verification is."}
overall_assessment: draft
does_not_prove: [scientific validity, identification quality, claim support, data truth, publication readiness]
""",
    "harness/human_review_receipt_template.md": """---
receipt_type: human_review_receipt
status: draft
reviewed_by:
reviewed_at:
source_snapshot:
coverage:
disagreement_log:
human_decision:
---

# Human Review Receipt

Use this when a task cannot be fully automated but a human says the evidence was reviewed.
AEROS checks the existence and required fields of the receipt; it does not replace the
human judgment recorded here.
""",
    "harness/automation_policy.yml": """version: "0.1"
automation_classes:
  auto_rerunnable:
    meaning: "Deterministic or local-cache-safe work that may rerun when stale."
  receipt_audited:
    meaning: "Human-reviewed evidence; AEROS verifies the receipt, not the judgment."
  frozen_evidence:
    meaning: "Evidence may be reused only with a recorded source snapshot and receipt."
  approval_required:
    meaning: "LLM/API/scraping/credential/source-date-sensitive work blocked until approval."
gate_statuses:
  - pending
  - done_auto_verified
  - done_human_verified_with_receipt
  - done_frozen_evidence_verified
  - skipped_unverified
  - needs_receipt_audit
  - blocked_requires_approval
  - blocked_missing_credentials
  - blocked_missing_source_snapshot
""",
    "harness/goal_mode_policy.yml": """version: "0.1"
policy: AEROS-GOAL-MODE-DATA-PROGRESS-001
principle: >
  Goal/continue mode may automate execution, but it must not turn paperwork,
  task scaffolding, terminal-status files, or receipt writing into claimed data
  progress. A data-oriented run either acquires/verifies a real data/source/probe
  artifact or reports an honest blocker/source-discovery attempt.
data_progress_requires_one_of:
  - discovery/data_inventory.csv
  - data/data_state.yml
  - data/data_gap_plan.yml
  - audits/data_probe_report.md
  - data/raw/
  - data/intermediate/
  - data/parquet/
  - data/clean/
  - data/snapshots/
  - data/probes/
  - data/source_snapshots/
  - evidence/source_snapshots/
  - outputs/source_snapshots/
  - outputs/data/
  - outputs/tables/
paperwork_only_paths_do_not_count_as_data_progress:
  - agent_runs/
  - decisions/
  - tasks/
  - checks/
  - harness/
  - docs/
  - templates/
  - code/checks/
  - README.md
  - Makefile
allowed_no_data_outcomes:
  - blocked_queue_preparation
  - source_discovery_attempt
  - mechanical_hygiene
enforced_by:
  - checks/check_action_receipts.py
  - checks/check_goal_mode_data_progress.py
""",
    "harness/work_lane_policy.yml": """version: "0.1"
policy: AEROS-WORK-LANE-ROUTER-001
principle: >
  AEROS work must run in an explicit lane. If a lane is blocked, stop and report
  the blocker instead of silently switching to another lane.
lanes:
  - data
  - literature
  - analysis
  - claim
  - writing
  - compliance
  - harness
switch_gate:
  rule: "No lane switch inside a run unless the human explicitly asks for it."
completion_definitions:
  data: {complete_only_if: ["data/source/probe artifact or honest blocker"]}
  literature: {complete_only_if: ["full-text extraction or function-specific synthesis"]}
  analysis: {complete_only_if: ["protocol, pipeline, result, robustness, or validation artifact"]}
  claim: {complete_only_if: ["claim audit, ceiling, registry boundary, or language constraint"]}
  writing: {complete_only_if: ["bounded prose tied to registered claims and numbers"]}
  compliance: {complete_only_if: ["terms/license/IRB/release artifact"]}
  harness: {complete_only_if: ["framework/check/policy/template change reported as harness progress"]}
forbidden_cross_lane_substitutions:
  - data lane blocked -> literature cleanup
  - data lane blocked -> task scaffolding
  - harness lane cleanup -> substantive research progress
""",
    "harness/completion_attestation_policy.yml": """version: "0.1"
policy: AEROS-COMPLETION-ATTESTATION-001
principle: "Completion is a small mechanical attestation, not a research verdict."
minimal_attestation_fields: [task_id, declared_outcome, work_lane, allowed_outputs_expected, actual_outputs, staging_artifact_paths, substantive_evidence_paths, check_attestations, substantive_progress, does_not_prove]
allowed_declared_outcomes: [complete, partial, blocked, hygiene]
passed_task_rule:
  declared_outcome: complete
  requires:
    - at least one allowed output outside runtime logs
    - staging/review/queue work uses staging_artifact_paths and ROUTE_READY
    - file outputs include sha256
    - every required check has command and exit_code
    - completion_verdict is pass
does_not_prove_defaults: [scientific validity, identification quality, claim support, human gate approval]
non_goals: [decide whether a result is true, approve gates, upgrade claims, replace evidence delta logs or provenance manifests]
enforced_by: [checks/check_completion_receipts.py, checks/check_noop_runs.py]
""",
    "harness/external_tool_registry.yml": """version: "0.1"
policy: AEROS-EXTERNAL-ECON-TOOLS-001
principle: "External tools are advisory/reference/adapter candidates, not AEROS truth sources."
default_status: advisory
tools:
  awesome_ai_for_economists: {lane: harness, role: reference_index, maturity: reference, url: "https://github.com/hanlulong/awesome-ai-for-economists", use_for: ["tool discovery"], evidence_output: ["external_tool_notes"], must_not_do: ["approve gates", "certify claims"]}
  openalex: {lane: literature, role: adapter_candidate, maturity: stable_api, url: "https://docs.openalex.org/", use_for: ["metadata discovery"], evidence_output: ["discovery/literature/search_log.csv"], must_not_do: ["approve gates", "certify gap claims"]}
  citec_repec: {lane: literature, role: adapter_candidate, maturity: stable_reference, url: "https://citec.repec.org/", use_for: ["econ citation graph discovery"], evidence_output: ["discovery/literature/citation_graph_edges.csv"], must_not_do: ["approve gates", "certify gap claims"]}
  pybiblionet: {lane: literature, role: adapter_candidate, maturity: emerging_tool, url: "https://arxiv.org/abs/2601.16990", use_for: ["citation-network exploration"], evidence_output: ["discovery/literature/literature_network_notes.md"], must_not_do: ["approve gates", "replace full-text extraction"]}
  preprintresolver: {lane: literature, role: adapter_candidate, maturity: advisory_resolver, url: "https://arxiv.org/abs/2309.01373", use_for: ["working-paper version resolution"], evidence_output: ["discovery/literature/preprint_resolution_log.csv"], must_not_do: ["approve gates", "bulk-resolve without review"]}
  aea_data_editor: {lane: compliance, role: external_standard, maturity: external_policy, url: "https://aeadataeditor.github.io/", use_for: ["replication package alignment"], evidence_output: ["replication/aea_data_package_manifest.yml"], must_not_do: ["certify AEA acceptance", "approve gates"]}
  opensourceeconomics: {lane: analysis, role: reference_index, maturity: reference, url: "https://github.com/OpenSourceEconomics", use_for: ["project-structure references"], evidence_output: ["external_tool_notes"], must_not_do: ["approve replication package", "certify claims"]}
  econstellar: {lane: analysis, role: reference_pattern, maturity: emerging_reference, url: "https://arxiv.org/abs/2606.05705", use_for: ["endpoint reproducibility pattern"], evidence_output: ["evidence/result_registry.csv"], must_not_do: ["approve gates", "certify claims"]}
  econometrics_agent: {lane: analysis, role: advisory_reviewer, maturity: emerging_tool, url: "https://github.com/FromCSUZhou/Econometrics-Agent", use_for: ["econometric workflow suggestions"], evidence_output: ["audits/advisory/econometrics_agent_notes.md"], must_not_do: ["approve gates", "certify identification", "certify claims"]}
  causal_copilot: {lane: claim, role: advisory_reviewer, maturity: emerging_tool, url: "https://arxiv.org/abs/2504.13263", use_for: ["causal-risk brainstorming"], evidence_output: ["audits/advisory/causal_copilot_notes.md"], must_not_do: ["approve gates", "certify identification", "upgrade claim status"]}
  causalagent: {lane: claim, role: advisory_reviewer, maturity: emerging_tool, url: "https://arxiv.org/abs/2602.11527", use_for: ["assumption-risk brainstorming"], evidence_output: ["audits/advisory/causalagent_notes.md"], must_not_do: ["approve gates", "certify identification", "upgrade claim status"]}
""",
    "harness/econ_literature_discovery_policy.yml": """version: "0.1"
policy: AEROS-ECON-LIT-DISCOVERY-001
principle: "Econ literature adapters produce candidates only; synthesis still requires full-text extraction cards."
adapters:
  openalex: {role: metadata_and_citation_candidate_source, default_output: ["discovery/literature/search_log.csv"], cannot_support: ["gap_claims"]}
  citec_repec: {role: economics_citation_graph_candidate_source, default_output: ["discovery/literature/citation_graph_edges.csv"], cannot_support: ["gap_claims"]}
  pybiblionet: {role: openalex_network_analysis_candidate_tool, default_output: ["discovery/literature/literature_network_notes.md"], cannot_support: ["synthesis_without_full_text_cards"]}
  preprintresolver: {role: working_paper_to_published_version_resolver, default_output: ["discovery/literature/preprint_resolution_log.csv"], manual_review_required: true, cannot_support: ["bulk_identity_overwrite", "gap_claims", "synthesis_without_full_text_cards"]}
required_artifacts_if_used:
  - discovery/literature/search_log.csv
  - discovery/literature/paper_registry.csv
  - discovery/literature/citation_audit.md
optional_artifacts_if_used:
  - discovery/literature/citation_graph_edges.csv
  - discovery/literature/preprint_resolution_log.csv
  - discovery/literature/literature_network_notes.md
hard_boundaries:
  - Metadata and citation graph discovery are not literature review completion.
  - Full-text extraction cards remain the minimum unit for synthesis support.
""",
    "harness/aea_replication_policy.yml": """version: "0.1"
policy: AEROS-AEA-REPLICATION-ALIGNMENT-001
external_standard: {name: AEA Data Editor replication package guidance, url: "https://aeadataeditor.github.io/"}
policy_version: "February 2026"
source_urls: ["https://www.aeaweb.org/journals/data/data-code-policy", "https://aeadataeditor.github.io/posts/2026-01-19-preparing-pandp-replication-packages"]
principle: "Align replication packages with AEA-style expectations without certifying acceptance."
required_alignment_items: [data_availability_statement, raw_data_or_exception, analysis_data_or_reproducible_build, data_provenance_access_costs, transformation_and_cleaning_code, analysis_code_for_computational_results, master_script_or_precise_step_by_step, setup_program_or_environment, top_level_readme, program_to_output_map, software_hardware_runtime, data_citations, licenses_and_redistribution_rights, trusted_repository_plan, non_public_data_constraints, ethics_irb_or_rct_if_applicable]
required_manifest_fields: [package_id, status, standard_alignment, data_availability, code_entrypoint, environment, result_registry, provenance, licenses, reproducibility]
required_package_artifacts: [README_replication.md, README_data.md, Makefile, requirements.txt, environment.yml, code/99_make_all.py, evidence/result_index.csv, evidence/result_registry.csv]
allowed_statuses: [draft, internal_review, ready_for_human_review, submitted, blocked]
p_and_p_2026_guidance: {compliance_check_scope: "limited compared with peer-reviewed AEA journals", requirement: "package must still be fully compliant with the AEA Data and Code Availability Policy", repository_note: "AEA Data and Code Repository strongly encouraged; GitHub alone is not a trusted archive"}
non_goals: [certify_AEA_acceptance, waive_data_license_or_confidentiality_constraints, replace_human_policy_review, certify_data_editor_acceptance]
""",
    "templates/aea_data_package_manifest.yml": """package_id: "AEA-PACKAGE-001"
status: draft
standard_alignment: {external_standard: "AEA Data Editor", reviewed_against_policy_url: "https://www.aeaweb.org/journals/data/data-code-policy", policy_version: "February 2026", p_and_p_2026_guidance_url: "https://aeadataeditor.github.io/posts/2026-01-19-preparing-pandp-replication-packages", reviewed_at: ""}
aea_2026_alignment: {data_availability_statement: draft, raw_data_or_exception: draft, analysis_data_or_reproducible_build: draft, data_provenance_access_costs: draft, transformation_and_cleaning_code: draft, analysis_code_for_computational_results: draft, master_script_or_precise_step_by_step: draft, setup_program_or_environment: draft, top_level_readme: draft, program_to_output_map: draft, software_hardware_runtime: draft, data_citations: draft, licenses_and_redistribution_rights: draft, trusted_repository_plan: draft, non_public_data_constraints: draft, ethics_irb_or_rct_if_applicable: not_applicable_or_pending}
data_availability: {statement_path: "data/README_data.md", public_data: [], restricted_data: [], synthetic_or_demo_data: []}
code_entrypoint: {command: "make all", master_script: "code/99_make_all.py"}
environment: {requirements_file: "requirements.txt", environment_file: "environment.yml", container_file: ""}
result_registry: {registry_path: "evidence/result_registry.csv", result_index_path: "evidence/result_index.csv"}
provenance: {event_log: "events/event_log.jsonl", provenance_dir: "outputs/.provenance"}
licenses: {data_license_notes: "", code_license_notes: "", redistribution_risks: []}
reproducibility: {last_reproduced_at: "", reproduced_by: "", command_log: "", known_limitations: []}
""",
    "code/99_make_all.py": """#!/usr/bin/env python3
print("AEROS project pipeline placeholder: configure automation.pipeline in project_manifest.yml")
""",
    "README.md": """# AEROS Project

This project was initialized with `aeros init`.
""",
}


def _template_root() -> Path:
    env = os.environ.get("AEROS_TEMPLATE_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _sync_framework_into(root: Path) -> None:
    """Vendor the current AEROS framework into an initialized project."""
    template_root = _template_root()
    sync_script = template_root / "tools" / "sync_aeros_latest.zsh"
    if not sync_script.exists():
        note = root / "AEROS_INIT_SYNC_WARNING.md"
        note.write_text(
            "# AEROS init sync warning\n\n"
            "The scaffold was created, but AEROS runtime/checks could not be "
            "vendored because tools/sync_aeros_latest.zsh was not found next "
            "to the template checkout. Set AEROS_TEMPLATE_ROOT to a full "
            "aeros-template checkout and run `tools/sync_aeros_latest.zsh "
            "<project>` manually.\n",
            encoding="utf-8",
        )
        return
    env = os.environ.copy()
    env.setdefault("AEROS_TEMPLATE_ROOT", str(template_root))
    subprocess.run(["zsh", str(sync_script), str(root)], check=True, env=env)


def init_project(path: str | Path, *, force: bool = False) -> Path:
    root = Path(path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    for directory in DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)

    for rel, content in FILES.items():
        target = root / rel
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    for directory in DIRS:
        marker = root / directory / ".gitkeep"
        if not marker.exists():
            marker.write_text("", encoding="utf-8")

    _sync_framework_into(root)
    return root
