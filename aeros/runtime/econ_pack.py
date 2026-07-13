"""Economics-native execution projections built on the existing AEROS core.

This module adds no research authority. It validates the empirical object chain,
compiles method protocols, prioritizes project literature, summarizes observed
skill usefulness, and maps six user-facing drive jobs onto existing commands.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
from typing import Any

import yaml

ECON_DIR = Path("evidence/econ")
REGISTRIES = {
    "samples": ("sample_registry.csv", ["sample_id", "dataset_snapshot_ids", "population", "time_window", "filters", "n_expected", "status"]),
    "specifications": ("specification_registry.csv", ["spec_id", "estimand_id", "sample_id", "outcome", "treatment", "controls", "fixed_effects", "cluster", "weights", "window", "estimator", "software", "package_versions", "protocol", "status"]),
    "exhibits": ("exhibit_registry.csv", ["exhibit_id", "result_id", "spec_id", "artifact_path", "cell_or_panel", "status"]),
    "sentences": ("sentence_binding_registry.csv", ["sentence_id", "manuscript_path", "sentence_locator", "exhibit_id", "result_id", "claim_id", "status"]),
}

PROTOCOLS: dict[str, dict[str, Any]] = {
    "iv": {"diagnostics": ["first_stage", "partial_f", "reduced_form", "weak_iv_robust_inference", "sample_consistency"], "human_review": ["instrument_definition", "exclusion_restriction"]},
    "did": {"diagnostics": ["panel_balance", "treatment_timing", "parallel_trends", "event_study_window", "pretrend_joint_test", "staggered_adoption_estimator"], "human_review": ["parallel_trends_plausibility", "anticipation"]},
    "rd": {"diagnostics": ["running_variable", "cutoff", "bandwidth_sensitivity", "density_test", "covariate_balance", "donut_rd"], "human_review": ["continuity_assumption", "manipulation_risk"]},
    "panel": {"diagnostics": ["panel_balance", "within_variation", "fixed_effects", "cluster_level", "serial_correlation", "sample_consistency"], "human_review": ["strict_exogeneity", "dynamic_bias"]},
    "synthetic_control": {"diagnostics": ["donor_pool", "pre_fit", "predictor_balance", "placebo_distribution", "leave_one_out", "post_pre_rmspe"], "human_review": ["no_interference", "donor_admissibility"]},
}

DRIVE_JOBS: dict[str, dict[str, Any]] = {
    "find_data": {"lane": "data", "command": "python3 -m aeros.cli data plan", "artifact": "discovery/data_inventory.csv", "stop": "candidate provider-native sources and the smallest next probe are identified"},
    "probe_data": {"lane": "data", "command": "python3 -m aeros.cli data probe official --series-id auto --json", "artifact": "data/probes/*/probe.json", "stop": "a bounded official-source sample pins provider ID/release and verifies units, coverage, missingness, and join keys"},
    "run_specification": {"lane": "analysis", "command": "python3 -m aeros.cli drive --job run_specification --source-candidate PATH --target SPEC_ID --execute", "artifact": "outputs/econ/specification_runs/*.json", "stop": "a registered simple OLS specification is executed in isolation and accepted only as a nonproduction candidate result"},
    "diagnose_design": {"lane": "method", "command": "python3 -m aeros.cli econ protocol --name panel --json", "artifact": "audits/advisory/econ_protocol_packet.json", "stop": "machine diagnostics and human identification questions are separated"},
    "read_literature": {"lane": "literature", "command": "python3 -m aeros.cli econ literature-radar --json", "artifact": "audits/literature/econ_literature_radar.json", "stop": "read_now/watch/ignore queues are refreshed from project relevance"},
    "bind_or_reproduce_paper": {"lane": "writing", "command": "python3 -m aeros.cli econ chain --json", "artifact": "evidence/econ/sentence_binding_registry.csv", "stop": "every registered sentence resolves through exhibit/result/specification/sample or is reported as debt"},
}


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists(): return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _claim_ids(path: Path) -> set[str]:
    if not path.exists(): return set()
    table = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("|")]
    if not table: return set()
    header = [cell.strip().lower() for cell in table[0].strip().strip("|").split("|")]
    try: index = header.index("claim id")
    except ValueError: return set()
    out: set[str] = set()
    for line in table[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if index < len(cells) and cells[index]: out.add(cells[index])
    return out


def initialize_registries(root: Path) -> list[Path]:
    paths: list[Path] = []
    base = root / ECON_DIR; base.mkdir(parents=True, exist_ok=True)
    for filename, fields in REGISTRIES.values():
        path = base / filename
        if not path.exists(): path.write_text(",".join(fields) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def validate_object_chain(root: Path) -> dict[str, Any]:
    paths = {name: root / ECON_DIR / spec[0] for name, spec in REGISTRIES.items()}
    rows = {name: _rows(path) for name, path in paths.items()}
    ids = {"samples": {r.get("sample_id", "") for r in rows["samples"]}, "specifications": {r.get("spec_id", "") for r in rows["specifications"]}, "exhibits": {r.get("exhibit_id", "") for r in rows["exhibits"]}}
    result_ids = {r.get("result_id", "") for r in _rows(root / "evidence/result_index.csv")}
    claim_ids = _claim_ids(root / "evidence/claim_registry.md")
    failures: list[str] = []
    for row in rows["specifications"]:
        if row.get("sample_id") and row["sample_id"] not in ids["samples"]: failures.append(f"spec {row.get('spec_id')} -> missing sample {row['sample_id']}")
    for row in rows["exhibits"]:
        if row.get("spec_id") and row["spec_id"] not in ids["specifications"]: failures.append(f"exhibit {row.get('exhibit_id')} -> missing spec {row['spec_id']}")
        if row.get("result_id") and row["result_id"] not in result_ids: failures.append(f"exhibit {row.get('exhibit_id')} -> missing result {row['result_id']}")
    for row in rows["sentences"]:
        if row.get("exhibit_id") and row["exhibit_id"] not in ids["exhibits"]: failures.append(f"sentence {row.get('sentence_id')} -> missing exhibit {row['exhibit_id']}")
        if row.get("result_id") and row["result_id"] not in result_ids: failures.append(f"sentence {row.get('sentence_id')} -> missing result {row['result_id']}")
        if row.get("claim_id") and row["claim_id"] not in claim_ids: failures.append(f"sentence {row.get('sentence_id')} -> missing claim {row['claim_id']}")
    return {"model": "AEROS-ECON-CHAIN-001", "status": "PASS" if not failures else "FAIL", "counts": {k: len(v) for k, v in rows.items()}, "failures": failures, "chain": "Sample -> Specification; ExhibitBinding -> (Specification, Result); SentenceBinding -> (Exhibit, Result, Claim)", "does_not_prove": ["that a Result was generated by the declared Specification unless provenance carries spec_id/sample_id", "scientific validity", "causal identification", "correct interpretation"]}


def compile_protocol(name: str, *, spec_id: str = "") -> dict[str, Any]:
    key = name.removeprefix("econ:").replace("-", "_")
    if key not in PROTOCOLS: raise ValueError(f"unknown economics protocol: {name}")
    pack = PROTOCOLS[key]
    return {"model": "AEROS-ECON-PROTOCOL-001", "protocol": f"econ:{key}", "spec_id": spec_id, "machine_diagnostics": pack["diagnostics"], "human_review": pack["human_review"], "authority": "advisory", "status": "ROUTE_READY", "does_not_prove": ["identification is valid", "the preferred specification is correct", "a claim may be upgraded"]}


def build_literature_radar(root: Path) -> dict[str, Any]:
    registry = _rows(root / "discovery/literature/paper_registry.csv")
    queues = {"read_now": [], "watch": [], "ignore_for_this_project": []}
    for row in registry:
        paper_id = row.get("paper_id") or row.get("citation_key") or row.get("title") or "unknown"
        screening = (row.get("screening_decision") or "").lower()
        used = (row.get("used_in_synthesis") or "").lower() in {"yes", "true", "1"}
        card = (row.get("extraction_card") or "").strip()
        fulltext = (row.get("full_text_available") or "").lower()
        function = " ".join((row.get("primary_function") or "", row.get("secondary_functions") or "")).lower()
        if screening in {"exclude", "excluded", "reject", "rejected"}:
            bucket, reason = "ignore_for_this_project", "screening decision excludes this paper"
        elif used and (not card or fulltext not in {"yes", "true", "indexed_fulltext"}):
            bucket, reason = "read_now", "paper is project-facing but lacks verified full-text extraction"
        elif any(token in function for token in ("closest", "method", "identification", "contradict", "measurement")) and not card:
            bucket, reason = "read_now", "high-value project function lacks extraction"
        else:
            bucket, reason = "watch", "registered candidate without a current blocking use"
        queues[bucket].append({"paper_id": paper_id, "title": row.get("title", ""), "reason": reason})
    return {"model": "AEROS-ECON-LITERATURE-RADAR-001", "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "queues": queues, "counts": {k: len(v) for k, v in queues.items()}, "authority": "advisory", "does_not_prove": ["literature completeness", "novelty", "citation support without full-text extraction"]}


def write_literature_radar(root: Path, report: dict[str, Any]) -> Path:
    path = root / "audits/literature/econ_literature_radar.json"; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); return path


def build_skill_scorecard(root: Path) -> dict[str, Any]:
    aggregate: dict[str, dict[str, float]] = {}
    for path in (root / "agent_runs/skill_invocations").glob("*.yml") if (root / "agent_runs/skill_invocations").exists() else []:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for skill in payload.get("skills_used") or []:
            row = aggregate.setdefault(str(skill), {"uses": 0, "outcomes": 0, "accepted": 0, "runtime": 0, "runtime_n": 0, "cost": 0, "cost_n": 0, "corrections": 0, "corrections_n": 0, "blockers_resolved": 0, "blockers_n": 0})
            row["uses"] += 1
            acceptance = str(payload.get("artifact_acceptance_status") or "").lower()
            if acceptance in {"accepted", "rejected"}:
                row["outcomes"] += 1; row["accepted"] += int(acceptance == "accepted")
            if "runtime_seconds" in payload: row["runtime"] += float(payload.get("runtime_seconds") or 0); row["runtime_n"] += 1
            if "cost_usd" in payload: row["cost"] += float(payload.get("cost_usd") or 0); row["cost_n"] += 1
            if "human_corrections" in payload: row["corrections"] += int(payload.get("human_corrections") or 0); row["corrections_n"] += 1
            if "blockers_resolved" in payload: row["blockers_resolved"] += int(payload.get("blockers_resolved") or 0); row["blockers_n"] += 1
    scorecards = []
    for skill, row in sorted(aggregate.items()):
        uses = int(row["uses"])
        outcomes = int(row["outcomes"])
        scorecards.append({"skill_id": skill, "uses": uses, "observed_acceptance_outcomes": outcomes, "artifact_acceptance_rate": row["accepted"] / outcomes if outcomes else None, "human_correction_rate": row["corrections"] / row["corrections_n"] if row["corrections_n"] else None, "blocker_resolution_rate": row["blockers_resolved"] / row["blockers_n"] if row["blockers_n"] else None, "average_runtime": row["runtime"] / row["runtime_n"] if row["runtime_n"] else None, "average_cost": row["cost"] / row["cost_n"] if row["cost_n"] else None})
    return {"model": "AEROS-SKILL-SCORECARD-001", "scorecards": scorecards, "selection_rule": "prefer eligible skills with higher blocker_resolution and acceptance, then lower correction/cost; no evidence means no ranking", "does_not_prove": ["skill scientific quality", "causal contribution of a skill to an outcome"]}


def compile_drive_job(job: str, *, source_candidate: str = "", target: str = "") -> dict[str, Any]:
    if job not in DRIVE_JOBS: raise ValueError(f"unknown drive job: {job}")
    row = DRIVE_JOBS[job]
    command = row["command"]
    if job == "run_specification" and source_candidate and target:
        command = (
            "python3 -m aeros.cli drive --job run_specification "
            f"--source-candidate {shlex.quote(source_candidate)} --target {shlex.quote(target)} --execute"
        )
    return {"objective_id": f"econ_job:{job}", "objective": job.replace("_", " "), "lane": row["lane"], "why": "Economics-native job selected explicitly; execution remains bounded by existing AEROS authority and promotion rules.", "command": command, "stop_condition": row["stop"], "expected_artifacts": [row["artifact"]], "can_run_without_human": True, "needs_human": False, "status_label": "ROUTE_READY", "safety": ["no automatic claim upgrade", "no automatic canonical admission", "human identification judgments remain advisory"], "source": "aeros.runtime.econ_pack.DRIVE_JOBS"}


def submission_review_ready(driver: dict[str, Any], readiness: dict[str, Any]) -> bool:
    """Mechanical eligibility for human review, never release approval."""
    return driver.get("status") == "ready" and readiness.get("recommendation") == "ready_for_human_paper_readiness_review"
