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
            "paper_id,citation_key,title,full_text_available,extraction_card,citation_function\n"
            "P001,smith2020,Background,no,,related_literature\n"
            "P002,jones2021,Claim,yes,discovery/literature/extraction_cards/P002.md,related_literature\n"
            "P003,moran2025,Number,abstract_only,,related_literature\n",
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
        functions = {row.get("citation_key"): row.get("citation_function") for row in report.get("rows") or []}
        if functions.get("jones2021") != "result_claim":
            failures.append("sentence-level result claim should override registry related_literature label")
        if functions.get("moran2025") != "number_fact":
            failures.append("sentence-level number fact should override registry related_literature label")
        if any(row.get("citation_key") == "smith2020" and row.get("blocking") for row in report.get("rows") or []):
            failures.append("metadata/background citation should not block without full text")

        (root / "tex/paper.tex").write_text(
            r"Prior work studies consumer acceptance and regulatory framing \citep{johnson2025future}. "
            r"Because the EPV ratio is 8.1, we use Firth's penalized-likelihood logit \citep{firth1993}. "
            r"A bounded method reference is allowed only as method background \citep{cameron2008}. "
            r"Replacing the ideology measure with Shor--McCarty scores yields similar estimates \citep{shor2011}. "
            r"We test the reflection hypothesis by adding a year trend \citep{manski1993}.",
            encoding="utf-8",
        )
        (root / "discovery/literature/paper_registry.csv").write_text(
            "paper_id,citation_key,title,primary_function,full_text_available,extraction_card,citation_function,support_route_note\n"
            "P004,johnson2025future,Framing,gap-verification,yes,discovery/literature/extraction_cards/P004.md,related_literature,\n"
            "P005,firth1993,Firth,method-identification,yes,discovery/literature/extraction_cards/P005.md,related_literature,\n"
            "P006,cameron2008,Bootstrap,method-identification,no,,related_literature,Bounded method/theory/data reference only; does not support empirical CMPD claim\n"
            "P007,shor2011,Ideological Mapping,data-measurement,no,,related_literature,Bounded method/theory/data reference only; does not support empirical CMPD claim\n"
            "P008,manski1993,Reflection Problem,method-identification,no,,related_literature,Bounded method/theory/data reference only; does not support empirical CMPD claim\n",
            encoding="utf-8",
        )
        (root / "discovery/literature/extraction_cards/P004.md").write_text(
            "# P004\nSource passage: regulatory framing appears in public debates.\n",
            encoding="utf-8",
        )
        (root / "discovery/literature/extraction_cards/P005.md").write_text(
            "# P005\nSource passage: Firth penalized likelihood reduces small-sample bias.\n",
            encoding="utf-8",
        )
        routed = build_sentence_citation_grounding(root)
        routed_functions = {row.get("citation_key"): row.get("citation_function") for row in routed.get("rows") or []}
        if routed_functions.get("johnson2025future") == "number_fact":
            failures.append("citation-key years must not turn related-literature sentences into number_fact")
        if routed_functions.get("johnson2025future") != "related_literature":
            failures.append("related-literature sentence with citation-key digits should stay related_literature")
        if routed_functions.get("firth1993") != "method_precedent":
            failures.append("method sentence with EPV/table-like numbers should route to method_precedent")
        if routed_functions.get("shor2011") != "data_source":
            failures.append("measurement-score citation should route to data_source even when sentence reports own estimates")
        if routed_functions.get("manski1993") != "method_precedent":
            failures.append("reflection-hypothesis citation should route to method_precedent even when sentence says test")
        routed_statuses = {row.get("citation_key"): row.get("support_status") for row in routed.get("rows") or []}
        if routed_statuses.get("cameron2008") != "route_admission_ok":
            failures.append("bounded method route admission should pass without pretending full-text support")

        tier1_sentence = r"Because the EPV ratio is 8.1, we use Firth's penalized-likelihood logit \citep{firth1993}."
        (root / "discovery/literature/interpretation_records/canonical_tier1.json").write_text(
            json.dumps(
                {
                    "sentence_id": "S_CANONICAL_TIER1",
                    "manuscript_path": "tex/paper.tex",
                    "manuscript_sentence": tier1_sentence,
                    "citation_key": "firth1993",
                    "paper_id": "P005",
                    "citation_grounding_tier": "tier_1_interpretive",
                    "producer": "fixture-producer",
                    "source_passage": {
                        "page_or_section": "p. 27, Method",
                        "quote_or_paraphrase_basis": "Firth penalized likelihood reduces small-sample bias.",
                    },
                    "our_interpretation": "The passage supports the bounded method precedent.",
                    "support_relation": "direct_support",
                    "review_verdict": "faithful",
                    "human_status": "pending",
                    "automated_verification": {
                        "verifier": "fixture-passage-checker",
                        "verified_at": "2026-07-13",
                        "confidence": "medium",
                        "verdict": "faithful",
                    },
                }
            ),
            encoding="utf-8",
        )
        tier1_fixed = build_sentence_citation_grounding(root)
        tier1_row = next((row for row in tier1_fixed.get("rows") or [] if row.get("citation_key") == "firth1993"), {})
        if tier1_row.get("blocking") or tier1_row.get("support_status") != "grounded":
            failures.append("canonical Tier-1 record with medium automated verification did not satisfy method grounding")
        if not str(tier1_row.get("interpretation_record") or "").endswith("canonical_tier1.json"):
            failures.append("legacy sentence grounding did not resolve canonical record by manuscript content")

        (root / "tex/paper.tex").write_text(
            r"Smith (2020) is a prior study \citep{smith2020}. "
            r"We find a significant policy effect on adoption \citep{jones2021}. "
            r"The program cost $1.6 billion \citep{moran2025}.",
            encoding="utf-8",
        )
        (root / "discovery/literature/paper_registry.csv").write_text(
            "paper_id,citation_key,title,full_text_available,extraction_card,citation_function\n"
            "P001,smith2020,Background,no,,related_literature\n"
            "P002,jones2021,Claim,yes,discovery/literature/extraction_cards/P002.md,related_literature\n"
            "P003,moran2025,Number,abstract_only,,related_literature\n",
            encoding="utf-8",
        )
        sentence_id = next((row.get("sentence_id") for row in fail_rows if row.get("citation_key") == "jones2021"), "")
        result_record_path = root / f"discovery/literature/interpretation_records/{sentence_id}.yml"
        result_record_path.write_text(
            json.dumps(
                {
                    "citation_grounding_tier": "tier_2_claim_bearing",
                    "human_status": "pending",
                    "review_verdict": "faithful",
                    "support_relation": "direct_support",
                    "source_passage": "the study estimates a policy effect on adoption",
                    "automated_verification": {
                        "verifier": "fixture-passage-checker",
                        "verified_at": "2026-07-13",
                        "confidence": "high",
                        "verdict": "faithful",
                    },
                }
            ),
            encoding="utf-8",
        )
        auto_only = build_sentence_citation_grounding(root)
        if not any(row.get("citation_key") == "jones2021" for row in auto_only.get("failures") or []):
            failures.append("Tier-2 result claim passed with automation but without human approval")
        result_record_path.write_text(
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
