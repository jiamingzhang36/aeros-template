"""Incremental package-mode preparation and conservative project detachment."""
from __future__ import annotations

from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
import subprocess
import yaml

VENDORED_SURFACES = ("aeros", "checks", "harness", "templates", "tools", "tests")
ATTACHMENT_MANIFEST = ".aeros/attachment.yml"
ATTACHMENT_MANAGED_PATHS = (".aeros/project.yml", "aeros.lock")


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
        "project_manifest": str(config.get("project_manifest") or "project_manifest.yml"),
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


def attach_package_mode(root: Path, *, policy_bundle_version: str = "aeros-policy-v1") -> dict[str, Any]:
    """Attach a fresh project to the installed runtime without vendoring it.

    Attachment is deliberately limited to package metadata. It refuses to
    overwrite existing package metadata or silently convert a vendored project.
    """
    root = Path(root).resolve()
    manifest_path = root / ATTACHMENT_MANIFEST
    conflicts = [rel for rel in (*ATTACHMENT_MANAGED_PATHS, ATTACHMENT_MANIFEST) if (root / rel).exists()]
    vendored = [name for name in VENDORED_SURFACES if (root / name).exists()]
    failures: list[str] = []
    if not (root / "project_manifest.yml").is_file():
        failures.append("missing project_manifest.yml")
    if conflicts:
        failures.append("existing AEROS metadata: " + ", ".join(conflicts))
    if vendored:
        failures.append("vendored runtime present: " + ", ".join(vendored))
    if failures:
        return {
            "status": "ATTENTION", "attached": False, "failures": failures,
            "does_not_prove": ["package compatibility", "research validity", "safe removal of an existing migration"],
        }
    config_path, lock_path = prepare_package_mode(root, policy_bundle_version=policy_bundle_version)
    records = [{"path": rel, "sha256": _file_hash(root / rel)} for rel in ATTACHMENT_MANAGED_PATHS]
    manifest_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "runtime_mode": "package",
        "managed_files": records,
        "detach_rule": "remove only when every managed file still matches its attach-time SHA-256",
    }, sort_keys=False), encoding="utf-8")
    return {
        "status": "PASS", "attached": True,
        "created": [str(config_path.relative_to(root)), str(lock_path.relative_to(root)), ATTACHMENT_MANIFEST],
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
    expected = {str(item.get("path")): str(item.get("sha256")) for item in records or [] if isinstance(item, dict)}
    if tuple(expected) != ATTACHMENT_MANAGED_PATHS or any(not expected[rel] for rel in ATTACHMENT_MANAGED_PATHS):
        return {
            "status": "ATTENTION", "detached": False, "would_remove": [],
            "failures": ["attachment manifest does not match the fixed package metadata allowlist"],
            "does_not_prove": ["safe detachment"],
        }
    unchanged: list[str] = []
    missing: list[str] = []
    modified: list[str] = []
    for rel in ATTACHMENT_MANAGED_PATHS:
        path = root / rel
        if not path.exists():
            missing.append(rel)
        elif _file_hash(path) == expected[rel]:
            unchanged.append(rel)
        else:
            modified.append(rel)
    report = {
        "status": "DRY_RUN" if not modified else "ATTENTION",
        "detached": False,
        "would_remove": [*unchanged, *missing, ATTACHMENT_MANIFEST],
        "retained_modified": modified,
        "does_not_prove": ["that the installed package is uninstalled", "scientific validity", "safe removal of user-modified metadata"],
    }
    if not confirm or modified:
        return report
    for rel in unchanged:
        (root / rel).unlink()
    manifest_path.unlink()
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
    failures: list[str] = []
    if config.get("runtime_mode") not in {"package", "hybrid"}: failures.append(".aeros/project.yml runtime_mode is not package or hybrid")
    if not lock_path.exists(): failures.append("missing aeros.lock")
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {} if lock_path.exists() else {}
    if str(lock.get("aeros_version") or "") != installed_version(): failures.append("installed AEROS version differs from aeros.lock")
    if str(lock.get("policy_bundle_version") or "") != str(config.get("policy_bundle_version") or ""): failures.append("policy bundle differs from aeros.lock")
    imported = Path(__file__).resolve()
    try: imported.relative_to(root.resolve()); imported_from_project = True
    except ValueError: imported_from_project = False
    if imported_from_project: failures.append("AEROS runtime is still imported from the project vendored tree")
    return {
        "status": "PASS" if not failures else "ATTENTION",
        "failures": failures,
        "aeros_version": installed_version(),
        "runtime_identity": runtime_identity(),
        "imported_runtime": str(imported),
        "vendored_surfaces_present": [name for name in VENDORED_SURFACES if (root / name).exists()],
        "does_not_prove": ["scientific validity", "policy equivalence across versions", "release readiness"],
    }
