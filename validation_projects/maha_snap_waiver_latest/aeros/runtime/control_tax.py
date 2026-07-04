"""Control-tax dashboard for AEROS project operation.

This is a derived dashboard. It summarizes how much recent work is control,
route, human-decision, or substantive artifact production. It does not approve
gates, certify claims, or score research quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


DOES_NOT_PROVE = [
    "that control work was unnecessary",
    "that substantive work is scientifically valid",
    "claim support",
    "that a gate or release is approved",
    "that lower control tax is always better",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def _receipt_paths(root: Path) -> list[Path]:
    return sorted((root / "agent_runs" / "completion_receipts").glob("*_completion_receipt.yml"))


def _receipt_bucket(receipt: dict[str, Any]) -> str:
    domain = str(receipt.get("progress_domain") or "").strip().lower()
    klass = str(receipt.get("progress_class") or "").strip().lower()
    outcome = str(receipt.get("outcome_kind") or "").strip().lower()
    authority = str(receipt.get("authority_status") or "").strip().lower()
    if domain == "governance" or "decision" in outcome or "approved" in authority:
        return "human_decisions"
    if klass in {"substantive", "substantive_produced"} or domain == "research":
        return "substantive_actions"
    if klass in {"routing", "route_ready"}:
        return "route_actions"
    return "control_actions"


def _accepted_artifact_count(root: Path) -> int:
    count = 0
    count += len(_csv_rows(root / "evidence" / "result_registry.csv"))
    count += len(list((root / "evidence" / "admissions").glob("*.yml")))
    count += len(list((root / "evidence" / "admissions").glob("*.yaml")))
    return count


def build_control_tax(root: Path) -> dict[str, Any]:
    root = root.resolve()
    buckets = {
        "control_actions": 0,
        "substantive_actions": 0,
        "route_actions": 0,
        "human_decisions": 0,
        "accepted_artifacts": _accepted_artifact_count(root),
    }
    receipt_examples: list[dict[str, str]] = []
    for path in _receipt_paths(root):
        receipt = _load_yaml(path)
        bucket = _receipt_bucket(receipt)
        buckets[bucket] += 1
        if len(receipt_examples) < 8:
            receipt_examples.append({
                "path": path.relative_to(root).as_posix(),
                "bucket": bucket,
                "progress_domain": str(receipt.get("progress_domain") or ""),
                "progress_class": str(receipt.get("progress_class") or ""),
            })
    decision_rows = _csv_rows(root / "decisions" / "decision_log.csv")
    buckets["human_decisions"] += len(decision_rows)
    route_records = _jsonl_records(root / "evidence" / "delta_log.jsonl")
    buckets["route_actions"] += sum(
        1
        for item in route_records
        if str(item.get("sufficiency_for_current_purpose") or "").lower()
        in {"route_ready", "blocked", "insufficient"}
    )
    total_actions = (
        buckets["control_actions"]
        + buckets["substantive_actions"]
        + buckets["route_actions"]
        + buckets["human_decisions"]
    )
    control_share = round(buckets["control_actions"] / total_actions, 4) if total_actions else 0.0
    substantive_share = round(buckets["substantive_actions"] / total_actions, 4) if total_actions else 0.0
    return {
        "version": "0.1",
        "policy": "AEROS-CONTROL-TAX-DASHBOARD-001",
        "project_root": str(root),
        "summary": buckets,
        "total_actions_counted": total_actions,
        "control_action_share": control_share,
        "substantive_action_share": substantive_share,
        "receipt_examples": receipt_examples,
        "source_files": [
            "agent_runs/completion_receipts/*_completion_receipt.yml",
            "decisions/decision_log.csv",
            "evidence/delta_log.jsonl",
            "evidence/result_registry.csv",
            "evidence/admissions/*.yml",
        ],
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_control_tax_dashboard(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# AEROS Control Tax Dashboard",
        "",
        "This is a derived operational dashboard. It separates control work from substantive research work so AEROS can get lighter without getting sloppy.",
        "",
        "## Counts",
    ]
    for key in ["control_actions", "substantive_actions", "route_actions", "human_decisions", "accepted_artifacts"]:
        lines.append(f"- {key}: {summary.get(key, 0)}")
    lines.extend([
        "",
        f"control_action_share: {report.get('control_action_share', 0.0)}",
        f"substantive_action_share: {report.get('substantive_action_share', 0.0)}",
        "",
        "## Recent Receipt Examples",
    ])
    examples = report.get("receipt_examples") or []
    if not examples:
        lines.append("- none")
    for item in examples:
        lines.append(
            f"- {item.get('bucket')}: {item.get('path')} "
            f"({item.get('progress_domain')}/{item.get('progress_class')})"
        )
    lines.extend(["", "## Does Not Prove"])
    for item in report.get("does_not_prove") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Use this dashboard to spot over-governance and fake progress risk; do not use it as a research-quality score.")
    return "\n".join(lines)


def write_control_tax_dashboard(root: Path) -> tuple[Path, Path]:
    report = build_control_tax(root)
    out_dir = root / "outputs" / "context"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "control_tax_dashboard.md"
    json_path = out_dir / "control_tax_dashboard.json"
    md_path.write_text(format_control_tax_dashboard(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path
