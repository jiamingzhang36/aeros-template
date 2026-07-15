"""Immutable, content-addressed RunBundle execution for accepted research runs.

The first supported vertical slice is ``run_specification``. The RunBundle ID
binds the declared action semantics, immutable inputs, executor identity, and
validator identity. An exact replay validates and reuses the accepted bundle;
any missing or changed accepted artifact fails closed and is never overwritten.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
from typing import Any

from .action_spec import ActionSpec
from .context_budget import prepare_context_packet
from .execution_envelope import ExecutionEnvelopeResult, execute_action_spec_in_isolated_worktree


RUN_BUNDLE_VERSION = 1
SUPPORTED_KINDS = {"run_specification"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _flag_value(parts: list[str], flag: str) -> str:
    try:
        index = parts.index(flag)
    except ValueError:
        return ""
    return parts[index + 1] if index + 1 < len(parts) else ""


def _replace_flag(parts: list[str], flag: str, value: str) -> list[str]:
    result = list(parts)
    try:
        index = result.index(flag)
    except ValueError:
        result.extend((flag, value))
        return result
    if index + 1 >= len(result):
        result.append(value)
    else:
        result[index + 1] = value
    return result


def _semantic_command(parts: list[str]) -> list[str]:
    result = list(parts)
    for flag in ("--output", "--exhibit"):
        try:
            index = result.index(flag)
        except ValueError:
            continue
        if index + 1 < len(result):
            result[index + 1] = f"<{flag[2:]}>"
    return result


def _input_records(root: Path, command_parts: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for flag in ("--source", "--registry"):
        value = _flag_value(command_parts, flag)
        if not value:
            continue
        path = (root / value).resolve()
        try:
            relative = path.relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"RunBundle input escapes project root: {value}") from exc
        if not path.exists() or not path.is_file():
            raise ValueError(f"RunBundle input is missing: {relative}")
        records.append({"role": flag[2:], "path": relative, "sha256": _sha256(path)})
    return records


def _validator_records(root: Path, acceptance_checks: tuple[str, ...]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for command in acceptance_checks:
        parts = shlex.split(command)
        script = next((item for item in parts if item.startswith("checks/") and item.endswith(".py")), "")
        if not script:
            raise ValueError(f"RunBundle validator is not a direct checks/*.py command: {command}")
        path = root / script
        if not path.exists() or not path.is_file():
            raise ValueError(f"RunBundle validator is missing: {script}")
        records.append({"path": script, "sha256": _sha256(path)})
    return records


def _executor_identity() -> dict[str, str]:
    path = Path(__file__).resolve().with_name("job_actions.py")
    if not path.exists():
        raise ValueError("RunBundle executor is missing: aeros/runtime/job_actions.py")
    return {
        "python": sys.version.split()[0],
        "job_actions_path": "aeros/runtime/job_actions.py",
        "job_actions_sha256": _sha256(path),
    }


def _failed(message: str, *, run_id: str = "", manifest: str = "") -> ExecutionEnvelopeResult:
    return ExecutionEnvelopeResult(
        ok=False,
        return_code=1,
        run_id=run_id,
        run_bundle_manifest=manifest,
        validation_passed=False,
        worktree_removed=True,
        message=message,
    )


def _plan(root: Path, spec: ActionSpec) -> tuple[ActionSpec, dict[str, Any], Path, Path]:
    if spec.kind not in SUPPORTED_KINDS:
        raise ValueError(f"immutable RunBundle does not support ActionSpec kind: {spec.kind}")
    command_parts = shlex.split(spec.command)
    inputs = _input_records(root, command_parts)
    validators = _validator_records(root, spec.acceptance_checks)
    identity = {
        "version": RUN_BUNDLE_VERSION,
        "kind": spec.kind,
        "lane": spec.lane,
        "effect_class": spec.effect_class,
        "capabilities": list(spec.capabilities),
        "semantic_command": _semantic_command(command_parts),
        "inputs": inputs,
        "executor": _executor_identity(),
        "validators": validators,
        "preconditions": list(spec.preconditions),
        "runtime_profile": spec.runtime_profile,
        "resource_budget": dict(spec.resource_budget),
    }
    run_id = "RUN-" + _json_hash(identity)[:24]
    bundle_rel = Path("outputs") / "econ" / "runs" / run_id
    result_rel = bundle_rel / "result.json"
    exhibit_rel = bundle_rel / "exhibit.csv"
    validation_rel = bundle_rel / "validation.json"
    manifest_rel = bundle_rel / "run_bundle.json"

    rewritten_command = _replace_flag(command_parts, "--output", result_rel.as_posix())
    rewritten_command = _replace_flag(rewritten_command, "--exhibit", exhibit_rel.as_posix())
    rewritten_checks: list[str] = []
    for check in spec.acceptance_checks:
        parts = _replace_flag(shlex.split(check), "--result", result_rel.as_posix())
        parts = _replace_flag(parts, "--exhibit", exhibit_rel.as_posix())
        rewritten_checks.append(shlex.join(parts))

    envelope = dict(spec.execution_envelope)
    envelope.update({
        "write_roots": [bundle_rel.as_posix() + "/"],
        "expected_outputs": [result_rel.as_posix(), exhibit_rel.as_posix()],
        "validation_manifest": validation_rel.as_posix(),
        "runtime_profile": "isolated-immutable-run-bundle",
    })
    rewritten = replace(
        spec,
        command=shlex.join(rewritten_command),
        expected_outputs=(result_rel.as_posix(), exhibit_rel.as_posix()),
        acceptance_checks=tuple(rewritten_checks),
        idempotency_key=run_id,
        runtime_profile="isolated-immutable-run-bundle",
        execution_envelope=envelope,
    )
    plan = {
        "run_id": run_id,
        "identity": identity,
        "expected_outputs": [result_rel.as_posix(), exhibit_rel.as_posix()],
        "validation_manifest": validation_rel.as_posix(),
        "manifest": manifest_rel.as_posix(),
    }
    return rewritten, plan, root / bundle_rel, root / manifest_rel


def _validate_existing(root: Path, plan: dict[str, Any], manifest_path: Path) -> tuple[bool, str]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        return False, f"RunBundle manifest is unreadable: {exc}"
    if manifest.get("version") != RUN_BUNDLE_VERSION or manifest.get("run_id") != plan["run_id"]:
        return False, "RunBundle manifest identity mismatch"
    if manifest.get("identity_hash") != _json_hash(plan["identity"]):
        return False, "RunBundle identity hash mismatch"
    recorded_outputs = manifest.get("accepted_outputs", [])
    expected_paths = set(plan["expected_outputs"])
    if {str(item.get("path", "")) for item in recorded_outputs} != expected_paths:
        return False, "RunBundle accepted-output set mismatch"
    for item in recorded_outputs:
        relative = str(item.get("path", ""))
        path = root / relative
        if not path.exists() or not path.is_file() or _sha256(path) != item.get("sha256"):
            return False, f"RunBundle accepted output was changed or removed: {relative}"
    validation = manifest.get("validation_manifest", {})
    validation_path = root / str(validation.get("path", ""))
    if not validation_path.exists() or not validation_path.is_file() or _sha256(validation_path) != validation.get("sha256"):
        return False, "RunBundle validation manifest was changed or removed"
    return True, "validated immutable RunBundle cache hit"


def _write_manifest_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    raw = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def execute_research_job_run_bundle(
    root: Path,
    spec: ActionSpec,
    *,
    timeout_seconds: int = 120,
) -> ExecutionEnvelopeResult:
    """Execute or validate-cache one immutable ``run_specification`` bundle."""

    root = root.resolve()
    try:
        rewritten, plan, bundle_dir, manifest_path = _plan(root, spec)
    except (OSError, ValueError) as exc:
        return _failed(str(exc))

    run_id = str(plan["run_id"])
    manifest_rel = manifest_path.relative_to(root).as_posix()
    if manifest_path.exists():
        valid, message = _validate_existing(root, plan, manifest_path)
        if not valid:
            return _failed(message, run_id=run_id, manifest=manifest_rel)
        return ExecutionEnvelopeResult(
            ok=True,
            return_code=0,
            accepted_outputs=tuple(plan["expected_outputs"]),
            validation_passed=True,
            validation_manifest=str(plan["validation_manifest"]),
            worktree_removed=True,
            message=message,
            run_id=run_id,
            run_bundle_manifest=manifest_rel,
            cache_hit=True,
        )
    if bundle_dir.exists():
        return _failed(
            "RunBundle directory already exists without an accepted immutable manifest",
            run_id=run_id,
            manifest=manifest_rel,
        )

    context_packet = prepare_context_packet(root, rewritten)
    result = execute_action_spec_in_isolated_worktree(root, rewritten, timeout_seconds=timeout_seconds)
    if not result.ok:
        return replace(result, run_id=run_id, run_bundle_manifest=manifest_rel, cache_hit=False)

    try:
        accepted_outputs = [
            {"path": relative, "sha256": _sha256(root / relative)} for relative in plan["expected_outputs"]
        ]
        validation_relative = str(plan["validation_manifest"])
        active_brief_hash = hashlib.sha256(context_packet.active_brief.encode("utf-8")).hexdigest()
        manifest = {
            "version": RUN_BUNDLE_VERSION,
            "run_id": run_id,
            "status": "accepted",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "identity": plan["identity"],
            "identity_hash": _json_hash(plan["identity"]),
            "accepted_outputs": accepted_outputs,
            "validation_manifest": {
                "path": validation_relative,
                "sha256": _sha256(root / validation_relative),
            },
            "context_budget": {
                "active_brief_sha256": active_brief_hash,
                "estimated_tokens": context_packet.estimated_tokens,
                "max_input_tokens": context_packet.max_input_tokens,
                "compacted": context_packet.compacted,
                "omitted_event_count": context_packet.omitted_event_count,
                "artifact_pointers": list(context_packet.artifact_pointers),
            },
            "does_not_prove": [
                "scientific validity of the specification",
                "claim or release authority",
                "semantic completeness of compacted context",
            ],
        }
        _write_manifest_atomic(manifest_path, manifest)
    except (OSError, ValueError) as exc:
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        return _failed(
            f"RunBundle manifest commit failed and copied outputs were rolled back: {exc}",
            run_id=run_id,
            manifest=manifest_rel,
        )

    return replace(
        result,
        run_id=run_id,
        run_bundle_manifest=manifest_rel,
        cache_hit=False,
        message="accepted immutable content-addressed RunBundle",
    )
