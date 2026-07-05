"""Typed artifact graph and claim-admissibility compiler for AEROS v0.5.

This module does not decide scientific truth. It decides whether artifact/edge
uses are formally admissible and compiles the maximum claim language allowed by
the evidence graph, estimand support, identification diagnostics, contradictions,
obligations, and exception debt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArtifactType(str, Enum):
    ACTION_RECEIPT = "action_receipt"
    SOURCE_POINTER = "source_pointer"
    RAW_DATA_SNAPSHOT = "raw_data_snapshot"
    PROCESSED_DATA_SNAPSHOT = "processed_data_snapshot"
    PROBE_REPORT = "probe_report"
    VALIDATION_REPORT = "validation_report"
    SPEC_RUN_RESULT = "spec_run_result"
    ROBUSTNESS_RESULT = "robustness_result"
    IDENTIFICATION_DIAGNOSTIC = "identification_diagnostic"
    HUMAN_GATE_DECISION = "human_gate_decision"
    PREANALYSIS_PLAN = "preanalysis_plan"
    ESTIMAND_CARD = "estimand_card"
    CLAIM_CARD = "claim_card"
    EXCEPTION = "exception"


class EdgeUse(str, Enum):
    LOGS = "logs"
    POINTS_TO = "points_to"
    DERIVES = "derives"
    PROBES = "probes"
    VALIDATES = "validates"
    PRODUCES_RESULT = "produces_result"
    SUPPORTS_FEASIBILITY = "supports_feasibility"
    SUPPORTS_DESCRIPTIVE = "supports_descriptive"
    SUPPORTS_ASSOCIATIONAL = "supports_associational"
    SUPPORTS_CAUSAL = "supports_causal"
    CONTRADICTS = "contradicts"
    AUTHORIZES = "authorizes"
    QUALIFIES = "qualifies"


class ClaimLanguageLevel(str, Enum):
    NONE = "none"
    FEASIBILITY = "feasibility"
    DESCRIPTIVE = "descriptive"
    ASSOCIATIONAL = "associational"
    QUASI_EXPERIMENTAL_SUGGESTIVE = "quasi_experimental_suggestive"
    LIMITED_CAUSAL = "limited_causal"
    STRONG_CAUSAL = "strong_causal"


@dataclass(frozen=True)
class ArtifactNode:
    artifact_id: str
    artifact_type: ArtifactType
    path: str = ""
    state_label: str = "unknown"
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceEdge:
    source_id: str
    target_id: str
    use: EdgeUse
    evidence_type: ArtifactType
    strength: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    severity: str
    reason: str
    required_before: str


@dataclass(frozen=True)
class ClaimAdmissibility:
    claim_id: str
    admissible: bool
    ceiling: ClaimLanguageLevel
    obligations: list[Obligation]
    exception_debt: float
    risk_flags: list[str]
    reasons: list[str]


ADMISSIBILITY: dict[ArtifactType, set[EdgeUse]] = {
    ArtifactType.ACTION_RECEIPT: {EdgeUse.LOGS},
    ArtifactType.SOURCE_POINTER: {EdgeUse.POINTS_TO},
    ArtifactType.RAW_DATA_SNAPSHOT: {EdgeUse.DERIVES},
    ArtifactType.PROCESSED_DATA_SNAPSHOT: {EdgeUse.DERIVES},
    ArtifactType.PROBE_REPORT: {EdgeUse.SUPPORTS_FEASIBILITY, EdgeUse.QUALIFIES},
    ArtifactType.VALIDATION_REPORT: {EdgeUse.VALIDATES, EdgeUse.QUALIFIES},
    ArtifactType.SPEC_RUN_RESULT: {EdgeUse.SUPPORTS_DESCRIPTIVE, EdgeUse.SUPPORTS_ASSOCIATIONAL, EdgeUse.CONTRADICTS},
    ArtifactType.ROBUSTNESS_RESULT: {EdgeUse.QUALIFIES, EdgeUse.CONTRADICTS},
    ArtifactType.IDENTIFICATION_DIAGNOSTIC: {EdgeUse.QUALIFIES, EdgeUse.SUPPORTS_CAUSAL, EdgeUse.CONTRADICTS},
    ArtifactType.HUMAN_GATE_DECISION: {EdgeUse.AUTHORIZES},
    ArtifactType.PREANALYSIS_PLAN: {EdgeUse.QUALIFIES},
    ArtifactType.ESTIMAND_CARD: {EdgeUse.QUALIFIES},
    ArtifactType.CLAIM_CARD: set(),
    ArtifactType.EXCEPTION: {EdgeUse.QUALIFIES},
}

CEILING_BY_USE: dict[EdgeUse, ClaimLanguageLevel] = {
    EdgeUse.SUPPORTS_FEASIBILITY: ClaimLanguageLevel.FEASIBILITY,
    EdgeUse.SUPPORTS_DESCRIPTIVE: ClaimLanguageLevel.DESCRIPTIVE,
    EdgeUse.SUPPORTS_ASSOCIATIONAL: ClaimLanguageLevel.ASSOCIATIONAL,
    EdgeUse.SUPPORTS_CAUSAL: ClaimLanguageLevel.LIMITED_CAUSAL,
}


def admissible_edge(edge: EvidenceEdge) -> tuple[bool, str]:
    allowed = ADMISSIBILITY.get(edge.evidence_type, set())
    if edge.use not in allowed:
        return False, f"{edge.evidence_type.value} cannot be used as {edge.use.value}"
    return True, "ok"


def _min_ceiling(left: ClaimLanguageLevel, right: ClaimLanguageLevel) -> ClaimLanguageLevel:
    order = list(ClaimLanguageLevel)
    return order[min(order.index(left), order.index(right))]


def compile_claim_admissibility(claim_id: str, edges: list[EvidenceEdge]) -> ClaimAdmissibility:
    obligations: list[Obligation] = []
    risk_flags: list[str] = []
    reasons: list[str] = []
    exception_debt = 0.0
    ceiling = ClaimLanguageLevel.NONE
    admissible = True

    if not edges:
        return ClaimAdmissibility(claim_id, False, ClaimLanguageLevel.NONE, [
            Obligation("missing_support_graph", "hard", "claim has no support edges", "claim_audit")
        ], 0.0, ["no_support_edges"], ["no support graph supplied"])

    for edge in edges:
        ok, reason = admissible_edge(edge)
        if not ok:
            admissible = False
            obligations.append(Obligation("inadmissible_edge", "hard", reason, "claim_audit"))
            risk_flags.append("evidence_laundering")
        else:
            reasons.append(reason)
        if edge.use in CEILING_BY_USE:
            proposed = CEILING_BY_USE[edge.use]
            ceiling = proposed if ceiling == ClaimLanguageLevel.NONE else max(ceiling, proposed, key=list(ClaimLanguageLevel).index)
        if edge.use == EdgeUse.CONTRADICTS:
            ceiling = _min_ceiling(ceiling if ceiling != ClaimLanguageLevel.NONE else ClaimLanguageLevel.DESCRIPTIVE, ClaimLanguageLevel.ASSOCIATIONAL)
            obligations.append(Obligation("resolve_contradiction", "hard", "contradicting evidence present", "claim_upgrade"))
            risk_flags.append("contradiction_unresolved")
        if edge.evidence_type == ArtifactType.EXCEPTION:
            debt = float(edge.metadata.get("exception_debt", 1.0) or 1.0)
            exception_debt += debt
            obligations.append(Obligation("exception_debt", "medium", "exception limits claim language until reviewed", "release_gate"))
            risk_flags.append("exception_debt")

    has_estimand = any(edge.evidence_type == ArtifactType.ESTIMAND_CARD for edge in edges)
    if ceiling in {ClaimLanguageLevel.ASSOCIATIONAL, ClaimLanguageLevel.QUASI_EXPERIMENTAL_SUGGESTIVE, ClaimLanguageLevel.LIMITED_CAUSAL, ClaimLanguageLevel.STRONG_CAUSAL} and not has_estimand:
        obligations.append(Obligation("missing_estimand", "hard", "non-descriptive claim requires an estimand card", "claim_audit"))
        admissible = False
        risk_flags.append("missing_estimand")

    if exception_debt >= 3:
        ceiling = _min_ceiling(ceiling, ClaimLanguageLevel.DESCRIPTIVE)
        obligations.append(Obligation("high_exception_debt", "hard", "exception debt caps claim ceiling", "human_gate"))

    return ClaimAdmissibility(claim_id, admissible and not any(o.severity == "hard" for o in obligations), ceiling, obligations, exception_debt, sorted(set(risk_flags)), reasons)
