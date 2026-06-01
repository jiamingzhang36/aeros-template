"""Run AEROS checks and parse their results into agent-actionable feedback."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    failures: list[str]
    hint: str
    raw_output: str


def run_check(project_root: Path, check_name: str) -> CheckResult:
    """Run one check script. Prefer --json; fall back to exit-code parsing."""
    script = project_root / "checks" / check_name
    if not script.exists():
        template_script = Path(__file__).resolve().parents[2] / "checks" / check_name
        if template_script.exists():
            script = template_script
        else:
            return CheckResult(check_name, False, [f"check script not found: {script}"], "", "")

    # First try structured JSON output.
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=str(project_root), text=True, capture_output=True,
    )
    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out)
        return CheckResult(
            name=data.get("check", check_name),
            passed=data.get("status") == "pass",
            failures=list(data.get("failures", [])),
            hint=data.get("hint", ""),
            raw_output=out,
        )
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: check does not support --json yet. Re-run plainly.
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(project_root), text=True, capture_output=True,
    )
    combined = ((proc.stdout or "") + (proc.stderr or "")).strip()
    passed = proc.returncode == 0
    failures = [] if passed else [line for line in combined.splitlines() if line.strip()]
    return CheckResult(check_name, passed, failures, "", combined)


def run_checks(project_root: Path, check_names: list[str]) -> tuple[bool, list[CheckResult]]:
    results = [run_check(project_root, name) for name in check_names]
    return all(r.passed for r in results), results


def format_feedback(results: list[CheckResult]) -> str:
    """Turn failed-check output into a compact instruction block for the agent."""
    lines: list[str] = []
    for r in results:
        if r.passed:
            continue
        lines.append(f"### Check FAILED: {r.name}")
        for f in r.failures:
            lines.append(f"- {f}")
        if r.hint:
            lines.append(f"- HINT: {r.hint}")
    return "\n".join(lines)
