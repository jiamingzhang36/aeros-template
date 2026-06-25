#!/usr/bin/env python3
"""Validate parser benchmark scaffold and deterministic local fixtures."""

from __future__ import annotations

from pathlib import Path
import sys
from html.parser import HTMLParser

import yaml


PATH = Path("harness/parser_benchmark.yml")
REQUIRED_BUCKETS = {"econ_pdf", "scanned_pdf", "tables", "appendix_formula", "policy_report", "html_working_paper"}
REQUIRED_METRICS = {"page_addressability", "table_recovery", "identity_match", "false_fulltext_rate", "parse_latency", "human_correction_minutes"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        data = " ".join(data.split())
        if data:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def _exercise_fixture(case: dict) -> list[str]:
    failures: list[str] = []
    fixture_path = Path(str(case.get("path", "")).strip())
    case_id = str(case.get("id", "unnamed_case")).strip()
    if not fixture_path.exists():
        return [f"{case_id}: missing parser fixture {fixture_path}"]
    if fixture_path.suffix.lower() not in {".html", ".htm"}:
        return [f"{case_id}: v1 executable parser fixture must be HTML"]
    parser = _TextExtractor()
    parser.feed(fixture_path.read_text(encoding="utf-8"))
    text = parser.text
    if case.get("should_be_rejected"):
        for marker in case.get("expected_negative_markers") or []:
            marker = str(marker).strip()
            if marker and marker not in text:
                failures.append(f"{case_id}: parsed negative fixture missing marker {marker!r}")
        forbidden = str(case.get("forbidden_target_title", "")).strip()
        if forbidden and forbidden in text:
            failures.append(f"{case_id}: false-fulltext fixture contains forbidden target title")
        if len(text) < int(case.get("min_chars", 20)):
            failures.append(f"{case_id}: negative fixture text is too short to classify")
        return failures
    for field in ["expected_title", "expected_doi", "expected_table_text"]:
        expected = str(case.get(field, "")).strip()
        if expected and expected not in text:
            failures.append(f"{case_id}: parsed text missing {field}={expected!r}")
    if len(text) < int(case.get("min_chars", 100)):
        failures.append(f"{case_id}: parsed text is too short for page-addressable review")
    return failures


def main() -> int:
    if not PATH.exists():
        print(f"FAIL: missing {PATH}")
        return 1
    data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
    buckets = {item.get("bucket") for item in data.get("corpus_buckets", []) if isinstance(item, dict)}
    metrics = set(data.get("metrics") or [])
    failures: list[str] = []
    for bucket in sorted(REQUIRED_BUCKETS - buckets):
        failures.append(f"missing corpus bucket {bucket}")
    for metric in sorted(REQUIRED_METRICS - metrics):
        failures.append(f"missing metric {metric}")
    fixture_cases = [case for case in data.get("fixture_cases", []) if isinstance(case, dict)]
    if not fixture_cases:
        failures.append("missing fixture_cases")
    for case in fixture_cases:
        bucket = str(case.get("bucket", "")).strip()
        if bucket not in REQUIRED_BUCKETS:
            failures.append(f"{case.get('id', 'unnamed_case')}: invalid fixture bucket {bucket!r}")
        failures.extend(_exercise_fixture(case))
    if failures:
        print("FAIL: parser benchmark scaffold problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: parser benchmark scaffold is valid ({len(fixture_cases)} local fixture(s) executed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
