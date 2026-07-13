#!/usr/bin/env python3
"""Require claim-bearing manuscript citation sentences to be grounded.

This check is deliberately tiered. Bibliographic pointers only need a registry
mapping. Interpretive citations produce non-blocking warnings. Claim-bearing
sentences are blocking until they have extraction support and an approved
interpretation record.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aeros.runtime.submission_driver import build_citation_faithfulness_rows  # noqa: E402


def _fixture_ok() -> tuple[bool, list[str]]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_citation_tier_") as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "paper").mkdir(parents=True)
        (tmp / "discovery/literature").mkdir(parents=True)
        (tmp / "paper/main.md").write_text(
            "For institutional background, see @smith2020. "
            "For a limited attribution, related evidence is discussed by @jones2021. "
            "We find a policy effect on outcomes @lee2022.",
            encoding="utf-8",
        )
        (tmp / "discovery/literature/paper_registry.csv").write_text(
            "paper_id,bib_key,title,citation_function,full_text_available,extraction_card\n"
            "P001,smith2020,Background paper,metadata_only,no,\n"
            "P002,jones2021,Interpretive paper,related_literature,yes,discovery/literature/extraction_cards/P002.md\n"
            "P003,lee2022,Claim paper,result_claim,yes,discovery/literature/extraction_cards/P003.md\n",
            encoding="utf-8",
        )
        cards = tmp / "discovery/literature/extraction_cards"
        cards.mkdir(parents=True)
        card_text = (
            "# Full-text extraction\n\n"
            "## Source passage\n\n"
            "The reported coefficient is positive in the stated sample.\n\n"
            "## What this paper can support\n\n"
            "The source supports the bounded attribution used in the cited sentence, "
            "subject to the stated sample and outcome definition.\n\n"
            "## Evidence notes\n\n"
            + ("The extraction remains limited to the reported design and population. " * 30)
        )
        (cards / "P002.md").write_text(card_text, encoding="utf-8")
        (cards / "P003.md").write_text(card_text, encoding="utf-8")
        initial = build_citation_faithfulness_rows(tmp)
        initial_by_key = {row.citation_key: row for row in initial}
        records = tmp / "discovery/literature/interpretation_records"
        records.mkdir(parents=True)

        def record(row, paper_id: str, tier: str, *, independent: bool) -> dict:
            payload = {
                "sentence_id": row.sentence_id,
                "manuscript_path": row.manuscript_path,
                "manuscript_sentence": row.manuscript_sentence,
                "citation_key": row.citation_key,
                "paper_id": paper_id,
                "citation_grounding_tier": tier,
                "producer": "producer-agent-a",
                "source_passage": {
                    "page_or_section": "p. 10, Results",
                    "quote_or_paraphrase_basis": "The reported coefficient is positive in the stated sample.",
                },
                "our_interpretation": "The passage supports only the bounded attribution in this sentence.",
                "support_relation": "direct_support",
                "scope_match": {key: "match" for key in ("geography", "population", "time_period", "method", "outcome")},
                "claim_strength_match": "pass",
                "mismatch_type": [],
                "overclaim_flags": [],
                "limitations_checked": True,
                "contradictory_evidence_checked": True,
                "review_verdict": "faithful",
                "human_status": "approved" if tier == "tier_2_claim_bearing" else "pending",
                "reviewer": "reviewer-human-a" if tier == "tier_2_claim_bearing" else "",
                "reviewed_at": "2026-07-13" if tier == "tier_2_claim_bearing" else "",
                "automated_verification": {
                    "verifier": "automated-passage-checker-v1",
                    "verified_at": "2026-07-13",
                    "confidence": "high",
                    "verdict": "faithful",
                },
            }
            if independent:
                payload["independent_verification"] = {
                    "verifier": "independent-reviewer-b",
                    "verified_at": "2026-07-13",
                    "independent_of_producer": True,
                    "source_fingerprint": "sha256:" + ("a" * 64),
                    "verdict": "faithful",
                }
            return payload

        tier1 = initial_by_key["jones2021"]
        tier2 = initial_by_key["lee2022"]
        (records / f"{tier1.sentence_id}.yml").write_text(
            yaml.safe_dump(record(tier1, "P002", "tier_1_interpretive", independent=False), sort_keys=False), encoding="utf-8"
        )
        (records / f"{tier2.sentence_id}.yml").write_text(
            yaml.safe_dump(record(tier2, "P003", "tier_2_claim_bearing", independent=False), sort_keys=False), encoding="utf-8"
        )
        without_independent = {row.citation_key: row for row in build_citation_faithfulness_rows(tmp)}
        if not without_independent["lee2022"].blocking or "independent" not in without_independent["lee2022"].notes:
            failures.append("tier_2 citation passed without an independent verifier")
        (records / f"{tier2.sentence_id}.yml").write_text(
            yaml.safe_dump(record(tier2, "P003", "tier_2_claim_bearing", independent=True), sort_keys=False), encoding="utf-8"
        )
        rows = build_citation_faithfulness_rows(tmp)
        by_key = {row.citation_key: row for row in rows}
        if by_key.get("smith2020") is None or by_key["smith2020"].blocking:
            failures.append("tier_0 bibliographic citation should not be blocking when registry-mapped")
        if by_key.get("smith2020") and by_key["smith2020"].citation_grounding_tier != "tier_0_bibliographic":
            failures.append("background citation fixture should be tier_0_bibliographic")
        if by_key.get("jones2021") is None or by_key["jones2021"].blocking or by_key["jones2021"].support_status != "faithful":
            failures.append("tier_1 automatic passage/locator/interpretation should pass at high confidence")
        if by_key.get("jones2021") and by_key["jones2021"].citation_grounding_tier != "tier_1_interpretive":
            failures.append("limited attribution fixture should be tier_1_interpretive")
        if by_key.get("lee2022") is None or by_key["lee2022"].blocking:
            failures.append("tier_2 citation with full text, human approval, and independent verifier should pass")
        if by_key.get("lee2022") and by_key["lee2022"].citation_grounding_tier != "tier_2_claim_bearing":
            failures.append("claim-bearing citation fixture should be tier_2_claim_bearing")
    return not failures, failures


def main() -> int:
    fixture_ok, fixture_failures = _fixture_ok()
    if not fixture_ok:
        print("FAIL: citation grounding tier fixture failed")
        for failure in fixture_failures:
            print(f"- {failure}")
        return 1

    rows = build_citation_faithfulness_rows(ROOT)
    if not rows:
        print("PASS: no manuscript citations found; citation interpretation check inactive; tier fixture passed")
        return 0
    failures = [row for row in rows if row.blocking]
    if failures:
        print("FAIL: manuscript citation grounding check failed")
        for row in failures[:25]:
            print(
                f"- {row.sentence_id} {row.manuscript_path} cite={row.citation_key} "
                f"paper={row.mapped_paper_id or '<unmapped>'} tier={row.citation_grounding_tier} "
                f"interpretation={row.interpretation_status} support={row.support_status} "
                f"mismatch={row.mismatch_type}: {row.required_action} ({row.notes})"
            )
        if len(failures) > 25:
            print(f"- ... {len(failures) - 25} more")
        return 1
    weak = [row for row in rows if row.support_status not in {"faithful", "bibliographic"}]
    print(f"PASS: {len(rows)} manuscript citation rows have no blocking claim-bearing grounding failures; weak={len(weak)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
