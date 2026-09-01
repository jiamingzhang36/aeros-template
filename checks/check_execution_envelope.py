#!/usr/bin/env python3
"""Exercise ExecutionEnvelope isolated-worktree enforcement."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.action_spec import declared_action_spec, validate_action_spec  # noqa: E402
from aeros.runtime.execution_envelope import ExecutionEnvelope, execute_action_spec_in_isolated_worktree, execute_in_isolated_worktree  # noqa: E402


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
    shutil.copytree(ROOT / "aeros", tmp / "aeros", ignore=shutil.ignore_patterns("__pycache__"))
    # The fixture vendors the policy needed by EnvironmentProfile compilation,
    # but intentionally omits the full adaptive-check catalog.  It is not a
    # complete research project, so deterministic task execution must retain
    # its explicit contract check rather than selecting absent project checks.
    (tmp / "harness").mkdir()
    shutil.copy2(ROOT / "harness/environment_profiles.yml", tmp / "harness/environment_profiles.yml")
    if (ROOT / "project_manifest.yml").exists():
        shutil.copy2(ROOT / "project_manifest.yml", tmp / "project_manifest.yml")
    _write(tmp / "scripts/good.py", "from pathlib import Path\nPath('outputs/envelope/allowed.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/allowed.txt').write_text('allowed\\n')\n")
    _write(tmp / "scripts/bad.py", "from pathlib import Path\nPath('outputs/envelope/bad.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/bad.txt').write_text('bad\\n')\nPath('paper/draft.md').parent.mkdir(parents=True, exist_ok=True)\nPath('paper/draft.md').write_text('denied\\n')\n")
    _write(tmp / "scripts/undeclared.py", "from pathlib import Path\nPath('outputs/other.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/other.txt').write_text('undeclared\\n')\n")
    _write(tmp / "scripts/extra.py", "from pathlib import Path\nPath('outputs/envelope/expected.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/expected.txt').write_text('expected\\n')\nPath('outputs/envelope/extra.txt').write_text('extra\\n')\n")
    _write(tmp / "scripts/fail_validation.py", "from pathlib import Path\nPath('outputs/envelope/unvalidated.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/unvalidated.txt').write_text('candidate\\n')\n")
    _write(tmp / "scripts/validator_target.py", "from pathlib import Path\nPath('outputs/envelope/validator_target.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/validator_target.txt').write_text('original\\n')\n")
    _write(tmp / "scripts/transaction.py", "from pathlib import Path\np=Path('outputs/envelope'); p.mkdir(parents=True, exist_ok=True); (p/'tx_a.txt').write_text('a\\n'); (p/'tx_b.txt').write_text('b\\n')\n")
    _write(tmp / "scripts/module_target.py", "from pathlib import Path\nPath('outputs/envelope/module_target.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/envelope/module_target.txt').write_text('candidate\\n')\n")
    _write(tmp / "scripts/run_good_task.py", "from pathlib import Path\nPath('outputs/enveloped/from_run.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/enveloped/from_run.txt').write_text('run allowed\\n')\n")
    _write(tmp / "scripts/run_bad_task.py", "from pathlib import Path\nPath('outputs/enveloped/from_bad.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('outputs/enveloped/from_bad.txt').write_text('run bad\\n')\nPath('data/raw/secret.csv').parent.mkdir(parents=True, exist_ok=True)\nPath('data/raw/secret.csv').write_text('denied\\n')\n")
    _write(tmp / "checks/check_fixture_read_only.py", "from pathlib import Path\nassert Path('scripts/good.py').exists()\nprint('PASS: fixture read-only check')\n")
    _write(tmp / "checks/check_accept_allowed.py", "from pathlib import Path\nassert Path('outputs/envelope/allowed.txt').read_text() == 'allowed\\n'\nprint('PASS: allowed artifact')\n")
    _write(tmp / "checks/check_accept_fail.py", "raise SystemExit('intentional validation failure')\n")
    _write(tmp / "checks/check_mutate_then_pass.py", "from pathlib import Path\nPath('outputs/envelope/validator_target.txt').write_text('mutated\\n')\nprint('PASS: but mutation must invalidate acceptance')\n")
    _write(tmp / "checks/check_accept_transaction.py", "from pathlib import Path\nassert Path('outputs/envelope/tx_a.txt').is_file() and Path('outputs/envelope/tx_b.txt').is_file()\nprint('PASS: transaction inputs exist')\n")
    _write(tmp / "checks/check_env_good.py", "from pathlib import Path\nassert Path('outputs/enveloped/from_run.txt').exists()\nprint('PASS: env good output exists')\n")
    _write(tmp / "tasks/execution/T_ENV_GOOD.yml", f"""task_id: T_ENV_GOOD
