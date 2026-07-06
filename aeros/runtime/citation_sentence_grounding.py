"""Sentence-level manuscript citation grounding.

This module upgrades citation checking from registry/card existence to a
sentence-level grounding queue. It parses manuscript sentences, extracts citation
keys, maps each key to paper_registry rows and extraction cards, and requires
claim-bearing sentences to have an approved human interpretation record.

It still does not prove scientific truth. It makes citation support auditable and
blocks paper-readiness claims when a cited claim-bearing sentence lacks a
source-bound support chain.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import hashlib
import json
import re
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

MANUSCRIPT_GLOBS = (
    "tex/paper.tex",
    "tex/*.tex",
    "paper/*.tex",
    "paper/*.md",
    "docs/manuscript/*.tex",
    "docs/manuscript/*.md",
    "docs/manuscript*.tex",
    "docs/manuscript*.md",
)
REGISTRY = Path("discovery/literature/paper_registry.csv")
EXTRACTION_DIR = Path("discovery/literature/extraction_cards")
INTERPRETATION_DIR = Path("discovery/literature/interpretation_records")

CLAIM_MARKERS = (
    "we find", "we show", "our result", "our estimate", "estimate", "estimated",
    "effect", "impact", "caus", "increase", "decrease", "reduc", "higher", "lower",
    "significant", "robust", "coefficient", "elasticit", "percent", "%", "pp ",
    "leads to", "results in", "supports our", "evidence that",
)
INTERPRETIVE_MARKERS = (
    "finds", "shows", "argues", "documents", "reports", "estimates", "demonstrates",
    "suggests", "literature", "evidence", "method", "data", "uses", "limitation",
)
APPROVED_FAITHFUL = {"faithful", "direct_support", "supports"}
WEAK_VALUES = {"weak", "partial_support", "background_only"}
BAD_VALUES = {"unsupported", "overclaimed", "contradicts", "mismatch", "fail"}

DOES_NOT_PROVE = [
    "that the cited source is true",
    "that human interpretation is correct beyond the recorded source passage",
    "that uncited manuscript claims are grounded",
    "that the paper is submission-ready",
    "that claim, gate, or release authority is granted",
]


@dataclass(frozen=True)
class SentenceCitationGroundingRow:
    sentence_id: str
    manuscript_path: str
    line: int
    manuscript_sentence: str
    citation_key: str
    mapped_paper_id: str
    extraction_card: str
    interpretation_record: str
    claim_type: str
    support_status: str
    required_action: str
    blocking: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _rel(root: Path, path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(root))
    except Exception:
        return str(p)


def _manuscripts(root: Path) -> list[Path]:
    out: list[Path] = []
    for pattern in MANUSCRIPT_GLOBS:
        out.extend(p for p in root.glob(pattern) if p.is_file())
    # Prefer main paper-ish names, but keep deterministic order.
    return sorted(set(out), key=lambda p: ("appendix" in p.name.lower(), str(p)))


def _strip_tex_noise(text: str) -> str:
    cleaned: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"(?<!\\)%.*$", "", raw)
        cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"\\(?:label|ref|eqref|url|href)(?:\[[^\]]*\])?\{[^}]*\}", " ", text)
    text = re.sub(r"\\(?:emph|textit|textbf)\{([^}]*)\}", r"\1", text)
    return text


def _sentence_spans(text: str) -> list[tuple[str, int]]:
    compact = _strip_tex_noise(text)
    spans: list[tuple[str, int]] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?。！？])\s+", compact):
        sent = compact[start:match.start()].strip()
        if sent:
            line = compact.count("\n", 0, start) + 1
            spans.append((re.sub(r"\s+", " ", sent), line))
        start = match.end()
    tail = compact[start:].strip()
    if tail:
        line = compact.count("\n", 0, start) + 1
        spans.append((re.sub(r"\s+", " ", tail), line))
    return spans


def _citation_keys(sentence: str) -> list[str]:
    keys: list[str] = []
    cite_cmd = r"\\(?:cite|citet|citep|citealp|citeauthor|citeyear|parencite|textcite|autocite|footcite)(?:\[[^\]]*\])*\{([^}]+)\}"
    for match in re.finditer(cite_cmd, sentence):
        for raw in match.group(1).split(","):
            key = raw.strip()
            if key and key not in keys:
                keys.append(key)
    for match in re.finditer(r"@([A-Za-z0-9_:\-.]+)", sentence):
        key = match.group(1).strip().rstrip(".,;:)]}")
        if key and key not in keys:
            keys.append(key)
    return keys


def _stable_sentence_id(path: str, line: int, sentence: str, key: str) -> str:
    payload = f"{path}\n{line}\n{sentence}\n{key}".encode("utf-8")
    return "S_" + hashlib.sha256(payload).hexdigest()[:12].upper()


def _registry_rows(root: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    path = root / REGISTRY
    by_pid: dict[str, dict[str, str]] = {}
    by_key: dict[str, str] = {}
    if not path.exists():
        return by_pid, by_key
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            pid = (row.get("paper_id") or row.get("id") or "").strip()
            if not pid:
                continue
            by_pid[pid] = row
            for col in ("bib_key", "citation_key", "bibtex_key", "key"):
                val = (row.get(col) or "").strip()
                if val:
                    by_key[val] = pid
            by_key.setdefault(pid, pid)
    return by_pid, by_key


def _claim_type(sentence: str) -> str:
    low = sentence.lower()
    if any(marker in low for marker in CLAIM_MARKERS):
        return "claim_bearing"
    if any(marker in low for marker in INTERPRETIVE_MARKERS):
        return "interpretive"
    return "bibliographic"


def _card_path(root: Path, pid: str, row: dict[str, str]) -> Path | None:
    explicit = (row.get("extraction_card") or row.get("card_path") or "").strip()
    if explicit:
        p = root / explicit
        if p.is_file():
            return p
    candidates = [
        root / EXTRACTION_DIR / f"{pid}.md",
        root / EXTRACTION_DIR / f"{pid}_extraction_card.md",
        root / EXTRACTION_DIR / f"extraction_{pid}.md",
    ]
    candidates.extend(sorted((root / EXTRACTION_DIR).glob(f"*{pid}*.md")))
    for p in candidates:
        if p.is_file():
            return p
    return None


def _card_has_support(path: Path | None) -> tuple[bool, str]:
    if path is None:
        return False, "missing extraction card"
    text = _read_text(path)
    low = text.lower()
    if any(marker in low for marker in ("source passage", "direct evidence", "what this paper can support", "evidence notes", "supports:")):
        if not any(marker in low for marker in ("todo", "placeholder", "tbd")):
            return True, "source-bound support notes found"
    if len(re.sub(r"\s+", "", text)) >= 1200:
        return True, "substantive extraction card text found"
    return False, "extraction card lacks source-bound support notes"


def _load_record(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = _read_text(path)
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    if yaml is not None and path.suffix.lower() in {".yml", ".yaml"}:
        try:
            data = yaml.safe_load(text) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _interpretation_record(root: Path, sentence_id: str, key: str) -> tuple[Path | None, dict[str, Any]]:
    base = root / INTERPRETATION_DIR
    candidates = []
    for stem in (sentence_id, key):
        candidates.extend([base / f"{stem}.yml", base / f"{stem}.yaml", base / f"{stem}.json"])
    for path in candidates:
        data = _load_record(path)
        if data:
            return path, data
    return None, {}


def _verdict_from_record(record: dict[str, Any]) -> tuple[str, str]:
    if not record:
        return "missing", "missing approved interpretation record"
    human = str(record.get("human_status") or record.get("approved") or "").strip().lower()
    verdict = str(record.get("review_verdict") or record.get("verdict") or record.get("support_status") or "").strip().lower()
    relation = str(record.get("support_relation") or "").strip().lower()
    passage = str(record.get("source_passage") or record.get("quoted_passage") or "").strip()
    if human not in {"approved", "yes", "true"}:
        return "needs_human_review", "interpretation record is not human-approved"
    if not passage:
        return "needs_human_review", "approved interpretation record lacks source_passage"
    if verdict in BAD_VALUES or relation in BAD_VALUES:
        return "overclaimed", "approved record marks support as unsupported/overclaimed/contradictory"
    if verdict in APPROVED_FAITHFUL or relation in APPROVED_FAITHFUL:
        return "faithful", "approved interpretation record supports sentence"
    if verdict in WEAK_VALUES or relation in WEAK_VALUES:
        return "weak_support", "approved interpretation record is weak/partial/background-only"
    return "needs_human_review", "approved interpretation record has unclear support verdict"


def build_sentence_citation_grounding(root: Path | str = Path.cwd()) -> dict[str, Any]:
    root = Path(root)
    registry, by_key = _registry_rows(root)
    rows: list[SentenceCitationGroundingRow] = []
    manuscripts = _manuscripts(root)
    for manuscript in manuscripts:
        rel = _rel(root, manuscript)
        for sentence, line in _sentence_spans(_read_text(manuscript)):
            keys = _citation_keys(sentence)
            if not keys:
                continue
            ctype = _claim_type(sentence)
            for key in keys:
                sid = _stable_sentence_id(rel, line, sentence, key)
                pid = by_key.get(key, "")
                reg_row = registry.get(pid, {}) if pid else {}
                card = _card_path(root, pid, reg_row) if pid else None
                card_ok, card_note = _card_has_support(card)
                rec_path, rec = _interpretation_record(root, sid, key)
                record_status, record_note = _verdict_from_record(rec)

                if not pid:
                    support = "source_unavailable"
                    action = "add citation key to paper_registry or remove/replace the citation"
                    blocking = ctype == "claim_bearing"
                    note = "citation key not found in paper registry"
                elif not card_ok and ctype == "claim_bearing":
                    support = "unsupported"
                    action = "add source-bound extraction card before claiming citation support"
                    blocking = True
                    note = card_note
                elif ctype == "claim_bearing" and record_status != "faithful":
                    support = record_status if record_status != "missing" else "needs_human_review"
                    action = "create/approve interpretation record with source_passage and faithful verdict"
                    blocking = True
                    note = record_note
                elif ctype == "interpretive" and (not card_ok or record_status in {"overclaimed", "unsupported"}):
                    support = "weak_support" if card_ok else "needs_human_review"
                    action = "review interpretive citation before using it for synthesis or claim language"
                    blocking = False
                    note = card_note if not card_ok else record_note
                else:
                    support = "bibliographic" if ctype == "bibliographic" else "faithful"
                    action = "none"
                    blocking = False
                    note = card_note if card_ok else "bibliographic citation mapped; no claim-bearing support asserted"

                rows.append(SentenceCitationGroundingRow(
                    sentence_id=sid,
                    manuscript_path=rel,
                    line=line,
                    manuscript_sentence=sentence,
                    citation_key=key,
                    mapped_paper_id=pid,
                    extraction_card=_rel(root, card) if card else "",
                    interpretation_record=_rel(root, rec_path) if rec_path else "",
                    claim_type=ctype,
                    support_status=support,
                    required_action=action,
                    blocking=blocking,
                    notes=note,
                ))

    failures = [row for row in rows if row.blocking]
    counts = {
        "manuscripts": len(manuscripts),
        "citation_sentences": len({(r.manuscript_path, r.line, r.manuscript_sentence) for r in rows}),
        "citation_rows": len(rows),
        "claim_bearing_rows": sum(r.claim_type == "claim_bearing" for r in rows),
        "blocking_rows": len(failures),
        "unknown_or_unavailable": sum(r.support_status == "source_unavailable" for r in rows),
        "weak_or_review_needed": sum(r.support_status in {"weak_support", "needs_human_review"} for r in rows),
    }
    status = "inactive" if not manuscripts or not rows else ("fail" if failures else "pass")
    return {
        "model": "AEROS-CITATION-SENTENCE-GROUNDING-001",
        "status": status,
        "counts": counts,
        "rows": [row.to_dict() for row in rows],
        "failures": [row.to_dict() for row in failures],
        "does_not_prove": DOES_NOT_PROVE,
    }
