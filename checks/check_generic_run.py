#!/usr/bin/env python3
"""Exercise the contract-free, context-bound candidate execution path."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=env, timeout=45)


def fixture() -> Path:
    root = Path(tempfile.mkdtemp(prefix="aeros-generic-run-"))
    for cmd in (["git", "init"], ["git", "config", "user.email", "fixture@example.test"], ["git", "config", "user.name", "fixture"]):
        proc = run(list(cmd), root)
        if proc.returncode:
            raise RuntimeError(proc.stderr or proc.stdout)
    (root / "project_manifest.yml").write_text("project_name: generic-run-fixture\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts/write_audit.py").write_text(
        "from pathlib import Path\nPath('audits').mkdir(exist_ok=True)\nPath('audits/generic.txt').write_text('ok\\n')\n",
        encoding="utf-8",
    )
    (root / "checks").mkdir()
    (root / "checks/check_generic_output.py").write_text(
        "from pathlib import Path\nraise SystemExit(0 if Path('audits/generic.txt').read_text() == 'ok\\n' else 1)\n",
        encoding="utf-8",
    )
    added = run(["git", "add", "project_manifest.yml", "scripts/write_audit.py", "checks/check_generic_output.py"], root)
    committed = run(["git", "commit", "-m", "fixture base"], root)
    if added.returncode or committed.returncode:
        raise RuntimeError(added.stderr or committed.stderr or added.stdout or committed.stdout)
    return root


def main() -> int:
    failures: list[str] = []
    root = fixture()
    command = f"{sys.executable} scripts/write_audit.py"
    proc = run([
        sys.executable, "-m", "aeros.cli", "run",
        "--lane", "analysis",
        "--intent", "write one bounded candidate audit artifact",
        "--command", command,
        "--expected-output", "audits/generic.txt",
        "--acceptance-check", "checks/check_generic_output.py",
        "--json",
    ], root)
    if proc.returncode != 0:
        failures.append(f"generic candidate run failed: {proc.stderr or proc.stdout}")
    else:
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"generic run did not emit JSON: {exc}: {proc.stdout}")
            report = {}
        if report.get("status") != "PASS":
            failures.append(f"generic candidate run did not pass: {report.get('status')!r}")
        if not (root / "audits/generic.txt").is_file():
            failures.append("accepted generic candidate artifact was not copied back")
        effect = report.get("effect") if isinstance(report.get("effect"), dict) else {}
        if effect.get("status") != "RESPONSE_ARTIFACT_OBSERVED":
            failures.append(f"generic run did not record bounded response effect: {effect.get('status')!r}")
        if not effect.get("preflight_recorded"):
            failures.append("generic run did not retain durable preflight evidence")

    dry = run([
        sys.executable, "-m", "aeros.cli", "run",
        "--lane", "writing",
        "--intent", "attempt forbidden manuscript edit",
        "--command", command,
        "--expected-output", "paper/draft.tex",
        "--dry-run",
        "--json",
    ], root)
    if dry.returncode != 2 or "candidate-surface outputs" not in (dry.stdout + dry.stderr):
        failures.append("generic run did not reject a paper output before execution")

    if failures:
        print("FAIL: generic run check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: generic run records context, executes only in an isolated candidate workspace, and reports bounded effect")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
