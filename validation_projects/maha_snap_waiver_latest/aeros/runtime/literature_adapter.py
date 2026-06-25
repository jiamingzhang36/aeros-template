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
import re
from typing import Any
from urllib.error import HTTPError, URLError
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

FULLTEXT_READY_COLUMNS = [
    "queued_at",
    "paper_id",
    "zotero_item_key",
    "zotero_attachment_key",
    "title",
    "availability",
    "indexed_fulltext_chars",
    "pdf_path_or_url",
    "status",
    "next_action",
    "notes",
]

MISSING_FULLTEXT_COLUMNS = [
    "queued_at",
    "paper_id",
    "zotero_item_key",
    "title",
    "reason",
    "status",
    "next_action",
    "notes",
]

ALLOWED_SOURCES = {"openalex", "manual", "zotero"}
ALLOWED_FUNCTIONS = {
    "idea-inspiring",
    "gap-verification",
    "method-identification",
    "data-measurement",
    "background-institutional",
    "theory-mechanism",
}

FULLTEXT_CANDIDATE_AVAILABILITY = {
    "indexed_fulltext",
    "pdf_attachment_only",
    "candidate_url_unverified",
}

FULLTEXT_BLOCKER_REASONS = {
    "metadata_only",
    "closed_oa",
    "security_challenge",
    "login_required",
    "captcha",
    "spa_shell",
    "not_pdf",
    "empty_response",
    "cache_mismatch",
    "doi_mismatch",
    "title_mismatch",
    "pdf_attachment_only",
    "needs_ocr",
    "manual_pdf_required",
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
    zotero_base_url: str = "http://127.0.0.1:23119"


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


def _identity_tokenize(value: str) -> set[str]:
    stopwords = {
        "a", "an", "and", "are", "as", "at", "by", "for", "from", "in",
        "is", "of", "on", "or", "the", "to", "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 4 and token not in stopwords
    }


def _doi_in_text(doi: str, text: str) -> bool:
    doi_norm = str(doi or "").lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    if not doi_norm:
        return False
    return doi_norm in str(text or "").lower()


def _title_match_score(title: str, text: str) -> float:
    tokens = _identity_tokenize(title)
    if not tokens:
        return 0.0
    haystack = _identity_tokenize(text)
    return len(tokens & haystack) / max(len(tokens), 1)


def verify_fulltext_candidate_content(
    body: bytes | str,
    *,
    content_type: str = "",
    expected_title: str = "",
    expected_doi: str = "",
    source_url: str = "",
) -> dict[str, str]:
    """Classify fetched full-text candidate content without certifying review.

    This is an integrity helper for literature adapters/fetchers. It does not
    download anything and it does not write extraction cards. Its job is to stop
    metadata/OA/cache routes from being mistaken for readable target-paper text.
    """
    raw = body.encode("utf-8", errors="ignore") if isinstance(body, str) else (body or b"")
    content_type_l = str(content_type or "").lower()
    text = raw[:200_000].decode("utf-8", errors="ignore")
    text_l = text.lower()
    notes: list[str] = []

    if not raw or len(raw) < 64:
        return {
            "verdict": "blocked",
            "content_kind": "empty",
            "blocker_reason": "empty_response",
            "matched_by": "",
            "notes": "empty or tiny response; cannot be treated as full text",
        }

    security_markers = {
        "just a moment": "security_challenge",
        "cloudflare": "security_challenge",
        "__cf_chl": "security_challenge",
        "checking your browser": "security_challenge",
        "captcha": "captcha",
        "access denied": "login_required",
        "sign in": "login_required",
        "log in": "login_required",
        "institutional login": "login_required",
        "404 not found": "not_pdf",
        "page not found": "not_pdf",
    }
    for marker, reason in security_markers.items():
        if marker in text_l:
            return {
                "verdict": "blocked",
                "content_kind": "html",
                "blocker_reason": reason,
                "matched_by": "",
                "notes": f"response contains blocker marker {marker!r}",
            }

    is_pdf = raw.startswith(b"%PDF") or "application/pdf" in content_type_l
    if is_pdf:
        if not raw.startswith(b"%PDF"):
            return {
                "verdict": "blocked",
                "content_kind": "html",
                "blocker_reason": "not_pdf",
                "matched_by": "",
                "notes": "content-type suggested PDF but response did not start with PDF magic bytes",
            }
        matched_by = ""
        if expected_doi and _doi_in_text(expected_doi, text):
            matched_by = "doi"
        elif expected_title and _title_match_score(expected_title, text) >= 0.6:
            matched_by = "title"
        if not matched_by and (expected_title or expected_doi):
            notes.append("PDF bytes verified, but title/DOI identity still requires parsed/OCR text before extraction")
            verdict = "needs_identity_check"
        else:
            verdict = "verified_pdf"
            notes.append("PDF bytes verified; still requires full-text extraction card before synthesis")
        return {
            "verdict": verdict,
            "content_kind": "pdf",
            "blocker_reason": "",
            "matched_by": matched_by,
            "notes": "; ".join(notes),
        }

    looks_html = "<html" in text_l or "<!doctype html" in text_l or "text/html" in content_type_l
    if looks_html and len(text_l) < 1500 and not _doi_in_text(expected_doi, text) and _title_match_score(expected_title, text) < 0.4:
        return {
            "verdict": "blocked",
            "content_kind": "html",
            "blocker_reason": "spa_shell",
            "matched_by": "",
            "notes": "short HTML shell without target-paper identity markers",
        }

    matched_by = ""
    if expected_doi and _doi_in_text(expected_doi, text):
        matched_by = "doi"
    elif expected_title and _title_match_score(expected_title, text) >= 0.6:
        matched_by = "title"

    if (expected_title or expected_doi) and not matched_by:
        reason = "doi_mismatch" if expected_doi else "title_mismatch"
        if expected_title and expected_doi:
            reason = "title_mismatch"
        return {
            "verdict": "blocked",
            "content_kind": "html" if looks_html else "text",
            "blocker_reason": reason,
            "matched_by": "",
            "notes": "candidate content did not match expected title/DOI; treat as cache/source mismatch until reviewed",
        }

    if len(text_l) < 1500:
        return {
            "verdict": "blocked",
            "content_kind": "html" if looks_html else "text",
            "blocker_reason": "spa_shell",
            "matched_by": matched_by,
            "notes": "response is too short to serve as article full text",
        }

    return {
        "verdict": "verified_article_html" if matched_by else "needs_identity_check",
        "content_kind": "html" if looks_html else "text",
        "blocker_reason": "",
        "matched_by": matched_by,
        "notes": "candidate text is readable but still requires full-text extraction card before synthesis",
    }


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


def _zotero_api_get(base_url: str, path: str) -> Any:
    url = base_url.rstrip("/") + (path if path.startswith("/") else "/" + path)
    request = Request(url, headers={"Zotero-API-Version": "3"})
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - local Zotero API
            return json.loads(response.read().decode("utf-8") or "null")
    except HTTPError as exc:
        raise RuntimeError(f"Zotero local API request failed: status={exc.code} path={path}") from exc
    except URLError as exc:
        raise RuntimeError(
            "Zotero local API is not reachable. Open Zotero Desktop and enable the local API first."
        ) from exc


def _year_from_date(raw: str) -> str:
    match = re.search(r"\b(18|19|20|21)\d{2}\b", str(raw or ""))
    return match.group(0) if match else ""


def _zotero_creators(data: dict[str, Any]) -> str:
    names: list[str] = []
    for creator in data.get("creators") or []:
        name = creator.get("name") or " ".join(
            part for part in [creator.get("firstName"), creator.get("lastName")] if part
        )
        if name:
            names.append(name)
    return "; ".join(names)


def _zotero_file_url(base_url: str, attachment_key: str) -> str:
    try:
        value = _zotero_api_get(base_url, f"/api/users/0/items/{quote_plus(attachment_key)}/file/view/url")
    except Exception:
        return ""
    return str(value or "")


def _zotero_fulltext_chars(base_url: str, attachment_key: str) -> int:
    try:
        value = _zotero_api_get(base_url, f"/api/users/0/items/{quote_plus(attachment_key)}/fulltext")
    except Exception:
        return 0
    if isinstance(value, dict):
        return len(str(value.get("content") or ""))
    return len(str(value or ""))


def _zotero_attachment_info(base_url: str, item_key: str) -> dict[str, str]:
    try:
        children = _zotero_api_get(base_url, f"/api/users/0/items/{quote_plus(item_key)}/children")
    except Exception:
        children = []
    best: dict[str, str] = {
        "attachment_key": "",
        "availability": "missing_pdf_attachment",
        "indexed_fulltext_chars": "0",
        "pdf_path_or_url": "",
    }
    for child in children or []:
        data = child.get("data", child)
        key = str(child.get("key") or data.get("key") or "")
        content_type = str(data.get("contentType") or "").lower()
        title = str(data.get("title") or "").lower()
        if data.get("itemType") != "attachment":
            continue
        if "pdf" not in content_type and ".pdf" not in title and "pdf" not in title:
            continue
        chars = _zotero_fulltext_chars(base_url, key) if key else 0
        file_url = _zotero_file_url(base_url, key) if key else ""
        availability = "indexed_fulltext" if chars > 0 else "pdf_attachment_only"
        return {
            "attachment_key": key,
            "availability": availability,
            "indexed_fulltext_chars": str(chars),
            "pdf_path_or_url": file_url,
        }
    return best


def _zotero_search(query: str, limit: int, base_url: str) -> list[tuple[dict[str, str], list[str]]]:
    if not query.strip():
        raise ValueError("Zotero search requires --query")
    safe_limit = max(1, min(int(limit or 20), 50))
    params = f"q={quote_plus(query)}&limit={safe_limit}&sort=title&direction=asc"
    rows = _zotero_api_get(base_url, f"/api/users/0/items/top?{params}")
    candidates: list[tuple[dict[str, str], list[str]]] = []
    for item in rows or []:
        data = item.get("data", item)
        item_key = str(item.get("key") or data.get("key") or "")
        attachment = _zotero_attachment_info(base_url, item_key) if item_key else {}
        title = str(data.get("title") or "").strip()
        authors = _zotero_creators(data)
        year = _year_from_date(str(data.get("date") or ""))
        doi = str(data.get("DOI") or data.get("doi") or "").strip()
        url = str(data.get("url") or "").strip() or (f"zotero://select/items/{item_key}" if item_key else "")
        pdf_url = str(attachment.get("pdf_path_or_url") or "")
        candidates.append(({
            "title": title,
            "authors": authors,
            "year": year,
            "source": "zotero",
            "doi": doi,
            "url": url,
            "pdf_url": pdf_url,
            "_zotero_item_key": item_key,
            "_zotero_attachment_key": str(attachment.get("attachment_key") or ""),
            "_zotero_availability": str(attachment.get("availability") or "missing_pdf_attachment"),
            "_zotero_fulltext_chars": str(attachment.get("indexed_fulltext_chars") or "0"),
            "_zotero_pdf_path_or_url": pdf_url,
        }, []))
    return candidates


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
    elif source == "zotero":
        raw_candidates = _zotero_search(args.query, args.limit, args.zotero_base_url)
    else:
        raw_candidates = _manual_candidate(args)

    registry_path = root / "discovery/literature/paper_registry.csv"
    search_path = root / "discovery/literature/search_log.csv"
    snowball_path = root / "discovery/literature/citation_snowball_queue.csv"
    fulltext_ready_path = root / "discovery/literature/fulltext_ready_queue.csv"
    missing_fulltext_path = root / "discovery/literature/missing_fulltext_queue.csv"
    existing = _read_csv(registry_path, PAPER_REGISTRY_COLUMNS)
    seen = {_candidate_key(row) for row in existing}

    new_rows: list[dict[str, str]] = []
    snowball_rows: list[dict[str, str]] = []
    fulltext_ready_rows: list[dict[str, str]] = []
    missing_fulltext_rows: list[dict[str, str]] = []
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
            "full_text_available": "yes" if int(candidate.get("_zotero_fulltext_chars") or "0") > 0 else "no",
            "opened_source": "",
            "opened_date": "",
            "evidence_basis": "none",
            "screening_decision": "defer",
            "extraction_card": "no",
            "used_in_synthesis": "no",
            "notes": "metadata discovery only; requires screening and full-text extraction before synthesis",
        }
        new_rows.append(row)
        if source == "zotero":
            if candidate.get("_zotero_attachment_key"):
                fulltext_ready_rows.append({
                    "queued_at": now,
                    "paper_id": paper_id,
                    "zotero_item_key": candidate.get("_zotero_item_key", ""),
                    "zotero_attachment_key": candidate.get("_zotero_attachment_key", ""),
                    "title": candidate.get("title", ""),
                    "availability": candidate.get("_zotero_availability", ""),
                    "indexed_fulltext_chars": candidate.get("_zotero_fulltext_chars", "0"),
                    "pdf_path_or_url": candidate.get("_zotero_pdf_path_or_url", ""),
                    "status": "ready_for_extraction",
                    "next_action": "open Zotero PDF/fulltext and write a full-text extraction card before synthesis",
                    "notes": "ROUTE_READY only; indexed_fulltext means text is locally readable, pdf_attachment_only means PDF must still be parsed/OCRed before extraction",
                })
            else:
                missing_fulltext_rows.append({
                    "queued_at": now,
                    "paper_id": paper_id,
                    "zotero_item_key": candidate.get("_zotero_item_key", ""),
                    "title": candidate.get("title", ""),
                    "reason": "no Zotero PDF attachment detected",
                    "status": "missing_fulltext",
                    "next_action": "locate PDF/full text or mark full_text_unavailable after review",
                    "notes": "metadata candidate only; cannot support synthesis",
                })
        elif candidate.get("pdf_url"):
            fulltext_ready_rows.append({
                "queued_at": now,
                "paper_id": paper_id,
                "zotero_item_key": "",
                "zotero_attachment_key": "",
                "title": candidate.get("title", ""),
                "availability": "candidate_url_unverified",
                "indexed_fulltext_chars": "0",
                "pdf_path_or_url": candidate.get("pdf_url", ""),
                "status": "needs_verification",
                "next_action": "fetch candidate URL and run full-text content/identity verification before extraction",
                "notes": "ROUTE_READY only; OA metadata/PDF URL is unverified and may be security_challenge, login_required, SPA shell, wrong PDF, or cache_mismatch",
            })
        else:
            missing_fulltext_rows.append({
                "queued_at": now,
                "paper_id": paper_id,
                "zotero_item_key": "",
                "title": candidate.get("title", ""),
                "reason": "metadata_only",
                "status": "missing_fulltext",
                "next_action": "locate PDF/full text, use Zotero/manual recovery, or mark unavailable after review",
                "notes": "metadata candidate only; cannot support synthesis",
            })
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
        "follow_up": "screen candidates, then obtain/read full text and write extraction cards before synthesis",
        "notes": "ROUTE_READY only; metadata/Zotero PDF availability is not literature review completion",
    }

    if args.dry_run:
        print(f"would log search in {search_path.relative_to(root)}")
        print(f"would add {len(new_rows)} new paper candidate(s) to {registry_path.relative_to(root)}")
        print(f"would queue {len(snowball_rows)} citation-neighborhood candidate(s) in {snowball_path.relative_to(root)}")
        print(f"would queue {len(fulltext_ready_rows)} full-text/PDF-verification item(s) in {fulltext_ready_path.relative_to(root)}")
        print(f"would queue {len(missing_fulltext_rows)} missing-fulltext item(s) in {missing_fulltext_path.relative_to(root)}")
        for row in new_rows[:10]:
            print(f"  - {row['paper_id']} {row['year']} {row['title'][:120]}")
        return 0

    _append_rows(search_path, SEARCH_LOG_COLUMNS, [search_row])
    if new_rows:
        _append_rows(registry_path, PAPER_REGISTRY_COLUMNS, new_rows)
    if snowball_rows:
        _append_rows(snowball_path, SNOWBALL_COLUMNS, snowball_rows)
    if fulltext_ready_rows:
        _append_rows(fulltext_ready_path, FULLTEXT_READY_COLUMNS, fulltext_ready_rows)
    if missing_fulltext_rows:
        _append_rows(missing_fulltext_path, MISSING_FULLTEXT_COLUMNS, missing_fulltext_rows)
    print(f"logged search -> {search_path.relative_to(root)}")
    print(f"added {len(new_rows)} paper candidate(s) -> {registry_path.relative_to(root)}")
    print(f"queued {len(snowball_rows)} citation-neighborhood candidate(s) -> {snowball_path.relative_to(root)}")
    print(f"queued {len(fulltext_ready_rows)} full-text/PDF-verification item(s) -> {fulltext_ready_path.relative_to(root)}")
    print(f"queued {len(missing_fulltext_rows)} missing-fulltext item(s) -> {missing_fulltext_path.relative_to(root)}")
    print("status_label: ROUTE_READY")
    print("does_not_prove: full-text review, extraction-card completion, synthesis, gap support, claim support, or gate approval")
    return 0
