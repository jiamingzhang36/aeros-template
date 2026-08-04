"""Sentence-level, source-grounded manuscript fact checking.

This module compiles AEROS's existing citation grounding, interpretation, and
risk-tier rules into one executable workflow.  It may verify exact source
passages and expose explicit contradictions; it never edits manuscripts,
claims, interpretation records, or approvals.
"""

from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from .citation_sentence_grounding import build_sentence_citation_grounding


MODEL = "AEROS-GROUNDED-FACT-CHECK-001"
REGISTRY = Path("discovery/literature/paper_registry.csv")
LOCAL_SOURCE_COLUMNS = (
    "source_snapshot", "snapshot_path", "source_or_path", "full_text_path",
    "local_path", "pdf_path_or_url", "opened_source",
)
URL_COLUMNS = ("stable_url", "source_url", "url", "pdf_url")
PASS_SUPPORT = {"grounded", "bibliographic", "metadata_only", "route_admission_ok", "related_literature_ok"}
CONTRADICTED_SUPPORT = {"overclaimed", "unsupported", "contradicted", "contradiction"}
MAX_REMOTE_BYTES = 8 * 1024 * 1024


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _registry(root: Path) -> dict[str, dict[str, str]]:
    path = root / REGISTRY
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {
            str(row.get("paper_id") or row.get("id") or "").strip(): row
            for row in csv.DictReader(handle)
            if str(row.get("paper_id") or row.get("id") or "").strip()
        }


def _interpretation(root: Path, relative_path: str) -> dict[str, Any]:
    if not relative_path or yaml is None:
        return {}
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return {}
    if not path.is_file():
        return {}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _passage(record: dict[str, Any]) -> tuple[str, str]:
    source = record.get("source_passage")
    if isinstance(source, dict):
        return (
            str(source.get("quote_or_paraphrase_basis") or "").strip(),
            str(source.get("page_or_section") or "").strip(),
        )
    return str(source or record.get("quoted_passage") or "").strip(), str(
        record.get("page") or record.get("locator") or record.get("page_or_table") or ""
    ).strip()


