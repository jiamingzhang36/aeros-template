"""Sentence-level manuscript citation grounding.

This module upgrades citation checking from registry/card existence to a
sentence-level grounding queue. It parses manuscript sentences, extracts citation
keys, maps each key to paper_registry rows and extraction cards, classifies the
citation function, and checks the function-specific evidence requirement.

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
REQUIREMENTS = Path("harness/citation_function_requirements.yml")

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
STRONG_FUNCTIONS = {"method_precedent", "data_source", "result_claim", "mechanism_claim", "number_fact", "literature_gap"}
TIER_1_FUNCTIONS = {"related_literature", "method_precedent", "data_source", "policy_fact", "legal_fact"}

DEFAULT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "metadata_only": {"required_evidence": ["registry_metadata"], "blocking": False, "allowed_status": "metadata_only_ok"},
    "background_pointer": {"required_evidence": ["registry_metadata"], "blocking": False, "allowed_status": "background_ok"},
    "related_literature": {"required_evidence": ["registry_metadata"], "blocking": False, "allowed_status": "related_literature_ok"},
    "method_precedent": {"required_evidence": ["registry_metadata", "extraction_card", "source_passage", "automated_interpretation"], "blocking": True, "allowed_status": "grounded"},
    "data_source": {"required_evidence": ["registry_metadata", "extraction_card"], "blocking": True, "allowed_status": "grounded_or_snapshot_backed"},
    "result_claim": {"required_evidence": ["registry_metadata", "extraction_card", "source_passage", "approved_interpretation"], "blocking": True, "allowed_status": "grounded"},
    "mechanism_claim": {"required_evidence": ["registry_metadata", "extraction_card", "source_passage", "approved_interpretation"], "blocking": True, "allowed_status": "grounded"},
    "number_fact": {"required_evidence": ["registry_metadata", "extraction_card", "source_passage", "approved_interpretation"], "blocking": True, "allowed_status": "grounded"},
    "policy_fact": {"required_evidence": ["registry_metadata"], "blocking": False, "allowed_status": "policy_source_ok"},
    "legal_fact": {"required_evidence": ["registry_metadata"], "blocking": False, "allowed_status": "legal_source_ok"},
    "literature_gap": {"required_evidence": ["registry_metadata", "extraction_card", "source_passage", "approved_interpretation"], "blocking": True, "allowed_status": "grounded"},
}

PASS_STATUSES = {
    "grounded",
    "metadata_only_ok",
    "background_ok",
    "related_literature_ok",
    "policy_source_ok",
    "legal_source_ok",
    "route_admission_ok",
}

DOES_NOT_PROVE = [
    "that the cited source is true",
    "that human interpretation is correct beyond the recorded source passage",
    "that uncited manuscript claims are grounded",
    "that citation-function inference is perfect",
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
    citation_function: str
    required_evidence: str
    available_evidence: str
    source_type: str
    risk_level: str
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


def _load_requirements(root: Path) -> dict[str, dict[str, Any]]:
    path = root / REQUIREMENTS
    if yaml is None or not path.exists():
        return DEFAULT_REQUIREMENTS
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return DEFAULT_REQUIREMENTS
    functions = data.get("functions") if isinstance(data, dict) else {}
    if not isinstance(functions, dict):
        return DEFAULT_REQUIREMENTS
    merged = {key: dict(value) for key, value in DEFAULT_REQUIREMENTS.items()}
    for key, value in functions.items():
        if isinstance(value, dict):
            merged[str(key)] = {**merged.get(str(key), {}), **value}
    return merged


def _manuscripts(root: Path) -> list[Path]:
    out: list[Path] = []
    for pattern in MANUSCRIPT_GLOBS:
        out.extend(p for p in root.glob(pattern) if p.is_file())
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
    for match in re.finditer(r"(?<![A-Za-z0-9._%+\-])@([A-Za-z0-9_:\-.]+)", sentence):
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


def _source_type(row: dict[str, str]) -> str:
    for col in ("source_type", "publication_type", "type", "source_kind"):
        val = (row.get(col) or "").strip().lower()
        if val:
            return val
    locator = " ".join((row.get(col) or "") for col in ("url", "source_or_path", "stable_url", "doi", "title")).lower()
    if any(token in locator for token in ("usda", "fda", "epa", "gov", "regulation", "statute", "code of federal")):
        return "official_source"
    return "academic_paper"


def _semantic_sentence_text(sentence: str) -> str:
    text = re.sub(
        r"\\(?:cite|citet|citep|citealp|citeauthor|citeyear|parencite|textcite|autocite|footcite)(?:\[[^\]]*\])*\{[^}]*\}",
        " ",
        sentence,
    )
    text = re.sub(r"@[A-Za-z0-9_:\-.]+", " ", text)
    text = re.sub(r"\\(?:label|ref|eqref)(?:\[[^\]]*\])?\{[^}]*\}", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}s?\b", text) is not None


def _sentence_citation_function(sentence: str) -> str:
    low = _semantic_sentence_text(sentence)
    if any(marker in low for marker in ("gap", "little evidence", "few studies", "literature lacks", "understudied")):
        return "literature_gap"
    method_phrases = (
        "difference-in-differences", "event study", "standard error",
        "maximum-likelihood", "tf-idf", "smith-waterman", "fixed effect",
    )
    method_words = (
        "method", "identification", "instrument", "iv", "did", "estimator",
        "specification", "clustered", "bootstrap", "firth", "logit", "ols",
        "lpm", "hazard", "equivalence", "alignment", "duration", "decomposition",
    )
    if any(marker in low for marker in method_phrases) or any(_has_word(low, marker) for marker in method_words):
        return "method_precedent"
    if any(marker in low for marker in ("mechanism", "channel", "pathway", "explanation", "why this", "because")):
        return "mechanism_claim"
    number_words = ("table", "figure", "appendix", "billion", "million", "percent", "usd", "statistic", "share", "rate")
    if (
        any(_has_word(low, marker) for marker in number_words)
        or "%" in low
        or r"\$" in low
    ) and any(ch.isdigit() for ch in low):
        return "number_fact"
    if any(marker in low for marker in ("dataset", "data source", "survey", "database", "measurement", "variable", "sample")):
        return "data_source"
    if any(marker in low for marker in CLAIM_MARKERS) or any(marker in low for marker in ("finds", "shows", "reports", "estimates", "documents", "demonstrates")):
        return "result_claim"
    if any(marker in low for marker in ("law", "legal", "statute", "regulation", "court", "rulemaking")):
        return "legal_fact"
    if any(marker in low for marker in ("agency", "official", "usda", "fda", "government")):
        return "policy_fact"
    if any(marker in low for marker in ("literature", "prior work", "related work", "studies", "scholars")):
        return "related_literature"
    if any(marker in low for marker in ("background", "context", "overview", "see also")):
        return "background_pointer"
    return "metadata_only"


def _citation_function(sentence: str, row: dict[str, str]) -> str:
    """Classify the citation's sentence-level function.

    Registry-level citation_function is only a default hint. A paper can be used
    as background in one sentence and as a method/result/number support in
    another; the sentence use must therefore override the registry label when it
    carries a stronger function.
    """
    inferred = _sentence_citation_function(sentence)
    low = _semantic_sentence_text(sentence)
    primary = " ".join(str(row.get(col) or "").lower() for col in ("primary_function", "secondary_functions", "citation_function"))
    title = str(row.get("title") or "").lower()
    if ("data" in primary or "measurement" in primary) and any(
        marker in low for marker in ("score", "measure", "indicator", "index", "series", "variable")
    ):
        return "data_source"
    if ("method" in primary or "identification" in primary) and any(
        marker in low for marker in (
            "hypothesis", "test", "problem", "model", "specification", "logit",
            "ols", "estimator", "benchmark", "diagnostic", "reflection",
        )
    ):
        return "method_precedent"
    if "ideological mapping" in title and "score" in low:
        return "data_source"
    if inferred != "metadata_only":
        return inferred
    for col in ("citation_function", "function"):
        explicit = (row.get(col) or "").strip().lower()
        if explicit:
            return explicit
    return inferred


def _claim_type_for_function(function: str, sentence: str) -> str:
    if function in STRONG_FUNCTIONS:
        return "claim_bearing"
    if function in {"metadata_only", "background_pointer"}:
        return "bibliographic"
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


def _normalise_record_sentence(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _interpretation_records(root: Path) -> dict[str, dict[Any, tuple[Path, dict[str, Any]]]]:
    base = root / INTERPRETATION_DIR
    indexes: dict[str, dict[Any, tuple[Path, dict[str, Any]]]] = {
        "by_stem": {},
        "by_id": {},
        "by_content": {},
    }
    if not base.exists():
        return indexes
    paths = sorted(list(base.glob("*.yml")) + list(base.glob("*.yaml")) + list(base.glob("*.json")))
    for path in paths:
        data = _load_record(path)
        if data:
            entry = (path, data)
            indexes["by_stem"].setdefault(path.stem, entry)
            sid = str(data.get("sentence_id") or "").strip()
            key = str(data.get("citation_key") or "").strip()
            manuscript_path = str(data.get("manuscript_path") or "").strip()
            sentence = _normalise_record_sentence(data.get("manuscript_sentence"))
            if sid and key:
                indexes["by_id"].setdefault((sid, key), entry)
            if manuscript_path and sentence and key:
                indexes["by_content"].setdefault((manuscript_path, sentence, key), entry)
    return indexes


def _interpretation_record(
    records: dict[str, dict[Any, tuple[Path, dict[str, Any]]]],
    sentence_id: str,
    key: str,
    manuscript_path: str,
    sentence: str,
) -> tuple[Path | None, dict[str, Any]]:
    entry = records["by_id"].get((sentence_id, key))
    if entry is None:
        entry = records["by_stem"].get(sentence_id) or records["by_stem"].get(key)
    if entry is None:
        content_key = (manuscript_path, _normalise_record_sentence(sentence), key)
        entry = records["by_content"].get(content_key)
    if entry is not None:
        return entry
    return None, {}


def _verdict_from_record(record: dict[str, Any]) -> tuple[str, str]:
    if not record:
        return "missing", "missing approved interpretation record"
    human = str(record.get("human_status") or record.get("approved") or "").strip().lower()
    verdict = str(record.get("review_verdict") or record.get("verdict") or record.get("support_status") or "").strip().lower()
    relation = str(record.get("support_relation") or "").strip().lower()
    passage = str(record.get("source_passage") or record.get("quoted_passage") or "").strip()
    if not passage:
        return "missing_passage", "interpretation record lacks source_passage"
    if verdict in BAD_VALUES or relation in BAD_VALUES:
        return "overclaimed", "interpretation record marks support as unsupported/overclaimed/contradictory"
    faithful = verdict in APPROVED_FAITHFUL or relation in APPROVED_FAITHFUL
    if human in {"approved", "yes", "true"} and faithful:
        return "faithful", "approved interpretation record supports sentence"
    tier = str(record.get("citation_grounding_tier") or "").strip().lower()
    automated = record.get("automated_verification") if isinstance(record.get("automated_verification"), dict) else {}
    auto_verdict = str(automated.get("verdict") or "").strip().lower()
    confidence = str(automated.get("confidence") or "").strip().lower()
    auto_metadata = bool(str(automated.get("verifier") or "").strip() and str(automated.get("verified_at") or "").strip())
    if (
        tier == "tier_1_interpretive"
        and faithful
        and auto_verdict in APPROVED_FAITHFUL
        and confidence in {"medium", "high"}
        and auto_metadata
    ):
        return "faithful", "Tier-1 interpretation has medium/high automated passage verification"
    if verdict in WEAK_VALUES or relation in WEAK_VALUES:
        return "weak_support", "approved interpretation record is weak/partial/background-only"
    return "needs_human_review", "interpretation record lacks required Tier-1 automation or Tier-2 human approval"


def _available_evidence(
    pid: str,
    row: dict[str, str],
    card_ok: bool,
    rec: dict[str, Any],
    record_status: str,
    function: str,
) -> set[str]:
    available: set[str] = set()
    if pid:
        available.add("registry_metadata")
    if any((row.get(col) or "").strip() for col in ("abstract", "summary")):
        available.add("abstract")
    if str(row.get("full_text_available") or row.get("fulltext_available") or "").strip().lower() in {"yes", "true", "indexed_fulltext"}:
        available.add("fulltext_available")
    if any((row.get(col) or "").strip() for col in ("source_snapshot", "snapshot_path", "source_or_path", "stable_url")):
        available.add("source_snapshot")
    if _source_type(row) in {"official_source", "source_snapshot"}:
        available.add("source_snapshot")
    if _source_type(row) == "official_source":
        available.add("official_source_snapshot")
    if card_ok:
        available.add("extraction_card")
    if rec:
        available.add("interpretation_record")
    if str(rec.get("source_passage") or rec.get("quoted_passage") or "").strip():
        available.add("source_passage")
    human = str(rec.get("human_status") or rec.get("approved") or "").strip().lower()
    if record_status == "faithful" and function in TIER_1_FUNCTIONS:
        available.add("automated_interpretation")
    if record_status == "faithful" and human in {"approved", "yes", "true"}:
        available.add("approved_interpretation")
    if any((rec.get(col) or "") for col in ("page", "table", "figure", "locator", "page_or_table")):
        available.add("table_or_page_locator")
    return available


def _route_admission(row: dict[str, str], function: str, card_ok: bool) -> tuple[bool, str]:
    note = str(row.get("support_route_note") or row.get("notes") or "").strip().lower()
    stype = _source_type(row)
    if not note:
        return False, ""
    if stype in {"source_snapshot", "official_source"} and "supports only" in note:
        return True, "source-snapshot route admission; bounded to the registered manuscript sentence"
    if "bounded method/theory/data reference only" in note and function in {"method_precedent", "mechanism_claim", "data_source"}:
        return True, "bounded method/theory/data route admission; does not support empirical CMPD claims"
    if card_ok and "final citation packet" in note and function in STRONG_FUNCTIONS:
        return True, "full-text extraction route admitted by final citation packet; bounded to the manuscript use"
    return False, ""


def _missing_status(function: str, missing: list[str], row: dict[str, str]) -> str:
    if "registry_metadata" in missing:
        return "source_unavailable"
    if "extraction_card" in missing:
        fulltext = str(row.get("full_text_available") or row.get("fulltext_available") or row.get("full_text_status") or "").strip().lower()
        if fulltext in {"no", "false", "abstract_only", "missing", ""} and function in STRONG_FUNCTIONS:
            return "abstract_only_too_strong"
        return "missing_extraction"
    if "source_passage" in missing:
        return "missing_passage"
    if "approved_interpretation" in missing:
        return "missing_interpretation"
    if "automated_interpretation" in missing:
        return "missing_interpretation"
    return "needs_human_review"


def _risk_level(status: str, blocking: bool, function: str) -> str:
    if blocking:
        return "high" if function in {"result_claim", "mechanism_claim", "number_fact", "literature_gap"} else "medium"
    if status in {"needs_human_review", "weak_support", "related_literature_ok"}:
        return "medium"
    return "low"


def _evaluate_requirement(
    *,
    function: str,
    requirement: dict[str, Any],
    pid: str,
    row: dict[str, str],
    card_ok: bool,
    card_note: str,
    rec: dict[str, Any],
    record_status: str,
    record_note: str,
) -> tuple[str, str, bool, str, str, str]:
    required = [str(item) for item in requirement.get("required_evidence") or ["registry_metadata"]]
    available = _available_evidence(pid, row, card_ok, rec, record_status, function)
    missing = [item for item in required if item not in available]
    blocks_when_missing = bool(requirement.get("blocking", function in STRONG_FUNCTIONS))
    if missing:
        admitted, admission_note = _route_admission(row, function, card_ok)
        if admitted:
            return "route_admission_ok", "none", False, admission_note, ";".join(required), ";".join(sorted(available | {"route_admission"}))
        status = _missing_status(function, missing, row)
        if "extraction_card" in missing:
            status = _missing_status(function, missing, row)
        elif ("approved_interpretation" in missing or "automated_interpretation" in missing) and not rec:
            status = "missing_interpretation"
        elif "source_passage" in missing and rec:
            status = "missing_passage"
        action = f"add required evidence for {function}: {', '.join(missing)}"
        if status == "source_unavailable":
            action = "add citation key to paper_registry or remove/replace the citation"
        elif status == "abstract_only_too_strong":
            action = "recover full text and create source-bound extraction before using this citation for a strong claim"
        elif status == "missing_interpretation":
            action = "create/approve interpretation record with source_passage and faithful verdict"
        elif status == "missing_passage":
            action = "add a concrete source_passage/page/table locator to the interpretation record"
        note = f"missing evidence: {', '.join(missing)}"
        if not card_ok and "extraction_card" in missing:
            note = card_note
        if "approved_interpretation" in missing or "automated_interpretation" in missing or "source_passage" in missing:
            note = record_note
        blocking = blocks_when_missing
        return status, action, blocking, note, ";".join(required), ";".join(sorted(available))
    if record_status in {"overclaimed", "unsupported"}:
        return "overclaimed", "weaken/remove sentence or replace citation", True, record_note, ";".join(required), ";".join(sorted(available))
    if function in STRONG_FUNCTIONS and record_status == "weak_support":
        return "overclaimed", "weaken the sentence or add a faithful source-passage interpretation", True, record_note, ";".join(required), ";".join(sorted(available))
    status = str(requirement.get("allowed_status") or "grounded")
    if status == "grounded_or_snapshot_backed":
        status = "grounded"
    return status, "none", False, "function-specific citation requirement satisfied", ";".join(required), ";".join(sorted(available))


def write_citation_debt_report(root: Path | str, report: dict[str, Any], *, path: Path | None = None) -> Path:
    root = Path(root)
    out = path or (root / "audits" / "citation_debt_report.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = report.get("rows") or []
    fields = [
        "sentence_id", "manuscript_path", "line", "manuscript_sentence", "citation_key",
        "mapped_paper_id", "citation_function", "required_evidence", "available_evidence",
        "source_type", "support_status", "risk_level", "required_action", "blocking", "notes",
    ]
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if row.get("support_status") not in PASS_STATUSES or row.get("blocking"):
                writer.writerow({field: row.get(field, "") for field in fields})
    return out


def build_sentence_citation_grounding(root: Path | str = Path.cwd()) -> dict[str, Any]:
    root = Path(root)
    requirements = _load_requirements(root)
    registry, by_key = _registry_rows(root)
    records = _interpretation_records(root)
    rows: list[SentenceCitationGroundingRow] = []
    manuscripts = _manuscripts(root)
    for manuscript in manuscripts:
        rel = _rel(root, manuscript)
        for sentence, line in _sentence_spans(_read_text(manuscript)):
            keys = _citation_keys(sentence)
            if not keys:
                continue
            for key in keys:
                sid = _stable_sentence_id(rel, line, sentence, key)
                pid = by_key.get(key, "")
                reg_row = registry.get(pid, {}) if pid else {}
                function = _citation_function(sentence, reg_row)
                req = requirements.get(function, DEFAULT_REQUIREMENTS.get(function, DEFAULT_REQUIREMENTS["metadata_only"]))
                ctype = _claim_type_for_function(function, sentence)
                stype = _source_type(reg_row) if reg_row else "unknown"
                card = _card_path(root, pid, reg_row) if pid else None
                card_ok, card_note = _card_has_support(card)
                rec_path, rec = _interpretation_record(records, sid, key, rel, sentence)
                record_status, record_note = _verdict_from_record(rec)
                support, action, blocking, note, required, available = _evaluate_requirement(
                    function=function,
                    requirement=req,
                    pid=pid,
                    row=reg_row,
                    card_ok=card_ok,
                    card_note=card_note,
                    rec=rec,
                    record_status=record_status,
                    record_note=record_note,
                )
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
                    citation_function=function,
                    required_evidence=required,
                    available_evidence=available,
                    source_type=stype,
                    risk_level=_risk_level(support, blocking, function),
                    support_status=support,
                    required_action=action,
                    blocking=blocking,
                    notes=note,
                ))

    failures = [row for row in rows if row.blocking]
    debt = [row for row in rows if row.blocking or row.support_status not in PASS_STATUSES]
    counts = {
        "manuscripts": len(manuscripts),
        "citation_sentences": len({(r.manuscript_path, r.line, r.manuscript_sentence) for r in rows}),
        "citation_rows": len(rows),
        "claim_bearing_rows": sum(r.claim_type == "claim_bearing" for r in rows),
        "citation_debt_rows": len(debt),
        "blocking_rows": len(failures),
        "unknown_or_unavailable": sum(r.support_status == "source_unavailable" for r in rows),
        "weak_or_review_needed": sum(r.support_status in {"weak_support", "needs_human_review", "missing_interpretation", "missing_passage"} for r in rows),
        "by_function": {function: sum(r.citation_function == function for r in rows) for function in sorted({r.citation_function for r in rows})},
    }
    status = "inactive" if not manuscripts or not rows else ("fail" if failures else "pass")
    return {
        "model": "AEROS-CITATION-FUNCTION-001",
        "status": status,
        "counts": counts,
        "rows": [row.to_dict() for row in rows],
        "failures": [row.to_dict() for row in failures],
        "citation_debt": [row.to_dict() for row in debt],
        "debt_report_path": "audits/citation_debt_report.csv",
        "does_not_prove": DOES_NOT_PROVE,
    }
