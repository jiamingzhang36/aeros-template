"""Single-flight, content-addressed execution for expensive project jobs.

Heavy jobs are declared in ``.aeros/heavy_jobs.yml``. The runtime hashes only
declared scripts, manifests, environment locks, and cheap stat-only inputs. It
never recursively inventories a large data directory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
from typing import Any

import yaml


HEAVY_RUN_VERSION = 1


@dataclass(frozen=True)
class HeavyRunResult:
    ok: bool
    status: str
    job_id: str
    run_key: str
    message: str
    command: tuple[str, ...] = ()
    pid: int | None = None
    log_path: str = ""
    accepted_manifest: str = ""
    resume_pack: str = ""
    attempts: int = 0
    expected_outputs: tuple[str, ...] = ()
    does_not_prove: tuple[str, ...] = (
        "scientific validity",
        "claim or release authority",
        "that undeclared inputs are unchanged",
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(payload: Any) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def find_heavy_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".aeros" / "heavy_jobs.yml").is_file():
            return candidate
    raise FileNotFoundError(
        "no .aeros/heavy_jobs.yml found in this directory or its parents"
    )


def _load(root: Path) -> dict[str, Any]:
    path = root / ".aeros" / "heavy_jobs.yml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if int(payload.get("version", 0)) != HEAVY_RUN_VERSION:
        raise ValueError(f"unsupported heavy job schema in {path}")
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        raise ValueError(f"{path} must declare at least one job")
    return payload


def list_heavy_jobs(root: Path) -> list[str]:
    return sorted(str(item) for item in _load(root)["jobs"])


def _resolve(root: Path, value: str) -> Path:
    expanded = Path(os.path.expandvars(value)).expanduser()
    return expanded.resolve() if expanded.is_absolute() else (root / expanded).resolve()


def _runtime_roots(root: Path, job: dict[str, Any]) -> dict[str, Any]:
    working_root = _resolve(root, str(job.get("working_root", ".")))
    artifact_root = _resolve(root, str(job.get("artifact_root", ".")))
    fallback_value = ""
    fallback_env = str(job.get("fallback_root_env", "")).strip()
    if fallback_env:
        fallback_value = os.environ.get(fallback_env, "").strip()
    if not fallback_value:
        fallback_value = str(job.get("fallback_root", "")).strip()
    fallback_root = _resolve(root, fallback_value) if fallback_value else None
    required_mounts = [
        _resolve(root, str(item)) for item in job.get("required_mounts", [])
    ]
    return {
        "working_root": working_root,
        "artifact_root": artifact_root,
        "fallback_root": fallback_root,
        "required_mounts": required_mounts,
    }


def _input_path(root: Path, value: str, fallback_root: Path | None) -> Path:
    candidate = _resolve(root, value)
    if candidate.exists() or Path(value).is_absolute() or fallback_root is None:
        return candidate
    return (fallback_root / value).resolve()


def _relative_or_absolute(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _file_records(
    root: Path,
    values: list[str],
    *,
    content: bool,
    fallback_root: Path | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for value in values:
        path = _input_path(root, str(value), fallback_root)
        if not path.exists():
            raise FileNotFoundError(
                f"declared heavy-job input is unavailable locally and at its "
                f"fallback root: {value}"
            )
        stat = path.stat()
        record: dict[str, Any] = {
            "path": _relative_or_absolute(root, path),
            "kind": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
        if content:
            if not path.is_file():
                raise ValueError(
                    f"content-hashed input must be a file, not a directory: {value}"
                )
            record["sha256"] = _sha256(path)
        records.append(record)
    return records


def _globbed_files(root: Path, patterns: list[str]) -> list[str]:
    files: set[str] = set()
    for pattern in patterns:
        if Path(pattern).is_absolute():
            raise ValueError(f"hash_globs must be project-relative: {pattern}")
        for path in root.glob(pattern):
            if path.is_file():
                files.add(path.relative_to(root).as_posix())
    return sorted(files)


def _command(job: dict[str, Any]) -> tuple[str, ...]:
    raw = job.get("command")
    if isinstance(raw, str):
        parts = tuple(shlex.split(raw))
    elif isinstance(raw, list):
        parts = tuple(str(item) for item in raw)
    else:
        parts = ()
    if not parts:
        raise ValueError("heavy job command must be a nonempty string or list")
    return parts


def _job(root: Path, job_id: str) -> dict[str, Any]:
    job = _load(root)["jobs"].get(job_id)
    if not isinstance(job, dict):
        known = ", ".join(list_heavy_jobs(root))
        raise KeyError(f"unknown heavy job {job_id!r}; known jobs: {known}")
    return job


def _identity(root: Path, job_id: str, job: dict[str, Any]) -> dict[str, Any]:
    command = _command(job)
    roots = _runtime_roots(root, job)
    missing_mounts = [
        path.as_posix()
        for path in roots["required_mounts"]
        if not path.exists()
    ]
    if missing_mounts:
        raise FileNotFoundError(
            "required external root is not mounted: " + ", ".join(missing_mounts)
        )
    if not roots["working_root"].is_dir():
        raise FileNotFoundError(
            f"heavy-job working root is unavailable: {roots['working_root']}"
        )
    if not roots["artifact_root"].is_dir():
        raise FileNotFoundError(
            f"heavy-job artifact root is unavailable: {roots['artifact_root']}"
        )
    executable = shutil.which(command[0]) or command[0]
    executable_path = (
        Path(executable).resolve() if Path(executable).exists() else Path(executable)
    )
    executable_record: dict[str, Any] = {"path": executable_path.as_posix()}
    if executable_path.exists():
        stat = executable_path.stat()
        executable_record.update({"size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return {
        "version": HEAVY_RUN_VERSION,
        "job_id": job_id,
        "command": list(command),
        "cost_class": str(job.get("cost_class", "heavy")),
        "working_root": _relative_or_absolute(root, roots["working_root"]),
        "artifact_root": _relative_or_absolute(root, roots["artifact_root"]),
        "fallback_root": (
            _relative_or_absolute(root, roots["fallback_root"])
            if roots["fallback_root"] is not None
            else ""
        ),
        "required_mounts": [
            _relative_or_absolute(root, path) for path in roots["required_mounts"]
        ],
        "executable": executable_record,
        "hash_inputs": _file_records(
            root,
            [
                *[str(item) for item in job.get("hash_inputs", [])],
                *_globbed_files(
                    root, [str(item) for item in job.get("hash_globs", [])]
                ),
            ],
            content=True,
            fallback_root=roots["fallback_root"],
        ),
        "stat_inputs": _file_records(
            root,
            [str(item) for item in job.get("stat_inputs", [])],
            content=False,
            fallback_root=roots["fallback_root"],
        ),
        "environment_locks": _file_records(
            root,
            [str(item) for item in job.get("environment_locks", [])],
            content=True,
            fallback_root=roots["fallback_root"],
        ),
        "expected_outputs": [
            str(item) for item in job.get("expected_outputs", [])
        ],
    }


def _paths(root: Path, job_id: str, run_key: str) -> dict[str, Path]:
    base = root / ".aeros" / "heavy_runs" / job_id
    return {
        "lease": base / "leases" / f"{run_key}.json",
        "accepted": base / "accepted" / f"{run_key}.json",
        "failures": base / "failures" / f"{run_key}.jsonl",
        "log": base / "logs" / f"{run_key}.log",
        "resume": base / "RESUME.json",
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _active_lease(path: Path) -> dict[str, Any]:
    lease = _read_json(path)
    if (
        lease
        and lease.get("host") == socket.gethostname()
        and _pid_alive(int(lease.get("pid", 0)))
    ):
        return lease
    return {}


def _acquire_lease(
    path: Path, payload: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            active = _active_lease(path)
            if active:
                return False, active
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True, payload
    return False, _read_json(path)


def _output_records(
    root: Path, artifact_root: Path, expected: list[str]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in expected:
        path = _resolve(artifact_root, relative)
        try:
            path.relative_to(artifact_root)
        except ValueError as exc:
            raise ValueError(
                f"heavy-job output escapes declared artifact root: {relative}"
            ) from exc
        recorded_path = _relative_or_absolute(root, path)
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(
                f"expected heavy-job output is missing or empty: {recorded_path}"
            )
        records.append(
            {
                "path": recorded_path,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return records


def _validate_accepted(
    root: Path, manifest_path: Path, run_key: str
) -> tuple[bool, str]:
    manifest = _read_json(manifest_path)
    if (
        not manifest
        or manifest.get("run_key") != run_key
        or manifest.get("status") != "accepted"
    ):
        return False, "accepted manifest identity/status mismatch"
    for record in manifest.get("outputs", []):
        recorded = Path(str(record.get("path", "")))
        path = recorded if recorded.is_absolute() else root / recorded
        if (
            not path.is_file()
            or path.stat().st_size != record.get("bytes")
            or _sha256(path) != record.get("sha256")
        ):
            return (
                False,
                f"accepted output changed or disappeared: {record.get('path', '')}",
            )
    return True, "validated accepted outputs without execution"


def _failure_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _max_attempts(job: dict[str, Any]) -> int:
    if "max_attempts" in job:
        return max(1, int(job["max_attempts"]))
    return {"cheap": 3, "medium": 2, "heavy": 1, "very_heavy": 1}.get(
        str(job.get("cost_class", "heavy")), 1
    )


def _write_resume(
    path: Path, result: HeavyRunResult, *, next_action: str
) -> None:
    _atomic_json(
        path,
        {
            "version": HEAVY_RUN_VERSION,
            "updated_at": _now(),
            "job_id": result.job_id,
            "run_key": result.run_key,
            "status": result.status,
            "message": result.message,
            "log_path": result.log_path,
            "accepted_manifest": result.accepted_manifest,
            "attempts": result.attempts,
            "expected_outputs": list(result.expected_outputs),
            "do_not_repeat": (
                "Do not launch the command directly or create a second "
                "process for this RunKey."
            ),
            "next_allowed_action": next_action,
        },
    )


def inspect_heavy_job(root: Path, job_id: str) -> HeavyRunResult:
    root = root.resolve()
    job = _job(root, job_id)
    try:
        identity = _identity(root, job_id, job)
    except FileNotFoundError as exc:
        return HeavyRunResult(
            False,
            "BLOCKED_EXTERNAL_INPUT",
            job_id,
            "",
            str(exc),
            command=_command(job),
            resume_pack=(
                root / ".aeros" / "heavy_runs" / job_id / "RESUME.json"
            ).relative_to(root).as_posix(),
            expected_outputs=tuple(
                str(item) for item in job.get("expected_outputs", [])
            ),
        )
    run_key = "HR-" + _json_hash(identity)[:24]
    paths = _paths(root, job_id, run_key)
    expected = tuple(str(item) for item in job.get("expected_outputs", []))
    common = {
        "job_id": job_id,
        "run_key": run_key,
        "command": _command(job),
        "log_path": _relative_or_absolute(root, paths["log"]),
        "accepted_manifest": _relative_or_absolute(root, paths["accepted"]),
        "resume_pack": _relative_or_absolute(root, paths["resume"]),
        "attempts": _failure_count(paths["failures"]),
        "expected_outputs": expected,
    }
    active = _active_lease(paths["lease"])
    if active:
        return HeavyRunResult(
            True,
            "ATTACHED",
            message="identical RunKey is already running",
            pid=int(active["pid"]),
            **common,
        )
    if paths["accepted"].exists():
        valid, message = _validate_accepted(root, paths["accepted"], run_key)
        return HeavyRunResult(
            valid, "CACHE_HIT" if valid else "FAIL_CLOSED", message=message, **common
        )
    if common["attempts"] >= _max_attempts(job):
        return HeavyRunResult(
            False,
            "PLATEAU",
            message="unchanged RunKey exhausted its retry budget",
            **common,
        )
    return HeavyRunResult(
        True,
        "READY",
        message="new RunKey is eligible for one designated execution",
        **common,
    )


def run_heavy_job(
    root: Path, job_id: str, *, dry_run: bool = False
) -> HeavyRunResult:
    root = root.resolve()
    initial = inspect_heavy_job(root, job_id)
    job = _job(root, job_id)
    if initial.status == "BLOCKED_EXTERNAL_INPUT":
        resume = root / initial.resume_pack
        _write_resume(
            resume,
            initial,
            next_action="mount or configure the declared external root; do not execute",
        )
        return initial
    paths = _paths(root, job_id, initial.run_key)
    if initial.status in {"ATTACHED", "CACHE_HIT", "FAIL_CLOSED", "PLATEAU"}:
        _write_resume(
            paths["resume"],
            initial,
            next_action=(
                "wait/reuse"
                if initial.ok
                else "change a declared input or request human review"
            ),
        )
        return initial
    if dry_run:
        _write_resume(
            paths["resume"],
            initial,
            next_action="run through aeros heavy run when execution is intended",
        )
        return initial

    lease_payload = {
        "version": HEAVY_RUN_VERSION,
        "job_id": job_id,
        "run_key": initial.run_key,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": _now(),
        "command": list(initial.command),
    }
    acquired, lease = _acquire_lease(paths["lease"], lease_payload)
    if not acquired:
        attached = HeavyRunResult(
            True,
            "ATTACHED",
            job_id,
            initial.run_key,
            "identical RunKey acquired by another executor",
            command=initial.command,
            pid=int(lease.get("pid", 0)) or None,
            log_path=initial.log_path,
            accepted_manifest=initial.accepted_manifest,
            resume_pack=initial.resume_pack,
            attempts=initial.attempts,
            expected_outputs=initial.expected_outputs,
        )
        _write_resume(
            paths["resume"], attached, next_action="wait for the designated executor"
        )
        return attached

    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {str(k): str(v) for k, v in (job.get("env") or {}).items()}
    )
    environment.update(
        {
            "AEROS_HEAVY_EXECUTOR": "1",
            "AEROS_HEAVY_JOB_ID": job_id,
            "AEROS_HEAVY_RUN_KEY": initial.run_key,
        }
    )
    return_code = 1
    failure_message = ""
    roots = _runtime_roots(root, job)
    try:
        with paths["log"].open("w", encoding="utf-8") as log:
            process = subprocess.run(
                list(initial.command),
                cwd=roots["working_root"],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        return_code = process.returncode
        if return_code == 0:
            for check in job.get("acceptance_checks", []):
                check_command = (
                    shlex.split(check)
                    if isinstance(check, str)
                    else [str(item) for item in check]
                )
                with paths["log"].open("a", encoding="utf-8") as log:
                    checked = subprocess.run(
                        check_command,
                        cwd=roots["working_root"],
                        env=environment,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False,
                    )
                if checked.returncode != 0:
                    return_code = checked.returncode
                    failure_message = (
                        f"acceptance check failed: {shlex.join(check_command)}"
                    )
                    break
        if return_code == 0:
            outputs = _output_records(
                root, roots["artifact_root"], list(initial.expected_outputs)
            )
            _atomic_json(
                paths["accepted"],
                {
                    "version": HEAVY_RUN_VERSION,
                    "status": "accepted",
                    "accepted_at": _now(),
                    "job_id": job_id,
                    "run_key": initial.run_key,
                    "identity": _identity(root, job_id, job),
                    "outputs": outputs,
                    "log": {
                        "path": _relative_or_absolute(root, paths["log"]),
                        "sha256": _sha256(paths["log"]),
                    },
                    "does_not_prove": list(initial.does_not_prove),
                },
            )
            result = HeavyRunResult(
                True,
                "ACCEPTED",
                job_id,
                initial.run_key,
                (
                    "one designated execution produced and validated all "
                    "declared outputs"
                ),
                command=initial.command,
                pid=os.getpid(),
                log_path=initial.log_path,
                accepted_manifest=initial.accepted_manifest,
                resume_pack=initial.resume_pack,
                attempts=initial.attempts,
                expected_outputs=initial.expected_outputs,
            )
            _write_resume(
                paths["resume"],
                result,
                next_action="reuse this RunBundle until a declared input changes",
            )
            return result
    except Exception as exc:
        failure_message = str(exc)
    finally:
        paths["lease"].unlink(missing_ok=True)

    log_tail = ""
    if paths["log"].is_file():
        log_tail = paths["log"].read_text(
            encoding="utf-8", errors="replace"
        )[-8192:]
    failure = {
        "failed_at": _now(),
        "job_id": job_id,
        "run_key": initial.run_key,
        "return_code": return_code,
        "failure_signature": _json_hash(
            {"return_code": return_code, "tail": log_tail}
        ),
        "message": failure_message or f"command exited {return_code}",
    }
    paths["failures"].parent.mkdir(parents=True, exist_ok=True)
    with paths["failures"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(failure, sort_keys=True) + "\n")
    attempts = _failure_count(paths["failures"])
    plateau = attempts >= _max_attempts(job)
    result = HeavyRunResult(
        False,
        "PLATEAU" if plateau else "FAILED",
        job_id,
        initial.run_key,
        (
            "retry budget exhausted; change inputs or escalate"
            if plateau
            else failure["message"]
        ),
        command=initial.command,
        log_path=initial.log_path,
        accepted_manifest=initial.accepted_manifest,
        resume_pack=initial.resume_pack,
        attempts=attempts,
        expected_outputs=initial.expected_outputs,
    )
    _write_resume(
        paths["resume"],
        result,
        next_action="human review or a materially changed declared input",
    )
    return result
