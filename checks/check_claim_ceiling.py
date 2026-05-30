#!/usr/bin/env python3
"""Enforce that no asserted claim exceeds the data-earned claim ceiling.

This is what gives the whole ratchet teeth: the earned_claim_ceiling produced by
`aeros adjudicate` (data prunes designs -> caps the claim) actually CONSTRAINS the
claim registry. An asserted claim (status supported/ambiguous) stronger than the
ceiling fails -- you cannot register a causal claim when the data only earned an
associational one. Draft/unsupported/retired claims are exempt (not yet asserted).
Skips when no adjudication exists yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

SELECTION = Path("discovery/design_selection.md")
REGISTRY = Path("evidence/claim_registry.md")
CHECK_NAME = "check_claim_ceiling"

# claim-type strength rank; the earned ceiling is one of the first four
STRENGTH = {
    "descriptive": 0, "measurement": 1, "associational": 2,
    "causal": 3, "mechanism": 3,
    "external-validity": 4, "policy-translation": 4, "forecast": 4,
}
ASSERTED = {"supported", "ambiguous"}


def _front_matter(path: Path) -> dict:
    t = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, flags=re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def _registry_rows() -> list[dict]:
    rows = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() in {"claim id", ""} or set(cells[0]) <= set("-: "):
            continue
        rows.append({"id": cells[0], "type": cells[2].lower(), "status": cells[3].lower()})
    return rows


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}))
    elif status == "pass":
        print(f"PASS: no asserted claim exceeds the earned ceiling{(' — ' + note) if note else ''}")
    else:
        print("FAIL: claims exceed the data-earned ceiling:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enforce the earned claim ceiling.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not SELECTION.exists():
        return _emit(as_json, "pass", [], "no adjudication yet")
    if not REGISTRY.exists():
        return _emit(as_json, "fail", [f"missing {REGISTRY}"])

    fm = _front_matter(SELECTION)
    ceiling = str(fm.get("earned_claim_ceiling", "")).strip().lower()
    diag_status = str(fm.get("diagnostics_status", "stub")).strip().lower()
    if ceiling in {"", "none"}:
        return _emit(as_json, "pass", [], "no claim earned yet")
    ceiling_rank = STRENGTH.get(ceiling, 0)

    failures: list[str] = []
    for r in _registry_rows():
        if r["status"] not in ASSERTED:
            continue
        rank = STRENGTH.get(r["type"], 99)
        if rank > ceiling_rank:
            failures.append(
                f"{r['id']}: asserted '{r['type']}' exceeds earned ceiling '{ceiling}' "
                f"(data only earned {ceiling}); weaken the claim or earn it with data")

    note = f"ceiling={ceiling}"
    if diag_status != "measured":
        note += " (PROVISIONAL — diagnostics are stub; ceiling not yet earned on real data)"
    return _emit(as_json, "fail" if failures else "pass", failures, note)


if __name__ == "__main__":
    sys.exit(main())
