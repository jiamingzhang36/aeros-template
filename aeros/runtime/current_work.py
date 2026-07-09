"""Current work context for AEROS driver/next-action ranking.

The current-work file is an operator hint, not authority. It lets a project say
"right now I am working on the poster/manuscript/data probe" so AEROS does not
mechanically fall back to broad-capture/data-first recommendations when the
active deliverable is paper-facing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


CONTEXT_PATHS = (
    Path("CURRENT_WORK.yml"),
    Path("aeros/state/current_work.yml"),
)

LANES = {"data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"}

DOES_NOT_PROVE = [
    "that the current objective is scientifically optimal",
    "that higher-priority harness failures can be ignored",
    "that paper, claim, gate, or release authority is granted",
    "that a human decision has been made",
]


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _norm(item)
        if text and text not in out:
            out.append(text)
    return out


def _infer_lane(blob: str) -> str:
    text = blob.lower()
    if any(token in text for token in ("poster", "manuscript", "paper", "submission", "draft", "tex", "response")):
        return "writing"
    if any(token in text for token in ("literature", "citation", "bib", "fulltext", "full-text", "zotero")):
        return "literature"
    if any(token in text for token in ("claim", "ceiling", "registry")):
        return "claim"
    if any(token in text for token in ("method", "identification", "causal", "robustness", "spec")):
        return "method"
    if any(token in text for token in ("data", "source", "capture", "probe", "backfill", "denominator")):
        return "data"
    return ""


def load_current_work_context(root: Path | str = Path.cwd()) -> dict[str, Any]:
    root = Path(root)
    source = ""
    payload: dict[str, Any] = {}
    if yaml is not None:
        for rel in CONTEXT_PATHS:
            path = root / rel
            if not path.exists():
                continue
            source = rel.as_posix()
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                payload = loaded
            break
    active_goal = _norm(payload.get("active_goal") or payload.get("current_goal"))
    active_deliverable = _norm(payload.get("active_deliverable") or payload.get("deliverable"))
    active_lane = _norm(payload.get("active_lane") or payload.get("lane")).lower()
    if active_lane not in LANES:
        active_lane = _infer_lane(" ".join([active_goal, active_deliverable, " ".join(_norm_list(payload.get("priority_order")))]))
    status = "active" if (active_goal or active_deliverable or active_lane) else "absent"
    priority_order = _norm_list(payload.get("priority_order"))
    deprioritized = _norm_list(payload.get("explicitly_deprioritized"))
    preferred_risk_domains: list[str] = []
    context_text = " ".join([active_goal, active_deliverable]).lower()
    if active_lane in {"writing", "literature", "compliance"} or any(token in context_text for token in ("poster", "manuscript", "submission", "citation")):
        preferred_risk_domains.append("submission_truth")
    if active_lane == "data":
        preferred_risk_domains.append("capture_efficiency")
    return {
        "status": status,
        "source_path": source,
        "active_goal": active_goal,
        "active_deliverable": active_deliverable,
        "active_lane": active_lane,
        "priority_order": priority_order,
        "explicitly_deprioritized": deprioritized,
        "preferred_risk_domains": preferred_risk_domains,
        "ranking_rule": [
            "hard harness/process failures still outrank current-work hints",
            "human gates still outrank current-work hints",
            "research-risk findings still outrank routine lane progress",
            "when no higher-priority risk exists, current active_lane biases next/drive routing",
        ],
        "does_not_prove": DOES_NOT_PROVE,
    }


def preferred_lane(root: Path | str = Path.cwd(), *, fallback: str = "") -> str:
    context = load_current_work_context(root)
    lane = _norm(context.get("active_lane")).lower()
    return lane if lane in LANES else fallback

