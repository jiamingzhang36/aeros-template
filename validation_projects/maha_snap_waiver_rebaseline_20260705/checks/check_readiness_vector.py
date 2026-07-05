#!/usr/bin/env python3
"""Validate the derived readiness vector."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import csv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.readiness import build_readiness_vector  # noqa: E402


REQUIRED_KEYS = {"data", "literature", "analysis", "claims", "paper", "compliance", "release"}


def main() -> int:
    failures: list[str] = []
    vector = build_readiness_vector(Path.cwd())
    readiness = vector.get("readiness") or {}
    missing = REQUIRED_KEYS - set(readiness)
    if missing:
        failures.append("readiness vector missing keys: " + ", ".join(sorted(missing)))
    if "does_not_prove" not in vector:
        failures.append("readiness vector missing does_not_prove")

    with tempfile.TemporaryDirectory(prefix="aeros_readiness_fixture_") as tmp:
        root = Path(tmp)
        registry = root / "discovery/literature/paper_registry.csv"
        registry.parent.mkdir(parents=True, exist_ok=True)
        with registry.open("w", newline="", encoding="utf-8") as handle:
            fields = ["paper_id", "status", "evidence_basis", "extraction_card", "notes"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow({"paper_id": "P_OK", "status": "extracted", "evidence_basis": "full_text", "extraction_card": "yes", "notes": ""})
            writer.writerow({"paper_id": "P_BLOCK", "status": "abstract_only", "evidence_basis": "abstract", "extraction_card": "no", "notes": "blocked_fulltext; remains abstract_only"})
        fixture = build_readiness_vector(root)
        if fixture.get("readiness", {}).get("literature") != "fulltext_partial_blocked":
            failures.append(
                "literature readiness should surface blockers even when some full text exists"
            )

    if failures:
        print("FAIL: readiness vector problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: readiness vector is derivable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
