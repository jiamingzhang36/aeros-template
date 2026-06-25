#!/usr/bin/env python3
"""Validate AgentEnvelope audit mode for provider-backed task runs."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime import kernel  # noqa: E402
from aeros.runtime.agent import AgentResult  # noqa: E402


def _run(cwd: Path, args: list[str]) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aeros_agent_envelope_"))
    _run(tmp, ["git", "init"])
    _run(tmp, ["git", "config", "user.email", "aeros@example.test"])
    _run(tmp, ["git", "config", "user.name", "aeros-test"])
    _write(tmp / "project_manifest.yml", "project:\n  name: fixture\n")
    _write(tmp / "harness/agent_envelope_policy.yml", "mode: audit\nblock_on_violation: true\ndeny_roots:\n- data/raw/\n- decisions/approvals/\n- aeros/state/\n")
    _write(tmp / "checks/check_allowed.py", "from pathlib import Path\nassert Path('outputs/agent/allowed.txt').exists()\nprint('PASS: allowed output exists')\n")
    _write(tmp / "checks/check_always.py", "print('PASS: fixture check')\n")
    _write(tmp / "tasks/T_AGENT_ALLOWED.yml", """task_id: T_AGENT_ALLOWED
stage: discovery
gate: G1
goal: Agent writes only declared output.
inputs: []
allowed_outputs:
- outputs/agent/allowed.txt
checks:
- check_allowed.py
retry_policy:
  max_retries: 0
budget:
  max_agent_calls: 1
  max_dollars: 0.01
""")
    _write(tmp / "tasks/T_AGENT_DENIED.yml", """task_id: T_AGENT_DENIED
stage: discovery
gate: G1
goal: Agent tries to write denied raw data.
inputs: []
allowed_outputs:
- outputs/agent/denied.txt
checks:
- check_always.py
retry_policy:
  max_retries: 0
budget:
  max_agent_calls: 1
  max_dollars: 0.01
""")
    _write(tmp / "tasks/T_AGENT_UNDECLARED.yml", """task_id: T_AGENT_UNDECLARED
stage: discovery
gate: G1
goal: Agent tries to write undeclared output.
inputs: []
allowed_outputs:
- outputs/agent/expected.txt
checks:
- check_always.py
retry_policy:
  max_retries: 0
budget:
  max_agent_calls: 1
  max_dollars: 0.01
""")
    _run(tmp, ["git", "add", "."])
    _run(tmp, ["git", "commit", "-m", "fixture"])
    return tmp


def main() -> int:
    failures: list[str] = []
    original = kernel.run_agent
    try:
        repo = _repo()

        def allowed_agent(_prompt: str, project_root: Path, **_kwargs) -> AgentResult:
            _write(project_root / "outputs/agent/allowed.txt", "allowed\n")
            return AgentResult(ok=True, output="ok", error="")

        kernel.run_agent = allowed_agent
        rc = kernel.run_task(repo / "tasks/T_AGENT_ALLOWED.yml")
        if rc != 0:
            failures.append(f"allowed agent task should pass, got rc={rc}")

        def denied_agent(_prompt: str, project_root: Path, **_kwargs) -> AgentResult:
            _write(project_root / "outputs/agent/denied.txt", "declared\n")
            _write(project_root / "data/raw/secret.csv", "denied\n")
            return AgentResult(ok=True, output="ok", error="")

        kernel.run_agent = denied_agent
        rc = kernel.run_task(repo / "tasks/T_AGENT_DENIED.yml")
        if rc == 0:
            failures.append("denied-write agent task unexpectedly passed")
        audits = sorted((repo / "agent_runs/agent_envelope_audits").glob("T_AGENT_DENIED_*.json"))
        if not audits or "denied_writes" not in audits[-1].read_text(encoding="utf-8"):
            failures.append("denied-write agent task did not write an AgentEnvelope audit")

        def undeclared_agent(_prompt: str, project_root: Path, **_kwargs) -> AgentResult:
            _write(project_root / "outputs/agent/unexpected.txt", "undeclared\n")
            return AgentResult(ok=True, output="ok", error="")

        kernel.run_agent = undeclared_agent
        rc = kernel.run_task(repo / "tasks/T_AGENT_UNDECLARED.yml")
        if rc == 0:
            failures.append("undeclared-write agent task unexpectedly passed")
        audits = sorted((repo / "agent_runs/agent_envelope_audits").glob("T_AGENT_UNDECLARED_*.json"))
        if not audits or "undeclared_writes" not in audits[-1].read_text(encoding="utf-8"):
            failures.append("undeclared-write agent task did not write an AgentEnvelope audit")
    finally:
        kernel.run_agent = original
        if "repo" in locals():
            shutil.rmtree(repo, ignore_errors=True)

    policy = ROOT / "harness/agent_envelope_policy.yml"
    if not policy.exists():
        failures.append("missing harness/agent_envelope_policy.yml")
    else:
        text = policy.read_text(encoding="utf-8")
        for phrase in ["mode: audit", "block_on_violation: true", "does_not_prove"]:
            if phrase not in text:
                failures.append(f"agent envelope policy missing {phrase!r}")

    if failures:
        print("FAIL: AgentEnvelope problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: AgentEnvelope audit mode is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
