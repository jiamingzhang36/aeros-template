#!/usr/bin/env python3
"""Check that task files include the core harness contract sections."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


TASK_DIR = Path("tasks")
REQUIRED_HEADINGS = [
    "## Objective",
    "## Stop Rule",
    "## Harness Mode",
    "## Files to Inspect",
    "## Files Allowed to Modify",
    "## Files Forbidden to Modify",
    "## Constraints",
    "## Expected Output",
    "## Checks to Run",
    "## Done When",
]
REQUIRED_HEADINGS_MINOR = [
    "## Objective",
    "## Allowed",
    "## Constraints",
    "## Done When",
]


def _load_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return {}

    front_matter = match.group(1)
    try:
        parsed = yaml.safe_load(front_matter) or {}
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def main() -> int:
    failures: list[str] = []
    task_files = sorted(TASK_DIR.rglob("*.md"))
    for path in task_files:
        text = path.read_text(encoding="utf-8")
        front = _load_front_matter(path)
        # Scope: only validate real task contracts. A .md in tasks/ with no front
        # matter is a note/bootstrap file, not a contract — validating it (e.g.
        # requiring allowed_skills) is a false failure.
        if not front:
            continue
        task_class = front.get("task_class", "standard").lower()
        if task_class not in {"minor", "standard", "high_risk"}:
            missing = ["front matter: task_class must be minor, standard, or high_risk"]
            required_headings = REQUIRED_HEADINGS
        elif task_class == "minor":
            required_headings = REQUIRED_HEADINGS_MINOR
            missing: list[str] = []
        else:
            required_headings = REQUIRED_HEADINGS
            missing = []

        allowed_skills = front.get("allowed_skills")
        if allowed_skills is None:
            missing.append("front matter: allowed_skills")
        elif not isinstance(allowed_skills, list):
            missing.append("front matter: allowed_skills must be a list")
        elif not all(isinstance(item, str) for item in allowed_skills):
            missing.append("front matter: allowed_skills items must be strings")

        if not missing:
            missing = [heading for heading in required_headings if heading not in text]
            if "task_class" not in front:
                missing.append("front matter: task_class")

        if missing:
            failures.append(f"{path}: missing {', '.join(missing)}")

    if failures:
        print("FAIL: task contract problems detected:")
        print("\n".join(failures))
        return 1

    print(
        "PASS: task contracts include required harness sections ("
        f"{len(task_files)} file(s) checked)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
