#!/usr/bin/env python3
"""Check that the AEROS skill layer scaffold is present."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_FILES = {
    Path("harness/skill_registry.md"): [
        "## Skill Layer Principle",
        "## Borrowed Organization",
        "## Skill Use Status",
    ],
    Path("harness/skill_invocation_rules.md"): [
        "## Invocation Order",
        "## Literature Skills",
        "## Skill Conflict Rule",
    ],
    Path("harness/external_skill_map.yml"): [
        "awesome_econ_ai_stuff:",
        "econ_writing_skill:",
        "research_ideation:",
        "lit_review_assistant:",
        "econ_writing_skill:",
    ],
}


def main() -> int:
    failures: list[str] = []

    for path, required_text in REQUIRED_FILES.items():
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [item for item in required_text if item not in text]
        if missing:
            failures.append(f"{path}: missing required content {missing}")

    if failures:
        print("FAIL: skill layer problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: skill layer scaffold is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
