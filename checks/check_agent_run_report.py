#!/usr/bin/env python3
"""Check agent run report and critic report templates for required sections."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_AGENT_HEADINGS = [
    "## Run Metadata",
    "## Objective",
    "## Files Read",
    "## Files Modified",
    "## Commands Run",
    "## Outputs Changed",
    "## Checks Run",
    "## Protected Definitions",
    "## Claim Changes",
    "## Human Decisions Needed",
    "## Completion Status",
]

REQUIRED_CRITIC_HEADINGS = [
    "## Review Target",
    "## Review Questions",
    "## Findings",
    "## Verdict",
]


def missing_headings(path: Path, required: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [heading for heading in required if heading not in text]


def main() -> int:
    failures: list[str] = []
    checks = [
        (Path("agent_runs/TEMPLATE_agent_run_report.md"), REQUIRED_AGENT_HEADINGS),
        (Path("agent_runs/TEMPLATE_critic_report.md"), REQUIRED_CRITIC_HEADINGS),
    ]

    for path, required in checks:
        if not path.exists():
            failures.append(f"{path}: missing file")
            continue
        missing = missing_headings(path, required)
        if missing:
            failures.append(f"{path}: missing {', '.join(missing)}")

    if failures:
        print("FAIL: agent report template problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: agent and critic report templates include required sections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
