"""Data-first project state inspection for AEROS.

This layer is deliberately mechanical. It inventories local data-like files,
reads the structured data inventory, detects data gaps, and writes advisory
state artifacts. It does not certify claims or approve gates.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

DATA_STATE = Path("data/data_state.yml")
GAP_PLAN = Path("data/data_gap_plan.yml")
DATA_REPORT = Path("audits/data_state_report.md")
INVENTORY = Path("discovery/data_inventory.csv")
BACKFILL_QUEUE = Path("data/backfill/backfill_queue.yml")

DATA_EXTENSIONS = {".csv", ".tsv", ".dta", ".xlsx", ".xls", ".parquet", ".feather", ".json", ".jsonl", ".geojson"}
SCRIPT_EXTENSIONS = {".py", ".R", ".r", ".do", ".sql", ".sh", ".zsh", ".js", ".ts"}
OUTPUT_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".parquet", ".png", ".pdf", ".tex", ".md"}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", ".venv", "venv"}


@dataclass(frozen=True)
class DataFirstArgs:
    command: str
    dry_run: bool = False
    write: bool = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def project_mode(root: Path) -> str:
    manifest = _load_yaml(root / "project_manifest.yml")
    project = manifest.get("project", {}) if isinstance(manifest.get("project"), dict) else {}
    research = manifest.get("research", {}) if isinstance(manifest.get("research"), dict) else {}
    explicit = str(project.get("project_mode") or research.get("project_mode") or "").strip()
    if explicit:
        return explicit
    state = _load_yaml(root / "aeros_state.yml")
    if (root / "adoption" / "source_manifest.yml").exists() or (root / "decisions" / "adoption" / "adoption_packet.md").exists():
        return "adopted"
    if state.get("tasks") or str(research.get("topic") or research.get("one_sentence_question") or "").strip():
        return "active_research"
    return "template"


def _artifact_kind(path: Path) -> str:
    rel = path.as_posix()
    ext = path.suffix.lower()
    if rel.startswith("data/") or ext in DATA_EXTENSIONS:
        return "data_like"
    if rel.startswith("code/") or ext in SCRIPT_EXTENSIONS:
        return "code_or_script"
    if rel.startswith("outputs/") or rel.startswith("paper/") or ext in OUTPUT_EXTENSIONS:
        return "output_or_report"
    if rel.startswith("docs/") or rel.startswith("discovery/") or rel.startswith("evidence/"):
        return "research_document"
    return "other"


def scan_project(root: Path) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel_path = path.resolve().relative_to(root.resolve())
        except Exception:
            continue
        if any(part in SKIP_PARTS for part in rel_path.parts):
            continue
        rel = rel_path.as_posix()
        if rel.startswith(("agent_runs/", "data/data_state.yml", "data/data_gap_plan.yml")):
            continue
        kind = _artifact_kind(rel_path)
        if kind == "other":
            continue
        artifacts.append({
            "path": rel,
            "kind": kind,
            "extension": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "empty": path.stat().st_size == 0,
        })
    counts: dict[str, int] = {}
    for item in artifacts:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return {
        "version": 1,
        "generated_at": _now(),
        "project_mode": project_mode(root),
        "artifact_counts": counts,
        "artifacts": artifacts[:1000],
        "truncated": len(artifacts) > 1000,
    }


def read_inventory(root: Path) -> list[dict[str, str]]:
    path = root / INVENTORY
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("data_id") or "").strip()]


def detect_gaps(root: Path, state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    state = state or scan_project(root)
    rows = read_inventory(root)
    gaps: list[dict[str, Any]] = []
    if not rows:
        gaps.append({
            "gap_id": "DATA-GAP-INVENTORY",
            "severity": "high" if state.get("project_mode") == "active_research" else "medium",
            "area": "inventory",
            "issue": "discovery/data_inventory.csv has no populated data rows",
            "next_action": "Run aeros data scan, then complete D002_data_scouting or write a receipt-backed waiver.",
            "automation_class": "receipt_audited",
        })
    if int((state.get("artifact_counts") or {}).get("data_like", 0)) == 0 and state.get("project_mode") in {"active_research", "adopted"}:
        gaps.append({
            "gap_id": "DATA-GAP-LOCAL-FILES",
            "severity": "medium",
            "area": "local_data",
            "issue": "No local data-like artifacts were found",
            "next_action": "Register source paths or queue official-source/API/credentialed collection explicitly.",
            "automation_class": "receipt_audited",
        })
    for row in rows:
        data_id = str(row.get("data_id", "")).strip()
        access = str(row.get("access_status", "")).strip().lower()
        engineering = str(row.get("engineering_status", "")).strip().lower()
        skill_probe = str(row.get("skill_probe_status", "")).strip().lower()
        next_probe = str(row.get("next_probe", "")).strip()
        if access in {"", "unknown", "located", "public", "restricted", "paid", "requested"}:
            gaps.append({
                "gap_id": f"{data_id}-ACCESS",
                "severity": "high" if access in {"restricted", "paid", "requested"} else "medium",
                "area": "access",
                "data_id": data_id,
                "issue": f"access_status={access or 'blank'} is not execution-ready",
                "next_action": next_probe or "Record access evidence/source snapshot or block for approval.",
                "automation_class": "approval_required" if access in {"restricted", "paid", "requested", "public", "located"} else "receipt_audited",
            })
        if engineering != "execution_ready":
            gaps.append({
                "gap_id": f"{data_id}-ENGINEERING",
                "severity": "medium",
                "area": "engineering",
                "data_id": data_id,
                "issue": f"engineering_status={engineering or 'blank'} is not execution_ready",
                "next_action": next_probe or "Run safe local inspection or create a blocked source-limited queue item.",
                "automation_class": "auto_rerunnable" if engineering in {"access_verified", "schema_inspected", "variables_verified", "linkage_tested", "coverage_diagnosed"} else "receipt_audited",
            })
        if skill_probe not in {"done", "blocked"}:
            gaps.append({
                "gap_id": f"{data_id}-SKILL-PROBE",
                "severity": "low",
                "area": "skills",
                "data_id": data_id,
                "issue": f"skill_probe_status={skill_probe or 'blank'} has not documented skill use or waiver",
                "next_action": "Invoke the relevant data skill or record a waiver in the run/skill receipt.",
                "automation_class": "receipt_audited",
            })
    return gaps


def write_scan(root: Path, dry_run: bool = False) -> int:
    state = scan_project(root)
    gaps = detect_gaps(root, state)
    print(f"[data-scan] project_mode: {state['project_mode']}")
    print(f"[data-scan] artifacts: {sum((state.get('artifact_counts') or {}).values())}")
    for kind, count in sorted((state.get("artifact_counts") or {}).items()):
        print(f"[data-scan] {kind}: {count}")
    print(f"[data-scan] gaps: {len(gaps)}")
    if dry_run:
        print("[data-scan] dry-run: no files written")
        return 0
    (root / DATA_STATE).parent.mkdir(parents=True, exist_ok=True)
    (root / DATA_STATE).write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")
    DATA_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Data State Report",
        "",
        f"- Generated at: {state['generated_at']}",
        f"- Project mode: {state['project_mode']}",
        f"- Artifact count: {sum((state.get('artifact_counts') or {}).values())}",
        f"- Gap count: {len(gaps)}",
        "",
        "## Counts",
        "",
    ]
    for kind, count in sorted((state.get("artifact_counts") or {}).items()):
        lines.append(f"- {kind}: {count}")
    lines.extend(["", "## First Data-Like Artifacts", ""])
    for item in [a for a in state.get("artifacts", []) if a.get("kind") == "data_like"][:50]:
        lines.append(f"- {item['path']} ({item['bytes']} bytes)")
    (root / DATA_REPORT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[data-scan] wrote {_rel(root, root / DATA_STATE)}")
    print(f"[data-scan] wrote {_rel(root, root / DATA_REPORT)}")
    return 0


def write_gaps(root: Path, dry_run: bool = False) -> int:
    state = _load_yaml(root / DATA_STATE) or scan_project(root)
    gaps = detect_gaps(root, state)
    payload = {
        "version": 1,
        "generated_at": _now(),
        "project_mode": state.get("project_mode") or project_mode(root),
        "source_state": str(DATA_STATE),
        "backfill_queue": str(BACKFILL_QUEUE),
        "gaps": gaps,
    }
    print(f"[data-gaps] project_mode: {payload['project_mode']}")
    print(f"[data-gaps] gaps: {len(gaps)}")
    for gap in gaps[:50]:
        print(f"  - {gap['gap_id']} [{gap['severity']}/{gap['area']}]: {gap['issue']}")
    if dry_run:
        print("[data-gaps] dry-run: no files written")
        return 0
    (root / GAP_PLAN).parent.mkdir(parents=True, exist_ok=True)
    (root / GAP_PLAN).write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[data-gaps] wrote {_rel(root, root / GAP_PLAN)}")
    return 0


def format_plan(root: Path) -> str:
    state = _load_yaml(root / DATA_STATE) or scan_project(root)
    gaps = detect_gaps(root, state)
    lines = [
        "AEROS Data-First Plan",
        "----------------------",
        f"project_mode: {state.get('project_mode') or project_mode(root)}",
        f"data_like_artifacts: {(state.get('artifact_counts') or {}).get('data_like', 0)}",
        f"inventory_rows: {len(read_inventory(root))}",
        f"gaps: {len(gaps)}",
        "",
        "Recommended next actions:",
    ]
    if not gaps:
        lines.append("- Data state has no detected mechanical gaps; proceed to validation/claim tasks.")
    else:
        lines.append("- Run `aeros data gaps` to materialize data/data_gap_plan.yml.")
        lines.append("- Run `aeros data backfill --dry-run` to convert inventory gaps into the formal backfill queue.")
        lines.append("- Auto-run only local-cache queue items with explicit run_command; approval/source-limited items need human approval or receipt.")
        lines.append("- Do not advance claims until data gaps are closed, receipt-audited, or explicitly bounded.")
    return "\n".join(lines)
