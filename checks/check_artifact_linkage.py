#!/usr/bin/env python3
"""Linkage guard: structured data references must resolve to real inventory ids.

Layer 2 against "conformance without substance" (the P0 anti-fabrication principle
generalized from paper numbers to design artifacts): instead of checking that a
field is *filled*, check that it *references something real*. A method card that
names the data it relies on must name data ids that actually exist in
discovery/data_inventory.csv — prose alone is not enough.

To stay robust (no fragile prose scanning), references are declared structurally
in the artifact's YAML front matter as a `data_refs:` list. Absent `data_refs`
(e.g. a draft/stub) -> pass; this is opt-in and never penalizes an unfilled file.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

CHECK_NAME = "check_artifact_linkage"
INVENTORY = Path("discovery/data_inventory.csv")
DEFAULT_ARTIFACTS = ["docs/method_card.md"]


def _front_matter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not m:
        return {}
    try:
        import yaml
        data = yaml.safe_load(m.group(1)) or {}
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def _inventory_ids() -> set[str]:
    if not INVENTORY.exists():
        return set()
    ids: set[str] = set()
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            did = (row.get("data_id") or "").strip()
            if did:
                ids.add(did)
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("artifacts", nargs="*", help="artifacts that may declare data_refs")
    args = parser.parse_args(argv)

    artifacts = [Path(p) for p in (args.artifacts or DEFAULT_ARTIFACTS)]
    failures: list[str] = []
    checked_refs = 0
    valid = _inventory_ids()

    for art in artifacts:
        if not art.exists():
            continue
        fm = _front_matter(art.read_text(encoding="utf-8", errors="ignore"))
        refs = fm.get("data_refs")
        if not refs:
            continue  # opt-in: no declared references to verify
        if not isinstance(refs, list):
            failures.append(f"{art}: data_refs must be a list")
            continue
        if not valid:
            failures.append(f"{art}: declares data_refs but {INVENTORY} has no data ids to verify against")
            continue
        for ref in refs:
            checked_refs += 1
            r = str(ref).strip()
            if r and r not in valid:
                failures.append(f"{art}: data_ref {r!r} does not exist in {INVENTORY}")

    status = "fail" if failures else "pass"
    if args.json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif failures:
        print("FAIL: unresolved artifact data references:")
        for f in failures:
            print(f"  - {f}")
    else:
        print(f"PASS: all declared data references resolve ({checked_refs} ref(s) checked)")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
