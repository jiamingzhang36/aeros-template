#!/usr/bin/env python3
"""Check provider-connector collection metadata when collection records exist."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


OUTPUTS = Path(os.getenv("AEROS_PROVIDER_COLLECTION_OUTPUT", "outputs/audit_runs/expanded_ai_outputs.jsonl"))
REQUIRED_FIELDS = {
    "provider",
    "provider_request_id",
    "prompt_sha256",
    "output_sha256",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "duration_ms",
}


def main() -> int:
    if not OUTPUTS.exists():
        print("SKIP: provider collection output not present yet")
        return 0

    failures: list[str] = []
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
                failures.append(f"{OUTPUTS}:{line_no}: missing provider fields {', '.join(sorted(missing))}")
            for field in ("prompt_sha256", "output_sha256"):
                value = str(record.get(field, "")).strip().lower()
                if len(value) != 64 or not all(c in "0123456789abcdef" for c in value):
                    failures.append(f"{OUTPUTS}:{line_no}: malformed {field}")
            if float(record.get("cost_usd", 0.0) or 0.0) < 0:
                failures.append(f"{OUTPUTS}:{line_no}: cost_usd must be non-negative")

    if failures:
        print("FAIL: provider collection metadata problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: provider collection metadata present ({rows} row(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
