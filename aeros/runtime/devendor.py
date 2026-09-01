"""Incremental package-mode preparation and conservative project detachment."""
from __future__ import annotations

from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
import shutil
import subprocess
import yaml

from .project_adapter import detach_entrypoint, detect_project_adapter, entrypoint_plan, install_task_entrypoint, write_project_adapter

VENDORED_SURFACES = ("aeros", "checks", "harness", "templates", "tools", "tests")
ATTACHMENT_MANIFEST = ".aeros/attachment.yml"
LEGACY_ATTACHMENT_MANAGED_PATHS = (".aeros/project.yml", "aeros.lock")
ATTACHMENT_MANAGED_PATHS = (*LEGACY_ATTACHMENT_MANAGED_PATHS, ".aeros/adapter.yml")
ATTACHMENT_CONTEXT_ROOT = Path(".aeros/context")
ATTACHMENT_CONTEXT_MARKER = ATTACHMENT_CONTEXT_ROOT / ".aeros-managed.json"


def installed_version() -> str:
    try:
        return version("aeros-runtime")
    except PackageNotFoundError:
        return "source-tree"


def runtime_identity() -> str:
    package_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(["git", "-C", str(package_root), "rev-parse", "HEAD"], text=True, capture_output=True, timeout=10)
    return proc.stdout.strip() if proc.returncode == 0 else f"package:{installed_version()}"


def _project_config(root: Path) -> dict[str, Any]:
    path = root / ".aeros/project.yml"
    if not path.exists(): return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _removable_context_state(root: Path) -> tuple[bool, list[str]]:
    """Return whether all package-mode context records are AEROS-owned.

    An attachment may safely remove its own compact episode records, but it
    must retain a similarly named directory if a user added any unknown file.
    """
    context_root = root / ATTACHMENT_CONTEXT_ROOT
    marker = root / ATTACHMENT_CONTEXT_MARKER
    if not marker.exists():
        return False, []
    try:
        payload = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return False, [ATTACHMENT_CONTEXT_MARKER.as_posix()]
    if not isinstance(payload, dict) or payload.get("managed_by") != "aeros_context_episode":
        return False, [ATTACHMENT_CONTEXT_MARKER.as_posix()]

    unknown: list[str] = []
    known_episode_records = {"opened.json", "closed.json", "superseded.json"}
    for candidate in context_root.rglob("*"):
        if candidate.is_dir() or candidate == marker:
            continue
        relative = candidate.relative_to(context_root)
        parts = relative.parts
        is_active_pointer = len(parts) == 3 and parts[:2] == ("episodes", "active") and candidate.suffix == ".json"
        is_episode_record = len(parts) == 3 and parts[0] == "episodes" and parts[1] != "active" and parts[2] in known_episode_records
        if not (is_active_pointer or is_episode_record):
            unknown.append(candidate.relative_to(root).as_posix())
    return not unknown, unknown


def prepare_package_mode(root: Path, *, policy_bundle_version: str = "aeros-policy-v1") -> tuple[Path, Path]:
    config_path = root / ".aeros/project.yml"
    lock_path = root / "aeros.lock"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = _project_config(root)
    vendored = [name for name in VENDORED_SURFACES if (root / name).exists()]
    config.update({
        "schema_version": int(config.get("schema_version") or 1),
        "runtime_mode": "hybrid" if vendored else "package",
        "policy_bundle_version": str(config.get("policy_bundle_version") or policy_bundle_version),
        "project_manifest": str(
            config.get("project_manifest")
            or ("project_manifest.yml" if (root / "project_manifest.yml").exists() else "")
        ),
    })
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    lock = {
        "schema_version": int(config.get("schema_version") or 1),
        "aeros_version": installed_version(),
        "runtime_identity": runtime_identity(),
        "policy_bundle_version": str(config.get("policy_bundle_version") or policy_bundle_version),
        "plugin_versions": {},
    }
    lock_path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
    return config_path, lock_path


