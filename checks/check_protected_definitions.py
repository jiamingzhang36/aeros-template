#!/usr/bin/env python3
"""Fail if protected definition files have uncommitted changes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = TEMPLATE_ROOT / "docs" / "protected_definitions.yml"
PROTECTED_PATHS = [
    TEMPLATE_ROOT / "docs" / "protected_definitions.yml",
    TEMPLATE_ROOT / "docs" / "data_contract.yml",
    TEMPLATE_ROOT / "evidence" / "claim_registry.md",
    TEMPLATE_ROOT / "harness" / "permissions.yml",
]


def _is_standalone_repo() -> bool:
    """Return True only when the current template is its own git root."""
    try:
        result = subprocess.run(
            ["git", "-C", str(TEMPLATE_ROOT), "rev-parse", "--show-toplevel"],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        print("SKIP: git unavailable in environment; skipping protected-definition guardrail.")
        return False

    if result.returncode != 0:
        print(result.stderr.strip())
        print(
            "SKIP: no git repository at template root "
            f"({TEMPLATE_ROOT}). Initialize one locally with `git init` first."
        )
        return False

    return Path(result.stdout.strip()).resolve() == TEMPLATE_ROOT.resolve()


def _load_protection_status(path: Path) -> str:
    default_status = "draft"
    if not path.exists():
        return default_status

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("status:"):
            raw = stripped.split(":", 1)[1].split("#", 1)[0].strip()
            return raw.strip().strip("'\"").lower()
    return default_status


def main() -> int:
    if not _is_standalone_repo():
        print(
            "SKIP: protected-definition check is disabled until the template root is a "
            "standalone git repo."
        )
        return 0

    result = subprocess.run(
        ["git", "-C", str(TEMPLATE_ROOT), "status", "--porcelain", "--", *map(str, PROTECTED_PATHS)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip())
        return result.returncode

    changes = result.stdout.strip()
    status = _load_protection_status(STATUS_PATH)
    if status not in {"draft", "locked"}:
        print(f"WARN: unknown protected_definitions status '{status}', treated as draft-mode.")
        status = "draft"

    if status == "draft":
        if changes:
            print("WARN: protected files have uncommitted changes while status is draft:")
            print(changes)
            print("Draft mode: review only; lock definitions before execution.")
            return 0
        print("PASS: protected definition files unchanged in draft mode")
        return 0

    if status == "locked":
        if changes:
            print("FAIL: protected files have uncommitted changes:")
            print(changes)
            print("Human approval is required before changing protected definitions.")
            return 1

        print("PASS: protected definition files are unchanged (locked mode)")
        return 0

    # Defensive fallback; should be unreachable due normalization above.
    if changes:
        print(f"WARN: protected files have uncommitted changes (status={status})")
        print(changes)
        return 0

    print(f"PASS: protected definition files are unchanged (status={status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
