#!/usr/bin/env python3
"""Check sentence-level manuscript citation grounding.

This is stronger than bibliography existence: cited sentences must declare an
inferred citation function, and function-specific evidence requirements decide
whether registry metadata, extraction cards, source passages, or approved
interpretation records are required. It still does not certify scientific truth.
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
        (root / "harness").mkdir(parents=True)
        (root / "discovery/literature/extraction_cards").mkdir(parents=True)
        (root / "discovery/literature/interpretation_records").mkdir(parents=True)
        (root / "harness/citation_function_requirements.yml").write_text(
            (ROOT / "harness/citation_function_requirements.yml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (root / "tex/paper.tex").write_text(
            r"Smith (2020) is a prior study \citep{smith2020}. "
            r"We find a significant policy effect on adoption \citep{jones2021}. "
            r"The program cost $1.6 billion \citep{moran2025}.",
            encoding="utf-8",
        )
        (root / "discovery/literature/paper_registry.csv").write_text(
            "paper_id,citation_key,title,full_text_available,extraction_card\n"
            "P001,smith2020,Background,no,\n"
            "P002,jones2021,Claim,yes,discovery/literature/extraction_cards/P002.md\n"
            "P003,moran2025,Number,abstract_only,\n",
            encoding="utf-8",
        )
        (root / "discovery/literature/extraction_cards/P002.md").write_text(
            "# P002\n"
            "## Direct evidence\n"
            "Source passage: the study estimates a policy effect on adoption.\n",
            encoding="utf-8",
        )
        report = build_sentence_citation_grounding(root)
        if report.get("status") != "fail":
            failures.append("claim/number-bearing citations without required evidence should fail")
        fail_rows = report.get("failures") or []
        statuses = {row.get("citation_key"): row.get("support_status") for row in fail_rows}
        if statuses.get("jones2021") != "missing_interpretation":
            failures.append("fixture did not identify claim-bearing missing-interpretation row")
        if statuses.get("moran2025") != "abstract_only_too_strong":
            failures.append("abstract-only number_fact should fail as abstract_only_too_strong")
        if any(row.get("citation_key") == "smith2020" and row.get("blocking") for row in report.get("rows") or []):
            failures.append("metadata/background citation should not block without full text")
        sentence_id = next((row.get("sentence_id") for row in fail_rows if row.get("citation_key") == "jones2021"), "")
        (root / f"discovery/literature/interpretation_records/{sentence_id}.yml").write_text(
            "human_status: approved\n"
            "review_verdict: faithful\n"
            "support_relation: direct_support\n"
            "source_passage: the study estimates a policy effect on adoption\n",
            encoding="utf-8",
        )
        fixed = build_sentence_citation_grounding(root)
        remaining = {row.get("citation_key") for row in fixed.get("failures") or []}
        if "jones2021" in remaining:
            failures.append("approved faithful interpretation record should clear the result_claim citation")
        if "moran2025" not in remaining:
            failures.append("number_fact should still fail until full source-passage grounding exists")
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
                f"function={row.get('citation_function')} required={row.get('required_evidence')} "
                f"support={row.get('support_status')}: {row.get('required_action')}"
            )
        if len(failures) > 25:
            print(f"- ... {len(failures) - 25} more")
        return 1
    counts = report.get("counts") or {}
    if report.get("status") == "inactive":
        print("PASS: sentence-level citation grounding inactive; fixture proved function-requirement blocking behavior")
    else:
        print(f"PASS: sentence-level citation grounding valid ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
