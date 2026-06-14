#!/usr/bin/env python3
"""HARD gate: the paper carries a substantive Data Availability Statement.

Most journals desk-reject a manuscript with no data/code availability statement.
This check confirms `tex/paper.tex` contains a labeled Data Availability
Statement (a `\\textbf{...}`, `\\section{...}`, or `\\paragraph{...}` form is all
fine) whose body is real prose, not a placeholder.

It does NOT judge whether the statement is *good* (that is the author's and the
journal's call) — only that one is present and non-empty, so it cannot silently
disappear or rot into a TODO between drafts. Stays quiet (passes) when there is
no `tex/paper.tex` yet (template-safe).

Run `python checks/check_data_availability_present.py --selftest`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PAPER = Path("tex/paper.tex")
CHECK_NAME = "check_data_availability_present"

# a *labeled* data-availability statement, not a passing mention in running text
DAS_RE = re.compile(
    r"data\s+availability\s+statement"
    r"|data\s+(?:and\s+code\s+)?availability\s*\}?\s*:"
    r"|availability\s+of\s+data\s+and\s+(?:code|materials)",
    re.I,
)
SECTION_RE = re.compile(r"\\(?:section|subsection|paragraph)\*?\{")
_PLACEHOLDER = ("todo", "tbd", "to be added", "to be completed", "to be provided",
                "forthcoming", "xxx", "<!--", "\\todo", "placeholder")
_MIN_CHARS = 40  # non-space chars of real content beyond the label


def _clean(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)  # drop LaTeX commands
    s = re.sub(r"[{}\\]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def audit(paper_text: str) -> list[str]:
    m = DAS_RE.search(paper_text)
    if not m:
        return ["no Data Availability Statement found in tex/paper.tex "
                "(expected a labeled 'Data Availability Statement')"]
    tail = paper_text[m.end():]
    cut = len(tail)
    sec = SECTION_RE.search(tail)
    if sec:
        cut = min(cut, sec.start())
    para = tail.find("\n\n")
    if para != -1:
        cut = min(cut, para)
    content = _clean(tail[:cut])
    low = content.lower()
    if any(p in low for p in _PLACEHOLDER):
        return ["Data Availability Statement is a placeholder "
                "(contains TODO/TBD/forthcoming/etc.)"]
    if len(content.replace(" ", "")) < _MIN_CHARS:
        return [f"Data Availability Statement has no substantive content "
                f"(<{_MIN_CHARS} chars after the label)"]
    return []


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: paper carries a substantive Data Availability Statement"
              f"{(' — ' + note) if note else ''}")
    else:
        print("FAIL: data-availability gate:")
        print("\n".join(failures))
        print("Add or restore a labeled Data Availability Statement in tex/paper.tex.")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate the paper's Data Availability Statement.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not PAPER.exists():
        return _emit(args.json, "pass", [], "no tex/paper.tex yet")
    failures = audit(PAPER.read_text(encoding="utf-8", errors="ignore"))
    return _emit(args.json, "fail" if failures else "pass", failures)


def _selftest() -> int:
    good = (r"\noindent\textbf{Data Availability Statement:} The CMPD data and "
            r"replication scripts are maintained in the project repository and "
            r"will be deposited on openICPSR upon publication." "\n\n\\section{Intro}")
    none = r"\section{Introduction} We study state policy. No statement here."
    todo = r"\textbf{Data Availability Statement:} TODO add before submission.\n\n"
    empty = r"\textbf{Data Availability Statement:}\n\n\section{Next}"
    cases = [
        ("substantive DAS -> pass", audit(good) == [], True),
        ("no DAS -> fail", audit(none) != [], True),
        ("placeholder DAS -> fail", any("placeholder" in x for x in audit(todo)), True),
        ("empty DAS -> fail", any("substantive" in x for x in audit(empty)), True),
    ]
    ok = all(got is want for _, got, want in cases)
    for name, got, want in cases:
        print(f"  [{'ok' if got is want else 'FAIL'}] {name}")
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
