#!/usr/bin/env python3
"""Check expanded AI-output collection records when present."""

from __future__ import annotations

import json
import sys
from pathlib import Path


OUTPUTS = Path("outputs/audit_runs/expanded_ai_outputs.jsonl")
GRID = Path("outputs/audit_runs/expanded_prompt_grid.csv")

REQUIRED_FIELDS = {
    "prompt_id",
    "persona",
    "prompt_variant",
    "model",
    "run_index",
    "collected_at",
    "prompt_text",
    "output_text",
}


def main() -> int:
    if not OUTPUTS.exists():
        print("SKIP: expanded AI output records not present yet")
        return 0

    failures: list[str] = []
    if not GRID.exists():
        failures.append(f"missing {GRID}")

    seen: set[str] = set()
    rows = 0
    with OUTPUTS.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            rows += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(f"{OUTPUTS}:{line_no}: invalid JSON ({exc})")
                continue
            missing = REQUIRED_FIELDS - set(record)
            if missing:
                failures.append(f"{OUTPUTS}:{line_no}: missing fields {', '.join(sorted(missing))}")
            prompt_id = str(record.get("prompt_id", "")).strip()
            if prompt_id:
                seen.add(prompt_id)
            if not str(record.get("output_text", "")).strip():
                failures.append(f"{OUTPUTS}:{line_no}: output_text is empty")

    if rows < 12:
        failures.append(f"{OUTPUTS}: expected at least 12 collected output rows")
    if len(seen) != rows:
        failures.append(f"{OUTPUTS}: prompt_id values must be populated and unique")

    if failures:
        print("FAIL: expanded collection output problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: expanded collection outputs are present ({rows} row(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
