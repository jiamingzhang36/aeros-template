"""Work-lane routing for AEROS task execution.

The lane layer is intentionally a view/control surface, not a new truth source.
It keeps data, literature, analysis, claims, writing, compliance, and harness
maintenance from being mixed in one "continue" run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

LANES = {
    "data",
    "literature",
    "analysis",
    "claim",
    "writing",
    "compliance",
    "harness",
}

COMMON_OUTPUT_PREFIXES = (
    "agent_runs/",
    "decisions/",
)
COMMON_OUTPUT_PATHS = {
    "agent_runs",
}

LANE_OUTPUT_PREFIXES = {
    "data": (
        "data/",
        "discovery/data",
        "discovery/variable_construction",
        "audits/data",
        "audits/expanded",
        "outputs/audit_runs/",
        "outputs/data/",
        "outputs/tables/expanded",
    ),
    "literature": (
        "discovery/literature/",
    ),
    "analysis": (
        "code/",
        "execution/",
        "outputs/",
        "evidence/result",
        "docs/robustness",
        "audits/design",
        "audits/result",
        "audits/replication",
    ),
    "claim": (
        "evidence/claim",
        "evidence/research_graph",
        "audits/claim",
        "docs/language",
    ),
    "writing": (
        "paper/",
        "tex/",
        "references",
        "audits/paper",
        "audits/referee",
        "README_replication",
    ),
    "compliance": (
        "compliance/",
        "audits/compliance",
        "data/README_data",
        "README_replication",
    ),
    "harness": (
        "AGENTS.md",
        "checks/",
        "harness/",
        "templates/",
        "tools/",
        "project_manifest.yml",
        "agent_runs/TEMPLATE",
        "docs/architecture",
        "decisions/update_ledger",
        "decisions/revision_log",
    ),
}

LANE_FORBIDDEN_PREFIXES = {
    "data": ("paper/", "tex/", "evidence/claim", "compliance/"),
    "literature": ("data/raw/", "outputs/", "paper/", "tex/", "evidence/claim", "compliance/"),
    "analysis": ("data/raw/", "paper/", "tex/", "compliance/"),
    "claim": ("data/raw/", "outputs/audit_runs/", "paper/", "tex/"),
    "writing": ("data/raw/", "outputs/audit_runs/", "evidence/claim"),
    "compliance": ("data/raw/", "paper/", "tex/", "evidence/claim"),
    "harness": ("data/raw/", "outputs/", "paper/", "tex/", "evidence/claim"),
}


def normalize_lane(raw: str | None) -> str:
    lane = str(raw or "").strip().lower().replace("_", "-")
    aliases = {
        "lit": "literature",
        "literature-review": "literature",
        "data-first": "data",
        "claims": "claim",
        "paper": "writing",
        "write": "writing",
        "maintenance": "harness",
        "framework": "harness",
    }
    lane = aliases.get(lane, lane)
    if lane not in LANES:
        return ""
    return lane


def infer_work_lane(contract: object) -> str:
    raw = getattr(contract, "raw", {}) or {}
    explicit = normalize_lane(raw.get("work_lane"))
    if explicit:
        return explicit

    task_id = str(getattr(contract, "task_id", "") or "")
    outputs = " ".join(str(item) for item in getattr(contract, "allowed_outputs", []) or [])
    goal = str(getattr(contract, "goal", "") or "").lower()
    text = f"{task_id} {outputs} {goal}".lower()

    if task_id.startswith("LIT-") or "discovery/literature/" in text:
        return "literature"
    if task_id in {"D002_data_scouting", "D004_variable_construction", "D005_data_probe",
                   "T002_data_feasibility", "T009_expanded_collection_design",
                   "T010_expanded_ai_output_collection", "T011_expanded_result_validation"}:
        return "data"
    if task_id in {"T005_claim_audit", "T012_claim_upgrade_review"} or "claim_audit" in text:
        return "claim"
    if task_id in {"T006_referee_panel", "T008_paper_package_draft"} or "paper/" in text:
        return "writing"
    if task_id in {"T013_compliance_release_review"} or "compliance/" in text:
        return "compliance"
    if task_id.startswith("D") and any(token in text for token in ["design", "method", "funnel", "variable"]):
        return "analysis"
    if any(token in text for token in ["code/99_make_all", "execution/", "result_index", "robustness"]):
        return "analysis"
    if any(token in text for token in ["checks/", "harness/", "templates/", "agents.md"]):
        return "harness"
    return "analysis"


def lane_matches(contract: object, lane: str | None) -> bool:
    normalized = normalize_lane(lane)
    if not normalized:
        return True
    return infer_work_lane(contract) == normalized


def _norm_path(raw: str) -> str:
    return str(raw or "").strip().replace("\\", "/").lstrip("./").rstrip("/")


def output_lane_problems(lane: str, outputs: Iterable[str]) -> list[str]:
    normalized = normalize_lane(lane)
    if not normalized:
        return [f"invalid work_lane {lane!r}"]
    failures: list[str] = []
    allowed = LANE_OUTPUT_PREFIXES[normalized]
    forbidden = LANE_FORBIDDEN_PREFIXES.get(normalized, ())
    for raw in outputs:
        rel = _norm_path(str(raw))
        if not rel:
            continue
        if rel in COMMON_OUTPUT_PATHS or rel.startswith(COMMON_OUTPUT_PREFIXES):
            continue
        if any(rel.startswith(prefix.rstrip("/")) for prefix in forbidden):
            failures.append(f"{rel}: forbidden output for {normalized} lane")
            continue
        if any(rel.startswith(prefix.rstrip("/")) for prefix in allowed):
            continue
        # Soft compatibility: audits are allowed unless they obviously belong to
        # another lane. This keeps existing contracts usable while catching the
        # dangerous cross-lane writes.
        if rel.startswith("audits/"):
            continue
    return failures


def lane_policy_path(project_root: Path) -> Path:
    return project_root / "harness/work_lane_policy.yml"
