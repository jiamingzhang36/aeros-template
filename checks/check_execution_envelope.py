#!/usr/bin/env python3
"""Exercise ExecutionEnvelope isolated-worktree enforcement."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.action_spec import declared_action_spec, validate_action_spec  # noqa: E402
from aeros.runtime.execution_envelope import ExecutionEnvelope, execute_in_isolated_worktree  # noqa: E402


def _run(cwd: Path, args: list[str]) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aeros_envelope_check_"))
    _run(tmp, ["git", "init"])
    _run(tmp, ["git", "config", "user.email", "aeros@example.test"])
    _run(tmp, ["git", "config", "user.name", "aeros-test"])
    _write(tmp / "scripts/good.py", "from pathlib import Path\nPath('outputs/envelope/allowed.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/allowed.txt').write_text('allowed\\n')\n")
    _write(tmp / "scripts/bad.py", "from pathlib import Path\nPath('outputs/envelope/bad.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/bad.txt').write_text('bad\\n')\nPath('paper/draft.md').parent.mkdir(parents=True, exist_ok=True)\nPath('paper/draft.md').write_text('denied\\n')\n")
    _write(tmp / "scripts/undeclared.py", "from pathlib import Path\nPath('outputs/other.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/other.txt').write_text('undeclared\\n')\n")
    _write(tmp / "checks/check_fixture_read_only.py", "from pathlib import Path\nassert Path('scripts/good.py').exists()\nprint('PASS: fixture read-only check')\n")
    _run(tmp, ["git", "add", "."])
    _run(tmp, ["git", "commit", "-m", "fixture"])
    return tmp


def main() -> int:
    failures: list[str] = []
    repo = _repo()
    envelope = ExecutionEnvelope(
        read_roots=(".",),
        write_roots=("outputs/envelope/",),
        deny_roots=("paper/", "evidence/claim_registry.md"),
        expected_outputs=("outputs/envelope/allowed.txt",),
        runtime_profile="local-safe",
    )
    good = execute_in_isolated_worktree(repo, [sys.executable, "scripts/good.py"], envelope)
    if not good.ok:
        failures.append(f"allowed write was not accepted: {good}")
    if not (repo / "outputs/envelope/allowed.txt").exists():
        failures.append("allowed output was not copied back to main repo")
    if not good.worktree_removed:
        failures.append("good run worktree was not removed")

    bad_env = ExecutionEnvelope(
        write_roots=("outputs/envelope/",),
        deny_roots=("paper/", "evidence/claim_registry.md"),
        expected_outputs=("outputs/envelope/bad.txt",),
    )
    bad = execute_in_isolated_worktree(repo, [sys.executable, "scripts/bad.py"], bad_env)
    if bad.ok:
        failures.append("denied write run unexpectedly passed")
    if "paper/draft.md" not in bad.denied_writes:
        failures.append(f"denied write not reported: {bad.denied_writes}")
    if (repo / "paper/draft.md").exists() or (repo / "outputs/envelope/bad.txt").exists():
        failures.append("denied run polluted the main repo")
    if not bad.worktree_removed:
        failures.append("bad run worktree was not removed")

    undeclared_env = ExecutionEnvelope(write_roots=("outputs/envelope/",), expected_outputs=())
    undeclared = execute_in_isolated_worktree(repo, [sys.executable, "scripts/undeclared.py"], undeclared_env)
    if undeclared.ok:
        failures.append("undeclared write run unexpectedly passed")
    if "outputs/other.txt" not in undeclared.undeclared_writes:
        failures.append(f"undeclared write not reported: {undeclared.undeclared_writes}")
    if (repo / "outputs/other.txt").exists():
        failures.append("undeclared run polluted the main repo")

    read_only_env = ExecutionEnvelope(
        read_roots=(".",),
        write_roots=(),
        deny_roots=("paper/", "evidence/claim_registry.md"),
        expected_outputs=(),
        runtime_profile="local-safe-readonly",
    )
    read_only = execute_in_isolated_worktree(repo, [sys.executable, "checks/check_fixture_read_only.py"], read_only_env)
    if not read_only.ok:
        failures.append(f"read-only safe check did not pass under envelope: {read_only}")
    if read_only.observed_writes:
        failures.append(f"read-only safe check wrote files: {read_only.observed_writes}")
    if read_only.accepted_outputs:
        failures.append(f"read-only safe check copied outputs: {read_only.accepted_outputs}")

    invalid = declared_action_spec(
        kind="bad_read_only",
        effect_class="read_only",
        lane="harness",
        command="python3 -m aeros.cli status",
        stop_condition="stop",
        expected_outputs=("outputs/x.txt",),
    )
    if not any("read_only" in item for item in validate_action_spec(invalid)):
        failures.append("read_only ActionSpec with expected_outputs was not rejected")

    if failures:
        print("FAIL: ExecutionEnvelope problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: ExecutionEnvelope isolated-worktree enforcement is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
