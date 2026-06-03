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
    "decisions/escalations",
    "discovery/literature",
    "docs",
    "evidence",
    "evidence/receipts",
    "execution",
    "harness/protocols",
    "outputs/logs",
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
  current_gate: "G0 Project Intake"
automation:
  pipeline:
    cwd: "."
    command: []
    key_outputs: []
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
