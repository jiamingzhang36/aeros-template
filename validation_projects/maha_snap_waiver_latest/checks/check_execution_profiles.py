#!/usr/bin/env python3
"""Validate ExecutionProfile wiring."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.execution_profile import load_execution_profiles, resolved_command  # noqa: E402


def main() -> int:
    root = Path.cwd()
    profiles = load_execution_profiles(root)
    failures: list[str] = []
    if "smoke" not in profiles:
        failures.append("missing smoke execution profile")
    for name, profile in profiles.items():
        if not profile.cwd:
            failures.append(f"{name}: missing cwd")
        if not profile.python:
            failures.append(f"{name}: missing python")
        if profile.command and not resolved_command(profile):
            failures.append(f"{name}: command did not resolve")
        if any(hook not in {"reconcile", "session_scope"} for hook in profile.post_run_hooks):
            failures.append(f"{name}: unsupported post_run_hook in {profile.post_run_hooks}")
    if failures:
        print("FAIL: execution profile problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: execution profiles are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
