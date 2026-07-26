"""Compile risk-based independent review from an accepted worker candidate.

This module does not execute work or certify scientific correctness. It turns
already-observed completion evidence into a bounded, content-addressed review
packet. Low-risk work remains mechanical; high-risk work requires an
independent critic; critical authority surfaces also require a human gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable


RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
CRITICAL_PREFIXES = (
    "decisions/approvals/",
    "docs/protected_definitions.yml",
    "evidence/claim_registry.md",
    "data/canonical/",
    "release/",
)
HIGH_PREFIXES = (
    "data/processed/",
    "evidence/result",
    "outputs/analysis/",
    "outputs/econ/",
    "outputs/figures/",
    "paper/",
    "tex/",
    "docs/manuscript/",
    "replication/",
)
MEDIUM_PREFIXES = (
    "data/intermediate/",
    "data/backfill/",
    "discovery/",
    "evidence/",
    "literature/",
)
HIGH_LANES = {"method", "claim", "writing", "compliance"}
HIGH_STAGES = {
    "analysis",
    "claim",
    "claim_audit",
    "method",
    "paper",
    "replication",
    "release",
    "submission",
    "writing",
}


@dataclass(frozen=True)
class CompletionReviewPlan:
    risk: str
    required: bool
    human_gate_required: bool
    reasons: tuple[str, ...]

    def should_run(self, *, advisory_enabled: bool) -> bool:
        return self.required or (self.risk == "medium" and advisory_enabled)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk": self.risk,
            "required": self.required,
            "human_gate_required": self.human_gate_required,
            "reasons": list(self.reasons),
        }


def _matches(path: str, prefixes: Iterable[str]) -> bool:
    clean = path.strip().lstrip("./")
    return any(clean == prefix.rstrip("/") or clean.startswith(prefix) for prefix in prefixes)


def classify_completion_review(contract: Any, accepted_outputs: Iterable[str]) -> CompletionReviewPlan:
    """Deterministically classify completion risk from contract and output paths."""
    paths = tuple(sorted({str(path).strip() for path in accepted_outputs if str(path).strip()}))
    raw = getattr(contract, "raw", {}) or {}
    lane = str(getattr(contract, "work_lane", "") or "").strip().lower()
    stage = str(getattr(contract, "stage", "") or "").strip().lower()
    risk = "low"
    reasons: list[str] = []

    if any(_matches(path, CRITICAL_PREFIXES) for path in paths):
        risk = "critical"
        reasons.append("accepted output touches an authority/canonical surface")
    elif any(_matches(path, HIGH_PREFIXES) for path in paths):
        risk = "high"
        reasons.append("accepted output can affect results, claims, manuscript, or release")
    elif any(_matches(path, MEDIUM_PREFIXES) for path in paths):
        risk = "medium"
        reasons.append("accepted output is research-facing but not yet canonical")

    if bool(raw.get("critic_required")) and RISK_RANK[risk] < RISK_RANK["high"]:
        risk = "high"
        reasons.append("task contract explicitly requires an independent critic")
    if lane in HIGH_LANES and RISK_RANK[risk] < RISK_RANK["high"]:
        risk = "high"
        reasons.append(f"work lane {lane} is high-risk")
    if stage in HIGH_STAGES and RISK_RANK[risk] < RISK_RANK["high"]:
        risk = "high"
        reasons.append(f"stage {stage} is high-risk")

    explicit_human = bool(raw.get("human_gate_required"))
    if explicit_human and risk != "critical":
        risk = "critical"
        reasons.append("task contract explicitly requires a human gate")
    if not reasons:
        reasons.append("no research-facing or authority-bearing output was detected")

    return CompletionReviewPlan(
        risk=risk,
        required=risk in {"high", "critical"},
        human_gate_required=risk == "critical" or explicit_human,
        reasons=tuple(reasons),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_text(path: Path, limit: int = 2400) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return text[:limit]


def _bounded_diff(root: Path, paths: tuple[str, ...], limit: int = 8000) -> str:
    if not paths:
        return ""
    proc = subprocess.run(
        ["git", "-C", str(root), "diff", "--", *paths],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return (proc.stdout or "")[:limit]


def build_review_packet(
    project_root: Path,
    contract: Any,
    candidate_run: Any,
    check_results: Iterable[Any],
    reviewer_identity: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the evidence-only packet consumed by the critic.

    Worker reasoning is excluded and no executor is invoked. Large artifacts
    are represented by hashes and bounded excerpts.
    """
    accepted = tuple(sorted(getattr(candidate_run, "accepted_outputs", ()) or ()))
    plan = classify_completion_review(contract, accepted)
    artifacts: list[dict[str, Any]] = []
    for relative in accepted:
        path = project_root / relative
        artifacts.append({
            "path": relative,
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
            "sha256": _sha256(path) if path.is_file() else "",
            "excerpt": _bounded_text(path),
        })
    checks = [{
        "name": str(getattr(result, "name", "")),
        "passed": bool(getattr(result, "passed", False)),
        "exit_code": int(getattr(result, "exit_code", -1)),
        "failures": list(getattr(result, "failures", []) or []),
    } for result in check_results]
    packet: dict[str, Any] = {
        "schema_version": 1,
        "review_policy": "risk_based_completion_review_v1",
        "reviewer_identity": dict(reviewer_identity or {}),
        "task_id": str(getattr(contract, "task_id", "")),
        "goal": str(getattr(contract, "goal", "")),
        "stage": str(getattr(contract, "stage", "")),
        "work_lane": str(getattr(contract, "work_lane", "")),
        "review_plan": plan.to_dict(),
        "accepted_outputs": list(accepted),
        "observed_writes": list(getattr(candidate_run, "observed_writes", ()) or ()),
        "denied_writes": list(getattr(candidate_run, "denied_writes", ()) or ()),
        "undeclared_writes": list(getattr(candidate_run, "undeclared_writes", ()) or ()),
        "artifacts": artifacts,
        "checks": checks,
        "git_diff": _bounded_diff(project_root, accepted),
        "does_not_prove": [
            "scientific truth",
            "causal identification",
            "canonical promotion, claim admission, gate approval, or release",
            "real-world human identity",
        ],
    }
    identity_payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    packet["review_key"] = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()
    return packet


def render_review_evidence(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
