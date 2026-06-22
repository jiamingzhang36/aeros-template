#!/usr/bin/env python3
"""Validate parser benchmark scaffold."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


PATH = Path("harness/parser_benchmark.yml")
REQUIRED_BUCKETS = {"econ_pdf", "scanned_pdf", "tables", "appendix_formula", "policy_report", "html_working_paper"}
REQUIRED_METRICS = {"page_addressability", "table_recovery", "identity_match", "false_fulltext_rate", "parse_latency", "human_correction_minutes"}


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
    if failures:
        print("FAIL: parser benchmark scaffold problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: parser benchmark scaffold is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
