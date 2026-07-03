#!/usr/bin/env python3
"""Exercise the protected-path pre-commit hook in temporary git repos."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "tools/hooks/pre-commit-aeros-protected-paths"
POLICY = ROOT / "harness/protected_path_commit_policy.yml"


def run(cmd: list[str], cwd: Path, *, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=merged_env, timeout=30)


def make_repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aeros-hook-fixture-"))
    init = run(["git", "init"], tmp)
    if init.returncode != 0:
        raise RuntimeError(init.stderr or init.stdout)
    return tmp


def stage(repo: Path, rel: str, body: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    added = run(["git", "add", rel], repo)
    if added.returncode != 0:
        raise RuntimeError(added.stderr or added.stdout)


def hook(repo: Path, *, override: bool = False) -> subprocess.CompletedProcess[str]:
    env = {"AEROS_ALLOW_PROTECTED_COMMIT": "1"} if override else None
    return run([sys.executable, str(HOOK)], repo, env=env)


def main() -> int:
    failures: list[str] = []
    if not HOOK.exists():
        failures.append("missing tools/hooks/pre-commit-aeros-protected-paths")
    else:
        text = HOOK.read_text(encoding="utf-8")
        if "AEROS-PROTECTED-PATH-HOOK-001" not in text:
            failures.append("hook missing AEROS marker")
        if "AEROS_ALLOW_PROTECTED_COMMIT" not in text:
            failures.append("hook missing explicit human override env var")
    if not POLICY.exists():
        failures.append("missing harness/protected_path_commit_policy.yml")

    if not failures:
        repo = make_repo()
        stage(repo, "notes/free.txt", "ok\n")
        proc = hook(repo)
        if proc.returncode != 0:
            failures.append(f"non-protected staged file was blocked: {proc.stderr or proc.stdout}")

        repo = make_repo()
        stage(repo, "evidence/claim_registry.md", "# claim\n")
        proc = hook(repo)
        if proc.returncode == 0:
            failures.append("protected claim registry edit was not blocked")
        if "AEROS_ALLOW_PROTECTED_COMMIT=1" not in (proc.stderr + proc.stdout):
            failures.append("blocked hook output did not explain the human override")

        repo = make_repo()
        stage(repo, "evidence/claim_registry.md", "# claim\n")
        proc = hook(repo, override=True)
        if proc.returncode != 0:
            failures.append(f"human override did not allow protected commit: {proc.stderr or proc.stdout}")

        repo = make_repo()
        stage(repo, "data/raw/source.csv", "x\n")
        proc = hook(repo)
        if proc.returncode == 0:
            failures.append("protected data/raw edit was not blocked")

    if failures:
        print("FAIL: protected-path hook check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: protected-path pre-commit hook blocks protected staged files by default")
    return 0


if __name__ == "__main__":
    sys.exit(main())

