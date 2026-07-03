"""Harvest framework-improvement signals from local AEROS artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


DOES_NOT_PROVE = [
    "that a proposed improvement is worth implementing",
    "that a task was scientifically successful",
    "that failures are bugs rather than real blockers",
    "that a human approved the backlog",
]


def _load_yaml(path: Path) -> Any:
    if not path.exists() or yaml is None:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None


def harvest_improvements(root: Path) -> dict[str, Any]:
    root = Path(root)
    candidates: list[dict[str, str]] = []

    for receipt in sorted((root / "agent_runs" / "skill_invocations").glob("*_skill_invocations.yml")):
        data = _load_yaml(receipt) or {}
        if data.get("skill_obligations") and not data.get("skills_used") and data.get("skill_waivers"):
            candidates.append({
                "kind": "skill_waiver_pattern",
                "source": receipt.as_posix(),
                "summary": "Skill obligation was waived; review whether task template needs better skill routing.",
            })

    for log in sorted((root / "outputs" / "logs").glob("*check_summary*.json")):
        try:
            data = json.loads(log.read_text(encoding="utf-8"))
        except Exception:
            continue
        failed = [item for item in data.get("checks", []) if item.get("exit_code") not in {0, "0"}]
        if failed:
            candidates.append({
                "kind": "recurring_check_failure",
                "source": log.as_posix(),
                "summary": f"{len(failed)} check(s) failed; inspect whether this is a project blocker or framework mismatch.",
            })

    if not candidates:
        candidates.append({
            "kind": "no_signal",
            "source": "local artifacts",
            "summary": "No harvestable improvement signals found in current local logs/receipts.",
        })

    return {
        "status": "ADVISORY",
        "backlog_candidates": candidates,
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_harvest(report: dict[str, Any]) -> str:
    lines = ["# AEROS Improvement Harvest", "", f"status: {report.get('status')}", "", "backlog_candidates:"]
    for item in report.get("backlog_candidates", []):
        lines.append(f"- kind: {item.get('kind')}")
        lines.append(f"  source: {item.get('source')}")
        lines.append(f"  summary: {item.get('summary')}")
    lines.append("")
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