def _safe_public_url(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False, "only credential-free public HTTPS sources are fetchable"
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except OSError as exc:
        return False, f"source hostname could not be resolved: {exc}"
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, "private, local, reserved, and link-local source addresses are denied"
    return True, ""


def _pdf_text(data: bytes) -> tuple[str, str]:
    binary = shutil.which("pdftotext")
    if not binary:
        return "", "PDF retrieved but pdftotext is unavailable"
    with tempfile.TemporaryDirectory(prefix="aeros_fact_check_") as name:
        source = Path(name) / "source.pdf"
        target = Path(name) / "source.txt"
        source.write_bytes(data)
        run = subprocess.run([binary, str(source), str(target)], capture_output=True, text=True, timeout=45, check=False)
        if run.returncode != 0 or not target.exists():
            return "", f"PDF text extraction failed: {run.stderr.strip() or run.returncode}"
        return target.read_text(encoding="utf-8", errors="ignore"), ""


def _decode_source(data: bytes, content_type: str, locator: str) -> tuple[str, str]:
    low = content_type.lower()
    if data.startswith(b"%PDF-") or "application/pdf" in low or locator.lower().endswith(".pdf"):
        return _pdf_text(data)
    decoded = data.decode("utf-8", errors="ignore")
    if "html" in low or "<html" in decoded[:1000].lower():
        parser = _TextExtractor()
        parser.feed(decoded)
        return " ".join(parser.parts), ""
    return decoded, ""


def _load_source(root: Path, registry_row: dict[str, str], record: dict[str, Any], allow_network: bool) -> dict[str, Any]:
    candidates: list[str] = []
    for key in ("source_path", "source_document", "opened_source", "source_snapshot"):
        value = str(record.get(key) or "").strip()
        if value:
            candidates.append(value)
    candidates.extend(str(registry_row.get(key) or "").strip() for key in LOCAL_SOURCE_COLUMNS)
    candidates.extend(str(registry_row.get(key) or "").strip() for key in URL_COLUMNS)
    seen: set[str] = set()
    for locator in candidates:
        if not locator or locator in seen:
            continue
        seen.add(locator)
        parsed = urlparse(locator)
        if parsed.scheme in {"http", "https"}:
            if not allow_network:
                continue
            safe, reason = _safe_public_url(locator)
            if not safe:
                return {"status": "blocked", "locator": locator, "reason": reason}
            try:
                request = Request(locator, headers={"User-Agent": "AEROS-grounded-fact-check/1.0"})
                with urlopen(request, timeout=25) as response:  # noqa: S310 - guarded public HTTPS only
                    final_url = response.geturl()
                    safe_final, final_reason = _safe_public_url(final_url)
                    if not safe_final:
                        return {"status": "blocked", "locator": final_url, "reason": final_reason}
                    data = response.read(MAX_REMOTE_BYTES + 1)
                    content_type = response.headers.get("Content-Type", "")
                if len(data) > MAX_REMOTE_BYTES:
                    return {"status": "blocked", "locator": final_url, "reason": "source exceeds retrieval byte limit"}
                text, reason = _decode_source(data, content_type, final_url)
                if text.strip():
                    return {"status": "loaded", "locator": final_url, "text": text, "sha256": hashlib.sha256(data).hexdigest()}
                return {"status": "unreadable", "locator": final_url, "reason": reason or "source contains no readable text"}
            except Exception as exc:
                return {"status": "unavailable", "locator": locator, "reason": f"source retrieval failed: {exc}"}
        path = Path(locator).expanduser()
        if not path.is_absolute():
            path = root / path
        try:
            path = path.resolve()
            path.relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        text, reason = _decode_source(data, "", str(path))
        if text.strip():
            return {
                "status": "loaded", "locator": str(path.relative_to(root.resolve())),
                "text": text, "sha256": hashlib.sha256(data).hexdigest(),
            }
        return {"status": "unreadable", "locator": str(path), "reason": reason or "source contains no readable text"}
    return {"status": "unavailable", "locator": "", "reason": "no readable local source; use --allow-network or recover full text"}


def _tier(row: dict[str, Any]) -> str:
    required = str(row.get("required_evidence") or "")
    function = str(row.get("citation_function") or "")
    if "independent_verification" in required or function in {"result_claim", "mechanism_claim", "number_fact", "literature_gap"}:
        return "tier_2_claim_bearing"
    if "source_passage" in required or function in {"method_precedent", "data_source", "legal_fact", "policy_fact"}:
        return "tier_1_interpretive"
    return "tier_0_bibliographic"


def _independent_ok(record: dict[str, Any], source_sha256: str) -> tuple[bool, str]:
    value = record.get("independent_verification")
    if not isinstance(value, dict):
        return False, "independent_verification missing"
    if not bool(value.get("independent_of_producer")):
        return False, "independent verifier is not attested independent"
    verdict = str(value.get("verdict") or "").strip().lower()
    if verdict not in {"faithful", "direct_support", "supports"}:
        return False, "independent verifier did not return faithful"
    if not str(value.get("verifier") or "").strip() or not str(value.get("verified_at") or "").strip():
        return False, "independent verifier metadata missing"
    fingerprint = str(value.get("source_fingerprint") or "").strip().lower().removeprefix("sha256:")
    if fingerprint and re.fullmatch(r"[0-9a-f]{64}", fingerprint) and fingerprint != source_sha256:
        return False, "independent verifier source fingerprint is stale"
    return True, "independent verifier floor satisfied"


def build_grounded_fact_check(
    root: Path | str = Path.cwd(), *, manuscript: str = "", allow_network: bool = False,
) -> dict[str, Any]:
    root = Path(root).resolve()
    grounding = build_sentence_citation_grounding(root)
    selected = str(Path(manuscript)) if manuscript else ""
    rows = [row for row in grounding.get("rows", []) if not selected or str(row.get("manuscript_path")) == selected]
    registry = _registry(root)
    source_cache: dict[tuple[str, bool], dict[str, Any]] = {}
    checked: list[dict[str, Any]] = []
    for row in rows:
        tier = _tier(row)
        support = str(row.get("support_status") or "").strip().lower()
        record = _interpretation(root, str(row.get("interpretation_record") or ""))
        passage, locator = _passage(record)
        paper_id = str(row.get("mapped_paper_id") or "")
        verification_scope = "bibliographic identity only"
        status = "UNRESOLVED"
        reason = str(row.get("notes") or "citation evidence is incomplete")
        source: dict[str, Any] = {"status": "not_required", "locator": "", "sha256": ""}
        passage_match = False
        if support in CONTRADICTED_SUPPORT:
            status = "CONTRADICTED"
            reason = "existing source-bound interpretation marks this manuscript use unsupported or overclaimed"
        elif tier == "tier_0_bibliographic" and paper_id and support in PASS_SUPPORT:
            status = "VERIFIED"
            reason = "citation identity is registered; semantic support was not asserted"
        elif paper_id:
            cache_key = (paper_id, allow_network)
            if cache_key not in source_cache:
                source_cache[cache_key] = _load_source(root, registry.get(paper_id, {}), record, allow_network)
            source = source_cache[cache_key]
            source_text = str(source.get("text") or "")
            passage_match = bool(passage and _normalise(passage) in _normalise(source_text))
            verification_scope = "source passage and sentence-support boundary"
            if source.get("status") != "loaded":
                reason = str(source.get("reason") or "source unavailable")
            elif not passage:
                reason = "interpretation record has no source passage"
            elif not passage_match:
                reason = "recorded passage was not found verbatim in the retrieved source; paraphrase entailment remains unresolved"
            elif support not in PASS_SUPPORT:
                reason = f"existing grounding status is {support or 'missing'}"
            elif tier == "tier_2_claim_bearing":
                independent, independent_reason = _independent_ok(record, str(source.get("sha256") or ""))
                if independent:
                    status = "VERIFIED"
                    reason = independent_reason
                else:
                    reason = independent_reason
            else:
                status = "VERIFIED"
                reason = "recorded passage was found in source and Tier-1 interpretation requirements passed"
        checked.append({
            **row,
            "citation_tier": tier,
            "fact_check_status": status,
            "verification_scope": verification_scope,
            "source_locator": source.get("locator", ""),
            "source_sha256": source.get("sha256", ""),
            "passage_locator": locator,
            "passage_match": passage_match,
            "fact_check_reason": reason,
        })
    counts = {value: sum(1 for row in checked if row["fact_check_status"] == value) for value in ("VERIFIED", "CONTRADICTED", "UNRESOLVED")}
    blocking_unresolved = sum(1 for row in checked if row["fact_check_status"] == "UNRESOLVED" and bool(row.get("blocking")))
    overall = "FAIL" if counts["CONTRADICTED"] else ("BLOCKED" if blocking_unresolved else "PASS")
    return {
        "model": MODEL,
        "status": overall,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manuscript": selected or "all discovered manuscripts",
        "network_retrieval": "enabled_public_https" if allow_network else "disabled_local_sources_only",
        "counts": {**counts, "blocking_unresolved": blocking_unresolved, "total": len(checked)},
        "rows": checked,
        "does_not_prove": [
            "scientific truth or causal identification",
            "semantic entailment for unresolved paraphrases",
            "completeness of external source discovery",
            "human approval, claim admission, paper readiness, or release authority",
        ],
    }


def write_grounded_fact_check(root: Path | str, report: dict[str, Any]) -> dict[str, str]:
    root = Path(root)
    audit_dir = root / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_path = audit_dir / "manuscript_fact_check.json"
    queue_path = audit_dir / "manuscript_fact_check_queue.csv"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = [
        "sentence_id", "manuscript_path", "line", "citation_key", "mapped_paper_id",
        "citation_tier", "fact_check_status", "manuscript_sentence", "source_locator",
        "passage_locator", "fact_check_reason", "required_action",
    ]
    with queue_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report.get("rows", []):
            if row.get("fact_check_status") != "VERIFIED":
                writer.writerow({field: row.get(field, "") for field in fields})
    return {"report": str(report_path.relative_to(root)), "human_queue": str(queue_path.relative_to(root))}
