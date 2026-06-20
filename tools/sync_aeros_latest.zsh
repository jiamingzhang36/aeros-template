#!/bin/zsh
# Sync the AEROS framework from this template into one or more project copies.
#
# Usage:
#   tools/sync_aeros_latest.zsh <project_path> [<project_path> ...]
#
# Forward-only and non-destructive: uses `rsync -a` WITHOUT `--delete`, so it
# updates framework files and preserves project-owned files that live alongside
# them (e.g. aeros/project_contract.yml, aeros/task_registry.csv, aeros/state/).
#
# There is intentionally NO hardcoded project list — pass the project(s) you want
# to sync. This works for any current or future project. Each target must contain
# project_manifest.yml (targets without it are skipped with a warning).
#
# To keep a project's customized AGENTS.md across syncs, drop an empty marker file
# named `.aeros_sync_keep_agents` in that project's root.
set -euo pipefail
SRC="/Users/jiamingzhang/aeros-template"

if [ "$#" -eq 0 ]; then
  print -u2 "usage: tools/sync_aeros_latest.zsh <project_path> [<project_path> ...]"
  print -u2 "  Syncs the AEROS framework from $SRC into each given project."
  print -u2 "  Forward-only, non-destructive. Each project needs project_manifest.yml."
  print -u2 "  Keep a project's own AGENTS.md by placing .aeros_sync_keep_agents in its root."
  exit 2
fi

typeset -a TARGETS SYNCED
TARGETS=("$@")
SYNCED=()

for T in "${TARGETS[@]}"; do
  if [ ! -f "$T/project_manifest.yml" ]; then
    print -u2 "!! skip (no project_manifest.yml): $T"
    continue
  fi
  echo "==> sync framework to $T"
  rsync -a "$SRC/aeros/" "$T/aeros/"
  rsync -a "$SRC/checks/" "$T/checks/"
  rsync -a "$SRC/harness/" "$T/harness/"
  rsync -a "$SRC/examples/" "$T/examples/"
  mkdir -p "$T/docs" "$T/templates" "$T/tests/adversarial" "$T/decisions"
  [ -f "$SRC/docs/architecture_v0_5.md" ] && rsync -a "$SRC/docs/architecture_v0_5.md" "$T/docs/architecture_v0_5.md"
  [ -f "$SRC/decisions/update_ledger.md" ] && rsync -a "$SRC/decisions/update_ledger.md" "$T/decisions/update_ledger.md"
  [ -d "$SRC/templates" ] && rsync -a "$SRC/templates/" "$T/templates/"
  [ -d "$SRC/tests/adversarial" ] && rsync -a "$SRC/tests/adversarial/" "$T/tests/adversarial/"
  mkdir -p "$T/agent_runs"
  rsync -a "$SRC/agent_runs/TEMPLATE_agent_run_report.md" "$T/agent_runs/TEMPLATE_agent_run_report.md"
  rsync -a "$SRC/agent_runs/TEMPLATE_critic_report.md" "$T/agent_runs/TEMPLATE_critic_report.md"
  if [ -f "$T/.aeros_sync_keep_agents" ]; then
    echo "    preserving project AGENTS.md (.aeros_sync_keep_agents present)"
  else
    rsync -a "$SRC/AGENTS.md" "$T/AGENTS.md"
  fi
  mkdir -p "$T/discovery/literature" "$T/execution" "$T/tasks"
  [ -f "$SRC/discovery/AGENTS.md" ] && rsync -a "$SRC/discovery/AGENTS.md" "$T/discovery/AGENTS.md"
  [ -f "$SRC/discovery/literature/AGENTS.md" ] && rsync -a "$SRC/discovery/literature/AGENTS.md" "$T/discovery/literature/AGENTS.md"
  mkdir -p "$T/discovery/literature/extraction_cards" "$T/discovery/literature/synthesis"
  [ -f "$SRC/discovery/literature/extraction_cards/TEMPLATE_extraction_card.md" ] && rsync -a "$SRC/discovery/literature/extraction_cards/TEMPLATE_extraction_card.md" "$T/discovery/literature/extraction_cards/TEMPLATE_extraction_card.md"
  [ -f "$SRC/discovery/literature/literature_rules.md" ] && rsync -a "$SRC/discovery/literature/literature_rules.md" "$T/discovery/literature/literature_rules.md"
  [ -f "$SRC/discovery/literature/function_taxonomy.md" ] && rsync -a "$SRC/discovery/literature/function_taxonomy.md" "$T/discovery/literature/function_taxonomy.md"
  [ -f "$SRC/execution/AGENTS.md" ] && rsync -a "$SRC/execution/AGENTS.md" "$T/execution/AGENTS.md"
  [ -f "$SRC/tasks/TEMPLATE_task.md" ] && rsync -a "$SRC/tasks/TEMPLATE_task.md" "$T/tasks/TEMPLATE_task.md"
  SYNCED+=("$T")
