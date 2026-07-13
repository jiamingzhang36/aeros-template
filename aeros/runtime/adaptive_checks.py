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


def assess_post_action(
    root: Path,
    paths: list[str],
    *,
    action_exit_code: int | None,
    expected_outputs: list[str],
) -> dict[str, Any]:
    """Fail closed around an adaptive post-action check selection.

    Selection alone is not completion evidence. A candidate-profile action must
    expose its observed exit code and at least one non-empty expected artifact
    inside the candidate worktree before selected checks can be treated as a
    passing post-action gate.
    """
    report = select_checks(root, paths)
    blockers: list[str] = []
    if action_exit_code is None:
        blockers.append("action_exit_not_observed")
    elif action_exit_code != 0:
        blockers.append(f"action_exit_nonzero:{action_exit_code}")

    if not expected_outputs:
        blockers.append("expected_outputs_not_declared")
    else:
        resolved_root = root.resolve()
        for raw in expected_outputs:
            candidate = (root / raw).resolve()
            try:
                candidate.relative_to(resolved_root)
            except ValueError:
                blockers.append(f"expected_output_outside_project:{raw}")
                continue
            if not candidate.is_file():
                blockers.append(f"expected_output_missing:{raw}")
            elif candidate.stat().st_size <= 0:
                blockers.append(f"expected_output_empty:{raw}")

    report.update({
        "post_action_evaluated": True,
        "action_exit_code": action_exit_code,
        "expected_outputs": list(expected_outputs),
        "blockers": blockers,
        "status": "FAIL" if blockers else "PASS",
        "does_not_prove": [
            "that a non-empty artifact is scientifically valid",
            "that a pre-existing artifact was freshly regenerated",
            "that selected checks cover omitted dependency paths",
            "that promotion, claim, gate, or release authority is granted",
        ],
    })
    return report
