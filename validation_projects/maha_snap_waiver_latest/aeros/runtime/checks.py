"""Run AEROS checks and parse their results into agent-actionable feedback."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    failures: list[str]
    hint: str
    raw_output: str
    command: list[str]
    exit_code: int
    elapsed_seconds: float


def run_check(project_root: Path, check_name: str) -> CheckResult:
    """Run one check script. Prefer --json; fall back to exit-code parsing."""
    started = time.monotonic()
    script = project_root / "checks" / check_name
    if not script.exists():
        template_script = Path(__file__).resolve().parents[2] / "checks" / check_name
        if template_script.exists():
            script = template_script
        else:
            return CheckResult(check_name, False, [f"check script not found: {script}"], "", "", [], 127, 0.0)
    try:
        if script.stat().st_size == 0:
            return CheckResult(
                check_name,
                False,
                [f"check script is empty/no-op: {script.relative_to(project_root) if project_root in script.parents else script}"],
                "A check must emit a real PASS/FAIL signal; empty scripts are not valid checks.",
                "",
                [],
                126,
                round(time.monotonic() - started, 3),
            )
    except OSError as exc:
        return CheckResult(check_name, False, [f"could not stat check script {script}: {exc}"], "", "", [], 126, 0.0)

    # First try structured JSON output.
    json_command = [sys.executable, str(script), "--json"]
    proc = subprocess.run(
        json_command,
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
            command=json_command,
            exit_code=proc.returncode,
            elapsed_seconds=round(time.monotonic() - started, 3),
        )
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: check does not support --json yet. Re-run plainly.
    plain_command = [sys.executable, str(script)]
    proc = subprocess.run(
        plain_command,
        cwd=str(project_root), text=True, capture_output=True,
    )
    combined = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode == 0 and not combined:
        return CheckResult(
            check_name,
            False,
            [f"check script produced no output: {script.relative_to(project_root) if project_root in script.parents else script}"],
            "A successful check must print an explicit PASS message or structured JSON.",
            combined,
            plain_command,
            proc.returncode,
            round(time.monotonic() - started, 3),
        )
    passed = proc.returncode == 0
    failures = [] if passed else [line for line in combined.splitlines() if line.strip()]
    return CheckResult(
        check_name,
        passed,
        failures,
        "",
        combined,
        plain_command,
        proc.returncode,
        round(time.monotonic() - started, 3),
    )


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