def attach_package_mode(
    root: Path,
    *,
    policy_bundle_version: str = "aeros-policy-v1",
    with_entrypoint: bool = False,
) -> dict[str, Any]:
    """Attach a fresh project to the installed runtime without vendoring it.

    Attachment is deliberately limited to package metadata. It refuses to
    overwrite existing package metadata or silently convert a vendored project.
    """
    root = Path(root).resolve()
    manifest_path = root / ATTACHMENT_MANIFEST
    entrypoint_preview = entrypoint_plan(root) if with_entrypoint else None
    conflicts = [rel for rel in (*ATTACHMENT_MANAGED_PATHS, ATTACHMENT_MANIFEST) if (root / rel).exists()]
    vendored = [name for name in VENDORED_SURFACES if (root / name).exists()]
    failures: list[str] = []
    if conflicts:
        failures.append("existing AEROS metadata: " + ", ".join(conflicts))
    if vendored:
        failures.append("vendored runtime present: " + ", ".join(vendored))
    if entrypoint_preview and entrypoint_preview.get("status") != "READY":
        failures.extend(entrypoint_preview.get("failures") or ["entrypoint installation needs manual review"])
    if failures:
        return {
            "status": "ATTENTION", "attached": False, "failures": failures,
            "does_not_prove": ["package compatibility", "research validity", "safe removal of an existing migration"],
        }
    config_path, lock_path = prepare_package_mode(root, policy_bundle_version=policy_bundle_version)
    adapter = detect_project_adapter(root)
    adapter["runtime_mode"] = "package"
    adapter_path = write_project_adapter(root, adapter)
    entrypoint = install_task_entrypoint(root) if with_entrypoint else None
    records = [{"path": rel, "sha256": _file_hash(root / rel)} for rel in ATTACHMENT_MANAGED_PATHS]
    manifest = {
        "schema_version": 1,
        "runtime_mode": "package",
        "managed_files": records,
        "detach_rule": "remove only when every managed file still matches its attach-time SHA-256",
    }
    if entrypoint and entrypoint.get("attachment"):
        manifest["entrypoint"] = entrypoint["attachment"]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return {
        "status": "PASS", "attached": True,
        "created": [
            str(config_path.relative_to(root)),
            str(lock_path.relative_to(root)),
            str(adapter_path.relative_to(root)),
            ATTACHMENT_MANIFEST,
            *((entrypoint.get("created") or []) if entrypoint else []),
        ],
        "does_not_prove": ["scientific validity", "policy compatibility", "release readiness"],
    }


def detach_package_mode(root: Path, *, confirm: bool = False) -> dict[str, Any]:
    """Report or remove only unchanged metadata created by ``attach``.

    This is intentionally all-or-nothing for managed metadata. If a project
    changed any tracked metadata, the caller must review it manually rather
    than risking a partial, misleading detachment.
    """
    root = Path(root).resolve()
    manifest_path = root / ATTACHMENT_MANIFEST
    if not manifest_path.is_file():
        return {
            "status": "NOT_ATTACHED", "detached": False, "would_remove": [],
            "failures": [f"missing {ATTACHMENT_MANIFEST}; only attach-managed projects can detach automatically"],
            "does_not_prove": ["that manually created package metadata is safe to remove"],
        }
    try:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {"status": "ATTENTION", "detached": False, "would_remove": [], "failures": [f"invalid attachment manifest: {exc}"], "does_not_prove": ["safe detachment"]}
    records = payload.get("managed_files") if isinstance(payload, dict) else None
    entrypoint_attachment = payload.get("entrypoint") if isinstance(payload, dict) and isinstance(payload.get("entrypoint"), dict) else None
    expected = {str(item.get("path")): str(item.get("sha256")) for item in records or [] if isinstance(item, dict)}
    managed_paths = tuple(expected)
    if managed_paths not in {LEGACY_ATTACHMENT_MANAGED_PATHS, ATTACHMENT_MANAGED_PATHS} or any(not expected[rel] for rel in managed_paths):
        return {
            "status": "ATTENTION", "detached": False, "would_remove": [],
            "failures": ["attachment manifest does not match the fixed package metadata allowlist"],
            "does_not_prove": ["safe detachment"],
        }
    unchanged: list[str] = []
    missing: list[str] = []
    modified: list[str] = []
    for rel in managed_paths:
        path = root / rel
        if not path.exists():
            missing.append(rel)
        elif _file_hash(path) == expected[rel]:
            unchanged.append(rel)
        else:
            modified.append(rel)
    entrypoint = detach_entrypoint(root, attachment=entrypoint_attachment, confirm=False) if entrypoint_attachment else None
    if entrypoint and entrypoint.get("status") == "ATTENTION":
        modified.append("AGENTS.md#AEROS-entrypoint")
    removable_context, retained_context_state = _removable_context_state(root)
    would_remove = [*unchanged, *missing, ATTACHMENT_MANIFEST]
    if entrypoint and entrypoint.get("status") == "DRY_RUN":
        would_remove.extend(entrypoint.get("would_remove") or [])
    if removable_context:
        would_remove.append(f"{ATTACHMENT_CONTEXT_ROOT.as_posix()}/")
    report = {
        "status": "DRY_RUN" if not modified else "ATTENTION",
        "detached": False,
        "would_remove": would_remove,
        "retained_modified": modified,
        "does_not_prove": ["that the installed package is uninstalled", "scientific validity", "safe removal of user-modified metadata"],
    }
    if retained_context_state:
        report["retained_context_state"] = retained_context_state
    if not confirm or modified:
        return report
    for rel in unchanged:
        (root / rel).unlink()
    manifest_path.unlink()
    if removable_context:
        shutil.rmtree(root / ATTACHMENT_CONTEXT_ROOT)
    if entrypoint and entrypoint.get("status") == "DRY_RUN":
        detach_entrypoint(root, attachment=entrypoint_attachment, confirm=True)
    aeros_dir = root / ".aeros"
    try:
        aeros_dir.rmdir()
        report["removed_empty_directory"] = ".aeros"
    except OSError:
        report["retained_project_state"] = ".aeros/"
    report.update({"status": "DETACHED", "detached": True, "removed": report.pop("would_remove")})
    return report


