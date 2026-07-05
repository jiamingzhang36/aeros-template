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
            "We find a policy effect on outcomes @jones2021.",
            encoding="utf-8",
        )
        (tmp / "discovery/literature/paper_registry.csv").write_text(
            "paper_id,bib_key,title\n"
            "P001,smith2020,Background paper\n"
            "P002,jones2021,Claim paper\n",
            encoding="utf-8",
        )
        rows = build_citation_faithfulness_rows(tmp)
        by_key = {row.citation_key: row for row in rows}
        if by_key.get("smith2020") is None or by_key["smith2020"].blocking:
            failures.append("tier_0 bibliographic citation should not be blocking when registry-mapped")
        if by_key.get("smith2020") and by_key["smith2020"].citation_grounding_tier != "tier_0_bibliographic":
            failures.append("background citation fixture should be tier_0_bibliographic")
        if by_key.get("jones2021") is None or not by_key["jones2021"].blocking:
            failures.append("claim-bearing citation without support should be blocking")
        if by_key.get("jones2021") and by_key["jones2021"].citation_grounding_tier != "tier_2_claim_bearing":
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
