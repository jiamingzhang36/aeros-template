#!/usr/bin/env python3
"""Validate the unified evidence-delta ledger."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.evidence_delta import DELTA_LOG, read_delta_records  # noqa: E402


def main() -> int:
    root = Path.cwd()
    path = root / DELTA_LOG
    if not path.exists():
        print("PASS: evidence delta log inactive (no evidence/delta_log.jsonl yet)")
        return 0
    records, failures = read_delta_records(root)
    if failures:
        print("FAIL: evidence delta log problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: evidence delta log valid ({len(records)} record(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
