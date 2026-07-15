"""Minimal ExecutionEnvelope with isolated git-worktree enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutionEnvelope:
    read_roots: tuple[str, ...] = (".",)
    write_roots: tuple[str, ...] = ()
    deny_roots: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    allowed_sidecars: tuple[str, ...] = ()
    validation_manifest: str = ""
    runtime_profile: str = "local-safe"

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_roots": list(self.read_roots),
            "write_roots": list(self.write_roots),
            "deny_roots": list(self.deny_roots),
            "expected_outputs": list(self.expected_outputs),
            "allowed_sidecars": list(self.allowed_sidecars),
            "validation_manifest": self.validation_manifest,
            "runtime_profile": self.runtime_profile,
        }


@dataclass(frozen=True)
class AcceptanceCheckResult:
    command: str
    return_code: int
    stdout_tail: str = ""
    stderr_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "return_code": self.return_code,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }


@dataclass(frozen=True)
class ExecutionEnvelopeResult:
    ok: bool
    return_code: int
    observed_writes: tuple[str, ...] = ()
    accepted_outputs: tuple[str, ...] = ()
    denied_writes: tuple[str, ...] = ()
    undeclared_writes: tuple[str, ...] = ()
    unexpected_outputs: tuple[str, ...] = ()
    missing_expected_outputs: tuple[str, ...] = ()
    unproduced_expected_outputs: tuple[str, ...] = ()
    acceptance_checks: tuple[AcceptanceCheckResult, ...] = ()
    failed_acceptance_checks: tuple[str, ...] = ()
    validator_modified_outputs: tuple[str, ...] = ()
    validation_passed: bool = False
    validation_manifest: str = ""
    copyback_error: str = ""
    worktree_removed: bool = False
    message: str = ""
    run_id: str = ""
    run_bundle_manifest: str = ""
    cache_hit: bool = False


def envelope_from_dict(data: dict[str, Any] | None) -> ExecutionEnvelope:
    data = data or {}
    return ExecutionEnvelope(
        read_roots=tuple(str(x) for x in data.get("read_roots", ["."]) if str(x).strip()),
        write_roots=tuple(str(x) for x in data.get("write_roots", []) if str(x).strip()),
        deny_roots=tuple(str(x) for x in data.get("deny_roots", []) if str(x).strip()),
        expected_outputs=tuple(str(x) for x in data.get("expected_outputs", []) if str(x).strip()),
        allowed_sidecars=tuple(str(x) for x in data.get("allowed_sidecars", []) if str(x).strip()),
        validation_manifest=str(data.get("validation_manifest") or "").strip(),
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


def _copy_back_transactional(worktree: Path, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Stage every file first, then replace destinations with rollback on error."""
    entries: list[dict[str, Any]] = []
    try:
        for rel in paths:
            src = worktree / rel
            dst = root / rel
            if not src.is_file():
                raise OSError(f"copyback source is not a file: {rel}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            stage_fd, stage_name = tempfile.mkstemp(prefix=f".{dst.name}.aeros-stage-", dir=dst.parent)
            os.close(stage_fd)
            stage = Path(stage_name)
            shutil.copy2(src, stage)
            entries.append({
                "rel": rel,
                "dst": dst,
                "stage": stage,
                "backup": None,
                "original_moved": False,
                "new_installed": False,
            })
        for entry in entries:
            dst = entry["dst"]
            if dst.exists():
                backup_fd, backup_name = tempfile.mkstemp(prefix=f".{dst.name}.aeros-backup-", dir=dst.parent)
                os.close(backup_fd)
                backup = Path(backup_name)
                os.replace(dst, backup)
                entry["backup"] = backup
                entry["original_moved"] = True
            os.replace(entry["stage"], dst)
            entry["new_installed"] = True
    except Exception as exc:
        rollback_failures: list[str] = []
        for entry in reversed(entries):
            try:
                dst = entry["dst"]
                if entry["new_installed"] and dst.exists():
                    dst.unlink()
                backup = entry["backup"]
                if entry["original_moved"] and backup is not None and backup.exists():
                    os.replace(backup, dst)
            except OSError as rollback_exc:
                rollback_failures.append(str(rollback_exc))
        detail = f"transactional copyback failed: {exc}"
        if rollback_failures:
            detail += "; rollback failures: " + "; ".join(rollback_failures)
        raise OSError(detail) from exc
    finally:
        for entry in entries:
            for key in ("stage", "backup"):
                path = entry.get(key)
                if isinstance(path, Path) and path.exists():
                    path.unlink()
    return tuple(str(entry["rel"]) for entry in entries)


def _matches_output(path: str, declarations: tuple[str, ...]) -> bool:
    normalized = path.strip().lstrip("./")
    for declaration in declarations:
        declared = declaration.strip().lstrip("./")
        if not declared:
            continue
        if declared.endswith("/"):
            if normalized.startswith(declared):
                return True
        elif normalized == declared:
            return True
    return False


def _declared_output_exists(worktree: Path, declaration: str) -> bool:
    path = worktree / declaration.strip().lstrip("./")
    if declaration.strip().endswith("/"):
        return path.is_dir() and any(candidate.is_file() for candidate in path.rglob("*"))
    return path.is_file()


def _default_validation_manifest(expected_outputs: tuple[str, ...]) -> str:
    if not expected_outputs:
        return ""
    first = Path(expected_outputs[0].rstrip("/"))
    parent = first.parent
    stem = first.stem or "outputs"
    return (parent / f"{stem}_validation.json").as_posix()


def _safe_project_relative(path: str) -> bool:
    candidate = Path(path)
    return bool(path.strip()) and not candidate.is_absolute() and ".." not in candidate.parts


def _snapshot_declared_files(worktree: Path, declarations: tuple[str, ...]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in _status_paths(worktree):
        if not _matches_output(path, declarations):
            continue
        candidate = worktree / path
        if candidate.is_file():
            snapshot[path] = sha256(candidate.read_bytes()).hexdigest()
    return snapshot


def _acceptance_argv(worktree: Path, command: str) -> list[str]:
    if any(token in command for token in ["|", "&&", "||", ";", ">", "<", "$("]):
        raise ValueError("acceptance check is not safe argv")
    parts = shlex.split(command)
    if not parts:
        raise ValueError("acceptance check is empty")
    if parts[0].endswith(".py"):
        candidate = Path(parts[0])
        if len(candidate.parts) == 1 and (worktree / "checks" / candidate).is_file():
            parts[0] = f"checks/{parts[0]}"
        script = (worktree / parts[0]).resolve()
        try:
            script.relative_to((worktree / "checks").resolve())
        except ValueError as exc:
            raise ValueError("acceptance check must be a committed checks/*.py script") from exc
        if not script.is_file():
            raise ValueError(f"acceptance check script is missing: {parts[0]}")
        return [sys.executable, *parts]
    if parts[0] in {"python", "python3", sys.executable} and len(parts) >= 2:
        if not parts[1].endswith(".py"):
            raise ValueError("acceptance check must invoke a checks/*.py script, not a module or executable")
        script = (worktree / parts[1]).resolve()
        try:
            script.relative_to((worktree / "checks").resolve())
        except ValueError as exc:
            raise ValueError("acceptance check must be a committed checks/*.py script") from exc
        if not script.is_file():
            raise ValueError(f"acceptance check script is missing: {parts[1]}")
        return [sys.executable, *parts[1:]]
    raise ValueError("acceptance check must be a Python check script")


def _run_acceptance_checks(
    worktree: Path,
    checks: tuple[str, ...],
    *,
    env: dict[str, str],
    timeout_seconds: int,
) -> tuple[AcceptanceCheckResult, ...]:
    results: list[AcceptanceCheckResult] = []
    for command in checks:
        try:
            argv = _acceptance_argv(worktree, command)
            proc = subprocess.run(
                argv,
                cwd=worktree,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
                env=env,
            )
            results.append(AcceptanceCheckResult(
                command=command,
                return_code=proc.returncode,
                stdout_tail=proc.stdout[-4000:],
                stderr_tail=proc.stderr[-4000:],
            ))
        except subprocess.TimeoutExpired as exc:
            results.append(AcceptanceCheckResult(
                command=command,
                return_code=124,
                stdout_tail=str(exc.stdout or "")[-4000:],
                stderr_tail=str(exc.stderr or "")[-4000:],
            ))
        except (OSError, ValueError) as exc:
            results.append(AcceptanceCheckResult(command=command, return_code=126, stderr_tail=str(exc)))
    return tuple(results)


def execute_in_isolated_worktree(
    root: Path,
    argv: list[str],
    envelope: ExecutionEnvelope,
    *,
    timeout_seconds: int = 30,
    cwd_rel: str = ".",
    acceptance_checks: tuple[str, ...] = (),
) -> ExecutionEnvelopeResult:
    root = root.resolve()
    if not (root / ".git").exists():
        return ExecutionEnvelopeResult(False, 1, message="root is not a git repository")
    if not envelope.write_roots and envelope.expected_outputs:
        return ExecutionEnvelopeResult(False, 1, message="read-only envelope must not declare expected outputs")
    validation_manifest = envelope.validation_manifest or _default_validation_manifest(envelope.expected_outputs)
    if validation_manifest and not _safe_project_relative(validation_manifest):
        return ExecutionEnvelopeResult(False, 1, message="validation manifest must be project-relative")
    if validation_manifest and _under(validation_manifest, envelope.deny_roots):
        return ExecutionEnvelopeResult(False, 1, message="validation manifest must not target a denied path")

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
        unexpected: tuple[str, ...] = ()
        missing: tuple[str, ...] = ()
        unproduced: tuple[str, ...] = ()
        check_results: tuple[AcceptanceCheckResult, ...] = ()
        failed_checks: tuple[str, ...] = ()
        validator_modified: tuple[str, ...] = ()
        validation_passed = False
        copyback_error = ""
        message = ""
        cleanup_ok = False
        try:
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            run_cwd = (worktree / cwd_rel).resolve()
            try:
                run_cwd.relative_to(worktree.resolve())
            except ValueError:
                return ExecutionEnvelopeResult(False, 1, message=f"run cwd escapes worktree: {cwd_rel}")
            proc = subprocess.run(argv, cwd=run_cwd, text=True, capture_output=True, timeout=timeout_seconds, check=False, env=env)
            return_code = proc.returncode
            observed = _status_paths(worktree)
            denied = tuple(path for path in observed if _under(path, envelope.deny_roots))
            undeclared = tuple(path for path in observed if not _under(path, envelope.write_roots) and path not in denied)
            artifact_outputs = (*envelope.expected_outputs, *envelope.allowed_sidecars)
            declared_outputs = (*artifact_outputs, *((validation_manifest,) if validation_manifest else ()))
            unexpected = tuple(
                path for path in observed
                if path not in denied and path not in undeclared and not _matches_output(path, declared_outputs)
            )
            missing = tuple(rel for rel in envelope.expected_outputs if not _declared_output_exists(worktree, rel))
            unproduced = tuple(
                rel for rel in envelope.expected_outputs
                if not any(_matches_output(path, (rel,)) for path in observed)
            )
            if return_code != 0:
                message = "command failed"
            elif denied:
                message = "denied writes observed"
            elif undeclared:
                message = "undeclared writes observed"
            elif unexpected:
                message = "unexpected outputs observed"
            elif missing:
                message = "expected outputs missing"
            elif unproduced:
                message = "expected outputs were not produced by this action"
            elif envelope.expected_outputs and not acceptance_checks:
                failed_checks = ("missing declared acceptance check",)
                message = "acceptance checks required before output copyback"
            else:
                before_validation = _snapshot_declared_files(worktree, artifact_outputs)
                check_results = _run_acceptance_checks(
                    worktree,
                    acceptance_checks,
                    env=env,
                    timeout_seconds=timeout_seconds,
                )
                failed_checks = tuple(result.command for result in check_results if result.return_code != 0)
                after_validation = _snapshot_declared_files(worktree, artifact_outputs)
                validator_modified = tuple(sorted(
                    path for path in set(before_validation) | set(after_validation)
                    if before_validation.get(path) != after_validation.get(path)
                ))
                observed = _status_paths(worktree)
                denied = tuple(path for path in observed if _under(path, envelope.deny_roots))
                undeclared = tuple(path for path in observed if not _under(path, envelope.write_roots) and path not in denied)
                unexpected = tuple(
                    path for path in observed
                    if path not in denied and path not in undeclared and not _matches_output(path, declared_outputs)
                )
                missing = tuple(rel for rel in envelope.expected_outputs if not _declared_output_exists(worktree, rel))
                unproduced = tuple(
                    rel for rel in envelope.expected_outputs
                    if not any(_matches_output(path, (rel,)) for path in observed)
                )
                if failed_checks:
                    message = "acceptance checks failed"
                elif validator_modified:
                    message = "acceptance checks modified candidate outputs"
                elif denied:
                    message = "acceptance checks produced denied writes"
                elif undeclared:
                    message = "acceptance checks produced undeclared writes"
                elif unexpected:
                    message = "acceptance checks produced unexpected outputs"
                elif missing or unproduced:
                    message = "acceptance checks did not preserve expected outputs"
                else:
                    validation_passed = True
                    if validation_manifest:
                        manifest_path = worktree / validation_manifest
                        manifest_path.parent.mkdir(parents=True, exist_ok=True)
                        manifest_payload = {
                            "version": 1,
                            "status": "passed",
                            "runtime_profile": envelope.runtime_profile,
                            "return_code": return_code,
                            "expected_outputs": [
                                {"path": path, "sha256": digest}
                                for path, digest in sorted(after_validation.items())
                            ],
                            "observed_writes": list(observed),
                            "acceptance_checks": [item.to_dict() for item in check_results],
                            "validator_modified_outputs": [],
                            "does_not_prove": [
                                "scientific validity",
                                "result admission",
                                "claim support",
                                "gate, submission, or release approval",
                            ],
                        }
                        manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
                    observed = _status_paths(worktree)
                    denied = tuple(path for path in observed if _under(path, envelope.deny_roots))
                    undeclared = tuple(
                        path for path in observed
                        if not _under(path, envelope.write_roots)
                        and path not in denied
                        and path != validation_manifest
                    )
                    unexpected = tuple(
                        path for path in observed
                        if path not in denied and path not in undeclared and not _matches_output(path, declared_outputs)
                    )
                    if denied or undeclared or unexpected:
                        validation_passed = False
                        message = "validation manifest violated declared write boundaries"
                    else:
                        copy_paths = tuple(path for path in observed if _matches_output(path, declared_outputs))
                        try:
                            copied = _copy_back_transactional(worktree, root, copy_paths) if envelope.write_roots else ()
                            accepted = tuple(path for path in copied if path != validation_manifest)
                            message = "accepted exact validated outputs" if envelope.write_roots else "read-only action completed"
                        except OSError as exc:
                            copyback_error = str(exc)
                            validation_passed = False
                            accepted = ()
                            message = "transactional copyback failed"
        except subprocess.TimeoutExpired:
            return_code = 124
            observed = _status_paths(worktree)
            message = "command timed out"
        finally:
            remove = _git(root, "worktree", "remove", "--force", str(worktree))
            cleanup_ok = remove.returncode == 0 and not worktree.exists()
    ok = (
        return_code == 0
        and not denied
        and not undeclared
        and not unexpected
        and not missing
        and not unproduced
        and not failed_checks
        and not validator_modified
        and validation_passed
        and not copyback_error
    )
    return ExecutionEnvelopeResult(
        ok=ok,
        return_code=return_code,
        observed_writes=observed,
        accepted_outputs=accepted,
        denied_writes=denied,
        undeclared_writes=undeclared,
        unexpected_outputs=unexpected,
        missing_expected_outputs=missing,
        unproduced_expected_outputs=unproduced,
        acceptance_checks=check_results,
        failed_acceptance_checks=failed_checks,
        validator_modified_outputs=validator_modified,
        validation_passed=validation_passed,
        validation_manifest=validation_manifest if validation_passed else "",
        copyback_error=copyback_error,
        worktree_removed=cleanup_ok,
        message=message,
    )


def default_envelope_for_action_spec(spec: Any) -> ExecutionEnvelope:
    data = spec.to_dict() if hasattr(spec, "to_dict") else dict(spec)
    if data.get("execution_envelope"):
        return envelope_from_dict(data.get("execution_envelope"))
    effect = str(data.get("effect_class", "")).strip()
    expected = tuple(str(x) for x in data.get("expected_outputs") or [] if str(x).strip())
    deny = (
        "paper/",
        "evidence/claim_registry.md",
        "decisions/approvals/",
        "data/raw/",
        "aeros/state/",
    )
    if effect == "read_only":
        return ExecutionEnvelope(read_roots=(".",), write_roots=(), deny_roots=deny, expected_outputs=())
    if effect in {"local_write", "local_write_preview"}:
        write_roots = tuple(sorted({path if path.endswith("/") else str(Path(path).parent) + "/" for path in expected if path}))
        return ExecutionEnvelope(read_roots=(".",), write_roots=write_roots, deny_roots=deny, expected_outputs=expected)
    return ExecutionEnvelope(read_roots=(".",), write_roots=(), deny_roots=deny, expected_outputs=())


def execute_action_spec_in_isolated_worktree(
    root: Path,
    spec: Any,
    *,
    timeout_seconds: int = 30,
) -> ExecutionEnvelopeResult:
    data = spec.to_dict() if hasattr(spec, "to_dict") else dict(spec)
    effect = str(data.get("effect_class", "")).strip()
    if effect not in {"read_only", "local_write", "local_write_preview"}:
        return ExecutionEnvelopeResult(False, 1, message=f"unsupported envelope effect_class: {effect}")
    command = str(data.get("command", "")).strip()
    if not command:
        return ExecutionEnvelopeResult(False, 1, message="ActionSpec has no command")
    if any(token in command for token in ["|", "&&", "||", ";", ">", "<", "$("]):
        return ExecutionEnvelopeResult(False, 1, message="ActionSpec command is not envelope-safe argv")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return ExecutionEnvelopeResult(False, 1, message=f"cannot parse ActionSpec command: {exc}")
    envelope = default_envelope_for_action_spec(data)
    checks = tuple(str(item) for item in data.get("acceptance_checks") or [] if str(item).strip())
    return execute_in_isolated_worktree(
        root,
        argv,
        envelope,
        timeout_seconds=timeout_seconds,
        acceptance_checks=checks,
    )