done

if [ "${#SYNCED[@]}" -eq 0 ]; then
  print -u2 "no valid targets synced."
  exit 1
fi

# Hand the resolved targets to the python post-processors (newline-joined).
export AEROS_SYNC_TARGETS="${(F)SYNCED}"

# Post-process 1: propagate task skill metadata (allowed/recommended skills) from
# the template's task contracts into each project's matching task_id files.
python3 - <<'PY'
import os
from pathlib import Path
import yaml

src = Path("/Users/jiamingzhang/aeros-template")
targets = [Path(p) for p in os.environ.get("AEROS_SYNC_TARGETS", "").splitlines() if p.strip()]

source_meta = {}
for path in sorted((src / "tasks").rglob("*.yml")):
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    task_id = str(data.get("task_id", "")).strip()
    if task_id:
        source_meta[task_id] = {
            "allowed_skills": list(data.get("allowed_skills") or []),
            "recommended_skills": list(data.get("recommended_skills") or []),
        }

def block(key, skills):
    if not skills:
        return f"{key}: []\n"
    return key + ":\n" + "".join(f"- {s}\n" for s in skills)

def replace_block(text, key, skills):
    lines = text.splitlines(keepends=True)
    out = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        if line.startswith(key + ":"):
            out.append(block(key, skills))
            i += 1
            while i < len(lines) and lines[i].startswith("- "):
                i += 1
            replaced = True
            continue
        out.append(line)
        i += 1
    if replaced:
        return "".join(out)
    lines = "".join(out).splitlines(keepends=True)
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("gate_status:"):
            out.append(block(key, skills))
            inserted = True
    return "".join(out) if inserted else "".join(out).rstrip() + "\n" + block(key, skills)

for root in targets:
    task_dir = root / "tasks"
    if not task_dir.exists():
        continue
    changed = 0
    for path in sorted(task_dir.rglob("*.yml")):
        text = path.read_text(encoding="utf-8")
        task_id = ""
        for line in text.splitlines():
            if line.startswith("task_id:"):
                task_id = line.split(":", 1)[1].strip().strip("\"'")
                break
        meta = source_meta.get(task_id)
        if not meta:
            continue
        new = replace_block(text, "allowed_skills", meta["allowed_skills"])
        new = replace_block(new, "recommended_skills", meta["recommended_skills"])
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"skill metadata updated: {root} ({changed} task file(s))")
PY

# Post-process 2: ensure each project's manifest wires the required framework
# files and checks.
python3 - <<'PYMANIFEST'
import os
from pathlib import Path

src = Path("/Users/jiamingzhang/aeros-template")
targets = [Path(p) for p in os.environ.get("AEROS_SYNC_TARGETS", "").splitlines() if p.strip()]

