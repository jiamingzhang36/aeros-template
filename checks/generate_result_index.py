#!/usr/bin/env python3
"""Generate evidence/result_index.csv from outputs/.provenance JSON files."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
utils_dir = ROOT_DIR / "code"
if str(utils_dir) not in sys.path:
    sys.path.insert(0, str(utils_dir))

from utils.provenance import normalize_records_for_index


PROVENANCE_DIR = Path("outputs/.provenance")
RESULT_INDEX = Path("evidence/result_index.csv")


def _collect_records() -> list[dict]:
    if not PROVENANCE_DIR.exists():
        return []

    records: list[dict] = []
    for path in sorted(PROVENANCE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        records.append(payload)
    return records


def main() -> int:
    records = _collect_records()
    rows = normalize_records_for_index(records)
    RESULT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_INDEX.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "result_id",
            "output_type",
            "path",
            "script_or_source",
            "description",
            "created_date",
            "linked_claims",
            "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {RESULT_INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
