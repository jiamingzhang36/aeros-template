#!/usr/bin/env python3
"""HARD gate: every number asserted in a SIGNED claim (and the paper abstract)
traces to a registered result artifact.

Why this exists. The number-injection registry (`check_number_registry`) hard-
gates only the handful of `{{token}}` cells. `check_number_scan` sees the other
hundreds of hand-typed numbers but is advisory-only by design (a hard gate on a
full paper's numbers means alarm fatigue). That leaves the *highest-stakes*
numbers -- the ones inside a claim a human has SIGNED, and the abstract -- on the
honor system. A wrong headline count or coefficient there is a fatal,
retraction-class error, and nothing currently blocks it.

This check closes that narrow, high-signal slice as a HARD gate. It extracts the
numbers from signed claim rows in `evidence/claim_registry.md` (Approved is a
real signature, not `pending`) and from the paper abstract, and FAILS if any of
them does not trace -- within rounding tolerance -- to a value found in some
registered result artifact (`evidence/result_index.csv`) or a verified
number-injection value. Calendar years are excluded (they are dates, not
estimates). The check stays quiet (passes) when there is no signed claim, no
paper, or no registered artifact yet.

This is deliberately NARROW: it does not scan the whole paper (that is
`check_number_scan`). It only guards numbers a human has put their name behind.

Run `python checks/check_claim_numbers_bound.py --selftest` to self-verify.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.number_injection import (  # noqa: E402
    load_whitelist,
    matches,
    verified_values,
)

REGISTRY = Path("evidence/claim_registry.md")
PAPER_CANDIDATES = ("tex/paper.tex", "paper/draft.md")
CHECK_NAME = "check_claim_numbers_bound"

# A number with optional thousands commas, optional decimals, optional percent.
NUM_RE = re.compile(r"(?<![\w.])([-+]?\d[\d,]*(?:\.\d+)?\s*%?)(?![\w.])")
ASSERTED = {"supported", "ambiguous"}
_UNSIGNED_MARKERS = ("pending", "todo", "tbd", "n/a", "none")


def _registry_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 8 or cells[0].lower() in {"claim id", ""} or set(cells[0]) <= set("-: "):
            continue
        rows.append({
            "id": cells[0], "claim": cells[1], "type": cells[2].lower(),
            "status": cells[3].lower(), "approved": cells[7].lower(),
        })
    return rows


def _is_signed(approved: str) -> bool:
    a = approved.strip().lower()
    return bool(a) and not any(m in a for m in _UNSIGNED_MARKERS)


def candidate_numbers(text: str) -> list[str]:
    """Estimate-like numbers in prose: commas stripped, calendar years dropped."""
    out: list[str] = []
    for m in NUM_RE.finditer(text):
        tok = m.group(1).replace(" ", "")
        bare = tok.rstrip("%").replace(",", "")
        try:
            val = float(bare)
        except ValueError:
            continue
        is_int = "." not in bare
        is_pct = tok.endswith("%")
        if is_int and not is_pct and 1900 <= abs(val) <= 2099:
            continue  # calendar year (incl. en-dash range tails like 2019--2025)
        out.append(tok.replace(",", ""))
    return out


def _abstract(root: Path) -> str:
    for rel in PAPER_CANDIDATES:
        p = root / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, flags=re.S)
        if m:
            return m.group(1)
    return ""


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: every signed-claim/abstract number traces to a registered "
              f"artifact{(' — ' + note) if note else ''}")
    else:
        print("FAIL: signed-claim/abstract numbers that do not trace to any registered artifact:")
        print("\n".join(failures))
        print("Fix by registering the backing artifact in evidence/result_index.csv "
              "(or correcting the number); do not whitelist a real estimate.")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind signed-claim/abstract numbers to artifacts.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()

    root = Path.cwd()
    if not REGISTRY.exists():
        return _emit(args.json, "pass", [], "no claim registry yet")

    rows = _registry_rows(REGISTRY.read_text(encoding="utf-8"))
    signed = [r for r in rows if _is_signed(r["approved"]) and r["status"] in ASSERTED]
    abstract_text = _abstract(root)

    if not signed and not abstract_text.strip():
        return _emit(args.json, "pass", [], "no signed claim or abstract yet")

    verified = verified_values(root)
    if not verified:
        return _emit(args.json, "pass", [], "no registered result artifacts to trace against yet")
    whitelist = load_whitelist(root)

    sources: list[tuple[str, str]] = [(f"claim {r['id']}", r["claim"]) for r in signed]
    if abstract_text.strip():
        sources.append(("abstract", abstract_text))

    failures: list[str] = []
    checked = 0
    for label, text in sources:
        for tok in candidate_numbers(text):
            checked += 1
            if not matches(tok, verified, whitelist):
                failures.append(f"{label}: '{tok}' does not trace to any registered result artifact")

    note = f"{len(signed)} signed claim(s), {checked} number(s) checked"
    return _emit(args.json, "fail" if failures else "pass", failures, note)


def _selftest() -> int:
    """Prove the catch and the pass without touching the live project."""
    pool = [140.0, 38.0, 21748.0, 7272.0, 6.5, 0.017]
    wl: set[str] = set()
    cases = [
        ("traceable count 140", matches("140", pool, wl), True),
        ("traceable 21,748 (comma)", matches("21748", pool, wl), True),
        ("rounded 0.02 -> 0.017", matches("0.02", pool, wl), True),
        ("fabricated 999 caught", matches("999", pool, wl), False),
        ("fabricated 6.7 caught", matches("6.7", pool, wl), False),
    ]
    extract = candidate_numbers("140 bills across 38 states over 2019--2025; EPV approx 6.5")
    ok = True
    for name, got, want in cases:
        flag = "ok" if got is want else "FAIL"
        if got is not want:
            ok = False
        print(f"  [{flag}] {name}: got={got} want={want}")
    want_extract = ["140", "38", "6.5"]  # 2019, 2025 dropped as years
    flag = "ok" if extract == want_extract else "FAIL"
    if extract != want_extract:
        ok = False
    print(f"  [{flag}] year-stripping extract: got={extract} want={want_extract}")
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
