"""Derived project readiness vector.

Readiness is a compact projection over existing artifacts. It is not a gate
approval, claim certification, or release decision.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle)]


def build_readiness_vector(project_root: Path) -> dict[str, Any]:
    data_contract = _load_yaml(project_root / "docs/data_contract.yml").get("data_contract") or {}
    paper_rows = _csv_rows(project_root / "discovery/literature/paper_registry.csv")
    result_rows = _csv_rows(project_root / "evidence/result_index.csv")
    claim_registry = project_root / "evidence/claim_registry.md"
    paper_draft = project_root / "paper/draft.md"
    compliance_manifest = project_root / "replication/aea_data_package_manifest.yml"
    state = _load_yaml(project_root / "aeros_state.yml")

    fulltext_rows = [
        row for row in paper_rows
        if str(row.get("evidence_basis", "")).strip() in {"full_text", "extraction_card"}
        and str(row.get("extraction_card", "")).strip().lower() == "yes"
    ]
    literature_blockers = [
        row for row in paper_rows
        if str(row.get("status", "")).strip().lower() in {"blocked_fulltext", "blocked", "retrieval_blocked"}
        or "blocked_fulltext" in str(row.get("notes", "")).strip().lower()
        or "remains abstract_only" in str(row.get("notes", "")).strip().lower()
    ]
    abstract_only_rows = [
        row for row in paper_rows
        if str(row.get("status", "")).strip().lower() == "abstract_only"
        or str(row.get("evidence_basis", "")).strip().lower() == "abstract"
    ]
    if not paper_rows:
        literature_status = "metadata_or_queue"
    elif literature_blockers:
        literature_status = "fulltext_partial_blocked" if fulltext_rows else "blocked_fulltext"
    elif abstract_only_rows:
        literature_status = "partial_extraction"
    elif fulltext_rows:
        literature_status = "fulltext_verified"
    else:
        literature_status = "metadata_or_queue"
    data_status = "contract_draft"
    if data_contract.get("status") in {"locked", "active"}:
        data_status = "contract_ready"
    if list((project_root / "data/probes").glob("*/probe_metadata.yml")):
        data_status = "probing"
    if result_rows:
        data_status = "results_registered"

    return {
        "version": "0.1",
        "policy": "AEROS-READINESS-VECTOR-001",
        "does_not_prove": [
            "gate approval",
            "claim support",
            "scientific validity",
            "release readiness",
        ],
        "readiness": {
            "data": data_status,
            "literature": literature_status,
            "analysis": "results_registered" if result_rows else "not_ready",
            "claims": "registry_present" if claim_registry.exists() else "candidate_only",
            "paper": "draft_present" if paper_draft.exists() else "not_started",
            "compliance": "package_manifest_present" if compliance_manifest.exists() else "preflight_required",
            "release": "approved" if state.get("current_gate") == "G13" and state.get("gate_status") == "approved" else "not_approved",
        },
        "counts": {
            "literature_registry_rows": len(paper_rows),
            "verified_fulltext_rows": len(fulltext_rows),
            "literature_blocker_rows": len(literature_blockers),
            "abstract_only_rows": len(abstract_only_rows),
            "result_index_rows": len(result_rows),
        },
    }


def format_readiness_vector(vector: dict[str, Any]) -> str:
    lines = ["# AEROS Readiness Vector", ""]
    for lane, status in (vector.get("readiness") or {}).items():
        lines.append(f"- {lane}: {status}")
    counts = vector.get("counts") or {}
    if counts:
        lines.extend(["", "counts:"])
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "does_not_prove:"])
    for item in vector.get("does_not_prove") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"
