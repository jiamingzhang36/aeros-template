#!/usr/bin/env python3
"""Exercise the source-grounded manuscript fact-check vertical slice."""

from __future__ import annotations

import csv
import hashlib
import tempfile
from pathlib import Path

import yaml

from aeros.runtime.citation_sentence_grounding import build_sentence_citation_grounding
from aeros.runtime.grounded_fact_check import build_grounded_fact_check, write_grounded_fact_check


def _write_registry(root: Path, rows: list[dict[str, str]]) -> None:
    path = root / "discovery/literature/paper_registry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["paper_id", "bib_key", "title", "citation_function", "full_text_available", "extraction_card", "source_or_path"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_grounded_fact_check_") as name:
        root = Path(name)
        (root / "harness").mkdir()
        (root / "harness/citation_function_requirements.yml").write_text(
            (Path(__file__).resolve().parents[1] / "harness/citation_function_requirements.yml").read_text(encoding="utf-8"), encoding="utf-8"
        )
        (root / "tex").mkdir()
        manuscript = "The estimator uses clustered standard errors \\citep{method2024}.\nThe policy increased employment by 10 percent \\citep{result2024}.\n"
        (root / "tex/paper.tex").write_text(manuscript, encoding="utf-8")
        (root / "sources").mkdir()
        method_text = "The estimator uses clustered standard errors in every specification."
        result_text = "The policy increased employment by 10 percent in the preferred sample."
        (root / "sources/method.txt").write_text(method_text, encoding="utf-8")
        (root / "sources/result.txt").write_text(result_text, encoding="utf-8")
        (root / "discovery/literature/extraction_cards").mkdir(parents=True)
        for paper_id in ("P_METHOD", "P_RESULT"):
            (root / f"discovery/literature/extraction_cards/{paper_id}.md").write_text(
                "# Source passage\nDirect evidence supports the registered use.\n" + ("evidence " * 220), encoding="utf-8"
            )
        _write_registry(root, [
            {"paper_id": "P_METHOD", "bib_key": "method2024", "title": "Method", "citation_function": "method_precedent", "full_text_available": "yes", "extraction_card": "yes", "source_or_path": "sources/method.txt"},
            {"paper_id": "P_RESULT", "bib_key": "result2024", "title": "Result", "citation_function": "result_claim", "full_text_available": "yes", "extraction_card": "yes", "source_or_path": "sources/result.txt"},
        ])
        initial = build_sentence_citation_grounding(root)
        (root / "discovery/literature/interpretation_records").mkdir(parents=True)
        source_hash = hashlib.sha256((root / "sources/result.txt").read_bytes()).hexdigest()
        for row in initial["rows"]:
            is_result = row["citation_key"] == "result2024"
            passage = result_text if is_result else method_text
            record = {
                "sentence_id": row["sentence_id"], "manuscript_path": row["manuscript_path"],
                "manuscript_sentence": row["manuscript_sentence"], "citation_key": row["citation_key"],
                "paper_id": row["mapped_paper_id"], "citation_grounding_tier": "tier_2_claim_bearing" if is_result else "tier_1_interpretive",
                "source_passage": {"page_or_section": "p. 1", "quote_or_paraphrase_basis": passage},
                "our_interpretation": "The source directly supports the bounded sentence.",
                "support_relation": "direct_support", "scope_match": {"population": "match", "treatment": "match", "outcome": "match", "time_period": "match", "estimand": "match"},
                "claim_strength_match": "pass", "overclaim_flags": [], "limitations_checked": True,
                "contradictory_evidence_checked": True, "review_verdict": "faithful",
                "human_status": "approved" if is_result else "pending",
                "reviewer": "human-reviewer" if is_result else "", "reviewed_at": "2026-08-04" if is_result else "",
                "producer": "producer-agent",
                "automated_verification": {"verifier": "passage-checker", "verified_at": "2026-08-04", "verdict": "faithful", "confidence": "high"},
            }
            if is_result:
                record["independent_verification"] = {"verifier": "independent-reviewer", "verified_at": "2026-08-04", "verdict": "faithful", "independent_of_producer": True, "source_fingerprint": f"sha256:{source_hash}"}
            (root / f"discovery/literature/interpretation_records/{row['sentence_id']}.yml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        report = build_grounded_fact_check(root, manuscript="tex/paper.tex")
        if report["status"] != "PASS" or report["counts"]["VERIFIED"] != 2:
            failures.append(f"exact Tier-1 and independently verified Tier-2 passages should pass: {report['counts']}")
        (root / "sources/result.txt").write_text("The result source changed and no longer contains the passage.", encoding="utf-8")
        stale = build_grounded_fact_check(root, manuscript="tex/paper.tex")
        result = next(row for row in stale["rows"] if row["citation_key"] == "result2024")
        if result["fact_check_status"] != "UNRESOLVED":
            failures.append("a stale/missing Tier-2 passage must become UNRESOLVED")
        written = write_grounded_fact_check(root, stale)
        if not (root / written["report"]).is_file() or not (root / written["human_queue"]).is_file():
            failures.append("fact-check report and human queue were not written")
        if (root / "evidence/claim_registry.md").exists():
            failures.append("fact checking must not mint or modify claim authority")
    if failures:
        print("FAIL: grounded fact-check problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: grounded fact check verifies exact passages and routes stale Tier-2 evidence to human review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
