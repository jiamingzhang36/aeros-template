#!/usr/bin/env python3
"""Validate AEROS literature adapter plumbing and discovery artifacts."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path.cwd()
ADAPTER = ROOT / "aeros/runtime/literature_adapter.py"
CLI = ROOT / "aeros/cli.py"
POLICY = ROOT / "harness/econ_literature_discovery_policy.yml"
SEARCH_LOG = ROOT / "discovery/literature/search_log.csv"
REGISTRY = ROOT / "discovery/literature/paper_registry.csv"
SNOWBALL = ROOT / "discovery/literature/citation_snowball_queue.csv"
CITATION_AUDIT = ROOT / "discovery/literature/citation_audit.md"

SEARCH_COLUMNS = ["date", "agent", "source", "search_query", "results_found", "useful_results", "not_useful_results", "follow_up", "notes"]
REGISTRY_COLUMNS = ["paper_id", "citation_key", "title", "authors", "year", "source", "doi", "url", "pdf_url", "primary_function", "secondary_functions", "reading_depth", "status", "full_text_available", "opened_source", "opened_date", "evidence_basis", "screening_decision", "extraction_card", "used_in_synthesis", "notes"]
SNOWBALL_COLUMNS = ["queued_at", "source_paper_id", "related_locator", "relation", "source", "status", "notes"]
ALLOWED_SNOWBALL_STATUSES = {"candidate", "screened", "imported", "excluded", "deferred"}


def _header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    failures: list[str] = []
    for path in [ADAPTER, CLI, POLICY, SEARCH_LOG, REGISTRY, SNOWBALL, CITATION_AUDIT]:
        if not path.exists():
            failures.append(f"missing {path}")

    if ADAPTER.exists():
        text = ADAPTER.read_text(encoding="utf-8")
        for marker in ["OpenAlex", "ROUTE_READY", "does_not_prove", "citation_snowball_queue.csv"]:
            if marker not in text:
                failures.append(f"{ADAPTER}: missing adapter boundary marker {marker!r}")
    if CLI.exists() and "literature" not in CLI.read_text(encoding="utf-8"):
        failures.append(f"{CLI}: missing literature subcommand wiring")
    if POLICY.exists():
        policy = POLICY.read_text(encoding="utf-8")
        for marker in ["citation_faithfulness", "CiteCheck", "HalluCiteChecker", "DeepSciVerify"]:
            if marker not in policy:
                failures.append(f"{POLICY}: missing {marker}")

    for path, required in [(SEARCH_LOG, SEARCH_COLUMNS), (REGISTRY, REGISTRY_COLUMNS), (SNOWBALL, SNOWBALL_COLUMNS)]:
        header = _header(path)
        missing = [column for column in required if column not in header]
        if missing:
            failures.append(f"{path}: missing columns: {', '.join(missing)}")

    registry_rows = _rows(REGISTRY)
    ids = {row.get("paper_id", "").strip() for row in registry_rows if row.get("paper_id", "").strip()}
    for row in _rows(SNOWBALL):
        status = row.get("status", "").strip()
        if status and status not in ALLOWED_SNOWBALL_STATUSES:
            failures.append(f"{SNOWBALL}: invalid status {status!r}")
        source_pid = row.get("source_paper_id", "").strip()
        if source_pid and source_pid not in ids:
            failures.append(f"{SNOWBALL}: source_paper_id {source_pid!r} not in paper registry")

    if CITATION_AUDIT.exists():
        audit = CITATION_AUDIT.read_text(encoding="utf-8")
        for marker in ["Citation exists", "Metadata faithful", "Claim support checked", "Evidence level"]:
            if marker not in audit:
                failures.append(f"{CITATION_AUDIT}: missing faithfulness column {marker!r}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: literature adapter plumbing is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
