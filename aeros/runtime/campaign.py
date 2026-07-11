"""Campaign contract and marginal-yield circuit breaker.

Campaign is an advisory controller layer for repeated same-lane work. It asks
whether another task in the current campaign is still worth doing. It does not
execute tasks, mutate runtime state, approve gates, or decide scientific truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import csv
import json
import re
from functools import lru_cache
from typing import Any

import yaml

DEFAULT_CONTRACT = Path("campaigns/active_campaign.yml")
DEFAULT_PROGRESS = Path("campaigns/campaign_progress.csv")
DEFAULT_DECISIONS = Path("campaigns/campaign_decisions.yml")
PROGRESS_FIELDS = (
    "campaign_id",
    "task_id",
    "task_type",
    "metric_before",
    "metric_after",
    "marginal_yield",
    "target_constraint",
    "used_batch_source",
    "decision_metric_rerun",
    "metric_evidence_path",
    "metric_evidence_sha256",
    "metric_unique_key_columns",
    "metric_verified_novel_units",
    "research_value_events",
    "completion_mode",
    "completion_receipt_path",
    "recorded_at",
)

DOES_NOT_PROVE = [
    "that the campaign objective is scientifically optimal",
    "that the stop condition is substantively correct",
    "that continuing work would be useless in every research sense",
    "that a metric improvement supports a claim",
    "that human approval, gate approval, or paper readiness is granted",
]


@dataclass(frozen=True)
class CampaignTaskProgress:
    campaign_id: str
    task_id: str
    task_type: str
    metric_before: float | None
    metric_after: float | None
    marginal_yield: float
    target_constraint: str
    used_batch_source: bool
    decision_metric_rerun: bool
    metric_evidence_path: str = ""
    metric_evidence_sha256: str = ""
    metric_unique_key_columns: str = ""
    metric_verified_novel_units: int = 0
    research_value_events: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "metric_before": self.metric_before,
            "metric_after": self.metric_after,
            "marginal_yield": self.marginal_yield,
            "target_constraint": self.target_constraint,
            "used_batch_source": self.used_batch_source,
            "decision_metric_rerun": self.decision_metric_rerun,
            "metric_evidence_path": self.metric_evidence_path,
            "metric_evidence_sha256": self.metric_evidence_sha256,
            "metric_unique_key_columns": self.metric_unique_key_columns,
            "metric_verified_novel_units": self.metric_verified_novel_units,
            "research_value_events": list(self.research_value_events),
        }


@dataclass(frozen=True)
class CampaignBreaker:
    breaker_id: str
    severity: str
    reason: str
    recommended_action: str

    def to_dict(self) -> dict[str, str]:
        return {
            "breaker_id": self.breaker_id,
            "severity": self.severity,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
        }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "pass", "passed"}


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _expected_yield(contract: dict[str, Any]) -> float:
    for key in ["expected_yield_per_task", "minimum_yield_per_task"]:
        value = _as_float(contract.get(key))
        if value is not None:
            return value
    return 0.0


def _contract_path(root: Path, value: str | Path | None) -> Path:
    path = Path(value) if value else DEFAULT_CONTRACT
    return path if path.is_absolute() else root / path


def load_campaign_contract(root: Path, contract_path: str | Path | None = None) -> dict[str, Any] | None:
    path = _contract_path(root, contract_path)
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"campaign contract must be a mapping: {path}")
    data.setdefault("_path", str(path))
    return data


def match_campaign_scope(
    contract: dict[str, Any],
    *,
    lane: str,
    objective_text: str,
    task_type: str = "",
    output_targets: Any = (),
    inferred_outputs: Any = (),
) -> dict[str, Any]:
    """Deterministically test whether undeclared work resembles an active campaign.

    Scope is matched on three phrasing-independent dimensions so that merely
    rewording the intent cannot dodge a tripped campaign breaker:
      * objective markers (owner-authored phrases in the intent/goal),
      * output targets (the task writes into an output class the campaign owns),
      * task type (the task's inferred mode matches a campaign task type).
    A missing marker list is not treated as proof of unrelated work: same-lane
    work must fail closed once the breaker has tripped. This guard does not add
    a task to the campaign; it only requires an explicit declaration or human
    confirmation before more potentially same-campaign work proceeds.
    """

    def normalize(value: Any) -> str:
        text = str(value or "").lower().replace("_", " ").replace("-", " ")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())

    def as_list(value: Any) -> list[str]:
        return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, (list, tuple)) else []

    active_lane = str(contract.get("work_lane") or "").strip()
    task_lane = str(lane or "").strip()
    lane_match = bool(active_lane and task_lane and active_lane == task_lane)

    raw_markers = contract.get("objective_markers") or []
    markers = as_list(raw_markers)
    normalized_text = normalize(objective_text)
    matched = [marker for marker in markers if normalize(marker) and normalize(marker) in normalized_text]

    # output-path dimension: same-lane work writing into an output class the
    # campaign owns is in scope regardless of wording. Owner-declared prefixes
    # are supplemented by classes inferred from the campaign's progress history.
    declared_outputs = as_list(contract.get("objective_outputs"))
    learned_outputs = [o for o in as_list(inferred_outputs) if o not in declared_outputs]
    output_prefixes = declared_outputs + learned_outputs
    targets = as_list(output_targets)
    matched_outputs = sorted({
        tgt for tgt in targets
        for pre in output_prefixes
        if pre and (tgt == pre or tgt.startswith(pre.rstrip("/") + "/") or tgt.startswith(pre))
    })

    # task-type dimension: the task's inferred mode matches a campaign task type.
    task_types = {normalize(t) for t in as_list(contract.get("objective_task_types"))}
    task_type_match = bool(task_type and normalize(task_type) in task_types)

    objective_match = bool(matched)
    output_match = bool(matched_outputs)
    scope_match_any = objective_match or output_match or task_type_match
    return {
        "active_lane": active_lane,
        "task_lane": task_lane,
        "lane_match": lane_match,
        "objective_markers": markers,
        "matched_markers": matched,
        "objective_match": objective_match,
        "objective_outputs": output_prefixes,
        "declared_outputs": declared_outputs,
        "inferred_outputs": learned_outputs,
        "matched_outputs": matched_outputs,
        "output_match": output_match,
        "task_type": task_type,
        "task_type_match": task_type_match,
        "scope_match_any": scope_match_any,
        "marker_status": "declared" if markers else "missing_fail_closed",
    }


def load_campaign_progress(root: Path, progress_path: str | Path | None = None) -> list[CampaignTaskProgress]:
    path = _contract_path(root, progress_path or DEFAULT_PROGRESS)
    if not path.exists():
        return []
    rows: list[CampaignTaskProgress] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            before = _as_float(row.get("metric_before"))
            after = _as_float(row.get("metric_after"))
            marginal = _as_float(row.get("marginal_yield"))
            if marginal is None:
                marginal = (after - before) if before is not None and after is not None else 0.0
            rows.append(
                CampaignTaskProgress(
                    campaign_id=str(row.get("campaign_id") or "").strip(),
                    task_id=str(row.get("task_id") or row.get("id") or "").strip(),
                    task_type=str(row.get("task_type") or row.get("action_type") or "").strip(),
                    metric_before=before,
                    metric_after=after,
                    marginal_yield=float(marginal),
                    target_constraint=str(row.get("target_constraint") or row.get("binding_constraint") or "").strip(),
                    used_batch_source=_as_bool(row.get("used_batch_source")),
                    decision_metric_rerun=_as_bool(row.get("decision_metric_rerun") or row.get("decision_metric_updated")),
                    metric_evidence_path=str(row.get("metric_evidence_path") or "").strip(),
                    metric_evidence_sha256=str(row.get("metric_evidence_sha256") or "").strip(),
                    metric_unique_key_columns=str(row.get("metric_unique_key_columns") or "").strip(),
                    metric_verified_novel_units=int(_as_float(row.get("metric_verified_novel_units")) or 0),
                    research_value_events=__import__("aeros.runtime.research_value", fromlist=["decode_events"]).decode_events(str(row.get("research_value_events") or "[]")),
                )
            )
    return rows


# Generic scaffolding directories are not campaign-specific output classes;
# inferring them would over-block unrelated same-lane work.
_GENERIC_OUTPUT_PREFIXES = (
    "agent_runs/", "audits/", "outputs/", "work/", "discovery/",
    "tasks/", "decisions/", "docs/",
)


def _output_class_prefix(path: str) -> str:
    """Directory-class of an output path, or '' for a bare filename/root."""
    p = str(path or "").strip()
    if not p:
        return ""
    if p.endswith("/"):
        return p
    parts = p.rstrip("/").split("/")
    return "/".join(parts[:-1]) + "/" if len(parts) > 1 else ""


def infer_campaign_output_classes(root: Path, *, progress_path: str | Path | None = None) -> list[str]:
    """Best-effort output footprint of a campaign, inferred from the contracts of
    tasks that already recorded progress. Generic scaffolding dirs are excluded so
    only campaign-specific output classes (e.g. data/backfill/) are learned. This
    supplements owner-declared objective_outputs so a stopped campaign cannot be
    dodged by rewording the intent AND omitting the declaration. Cached per
    process on the progress file's identity so repeated preflights in one run do
    not re-glob tasks/**."""
    progress_file = _contract_path(root, progress_path or DEFAULT_PROGRESS)
    try:
        stat = progress_file.stat()
        key = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        key = (0, 0)
    return list(_infer_output_classes_cached(str(root), progress_file if key != (0, 0) else None, key))


@lru_cache(maxsize=64)
def _infer_output_classes_cached(root_str: str, progress_file: Path | None, _key: tuple[int, int]) -> tuple[str, ...]:
    root = Path(root_str)
    classes: set[str] = set()
    rows = load_campaign_progress(root, progress_file) if progress_file else []
    for row in rows:
        tid = row.task_id
        if not tid:
            continue
        candidates = [root / "tasks" / f"{tid}.yml", *sorted(root.glob(f"tasks/**/{tid}.yml"))]
        for cand in candidates:
            if not cand.is_file():
                continue
            try:
                data = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            except Exception:
                break
            for out in (data.get("allowed_outputs") or []):
                pre = _output_class_prefix(str(out))
                if pre and not any(pre.startswith(g) for g in _GENERIC_OUTPUT_PREFIXES):
                    classes.add(pre)
            break
    return tuple(sorted(classes))


def record_campaign_decision(
    root: Path,
    *,
    decision: str,
    approval_artifact: str | Path | None = None,
    reason: str = "",
    breaker_id: str = "all",
    reviewer: str = "",
    expires_after_tasks: int = 1,
    decisions_path: str | Path | None = None,
) -> dict[str, Any]:
    """Consume a committed human approval and append its campaign decision.

    ``reason``, ``reviewer``, ``breaker_id`` and ``expires_after_tasks`` remain
    accepted only for API compatibility. Authority and decision parameters come
    from the approval artifact; caller-supplied identity text grants nothing.
    """
    kind = str(decision or "").strip().lower()
    if kind not in {"continue", "stop"}:
        raise ValueError("decision must be 'continue' or 'stop'")
    active = load_campaign_contract(root)
    active_id = str((active or {}).get("campaign_id") or (active or {}).get("id") or "").strip()
    if not active_id:
        raise ValueError("no active campaign exists")
    if not approval_artifact:
        raise PermissionError("campaign decisions require --approval pointing to a committed human approval artifact")
    approval_path = Path(approval_artifact)
    if not approval_path.is_absolute():
        approval_path = root / approval_path
    try:
        approval_path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PermissionError("campaign approval artifact must be inside the project") from exc
    from .authority import evaluate_authority, load_requested_level
    authority = evaluate_authority(root, approval_path, load_requested_level(approval_path))
    if not authority.granted:
        raise PermissionError(f"campaign decision approval rejected: {authority.reason}")
    try:
        approval = yaml.safe_load(approval_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ValueError(f"cannot parse campaign approval artifact: {exc}") from exc
    if not isinstance(approval, dict):
        raise ValueError("campaign approval artifact must be a YAML mapping")
    required = ["campaign_id", "decision", "reason", "approved_at", "decision_ref"]
    missing = [field for field in required if not str(approval.get(field) or "").strip()]
    if missing:
        raise ValueError(f"campaign approval artifact missing required fields: {', '.join(missing)}")
    if str(approval.get("campaign_id") or "").strip() != active_id:
        raise ValueError("campaign approval artifact campaign_id does not match the active campaign")
    if str(approval.get("decision") or "").strip().lower() != kind:
        raise ValueError("campaign approval artifact decision does not match the requested command")
    approved_reason = str(approval.get("reason") or "").strip()
    approved_breaker = str(approval.get("breaker_id") or "all").strip() or "all"
    approved_horizon = max(1, int(approval.get("expires_after_tasks") or 1))
    author = authority.actor
    if not author:
        raise PermissionError("campaign approval artifact has no verifiable approving commit author")
    tasks_observed = len([
        row for row in load_campaign_progress(root)
        if not row.campaign_id or row.campaign_id == active_id
    ])
    record: dict[str, Any] = {
        "campaign_id": active_id or "active_campaign",
        "decision": kind,
        "reason": approved_reason,
        "reviewer": author,
        "approval_artifact": str(approval_path.resolve().relative_to(root.resolve())),
        "decision_ref": str(approval.get("decision_ref") or "").strip(),
        "approved_at": str(approval.get("approved_at") or "").strip(),
        "authority_evidence": authority.to_dict(),
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "recorded_at_progress": tasks_observed,
    }
    if kind == "continue":
        record["breaker_id"] = approved_breaker
        record["expires_after_tasks"] = approved_horizon
    path = _contract_path(root, decisions_path or DEFAULT_DECISIONS)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    decisions = list(data.get("decisions") or []) if isinstance(data, dict) else []
    decisions.append(record)
    path.write_text(yaml.safe_dump({"decisions": decisions}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return record


def _evidence_rowcount(path: Path) -> int | None:
    """Independent data-row count of an evidence file: CSV data rows (minus
    header) or non-empty lines. Returns None if unreadable."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0
    if path.suffix.lower() in {".csv", ".tsv"}:
        return max(0, len(lines) - 1)  # drop header
    return len(lines)


# High-confidence, framework-standard artifacts whose *presence* is itself a
# decision-relevant research value event. Kept deliberately strict: only things
# that cannot be produced by mere collection volume (a registered result, a
# grounded claim-bearing citation, a closed data gap), so inference recognises
# real value without letting raw counts masquerade as value.
_VALUE_ARTIFACT_SOURCES: tuple[tuple[str, str], ...] = (
    ("probe_passed", "evidence/result_registry.csv"),
    ("paper_exhibit_reproduced", "evidence/result_index.csv"),
    ("claim_bearing_citation_grounded", "discovery/literature/interpretation_records"),
    ("resolved_data_gap", "data/backfill/resolved"),
    ("replication_blocker_resolved", "evidence/negative_result_ledger.md"),
)


def infer_research_value_events(root: Path, *, since_mtime: float | None = None) -> list[dict[str, Any]]:
    """Recognise decision-relevant value the project already recorded elsewhere,
    so `low_decision_value` reflects real value (declared ∪ inferred), not just
    annotation diligence. Strict by design: only high-confidence artifacts count,
    and only those produced since the campaign started (anchored to the campaign
    contract's mtime) so pre-campaign results cannot permanently suppress the
    breaker. Fail-safe: unreadable mtimes yield no inference → the breaker fires
    (conservative)."""
    anchor = since_mtime
    if anchor is None:
        contract_file = root / DEFAULT_CONTRACT
        try:
            anchor = contract_file.stat().st_mtime if contract_file.exists() else None
        except OSError:
            anchor = None
    inferred: list[dict[str, Any]] = []
    for event_type, rel in _VALUE_ARTIFACT_SOURCES:
        base = root / rel
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for f in candidates:
            try:
                if anchor is not None and f.stat().st_mtime < anchor:
                    continue
            except OSError:
                continue
            if f.suffix.lower() in {".csv", ".tsv"} and (_evidence_rowcount(f) or 0) < 1:
                continue  # header-only registries carry no value yet
            inferred.append({"event_type": event_type, "source": str(f.relative_to(root))})
            break  # one confirmation per source is enough
    return inferred


def _metric_key_columns(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    if not isinstance(value, list):
        return []
    return [str(part).strip() for part in value if str(part).strip()]


def _evidence_unique_units(path: Path, key_columns: list[str] | None = None) -> tuple[set[tuple[str, ...]], str]:
    """Return independently observed unique evidence units.

    CSV/TSV evidence defaults to its first column when no key is declared.
    Text evidence uses unique non-empty lines. This is deliberately mechanical:
    it verifies novelty, not scientific relevance or source quality.
    """
    columns = list(key_columns or [])
    if path.suffix.lower() in {".csv", ".tsv"}:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            fields = list(reader.fieldnames or [])
            if not fields:
                return set(), ""
            use = columns or [fields[0]]
            missing = [name for name in use if name not in fields]
            if missing:
                raise ValueError(f"metric unique-key column(s) missing from evidence: {', '.join(missing)}")
            units = {
                tuple(str(row.get(name) or "").strip() for name in use)
                for row in reader
            }
            units.discard(tuple("" for _ in use))
            return units, ",".join(use)
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {(line.strip(),) for line in text.splitlines() if line.strip()}, "__line__"


def load_campaign_decisions(root: Path, campaign_id: str = "", decisions_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Human continue/stop decisions recorded against a campaign. This is the
    consumption side of the breaker's escalation: a recorded decision lets the
    human release a tripped breaker for a bounded number of tasks (continue) or
    halt the campaign (stop), instead of hand-editing the contract."""
    path = _contract_path(root, decisions_path or DEFAULT_DECISIONS)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    raw = data.get("decisions") if isinstance(data, dict) else data
    out: list[dict[str, Any]] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("campaign_id") or "").strip()
        if cid and campaign_id and cid not in {campaign_id, "*"}:
            continue
        out.append(item)
    return out


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _allowed_metric_evidence(path: str, allowed_outputs: list[str]) -> bool:
    value = str(path or "").strip().strip("/")
    for allowed in allowed_outputs:
        prefix = str(allowed or "").strip().strip("/")
        if prefix and (value == prefix or value.startswith(prefix + "/")):
            return True
    return False


def record_campaign_progress(
    root: Path,
    contract: Any,
    *,
    completion_mode: str,
    completion_receipt_path: str,
    append: bool = True,
) -> dict[str, Any]:
    """Validate and idempotently record one passed task's campaign progress.

    Metrics are declared by the task but must be anchored to an existing allowed
    output. AEROS computes marginal yield itself and never appends a row for a
    task outside the active campaign. Revalidation of an identical task is a
    no-op; conflicting values fail closed instead of rewriting history.
    """
    campaign_id = str(getattr(contract, "campaign_id", "") or "").strip()
    if not campaign_id:
        return {"status": "not_campaign_task", "campaign_id": "", "row": {}, "failures": []}

    active = load_campaign_contract(root)
    if active is None:
        return {
            "status": "missing_active_campaign",
            "campaign_id": campaign_id,
            "row": {},
            "failures": [f"campaign task {contract.task_id} declares {campaign_id} but no active campaign contract exists"],
        }
    active_id = str(active.get("campaign_id") or active.get("id") or "").strip()
    if active_id != campaign_id:
        return {
            "status": "campaign_mismatch",
            "campaign_id": campaign_id,
            "active_campaign_id": active_id,
            "row": {},
            "failures": [f"task campaign_id {campaign_id} does not match active campaign {active_id or '<missing>'}"],
        }

    declared = dict(getattr(contract, "campaign_progress", {}) or {})
    before = _as_float(declared.get("metric_before"))
    after = _as_float(declared.get("metric_after"))
    target = str(declared.get("target_constraint") or "").strip()
    evidence_rel = str(declared.get("metric_evidence_path") or "").strip()
    unique_key_columns = _metric_key_columns(declared.get("metric_unique_key_columns"))
    failures: list[str] = []
    from .research_value import encode_events, validate_events
    value_events, value_failures = validate_events(
        root,
        declared.get("research_value_events") or [],
        list(getattr(contract, "allowed_outputs", []) or []),
    )
    failures.extend(value_failures)
    if before is None or after is None:
        failures.append("campaign_progress requires numeric metric_before and metric_after")
    if not target:
        failures.append("campaign_progress requires target_constraint")
    if not evidence_rel:
        failures.append("campaign_progress requires metric_evidence_path")
    elif not _allowed_metric_evidence(evidence_rel, list(getattr(contract, "allowed_outputs", []) or [])):
        failures.append("campaign metric_evidence_path must be inside the task's allowed_outputs")
    evidence_path = root / evidence_rel if evidence_rel else root / "__missing_campaign_evidence__"
    if evidence_rel and not evidence_path.is_file():
        failures.append(f"campaign metric evidence file is missing: {evidence_rel}")
    elif evidence_rel:
        # Anti-inflation: a claimed integer gain must be backed by at least that
        # many data rows/lines in the evidence file, so a task cannot report a
        # large metric_after while pointing at a tiny real file. Fractional/rate
        # metrics (gain < 1) only require the evidence to be non-empty.
        gain = (after - before) if (before is not None and after is not None) else 0.0
        rowcount = _evidence_rowcount(evidence_path)
        # Only a *claimed positive gain* must be backed by that many evidence rows.
        # A zero-gain task ("found nothing new") is a legitimate diminishing-returns
        # signal and may point at empty/header-only evidence — rejecting it would
        # suppress the very plateau that low_marginal_yield and convergence_freeze
        # need to see.
        if rowcount is not None and gain >= 1 and rowcount < int(gain):
            failures.append(
                f"declared metric gain {gain:g} exceeds evidence rows {rowcount} in {evidence_rel}; "
                "metric_after is not backed by enough evidence"
            )
        try:
            current_units, observed_key = _evidence_unique_units(evidence_path, unique_key_columns)
        except (OSError, ValueError) as exc:
            failures.append(str(exc))
            current_units, observed_key = set(), ""
        prior_rows = [
            row for row in load_campaign_progress(root)
            if row.campaign_id == campaign_id and row.task_id != str(contract.task_id)
        ]
        if prior_rows and before is not None:
            expected_before = prior_rows[-1].metric_after
            if before != expected_before:
                failures.append(
                    f"metric_before {before:g} does not continue the recorded campaign value {expected_before:g}"
                )
        historical_units: set[tuple[str, ...]] = set()
        for previous in prior_rows:
            previous_path = root / previous.metric_evidence_path
            if not previous.metric_evidence_path or not previous_path.is_file():
                continue
            try:
                units, _ = _evidence_unique_units(previous_path, unique_key_columns)
                historical_units.update(units)
            except (OSError, ValueError):
                continue
        novel_units = current_units - historical_units
        if gain >= 1 and len(novel_units) < int(gain):
            failures.append(
                f"declared metric gain {gain:g} exceeds independently observed novel units {len(novel_units)} "
                f"using key {observed_key or '<unavailable>'}; duplicate or previously counted evidence cannot inflate progress"
            )
    if failures:
        return {
            "status": "invalid_progress_declaration",
            "campaign_id": campaign_id,
            "row": {},
            "failures": failures,
        }

    assert before is not None and after is not None
    row = {
        "campaign_id": campaign_id,
        "task_id": str(contract.task_id),
        "task_type": str(declared.get("task_type") or getattr(contract, "work_lane", "") or "task").strip(),
        "metric_before": f"{before:g}",
        "metric_after": f"{after:g}",
        "marginal_yield": f"{after - before:g}",
        "target_constraint": target,
        "used_batch_source": "true" if _as_bool(declared.get("used_batch_source")) else "false",
        "decision_metric_rerun": "true" if _as_bool(declared.get("decision_metric_rerun")) else "false",
        "metric_evidence_path": evidence_rel,
        "metric_evidence_sha256": _sha256_file(evidence_path),
        "metric_unique_key_columns": observed_key,
        "metric_verified_novel_units": str(len(novel_units)),
        "research_value_events": encode_events(value_events),
        "completion_mode": str(completion_mode or ""),
        "completion_receipt_path": str(completion_receipt_path or ""),
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if not append:
        return {"status": "validated_not_recorded", "campaign_id": campaign_id, "row": row, "failures": []}

    path = root / DEFAULT_PROGRESS
    existing_rows: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            existing_rows = [{str(k): str(v or "") for k, v in item.items()} for item in csv.DictReader(handle)]
    matches = [item for item in existing_rows if item.get("campaign_id", "") == campaign_id and item.get("task_id", "") == str(contract.task_id)]
    compare_fields = [field for field in PROGRESS_FIELDS if field not in {"recorded_at", "completion_mode", "completion_receipt_path"}]
    if matches:
        previous = matches[-1]
        if all(str(previous.get(field, "")) == str(row.get(field, "")) for field in compare_fields):
            return {"status": "unchanged", "campaign_id": campaign_id, "row": previous, "failures": []}
        return {
            "status": "conflicting_existing_progress",
            "campaign_id": campaign_id,
            "row": row,
            "failures": [f"campaign progress already exists with different values for {campaign_id}/{contract.task_id}"],
        }

    existing_rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PROGRESS_FIELDS), extrasaction="ignore")
        writer.writeheader()
        for item in existing_rows:
            writer.writerow({field: item.get(field, "") for field in PROGRESS_FIELDS})
    temp.replace(path)
    return {"status": "appended", "campaign_id": campaign_id, "row": row, "failures": []}


def _is_single_item_task(row: CampaignTaskProgress) -> bool:
    text = row.task_type.lower().replace("-", "_").replace(" ", "_")
    return any(marker in text for marker in ["single", "manual_lookup", "one_by_one", "portal_lookup", "item_lookup"])


def assess_campaign(
    root: Path,
    *,
    contract_path: str | Path | None = None,
    progress_path: str | Path | None = None,
    campaign_id: str = "",
) -> dict[str, Any]:
    contract = load_campaign_contract(root, contract_path)
    if contract is None:
        return {
            "model": "AEROS-CAMPAIGN-001",
            "status": "NO_ACTIVE_CAMPAIGN",
            "summary": "No active campaign contract found; circuit breaker is inactive.",
            "breakers": [],
            "recommended_action": "Create a campaign contract before starting a repeated same-lane autonomous loop.",
            "does_not_prove": DOES_NOT_PROVE,
        }

    active_id = str(contract.get("campaign_id") or contract.get("id") or "").strip()
    declared_id = str(campaign_id or "").strip()
    if declared_id and declared_id != active_id:
        return {
            "model": "AEROS-CAMPAIGN-001",
            "status": "CAMPAIGN_MISMATCH",
            "campaign_id": declared_id,
            "active_campaign_id": active_id,
            "breakers": [],
            "recommended_action": "do not apply the active campaign breaker to this task",
            "does_not_prove": DOES_NOT_PROVE,
        }

    rows = [
        row for row in load_campaign_progress(root, progress_path)
        if not row.campaign_id or row.campaign_id == active_id
    ]
    expected = _expected_yield(contract)
    window = int(contract.get("marginal_yield_window") or 3)
    task_budget = int(contract.get("task_budget") or 0)
    binding = str(contract.get("binding_constraint") or "").strip()
    stop_met = _as_bool(contract.get("stop_condition_met")) or any(row.decision_metric_rerun and row.marginal_yield >= expected for row in rows)
    fallback = str(contract.get("fallback_if_stalled") or "escalate to human decision packet").strip()

    breakers: list[CampaignBreaker] = []
    value_window = max(1, int(contract.get("research_value_window") or contract.get("marginal_yield_window") or 3))
    declared_value = any(row.research_value_events for row in rows[-value_window:])
    inferred_value: list[dict[str, Any]] = []
    if len(rows) >= value_window and not declared_value:
        inferred_value = infer_research_value_events(root)
        if not inferred_value:
            # Fire, but present BOTH interpretations honestly: genuinely no
            # decision value, OR value produced but not recorded.
            breakers.append(CampaignBreaker(
                "low_decision_value",
                "BLOCK",
                f"the last {value_window} campaign task(s) recorded no research_value_event, "
                "and none was inferred from project value artifacts",
                "either the recent work produced no decision-relevant value (stop and reconsider "
                "route/metric/objective), or value was produced but not recorded — record it as a "
                "campaign research_value_event to clear this",
            ))
    recent = rows[-window:] if window > 0 else rows
    if expected > 0 and len(recent) >= window and all(row.marginal_yield < expected for row in recent):
        breakers.append(CampaignBreaker(
            "low_marginal_yield",
            "block_same_campaign_loop",
            f"last {window} task(s) all yielded below expected_yield_per_task={expected:g}",
            fallback,
        ))

    if task_budget > 0 and len(rows) >= task_budget and not stop_met:
        breakers.append(CampaignBreaker(
            "task_budget_exhausted",
            "block_same_campaign_loop",
            f"{len(rows)} task(s) reached task_budget={task_budget} without stop_condition_met",
            fallback,
        ))

    if binding:
        drifted = [row.task_id or f"row_{idx+1}" for idx, row in enumerate(rows) if row.target_constraint and row.target_constraint != binding]
        if drifted:
            breakers.append(CampaignBreaker(
                "binding_constraint_drift",
                "escalate_before_more_work",
                f"task(s) targeted a different constraint than {binding}: {', '.join(drifted[:5])}",
                "pause and ask whether the campaign objective or binding constraint changed",
            ))

    if _as_bool(contract.get("batch_source_available")) and len(recent) >= window:
        if all(_is_single_item_task(row) and not row.used_batch_source for row in recent):
            breakers.append(CampaignBreaker(
                "batch_source_unused",
                "switch_strategy",
                f"last {window} task(s) were single-item lookups while a structured batch source is declared available",
                "try the batch/structured source first or document why it is unusable",
            ))

    gain_threshold = _as_float(contract.get("rerun_decision_metric_after_gain"))
    if gain_threshold is not None and rows:
        start = rows[0].metric_before
        latest_after = next((row.metric_after for row in reversed(rows) if row.metric_after is not None), None)
        if start is not None and latest_after is not None and latest_after - start >= gain_threshold:
            if not any(row.decision_metric_rerun for row in rows):
                breakers.append(CampaignBreaker(
                    "collecting_without_testing",
                    "run_decision_metric",
                    f"objective metric increased by {latest_after - start:g}, meeting rerun_decision_metric_after_gain={gain_threshold:g}, but no decision metric rerun is recorded",
                    "rerun the binding decision metric before more collection",
                ))

    # Convergence / FREEZE: the positive counterpart of the stall breakers. When
    # the objective metric has plateaued across the recent window, stop expanding
    # side-branches and ask the human to finalize (freeze), rather than grinding.
    conv_window = int(contract.get("convergence_window") or window)
    conv_eps = _as_float(contract.get("convergence_epsilon"))
    conv_eps = conv_eps if conv_eps is not None else 0.0
    conv_recent = rows[-conv_window:] if conv_window > 0 else rows
    conv_levels = [row.metric_after for row in conv_recent if row.metric_after is not None]
    if (not stop_met and conv_window > 0 and len(conv_levels) >= conv_window
            and len(rows) >= 2 * conv_window
            and max(conv_levels) - min(conv_levels) <= conv_eps):
        breakers.append(CampaignBreaker(
            "convergence_freeze",
            "recommend_finalize",
            f"objective metric stable within {conv_eps:g} across last {conv_window} task(s) "
            f"(levels {min(conv_levels):g}..{max(conv_levels):g}); results appear converged",
            "stop expanding this campaign and request a human finalize/freeze decision",
        ))

    # Human release valve: consume recorded continue/stop decisions. A `stop`
    # decision halts the campaign; a `continue` decision releases the named
    # breaker (or all) for a bounded number of tasks, then it re-applies so the
    # human must re-review. This makes the human's answer a first-class record
    # instead of forcing a hand-edit of the contract with mismatched semantics.
    decisions = load_campaign_decisions(root, active_id)
    released: list[dict[str, Any]] = []
    applied_decisions: list[dict[str, Any]] = []
    halt_decision: dict[str, Any] | None = None
    continue_decisions: list[dict[str, Any]] = []
    for dec in decisions:
        kind = str(dec.get("decision") or "").strip().lower()
        if kind == "stop":
            halt_decision = dec
            applied_decisions.append(dec)
        elif kind == "continue":
            at = int(_as_float(dec.get("recorded_at_progress")) or 0)
            horizon = int(_as_float(dec.get("expires_after_tasks")) or 0)
            active_window = horizon <= 0 or len(rows) < at + horizon
            if active_window:
                continue_decisions.append(dec)
                applied_decisions.append(dec)

    if halt_decision is not None:
        breakers = [CampaignBreaker(
            "human_stop",
            "block_same_campaign_loop",
            f"human recorded a stop decision for this campaign: {str(halt_decision.get('reason') or '').strip()}",
            "the campaign is stopped by human decision; start a new campaign or remove the stop decision to resume",
        )]
    elif continue_decisions:
        kept: list[CampaignBreaker] = []
        for breaker in breakers:
            match = next(
                (dec for dec in continue_decisions
                 if str(dec.get("breaker_id") or "all").strip().lower() in {"all", breaker.breaker_id}),
                None,
            )
            if match is not None:
                released.append({"breaker_id": breaker.breaker_id, "released_by": match})
            else:
                kept.append(breaker)
        breakers = kept

    status = "ESCALATE" if breakers else "CONTINUE"
    return {
        "model": "AEROS-CAMPAIGN-001",
        "status": status,
        "campaign_id": active_id or "active_campaign",
        "work_lane": str(contract.get("work_lane") or "").strip(),
        "objective_markers": [
            str(item).strip()
            for item in (contract.get("objective_markers") or [])
            if str(item).strip()
        ] if isinstance(contract.get("objective_markers") or [], list) else [],
        "objective_metric": contract.get("objective_metric") or "",
        "binding_constraint": binding,
        "stop_condition": contract.get("stop_condition") or "",
        "task_budget": task_budget,
        "tasks_observed": len(rows),
        "expected_yield_per_task": expected,
        "recent_marginal_yields": [row.marginal_yield for row in recent],
        "breakers": [breaker.to_dict() for breaker in breakers],
        "released_breakers": released,
        "human_decisions_applied": applied_decisions,
        "inferred_research_value": inferred_value,
        "unrecorded_value_hint": (
            "decision value was inferred from project artifacts but not recorded as campaign "
            "research_value_events; record it for a durable trail" if inferred_value else ""
        ),
        "campaign_halted": halt_decision is not None,
        "recommended_action": (
            "the campaign is stopped by a human stop decision" if halt_decision is not None
            else fallback if breakers
            else "continue only if the next task still targets the binding constraint and expected marginal yield"
        ),
        "progress_rows": [row.to_dict() for row in rows],
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_campaign_assessment(report: dict[str, Any]) -> str:
    lines = ["# AEROS Campaign Circuit Breaker", ""]
    lines.append(f"status: {report.get('status')}")
    if report.get("campaign_id"):
        lines.append(f"campaign: {report.get('campaign_id')}")
        lines.append(f"objective_metric: {report.get('objective_metric')}")
        lines.append(f"binding_constraint: {report.get('binding_constraint')}")
        lines.append(f"tasks_observed: {report.get('tasks_observed')}")
        lines.append(f"recent_marginal_yields: {report.get('recent_marginal_yields')}")
    lines.append("")
    breakers = report.get("breakers") or []
    if breakers:
        lines.append("Breakers:")
        for breaker in breakers:
            lines.append(f"- {breaker.get('breaker_id')}: {breaker.get('reason')}")
            lines.append(f"  action: {breaker.get('recommended_action')}")
    else:
        lines.append(str(report.get("summary") or "No campaign breaker fired."))
    lines.append("")
    lines.append(f"Recommended action: {report.get('recommended_action')}")
    lines.append("")
    lines.append("Boundary: advisory only. Does not mutate state, approve gates, or decide scientific validity.")
    return "\n".join(lines)


def write_campaign_assessment(root: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    out_dir = root / "outputs" / "campaign"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "campaign_assessment.md"
    js = out_dir / "campaign_assessment.json"
    md.write_text(format_campaign_assessment(report) + "\n", encoding="utf-8")
    js.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return md, js
