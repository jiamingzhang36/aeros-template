#!/usr/bin/env python3
"""Prevent goal/continue mode from reporting paperwork as data progress."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.action_receipt import (  # noqa: E402
    ACTION_DIR,
    _is_data_evidence_path,
    _is_paperwork_only_path,
    validate_payload,
)


REPORT_DIR = Path("agent_runs")
DATA_COMPLETION_PATTERNS = [
    r"\bcollect(?:ed|ion)?\s+data\b",
    r"\bdata\s+(?:backfill|collection|acquisition|refresh|validation|repair)\b",
    r"\bofficial\s+(?:source|data|validation|packet|record)",
    r"\bsource\s+(?:snapshot|validation|collection|acquisition)\b",
    r"\braw\s+data\b",
    r"抓数据",
    r"采集数据",
    r"数据(?:回填|抓取|采集|验证|补齐)",
    r"官方(?:来源|数据|文件|记录|表格)",
]
BLOCKED_MARKERS = {
    "blocked_queue_preparation",
    "source_discovery_attempt",
    "blocked",
    "do_not_promote",
    "not promoted",
    "no data acquired",
    "no source artifact acquired",
}


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _reports() -> Iterable[Path]:
    if not REPORT_DIR.exists():
        return []
    return sorted(
        path
        for path in REPORT_DIR.glob("*.md")
        if not path.name.startswith(("TEMPLATE_", "EXAMPLE_")) and path.name != "INDEX.csv"
    )


def _extract_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == heading.lower():
            out: list[str] = []
            for candidate in lines[i + 1 :]:
                if candidate.startswith("## "):
                    break
                out.append(candidate)
            return "\n".join(out)
    return ""


def _completion_status(text: str) -> str:
    section = _extract_section(text, "## Completion Status")
    for line in section.splitlines():
        cleaned = line.strip().strip("-* ").strip()
        if cleaned:
            return cleaned.lower()
    for line in text.splitlines():
        match = re.match(r"^\s*(?:[-*]\s*)?Completion Status\s*:\s*(.+)$", line, flags=re.I)
        if match:
            return match.group(1).strip().lower()
    return ""


def _path_candidates(text: str) -> list[str]:
    candidates: set[str] = set()
    candidates.update(match.strip() for match in re.findall(r"`([^`]+)`", text))
    for match in re.findall(r"(?<![\w.-])([A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+)(?![\w.-])", text):
        candidates.add(match.strip())
    return sorted(candidate for candidate in candidates if candidate)


def _has_real_data_evidence(root: Path, text: str) -> bool:
    return any(_is_data_evidence_path(root, candidate) for candidate in _path_candidates(text))


def _paperwork_only_paths(text: str) -> bool:
    paths = _path_candidates(text)
    if not paths:
        return False
    relevant = [path for path in paths if not path.startswith(("http://", "https://"))]
    if not relevant:
        return False
    return all(_is_paperwork_only_path(path) for path in relevant)


def _claims_data_completion(text: str) -> bool:
    lower = text.lower()
    if "action_mode:" in lower and "data_" in lower:
        return True
    if "honest_progress_label:" in lower and "substantive_research_progress" in lower:
        return True
    return any(re.search(pattern, lower, flags=re.I) for pattern in DATA_COMPLETION_PATTERNS)


def _is_honest_blocker(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in BLOCKED_MARKERS)


def _check_action_receipts(root: Path) -> list[str]:
    failures: list[str] = []
    receipt_root = root / ACTION_DIR
    if not receipt_root.exists():
        return failures
    for path in sorted(receipt_root.glob("*.yml")):
        payload = _read_yaml(path)
        if not payload:
            continue
        failures.extend(f"{path}: {failure}" for failure in validate_payload(payload, root))
    return failures


def _check_reports(root: Path) -> list[str]:
    failures: list[str] = []
    for path in _reports():
        text = path.read_text(encoding="utf-8", errors="ignore")
        completion = _completion_status(text)
        if completion != "complete":
            continue
        if not _claims_data_completion(text):
            continue
        if _is_honest_blocker(text):
            continue
        if _has_real_data_evidence(root, text):
            continue
        if _paperwork_only_paths(text) or "substantive_research_progress" in text:
            failures.append(
                f"{path}: claims completed data/source progress but cites no real data, source snapshot, "
                "inventory, or probe artifact"
            )
    return failures


def main() -> int:
    root = Path.cwd()
    failures = _check_action_receipts(root)
    failures.extend(_check_reports(root))
    if failures:
        print("FAIL: goal-mode data progress honesty problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: goal-mode data progress claims are artifact-backed or honestly blocked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
