"""Diagnose whether downstream projects have the latest AEROS adapter layer.

The sync doctor is advisory. It compares framework files in a project against
the template and reports missing/outdated capabilities; it does not sync files,
approve gates, or modify project state.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


CAPABILITIES: dict[str, list[str]] = {
    "improve": ["aeros/runtime/improve_harvest.py", "checks/check_improve_harvest.py"],
    "mode": ["aeros/runtime/execution_mode.py", "aeros/runtime/task_mode.py", "harness/task_mode_policy.yml", "checks/check_task_mode.py"],
    "artifact_stage": ["aeros/runtime/artifact_stage.py", "checks/check_artifact_stage.py"],
    "skill_coverage": ["aeros/runtime/skill_obligation.py", "harness/skill_obligation_policy.yml", "checks/check_skill_coverage.py"],
    "output_intent": ["aeros/runtime/output_intent.py", "harness/output_intent_policy.yml", "checks/check_output_intent.py"],
    "source_capture_permission": ["aeros/runtime/source_capture_permission.py", "harness/source_capture_permission_policy.yml", "checks/check_source_capture_permission.py"],
    "task_preflight": ["aeros/runtime/task_preflight.py", "checks/check_task_preflight.py"],
}

DOES_NOT_PROVE = [
    "that a project is scientifically correct",
    "that a project should be synced now",
    "that local project customizations are safe to overwrite",
    "that gates, claims, or papers are approved",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_template_root(current_root: Path) -> Path:
    env = os.environ.get("AEROS_TEMPLATE_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if (current_root / "tools" / "sync_aeros_latest.zsh").exists():
        return current_root.resolve()
    fallback = Path("/Users/jiamingzhang/aeros-template")
    return fallback if fallback.exists() else current_root.resolve()


def default_project_roots(root: Path) -> list[Path]:
    root = root.resolve()
    if not (root / "tools" / "sync_aeros_latest.zsh").exists() and (root / "project_manifest.yml").exists():
        return [root]
    validation = root / "validation_projects"
    if not validation.exists():
        return []
    return [path for path in sorted(validation.iterdir()) if (path / "project_manifest.yml").exists()]


def diagnose_project(template_root: Path, project_root: Path) -> dict[str, Any]:
    template_root = Path(template_root).resolve()
    project_root = Path(project_root).resolve()
    capabilities: dict[str, dict[str, Any]] = {}
    missing_capabilities: list[str] = []
    outdated_capabilities: list[str] = []
    for capability, rels in CAPABILITIES.items():
        file_rows: list[dict[str, str]] = []
        cap_missing = False
        cap_outdated = False
        for rel in rels:
            template_path = template_root / rel
            project_path = project_root / rel
            if not template_path.exists():
                status = "template_missing"
                cap_missing = True
            elif not project_path.exists():
                status = "missing"
                cap_missing = True
            else:
                status = "ok" if _sha256(template_path) == _sha256(project_path) else "outdated"
                cap_outdated = cap_outdated or status == "outdated"
            file_rows.append({"path": rel, "status": status})
        if cap_missing:
            missing_capabilities.append(capability)
        elif cap_outdated:
            outdated_capabilities.append(capability)
        capabilities[capability] = {
            "status": "missing" if cap_missing else "outdated" if cap_outdated else "ok",
            "files": file_rows,
        }
    return {
        "project": project_root.as_posix(),
        "status": "PASS" if not missing_capabilities and not outdated_capabilities else "ATTENTION",
        "missing_capabilities": missing_capabilities,
        "outdated_capabilities": outdated_capabilities,
        "capabilities": capabilities,
    }


def sync_doctor(root: Path, *, projects: list[str] | None = None, template_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root)
    tpl = Path(template_root).expanduser().resolve() if template_root else default_template_root(root)
    project_roots = [Path(p).expanduser().resolve() for p in (projects or [])] or default_project_roots(root)
    rows = [diagnose_project(tpl, project) for project in project_roots if (project / "project_manifest.yml").exists()]
    missing = sum(len(row["missing_capabilities"]) for row in rows)
    outdated = sum(len(row["outdated_capabilities"]) for row in rows)
    return {
        "status": "PASS" if rows and missing == 0 and outdated == 0 else "ATTENTION",
        "template_root": tpl.as_posix(),
        "projects_checked": len(rows),
        "projects": rows,
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_sync_doctor(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Sync Doctor",
        "",
        f"status: {report.get('status')}",
        f"template_root: {report.get('template_root')}",
        f"projects_checked: {report.get('projects_checked')}",
        "",
        "projects:",
    ]
    for project in report.get("projects", []):
        lines.append(f"- project: {project.get('project')}")
        lines.append(f"  status: {project.get('status')}")
        lines.append(f"  missing_capabilities: {project.get('missing_capabilities')}")
        lines.append(f"  outdated_capabilities: {project.get('outdated_capabilities')}")
    lines.append("")
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
