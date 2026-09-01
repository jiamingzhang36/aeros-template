"""Generic project adaptation without vendoring the AEROS framework.

The adapter is intentionally a small projection of a project's layout.  It
does not decide whether an artifact is valid, canonical, or claim-supporting;
it only tells the runtime where common research surfaces appear to be.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


ADAPTER_PATH = Path(".aeros/adapter.yml")
ENTRYPOINT_PATH = Path("AGENTS.md")
ENTRYPOINT_BEGIN = "<!-- AEROS:ENTRYPOINT:BEGIN -->"
ENTRYPOINT_END = "<!-- AEROS:ENTRYPOINT:END -->"
ENTRYPOINT_BLOCK = """<!-- AEROS:ENTRYPOINT:BEGIN -->
## AEROS task entrypoint

Before any substantive research or project change:

1. Run `aeros task preflight --intent "<task request>" --json`.
   Before reporting completion, close the active context episode so AEROS can report whether it blocked, redirected, or only recorded guidance.
2. Read `startup_brief` before proposing or executing work. It contains the current goal, highest deterministic research risk, and recommended bounded action.
3. If `startup_brief.status` is `ATTENTION_REQUIRED`, explain that P0 risk and keep unrelated work on hold until the user redirects or clears it.
4. Treat AEROS output as advisory except for explicit process or authority blocks. It does not certify scientific validity, human approval, claim support, or paper readiness.

