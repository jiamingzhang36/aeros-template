"""Compile verified full-text extraction cards into source-bound draft packets.

The compiler intentionally produces candidate prose in a work surface. It does
not interpret a source beyond its recorded extraction card and it never writes
to a manuscript, claim registry, synthesis, or gate artifact.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


REGISTRY = Path("discovery/literature/paper_registry.csv")
CARDS_DIR = Path("discovery/literature/extraction_cards")
PLACEHOLDERS = {"", "tbd", "todo", "unknown", "not stated", "n/a", "na", "none"}
REQUIRED_CARD_SECTIONS = (
    "## Full Text Status",
    "## Extraction Depth",
    "## Content Summary",
    "## What This Paper Can Support",
    "## What This Paper Cannot Support",
    "## Direct Evidence Notes",
    "## Opened Source",
)


@dataclass(frozen=True)
class ParagraphCandidateArgs:
    paper_ids: tuple[str, ...]
    purpose: str
    target_claim: str
    output_dir: str = "work/literature_candidate_paragraphs"
    dry_run: bool = False


@dataclass(frozen=True)
class BoundSource:
    paper_id: str
    citation_key: str
    citation: str
    extraction_card: str
    evidence_locator: str
    content_summary: str
    can_support: str
    cannot_support: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    end = text.find("\n## ", start)
    return text[start:end if end != -1 else len(text)].strip()


def _substantive(value: str) -> bool:
    lines = [line.strip(" |-:\t") for line in value.splitlines()]
    return any(line and line.lower() not in PLACEHOLDERS and "tbd" not in line.lower() for line in lines)


def _first_statement(value: str, *, limit: int = 360) -> str:
    clean_lines = []
    for raw in value.splitlines():
        line = raw.strip().lstrip("-*").strip()
        if not line or line.lower() in PLACEHOLDERS or set(line) <= {"-", "|", ":"}:
            continue
        clean_lines.append(line)
    text = re.sub(r"\s+", " ", " ".join(clean_lines)).strip()
    if not text:
        return ""
    sentence = re.split(r"(?<=[.!?。！？])\s+", text, maxsplit=1)[0]
    return sentence[:limit].rstrip()


def _direct_locator(value: str) -> str:
    for raw in value.splitlines():
        if not raw.strip().startswith("|") or "---" in raw or "Page / section" in raw:
            continue
        fields = [field.strip() for field in raw.strip().strip("|").split("|")]
        if fields and _substantive(fields[0]):
            return fields[0]
    return ""


def _read_registry(root: Path) -> dict[str, dict[str, str]]:
    path = root / REGISTRY
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            str(row.get("paper_id") or "").strip(): row
            for row in csv.DictReader(handle)
            if str(row.get("paper_id") or "").strip()
        }


def _citation(row: dict[str, str]) -> str:
    authors = str(row.get("authors") or "").strip()
    year = str(row.get("year") or "n.d.").strip()
    title = str(row.get("title") or "Untitled source").strip()
    first_author = authors.split(";", 1)[0].strip() if authors else "Unknown author"
    return f"{first_author} ({year}), {title}"


def _bound_source(root: Path, paper_id: str, row: dict[str, str]) -> tuple[BoundSource | None, list[str]]:
    errors: list[str] = []
    if str(row.get("full_text_available") or "").strip().lower() != "yes":
        errors.append("registry does not declare full_text_available=yes")
    if str(row.get("extraction_card") or "").strip().lower() != "yes":
        errors.append("registry does not declare extraction_card=yes")
    if str(row.get("evidence_basis") or "").strip() not in {"full_text", "extraction_card"}:
        errors.append("registry evidence_basis is not full_text/extraction_card")
    key = str(row.get("citation_key") or row.get("bib_key") or "").strip()
    if not key:
        errors.append("registry lacks citation_key")
    card = root / CARDS_DIR / f"{paper_id}.md"
    if not card.exists():
        errors.append(f"missing extraction card {card.relative_to(root)}")
        return None, errors
    text = card.read_text(encoding="utf-8", errors="ignore")
    for heading in REQUIRED_CARD_SECTIONS:
        if heading not in text:
            errors.append(f"card missing {heading}")
    if "full_text_obtained" not in _section(text, "## Full Text Status"):
        errors.append("card is not marked full_text_obtained")
    if "full_text_extraction" not in _section(text, "## Extraction Depth"):
        errors.append("card is not marked full_text_extraction")
    summary = _first_statement(_section(text, "## Content Summary"))
    supports = _first_statement(_section(text, "## What This Paper Can Support"))
    limits = _first_statement(_section(text, "## What This Paper Cannot Support"))
    locator = _direct_locator(_section(text, "## Direct Evidence Notes"))
    if not summary:
        errors.append("card Content Summary is not substantive")
    if not supports:
        errors.append("card Can Support section is not substantive")
    if not limits:
        errors.append("card Cannot Support section is not substantive")
    if not locator:
        errors.append("card Direct Evidence Notes lacks a page/section locator")
    if errors:
        return None, errors
    return BoundSource(
        paper_id=paper_id,
        citation_key=key,
        citation=_citation(row),
        extraction_card=card.relative_to(root).as_posix(),
        evidence_locator=locator,
        content_summary=summary,
        can_support=supports,
        cannot_support=limits,
    ), []


def _candidate_prose(source: BoundSource, purpose: str, target_claim: str) -> str:
    """Render deliberately bounded candidate prose from recorded card fields."""
    return (
        f"For the limited purpose of {purpose}, {source.citation} is relevant because "
        f"{source.content_summary} The full-text extraction records the relevant evidence at "
        f"{source.evidence_locator}. This source can support only the bounded proposition that "
        f"{source.can_support} It cannot by itself support {source.cannot_support} Accordingly, "
        f"the following is a candidate sentence requiring sentence-level grounding before manuscript use: "
        f"{target_claim} \\cite{{{source.citation_key}}}"
    )


def _packet_markdown(args: ParagraphCandidateArgs, sources: list[BoundSource], packet_id: str) -> str:
    lines = [
        f"# Source-Bound Candidate Paragraph Packet: {packet_id}",
        "",
        "status: CANDIDATE_ONLY",
        f"purpose: {args.purpose}",
        f"target_claim: {args.target_claim}",
        "",
        "## Candidate Prose",
        "",
    ]
    for source in sources:
        lines.extend([_candidate_prose(source, args.purpose, args.target_claim), ""])
    lines.extend([
        "## Evidence Bindings",
        "",
    ])
    for source in sources:
        lines.extend([
            f"- `{source.paper_id}` / `\\cite{{{source.citation_key}}}`",
            f"  - extraction_card: `{source.extraction_card}`",
            f"  - direct_evidence_locator: {source.evidence_locator}",
            f"  - can_support: {source.can_support}",
            f"  - cannot_support: {source.cannot_support}",
        ])
    lines.extend([
        "",
        "## Required Before Manuscript Promotion",
        "",
        "- Rewrite or accept the candidate only after a researcher reviews its source-bound limits.",
        "- Place any accepted sentence in the manuscript, then run the sentence-level citation grounding and interpretation checks.",
        "- Tier-2 claim-bearing use requires its existing independent-verifier floor; this packet cannot grant that status.",
        "",
        "## Does Not Prove",
        "",
        "- that the candidate prose is a correct scientific interpretation",
        "- that the target claim is supported, causal, novel, or publication-ready",
        "- claim, gate, canonical, or manuscript-promotion authority",
    ])
    return "\n".join(lines) + "\n"


def compile_candidate_paragraphs(root: Path, args: ParagraphCandidateArgs) -> dict[str, Any]:
    """Compile eligible cards to a work-only candidate packet; never promote it."""
    paper_ids = tuple(dict.fromkeys(str(value or "").strip() for value in args.paper_ids if str(value or "").strip()))
    if not paper_ids:
        raise ValueError("candidate paragraph compilation requires at least one --paper-id")
    if not args.purpose.strip() or not args.target_claim.strip():
        raise ValueError("candidate paragraph compilation requires --purpose and --target-claim")
    if Path(args.output_dir).is_absolute() or ".." in Path(args.output_dir).parts or not args.output_dir.startswith("work/"):
        raise ValueError("output_dir must be a safe project-relative work/ path")
    registry = _read_registry(root)
    sources: list[BoundSource] = []
    failures: dict[str, list[str]] = {}
    for paper_id in paper_ids:
        row = registry.get(paper_id)
        if row is None:
            failures[paper_id] = ["paper_id is absent from the literature registry"]
            continue
        source, errors = _bound_source(root, paper_id, row)
        if errors:
            failures[paper_id] = errors
        elif source is not None:
            sources.append(source)
    payload: dict[str, Any] = {
        "policy": "AEROS-LITERATURE-PARAGRAPH-001",
        "status": "REFUSED" if failures else ("ROUTE_READY" if args.dry_run else "CANDIDATE_COMPILED"),
        "paper_ids": list(paper_ids),
        "purpose": args.purpose,
        "target_claim": args.target_claim,
        "sources": [source.to_dict() for source in sources],
        "failures": failures,
        "writes": [],
        "next_action": "repair the listed full-text extraction prerequisites before compiling prose" if failures else "review candidate prose, then run sentence grounding only after a reviewed sentence enters a manuscript",
        "does_not_prove": [
            "scientific truth or faithful interpretation", "claim support or causal identification",
            "independent verification", "manuscript, claim, gate, or release promotion",
        ],
    }
    if failures or args.dry_run:
        return payload
    fingerprint = hashlib.sha256("\n".join([args.purpose, args.target_claim, *paper_ids]).encode("utf-8")).hexdigest()[:12]
    packet_id = f"LIT-PARA-{fingerprint.upper()}"
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{packet_id}.md"
    manifest_path = output_dir / f"{packet_id}.json"
    markdown_path.write_text(_packet_markdown(args, sources, packet_id), encoding="utf-8")
    manifest_path.write_text(json.dumps({**payload, "packet_id": packet_id, "compiled_at": _utc_now()}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload["packet_id"] = packet_id
    payload["writes"] = [markdown_path.relative_to(root).as_posix(), manifest_path.relative_to(root).as_posix()]
    return payload
