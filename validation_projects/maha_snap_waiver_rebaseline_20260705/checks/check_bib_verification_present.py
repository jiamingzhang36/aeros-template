#!/usr/bin/env python3
"""HARD gate: a human-signed online bib-verification report covers every entry.

Pairs with the advisory `verify_bib_online.py` tool the same way
`check_referee_review_present` pairs with the referee panel: the tool does the
non-deterministic online work and emits `audits/bib_verification_report.md`; this
check hard-gates that the report

1. exists,
2. lists every key currently in `tex/references.bib` (no entry escaped review),
3. carries a filled `Verified-by:` sign-off (a human resolved the REVIEW / NOT
   FOUND rows -- confirmed the work, fixed the entry, or dropped the citation).

It does NOT itself hit the network. Stays quiet (passes) when there is no .bib
yet. Run `python checks/check_bib_verification_present.py --selftest`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BIB = Path("tex/references.bib")
REPORT = Path("audits/bib_verification_report.md")
CHECK_NAME = "check_bib_verification_present"
ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.I)
SIGNOFF_RE = re.compile(r"verified-by:\s*(.+)", re.I)
# chars that may legitimately appear inside a bibtex key; used to require that a
# key matches as a whole token in the report, not as a fragment of another word
# (e.g. key `b` must not be considered "covered" by the `b` inside "Verified-by")
_KEYCHAR = r"[A-Za-z0-9:_./+-]"
_PLACEHOLDER = ("<!--", "todo", "tbd", "name + date", "")


def _bib_keys(text: str) -> set[str]:
    return {m.group(2).strip() for m in ENTRY_RE.finditer(text)
            if m.group(1).lower() not in {"comment", "string", "preamble"}}


def _signed(report: str) -> bool:
    m = SIGNOFF_RE.search(report)
    if not m:
        return False
    val = m.group(1).strip()
    return bool(val) and not any(val.lower().startswith(p) or val.lower() == p
                                 for p in _PLACEHOLDER if p)


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: signed bib-verification report covers every entry{(' — ' + note) if note else ''}")
    else:
        print("FAIL: bibliography online-verification gate:")
        print("\n".join(failures))
        print("Run `python checks/verify_bib_online.py`, resolve REVIEW/NOT FOUND rows, "
              "then add a `Verified-by:` line to audits/bib_verification_report.md.")
    return 0 if status == "pass" else 1


def audit(bib_text: str, report_text: str | None) -> list[str]:
    keys = _bib_keys(bib_text)
    if report_text is None:
        return [f"missing {REPORT} (run checks/verify_bib_online.py)"]
    failures = []
    uncovered = sorted(k for k in keys if not re.search(
        rf"(?<!{_KEYCHAR}){re.escape(k)}(?!{_KEYCHAR})", report_text))
    if uncovered:
        failures.append(f"{len(uncovered)} bib key(s) not covered by the report: "
                        f"{', '.join(uncovered[:8])}{' …' if len(uncovered) > 8 else ''}")
    if not _signed(report_text):
        failures.append("report has no filled `Verified-by:` sign-off (human must resolve REVIEW/NOT FOUND rows)")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate the signed bib-verification report.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not BIB.exists():
        return _emit(args.json, "pass", [], "no references.bib yet")
    bib_text = BIB.read_text(encoding="utf-8", errors="ignore")
    report_text = REPORT.read_text(encoding="utf-8", errors="ignore") if REPORT.exists() else None
    failures = audit(bib_text, report_text)
    n = len(_bib_keys(bib_text))
    return _emit(args.json, "fail" if failures else "pass", failures, f"{n} bib key(s)")


def _selftest() -> int:
    bib = "@article{a,\n title={T},\n year={2020}\n}\n@book{b,\n title={U},\n year={2019}\n}\n"
    report_full = "a VERIFIED\nb VERIFIED\nVerified-by: Jiaming 2026-06-13\n"
    report_unsigned = "a VERIFIED\nb VERIFIED\nVerified-by: <!-- name + date -->\n"
    report_partial = "a VERIFIED\nVerified-by: Jiaming\n"
    cases = [
        ("covered + signed -> pass", audit(bib, report_full) == [], True),
        ("missing report -> fail", audit(bib, None) != [], True),
        ("unsigned -> fail", any("sign-off" in x for x in audit(bib, report_unsigned)), True),
        ("uncovered key -> fail", any("not covered" in x for x in audit(bib, report_partial)), True),
    ]
    ok = all(got is want for _, got, want in cases)
    for name, got, want in cases:
        print(f"  [{'ok' if got is want else 'FAIL'}] {name}")
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
