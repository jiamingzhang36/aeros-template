#!/usr/bin/env python3
"""ADVISORY tool (online): verify each references.bib entry actually exists.

This is the network half of bibliography verification -- the part
`check_bib_integrity` (offline) cannot do. It queries OpenAlex for every bib
entry, fuzzy-matches the returned title/year, and writes a human-reviewable
report to `audits/bib_verification_report.md`:

  - VERIFIED  : strong title match (or exact DOI hit)
  - REVIEW    : partial match -- a human should eyeball it
  - NOT FOUND : no plausible match -- possible fabrication or obscure venue

It is NOT a CI gate (network access + fuzzy matching + obscure-venue false
negatives make it non-deterministic). It produces an artifact a human signs;
`check_bib_verification_present` then hard-gates that the signed report exists
and covers every current key -- the same pattern as the referee-review gate.

Usage:
    python checks/verify_bib_online.py            # writes the report
    python checks/verify_bib_online.py --insecure # skip TLS verify (broken cert store only)

Re-run after editing references.bib; then a human reviews REVIEW/NOT FOUND rows
and adds a `Verified-by:` sign-off line.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

BIB = Path("tex/references.bib")
REPORT = Path("audits/bib_verification_report.md")
MAILTO = "zhangjiaming3608@gmail.com"
API = "https://api.openalex.org/works"
ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.I)


def _field(body: str, name: str) -> str:
    """Extract a brace- or quote-delimited bibtex field value."""
    m = re.search(rf"{name}\s*=\s*", body, re.I)
    if not m:
        return ""
    i = m.end()
    if i >= len(body) or body[i] not in "{\"":
        m2 = re.match(r"\s*([^,\n]+)", body[i:])
        return (m2.group(1).strip() if m2 else "")
    close = "}" if body[i] == "{" else "\""
    depth, out, i = 0, [], i
    for ch in body[i:]:
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                break
            continue
        if ch == close and close == "\"":
            break
        out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _entries(text: str) -> list[dict]:
    out = []
    for m in ENTRY_RE.finditer(text):
        etype, key = m.group(1).lower(), m.group(2).strip()
        if etype in {"comment", "string", "preamble"}:
            continue
        nxt = ENTRY_RE.search(text, m.end())
        body = text[m.end(): nxt.start() if nxt else len(text)]
        out.append({
            "key": key, "type": etype,
            "title": _field(body, "title"),
            "author": _field(body, "author") or _field(body, "editor"),
            "year": _field(body, "year"),
            "doi": _field(body, "doi"),
        })
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def _get(url: str, ctx, retries: int = 3) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": f"aeros-bib-verify (mailto:{MAILTO})"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
                return json.load(r)
        except Exception as exc:  # noqa: BLE001 -- transient API/network, back off and retry
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise last  # type: ignore[misc]


def _verify_one(e: dict, ctx) -> dict:
    title = e["title"]
    if not title:
        return {**e, "status": "REVIEW", "matched": "", "match_doi": "", "note": "no title in entry"}
    # DOI exact hit first (strongest)
    if e["doi"]:
        try:
            d = _get(f"{API}/doi:{urllib.parse.quote(e['doi'])}?mailto={MAILTO}", ctx)
            if d.get("id"):
                return {**e, "status": "VERIFIED", "matched": d.get("display_name", ""),
                        "match_doi": (d.get("doi") or "").replace("https://doi.org/", ""),
                        "note": "exact DOI"}
        except Exception:
            pass
    q = urllib.parse.quote(title)
    try:
        d = _get(f"{API}?filter=title.search:{q}&per_page=5&mailto={MAILTO}", ctx)
    except Exception as exc:
        return {**e, "status": "REVIEW", "matched": "", "match_doi": "", "note": f"query error: {type(exc).__name__}"}
    best, best_r = None, 0.0
    for c in d.get("results", []):
        r = SequenceMatcher(None, _norm(title), _norm(c.get("display_name", ""))).ratio()
        if r > best_r:
            best, best_r = c, r
    if not best:
        return {**e, "status": "NOT FOUND", "matched": "", "match_doi": "", "note": "no OpenAlex results"}
    matched = best.get("display_name", "")
    mdoi = (best.get("doi") or "").replace("https://doi.org/", "")
    myear = best.get("publication_year")
    note = f"title sim {best_r:.2f}"
    if e["year"] and myear and abs(int(re.sub(r"\D", "", e['year']) or 0) - int(myear)) > 1:
        note += f"; YEAR MISMATCH bib={e['year']} found={myear}"
    if best_r >= 0.92 and "MISMATCH" not in note:
        status = "VERIFIED"
    elif best_r >= 0.75:
        status = "REVIEW"
    else:
        status = "NOT FOUND"
    return {**e, "status": status, "matched": matched, "match_doi": mdoi, "note": note}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (broken cert store only)")
    args = ap.parse_args(argv)
    if not BIB.exists():
        print(f"REFUSED: {BIB} not found")
        return 2
    if args.insecure:
        ctx = ssl._create_unverified_context()
    else:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()

    entries = _entries(BIB.read_text(encoding="utf-8", errors="ignore"))
    results = []
    for i, e in enumerate(entries, 1):
        res = _verify_one(e, ctx)
        results.append(res)
        print(f"  [{i:>2}/{len(entries)}] {res['status']:<9} {e['key']}  {res['note']}")
        time.sleep(0.15)  # polite pool

    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("VERIFIED", "REVIEW", "NOT FOUND")}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Bibliography Verification Report",
        "",
        f"Source: `{BIB}` ({len(entries)} entries) — checked against OpenAlex.",
        f"Summary: **{counts['VERIFIED']} verified, {counts['REVIEW']} review, {counts['NOT FOUND']} not found**.",
        "",
        "Advisory: OpenAlex misses some books/working papers/obscure venues, so a",
        "REVIEW/NOT FOUND row is a prompt to check by hand, not proof of fabrication.",
        "",
        "| Key | Status | Bib title | Matched (OpenAlex) | DOI | Note |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        bt = (r["title"][:50] + "…") if len(r["title"]) > 50 else r["title"]
        mt = (r["matched"][:50] + "…") if len(r["matched"]) > 50 else r["matched"]
        lines.append(f"| {r['key']} | {r['status']} | {bt} | {mt} | {r['match_doi']} | {r['note']} |")
    lines += [
        "",
        "## Human sign-off",
        "",
        "A human must review every REVIEW / NOT FOUND row (confirm the work is real,",
        "fix the entry, or drop the citation), then sign below. `check_bib_verification_present`",
        "requires this line to be filled.",
        "",
        "Verified-by:   <!-- name + date once REVIEW/NOT FOUND rows are resolved -->",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT} — {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
