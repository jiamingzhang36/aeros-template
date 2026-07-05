"""Broad-capture firewall for early source/data lead collection.

Broad capture is deliberately low-governance because it is not evidence,
canonical data, or claim support. The firewall keeps that bargain honest: lead
collection may write only isolated lead/candidate queues and batch audit notes.
Anything paper-facing, claim-facing, processed, canonical, or release-facing
must go through a later promotion path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from datetime import date, datetime, timezone


ALLOWED_PREFIXES = (
    "work/leads/",
    "audits/broad_capture/",
    "quality_reports/broad_capture/",
    "outputs/logs/",
)

ALLOWED_EXACT = {
    "evidence/delta_log.jsonl",
}

PROTECTED_PREFIXES = (
    "data/raw/",
    "data/intermediate/",
    "data/processed/",
    "paper/",
    "tex/",
    "replication/",
    "compliance/",
    "decisions/approvals/",
)

PROTECTED_EXACT = {
    "evidence/claim_registry.md",
    "decisions/decision_log.csv",
}

DOES_NOT_PROVE = [
    "that a source is relevant",
    "that a lead is admissible evidence",
    "that a candidate should be promoted",
    "that data collection is complete",
    "that a claim, paper, or release artifact is supported",
]

LEAD_QUEUE_REQUIRED_FIELDS = (
    "lead_id",
    "source_url",
    "captured_at",
    "capture_method",
    "why_potentially_relevant",
    "route",
    "dedupe_key",
    "promotion_status",
    "ttl_days",
    "promotion_requirements",
)

PROMOTION_STATUSES = {
    "unreviewed",
    "rejected",
    "candidate",
    "stale",
    "promoted",
}

DEFAULT_TTL_DAYS = 30


@dataclass(frozen=True)
class BroadCaptureFirewallResult:
    ok: bool
    failures: tuple[str, ...]
    allowed_writes: tuple[str, ...]
    protected_writes: tuple[str, ...]
    does_not_prove: tuple[str, ...] = tuple(DOES_NOT_PROVE)


@dataclass(frozen=True)
class LeadQueueValidation:
    ok: bool
    failures: tuple[str, ...]
    row_count: int
    stale_count: int


def normalize_path(path: str | Path) -> str:
    rel = str(path).strip().replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def is_lead_queue(path: str) -> bool:
    return path.startswith("data/backfill/") and path.endswith("_lead_queue.csv")


def is_candidate_queue(path: str) -> bool:
    return path.startswith("data/backfill/") and path.endswith("_candidate_queue.csv")


def is_allowed_broad_capture_write(path: str | Path) -> bool:
    rel = normalize_path(path)
    return (
        rel in ALLOWED_EXACT
        or rel.startswith(ALLOWED_PREFIXES)
        or is_lead_queue(rel)
        or is_candidate_queue(rel)
    )


def is_protected_broad_capture_write(path: str | Path) -> bool:
    rel = normalize_path(path)
    return rel in PROTECTED_EXACT or rel.startswith(PROTECTED_PREFIXES)


def validate_broad_capture_writes(paths: list[str] | tuple[str, ...]) -> BroadCaptureFirewallResult:
    failures: list[str] = []
    allowed: list[str] = []
    protected: list[str] = []
    for raw in paths:
        rel = normalize_path(raw)
        if is_protected_broad_capture_write(rel):
            protected.append(rel)
            failures.append(f"broad_capture cannot write protected path: {rel}")
            continue
        if is_allowed_broad_capture_write(rel):
            allowed.append(rel)
            continue
        failures.append(f"broad_capture write is outside isolated lead/candidate surfaces: {rel}")
    return BroadCaptureFirewallResult(
        ok=not failures,
        failures=tuple(failures),
        allowed_writes=tuple(allowed),
        protected_writes=tuple(protected),
    )


def _parse_date(raw: str) -> date | None:
    value = str(raw or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _is_stale(row: dict[str, str], *, today: date) -> bool:
    status = str(row.get("promotion_status", "")).strip().lower()
    if status == "stale":
        return True
    if status not in {"", "unreviewed"}:
        return False
    captured = _parse_date(row.get("captured_at", ""))
    if captured is None:
        return False
    try:
        ttl = int(str(row.get("ttl_days") or DEFAULT_TTL_DAYS).strip())
    except ValueError:
        ttl = DEFAULT_TTL_DAYS
    return (today - captured).days > ttl


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def validate_lead_queue(path: Path, *, today: date | None = None) -> LeadQueueValidation:
    today = today or datetime.now(timezone.utc).date()
    failures: list[str] = []
    if not path.exists():
        return LeadQueueValidation(False, (f"missing lead queue: {path}",), 0, 0)
    rows = read_csv_rows(path)
    header = set(rows[0].keys()) if rows else set()
    if rows:
        missing = set(LEAD_QUEUE_REQUIRED_FIELDS) - header
        if missing:
            failures.append(f"{path}: missing required lead queue fields: {', '.join(sorted(missing))}")
    else:
        failures.append(f"{path}: lead queue is empty")
    seen_ids: set[str] = set()
    stale_count = 0
    for index, row in enumerate(rows, start=2):
        lead_id = str(row.get("lead_id", "")).strip()
        if not lead_id:
            failures.append(f"{path}:{index}: missing lead_id")
        elif lead_id in seen_ids:
            failures.append(f"{path}:{index}: duplicate lead_id {lead_id}")
        seen_ids.add(lead_id)
        status = str(row.get("promotion_status", "")).strip().lower()
        if status not in PROMOTION_STATUSES:
            failures.append(f"{path}:{index}: invalid promotion_status {status!r}")
        try:
            ttl = int(str(row.get("ttl_days") or DEFAULT_TTL_DAYS).strip())
            if ttl <= 0:
                failures.append(f"{path}:{index}: ttl_days must be positive")
        except ValueError:
            failures.append(f"{path}:{index}: ttl_days must be an integer")
        if _is_stale(row, today=today):
            stale_count += 1
    return LeadQueueValidation(not failures, tuple(failures), len(rows), stale_count)


def summarize_broad_capture(root: Path, *, today: date | None = None) -> dict[str, object]:
    today = today or datetime.now(timezone.utc).date()
    backfill = root / "data" / "backfill"
    lead_paths = sorted(backfill.glob("*_lead_queue.csv")) if backfill.exists() else []
    candidate_paths = sorted(backfill.glob("*_candidate_queue.csv")) if backfill.exists() else []
    total_leads = 0
    total_candidates = 0
    stale_leads = 0
    promoted = 0
    candidate_status = 0
    blocker_distribution: dict[str, int] = {}
    validation_failures: list[str] = []
    duplicate_lead_count = 0
    seen_dedupe_keys: set[str] = set()
    for path in lead_paths:
        validation = validate_lead_queue(path, today=today)
        validation_failures.extend(validation.failures)
        rows = read_csv_rows(path) if path.exists() else []
        total_leads += len(rows)
        stale_leads += validation.stale_count
        for row in rows:
            status = str(row.get("promotion_status", "")).strip().lower()
            if status == "promoted":
                promoted += 1
            if status == "candidate":
                candidate_status += 1
            dedupe_key = str(row.get("dedupe_key", "")).strip()
            if dedupe_key:
                if dedupe_key in seen_dedupe_keys:
                    duplicate_lead_count += 1
                seen_dedupe_keys.add(dedupe_key)
            blocker = str(row.get("promotion_blocker", "")).strip() or "none"
            blocker_distribution[blocker] = blocker_distribution.get(blocker, 0) + 1
    for path in candidate_paths:
        total_candidates += len(read_csv_rows(path))
    denominator = total_leads or 1
    lead_to_candidate_rate = round((candidate_status + total_candidates) / denominator, 4)
    duplicate_lead_rate = round(duplicate_lead_count / denominator, 4)
    capture_saturation_stop = bool(total_leads >= 20 and (lead_to_candidate_rate < 0.05 or stale_leads / denominator > 0.5 or duplicate_lead_rate > 0.5))
    if capture_saturation_stop:
        recommended_next_action = "triage/dedupe/promote existing leads before more broad_capture"
    elif total_leads == 0:
        recommended_next_action = "run a bounded broad_capture lead sweep"
    else:
        recommended_next_action = "continue broad_capture only if current candidate queue has been triaged"
    return {
        "status": "PASS" if not validation_failures else "FAIL",
        "lead_queue_count": len(lead_paths),
        "candidate_queue_count": len(candidate_paths),
        "total_leads": total_leads,
        "total_candidates": total_candidates,
        "lead_to_candidate_rate": lead_to_candidate_rate,
        "candidate_to_staging_rate": round(promoted / denominator, 4),
        "stale_lead_count": stale_leads,
        "duplicate_lead_count": duplicate_lead_count,
        "duplicate_lead_rate": duplicate_lead_rate,
        "capture_saturation_stop": capture_saturation_stop,
        "recommended_next_action": recommended_next_action,
        "promotion_blocker_distribution": blocker_distribution,
        "validation_failures": validation_failures,
        "does_not_prove": DOES_NOT_PROVE,
    }
