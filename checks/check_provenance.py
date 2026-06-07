#!/usr/bin/env python3
"""Validate provenance JSON and paper result-id references."""

from __future__ import annotations

import csv
import json
import hashlib
import re
from pathlib import Path


RESULT_INDEX = Path("evidence/result_index.csv")
PROVENANCE_DIR = Path("outputs/.provenance")
PAPER_DIR = Path("paper")


def _collect_provenance_records() -> dict[str, dict]:
    if not PROVENANCE_DIR.exists():
        return {}
    records: dict[str, dict] = {}
    for path in sorted(PROVENANCE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        result_id = str(payload.get("result_id", "")).strip()
        if not result_id:
            continue
        records[result_id] = payload
    return records


def _load_result_index() -> dict[str, dict]:
    if not RESULT_INDEX.exists():
        return {}
    entries: dict[str, dict] = {}
    with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            result_id = str(row.get("result_id", "")).strip()
            if result_id:
                entries[result_id] = row
    return entries


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _collect_paper_result_ids() -> set[str]:
    if not PAPER_DIR.exists():
        return set()
    refs: set[str] = set()
    for path in PAPER_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".tex", ".qmd", ".Rmd"}:
            continue
        text = path.read_text(encoding="utf-8")
        refs.update(re.findall(r"\bR(?:_[A-Z]+)*_?\d{2,}\b", text))
    return refs


def main() -> int:
    provenance = _collect_provenance_records()
    index = _load_result_index()

    failures: list[str] = []

    for result_id, row in index.items():
        if result_id not in provenance:
            failures.append(f"{result_id}: in result_index but missing provenance JSON")
        else:
            output_path = Path(row.get("path", "")).expanduser()
            if output_path and not output_path.exists():
                failures.append(f"{result_id}: registered path does not exist: {row.get('path')}")

    for result_id, record in provenance.items():
        if result_id not in index:
            failures.append(f"{result_id}: provenance exists but not present in result_index.csv")
        for required in ("output_path", "created_at", "script_or_source", "sha256"):
            if not str(record.get(required, "")).strip():
                failures.append(f"{result_id}: provenance missing required field '{required}'")

        output_file = Path(record.get("output_path", ""))
        if str(output_file):
            if not output_file.exists():
                failures.append(f"{result_id}: output_path does not exist: {output_file}")
                continue
            actual = _sha256(output_file)
            expected = str(record.get("sha256", "")).strip().lower()
            if not expected:
                continue
            if len(expected) != 64 or not all(c in "0123456789abcdef" for c in expected):
                failures.append(f"{result_id}: malformed sha256 '{record.get('sha256')}'")
            elif actual != expected:
                failures.append(f"{result_id}: provenance sha256 mismatch for {output_file}")

    paper_refs = _collect_paper_result_ids()
    for ref in sorted(paper_refs):
        if ref not in provenance:
            failures.append(f"{ref}: referenced in paper files but provenance JSON not found")

    if failures:
        print("FAIL: provenance checks failed:")
        print("\n".join(failures))
        return 1

    print(
        "PASS: provenance and result_id references are consistent ("
        f"{len(index)} indexed / {len(provenance)} provenance records)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
