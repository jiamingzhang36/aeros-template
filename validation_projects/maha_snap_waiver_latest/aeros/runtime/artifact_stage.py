"""Canonical artifact staging selector.

The selector separates canonical outputs from raw/staging captures before a
human or agent commits work.  It can stage canonical paths with ``--apply``, but
it does not commit, approve gates, or certify the content of selected files.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


CANONICAL_PREFIXES = (
    "aeros/state/",
    "aeros/",
    "audits/",
    "checks/",
    "compliance/",
    "data/backfill/",
    "data/clean/",
    "data/final/",
    "data/final_csv/",
    "decisions/",
    "design/",
    "discovery/",
    "docs/",
    "evidence/",
    "harness/",
    "outputs/figures/",
    "outputs/model_outputs/",
    "outputs/tables/",
    "paper/",
    "quality_reports/",
    "replication/",
    "templates/",
    "tools/",
)

CANONICAL_FILES = {
    "AGENTS.md",
    "CONTEXT_BUNDLE.md",
    "CURRENT_STATE.md",
    "NEXT_ACTION.md",
    "SESSION_CONTRACT.yml",
    "project_manifest.yml",
}

RAW_STAGING_PREFIXES = (
    "api_responses/",
    "data/raw/",
    "outputs/logs/",
    "outputs/raw/",
    "request_bundles/",
    "source_snapshots/",
    "work/",
)

DOES_NOT_PROVE = [
    "selected artifacts are scientifically valid",
    "raw staging can be deleted",
    "selected files are safe to release publicly",
    "a commit should be created",
]


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _parse_status_line(line: str) -> str:
    # Porcelain v1: XY<space>path, rename: XY<space>old -> new.
    path = line[3:].strip() if len(line) > 3 else line.strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path


def git_status_paths(root: Path) -> list[str]:
    proc = _run_git(Path(root), ["status", "--porcelain", "--untracked-files=all"])
    if proc.returncode != 0:
        return []
    return [_parse_status_line(line) for line in proc.stdout.splitlines() if line.strip()]


def classify_path(path: str) -> str:
    normalized = path.strip().lstrip("./")
    if not normalized:
        return "unclassified"
    if normalized in CANONICAL_FILES or normalized.startswith(CANONICAL_PREFIXES):
        if normalized.startswith(RAW_STAGING_PREFIXES):
            return "excluded_raw_staging"
        return "canonical"
    if normalized.startswith(RAW_STAGING_PREFIXES):
        return "excluded_raw_staging"
    return "unclassified"


def classify_artifacts(root: Path, paths: list[str] | None = None) -> dict[str, Any]:
    changed = paths if paths is not None else git_status_paths(Path(root))
    buckets = {"canonical": [], "excluded_raw_staging": [], "unclassified": []}
    for path in sorted(set(changed)):
        buckets[classify_path(path)].append(path)
    return {
        "status": "PASS",
        "canonical": buckets["canonical"],
        "excluded_raw_staging": buckets["excluded_raw_staging"],
        "unclassified": buckets["unclassified"],
        "does_not_prove": DOES_NOT_PROVE,
    }


def stage_canonical_artifacts(
    root: Path,
    *,
    apply: bool = False,
    canonical: bool = True,
    exclude_raw_staging: bool = True,
) -> dict[str, Any]:
    report = classify_artifacts(Path(root))
    report["applied"] = False
    report["command"] = "git add -- " + " ".join(report["canonical"]) if report["canonical"] else "no canonical paths"
    if not canonical:
        report["status"] = "REFUSED"
        report["issues"] = ["--canonical is required so this selector cannot be confused with general git add"]
        return report
    if not exclude_raw_staging:
        report["status"] = "REFUSED"
        report["issues"] = ["--exclude-raw-staging is required to keep raw captures out of canonical commits"]
        return report
    if apply and report["canonical"]:
        proc = _run_git(Path(root), ["add", "--", *report["canonical"]])
        report["applied"] = proc.returncode == 0
        report["git_stdout"] = proc.stdout
        report["git_stderr"] = proc.stderr
        if proc.returncode != 0:
            report["status"] = "FAIL"
            report.setdefault("issues", []).append("git add failed")
    return report


def format_artifact_stage_report(report: dict[str, Any]) -> str:
    lines = [f"artifact stage: {report.get('status', 'UNKNOWN')}"]
    lines.append(f"applied: {json.dumps(report.get('applied', False))}")
    for key in ("canonical", "excluded_raw_staging", "unclassified"):
        lines.append(f"{key}:")
        values = report.get(key, [])
        if values:
            lines.extend(f"- {path}" for path in values)
        else:
            lines.append("- none")
    if report.get("issues"):
        lines.append("issues:")
        lines.extend(f"- {issue}" for issue in report["issues"])
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove", []))
    return "\n".join(lines)
