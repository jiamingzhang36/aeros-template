#!/usr/bin/env python3
"""AEROS master pipeline: delegates to a configured project pipeline.

This script is the bridge between AEROS's check_pipeline_runs check and the
actual research pipeline. Configure the delegate in project_manifest.yml under
automation.pipeline, or with AEROS_PIPELINE_* environment variables.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

AEROS_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = AEROS_ROOT / "project_manifest.yml"


def _load_pipeline_config() -> dict:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    automation = manifest.get("automation", {}) or {}
    configured = automation.get("pipeline", {}) or {}
    env_command = os.getenv("AEROS_PIPELINE_COMMAND", "").strip()
    env_cwd = os.getenv("AEROS_PIPELINE_CWD", "").strip()
    env_outputs = os.getenv("AEROS_PIPELINE_OUTPUTS", "").strip()

    command = env_command.split() if env_command else configured.get("command", [])
    cwd = env_cwd or configured.get("cwd", ".")
    key_outputs = (
        [item.strip() for item in env_outputs.split(",") if item.strip()]
        if env_outputs
        else configured.get("key_outputs", [])
    )
    return {"command": command, "cwd": cwd, "key_outputs": key_outputs}


def _resolve(path: str, *, base: Path) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else base / p


def main() -> int:
    config = _load_pipeline_config()
    command = list(config["command"] or [])
    if not command:
        print("SKIP: no automation.pipeline.command configured")
        print("Set project_manifest.yml automation.pipeline.command or AEROS_PIPELINE_COMMAND.")
        return 0

    cwd = _resolve(str(config["cwd"]), base=AEROS_ROOT)
    executable = _resolve(command[0], base=cwd)
    if executable.exists():
        command[0] = str(executable)
    if not cwd.exists():
        print(f"FAIL: configured pipeline cwd does not exist: {cwd}")
        return 1

    print("=== AEROS delegated pipeline ===")
    print(f"  cwd     : {cwd}")
    print(f"  command : {' '.join(command)}")

    result = subprocess.run(command, cwd=str(cwd))

    if result.returncode != 0:
        print(f"FAIL: delegated pipeline exited with code {result.returncode}")
        return result.returncode

    key_outputs = [_resolve(str(path), base=cwd) for path in config["key_outputs"]]
    missing = [p for p in key_outputs if not p.exists()]
    if missing:
        print("WARN: some expected output files not found:")
        for p in missing:
            print(f"  {p}")
    elif key_outputs:
        print("PASS: all key output files present")
    else:
        print("PASS: pipeline completed; no key_outputs configured")

    print("=== delegated pipeline complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
