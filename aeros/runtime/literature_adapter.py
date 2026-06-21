"""Literature discovery adapter layer for AEROS.

This module is intentionally conservative. It can query/import metadata and
write discovery registries/queues, but it never writes synthesis, claim
support, gate decisions, or extraction cards.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


SEARCH_LOG_COLUMNS = [
    "date",
    "agent",
    "source",
    "search_query",
    "results_found",
    "useful_results",
    "not_useful_results",
    "follow_up",
    "notes",
]

PAPER_REGISTRY_COLUMNS = [
    "paper_id",
    "citation_key",
    "title",
    "authors",
    "year",
    "source",
    "doi",
    "url",
    "pdf_url",
    "primary_function",
    "secondary_functions",
    "reading_depth",
    "status",
    "full_text_available",
    "opened_source",
    "opened_date",
    "evidence_basis",
    "screening_decision",
    "extraction_card",
    "used_in_synthesis",
    "notes",
]

SNOWBALL_COLUMNS = [
    "queued_at",
    "source_paper_id",
    "related_locator",
    "relation",
    "source",
    "status",
    "notes",
]

ALLOWED_SOURCES = {"openalex", "manual"}
ALLOWED_FUNCTIONS = {
    "idea-inspiring",
    "gap-verification",
    "method-identification",
    "data-measurement",
    "background-institutional",
    "theory-mechanism",
}


@dataclass(frozen=True)
class LiteratureSearchArgs:
    source: str
    query: str
    limit: int = 20
    primary_function: str = "idea-inspiring"
    dry_run: bool = False
    title: str = ""
    authors: str = ""
    year: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_csv(path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        path.write_text(",".join(columns) + "\n", encoding="utf-8")


def _read_csv(path: Path, columns: list[str]) -> list[dict[str, str]]:
    _ensure_csv(path, columns)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _append_rows(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    _ensure_csv(path, columns)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        for row in rows:
            writer.writerow({column: str(row.get(column, "")) for column in columns})


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _next_paper_id(existing: list[dict[str, str]]) -> str:
    max_seen = 0
    for row in existing:
        pid = str(row.get("paper_id", "")).strip().upper()
        if len(pid) >= 4 and pid.startswith("P") and pid[1:].isdigit():
            max_seen = max(max_seen, int(pid[1:]))
    return f"P{max_seen + 1:03d}"


def _citation_key(authors: str, year: str, title: str) -> str:
    first = "unknown"
    if authors.strip():
        first = authors.split(";", 1)[0].split(",", 1)[0].split()[-1].lower()
    elif title.strip():
        first = title.split()[0].lower()
    key = f"{first}{year or 'nd'}"
    cleaned = "".join(ch for ch in key if ch.isalnum() or ch in {"_", "-"})
    return cleaned or hashlib.sha1(title.encode("utf-8")).hexdigest()[:10]


def _openalex_work_to_candidate(work: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    title = str(work.get("title") or "").strip()
    year = str(work.get("publication_year") or "").strip()
    doi = str(work.get("doi") or "").strip()
    url = str(work.get("id") or "").strip()
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = str(author.get("display_name") or "").strip()
        if name:
            authors.append(name)
    pdf_url = ""
    for location_key in ("best_oa_location", "primary_location"):
        location = work.get(location_key) or {}
        pdf_url = str(location.get("pdf_url") or "").strip()
        if pdf_url:
            break
    related: list[str] = []
    for item in (work.get("referenced_works") or [])[:10]:
        if item:
            related.append(str(item))
    return {
        "title": title,
        "authors": "; ".join(authors),
        "year": year,
        "source": "openalex",
        "doi": doi,
        "url": url,
        "pdf_url": pdf_url,
    }, related


def _openalex_search(query: str, limit: int) -> list[tuple[dict[str, str], list[str]]]:
    safe_limit = max(1, min(int(limit or 20), 50))
    url = f"https://api.openalex.org/works?search={quote_plus(query)}&per-page={safe_limit}"
    request = Request(url, headers={"User-Agent": "AEROS literature adapter (mailto:example@example.com)"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - public scholarly metadata endpoint
        payload = json.loads(response.read().decode("utf-8"))
    return [_openalex_work_to_candidate(work) for work in payload.get("results") or []]


def _manual_candidate(args: LiteratureSearchArgs) -> list[tuple[dict[str, str], list[str]]]:
    if not args.title.strip() and not args.doi.strip() and not args.url.strip():
        raise ValueError("manual literature import requires --title, --doi, or --url")
    return [({
        "title": args.title,
        "authors": args.authors,
        "year": args.year,
        "source": "manual",
        "doi": args.doi,
        "url": args.url,
        "pdf_url": args.pdf_url,
    }, [])]


def _candidate_key(candidate: dict[str, str]) -> tuple[str, str, str]:
    return (_norm(candidate.get("doi", "")), _norm(candidate.get("url", "")), _norm(candidate.get("title", "")))


def literature_status(root: Path) -> dict[str, int | bool]:
    registry_path = root / "discovery/literature/paper_registry.csv"
    search_path = root / "discovery/literature/search_log.csv"
    rows = _read_csv(registry_path, PAPER_REGISTRY_COLUMNS) if registry_path.exists() else []
    search_rows = _read_csv(search_path, SEARCH_LOG_COLUMNS) if search_path.exists() else []
    candidates = [r for r in rows if r.get("screening_decision", "").strip() in {"maybe", "defer"}]
    included = [r for r in rows if r.get("screening_decision", "").strip() == "include"]
    extracted = [r for r in rows if r.get("extraction_card", "").strip() == "yes"]
    synthesis_ready = [r for r in rows if r.get("used_in_synthesis", "").strip() == "yes"]
    return {
        "searches": len([r for r in search_rows if any(str(v).strip() for v in r.values())]),
        "papers": len([r for r in rows if r.get("paper_id", "").strip()]),
        "candidates": len(candidates),
        "included": len(included),
        "extracted": len(extracted),
        "synthesis_ready": len(synthesis_ready),
    }


def format_literature_status(root: Path) -> str:
    status = literature_status(root)
    lines = ["Literature lane status"]
    for key in ["searches", "papers", "candidates", "included", "extracted", "synthesis_ready"]:
        lines.append(f"{key}: {status[key]}")
    lines.append("does_not_prove: metadata discovery does not prove full-text review, synthesis, gap support, or claim support")
    return "\n".join(lines)


def run_literature_search(root: Path, args: LiteratureSearchArgs) -> int:
    source = args.source.strip().lower()
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"unsupported literature source {args.source!r}; supported: {', '.join(sorted(ALLOWED_SOURCES))}")
    primary_function = args.primary_function.strip() or "idea-inspiring"
    if primary_function not in ALLOWED_FUNCTIONS:
        raise ValueError(f"invalid primary function {primary_function!r}")

    if source == "openalex":
        if not args.query.strip():
            raise ValueError("OpenAlex search requires --query")
        raw_candidates = _openalex_search(args.query, args.limit)
    else:
        raw_candidates = _manual_candidate(args)

    registry_path = root / "discovery/literature/paper_registry.csv"
    search_path = root / "discovery/literature/search_log.csv"
    snowball_path = root / "discovery/literature/citation_snowball_queue.csv"
    existing = _read_csv(registry_path, PAPER_REGISTRY_COLUMNS)
    seen = {_candidate_key(row) for row in existing}

    new_rows: list[dict[str, str]] = []
    snowball_rows: list[dict[str, str]] = []
    next_id = _next_paper_id(existing)
    next_num = int(next_id[1:])
    now = _utc_now()
    for candidate, related in raw_candidates:
        key = _candidate_key(candidate)
        if key in seen or not any(key):
            continue
        paper_id = f"P{next_num:03d}"
        next_num += 1
        seen.add(key)
        row = {
            **candidate,
            "paper_id": paper_id,
            "citation_key": _citation_key(candidate.get("authors", ""), candidate.get("year", ""), candidate.get("title", "")),
            "primary_function": primary_function,
            "secondary_functions": "",
            "reading_depth": "not_read",
            "status": "discovered",
            "full_text_available": "no",
            "opened_source": "",
            "opened_date": "",
            "evidence_basis": "none",
            "screening_decision": "defer",
            "extraction_card": "no",
            "used_in_synthesis": "no",
            "notes": "metadata discovery only; requires screening and full-text extraction before synthesis",
        }
        new_rows.append(row)
        for locator in related[:10]:
            snowball_rows.append({
                "queued_at": now,
                "source_paper_id": paper_id,
                "related_locator": locator,
                "relation": "referenced_work",
                "source": source,
                "status": "candidate",
                "notes": "citation-neighborhood candidate; not evidence",
            })

    search_row = {
        "date": now,
        "agent": "aeros-literature-adapter",
        "source": source,
        "search_query": args.query or args.title or args.doi or args.url,
        "results_found": len(raw_candidates),
        "useful_results": len(new_rows),
        "not_useful_results": max(len(raw_candidates) - len(new_rows), 0),
        "follow_up": "screen candidates, then obtain full text and extraction cards before synthesis",
        "notes": "ROUTE_READY only; metadata/citation discovery is not literature review completion",
    }

    if args.dry_run:
        print(f"would log search in {search_path.relative_to(root)}")
        print(f"would add {len(new_rows)} new paper candidate(s) to {registry_path.relative_to(root)}")
        print(f"would queue {len(snowball_rows)} citation-neighborhood candidate(s) in {snowball_path.relative_to(root)}")
        for row in new_rows[:10]:
            print(f"  - {row['paper_id']} {row['year']} {row['title'][:120]}")
        return 0

    _append_rows(search_path, SEARCH_LOG_COLUMNS, [search_row])
    if new_rows:
        _append_rows(registry_path, PAPER_REGISTRY_COLUMNS, new_rows)
    if snowball_rows:
        _append_rows(snowball_path, SNOWBALL_COLUMNS, snowball_rows)
    print(f"logged search -> {search_path.relative_to(root)}")
    print(f"added {len(new_rows)} paper candidate(s) -> {registry_path.relative_to(root)}")
    print(f"queued {len(snowball_rows)} citation-neighborhood candidate(s) -> {snowball_path.relative_to(root)}")
    print("status_label: ROUTE_READY")
    print("does_not_prove: full-text review, synthesis, gap support, claim support, or gate approval")
    return 0
