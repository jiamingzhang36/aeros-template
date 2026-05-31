#!/usr/bin/env python3
"""Emit a one-shot project status dashboard used by operators."""

from __future__ import annotations

import csv
from pathlib import Path
import re
from collections import Counter
from typing import Any, Iterable

import yaml


MANIFEST = Path("project_manifest.yml")
AEROS_STATE = Path("aeros_state.yml")
IDEA_BANK = Path("discovery/idea_bank.csv")
PAPER_REGISTRY = Path("discovery/literature/paper_registry.csv")
CLAIM_REGISTRY = Path("evidence/claim_registry.md")
DECISION_LOG = Path("decisions/decision_log.csv")
PROTECTED_DEFS_SECTION = "protected_files"
PROVENANCE_DIR = Path("outputs/.provenance")


PLACEHOLDER_VALUES = {"", "tbd", "todo", "to be determined", "to be filled", "na", "n/a"}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).strip().lower()


def _is_placeholder(value: Any) -> bool:
    return _norm_lower(value) in PLACEHOLDER_VALUES


def _extract_status_dist(rows: Iterable[dict[str, str]], status_key: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        key = _norm(row.get(status_key, "")).lower() or "unlabeled"
        counts[key] += 1
    return counts


def _count_stale(rows: Iterable[dict[str, str]], status_key: str) -> int:
    return sum(
        1 for row in rows if _norm_lower(row.get(status_key, "")).startswith("stale")
    )


def _is_truthy_yes(value: Any) -> bool:
    normalized = _norm_lower(value)
    return normalized in {"yes", "y", "true", "1", "checked", "done", "ok"}


def _is_placeholder_extraction(value: Any) -> bool:
    return not _is_truthy_yes(value)


def _parse_markdown_table_rows(path: Path, required_headers: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    normalized_required = [hdr.lower() for hdr in required_headers]
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if [h.lower() for h in headers] != [h.lower() for h in required_headers]:
            continue
        if i + 1 >= len(lines):
            continue
        sep = lines[i + 1].strip()
        if not re.match(r"^\s*\|?\s*:?-{3,}\s*:?(?:\|\s*:?-{3,}\s*:?\|?)*\s*$", sep):
            continue

        data: list[dict[str, str]] = []
        for row_line in lines[i + 2 :]:
            row_str = row_line.strip()
            if not row_str.startswith("|"):
                break
            cells = [cell.strip() for cell in row_str.strip("|").split("|")]
            if len(cells) < len(headers):
                continue
            data.append(dict(zip(headers, cells)))
        if data:
            return data
    return []


def _parse_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parse_decision_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        return _parse_csv_rows(path)

    headers = [
        "Date",
        "Decision ID",
        "Task ID",
        "Agent Recommendation",
        "Critic Verdict",
        "Human Decision",
        "Rationale",
        "Owner",
        "Follow-up",
    ]
    return _parse_markdown_table_rows(path, headers)


def _protected_file_statuses(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    outputs: list[tuple[str, str]] = []
    protected_files = manifest.get(PROTECTED_DEFS_SECTION, [])
    for item in protected_files if isinstance(protected_files, list) else []:
        path = Path(str(item))
        status = "missing"
        if not path.exists():
            outputs.append((str(path), status))
            continue

        if path.suffix.lower() in {".yml", ".yaml"}:
            try:
                payload = _load_yaml(path)
                status = _norm(payload.get("status", "unlabeled")) or "unlabeled"
            except Exception:
                status = "parse_failed"
        else:
            # Best effort: front-matter YAML in markdown or explicit `status:` line
            text = path.read_text(encoding="utf-8")
            match = re.search(r"^status:\s*(.+)$", text, flags=re.M)
            if match:
                status = _norm(match.group(1)).strip('"\'')
            else:
                status = "no_status"
        outputs.append((str(path), status))
    return outputs


def _paper_result_references() -> list[str]:
    paper_dir = Path("paper")
    if not paper_dir.exists() or not paper_dir.is_dir():
        return []
    refs: set[str] = set()
    for path in paper_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".tex", ".qmd", ".Rmd"}:
            continue
        text = path.read_text(encoding="utf-8")
        refs.update(re.findall(r"\bR\d{3}\b", text))
    return sorted(refs)


def main() -> int:
    if not MANIFEST.exists():
        print("FAIL: project_status failed: missing project_manifest.yml")
        return 1

    manifest = _load_yaml(MANIFEST)
    runtime_state = _load_yaml(AEROS_STATE) if AEROS_STATE.exists() else {}
    project = manifest.get("project", {})
    gate_lifecycle = manifest.get("gate_lifecycle", {})

    print("AEROS Project Status Dashboard")
    print("------------------------------")
    stage = _norm(runtime_state.get("current_stage", ""))
    if not stage:
        stage = _norm(project.get("current_stage", ""))
    if not stage:
        stage = _norm(manifest.get("research", {}).get("current_stage", "unknown"))
    print(
        "Project: "
        f"{_norm(project.get('name', 'unnamed'))} | "
        f"Status: {_norm(project.get('status', 'unknown'))} | "
        f"Stage: {stage}"
    )
    current_gate = runtime_state.get("current_gate") or gate_lifecycle.get("current_gate", "unknown")
    print(f"Current gate: {current_gate}")
    if runtime_state.get("gate_status"):
        print(f"Gate status: {runtime_state.get('gate_status')}")
    if runtime_state.get("candidate_gate"):
        print(
            "Candidate gate: "
            f"{runtime_state.get('candidate_stage', 'unknown')} / {runtime_state.get('candidate_gate')}"
        )

    idea_rows = _read_csv_rows(IDEA_BANK)
    idea_status = _extract_status_dist(idea_rows, "status")
    idea_stale = _count_stale(idea_rows, "status")
    print("\nIdea Bank")
    print(f"- total: {len(idea_rows)}")
    print(f"- stale: {idea_stale}")
    if idea_status:
        print(f"- status distribution: {dict(idea_status)}")
    else:
        print("- status distribution: no data")

    paper_rows = _read_csv_rows(PAPER_REGISTRY)
    paper_status = _extract_status_dist(paper_rows, "status")
    missing_extraction = 0
    for row in paper_rows:
        if _is_placeholder_extraction(row.get("extraction_card")):
            missing_extraction += 1
    print("\nLiterature Registry")
    print(f"- total papers: {len(paper_rows)}")
    print(f"- papers missing extraction cards: {missing_extraction}")
    if paper_status:
        print(f"- status distribution: {dict(paper_status)}")
    else:
        print("- status distribution: no data")

    claim_rows = _parse_markdown_table_rows(
        CLAIM_REGISTRY,
        ["Claim ID", "Claim", "Type", "Status", "Evidence ID(s)", "Result ID(s)", "Boundary / Limitation", "Approved"],
    )
    claim_status = _extract_status_dist(claim_rows, "Status")
    print("\nClaim Registry")
    print(f"- total claims: {len(claim_rows)}")
    if claim_status:
        print(f"- status distribution: {dict(claim_status)}")
    else:
        print("- status distribution: no claims")
    claim_draft = claim_status.get("draft", 0)
    print(f"- draft claims: {claim_draft}")

    print("\nProtected Definitions")
    for path, status in _protected_file_statuses(manifest):
        print(f"- {path}: {status}")

    decisions = _parse_decision_rows(DECISION_LOG)
    pending: list[tuple[str, str]] = []
    for row in decisions:
        decision = _norm_lower(row.get("Human Decision", ""))
        if not decision or decision in PLACEHOLDER_VALUES or decision in {"todo", "pending", "in progress"}:
            pending.append((row.get("Decision ID", ""), row.get("Task ID", "")))
    print("\nHuman Decisions")
    print(f"- pending entries: {len(pending)}")
    if pending:
        preview = ", ".join(f"{i}-{t}" for i, t in pending[:5]) or "(none)"
        print(f"- pending preview: {preview}")
        if len(pending) > 5:
            print(f"- ... plus {len(pending)-5} more")

    print("\nProvenance")
    result_dir = PROVENANCE_DIR
    if result_dir.exists():
        provenance_count = len(list(result_dir.glob("*.json")))
    else:
        provenance_count = 0
    print(f"- provenance records: {provenance_count}")

    paper_refs = _paper_result_references()
    print(f"- paper-result references: {len(paper_refs)}")
    if paper_refs:
        print(f"- top refs: {', '.join(paper_refs[:5])}")
    print("STATUS: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
