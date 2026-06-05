#!/usr/bin/env python3
"""Anti-degeneracy content guard for structured markdown artifacts.

Presence checks (file/heading exists) can be gamed by filling distinct sections
with identical or hollow text — "conformance without substance". This is a cheap,
DETERMINISTIC (non-LLM) floor against the clearest such patterns. It does NOT
judge whether content is *good* (that stays a human/critic job); it only flags
mechanically-detectable degeneracy.

Two rules, tuned conservatively to avoid false positives:

1. Duplicate substantive sections (always on): two different headings in the same
   file whose bodies are (near-)identical AND substantive. Stub/placeholder bodies
   are excluded from comparison, so a fresh template (every section "(fill in)")
   does NOT trip this.

2. Empty / filler-only sections (only when the file declares `status: filled`):
   a file that claims to be done must not have empty or pure-placeholder sections.
   Draft files are exempt — they are allowed to be incomplete.

Pass paths as arguments, or rely on the default discovery/design artifact set.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

CHECK_NAME = "check_no_degenerate_content"

DEFAULT_FILES = [
    "discovery/idea_memo.md",
    "discovery/01_literature_scope.md",
    "discovery/feasibility_memo.md",
    "discovery/design_sketch.md",
    "discovery/exploration_policy.md",
    "discovery/PROMOTE_TO_HARNESS.md",
    "discovery/literature/synthesis/literature_map.md",
    "docs/method_card.md",
]

FILLER_PHRASES = [
    "to be determined", "to be filled", "fill in", "see related discovery artifacts",
    "see related artifacts", "placeholder", "coming soon", "tbd", "todo", "n/a",
    "fill this in", "(fill in)",
]

MIN_DUP_WORDS = 5          # ignore trivial bodies when comparing for duplicates
NEAR_DUP_RATIO = 0.92      # difflib ratio above which two bodies count as duplicate
MIN_FILLED_WORDS = 3       # a 'filled' file's section must have at least this many content words


def _status(text: str) -> str:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not m:
        return ""
    sm = re.search(r"(?m)^\s*status\s*:\s*([A-Za-z_]+)", m.group(1))
    return (sm.group(1).strip().lower() if sm else "")


def _sections(text: str) -> list[tuple[str, str]]:
    """Return (heading, body) for level-2+ headings."""
    body_start = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
    out: list[tuple[str, str]] = []
    cur_h, cur_b = None, []
    for line in body_start.splitlines():
        if re.match(r"^#{2,}\s+", line):
            if cur_h is not None:
                out.append((cur_h, "\n".join(cur_b).strip()))
            cur_h = line.lstrip("#").strip()
            cur_b = []
        elif cur_h is not None:
            cur_b.append(line)
    if cur_h is not None:
        out.append((cur_h, "\n".join(cur_b).strip()))
    return out


def _norm(body: str) -> str:
    return re.sub(r"\s+", " ", body.strip().lower())


def _strip_filler(body: str) -> str:
    b = body.lower()
    for ph in FILLER_PHRASES:
        b = b.replace(ph, " ")
    return b


def _content_words(body: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", _strip_filler(body))


def _is_stub(body: str) -> bool:
    """A body that is empty or essentially only filler/pointer text."""
    return len(_content_words(body)) < MIN_FILLED_WORDS


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    status = _status(text)
    secs = _sections(text)
    problems: list[str] = []

    # Rule 2: a 'filled' file must not have empty/filler-only sections.
    if status == "filled":
        for h, b in secs:
            if not b.strip():
                problems.append(f"{path}: section '{h}' is empty but file is status: filled")
            elif _is_stub(b):
                problems.append(f"{path}: section '{h}' is placeholder/filler-only but file is status: filled")

    # Rule 1 (always): duplicate substantive sections.
    substantive = [(h, _norm(b)) for h, b in secs
                   if len(_content_words(b)) >= MIN_DUP_WORDS]
    for i in range(len(substantive)):
        for j in range(i + 1, len(substantive)):
            (h1, b1), (h2, b2) = substantive[i], substantive[j]
            if b1 == b2 or difflib.SequenceMatcher(None, b1, b2).ratio() >= NEAR_DUP_RATIO:
                problems.append(
                    f"{path}: sections '{h1}' and '{h2}' have (near-)identical content "
                    f"— distinct sections must say distinct things"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("paths", nargs="*", help="markdown files to scan (default: discovery/design set)")
    args = parser.parse_args(argv)

    targets = [Path(p) for p in (args.paths or DEFAULT_FILES)]
    failures: list[str] = []
    scanned = 0
    for p in targets:
        if not p.exists():
            continue  # absence is the presence-check's job, not this one's
        scanned += 1
        failures.extend(check_file(p))

    status = "fail" if failures else "pass"
    if args.json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif failures:
        print("FAIL: degenerate content detected:")
        for f in failures:
            print(f"  - {f}")
    else:
        print(f"PASS: no degenerate content ({scanned} file(s) scanned)")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
