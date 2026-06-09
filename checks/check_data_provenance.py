#!/usr/bin/env python3
"""Data-layer provenance check (mirror of check_provenance for acquired data).

Every row in evidence/data_index.csv must have a provenance JSON
(outputs/.data_provenance/<data_id>.json) with a verifiable source URL, a
retrieval timestamp, and a content hash; if it registered a local file, that file
must exist and its sha256 must match.

Passes quietly when there is no data_index.csv yet (the data-acquisition layer is
opt-in / roadmap — see docs/data_layer_roadmap.md), so wiring this into a gate is
safe before the layer is in use.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

DATA_INDEX = Path("evidence/data_index.csv")
PROVENANCE_DIR = Path("outputs/.data_provenance")
REQUIRED = ("source_url", "retrieved_at", "sha256")
CHECK_NAME = "check_data_provenance"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    failures: list[str] = []
    if not DATA_INDEX.exists():
        msg = f"{DATA_INDEX} not present (data-acquisition layer not in use yet)"
        print(json.dumps({"check": CHECK_NAME, "status": "pass", "failures": []})
              if as_json else f"PASS: {msg}")
        return 0

    with DATA_INDEX.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    for row in rows:
        did = (row.get("data_id") or "").strip()
        if not did:
            continue
        prov = PROVENANCE_DIR / f"{did}.json"
        if not prov.exists():
            failures.append(f"{did}: missing provenance JSON ({prov})")
            continue
        try:
            rec = json.loads(prov.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{did}: provenance JSON unreadable ({exc})")
            continue
        for field in REQUIRED:
            if not str(rec.get(field, "")).strip():
                failures.append(f"{did}: provenance missing required field '{field}'")
        # index sha256 should match provenance sha256
        if row.get("sha256") and rec.get("sha256") and row["sha256"] != rec["sha256"]:
            failures.append(f"{did}: sha256 in data_index != provenance")
        # if a local file is registered, it must exist + hash-match
        out = (row.get("output_path") or "").strip()
        if out:
            p = Path(out)
            if not p.exists():
                failures.append(f"{did}: registered output_path missing: {out}")
            elif row.get("sha256") and _sha256(p) != row["sha256"]:
                failures.append(f"{did}: sha256 mismatch for {out}")

    status = "fail" if failures else "pass"
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif failures:
        print("FAIL: data provenance problems:")
        for f in failures:
            print(f"  - {f}")
    else:
        print(f"PASS: {len(rows)} data source(s) traced to provenance")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
