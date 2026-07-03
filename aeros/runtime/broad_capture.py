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


@dataclass(frozen=True)
class BroadCaptureFirewallResult:
    ok: bool
    failures: tuple[str, ...]
    allowed_writes: tuple[str, ...]
    protected_writes: tuple[str, ...]
    does_not_prove: tuple[str, ...] = tuple(DOES_NOT_PROVE)


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
