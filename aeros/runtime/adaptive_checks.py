"""Deterministic observed-write to risk-domain/check selection."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import subprocess
import yaml

RISK_DOMAINS = (
    "execution_integrity", "data_sample_integrity", "specification_integrity",
    "evidence_claim_integrity", "paper_binding_integrity", "release_reproduction_integrity",
)


def _load(root: Path) -> dict[str, Any]:
    return yaml.safe_load((root / "harness/adaptive_checks.yml").read_text(encoding="utf-8")) or {}


def changed_paths(root: Path) -> list[str]:
    proc = subprocess.run(["git", "-C", str(root), "diff", "--name-only", "HEAD"], text=True, capture_output=True, timeout=15)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def select_checks(root: Path, paths: list[str]) -> dict[str, Any]:
    policy = _load(root)
    selected_domains: list[str] = []
    selected_checks: list[str] = []
    for domain, spec in (policy.get("domains") or {}).items():
        prefixes = [str(x) for x in spec.get("path_prefixes") or []]
        if any(any(path == pre.rstrip('/') or path.startswith(pre) for pre in prefixes) for path in paths):
            selected_domains.append(domain)
            selected_checks.extend(str(x) for x in spec.get("checks") or [])
    if not selected_checks:
        selected_checks = list(policy.get("default_checks") or [])
    return {"changed_paths": paths, "risk_domains": selected_domains, "checks": list(dict.fromkeys(selected_checks))}

