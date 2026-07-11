"""Incremental package-mode preparation; never deletes a vendored runtime."""
from __future__ import annotations

from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
import subprocess
import yaml

VENDORED_SURFACES = ("aeros", "checks", "harness", "templates", "tools", "tests")


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


def prepare_package_mode(root: Path, *, policy_bundle_version: str = "aeros-policy-v1") -> tuple[Path, Path]:
    config_path = root / ".aeros/project.yml"
    lock_path = root / "aeros.lock"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(yaml.safe_dump({
            "schema_version": 1,
            "runtime_mode": "package",
            "policy_bundle_version": policy_bundle_version,
            "project_manifest": "project_manifest.yml",
        }, sort_keys=False), encoding="utf-8")
    config = _project_config(root)
    lock = {
        "schema_version": int(config.get("schema_version") or 1),
        "aeros_version": installed_version(),
        "runtime_identity": runtime_identity(),
        "policy_bundle_version": str(config.get("policy_bundle_version") or policy_bundle_version),
        "plugin_versions": {},
    }
    lock_path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
    return config_path, lock_path


def inspect_migration(root: Path) -> dict[str, Any]:
    vendored = [name for name in VENDORED_SURFACES if (root / name).exists()]
    return {
        "runtime_mode": str(_project_config(root).get("runtime_mode") or "vendored"),
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
    if config.get("runtime_mode") != "package": failures.append(".aeros/project.yml runtime_mode is not package")
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

