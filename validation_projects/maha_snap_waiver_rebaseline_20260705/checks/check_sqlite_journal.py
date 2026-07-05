#!/usr/bin/env python3
"""Validate the SQLite journal as a derived index, not a truth source."""

from __future__ import annotations

import csv
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.sqlite_journal import build_sqlite_journal  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_sqlite_journal_") as tmp:
        root = Path(tmp)
        _write(root / "project_manifest.yml", "name: fixture\n")
        (root / "evidence").mkdir()
        with (root / "evidence/result_index.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["result_id", "output_type", "path", "script_or_source", "description", "created_date", "linked_claims", "notes"])
            writer.writeheader()
            writer.writerow({"result_id": "R_FIX_001", "output_type": "table", "path": "outputs/table.csv", "script_or_source": "code/run.py", "description": "fixture", "created_date": "2026-06-23", "linked_claims": "C_FIX", "notes": ""})
        _write(root / "outputs/.provenance/R_FIX_001.json", '{"result_id":"R_FIX_001","artifact_path":"outputs/table.csv","sha256":"abc"}\n')
        _write(root / "evidence/evidence_units/EU_FIX.yml", "evidence_unit_id: EU_FIX\nmachine_status: locator_verified\nadmission_status: not_admitted\nclaim_effect: none\n")
        _write(root / "events/event_log.jsonl", '{"event_id":"EV_FIX","event_type":"fixture","action":"build"}\n')
        before = {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file()}
        dry = build_sqlite_journal(root, dry_run=True)
        if dry.status != "DRY_RUN" or (root / dry.output_path).exists():
            failures.append("dry-run wrote a SQLite journal or returned wrong status")
        report = build_sqlite_journal(root)
        db_path = root / report.output_path
        if report.status != "PASS" or not db_path.exists():
            failures.append("journal build did not create expected sqlite output")
        after = {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file() and path.suffix != ".sqlite"}
        for rel, text in before.items():
            if after.get(rel) != text:
                failures.append(f"source file mutated during journal build: {rel}")
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                authority = conn.execute("SELECT value FROM journal_metadata WHERE key='authority'").fetchone()
                result_count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
                unit_count = conn.execute("SELECT COUNT(*) FROM evidence_units").fetchone()[0]
                event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            finally:
                conn.close()
            if not authority or authority[0] != "derived_index_only":
                failures.append("journal metadata does not mark derived_index_only authority")
            if (result_count, unit_count, event_count) != (1, 1, 1):
                failures.append(f"unexpected journal row counts: results={result_count}, evidence_units={unit_count}, events={event_count}")

    if failures:
        print("FAIL: SQLite journal problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: SQLite journal derived index is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
