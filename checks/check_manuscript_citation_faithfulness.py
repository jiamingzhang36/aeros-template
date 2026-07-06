#!/usr/bin/env python3
"""Check sentence-level manuscript citation grounding.

This is stronger than bibliography existence: claim-bearing cited sentences must
map to a registry paper, a source-bound extraction card, and a human-approved
interpretation record. It still does not certify scientific truth.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.citation_sentence_grounding import build_sentence_citation_grounding  # noqa: E402


def _fixture_fail_then_pass() -> tuple[bool, list[str]]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_sentence_grounding_") as raw:
        root = Path(raw)
        (root / "tex").mkdir(parents=True)
        (root / "discovery/literature/extraction_cards").mkdir(parents=True)
        (root / "discovery/literature/interpretation_records").mkdir(parents=True)
        (root / "tex/paper.tex").write_text(
            "Background context follows \\citep{smith2020}. "
            "We find a significant policy effect on adoption \\citep{jones2021}.",
            encoding="utf-8",
        )
        (root / "discovery/literature/paper_registry.csv").write_text(
            "paper_id,citation_key,title,extraction_card\n"
            "P001,smith2020,Background,discovery/literature/extraction_cards/P001.md\n"
            "P002,jones2021,Claim,discovery/literature/extraction_cards/P002.md\n",
            encoding="utf-8",
        )
        (root / "discovery/literature/extraction_cards/P001.md").write_text("# P001\nBackground note only.\n", encoding="utf-8")
        (root / "discovery/literature/extraction_cards/P002.md").write_text(
            "# P002\n## Direct evidence\nSource passage: the study estimates a policy effect on adoption.\n",
            encoding="utf-8",
        )
        report = build_sentence_citation_grounding(root)
        if report.get("status") != "fail":
            failures.append("claim-bearing citation without interpretation record should fail")
        fail_rows = report.get("failures") or []
        if not fail_rows or fail_rows[0].get("citation_key") != "jones2021":
            failures.append("fixture did not identify the claim-bearing missing-interpretation row")
        sentence_id = fail_rows[0].get("sentence_id") if fail_rows else ""
        (root / f"discovery/literature/interpretation_records/{sentence_id}.yml").write_text(
            "human_status: approved\n"
            "review_verdict: faithful\n"
            "support_relation: direct_support\n"
            "source_passage: the study estimates a policy effect on adoption\n",
            encoding="utf-8",
        )
        fixed = build_sentence_citation_grounding(root)
        if fixed.get("status") != "pass":
            failures.append("approved faithful interpretation record should clear the claim-bearing citation")
    return not failures, failures


def main() -> int:
    fixture_ok, fixture_failures = _fixture_fail_then_pass()
    if not fixture_ok:
        print("FAIL: sentence-level citation grounding fixture failed")
        for failure in fixture_failures:
            print(f"- {failure}")
        return 1

    report = build_sentence_citation_grounding(ROOT)
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    failures = report.get("failures") or []
    if failures:
        print("FAIL: sentence-level manuscript citation grounding problems detected")
        for row in failures[:25]:
            print(
                f"- {row.get('sentence_id')} {row.get('manuscript_path')}:{row.get('line')} "
                f"cite={row.get('citation_key')} paper={row.get('mapped_paper_id') or '<unmapped>'} "
                f"type={row.get('claim_type')} support={row.get('support_status')}: "
                f"{row.get('required_action')}"
            )
        if len(failures) > 25:
            print(f"- ... {len(failures) - 25} more")
        return 1
    counts = report.get("counts") or {}
    if report.get("status") == "inactive":
        print("PASS: sentence-level citation grounding inactive; fixture proved blocking behavior")
    else:
        print(f"PASS: sentence-level citation grounding valid ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
