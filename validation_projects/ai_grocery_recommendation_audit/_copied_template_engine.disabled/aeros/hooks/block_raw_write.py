#!/usr/bin/env python3
"""PreToolUse hook: hard-block any agent write into data/raw/.

This is the runtime enforcement of `harness/permissions.yml` -> deny: data/raw/**.
Claude Code runs this before every Write/Edit/MultiEdit tool call, passing the
tool input as JSON on stdin. Exit code 2 blocks the call and returns the stderr
text to the agent as the reason.

Test standalone (no agent needed):
    echo '{"tool_name":"Write","tool_input":{"file_path":"data/raw/x.csv"}}' \\
        | python3 aeros/hooks/block_raw_write.py ; echo "exit=$?"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Paths that may never be written by an agent. Mirrors permissions.yml `deny`.
PROTECTED_PREFIXES = ("data/raw/",)
ALLOWED_EXACT = {"data/raw/.gitkeep"}


def _extract_paths(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input", {}) or {}
    paths: list[str] = []
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            paths.append(value)
    # MultiEdit / batched edits sometimes carry an edits list.
    for edit in tool_input.get("edits", []) or []:
        if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
            paths.append(edit["file_path"])
    return paths


def _is_protected(raw_path: str) -> bool:
    # Normalize to a repo-relative posix path when possible.
    p = raw_path.replace("\\", "/")
    # Strip a leading absolute project root if present.
    if "/data/raw/" in p:
        p = "data/raw/" + p.split("/data/raw/", 1)[1]
    p = p.lstrip("./")
    if p in ALLOWED_EXACT:
        return False
    return any(p.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # If we cannot parse the event, do not block (fail open for unknown shapes).
        return 0

    for path in _extract_paths(payload):
        if _is_protected(path):
            sys.stderr.write(
                "AEROS permission policy: writing to data/raw/ is denied "
                f"(attempted: {path}). Raw data is immutable; write to "
                "data/intermediate/ or data/clean/ instead."
            )
            return 2  # exit 2 => block the tool call, feed stderr back to agent

    return 0


if __name__ == "__main__":
    sys.exit(main())
