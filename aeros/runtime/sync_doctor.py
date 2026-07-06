"""Diagnose whether downstream projects have the latest AEROS adapter layer.

The sync doctor is advisory. It compares framework files in a project against
the template and reports missing/outdated capabilities; it does not sync files,
approve gates, or modify project state.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


CAPABILITIES: dict[str, list[str]] = {
    "improve": ["aeros/runtime/improve_harvest.py", "checks/check_improve_harvest.py"],
    "harness_observed_receipts": ["aeros/runtime/harness_receipt.py", "checks/check_harness_observed_receipts.py", "checks/run_harness_checks.py"],
    "update_ledger_hash_chain": ["aeros/runtime/ledger_hash_chain.py", "harness/update_ledger_hash_chain_policy.yml", "checks/check_update_ledger_hash_chain.py"],
    "protected_path_hook": ["harness/protected_path_commit_policy.yml", "tools/hooks/pre-commit-aeros-protected-paths", "tools/install_aeros_git_hooks.zsh", "checks/check_protected_path_hook.py"],
    "evidence_sufficiency_audit": ["harness/evidence_sufficiency_audit_policy.yml", "templates/evidence_sufficiency_audit.yml", "checks/check_evidence_sufficiency_audit.py"],
    "aea_replication_alignment": ["harness/aea_replication_policy.yml", "templates/aea_data_package_manifest.yml", "checks/check_aea_replication_alignment.py"],
    "mode": ["aeros/runtime/execution_mode.py", "aeros/runtime/task_mode.py", "aeros/runtime/mode_compiler.py", "harness/task_mode_policy.yml", "checks/check_task_mode.py"],
    "broad_capture": ["aeros/runtime/broad_capture.py", "checks/check_broad_capture_firewall.py", "harness/execution_mode_policy.yml", "harness/task_mode_policy.yml", "harness/session_scope.yml"],
    "workflow_presets": ["aeros/runtime/session_guard.py", "harness/session_scope.yml", "checks/check_session_scope.py"],
    "route_gate": ["aeros/runtime/route_gate.py", "checks/check_route_early_gate.py", "checks/check_discovery_route_decision.py"],
    "artifact_stage": ["aeros/runtime/artifact_stage.py", "checks/check_artifact_stage.py"],
    "skill_coverage": ["aeros/runtime/skill_obligation.py", "harness/skill_obligation_policy.yml", "checks/check_skill_coverage.py"],
    "output_intent": ["aeros/runtime/output_intent.py", "harness/output_intent_policy.yml", "checks/check_output_intent.py"],
    "source_capture_permission": ["aeros/runtime/source_capture_permission.py", "harness/source_capture_permission_policy.yml", "checks/check_source_capture_permission.py"],
    "task_preflight": ["aeros/runtime/task_preflight.py", "checks/check_task_preflight.py"],
    "control_tax_dashboard": ["aeros/runtime/control_tax.py", "checks/check_control_tax_dashboard.py", "aeros/runtime/cockpit.py"],
    "write_audit": ["aeros/runtime/write_audit.py", "checks/check_write_audit.py", "aeros/cli.py"],
    "submission_research_driver": ["aeros/runtime/submission_driver.py", "aeros/runtime/citation_sentence_grounding.py", "checks/check_manuscript_citation_faithfulness.py",
        "checks/check_manuscript_citation_interpretation.py", "checks/check_literature_wrapper_sync.py", "aeros/cli.py"],
    "citation_risk_radar": ["aeros/runtime/citation_radar.py", "checks/check_citation_risk_radar.py",
        "aeros/runtime/drive.py"],
    "drive": ["aeros/runtime/drive.py", "checks/check_drive.py", "aeros/cli.py"],
    "campaign_contract": ["aeros/runtime/campaign.py", "checks/check_campaign_contract.py", "templates/campaign_contract.yml", "templates/campaign_progress.csv", "aeros/cli.py"],
    "owner_decision_rules": ["aeros/runtime/owner_decisions.py", "checks/check_owner_decisions.py", "aeros/runtime/task_preflight.py"],
}

CAPABILITY_EXEMPT_CHECKS: dict[str, str] = {
    "check_action_spec.py": "contract-internal invariant; synced through aeros/runtime/action_spec.py in broader framework sync",
    "check_agent_envelope.py": "runtime sandbox/audit invariant; not a downstream sync capability selector",
    "check_architecture_freeze.py": "template design/freeze invariant",
    "check_broad_capture_firewall.py": "covered by broad_capture capability",
    "check_approval_freshness.py": "authority invariant over project-owned approvals",
    "check_action_receipts.py": "project run-record invariant",
    "check_analysis_ledger.py": "analysis record invariant over project-owned artifacts",
    "check_citation_audit.py": "literature evidence invariant over project-owned registry rows",
    "check_claim_upgrade.py": "claim compiler invariant; not used as a sync-doctor project capability",
    "check_claim_vector.py": "claim compiler invariant; not used as a sync-doctor project capability",
    "check_claim_ceiling.py": "claim-boundary invariant over project-owned claims",
    "check_claim_method_consistency.py": "claim/method invariant over project-owned claims",
    "check_claim_numbers_bound.py": "paper-number invariant over project-owned claims/paper",
    "check_claim_registry.py": "claim registry invariant over project-owned claims",
    "check_claim_toulmin_schema.py": "claim-card schema invariant",
    "check_compliance_gate.py": "release/compliance gate invariant",
    "check_cockpit.py": "operator view invariant; covered by framework sync as a whole",
    "check_context_bundle.py": "operator context invariant; covered by framework sync as a whole",
    "check_context_graph.py": "operator context invariant; covered by framework sync as a whole",
    "check_data_availability_present.py": "paper data-availability invariant",
    "check_data_backfill_queue.py": "project data queue invariant",
    "check_data_first_readiness.py": "project data-readiness invariant",
    "check_data_inventory.py": "project data inventory invariant",
    "check_data_probe.py": "project data probe invariant",
    "check_discovery_route_decision.py": "covered by route_gate capability",
    "check_estimand_cards.py": "project estimand-card invariant",
    "check_estimand_data_contract.py": "project estimand/data contract invariant",
    "check_evidence_units.py": "evidence-object invariant; not a sync-doctor capability selector",
    "check_execution_envelope.py": "execution isolation invariant; not a sync-doctor capability selector",
    "check_execution_mode.py": "covered by mode capability",
    "check_execution_profiles.py": "project manifest/execution profile invariant",
    "check_goal_mode_data_progress.py": "goal-mode project-progress invariant",
    "check_harness_profiles.py": "meta-check for profiles; not a project capability",
    "check_identification_gate.py": "identification advisory gate invariant",
    "check_literature_adapters.py": "literature adapter plumbing invariant",
    "check_literature_fulltext_execution.py": "literature full-text execution invariant",
    "check_literature_tools.py": "combined literature lane invariant",
    "check_negative_result_ledger.py": "analysis/spec ledger invariant",
    "check_next_action.py": "cockpit/next-action invariant; covered by framework sync as a whole",
    "check_noop_runs.py": "project run anti-noop invariant",
    "check_number_registry.py": "paper-number registry invariant",
    "check_number_scan.py": "paper-number advisory scan",
    "check_operating_dashboard.py": "operator dashboard invariant; covered by framework sync as a whole",
    "check_paper_package.py": "paper package invariant",
    "check_paper_readiness.py": "paper-readiness advisory compiler invariant",
    "check_parser_benchmark.py": "benchmark fixture invariant",
    "check_preanalysis_happens_before.py": "analysis event-order invariant",
    "check_progress_semantics.py": "completion/status taxonomy invariant",
    "check_provenance.py": "project provenance invariant over project-owned result/provenance artifacts",
    "check_readiness_vector.py": "derived readiness invariant",
    "check_reconcile.py": "post-run derived-index invariant",
    "check_replication_package.py": "replication package scaffold invariant",
    "check_research_graph.py": "research graph relationship invariant",
    "check_skill_coverage.py": "covered by skill_coverage capability",
    "check_source_capture_permission.py": "covered by source_capture_permission capability",
    "check_source_id_consistency.py": "source-id consistency invariant over project-owned metadata",
    "check_sqlite_journal.py": "derived journal invariant",
    "check_stale_triage.py": "stale triage invariant; covered by framework sync as a whole",
    "check_sync_doctor.py": "self-check for sync doctor",
    "check_table_cell_sources.py": "paper table-source invariant",
    "check_work_lanes.py": "lane taxonomy invariant",
}

DOES_NOT_PROVE = [
    "that a project is scientifically correct",
    "that a project should be synced now",
    "that local project customizations are safe to overwrite",
    "that gates, claims, or papers are approved",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_template_root(current_root: Path) -> Path:
    env = os.environ.get("AEROS_TEMPLATE_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if (current_root / "tools" / "sync_aeros_latest.zsh").exists():
        return current_root.resolve()
    return Path("__AEROS_TEMPLATE_ROOT_NOT_FOUND__")


def default_project_roots(root: Path) -> list[Path]:
    root = root.resolve()
    if not (root / "tools" / "sync_aeros_latest.zsh").exists() and (root / "project_manifest.yml").exists():
        return [root]
    validation = root / "validation_projects"
    if not validation.exists():
        return []
    return [path for path in sorted(validation.iterdir()) if (path / "project_manifest.yml").exists()]


def diagnose_project(template_root: Path, project_root: Path) -> dict[str, Any]:
    template_root = Path(template_root).resolve()
    project_root = Path(project_root).resolve()
    capabilities: dict[str, dict[str, Any]] = {}
    missing_capabilities: list[str] = []
    outdated_capabilities: list[str] = []
    for capability, rels in CAPABILITIES.items():
        file_rows: list[dict[str, str]] = []
        cap_missing = False
        cap_outdated = False
        for rel in rels:
            template_path = template_root / rel
            project_path = project_root / rel
            if not template_path.exists():
                status = "template_missing"
                cap_missing = True
            elif not project_path.exists():
                status = "missing"
                cap_missing = True
            else:
                status = "ok" if _sha256(template_path) == _sha256(project_path) else "outdated"
                cap_outdated = cap_outdated or status == "outdated"
            file_rows.append({"path": rel, "status": status})
        if cap_missing:
            missing_capabilities.append(capability)
        elif cap_outdated:
            outdated_capabilities.append(capability)
        capabilities[capability] = {
            "status": "missing" if cap_missing else "outdated" if cap_outdated else "ok",
            "files": file_rows,
        }
    return {
        "project": project_root.as_posix(),
        "status": "PASS" if not missing_capabilities and not outdated_capabilities else "ATTENTION",
        "missing_capabilities": missing_capabilities,
        "outdated_capabilities": outdated_capabilities,
        "capabilities": capabilities,
    }


def sync_doctor(root: Path, *, projects: list[str] | None = None, template_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root)
    tpl = Path(template_root).expanduser().resolve() if template_root else default_template_root(root)
    if not tpl.exists() or not (tpl / "tools" / "sync_aeros_latest.zsh").exists():
        return {
            "status": "ATTENTION",
            "template_root": tpl.as_posix(),
            "template_status": "template_not_found",
            "projects_checked": 0,
            "projects": [],
            "does_not_prove": DOES_NOT_PROVE,
        }
    project_roots = [Path(p).expanduser().resolve() for p in (projects or [])] or default_project_roots(root)
    rows = [diagnose_project(tpl, project) for project in project_roots if (project / "project_manifest.yml").exists()]
    missing = sum(len(row["missing_capabilities"]) for row in rows)
    outdated = sum(len(row["outdated_capabilities"]) for row in rows)
    return {
        "status": "PASS" if rows and missing == 0 and outdated == 0 else "ATTENTION",
        "template_root": tpl.as_posix(),
        "projects_checked": len(rows),
        "projects": rows,
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_sync_doctor(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Sync Doctor",
        "",
        f"status: {report.get('status')}",
        f"template_root: {report.get('template_root')}",
        f"projects_checked: {report.get('projects_checked')}",
        "",
        "projects:",
    ]
    for project in report.get("projects", []):
        lines.append(f"- project: {project.get('project')}")
        lines.append(f"  status: {project.get('status')}")
        lines.append(f"  missing_capabilities: {project.get('missing_capabilities')}")
        lines.append(f"  outdated_capabilities: {project.get('outdated_capabilities')}")
    lines.append("")
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