def inspect_migration(root: Path) -> dict[str, Any]:
    vendored = [name for name in VENDORED_SURFACES if (root / name).exists()]
    configured = str(_project_config(root).get("runtime_mode") or "").strip()
    inferred = "hybrid" if vendored and (root / "aeros.lock").exists() else "vendored" if vendored else "package" if (root / "aeros.lock").exists() else "unknown"
    return {
        "runtime_mode": configured or inferred,
        "installed_aeros_version": installed_version(),
        "runtime_identity": runtime_identity(),
        "vendored_surfaces": vendored,
        "ready_to_prepare": (root / "project_manifest.yml").exists(),
        "destructive_changes": [],
        "does_not_prove": ["migration safety", "policy compatibility", "research validity"],
    }


def doctor_package_mode(root: Path) -> dict[str, Any]:
    config = _project_config(root)
    lock_path = root / "aeros.lock"
    configured_mode = str(config.get("runtime_mode") or "").strip().lower()
    vendored = [name for name in VENDORED_SURFACES if (root / name).exists()]
    inferred_mode = "hybrid" if vendored and lock_path.exists() else "vendored" if vendored else "package" if lock_path.exists() else "unknown"
    runtime_mode = configured_mode if configured_mode in {"package", "vendored", "hybrid"} else inferred_mode
    if runtime_mode == "vendored":
        return {
            "status": "PASS",
            "runtime_mode": "vendored",
            "failures": [],
            "warnings": ["project uses its vendored AEROS runtime; use sync doctor for template drift"],
            "aeros_version": "project-vendored",
            "runtime_identity": "project-vendored",
            "imported_runtime": str(Path(__file__).resolve()),
            "vendored_surfaces_present": vendored,
            "does_not_prove": ["template freshness", "scientific validity", "release readiness"],
        }
    failures: list[str] = []
    if runtime_mode not in {"package", "hybrid"}: failures.append("project is not attached to package or vendored AEROS runtime")
    if not lock_path.exists(): failures.append("missing aeros.lock")
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {} if lock_path.exists() else {}
    if str(lock.get("aeros_version") or "") != installed_version(): failures.append("installed AEROS version differs from aeros.lock")
    if str(lock.get("policy_bundle_version") or "") != str(config.get("policy_bundle_version") or ""): failures.append("policy bundle differs from aeros.lock")
    imported = Path(__file__).resolve()
    try: imported.relative_to(root.resolve()); imported_from_project = True
    except ValueError: imported_from_project = False
    warnings: list[str] = []
    if imported_from_project and runtime_mode == "package":
        failures.append("AEROS runtime is still imported from the project vendored tree")
    elif imported_from_project and runtime_mode == "hybrid":
        warnings.append("hybrid mode is using a project-vendored runtime; package metadata is validated but migration is incomplete")
    status = "PASS" if not failures else "ATTENTION"
    if status == "PASS" and runtime_mode == "hybrid":
        status = "MIGRATION_ACTIVE"
    return {
        "status": status,
        "runtime_mode": runtime_mode,
        "failures": failures,
        "warnings": warnings,
        "aeros_version": installed_version(),
        "runtime_identity": runtime_identity(),
        "imported_runtime": str(imported),
        "vendored_surfaces_present": [name for name in VENDORED_SURFACES if (root / name).exists()],
        "does_not_prove": ["scientific validity", "policy equivalence across versions", "release readiness"],
    }
