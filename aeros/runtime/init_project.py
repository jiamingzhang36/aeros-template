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
    "outputs/source_snapshots",
    "outputs/tables",
    "outputs/figures",
    "outputs/model_outputs",
    "paper",
    "tasks/discovery",
    "tasks/execution",
]


FILES = {
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
    key_outputs: []
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
