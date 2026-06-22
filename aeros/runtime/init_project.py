"""Create a minimal AEROS project scaffold."""

from __future__ import annotations

from pathlib import Path


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
    "outputs/context",
    "outputs/source_snapshots",
    "outputs/tables",
    "outputs/figures",
    "outputs/model_outputs",
    "paper",
    "tasks/discovery",
    "tasks/execution",
    "templates",
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
    cwd: "."
    command: []
    runtime:
      python: "python3"
    key_outputs: []
""",
    "harness/econ_method_advisory_policy.yml": """version: "0.1"
policy: AEROS-ECON-METHOD-ADVISORY-001
principle: Advisory method skills cannot certify identification, claims, or gates.
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
  smoke: {checks: [check_next_action.py, check_context_bundle.py, check_context_graph.py, check_cockpit.py, check_harness_profiles.py]}
  full: {checks: all}
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
    "harness/context_graph_policy.yml": """version: "0.1"
policy: AEROS-CONTEXT-GRAPH-001
principle: Context graph is derived navigation only, not research evidence.
""",
    "harness/status_label_policy.yml": """version: "0.1"
policy: AEROS-STATUS-LABELS-001
principle: "Distinguish mechanical checks, route readiness, and substantive progress."
labels:
  CHECK_PASS: {meaning: "Mechanical checks passed."}
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
# Human-gate trust anchor. Off by default so a new project runs immediately.
# To require a committed human grant at gates: set enforcement to git_committer
# and put your git author name in approver_identity. The autonomous loop commits
# under agent_identity and can never grant its own gate.
human_approval:
  enforcement: "off"             # -> "git_committer" to enable
  approver_identity: []          # e.g. ["your-git-author-name"]
  agent_identity: ["aeros-agent"]
  approval_artifact_dir: "decisions/approvals"
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
    "templates/completion_attestation.yml": """version: 3
task_id: T000
generated_at: ""
completion_mode: agent_run
declared_outcome: complete
outcome_kind: complete
contract_status: failed
verification_level: failed_attestation
progress_class: none
progress_label: CHECK_PASS
authority_status: no_new_authority
work_lane: data
allowed_outputs_expected: []
actual_outputs: []
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
minimal_attestation_fields: [task_id, declared_outcome, work_lane, allowed_outputs_expected, actual_outputs, check_attestations, substantive_progress, does_not_prove]
allowed_declared_outcomes: [complete, partial, blocked, hygiene]
passed_task_rule:
  declared_outcome: complete
  requires:
    - at least one substantive allowed output outside agent_runs/
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
principle: "Align replication packages with AEA-style expectations without certifying acceptance."
required_manifest_fields: [package_id, status, standard_alignment, data_availability, code_entrypoint, environment, result_registry, provenance, licenses, reproducibility]
required_package_artifacts: [README_replication.md, README_data.md, Makefile, requirements.txt, environment.yml, code/99_make_all.py, evidence/result_index.csv, evidence/result_registry.csv]
allowed_statuses: [draft, internal_review, ready_for_human_review, submitted, blocked]
non_goals: [certify_AEA_acceptance, waive_data_license_or_confidentiality_constraints, replace_human_policy_review]
""",
    "templates/aea_data_package_manifest.yml": """package_id: "AEA-PACKAGE-001"
status: draft
standard_alignment: {external_standard: "AEA Data Editor", reviewed_against_policy_url: "https://aeadataeditor.github.io/", reviewed_at: ""}
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

    return root