REQUIRED_FILES = [
    "harness/improvement_backlog.yml",
    "harness/derived_vs_asserted_audit.yml",
    "harness/event_sourcing_policy.yml",
    "harness/evidence_type_lattice.yml",
    "harness/scope_calculus.yml",
    "harness/result_adapter_contract.yml",
    "harness/literature_fulltext_policy.yml",
    "harness/external_tool_registry.yml",
    "harness/econ_literature_discovery_policy.yml",
    "harness/aea_replication_policy.yml",
    "harness/completion_attestation_policy.yml",
    "harness/goal_mode_policy.yml",
    "harness/work_lane_policy.yml",
    "harness/admissibility_matrix.yml",
    "harness/analysis_integrity.yml",
    "harness/claim_toulmin_schema.yml",
    "harness/invariants.yml",
    "harness/state_transition.yml",
    "harness/source_type_matrix.yml",
    "harness/probe_failure_taxonomy.yml",
    "harness/provenance_boundary.yml",
    "templates/preanalysis_plan.yml",
    "templates/spec_space.yml",
    "templates/spec_run_index.csv",
    "templates/claim_card.yml",
    "templates/analytic_deviation.yml",
    "templates/identification_gate.yml",
    "templates/estimand_card.yml",
    "templates/negative_result_ledger.csv",
    "templates/source_card.yml",
    "templates/result_registry_record.json",
    "templates/aea_data_package_manifest.yml",
    "templates/evidence_delta_record.json",
    "templates/completion_attestation.yml",
    "templates/update_ledger_entry.md",
    "decisions/update_ledger.md",
    "docs/architecture_v0_5.md",
]

CHECKS = {
    "improvement_backlog": "checks/check_improvement_backlog.py",
    "literature_fulltext_execution": "checks/check_literature_fulltext_execution.py",
    "derived_vs_asserted_audit": "checks/check_derived_vs_asserted_audit.py",
    "event_log_replay": "checks/check_event_log_replay.py",
    "evidence_delta_log": "checks/check_evidence_delta_log.py",
    "preanalysis_happens_before": "checks/check_preanalysis_happens_before.py",
    "external_tool_registry": "checks/check_external_tool_registry.py",
    "aea_replication_alignment": "checks/check_aea_replication_alignment.py",
    "data_first_readiness": "checks/check_data_first_readiness.py",
    "data_probe": "checks/check_data_probe.py",
    "global_state": "checks/check_global_state.py",
    "action_receipts": "checks/check_action_receipts.py",
    "goal_mode_data_progress": "checks/check_goal_mode_data_progress.py",
    "work_lanes": "checks/check_work_lanes.py",
    "noop_runs": "checks/check_noop_runs.py",
    "exception_scope": "checks/check_exception_scope.py",
    "provenance_boundary": "checks/check_provenance_boundary.py",
    "analysis_ledger": "checks/check_analysis_ledger.py",
    "claim_toulmin_schema": "checks/check_claim_toulmin_schema.py",
    "identification_gate": "checks/check_identification_gate.py",
    "meta_monitor": "checks/check_meta_monitor.py",
    "artifact_admissibility": "checks/check_artifact_admissibility.py",
    "estimand_cards": "checks/check_estimand_cards.py",
    "negative_result_ledger": "checks/check_negative_result_ledger.py",
}

def ensure_manifest_wiring(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    original = text
    for required in REQUIRED_FILES:
        if required not in text:
            if "required_files:" in text:
                lines = text.splitlines(keepends=True)
                out = []
                inserted = False
                for line in lines:
                    out.append(line)
                    if not inserted and line.strip() == "required_files:":
                        indent = line[: len(line) - len(line.lstrip())] + "  "
                        out.append(f"{indent}- {required}\n")
                        inserted = True
                text = "".join(out)
            elif "checks:" in text:
                text = text.replace("checks:\n", f"required_files:\n  - {required}\nchecks:\n", 1)
            else:
                text = text.rstrip() + f"\nrequired_files:\n  - {required}\n"
    if "checks:\n" not in text:
        text = text.rstrip() + "\nchecks:\n"
    for key, value in CHECKS.items():
        if f"{key}:" not in text:
            text = text.replace("checks:\n", f"checks:\n  {key}: {value}\n", 1)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False

for root in targets:
    changed = ensure_manifest_wiring(root / "project_manifest.yml")
    print(f"manifest wiring {'updated' if changed else 'ok'}: {root}")
PYMANIFEST
