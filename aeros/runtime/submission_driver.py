"""Submission research driver utilities for AEROS.

This module is intentionally conservative. It turns manuscript-facing
literature risks into review packets and checks. It does not certify that a
paper is true. The strongest guarantee it can enforce is narrower: every
manuscript sentence that cites a source must be traceable to a registered paper,
a full-text/extraction card, and a human-approved interpretation record that
shows how the cited source supports the sentence. Citation grounding is tiered:
plain bibliographic pointers are non-blocking, interpretive citations are
advisory unless weak, and claim-bearing citations are blocking until grounded.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - checks report this cleanly.
    yaml = None

MANUSCRIPT_GLOBS = [
    "paper/*.md",
    "paper/*.tex",
    "docs/manuscript*.md",
    "docs/manuscript*.tex",
]
INTERPRETATION_RECORD_DIR = Path("discovery/literature/interpretation_records")
EXTRACTION_CARD_DIR = Path("discovery/literature/extraction_cards")
SUPPORTED_INTERPRETATION_VERDICTS = {"faithful"}
WEAK_INTERPRETATION_VERDICTS = {"weak"}
FAILED_INTERPRETATION_VERDICTS = {"overclaimed", "unsupported", "interpretation_record_missing"}
VALID_SUPPORT_RELATIONS = {"direct_support", "partial_support", "background_only", "contradicts", "unsupported"}
VALID_SCOPE_VALUES = {"match", "partial", "mismatch", "unclear", "not_applicable"}
VALID_CLAIM_STRENGTH = {"pass", "weak", "fail"}
VALID_REVIEW_VERDICTS = {"faithful", "weak", "overclaimed", "unsupported"}
VALID_HUMAN_STATUS = {"pending", "approved", "rejected"}
VALID_CITATION_GROUNDING_TIERS = {"tier_0_bibliographic", "tier_1_interpretive", "tier_2_claim_bearing"}
CLAIM_BEARING_MARKERS = (
    " we find",
    " we show",
    " our result",
    " our estimate",
    " effect",
    " impact",
    " caus",
    " identification",
    " mechanism",
    " policy implication",
    " statistically significant",
    " robust",
    " supports our",
    " treatment",
    " coefficient",
)
INTERPRETIVE_MARKERS = (
    "finds",
    "shows",
    "argues",
    "documents",
    "uses",
    "estimates",
    "reports",
    "demonstrates",
    "suggests",
    "literature",
    "evidence",
    "method",
    "data",
    "limitation",
)
NONBLOCKING_SUPPORT_STATUSES = {"faithful", "bibliographic"}


@dataclass
class CitationFaithfulnessRow:
    sentence_id: str
    manuscript_path: str
    manuscript_sentence: str
    citation_key: str
    mapped_paper_id: str
    supporting_extraction_card: str
    extraction_support_status: str
    interpretation_record_path: str
    interpretation_status: str
    support_relation: str
    review_verdict: str
    human_status: str
    citation_grounding_tier: str
    mismatch_type: str
    blocking: bool
    support_status: str
    required_action: str
    notes: str


@dataclass
class WrapperSyncReport:
    status: str
    source_project: str
    source_cards: int
    wrapper_cards: int
    missing_cards: list[str]
    notes: list[str]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lowered = text.lower()
    return lowered in {"todo", "tbd", "placeholder", "n/a", "na", "none", "unknown"} or "placeholder" in lowered


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"yes", "true", "y", "1", "checked", "complete", "completed"}


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _paper_registry(root: Path) -> dict[str, dict[str, str]]:
    rows = _load_csv(root / "discovery/literature/paper_registry.csv")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        pid = (row.get("paper_id") or row.get("id") or "").strip()
        if pid:
            out[pid] = row
    return out


def _bib_key_to_paper_id(registry: dict[str, dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pid, row in registry.items():
        for key in ["bib_key", "citation_key", "bibtex_key", "key"]:
            val = (row.get(key) or "").strip()
            if val:
                out[val] = pid
        if pid:
            out.setdefault(pid, pid)
    return out


def _normalise_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _stable_sentence_id(path: str, sentence: str, citation_key: str) -> str:
    payload = f"{path}\n{_normalise_sentence(sentence)}\n{citation_key}".encode("utf-8")
    return "S_" + hashlib.sha256(payload).hexdigest()[:12].upper()


def _manuscript_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in MANUSCRIPT_GLOBS:
        files.extend(root.glob(pattern))
    return sorted({p for p in files if p.is_file()})


def _split_sentences(text: str) -> list[str]:
    # Keep this deliberately simple and deterministic. Citation-adjacent prose in
    # TeX/Markdown usually fits sentence-level splitting well enough for a review
    # queue; humans own the final interpretation record.
    compact = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?。！？])\s+", compact)
    return [p.strip() for p in parts if p.strip()]


def _citation_keys(sentence: str) -> list[str]:
    keys: list[str] = []
    # LaTeX cite commands.
    for match in re.finditer(r"\\(?:cite|citet|citep|citealp|citeauthor|citeyear|parencite|textcite)(?:\[[^\]]*\])*\{([^}]+)\}", sentence):
        for raw in match.group(1).split(","):
            key = raw.strip()
            if key:
                keys.append(key)
    # Pandoc markdown citations: [@key; @key2] and bare @key.
    for match in re.finditer(r"@([A-Za-z0-9_:\-\.]+)", sentence):
        key = match.group(1).strip().rstrip(".,;:)]}")
        if key and key not in keys:
            keys.append(key)
    return keys


def _extract_support_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            if current:
                sections[current] = "\n".join(buffer).strip()
            title = line.lstrip("#").strip().lower()
            current = title
            buffer = []
        else:
            buffer.append(raw)
    if current:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _card_for_paper(root: Path, paper_id: str) -> Path | None:
    if not paper_id:
        return None
    card_dir = root / EXTRACTION_CARD_DIR
    candidates = [
        card_dir / f"{paper_id}.md",
        card_dir / f"{paper_id}_extraction_card.md",
        card_dir / f"extraction_{paper_id}.md",
    ]
    candidates.extend(sorted(card_dir.glob(f"*{paper_id}*.md")))
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def _extraction_support_status(root: Path, paper_id: str) -> tuple[str, str, str]:
    card = _card_for_paper(root, paper_id)
    if not card:
        return "missing", "", "missing full-text extraction card"
    text = _read_text(card)
    sections = _extract_support_sections(text)
    support_text = "\n".join(
        value for key, value in sections.items()
        if "what this paper can support" in key or "direct evidence" in key or "evidence notes" in key
    ).strip()
    if not support_text or _is_placeholder(support_text):
        return "weak", str(card.relative_to(root)), "extraction card lacks source-bound support notes"
    return "faithful", str(card.relative_to(root)), "extraction card has source-bound support notes"


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        return {}
    try:
        loaded = yaml.safe_load(_read_text(path))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _interpretation_records(root: Path) -> dict[tuple[str, str], tuple[Path, dict[str, Any]]]:
    records: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    base = root / INTERPRETATION_RECORD_DIR
    if not base.exists():
        return records
    for path in sorted(list(base.glob("*.yml")) + list(base.glob("*.yaml"))):
        data = _load_yaml(path)
        sid = str(data.get("sentence_id") or "").strip()
        key = str(data.get("citation_key") or "").strip()
        if sid and key:
            records[(sid, key)] = (path, data)
    return records


def _scope_failures(scope_match: Any) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    weak: list[str] = []
    if not isinstance(scope_match, dict):
        return ["scope_match missing"], []
    for dim in ["geography", "population", "time_period", "method", "outcome"]:
        val = str(scope_match.get(dim) or "").strip().lower()
        if val not in VALID_SCOPE_VALUES:
            hard.append(f"scope_match.{dim} invalid_or_missing")
        elif val == "mismatch":
            hard.append(f"scope_match.{dim} mismatch")
        elif val == "unclear":
            weak.append(f"scope_match.{dim} unclear")
    return hard, weak


def _citation_grounding_tier(sentence: str, record_data: dict[str, Any] | None = None) -> str:
    if isinstance(record_data, dict):
        explicit = str(record_data.get("citation_grounding_tier") or "").strip().lower()
        if explicit in VALID_CITATION_GROUNDING_TIERS:
            return explicit
    lowered = f" {_normalise_sentence(sentence).lower()} "
    if any(marker in lowered for marker in CLAIM_BEARING_MARKERS):
        return "tier_2_claim_bearing"
    if any(marker in lowered for marker in INTERPRETIVE_MARKERS):
        return "tier_1_interpretive"
    return "tier_0_bibliographic"


def _mismatch_type_from_notes(notes: list[str]) -> str:
    joined = "; ".join(notes).lower()
    buckets: list[str] = []
    mapping = [
        ("geography", "geography_mismatch"),
        ("population", "population_mismatch"),
        ("time_period", "time_period_mismatch"),
        ("method", "method_mismatch"),
        ("outcome", "outcome_mismatch"),
        ("claim_strength", "claim_strength_mismatch"),
        ("overclaim", "overclaim"),
        ("unsupported", "unsupported"),
        ("contradicts", "contradiction"),
        ("scope_match", "scope_mismatch"),
        ("full-text extraction", "missing_extraction"),
        ("interpretation record", "missing_interpretation"),
        ("paper_registry", "unmapped_citation"),
    ]
    for needle, bucket in mapping:
        if needle in joined and bucket not in buckets:
            buckets.append(bucket)
    return ";".join(buckets) if buckets else "none"


def _interpretation_status(
    root: Path,
    record_entry: tuple[Path, dict[str, Any]] | None,
    *,
    sentence_id: str,
    manuscript_path: str,
    sentence: str,
    citation_key: str,
    paper_id: str,
) -> tuple[str, str, str, str, str, str, str]:
    if record_entry is None:
        return (
            "interpretation_record_missing",
            "create and approve a literature interpretation record for this cited sentence",
            "no interpretation record found for sentence_id+citation_key",
            "",
            "",
            "",
            "",
        )
    path, data = record_entry
    rel = str(path.relative_to(root))
    hard: list[str] = []
    weak: list[str] = []

    if str(data.get("sentence_id") or "").strip() != sentence_id:
        hard.append("sentence_id mismatch")
    if str(data.get("manuscript_path") or "").strip() != manuscript_path:
        hard.append("manuscript_path mismatch")
    if _normalise_sentence(str(data.get("manuscript_sentence") or "")) != _normalise_sentence(sentence):
        hard.append("manuscript_sentence mismatch")
    if str(data.get("citation_key") or "").strip() != citation_key:
        hard.append("citation_key mismatch")
    if str(data.get("paper_id") or "").strip() != paper_id:
        hard.append("paper_id mismatch")

    source_passage = data.get("source_passage") if isinstance(data.get("source_passage"), dict) else {}
    if _is_placeholder(source_passage.get("page_or_section")):
        hard.append("source_passage.page_or_section missing")
    if _is_placeholder(source_passage.get("quote_or_paraphrase_basis")):
        hard.append("source_passage.quote_or_paraphrase_basis missing")
    if _is_placeholder(data.get("our_interpretation")):
        hard.append("our_interpretation missing")

    support_relation = str(data.get("support_relation") or "").strip().lower()
    if support_relation not in VALID_SUPPORT_RELATIONS:
        hard.append("support_relation invalid")
    elif support_relation != "direct_support":
        if support_relation in {"contradicts", "unsupported"}:
            hard.append(f"support_relation={support_relation}")
        else:
            weak.append(f"support_relation={support_relation}")

    scope_hard, scope_weak = _scope_failures(data.get("scope_match"))
    hard.extend(scope_hard)
    weak.extend(scope_weak)

    claim_strength = str(data.get("claim_strength_match") or "").strip().lower()
    if claim_strength not in VALID_CLAIM_STRENGTH:
        hard.append("claim_strength_match invalid_or_missing")
    elif claim_strength == "fail":
        hard.append("claim_strength_match=fail")
    elif claim_strength == "weak":
        weak.append("claim_strength_match=weak")

    overclaim_flags = data.get("overclaim_flags")
    if overclaim_flags is None:
        overclaim_flags = []
    if not isinstance(overclaim_flags, list):
        hard.append("overclaim_flags must be a list")
    elif overclaim_flags:
        hard.append("overclaim_flags present")

    if not _truthy(data.get("limitations_checked")):
        hard.append("limitations_checked missing")
    if not _truthy(data.get("contradictory_evidence_checked")):
        hard.append("contradictory_evidence_checked missing")

    review_verdict = str(data.get("review_verdict") or "").strip().lower()
    human_status = str(data.get("human_status") or "").strip().lower()
    if review_verdict not in VALID_REVIEW_VERDICTS:
        hard.append("review_verdict invalid_or_missing")
    elif review_verdict != "faithful":
        hard.append(f"review_verdict={review_verdict}")
    if human_status not in VALID_HUMAN_STATUS:
        hard.append("human_status invalid_or_missing")
    elif human_status != "approved":
        hard.append(f"human_status={human_status}")
    if human_status == "approved":
        if _is_placeholder(data.get("reviewer")):
            hard.append("reviewer missing for approved record")
        if _is_placeholder(data.get("reviewed_at")):
            hard.append("reviewed_at missing for approved record")

    if hard:
        if any("unsupported" in item or "contradicts" in item or "overclaim" in item for item in hard):
            status = "overclaimed"
        else:
            status = "unsupported"
        action = "revise manuscript sentence or fix/approve interpretation record"
        notes = "; ".join(hard + weak)
    elif weak:
        status = "weak"
        action = "revise sentence to include source limitations or approve as weak/background citation"
        notes = "; ".join(weak)
    else:
        status = "faithful"
        action = "none"
        notes = "human-approved interpretation record supports the cited sentence"
    return status, action, notes, rel, support_relation, review_verdict, human_status


def build_citation_faithfulness_rows(root: Path | str = Path.cwd()) -> list[CitationFaithfulnessRow]:
    root = Path(root)
    registry = _paper_registry(root)
    bib_map = _bib_key_to_paper_id(registry)
    records = _interpretation_records(root)
    rows: list[CitationFaithfulnessRow] = []

    for manuscript in _manuscript_files(root):
        rel = str(manuscript.relative_to(root))
        text = _read_text(manuscript)
        for sentence in _split_sentences(text):
            keys = _citation_keys(sentence)
            if not keys:
                continue
            for key in keys:
                sid = _stable_sentence_id(rel, sentence, key)
                record_entry = records.get((sid, key))
                record_data = record_entry[1] if record_entry else None
                tier = _citation_grounding_tier(sentence, record_data)
                paper_id = bib_map.get(key, "")
                card_status = "missing"
                card_path = ""
                card_notes = ""
                interpretation_status = "interpretation_record_missing"
                interpretation_action = "create and approve a literature interpretation record for this cited sentence"
                interpretation_notes = "no interpretation record found"
                interpretation_path = ""
                support_relation = ""
                review_verdict = ""
                human_status = ""
                support_status = "unsupported"
                required_action = "map citation key to paper_registry and create interpretation record"
                blocking = False
                notes: list[str] = []

                if not paper_id:
                    blocking = True
                    notes.append("citation key is not mapped to a paper_registry row")
                elif tier == "tier_0_bibliographic":
                    card_status = "not_required"
                    interpretation_status = "not_required"
                    support_relation = "bibliographic_only"
                    review_verdict = "not_required"
                    human_status = "not_required"
                    support_status = "bibliographic"
                    required_action = "none"
                    notes.append("bibliographic citation: registry mapping is sufficient; no claim support is inferred")
                else:
                    card_status, card_path, card_notes = _extraction_support_status(root, paper_id)
                    if card_status != "faithful":
                        notes.append(card_notes)
                    interpretation_status, interpretation_action, interpretation_notes, interpretation_path, support_relation, review_verdict, human_status = _interpretation_status(
                        root,
                        record_entry,
                        sentence_id=sid,
                        manuscript_path=rel,
                        sentence=sentence,
                        citation_key=key,
                        paper_id=paper_id,
                    )
                    if interpretation_status != "faithful":
                        notes.append(interpretation_notes)

                    if card_status == "faithful" and interpretation_status == "faithful":
                        support_status = "faithful"
                        required_action = "none"
                        notes.append("citation has registry mapping, extraction support, and approved interpretation record")
                    elif card_status == "faithful" and interpretation_status == "weak":
                        support_status = "weak"
                        required_action = interpretation_action
                    elif card_status == "weak" or interpretation_status == "weak":
                        support_status = "weak"
                        required_action = interpretation_action if interpretation_status != "faithful" else "strengthen extraction support notes"
                    else:
                        support_status = interpretation_status if interpretation_status in FAILED_INTERPRETATION_VERDICTS | WEAK_INTERPRETATION_VERDICTS else "unsupported"
                        required_action = interpretation_action

                    if tier == "tier_2_claim_bearing" and support_status != "faithful":
                        blocking = True

                mismatch_type = _mismatch_type_from_notes(notes)
                if tier == "tier_1_interpretive" and support_status not in NONBLOCKING_SUPPORT_STATUSES and required_action == "none":
                    required_action = "review interpretive citation grounding before final submission"
                rows.append(CitationFaithfulnessRow(
                    sentence_id=sid,
                    manuscript_path=rel,
                    manuscript_sentence=_normalise_sentence(sentence),
                    citation_key=key,
                    mapped_paper_id=paper_id,
                    supporting_extraction_card=card_path,
                    extraction_support_status=card_status,
                    interpretation_record_path=interpretation_path,
                    interpretation_status=interpretation_status,
                    support_relation=support_relation,
                    review_verdict=review_verdict,
                    human_status=human_status,
                    citation_grounding_tier=tier,
                    mismatch_type=mismatch_type,
                    blocking=blocking,
                    support_status=support_status,
                    required_action=required_action,
                    notes="; ".join(n for n in notes if n),
                ))
    return rows

def build_citation_faithfulness(root: Path | str = Path.cwd()) -> dict[str, Any]:
    rows = build_citation_faithfulness_rows(root)
    failures = [asdict(row) for row in rows if row.blocking]
    weak = [asdict(row) for row in rows if not row.blocking and row.support_status not in NONBLOCKING_SUPPORT_STATUSES]
    missing_interpretation = [
        asdict(row)
        for row in rows
        if row.citation_grounding_tier != "tier_0_bibliographic" and row.interpretation_status == "interpretation_record_missing"
    ]
    tier_counts = {tier: sum(1 for row in rows if row.citation_grounding_tier == tier) for tier in sorted(VALID_CITATION_GROUNDING_TIERS)}
    return {
        "status": "pass" if not failures else "fail",
        "rows": [asdict(row) for row in rows],
        "failures": failures,
        "weak": weak,
        "summary": {
            "total_cited_sentences": len(rows),
            "faithful": sum(1 for row in rows if row.support_status == "faithful"),
            "bibliographic": sum(1 for row in rows if row.support_status == "bibliographic"),
            "weak": len(weak),
            "failed": len(failures),
            "blocking_failures": len(failures),
            "nonblocking_weak": len(weak),
            "missing_interpretation_records": len(missing_interpretation),
            "tier_counts": tier_counts,
        },
        "does_not_prove": [
            "cited sources are true",
            "human interpretation records are correct beyond their recorded review basis",
            "tier classification is a substitute for human manuscript judgment",
            "submission readiness outside citation grounding",
        ],
    }

def _source_project(root: Path) -> Path | None:
    # Environment variable is intentionally avoided here so checks stay deterministic
    # unless the caller configures project_manifest/adoption metadata.
    for rel in ["adoption/source_manifest.yml", "project_manifest.yml"]:
        path = root / rel
        if not path.exists() or yaml is None:
            continue
        data = _load_yaml(path)
        candidates: list[Any] = []
        if isinstance(data.get("source_project"), dict):
            candidates.append(data["source_project"].get("path"))
        if isinstance(data.get("adoption"), dict):
            candidates.append(data["adoption"].get("source_project_path"))
        if isinstance(data.get("aeros"), dict):
            candidates.append(data["aeros"].get("source_project_path"))
        for candidate in candidates:
            if candidate:
                p = Path(str(candidate)).expanduser()
                if not p.is_absolute():
                    p = (root / p).resolve()
                if p.exists() and p.is_dir() and p != root:
                    return p
    return None


def _card_ids(base: Path) -> set[str]:
    card_dir = base / EXTRACTION_CARD_DIR
    if not card_dir.exists():
        return set()
    ids: set[str] = set()
    for path in card_dir.glob("*.md"):
        name = path.stem
        name = name.replace("_extraction_card", "").replace("extraction_", "")
        ids.add(name)
    return ids


def build_literature_wrapper_sync_report(root: Path | str = Path.cwd()) -> WrapperSyncReport:
    root = Path(root)
    source = _source_project(root)
    if source is None:
        return WrapperSyncReport(
            status="inactive",
            source_project="",
            source_cards=0,
            wrapper_cards=len(_card_ids(root)),
            missing_cards=[],
            notes=["no source project configured; wrapper sync check is inactive"],
        )
    source_ids = _card_ids(source)
    wrapper_ids = _card_ids(root)
    missing = sorted(source_ids - wrapper_ids)
    status = "pass" if not missing else "fail"
    notes = [] if not missing else ["wrapper is missing source-project extraction cards"]
    return WrapperSyncReport(
        status=status,
        source_project=str(source),
        source_cards=len(source_ids),
        wrapper_cards=len(wrapper_ids),
        missing_cards=missing,
        notes=notes,
    )


def build_literature_wrapper_sync(root: Path | str = Path.cwd()) -> dict[str, Any]:
    report = build_literature_wrapper_sync_report(root)
    failures = [f"missing wrapper extraction card for source paper {pid}" for pid in report.missing_cards]
    return {
        "status": report.status,
        "source_project": report.source_project,
        "source_card_count": report.source_cards,
        "wrapper_card_count": report.wrapper_cards,
        "missing_cards": report.missing_cards,
        "failures": failures,
        "notes": report.notes,
        "does_not_prove": [
            "source-project extraction cards are correct",
            "wrapper literature synthesis is complete",
            "citation claims are faithful",
        ],
    }


def build_submission_driver(root: Path | str = Path.cwd()) -> dict[str, Any]:
    root = Path(root)
    citation_rows = build_citation_faithfulness_rows(root)
    wrapper = build_literature_wrapper_sync_report(root)
    failures = [row for row in citation_rows if row.blocking]
    weak = [row for row in citation_rows if not row.blocking and row.support_status not in NONBLOCKING_SUPPORT_STATUSES]
    missing_interpretation = [
        row for row in citation_rows
        if row.citation_grounding_tier != "tier_0_bibliographic" and row.interpretation_status == "interpretation_record_missing"
    ]
    tier_counts = {tier: sum(1 for row in citation_rows if row.citation_grounding_tier == tier) for tier in sorted(VALID_CITATION_GROUNDING_TIERS)}
    priorities: list[dict[str, str]] = []
    if failures:
        priorities.append({
            "priority": "P0",
            "action": "run manuscript citation grounding audit",
            "command": "python3 checks/check_manuscript_citation_interpretation.py",
            "reason": "claim-bearing cited sentences are not all backed by approved interpretation records",
            "stop_condition": "every tier_2_claim_bearing citation has registry mapping, extraction support, and faithful approved interpretation record",
        })
    if wrapper.status == "fail":
        priorities.append({
            "priority": "P0",
            "action": "sync literature wrapper evidence visibility",
            "command": "python3 checks/check_literature_wrapper_sync.py",
            "reason": "source project has extraction cards not visible in the wrapper",
            "stop_condition": "wrapper source-card gap is zero or explicitly waived",
        })
    if weak:
        priorities.append({
            "priority": "P1",
            "action": "review non-blocking interpretive citation weaknesses",
            "command": "python3 -m aeros.cli paper citation-faithfulness",
            "reason": "tier_1/background citation weaknesses should be resolved before final submission but do not block research execution",
            "stop_condition": "non-blocking weak citation count is zero or explicitly accepted by human review",
        })
    if not priorities:
        priorities.append({
            "priority": "P1",
            "action": "continue submission readiness with claim and writing audit",
            "command": "python3 -m aeros.cli next --lane writing",
            "reason": "citation-grounding blockers are not currently active",
            "stop_condition": "next writing/claim audit packet generated",
        })
    return {
        "status": "blocked" if failures or wrapper.status == "fail" else "ready",
        "citation_faithfulness": {
            "rows": [asdict(row) for row in citation_rows],
            "total_cited_sentences": len(citation_rows),
            "faithful": sum(1 for row in citation_rows if row.support_status == "faithful"),
            "bibliographic": sum(1 for row in citation_rows if row.support_status == "bibliographic"),
            "weak": len(weak),
            "failed": len(failures),
            "blocking_failures": len(failures),
            "nonblocking_weak": len(weak),
            "missing_interpretation_records": len(missing_interpretation),
            "tier_counts": tier_counts,
        },
        "literature_wrapper_sync": asdict(wrapper),
        "recommended_priorities": priorities,
        "does_not_prove": [
            "cited sources are true",
            "paper claims are scientifically valid",
            "human interpretation records are correct beyond their recorded review basis",
            "citation tier inference replaces human submission judgment",
            "submission readiness outside citation/literature visibility risks",
        ],
    }

def write_submission_driver(root: Path | str = Path.cwd(), *, write: bool = True) -> dict[str, Any]:
    root = Path(root)
    report = build_submission_driver(root)
    if not write:
        return report
    out_dir = root / "audits/submission_driver"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "submission_research_driver.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = report["citation_faithfulness"]["rows"]
    csv_path = out_dir / "manuscript_citation_faithfulness.csv"
    fieldnames = [
        "sentence_id",
        "manuscript_path",
        "manuscript_sentence",
        "citation_key",
        "mapped_paper_id",
        "supporting_extraction_card",
        "extraction_support_status",
        "interpretation_record_path",
        "interpretation_status",
        "support_relation",
        "review_verdict",
        "human_status",
        "citation_grounding_tier",
        "mismatch_type",
        "blocking",
        "support_status",
        "required_action",
        "notes",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    md = format_submission_driver(report)
    (out_dir / "submission_research_driver.md").write_text(md + "\n", encoding="utf-8")
    return report


def format_submission_driver(report: dict[str, Any]) -> str:
    citation = report["citation_faithfulness"]
    wrapper = report["literature_wrapper_sync"]
    lines = [
        "# Submission Research Driver",
        "",
        f"Status: {report['status']}",
        "",
        "## Manuscript citation faithfulness",
        f"- cited sentence rows: {citation['total_cited_sentences']}",
        f"- faithful: {citation['faithful']}",
        f"- bibliographic only: {citation.get('bibliographic', 0)}",
        f"- weak non-blocking: {citation.get('nonblocking_weak', citation['weak'])}",
        f"- blocking failures: {citation.get('blocking_failures', citation['failed'])}",
        f"- missing interpretation records: {citation['missing_interpretation_records']}",
        f"- tier counts: {citation.get('tier_counts', {})}",
        "",
        "## Literature wrapper sync",
        f"- status: {wrapper['status']}",
        f"- source project: {wrapper['source_project'] or '<none>'}",
        f"- source cards: {wrapper['source_cards']}",
        f"- wrapper cards: {wrapper['wrapper_cards']}",
        f"- missing cards: {len(wrapper['missing_cards'])}",
        "",
        "## Recommended priorities",
    ]
    for item in report["recommended_priorities"]:
        lines.extend([
            f"- {item['priority']}: {item['action']}",
            f"  command: `{item['command']}`",
            f"  reason: {item['reason']}",
            f"  stop: {item['stop_condition']}",
        ])
    lines.extend(["", "## Boundary", "This driver does not certify scientific truth or submission readiness. It only surfaces literature-grounding and wrapper-visibility risks."])
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_submission_driver(write_submission_driver(Path.cwd(), write=False)))
