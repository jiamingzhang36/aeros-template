#!/usr/bin/env python3
"""Validate AEROS literature adapter plumbing and discovery artifacts."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from aeros.runtime import literature_adapter as adapter  # noqa: E402

ADAPTER = ROOT / "aeros/runtime/literature_adapter.py"
CLI = ROOT / "aeros/cli.py"
POLICY = ROOT / "harness/econ_literature_discovery_policy.yml"
SEARCH_LOG = ROOT / "discovery/literature/search_log.csv"
REGISTRY = ROOT / "discovery/literature/paper_registry.csv"
SNOWBALL = ROOT / "discovery/literature/citation_snowball_queue.csv"
FULLTEXT_READY = ROOT / "discovery/literature/fulltext_ready_queue.csv"
MISSING_FULLTEXT = ROOT / "discovery/literature/missing_fulltext_queue.csv"
CITATION_AUDIT = ROOT / "discovery/literature/citation_audit.md"

SEARCH_COLUMNS = ["date", "agent", "source", "search_query", "results_found", "useful_results", "not_useful_results", "follow_up", "notes"]
REGISTRY_COLUMNS = ["paper_id", "citation_key", "title", "authors", "year", "source", "doi", "url", "pdf_url", "primary_function", "secondary_functions", "reading_depth", "status", "full_text_available", "opened_source", "opened_date", "evidence_basis", "screening_decision", "extraction_card", "used_in_synthesis", "notes"]
SNOWBALL_COLUMNS = ["queued_at", "source_paper_id", "related_locator", "relation", "source", "status", "notes"]
FULLTEXT_READY_COLUMNS = ["queued_at", "paper_id", "zotero_item_key", "zotero_attachment_key", "title", "availability", "indexed_fulltext_chars", "pdf_path_or_url", "status", "next_action", "notes"]
MISSING_FULLTEXT_COLUMNS = ["queued_at", "paper_id", "zotero_item_key", "title", "reason", "status", "next_action", "notes"]
ALLOWED_SNOWBALL_STATUSES = {"candidate", "screened", "imported", "excluded", "deferred"}
ALLOWED_READY_STATUSES = {"ready_for_extraction", "needs_verification", "extracted", "deferred"}
ALLOWED_MISSING_STATUSES = {"missing_fulltext", "resolved", "unavailable", "deferred"}
ALLOWED_FULLTEXT_AVAILABILITY = {"indexed_fulltext", "pdf_attachment_only", "candidate_url_unverified"}


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
    for path in [ADAPTER, CLI, POLICY, SEARCH_LOG, REGISTRY, SNOWBALL, FULLTEXT_READY, MISSING_FULLTEXT, CITATION_AUDIT]:
        if not path.exists():
            failures.append(f"missing {path}")

    if ADAPTER.exists():
        text = ADAPTER.read_text(encoding="utf-8")
        for marker in [
            "OpenAlex",
            "Zotero",
            "ROUTE_READY",
            "does_not_prove",
            "citation_snowball_queue.csv",
            "fulltext_ready_queue.csv",
            "missing_fulltext_queue.csv",
            "candidate_url_unverified",
            "security_challenge",
            "cache_mismatch",
            "verify_fulltext_candidate_content",
        ]:
            if marker not in text:
                failures.append(f"{ADAPTER}: missing adapter boundary marker {marker!r}")
    if CLI.exists():
        cli_text = CLI.read_text(encoding="utf-8")
        for marker in ["literature", "zotero", "zotero-base-url"]:
            if marker not in cli_text:
                failures.append(f"{CLI}: missing literature/Zotero subcommand wiring marker {marker!r}")
    if POLICY.exists():
        policy = POLICY.read_text(encoding="utf-8")
        for marker in ["citation_faithfulness", "CiteCheck", "HalluCiteChecker", "DeepSciVerify"]:
            if marker not in policy:
                failures.append(f"{POLICY}: missing {marker}")

    for path, required in [
        (SEARCH_LOG, SEARCH_COLUMNS),
        (REGISTRY, REGISTRY_COLUMNS),
        (SNOWBALL, SNOWBALL_COLUMNS),
        (FULLTEXT_READY, FULLTEXT_READY_COLUMNS),
        (MISSING_FULLTEXT, MISSING_FULLTEXT_COLUMNS),
    ]:
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
    for row in _rows(FULLTEXT_READY):
        paper_id = row.get("paper_id", "").strip()
        if paper_id and paper_id not in ids:
            failures.append(f"{FULLTEXT_READY}: paper_id {paper_id!r} not in paper registry")
        status = row.get("status", "").strip()
        if status and status not in ALLOWED_READY_STATUSES:
            failures.append(f"{FULLTEXT_READY}: invalid status {status!r}")
        availability = row.get("availability", "").strip()
        if availability and availability not in ALLOWED_FULLTEXT_AVAILABILITY:
            failures.append(f"{FULLTEXT_READY}: invalid availability {availability!r}")
        if availability == "candidate_url_unverified" and status != "needs_verification":
            failures.append(f"{FULLTEXT_READY}: candidate_url_unverified rows must stay needs_verification")
        if availability == "pdf_attachment_only" and "ocr" not in row.get("notes", "").lower() and "parse" not in row.get("notes", "").lower():
            failures.append(f"{FULLTEXT_READY}: pdf_attachment_only rows must mention parse/OCR before extraction")
        if availability == "candidate_url_unverified":
            note = row.get("notes", "").lower() + " " + row.get("next_action", "").lower()
            for marker in ["verification", "metadata"]:
                if marker not in note:
                    failures.append(f"{FULLTEXT_READY}: candidate URL rows must state {marker} boundary")
        forbidden_notes = ["supports claims", "proves claim", "synthesis complete", "extraction complete"]
        note = row.get("notes", "").lower()
        if row.get("status", "").strip() == "ready_for_extraction" and any(term in note for term in forbidden_notes):
            failures.append(f"{FULLTEXT_READY}: ready queue must not claim completed evidence")
    for row in _rows(MISSING_FULLTEXT):
        paper_id = row.get("paper_id", "").strip()
        if paper_id and paper_id not in ids:
            failures.append(f"{MISSING_FULLTEXT}: paper_id {paper_id!r} not in paper registry")
        status = row.get("status", "").strip()
        if status and status not in ALLOWED_MISSING_STATUSES:
            failures.append(f"{MISSING_FULLTEXT}: invalid status {status!r}")

    if adapter._year_from_date("Spring 2024") != "2024":
        failures.append("_year_from_date must parse season/non-ISO dates")
    if adapter._year_from_date("2023-11-05") != "2023":
        failures.append("_year_from_date must parse ISO-like dates")
    creators = adapter._zotero_creators({
        "creators": [
            {"firstName": "Ada", "lastName": "Lovelace"},
            {"name": "Research Collective"},
        ]
    })
    if creators != "Ada Lovelace; Research Collective":
        failures.append(f"_zotero_creators fixture mismatch: {creators!r}")
    original_get = adapter._zotero_api_get
    try:
        def fake_get(_base_url: str, path: str):  # noqa: ANN001
            if path.endswith("/children"):
                return [
                    {"key": "NOTE1", "data": {"itemType": "note", "title": "not a pdf"}},
                    {"key": "PDF1", "data": {"itemType": "attachment", "title": "paper.pdf", "contentType": "application/pdf"}},
                ]
            if path.endswith("/fulltext"):
                return {"content": "indexed text"}
            if path.endswith("/file/view/url"):
                return "file:///tmp/paper.pdf"
            return {}
        adapter._zotero_api_get = fake_get
        info = adapter._zotero_attachment_info("http://127.0.0.1:23119", "ITEM1")
    finally:
        adapter._zotero_api_get = original_get
    if info.get("availability") != "indexed_fulltext" or info.get("indexed_fulltext_chars") != "12":
        failures.append(f"_zotero_attachment_info indexed fixture mismatch: {info!r}")

    cloudflare = adapter.verify_fulltext_candidate_content(
        "<html><title>Just a moment...</title>Cloudflare checking your browser</html>",
        content_type="text/html",
        expected_title="Target economics paper",
        expected_doi="10.1234/example",
    )
    if cloudflare.get("verdict") != "blocked" or cloudflare.get("blocker_reason") != "security_challenge":
        failures.append(f"Cloudflare/security challenge fixture mismatch: {cloudflare!r}")
    shell = adapter.verify_fulltext_candidate_content(
        "<html><div id='app'></div><script src='bundle.js'></script></html>",
        content_type="text/html",
        expected_title="Target economics paper",
    )
    if shell.get("verdict") != "blocked" or shell.get("blocker_reason") != "spa_shell":
        failures.append(f"SPA shell fixture mismatch: {shell!r}")
    article = adapter.verify_fulltext_candidate_content(
        """
        <html><body><h1>SNAP work requirements increase mental health care use</h1>
        DOI: 10.1234/snap.2024. This article contains a long readable body.
        The study examines administrative burden, benefit access, labor supply,
        and health care utilization with enough repeated text to exceed the
        verifier length threshold for an article-like HTML document.
        """ + (" evidence" * 400) + "</body></html>",
        content_type="text/html",
        expected_title="SNAP work requirements increase mental health care use",
        expected_doi="10.1234/snap.2024",
    )
    if article.get("verdict") != "verified_article_html" or article.get("matched_by") not in {"doi", "title"}:
        failures.append(f"article HTML verifier fixture mismatch: {article!r}")

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
