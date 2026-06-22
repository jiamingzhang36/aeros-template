"""Execution profiles for AEROS runtime commands.

ExecutionProfile v1 centralizes cwd/interpreter/command/post-run hooks so checks,
ActionSpecs, and pipeline runners do not each invent their own runtime semantics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import os
import shlex
from typing import Any

import yaml


MANIFEST = Path("project_manifest.yml")
DEFAULT_PROFILE = "smoke"


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    cwd: str = "."
    command: tuple[str, ...] = ()
    python: str = "python3"
    env_file: str = ""
    env_policy: str = "no_secrets"
    post_run_hooks: tuple[str, ...] = field(default_factory=tuple)
    source: str = "project_manifest.yml"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["command"] = list(self.command)
        data["post_run_hooks"] = list(self.post_run_hooks)
        return data


def _command_list(raw_command: object) -> list[str]:
    if isinstance(raw_command, list):
        return [str(part) for part in raw_command if str(part)]
    if isinstance(raw_command, str) and raw_command.strip():
        return shlex.split(raw_command)
    return []


def _load_manifest(project_root: Path) -> dict[str, Any]:
    path = project_root / MANIFEST
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _profile_from_mapping(name: str, mapping: dict[str, Any], *, source: str) -> ExecutionProfile:
    runtime = mapping.get("runtime") if isinstance(mapping.get("runtime"), dict) else {}
    python = (
        os.getenv("AEROS_PIPELINE_PYTHON", "").strip()
        or str(mapping.get("python") or runtime.get("python") or "python3").strip()
    )
    hooks = mapping.get("post_run_hooks") or runtime.get("post_run_hooks") or []
    if isinstance(hooks, str):
        hooks = [hooks]
    return ExecutionProfile(
        name=name,
        cwd=str(mapping.get("cwd") or "."),
        command=tuple(_command_list(mapping.get("command", []))),
        python=python,
        env_file=str(mapping.get("env_file") or runtime.get("env_file") or ""),
        env_policy=str(mapping.get("env_policy") or runtime.get("env_policy") or "no_secrets"),
        post_run_hooks=tuple(str(hook) for hook in hooks if str(hook)),
        source=source,
    )


def load_execution_profiles(project_root: Path) -> dict[str, ExecutionProfile]:
    manifest = _load_manifest(project_root)
    profiles: dict[str, ExecutionProfile] = {}
    raw_profiles = manifest.get("execution_profiles") or {}
    if isinstance(raw_profiles, dict):
        for name, data in raw_profiles.items():
            if isinstance(data, dict):
                profiles[str(name)] = _profile_from_mapping(
                    str(name),
                    data,
                    source="project_manifest.yml:execution_profiles",
                )

    # Backward compatibility: automation.pipeline remains a valid profile source.
    pipeline = ((manifest.get("automation") or {}).get("pipeline") or {})
    if isinstance(pipeline, dict):
        name = str(pipeline.get("profile") or DEFAULT_PROFILE)
        profiles.setdefault(name, _profile_from_mapping(
            name,
            pipeline,
            source="project_manifest.yml:automation.pipeline",
        ))
    return profiles


def resolve_execution_profile(project_root: Path, profile_name: str | None = None) -> ExecutionProfile:
    profiles = load_execution_profiles(project_root)
    name = profile_name or os.getenv("AEROS_EXECUTION_PROFILE", "").strip() or DEFAULT_PROFILE
    if name in profiles:
        return profiles[name]
    if profiles:
        return profiles[sorted(profiles)[0]]
    return ExecutionProfile(name=name)


def resolved_command(profile: ExecutionProfile) -> list[str]:
    cmd = list(profile.command)
    if cmd:
        first = Path(cmd[0]).name
        if first in {"python", "python3"} and profile.python:
            cmd[0] = profile.python
    return cmd


def display_command(cmd: list[str]) -> str:
    return shlex.join(cmd)