stage: execution
gate: G4
goal: Run a deterministic envelope fixture.
inputs:
- scripts/run_good_task.py
allowed_outputs:
- outputs/enveloped/from_run.txt
checks:
- check_env_good.py
run:
  command:
  - {sys.executable}
  - scripts/run_good_task.py
  cwd: .
retry_policy:
  max_retries: 0
budget:
  max_agent_calls: 0
  max_dollars: 0.0
""")
    _write(tmp / "tasks/execution/T_ENV_BAD.yml", f"""task_id: T_ENV_BAD
stage: execution
gate: G4
goal: Try to write a denied path from a deterministic task.
inputs:
- scripts/run_bad_task.py
allowed_outputs:
- outputs/enveloped/from_bad.txt
checks:
- check_env_good.py
run:
  command:
  - {sys.executable}
  - scripts/run_bad_task.py
  cwd: .
retry_policy:
  max_retries: 0
budget:
  max_agent_calls: 0
  max_dollars: 0.0
""")
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
    good = execute_in_isolated_worktree(
        repo,
        [sys.executable, "scripts/good.py"],
        envelope,
        acceptance_checks=("checks/check_accept_allowed.py",),
    )
    if not good.ok:
        failures.append(f"allowed write was not accepted: {good}")
    if not (repo / "outputs/envelope/allowed.txt").exists():
        failures.append("allowed output was not copied back to main repo")
    if not good.worktree_removed:
        failures.append("good run worktree was not removed")
    if not good.validation_passed or good.failed_acceptance_checks:
        failures.append(f"allowed output was copied without a passing validator: {good}")
    if not good.validation_manifest or not (repo / good.validation_manifest).is_file():
        failures.append("passing acceptance did not persist a validation manifest")
    else:
        import json
        manifest = json.loads((repo / good.validation_manifest).read_text(encoding="utf-8"))
        if manifest.get("status") != "passed" or not manifest.get("acceptance_checks"):
            failures.append("durable validation manifest is incomplete")

    missing_check = execute_in_isolated_worktree(repo, [sys.executable, "scripts/good.py"], envelope)
    if missing_check.ok or missing_check.accepted_outputs:
        failures.append("write action without an acceptance check was accepted")

    extra_env = ExecutionEnvelope(
        write_roots=("outputs/envelope/",),
        expected_outputs=("outputs/envelope/expected.txt",),
    )
    extra = execute_in_isolated_worktree(
        repo,
        [sys.executable, "scripts/extra.py"],
        extra_env,
        acceptance_checks=("checks/check_accept_allowed.py",),
    )
    if extra.ok or "outputs/envelope/extra.txt" not in extra.unexpected_outputs:
        failures.append(f"extra file inside write root was not rejected: {extra}")
    if (repo / "outputs/envelope/expected.txt").exists() or (repo / "outputs/envelope/extra.txt").exists():
        failures.append("unexpected-output run polluted the main repo")

    failed_validation_env = ExecutionEnvelope(
        write_roots=("outputs/envelope/",),
        expected_outputs=("outputs/envelope/unvalidated.txt",),
    )
    failed_validation = execute_in_isolated_worktree(
        repo,
        [sys.executable, "scripts/fail_validation.py"],
        failed_validation_env,
        acceptance_checks=("checks/check_accept_fail.py",),
    )
    if failed_validation.ok or not failed_validation.failed_acceptance_checks:
        failures.append(f"failed acceptance check did not block copyback: {failed_validation}")
    if (repo / "outputs/envelope/unvalidated.txt").exists():
        failures.append("failed-validation run polluted the main repo")

    mutating_env = ExecutionEnvelope(
        write_roots=("outputs/envelope/",),
        expected_outputs=("outputs/envelope/validator_target.txt",),
    )
    mutating = execute_in_isolated_worktree(
        repo,
        [sys.executable, "scripts/validator_target.py"],
        mutating_env,
        acceptance_checks=("checks/check_mutate_then_pass.py",),
    )
    if mutating.ok or "outputs/envelope/validator_target.txt" not in mutating.validator_modified_outputs:
        failures.append(f"validator mutation was not rejected: {mutating}")
    if (repo / "outputs/envelope/validator_target.txt").exists():
        failures.append("validator mutation polluted the main repo")

    module_env = ExecutionEnvelope(
        write_roots=("outputs/envelope/",),
        expected_outputs=("outputs/envelope/module_target.txt",),
    )
    module_check = execute_in_isolated_worktree(
        repo,
        [sys.executable, "scripts/module_target.py"],
        module_env,
        acceptance_checks=("python3 -m compileall",),
    )
    if module_check.ok or not module_check.failed_acceptance_checks:
        failures.append("python -m acceptance command bypass was not rejected")
    if (repo / "outputs/envelope/module_target.txt").exists():
        failures.append("rejected module acceptance command polluted the main repo")

    transaction_env = ExecutionEnvelope(
        write_roots=("outputs/envelope/",),
        expected_outputs=("outputs/envelope/tx_a.txt", "outputs/envelope/tx_b.txt"),
    )
    real_replace = __import__("os").replace
    stage_replacements = {"count": 0}

    def fail_second_stage_replace(src, dst):
        if ".aeros-stage-" in Path(src).name:
            stage_replacements["count"] += 1
            if stage_replacements["count"] == 2:
                raise OSError("injected second-file copyback failure")
        return real_replace(src, dst)

    with patch("aeros.runtime.execution_envelope.os.replace", side_effect=fail_second_stage_replace):
        transaction = execute_in_isolated_worktree(
            repo,
            [sys.executable, "scripts/transaction.py"],
            transaction_env,
            acceptance_checks=("checks/check_accept_transaction.py",),
        )
    if transaction.ok or not transaction.copyback_error:
        failures.append(f"injected transactional copyback failure was not surfaced: {transaction}")
    if any((repo / rel).exists() for rel in ("outputs/envelope/tx_a.txt", "outputs/envelope/tx_b.txt")):
        failures.append("transactional copyback failure left a partial result in the main repo")

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

    next_spec = declared_action_spec(
        kind="cli_help_preview",
        effect_class="read_only",
        lane="harness",
        command=f"{sys.executable} -m aeros.cli --help",
        stop_condition="stop after emitting CLI help",
        capabilities=("read_project_state",),
    )
    next_result = execute_action_spec_in_isolated_worktree(repo, next_spec, timeout_seconds=30)
    if not next_result.ok:
        failures.append(f"real read-only ActionSpec did not pass under envelope: {next_result}")
    if next_result.observed_writes:
        failures.append(f"real read-only ActionSpec wrote files: {next_result.observed_writes}")

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

    env_run = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "run", "tasks/execution/T_ENV_GOOD.yml"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if env_run.returncode != 0:
        failures.append(f"aeros run deterministic envelope fixture failed: {env_run.stderr or env_run.stdout}")
    if not (repo / "outputs/enveloped/from_run.txt").exists():
        failures.append("aeros run did not copy declared deterministic task output back to main repo")

    denied_run = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "run", "tasks/execution/T_ENV_BAD.yml"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if denied_run.returncode == 0:
        failures.append("aeros run deterministic denied-write fixture unexpectedly passed")
    if (repo / "data/raw/secret.csv").exists() or (repo / "outputs/enveloped/from_bad.txt").exists():
        failures.append("aeros run deterministic denied-write fixture polluted the main repo")

    if failures:
        print("FAIL: ExecutionEnvelope problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: ExecutionEnvelope isolated-worktree enforcement is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
