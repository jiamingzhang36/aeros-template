"""Citation Risk Radar — the execution engine behind `aeros drive --goal citation-risk`.

Read-only. Parses a manuscript's narrative author-year citations, matches them to
the paper registry by year + author-token overlap (handles institutional authors),
and ranks the cited sources whose backing is weakest. This is deliberately advisory:
it surfaces grounding risk, it does not certify claims, approve gates, or edit the
paper. It complements the pandoc-`@key` path in submission_driver for projects that
cite in narrative author-year style.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

YEAR = r"(?:19|20)\d{2}"
_STOP = {
    "and", "the", "for", "with", "jr", "et", "al", "see", "note", "notes",
    "pay", "table", "figure", "panel", "column", "section", "appendix",
    "source", "sources", "policy", "who", "benefits", "program",
}
_CLAIM_WORDS = (
    "reduc", "increas", "decreas", "effect", "caus", "impact", "signific",
    "elasticit", "decline", "raise", "lower", "%", "percent", "billion",
    "million", "more likely", "less likely", "estimate", "leads to", "results in",
)
# manuscript-name priority (higher wins) so we scan the draft, not audit reports
_MANUSCRIPT_GLOBS = ("paper/*.md", "paper/*.tex", "docs/manuscript/*.md",
                     "docs/manuscript/*.tex", "docs/manuscript*.md", "docs/manuscript*.tex")
_REGISTRY_CANDIDATES = ("discovery/literature/paper_registry.csv",
                        "docs/manuscript/literature_extraction_cards_status.csv")


@dataclass(frozen=True)
class RadarResult:
    active: bool
    reason: str
    manuscript: str
    registry_papers: int
    distinct_sources: int
    grounded: int
    unknown: int
    ungrounded: int
    claim_bearing_at_risk: int
    findings: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active, "reason": self.reason, "manuscript": self.manuscript,
            "registry_papers": self.registry_papers, "distinct_sources": self.distinct_sources,
            "grounded": self.grounded, "unknown": self.unknown, "ungrounded": self.ungrounded,
            "claim_bearing_at_risk": self.claim_bearing_at_risk, "findings": self.findings,
        }


def _tokens(phrase: str) -> set[str]:
    """Distinctive author tokens = proper nouns (Capitalized, len>=3, non-stop)."""
    phrase = re.sub(r"[{}.,;:]", " ", phrase)
    return {w.lower() for w in re.findall(r"[A-Z][A-Za-z'\-]{2,}", phrase)
            if w.lower() not in _STOP}


def _manuscript_file(root: Path) -> Path | None:
    best, best_rank = None, (-1, -1)
    for pat in _MANUSCRIPT_GLOBS:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            name = p.name.lower()
            rank = (("draft" in name) * 4 + ("manuscript" in name) * 2 + ("paper" in name),
                    p.stat().st_size)
            if rank > best_rank:
                best, best_rank = p, rank
    return best


def _registry_file(root: Path) -> Path | None:
    for rel in _REGISTRY_CANDIDATES:
        p = root / rel
        if p.is_file():
            return p
    return None


def _load_registry(reg_csv: Path) -> tuple[dict[str, list[dict]], int]:
    """year -> [{citekey, toks, grounded, fta}], plus paper count."""
    by_year: dict[str, list[dict]] = defaultdict(list)
    n = 0
    with reg_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row.get("citation_key") or row.get("citekey") or "").strip()
            yr = (row.get("year") or "").strip()[:4]
            if not key or not yr.isdigit():
                # status CSV has no year column; skip cleanly
                continue
            n += 1
            fta = (row.get("full_text_available") or row.get("full_text_status") or "").strip().lower()
            card = (row.get("extraction_card") or row.get("card_path") or "").strip()
            grounded = fta in {"yes", "full_text_obtained", "full_text"} and bool(card)
            by_year[yr].append({"citekey": key, "toks": _tokens(row.get("authors") or ""),
                                 "grounded": grounded, "fta": fta})
    return by_year, n


def _best_match(auth_toks: set[str], year: str, by_year: dict) -> dict | None:
    best, best_ov = None, 0
    for rec in by_year.get(year, []):
        ov = len(auth_toks & rec["toks"])
        if ov > best_ov:
            best, best_ov = rec, ov
    return best if best_ov >= 1 else None


def _window(text: str, pos: int) -> str:
    start = max(text.rfind(". ", 0, pos), text.rfind("\n", 0, pos)) + 1
    end = text.find(". ", pos)
    end = end + 1 if end != -1 else min(pos + 170, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _real_year(seg: str, ym: re.Match) -> bool:
    """Reject a date (2025-12-01), quarter (2026Q1), or numeric range (2022-2024)."""
    before = seg[ym.start() - 1] if ym.start() else " "
    after = seg[ym.end()] if ym.end() < len(seg) else " "
    return before not in "-/" and after not in "-/Qq"


def _parse_citations(text: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    # Parenthetical: (Author and Author 2011; Other et al. 2016) — may wrap lines
    for m in re.finditer(r"\(([^()]{0,400}?\b" + YEAR + r"[^()]*?)\)", text):
        grp = re.sub(r"\s+", " ", m.group(1))
        if "/" in grp or ".md" in grp or ".csv" in grp or "http" in grp:
            continue
        win = _window(text, m.start())
        for seg in grp.split(";"):
            ys = [y for y in re.finditer(YEAR, seg) if _real_year(seg, y)]
            if ys and _tokens(seg[:ys[-1].start()]):
                out.append((seg[:ys[-1].start()], ys[-1].group(0), win))
    # Narrative: Author (2025) / Author and Author (2025) / Author et al. (2025)
    for m in re.finditer(
            r"((?:[A-Z][A-Za-z'\-]+\.?(?:,? (?:and|&) )?){1,4}(?:et al\.?\s*)?)\s*\((" + YEAR + r")\)",
            text):
        if _tokens(m.group(1)):
            out.append((m.group(1), m.group(2), _window(text, m.start())))
    return out


def _is_claim(win: str) -> bool:
    low = win.lower()
    return any(w in low for w in _CLAIM_WORDS)


def _label(phrase: str, year: str) -> str:
    toks = [w for w in re.findall(r"[A-Za-z'\-]+", phrase) if w.lower() not in {"and", "et", "al"}]
    head = toks[0] if toks else phrase.strip()
    return f"{head}{' et al.' if 'et al' in phrase.lower() else ''} {year}"


def build_citation_radar(root: Path | str = Path.cwd(), *, top: int = 12) -> RadarResult:
    root = Path(root)
    man = _manuscript_file(root)
    reg = _registry_file(root)
    if man is None:
        return RadarResult(False, "no manuscript found under paper/ or docs/manuscript/",
                           "", 0, 0, 0, 0, 0, 0, [])
    if reg is None:
        return RadarResult(False, "no paper registry found (discovery/literature/paper_registry.csv)",
                           str(man.relative_to(root)) if man else "", 0, 0, 0, 0, 0, 0, [])

    by_year, n_reg = _load_registry(reg)
    text = man.read_text(encoding="utf-8", errors="ignore")

    raw: list[dict[str, Any]] = []
    for phrase, year, win in _parse_citations(text):
        rec = _best_match(_tokens(phrase), year, by_year)
        claim = _is_claim(win)
        if rec is None:
            key, risk, reason, tier = (None, "UNKNOWN",
                f"“{_label(phrase, year)}” matches no registry paper for {year} — cited source outside the evidence base.", 90)
        elif not rec["grounded"]:
            key, risk, reason, tier = (rec["citekey"], "UNGROUNDED",
                f"{rec['citekey']}: matched but full text not available (full_text={rec['fta'] or 'none'}).", 70)
        else:
            key, risk, reason, tier = (rec["citekey"], "GROUNDED", f"{rec['citekey']}: full-text card on file.", 5)
        raw.append({"citation": _label(phrase, year), "citekey": key, "risk": risk,
                    "claim_bearing": claim, "score": tier + (15 if claim else 0),
                    "reason": reason, "sentence": win[:240]})

    # collapse repeated cites of the same source; prefer a claim-bearing sentence
    collapsed: dict[str, dict] = {}
    for f in raw:
        k = f["citekey"] or f["citation"].lower()
        c = collapsed.get(k)
        if c is None:
            collapsed[k] = dict(f, occurrences=1)
        else:
            c["occurrences"] += 1
            if f["claim_bearing"] and not c["claim_bearing"]:
                c.update(claim_bearing=True, sentence=f["sentence"], score=f["score"])
    findings = sorted(collapsed.values(), key=lambda x: -x["score"])
    at_risk = [f for f in findings if f["risk"] != "GROUNDED"]

    return RadarResult(
        active=True, reason="ok", manuscript=str(man.relative_to(root)),
        registry_papers=n_reg, distinct_sources=len(findings),
        grounded=len(findings) - len(at_risk),
        unknown=sum(f["risk"] == "UNKNOWN" for f in findings),
        ungrounded=sum(f["risk"] == "UNGROUNDED" for f in findings),
        claim_bearing_at_risk=sum(f["claim_bearing"] and f["risk"] != "GROUNDED" for f in findings),
        findings=at_risk[:top] if top else at_risk,
    )


def format_citation_radar(res: RadarResult) -> str:
    if not res.active:
        return f"citation risk radar inactive: {res.reason}"
    out = [
        "# Citation Risk Radar",
        f"manuscript: {res.manuscript}",
        f"registry papers: {res.registry_papers}   distinct cited sources: {res.distinct_sources}",
        f"grounded: {res.grounded}   unknown-source: {res.unknown}   ungrounded: {res.ungrounded}"
        f"   (claim-bearing at risk: {res.claim_bearing_at_risk})",
        "",
        f"Top {len(res.findings)} risks:",
    ]
    for i, f in enumerate(res.findings, 1):
        tag = "CLAIM" if f["claim_bearing"] else "backg"
        occ = f"  (×{f['occurrences']})" if f.get("occurrences", 1) > 1 else ""
        out.append(f"  {i:>2}. [{f['risk']:<10} {tag}] {f['citation']}{occ}")
        out.append(f"      {f['reason']}")
        out.append(f"      “…{f['sentence']}…”")
    out += ["", "Boundary: read-only advisory. Does not certify claims, edit the paper, or approve gates."]
    return "\n".join(out)


def write_citation_radar(root: Path | str, res: RadarResult) -> Path:
    root = Path(root)
    out_dir = root / "audits" / "citation_radar"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "citation_risk_radar.json"
    out.write_text(json.dumps(res.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return out
