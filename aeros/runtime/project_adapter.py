"""Generic project adaptation without vendoring the AEROS framework.

The adapter is intentionally a small projection of a project's layout.  It
does not decide whether an artifact is valid, canonical, or claim-supporting;
it only tells the runtime where common research surfaces appear to be.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ADAPTER_PATH = Path(".aeros/adapter.yml")
VENDORED_SURFACES = ("aeros", "checks", "harness", "templates", "tools", "tests")

PATH_CANDIDATES: dict[str, tuple[str, ...]] = {
    "manifest": ("project_manifest.yml", "project.yml"),
    "instructions": ("AGENTS.md", "CLAUDE.md", "README.md"),
    "state": ("CURRENT_STATE.md", "CURRENT_WORK.yml", "context/CURRENT_STATE.md"),
    "manuscript": ("tex/paper.tex", "paper", "paper/", "manuscript", "manuscript/", "output/tex"),
    "bibliography": ("tex/references.bib", "references.bib", "bibliography", "bibliography/"),
    "literature": ("discovery/literature", "literature", "references"),
    "data": ("data", "data/", "raw", "raw/"),
    "results": ("outputs", "outputs/", "output", "output/", "results", "results/"),
    "provenance": ("outputs/.provenance", "provenance", "provenance/"),
    "claims": ("evidence/claim_registry.md", "claims", "claims/"),
    "decisions": ("decisions", "decisions/"),
    "tasks": ("tasks", "tasks/"),
    "run_records": ("agent_runs", "agent_runs/", "runs", "runs/"),
    "checks": ("checks", "checks/"),
    "harness": ("harness", "harness/"),
}


DOES_NOT_PROVE = [
    "that the project has scientifically valid data or results",
    "that a detected directory is canonical or claim-supporting",
    "that a missing surface is unnecessary",
    "that a package/runtime policy is compatible with every project convention",
]


def _configured_mode(root: Path) -> str:
    path = root / ".aeros/project.yml"
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        mode = str(data.get("runtime_mode") or "").strip().lower()
        if mode in {"package", "vendored", "hybrid"}:
            return mode
    vendored = any((root / name).exists() for name in VENDORED_SURFACES)
    if vendored and (root / "aeros.lock").exists():
        return "hybrid"
    if vendored:
        return "vendored"
    if (root / "aeros.lock").exists():
        return "package"
    return "unknown"


def _project_id(root: Path) -> str:
    manifest = root / "project_manifest.yml"
    if manifest.exists():
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            project = data.get("project") if isinstance(data, dict) else {}
            name = project.get("name") if isinstance(project, dict) else ""
            if name:
                return str(name)
        except yaml.YAMLError:
            pass
    return root.name or "aeros-project"


def _present_paths(root: Path, candidates: tuple[str, ...]) -> list[str]:
    present: list[str] = []
    seen: set[str] = set()
    for rel in candidates:
        normalized = rel.rstrip("/")
        path = root / normalized
        if path.exists() and normalized not in seen:
            present.append(normalized)
            seen.add(normalized)
    return present


CONTEXT_ANCHOR_NAMES = (
    "CURRENT_STATE.md",
    "CURRENT_WORK.yml",
    "README.md",
    "README",
    "draft.md",
    "paper.tex",
    "main.tex",
    "metadata.yml",
    "metadata.yaml",
)

LANE_SURFACES = {
    "data": ("state", "data", "results", "provenance"),
    "literature": ("state", "literature", "bibliography", "manuscript"),
    "method": ("state", "manuscript", "results"),
    "analysis": ("state", "data", "results", "provenance"),
    "claim": ("state", "claims", "literature", "manuscript"),
    "writing": ("state", "manuscript", "bibliography", "claims"),
    "compliance": ("state", "decisions", "run_records", "provenance"),
}


def context_anchor_paths(
    root: Path | str,
    *,
    adapter: dict[str, Any] | None = None,
    lane: str = "project",
) -> list[str]:
    """Return a small, non-data-heavy set of context anchors for any project.

    Directories are never recursively scanned or content-hashed.  An adapter
    may expose ``data/`` or ``paper/``, but only lightweight conventional files
    inside those directories become context inputs.
    """

    project_root = Path(root).expanduser().resolve()
    payload = adapter or detect_project_adapter(project_root)
    path_map = payload.get("path_map") if isinstance(payload.get("path_map"), dict) else {}
    surfaces = LANE_SURFACES.get(str(lane or "").strip().lower())
    if surfaces is None:
        surfaces = ("state", "manifest", "instructions", "manuscript", "bibliography", "literature", "data", "results", "claims", "decisions")
    anchors: list[str] = []
    for rel in (".aeros/adapter.yml", ".aeros/project.yml", "aeros.lock"):
        if (project_root / rel).is_file():
            anchors.append(rel)
    for surface in surfaces:
        values = path_map.get(surface) if isinstance(path_map, dict) else []
        for raw in values if isinstance(values, list) else []:
            rel = str(raw).strip().rstrip("/")
            if not rel:
                continue
            path = project_root / rel
            if path.is_file():
                anchors.append(rel)
                continue
            if not path.is_dir():
                continue
            for name in CONTEXT_ANCHOR_NAMES:
                candidate = path / name
                if candidate.is_file():
                    anchors.append(candidate.relative_to(project_root).as_posix())
                    break
    return list(dict.fromkeys(anchors))


def detect_project_adapter(root: Path | str) -> dict[str, Any]:
    """Inspect a project using conventional paths without writing anything."""
    root = Path(root).expanduser().resolve()
    path_map = {key: _present_paths(root, values) for key, values in PATH_CANDIDATES.items()}
    detected = {key: bool(values) for key, values in path_map.items()}
    research_surface_count = sum(
        detected.get(key, False)
        for key in ("manuscript", "bibliography", "literature", "data", "results", "claims")
    )
    return {
        "schema_version": 1,
        "adapter_id": "aeros.generic.project",
        "project_id": _project_id(root),
        "project_root": root.as_posix(),
        "runtime_mode": _configured_mode(root),
        "project_kind": "research_project" if research_surface_count else "generic_project",
        "git_present": (root / ".git").exists(),
        "path_map": path_map,
        "detected": detected,
        "research_surface_count": research_surface_count,
        "status": "READY" if root.is_dir() else "ATTENTION",
        "does_not_prove": DOES_NOT_PROVE,
    }


def write_project_adapter(root: Path | str, adapter: dict[str, Any] | None = None) -> Path:
    root = Path(root).expanduser().resolve()
    path = root / ADAPTER_PATH
    payload = dict(adapter or detect_project_adapter(root))
    payload["project_root"] = root.as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def attach_project(
    root: Path | str,
    *,
    mode: str = "auto",
    dry_run: bool = False,
    policy_bundle_version: str = "aeros-policy-v1",
) -> dict[str, Any]:
    """Attach a project by metadata only, preserving all research files."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        return {"status": "ATTENTION", "attached": False, "failures": [f"project directory not found: {root}"]}
    requested = (mode or "auto").strip().lower()
    if requested not in {"auto", "package", "adapter"}:
        return {"status": "ATTENTION", "attached": False, "failures": [f"unsupported attach mode: {mode}"]}
    before = detect_project_adapter(root)
    runtime_mode = str(before.get("runtime_mode") or "unknown")
    if dry_run:
        target_mode = "package" if requested == "package" or (requested == "auto" and runtime_mode == "unknown") else runtime_mode
        return {
            "status": "DRY_RUN",
            "attached": False,
            "runtime_mode_before": runtime_mode,
            "runtime_mode_after": target_mode,
            "would_create": [".aeros/project.yml", "aeros.lock", ".aeros/adapter.yml"]
            if target_mode == "package"
            else [".aeros/adapter.yml"],
            "adapter": before,
            "does_not_prove": DOES_NOT_PROVE,
        }
    if requested == "package" or (requested == "auto" and runtime_mode == "unknown"):
        from .devendor import attach_package_mode

        report = attach_package_mode(root, policy_bundle_version=policy_bundle_version)
        report.setdefault("adapter", detect_project_adapter(root))
        return report
    path = write_project_adapter(root, before)
    return {
        "status": "ADAPTED",
        "attached": True,
        "runtime_mode": runtime_mode,
        "created": [path.relative_to(root).as_posix()],
        "adapter": detect_project_adapter(root),
        "does_not_prove": DOES_NOT_PROVE,
    }
