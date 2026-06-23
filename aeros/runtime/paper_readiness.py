"""Human-gated paper-readiness report.

This module turns the derived readiness vector into a review packet. It does
not approve paper readiness, release readiness, claim support, or gate status.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .readiness import build_readiness_vector, format_readiness_vector


@dataclass(frozen=True)
class PaperReadinessReport:
    recommendation: str
    authority_status: str
    paper_ready_verdict: str
    required_human_gate: bool
    readiness_vector: dict[str, Any]
    blockers: tuple[str, ...]
    human_actions: tuple[str, ...]
    packet_path: str = "decisions/paper_readiness/paper_readiness_report.md"
    does_not_prove: tuple[str, ...] = (
        "paper readiness",
        "scientific truth",
        "claim support",
        "gate approval",
        "release approval",
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["human_actions"] = list(self.human_actions)
        data["does_not_prove"] = list(self.does_not_prove)
        return data


def _blockers_from_readiness(readiness: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if readiness.get("paper") != "draft_present":
        blockers.append("paper_draft_missing")
    if readiness.get("claims") != "registry_present":
        blockers.append("claim_registry_missing_or_candidate_only")
    if readiness.get("analysis") != "results_registered":
        blockers.append("registered_results_missing")
    if readiness.get("literature") != "fulltext_verified":
        blockers.append("literature_fulltext_or_extraction_incomplete")
    if readiness.get("compliance") != "package_manifest_present":
        blockers.append("replication_or_compliance_preflight_missing")
    if readiness.get("release") != "approved":
        blockers.append("release_gate_not_human_approved")
    return blockers


def assess_paper_readiness(root: Path) -> PaperReadinessReport:
    vector = build_readiness_vector(root)
    readiness = vector.get("readiness") or {}
    blockers = _blockers_from_readiness(readiness)
    core_review_blockers = {
        "paper_draft_missing",
        "claim_registry_missing_or_candidate_only",
        "registered_results_missing",
    }
    if not any(blocker in core_review_blockers for blocker in blockers):
        recommendation = "ready_for_human_paper_readiness_review"
        human_actions = [
            "review paper draft against claim registry and registered results",
            "review literature extraction status before synthesis or positioning claims",
            "review compliance/release packet separately before public submission",
        ]
    else:
        recommendation = "not_ready_for_paper_readiness_review"
        human_actions = [
            "resolve core blockers before requesting paper-readiness review",
            "rerun aeros readiness after updating paper, claim, or result artifacts",
            "do not label the paper ready from this report alone",
        ]
    return PaperReadinessReport(
        recommendation=recommendation,
        authority_status="report_only",
        paper_ready_verdict="not_asserted",
        required_human_gate=True,
        readiness_vector=vector,
        blockers=tuple(blockers),
        human_actions=tuple(human_actions),
    )


def format_paper_readiness_report(report: PaperReadinessReport) -> str:
    lines = [
        "# Paper Readiness Report",
        "",
        f"- recommendation: {report.recommendation}",
        f"- authority_status: {report.authority_status}",
        f"- paper_ready_verdict: {report.paper_ready_verdict}",
        f"- required_human_gate: {str(report.required_human_gate).lower()}",
        "",
        "## Blockers",
        "",
    ]
    if report.blockers:
        lines.extend(f"- {blocker}" for blocker in report.blockers)
    else:
        lines.append("- none detected by mechanical readiness projection")
    lines.extend(["", "## Human actions", ""])
    lines.extend(f"- {action}" for action in report.human_actions)
    lines.extend(
        [
            "",
            "## Readiness vector",
            "",
            "```text",
            format_readiness_vector(report.readiness_vector).rstrip(),
            "```",
            "",
            "## Boundary",
            "",
            "This report is an audit packet. It does not approve paper readiness, gate status, release, or claims.",
            "",
            "does_not_prove:",
        ]
    )
    lines.extend(f"- {item}" for item in report.does_not_prove)
    return "\n".join(lines) + "\n"


def write_paper_readiness_report(root: Path, report: PaperReadinessReport) -> Path:
    path = root / report.packet_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_paper_readiness_report(report), encoding="utf-8")
    return path
