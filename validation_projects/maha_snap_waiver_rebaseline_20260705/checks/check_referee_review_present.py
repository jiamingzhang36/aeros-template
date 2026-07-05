#!/usr/bin/env python3
"""Require an on-file adversarial review before any claim is signed at the gate.

This is the "not hasty" mechanism made into a hard precondition: you cannot exit
the claim-audit gate (G7) with a SIGNED claim unless an adversarial referee review
artifact exists AND explicitly covers that claim. It is what stops a claim from
being approved before it has survived a documented attack.

A claim is "signed" when its `Approved` cell is non-empty and does not start with
`pending`. A referee review artifact is any `audits/*referee*.md` file. Coverage
is satisfied when the claim's ID (e.g. `C4`) appears in at least one such file.

Rationale for ID-coverage (not mtime): the act of signing edits the registry
*after* the review is written, so the registry is always newer than the review at
sign time — an mtime "staleness" rule would false-fail every legitimate sign-off.
Per-claim ID coverage gives real teeth (no signing a claim no referee even names)
without that fragility. When the ceiling or claim wording changes, the convention
is to write a fresh dated review (see audits/referee_panel_upgrade_*.md); a future
extension may fingerprint claim text to enforce that automatically.

Passes (skips) when there is no registry or nothing is signed yet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REGISTRY = Path("evidence/claim_registry.md")
REVIEW_GLOB = "audits/*referee*.md"
CHECK_NAME = "check_referee_review_present"


def _registry_rows() -> list[dict]:
    rows = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 8 or cells[0].lower() in {"claim id", ""} or set(cells[0]) <= set("-: "):
            continue
        rows.append({"id": cells[0], "status": cells[3].lower(), "approved": cells[7].strip()})
    return rows


def _is_signed(approved: str) -> bool:
    a = approved.lower()
    return bool(a) and not a.startswith("pending")


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}))
    elif status == "pass":
        print(f"PASS: every signed claim is covered by an on-file referee review"
              f"{(' — ' + note) if note else ''}")
    else:
        print("FAIL: signed claims lack a covering adversarial review:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Require an adversarial review before claim sign-off.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true", help="prove the check catches an uncovered signed claim")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not REGISTRY.exists():
        return _emit(args.json, "pass", [], "no claim registry yet")

    signed = [r for r in _registry_rows() if _is_signed(r["approved"])]
    if not signed:
        return _emit(args.json, "pass", [], "no signed claims yet")

    reviews = sorted(Path().glob(REVIEW_GLOB))
    if not reviews:
        ids = ", ".join(r["id"] for r in signed)
        return _emit(args.json, "fail",
                     [f"{len(signed)} signed claim(s) ({ids}) but no adversarial review found "
                      f"matching '{REVIEW_GLOB}'; a claim may not be signed before it survives a "
                      f"documented referee pass"])

    blob = "\n".join(p.read_text(encoding="utf-8") for p in reviews)
    failures = [
        f"{r['id']}: signed (Approved='{r['approved']}') but no referee review in "
        f"'{REVIEW_GLOB}' mentions it — run an adversarial pass covering {r['id']} before signing"
        for r in signed if r["id"] not in blob
    ]
    note = f"{len(signed)} signed; {len(reviews)} review file(s)"
    return _emit(args.json, "fail" if failures else "pass", failures, note)


def _selftest() -> int:
    import tempfile, os
    ok = True
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        try:
            os.chdir(d)
            (Path("evidence")).mkdir()
            (Path("audits")).mkdir()
            reg = (
                "| Claim ID | Claim | Type | Status | Evidence ID(s) | Result ID(s) | Boundary / Limitation | Approved |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| C1 | x | associational | Supported | EV1 | R1 | b | jiaming (2026-06-13) |\n"
                "| C2 | y | descriptive | Supported | EV1 | R2 | b | pending (author review) |\n"
            )
            Path("evidence/claim_registry.md").write_text(reg, encoding="utf-8")
            # no review yet -> must FAIL on signed C1
            rc1 = main([])
            # add a review that covers C1 -> must PASS
            Path("audits/referee_panel_report.md").write_text("review of C1 ...", encoding="utf-8")
            rc2 = main([])
            ok = (rc1 == 1) and (rc2 == 0)
            print(f"selftest: no-review->fail={rc1==1}, covered->pass={rc2==0} => {'OK' if ok else 'BROKEN'}")
        finally:
            os.chdir(cwd)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
