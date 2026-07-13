"""Deterministic research-risk compiler for AEROS.

This module is the small PI/editor-style projection layer: it ranks existing
AEROS signals by research risk so `aeros drive` and `aeros next` can explain why
a citation-grounding or promotion-boundary issue outranks mechanical stale
revalidation. It is advisory and read-only. It does not approve gates, edit
claims, run providers, or certify scientific truth.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .broad_capture import summarize_broad_capture
from .citation_sentence_grounding import build_sentence_citation_grounding
from .submission_driver import build_submission_driver


DOES_NOT_PROVE = [
    "that the top-ranked risk is scientifically optimal",
    "that omitted risks are absent",
    "that citation-function inference is perfect",
    "that a lead/candidate is evidence",
    "that claim, paper, gate, or release authority is granted",
]


@dataclass(frozen=True)
class ResearchRiskItem:
    risk_id: str
    domain: str
    lane: str
    score: int
    severity: str
    status_label: str
    recommended_action: str
    why: str
    command: str
    stop_condition: str
    expected_artifacts: tuple[str, ...]
    outranks: tuple[str, ...]
    source: str
    can_run_without_human: bool = True
    needs_human: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected_artifacts"] = list(self.expected_artifacts)
        data["outranks"] = list(self.outranks)
        return data


def _severity(score: int) -> str:
    if score >= 80:
        return "p0"
    if score >= 55:
        return "p1"
    if score > 0:
        return "p2"
    return "none"


def _submission_truth_item(root: Path) -> ResearchRiskItem | None:
    grounding = build_sentence_citation_grounding(root)
    counts = grounding.get("counts") or {}
    debt = int(counts.get("citation_debt_rows") or 0)
    blocking = int(counts.get("blocking_rows") or 0)
    if debt <= 0 and blocking <= 0:
        return None
    score = min(100, 70 + blocking * 10 + max(0, debt - blocking) * 3)
    return ResearchRiskItem(
        risk_id="submission_truth_risk",
        domain="submission_truth",
        lane="writing",
        score=score,
        severity=_severity(score),
        status_label="ROUTE_READY",
        recommended_action="Resolve manuscript citation debt before mechanical stale recovery.",
        why=(
            f"Sentence-level citation grounding reports {debt} citation-debt row(s), "
            f"including {blocking} blocking row(s). Claim-bearing manuscript truth can affect paper readiness more than routine stale revalidation."
        ),
        command="python3 checks/check_manuscript_citation_faithfulness.py",
        stop_condition="Stop after citation debt rows identify whether to recover full text, add extraction cards, add interpretation records, weaken prose, or replace citations.",
        expected_artifacts=("audits/citation_debt_report.csv",),
        outranks=("stale_revalidate", "mechanical_bookkeeping", "routine_lane_progress"),
        source="aeros.runtime.citation_sentence_grounding",
        can_run_without_human=True,
        needs_human=False,
    )


def _wrapper_sync_item(root: Path) -> ResearchRiskItem | None:
    report = build_submission_driver(root)
    wrapper = report.get("literature_wrapper_sync") or {}
    if wrapper.get("status") != "fail":
        return None
    missing = len(wrapper.get("missing_cards") or [])
    score = min(95, 75 + missing)
    return ResearchRiskItem(
        risk_id="literature_visibility_risk",
        domain="submission_truth",
        lane="literature",
        score=score,
        severity=_severity(score),
        status_label="ROUTE_READY",
        recommended_action="Resolve literature wrapper/source-project sync before judging literature readiness.",
        why=(
            f"The wrapper literature view is incomplete ({missing} missing card(s)); AEROS may otherwise route from a blind evidence state."
        ),
        command="python3 checks/check_literature_wrapper_sync.py",
        stop_condition="Stop after source-project cards are imported, intentionally waived, or the source-project link is corrected.",
        expected_artifacts=("adoption/source_manifest.yml", "discovery/literature/extraction_cards/"),
        outranks=("stale_revalidate", "routine_literature_status"),
        source="aeros.runtime.submission_driver",
        can_run_without_human=True,
        needs_human=False,
    )


def _capture_efficiency_item(root: Path) -> ResearchRiskItem | None:
    summary = summarize_broad_capture(root)
    total_leads = int(summary.get("total_leads") or 0)
    total_candidates = int(summary.get("total_candidates") or 0)
    saturation = bool(summary.get("capture_saturation_stop"))
    stale = int(summary.get("stale_lead_count") or 0)
    duplicates = int(summary.get("duplicate_lead_count") or 0)
    if not saturation:
        return None
    score = min(80, 50 + stale + duplicates + max(0, total_leads - 20))
    return ResearchRiskItem(
        risk_id="capture_efficiency_risk",
        domain="capture_efficiency",
        lane="data",
        score=score,
        severity=_severity(score),
        status_label="CAPTURE_LOGGED",
        recommended_action="Triage existing leads or review/promote the candidate pool before collecting more.",
        why=(
            f"Broad capture appears saturated: leads={total_leads}, candidates={total_candidates}, stale={stale}, duplicates={duplicates}, "
            f"lead_to_candidate_rate={summary.get('lead_to_candidate_rate')}. More capture may be lower value than triage."
        ),
        command='python3 -m aeros.cli task preflight --lane data --intent "triage existing broad-capture candidates for promotion readiness" --json',
        stop_condition="Stop after lead triage/promotion blockers are visible; do not promote to processed/canonical/claim without promotion checks.",
        expected_artifacts=("data/backfill/*_lead_queue.csv", "data/backfill/*_candidate_queue.csv", "audits/broad_capture/"),
        outranks=("more_broad_capture", "routine_data_scan"),
        source="aeros.runtime.broad_capture",
        can_run_without_human=True,
        needs_human=False,
    )


def compile_research_risk(root: Path | str = Path.cwd(), *, lane: str = "") -> dict[str, Any]:
    root = Path(root)
    requested_lane = (lane or "").strip()
    items = [item for item in (
        _submission_truth_item(root),
        _wrapper_sync_item(root),
        _capture_efficiency_item(root),
    ) if item is not None]
    if requested_lane:
        lane_items = [item for item in items if item.lane == requested_lane or (requested_lane in {"literature", "writing", "compliance"} and item.domain == "submission_truth")]
    else:
        lane_items = items
    ranked = sorted(lane_items, key=lambda item: (-item.score, item.domain, item.risk_id))
    top = ranked[0] if ranked else None
    return {
        "model": "AEROS-RESEARCH-RISK-002",
        "status": "RISKS_FOUND" if top else "CLEAR",
        "requested_lane": requested_lane,
        "top_risk": top.to_dict() if top else None,
        "ranked_risks": [item.to_dict() for item in ranked],
        "risk_vector": {
            "submission_truth_risk": next((item.score for item in items if item.risk_id == "submission_truth_risk"), 0),
            "literature_visibility_risk": next((item.score for item in items if item.risk_id == "literature_visibility_risk"), 0),
            "capture_efficiency_risk": next((item.score for item in items if item.risk_id == "capture_efficiency_risk"), 0),
            "mechanical_integrity_risk": 0,
        },
        "ranking_rule": [
            "hard process/harness violations are handled before research-risk ranking",
            "submission truth and citation debt outrank routine stale revalidation",
            "claim/promotion/data pollution risks outrank cosmetic bookkeeping",
            "capture saturation triggers triage before more collection",
        ],
        "does_not_prove": DOES_NOT_PROVE,
    }
