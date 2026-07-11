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
from typing import Any

import yaml

DEFAULT_CONTRACT = Path("campaigns/active_campaign.yml")
DEFAULT_PROGRESS = Path("campaigns/campaign_progress.csv")
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
) -> dict[str, Any]:
    """Deterministically test whether undeclared work resembles an active campaign.

    Markers are owner-authored phrases in the campaign contract. A missing
    marker list is not treated as proof of unrelated work: same-lane work must
    fail closed once the campaign breaker has tripped. This guard does not add
    a task to the campaign; it only requires an explicit declaration or human
    confirmation before more potentially same-campaign work proceeds.
    """

    def normalize(value: Any) -> str:
        text = str(value or "").lower().replace("_", " ").replace("-", " ")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())

    active_lane = str(contract.get("work_lane") or "").strip()
    task_lane = str(lane or "").strip()
    raw_markers = contract.get("objective_markers") or []
    markers = [str(item).strip() for item in raw_markers if str(item).strip()] if isinstance(raw_markers, list) else []
    normalized_text = normalize(objective_text)
    matched = [marker for marker in markers if normalize(marker) and normalize(marker) in normalized_text]
    lane_match = bool(active_lane and task_lane and active_lane == task_lane)
    return {
        "active_lane": active_lane,
        "task_lane": task_lane,
        "lane_match": lane_match,
        "objective_markers": markers,
        "matched_markers": matched,
        "objective_match": bool(matched),
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
                )
            )
    return rows


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
    failures: list[str] = []
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
        "recommended_action": fallback if breakers else "continue only if the next task still targets the binding constraint and expected marginal yield",
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
