#!/usr/bin/env python3
"""Exercise observed-write dry-run audit."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.write_audit import audit_writes, format_write_audit  # noqa: E402


def _run(cwd: Path, args: list[str]) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aeros_write_audit_"))
    _run(tmp, ["git", "init"])
    _run(tmp, ["git", "config", "user.email", "aeros@example.test"])
    _run(tmp, ["git", "config", "user.name", "aeros-test"])
    _write(tmp / "README.md", "fixture\n")
    _write(tmp / "harness/protected_path_commit_policy.yml", """version: '0.1'
protected_paths:
  exact:
    - evidence/claim_registry.md
  prefixes:
    - data/raw/
""")
    _write(tmp / "SESSION_CONTRACT.yml", """version: '0.1'
active: true
allowed_prefixes:
  - outputs/allowed/
""")
    _run(tmp, ["git", "add", "."])
    _run(tmp, ["git", "commit", "-m", "fixture"])
    return tmp


def main() -> int:
    failures: list[str] = []
    repo = _repo()
    try:
        _write(repo / "outputs/allowed/a.txt", "allowed\n")
        _write(repo / "misc/side.txt", "side\n")
        _write(repo / "data/raw/secret.csv", "protected\n")
        report = audit_writes(repo, since="HEAD")
        rendered = format_write_audit(report)
        if report.status != "FAIL":
            failures.append(f"expected protected write failure, got {report.status}")
        if "outputs/allowed/a.txt" not in report.observed_writes:
            failures.append("allowed write missing from observed_writes")
        if "data/raw/secret.csv" not in report.protected_writes:
            failures.append(f"protected write missing: {report.protected_writes}")
        if "misc/side.txt" not in report.undeclared_writes:
            failures.append(f"undeclared write missing: {report.undeclared_writes}")
        if "AEROS Writes Audit" not in rendered or "Does Not Prove" not in rendered:
            failures.append("rendered audit missing required markers")

        clean = _repo()
        clean_report = audit_writes(clean, since="HEAD")
        if clean_report.status != "NO_WRITES":
            failures.append(f"clean repo should have NO_WRITES, got {clean_report.status}")

        declared = _repo()
        _write(declared / "outputs/manual/a.txt", "manual\n")
        declared_report = audit_writes(declared, since="HEAD", declared_writes=["outputs/manual/"])
        if declared_report.status != "PASS":
            failures.append(f"declared write should pass, got {declared_report.status}: {declared_report.to_dict()}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: writes audit is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
