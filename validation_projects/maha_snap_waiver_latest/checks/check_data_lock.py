#!/usr/bin/env python3
"""HARD gate: registered datasets match the frozen, owner-signed lock.

Data-layer analog of the number-drift lock (`paper/numbers.lock.yml`, Phase E).
`check_data_provenance` checks file == the sha recorded in `data_index.csv`;
this checks that recorded sha == the FROZEN sha in `evidence/data.lock.yml`.

The two together close the silent-update hole: changing a dataset's file and its
provenance record in lockstep passes provenance, but still trips this lock until
an owner deliberately re-locks (bumps sha256 + locked_by + locked_at). The git
history of `data.lock.yml` is the acceptance audit trail.

Stays quiet (passes) when there is no `data_index.csv` yet (opt-in layer).
Run `python checks/check_data_lock.py --selftest`.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

DATA_INDEX = Path("evidence/data_index.csv")
LOCK = Path("evidence/data.lock.yml")
CHECK_NAME = "check_data_lock"


def audit(index_rows: list[dict], lock: dict | None) -> list[str]:
    if lock is None:
        return [f"missing {LOCK} (lock each registered dataset with an owner sign-off)"]
    locked = lock.get("datasets") or {}
    failures: list[str] = []
    for row in index_rows:
        did = (row.get("data_id") or "").strip()
        if not did:
            continue
        idx_sha = (row.get("sha256") or "").strip()
        entry = locked.get(did)
        if entry is None:
            failures.append(f"{did}: not in data.lock.yml (lock it with owner sign-off)")
            continue
        if not str(entry.get("locked_by") or "").strip():
            failures.append(f"{did}: lock entry missing locked_by (owner sign-off)")
        lock_sha = str(entry.get("sha256") or "").strip()
        if lock_sha and idx_sha and lock_sha != idx_sha:
            failures.append(f"{did}: sha256 drifted from lock — data changed; "
                            f"re-verify upstream, then re-lock (bump sha256 + locked_by + locked_at)")
    return failures


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: registered datasets match the owner-signed lock{(' — ' + note) if note else ''}")
    else:
        print("FAIL: data lock/drift gate:")
        for f in failures:
            print(f"  - {f}")
        print("Update evidence/data.lock.yml (owner re-lock) only after re-verifying the source.")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate datasets against the frozen lock.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not DATA_INDEX.exists():
        return _emit(args.json, "pass", [], "no data_index.csv yet")
    if yaml is None:
        return _emit(args.json, "fail", ["PyYAML not available to read the lock"])
    index_rows = list(csv.DictReader(DATA_INDEX.read_text(encoding="utf-8").splitlines()))
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else None
    failures = audit(index_rows, lock)
    return _emit(args.json, "fail" if failures else "pass", failures, f"{len(index_rows)} dataset(s)")


def _selftest() -> int:
    rows = [{"data_id": "ds1", "sha256": "aaa"}]
    good = {"datasets": {"ds1": {"sha256": "aaa", "locked_by": "jiaming", "locked_at": "2026-06-14"}}}
    drifted = {"datasets": {"ds1": {"sha256": "bbb", "locked_by": "jiaming"}}}
    unlocked = {"datasets": {}}
    no_owner = {"datasets": {"ds1": {"sha256": "aaa"}}}
    cases = [
        ("matches lock -> pass", audit(rows, good) == [], True),
        ("missing lock file -> fail", audit(rows, None) != [], True),
        ("sha drift -> fail", any("drifted" in x for x in audit(rows, drifted)), True),
        ("dataset not locked -> fail", any("not in data.lock" in x for x in audit(rows, unlocked)), True),
        ("missing owner -> fail", any("locked_by" in x for x in audit(rows, no_owner)), True),
    ]
    res = all(got is want for _, got, want in cases)
    for name, got, want in cases:
        print(f"  [{'ok' if got is want else 'FAIL'}] {name}")
    print("SELFTEST PASS" if res else "SELFTEST FAIL")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(main())