Do not store raw conversation transcripts in this project merely to satisfy this entrypoint.
<!-- AEROS:ENTRYPOINT:END -->"""
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


def _sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _entrypoint_span(text: str) -> tuple[int, int] | None:
    start = text.find(ENTRYPOINT_BEGIN)
    if start < 0:
        return None
    end_start = text.find(ENTRYPOINT_END, start)
    if end_start < 0:
        return None
    return start, end_start + len(ENTRYPOINT_END)


def entrypoint_plan(root: Path | str) -> dict[str, Any]:
    """Inspect whether a minimal, AEROS-owned task entrypoint can be installed."""
    project_root = Path(root).expanduser().resolve()
    path = project_root / ENTRYPOINT_PATH
    if not path.exists():
        return {"status": "READY", "action": "create", "path": ENTRYPOINT_PATH.as_posix()}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"status": "ATTENTION", "failures": [f"cannot read {ENTRYPOINT_PATH}: {exc}"]}
    has_begin = ENTRYPOINT_BEGIN in text
    has_end = ENTRYPOINT_END in text
    if has_begin != has_end:
        return {"status": "ATTENTION", "failures": ["AEROS entrypoint markers are incomplete; repair manually before installation"]}
    if has_begin:
        span = _entrypoint_span(text)
        if span is None or text[span[0]:span[1]] != ENTRYPOINT_BLOCK:
            return {"status": "ATTENTION", "failures": ["existing AEROS entrypoint block was modified; it will not be overwritten"]}
        return {"status": "READY", "action": "already_installed", "path": ENTRYPOINT_PATH.as_posix()}
    return {"status": "READY", "action": "append", "path": ENTRYPOINT_PATH.as_posix()}


def install_task_entrypoint(root: Path | str, *, dry_run: bool = False) -> dict[str, Any]:
    """Install one bounded task-entry block without replacing project instructions."""
    project_root = Path(root).expanduser().resolve()
    plan = entrypoint_plan(project_root)
    if plan.get("status") != "READY":
        return {"status": "ATTENTION", "installed": False, **plan, "does_not_prove": DOES_NOT_PROVE}
    action = str(plan.get("action") or "")
    if action == "already_installed":
        return {"status": "ALREADY_INSTALLED", "installed": False, "created": [], "does_not_prove": DOES_NOT_PROVE}
    label = f"{ENTRYPOINT_PATH.as_posix()}#AEROS-entrypoint"
    if dry_run:
        return {"status": "DRY_RUN", "installed": False, "would_create": [label], "does_not_prove": DOES_NOT_PROVE}
    path = project_root / ENTRYPOINT_PATH
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    inserted_text = ""
    if action == "create":
        after = ENTRYPOINT_BLOCK + "\n"
    else:
        separator = "" if before.endswith("\n\n") else "\n" if before.endswith("\n") else "\n\n"
        inserted_text = separator + ENTRYPOINT_BLOCK + "\n"
        after = before + inserted_text
    path.write_text(after, encoding="utf-8")
    attachment = {
        "path": ENTRYPOINT_PATH.as_posix(),
        "mode": action,
        "block_sha256": _sha256_text(ENTRYPOINT_BLOCK),
    }
    if action == "create":
        attachment["file_sha256"] = _sha256_text(after)
    else:
        attachment["inserted_text"] = inserted_text
    return {
        "status": "INSTALLED",
        "installed": True,
        "created": [label],
        "attachment": attachment,
        "does_not_prove": DOES_NOT_PROVE,
    }


def detach_entrypoint(
    root: Path | str,
    *,
    attachment: dict[str, Any] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Remove only an intact AEROS entrypoint block, never surrounding instructions."""
    project_root = Path(root).expanduser().resolve()
    path = project_root / ENTRYPOINT_PATH
    if not path.exists():
        return {"status": "NOT_PRESENT", "detached": False, "would_remove": []}
    plan = entrypoint_plan(project_root)
    if plan.get("status") != "READY" or plan.get("action") != "already_installed":
        return {
            "status": "ATTENTION",
            "detached": False,
            "would_remove": [],
            "failures": plan.get("failures") or ["no intact AEROS entrypoint block is available for safe removal"],
        }
    text = path.read_text(encoding="utf-8")
    span = _entrypoint_span(text)
    assert span is not None
    mode = str((attachment or {}).get("mode") or "append")
    expected_file_hash = str((attachment or {}).get("file_sha256") or "")
    if mode == "create":
        if expected_file_hash and _sha256_text(text) != expected_file_hash:
            return {
                "status": "ATTENTION",
                "detached": False,
                "would_remove": [],
                "failures": ["AEROS-created AGENTS.md changed after attachment; retaining it for manual review"],
            }
        would_remove = [ENTRYPOINT_PATH.as_posix()]
        if confirm:
            path.unlink()
        return {"status": "DETACHED" if confirm else "DRY_RUN", "detached": bool(confirm), "would_remove": would_remove, "removed": would_remove if confirm else []}
    inserted_text = str((attachment or {}).get("inserted_text") or "")
    if attachment and not inserted_text:
        return {
            "status": "ATTENTION",
            "detached": False,
            "would_remove": [],
            "failures": ["entrypoint attachment lacks its original inserted text; retaining project instructions for manual review"],
        }
    if inserted_text:
        if not text.endswith(inserted_text):
            return {
                "status": "ATTENTION",
                "detached": False,
                "would_remove": [],
                "failures": ["AEROS entrypoint is no longer its original appended suffix; retaining project instructions for manual review"],
            }
        replacement = text[: -len(inserted_text)]
    else:
        before = text[:span[0]].rstrip()
        after = text[span[1]:].lstrip("\n")
        replacement = (before + "\n\n" + after).rstrip() + "\n" if before and after else (before or after)
    label = f"{ENTRYPOINT_PATH.as_posix()}#AEROS-entrypoint"
    if confirm:
        path.write_text(replacement, encoding="utf-8")
    return {"status": "DETACHED" if confirm else "DRY_RUN", "detached": bool(confirm), "would_remove": [label], "removed": [label] if confirm else []}


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
    install_entrypoint: bool = False,
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
    entrypoint = entrypoint_plan(root) if install_entrypoint else None
    if entrypoint and entrypoint.get("status") != "READY":
        return {"status": "ATTENTION", "attached": False, "failures": entrypoint.get("failures") or ["entrypoint installation needs manual review"]}
    if dry_run:
        target_mode = "package" if requested == "package" or (requested == "auto" and runtime_mode == "unknown") else runtime_mode
        would_create = [".aeros/project.yml", "aeros.lock", ".aeros/adapter.yml"] if target_mode == "package" else [".aeros/adapter.yml"]
        if entrypoint and entrypoint.get("action") in {"create", "append"}:
            would_create.append(f"{ENTRYPOINT_PATH.as_posix()}#AEROS-entrypoint")
        return {
            "status": "DRY_RUN",
            "attached": False,
            "runtime_mode_before": runtime_mode,
            "runtime_mode_after": target_mode,
            "would_create": would_create,
            "adapter": before,
            "does_not_prove": DOES_NOT_PROVE,
        }
    if requested == "package" or (requested == "auto" and runtime_mode == "unknown"):
        from .devendor import attach_package_mode

        report = attach_package_mode(root, policy_bundle_version=policy_bundle_version, with_entrypoint=install_entrypoint)
        report.setdefault("adapter", detect_project_adapter(root))
        return report
    path = write_project_adapter(root, before)
    installed = install_task_entrypoint(root) if install_entrypoint else None
    if installed and installed.get("status") == "ATTENTION":
        return {"status": "ATTENTION", "attached": False, "failures": installed.get("failures") or ["entrypoint installation needs manual review"]}
    return {
        "status": "ADAPTED",
        "attached": True,
        "runtime_mode": runtime_mode,
        "created": [path.relative_to(root).as_posix(), *(installed.get("created") or [])] if installed else [path.relative_to(root).as_posix()],
        "adapter": detect_project_adapter(root),
        "does_not_prove": DOES_NOT_PROVE,
    }
