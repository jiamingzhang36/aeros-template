#!/usr/bin/env python3
"""Check that root, discovery, literature, and execution AGENTS rules exist."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED = {
    Path("AGENTS.md"): ["## Hard Rules", "## Discovery-Stage Rules", "## Execution Rules"],
    Path("discovery/AGENTS.md"): ["## Literature Function Rules", "## Source-Grounded Rules", "## Stage Rule"],
    Path("discovery/literature/AGENTS.md"): ["## Hard Rules", "## Status Flow", "## Output Rule"],
    Path("execution/AGENTS.md"): ["## Stage Entry Rule", "## Protected Definitions", "## Required Checks", "## Critic and Human Gate"],
}


def main() -> int:
    failures: list[str] = []
    for path, headings in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [heading for heading in headings if heading not in text]
        if missing:
            failures.append(f"{path}: missing headings {missing}")

    if failures:
        print("FAIL: stage AGENTS problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: root, discovery, literature, and execution AGENTS rules exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
