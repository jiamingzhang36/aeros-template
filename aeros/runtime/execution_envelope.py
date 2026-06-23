"""Minimal ExecutionEnvelope with isolated git-worktree enforcement."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutionEnvelope:
    read_roots: tuple[str, ...] = (".",)
    write_roots: tuple[str, ...] = ()
    deny_roots: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    runtime_profile: str = "local-safe"

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_roots": list(self.read_roots),
            "write_roots": list(self.write_roots),
            "deny_roots": list(self.deny_roots),
            "expected_outputs": list(self.expected_outputs),
            "runtime_profile": self.runtime_profile,
        }


@dataclass(frozen=True)
class ExecutionEnvelopeResult:
    ok: bool
    return_code: int
    observed_writes: tuple[str, ...] = ()
    accepted_outputs: tuple[str, ...] = ()
    denied_writes: tuple[str, ...] = ()
    undeclared_writes: tuple[str, ...] = ()
    missing_expected_outputs: tuple[str, ...] = ()
    worktree_removed: bool = False
    message: str = ""


def envelope_from_dict(data: dict[str, Any] | None) -> ExecutionEnvelope:
    data = data or {}
    return ExecutionEnvelope(
        read_roots=tuple(str(x) for x in data.get("read_roots", ["."]) if str(x).strip()),
        write_roots=tuple(str(x) for x in data.get("write_roots", []) if str(x).strip()),
        deny_roots=tuple(str(x) for x in data.get("deny_roots", []) if str(x).strip()),
        expected_outputs=tuple(str(x) for x in data.get("expected_outputs", []) if str(x).strip()),
        runtime_profile=str(data.get("runtime_profile") or "local-safe"),
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30, check=False)


def _under(path: str, roots: tuple[str, ...]) -> bool:
    path = path.strip().lstrip("./")
    for root in roots:
        root = root.strip().lstrip("./")
        if not root:
            continue
        if root in {".", "*"}:
            return True
        if root.endswith("/") and path.startswith(root):
            return True
        if path == root or path.startswith(root + "/"):
            return True
    return False


def _status_paths(worktree: Path) -> tuple[str, ...]:
    result = _git(worktree, "status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        path = path.strip('"').lstrip("./")
        if path:
            paths.append(path)
    return tuple(sorted(dict.fromkeys(paths)))


def _copy_back(worktree: Path, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    accepted: list[str] = []
    for rel in paths:
        src = worktree / rel
        dst = root / rel
        if not src.exists() or src.is_dir():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        accepted.append(rel)
    return tuple(accepted)


def execute_in_isolated_worktree(
    root: Path,
    argv: list[str],
    envelope: ExecutionEnvelope,
    *,
    timeout_seconds: int = 30,
) -> ExecutionEnvelopeResult:
    root = root.resolve()
    if not (root / ".git").exists():
        return ExecutionEnvelopeResult(False, 1, message="root is not a git repository")
    if not envelope.write_roots:
        return ExecutionEnvelopeResult(False, 1, message="envelope declares no write_roots")

    with tempfile.TemporaryDirectory(prefix="aeros_envelope_") as tmp_name:
        worktree = Path(tmp_name) / "worktree"
        add = _git(root, "worktree", "add", "--detach", str(worktree), "HEAD")
        if add.returncode != 0:
            return ExecutionEnvelopeResult(False, add.returncode, message=add.stderr.strip() or add.stdout.strip())
        return_code = 1
        observed: tuple[str, ...] = ()
        accepted: tuple[str, ...] = ()
        denied: tuple[str, ...] = ()
        undeclared: tuple[str, ...] = ()
        missing: tuple[str, ...] = ()
        message = ""
        cleanup_ok = False
        try:
            proc = subprocess.run(argv, cwd=worktree, text=True, capture_output=True, timeout=timeout_seconds, check=False)
            return_code = proc.returncode
            observed = _status_paths(worktree)
            denied = tuple(path for path in observed if _under(path, envelope.deny_roots))
            undeclared = tuple(path for path in observed if not _under(path, envelope.write_roots) and path not in denied)
            missing = tuple(rel for rel in envelope.expected_outputs if not (worktree / rel).exists())
            if return_code != 0:
                message = "command failed"
            elif denied:
                message = "denied writes observed"
            elif undeclared:
                message = "undeclared writes observed"
            elif missing:
                message = "expected outputs missing"
            else:
                accepted = _copy_back(worktree, root, observed)
                message = "accepted declared writes"
        except subprocess.TimeoutExpired:
            return_code = 124
            observed = _status_paths(worktree)
            message = "command timed out"
        finally:
            remove = _git(root, "worktree", "remove", "--force", str(worktree))
            cleanup_ok = remove.returncode == 0 and not worktree.exists()
    ok = return_code == 0 and not denied and not undeclared and not missing
    return ExecutionEnvelopeResult(
        ok=ok,
        return_code=return_code,
        observed_writes=observed,
        accepted_outputs=accepted,
        denied_writes=denied,
        undeclared_writes=undeclared,
        missing_expected_outputs=missing,
        worktree_removed=cleanup_ok,
        message=message,
    )
