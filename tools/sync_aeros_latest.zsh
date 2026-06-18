#!/bin/zsh
set -euo pipefail
SRC="/Users/jiamingzhang/aeros-template"
TARGETS=(
  "/Users/jiamingzhang/Desktop/SNAP_Store_Format_Purchasing_Power_Project"
  "/Users/jiamingzhang/Desktop/cultured_meat_policy_project"
  "/Users/jiamingzhang/Desktop/cultured_meat_policy_project/validation_projects/maha_snap_waiver"
  "/Users/jiamingzhang/Desktop/aeros-template-desktop"
  "/Users/jiamingzhang/Desktop/aeros-pilot-franchise-fraud"
  "/Users/jiamingzhang/Desktop/land-grid-farm"
  "/Users/jiamingzhang/Desktop/AI_Grocery_Recommendation_Audit"
  "/Users/jiamingzhang/Desktop/VLM_Satellite_GDP_Revision_Project"
  "/Users/jiamingzhang/Desktop/LLM_SNAP"
  "/Users/jiamingzhang/Desktop/implementation_mismatch_project"
)
for T in "${TARGETS[@]}"; do
  [ -f "$T/project_manifest.yml" ] || continue
  echo "==> sync framework to $T"
  mkdir -p "$T"
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
  if [ "$T" = "/Users/jiamingzhang/Desktop/implementation_mismatch_project" ] && [ -f "$T/AGENTS.md" ]; then
    echo "    preserving project AGENTS.md for $T"
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
done
python3 - <<'PY'
from pathlib import Path
import yaml

src = Path("/Users/jiamingzhang/aeros-template")
targets = [
    Path("/Users/jiamingzhang/Desktop/cultured_meat_policy_project"),
    Path("/Users/jiamingzhang/Desktop/cultured_meat_policy_project/validation_projects/maha_snap_waiver"),
    Path("/Users/jiamingzhang/Desktop/aeros-template-desktop"),
    Path("/Users/jiamingzhang/Desktop/aeros-pilot-franchise-fraud"),
    Path("/Users/jiamingzhang/Desktop/land-grid-farm"),
    Path("/Users/jiamingzhang/Desktop/AI_Grocery_Recommendation_Audit"),
    Path("/Users/jiamingzhang/Desktop/VLM_Satellite_GDP_Revision_Project"),
    Path("/Users/jiamingzhang/Desktop/LLM_SNAP"),
    Path("/Users/jiamingzhang/Desktop/implementation_mismatch_project"),
]
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

python3 - <<'PYMANIFEST'
from pathlib import Path
import yaml

src = Path("/Users/jiamingzhang/aeros-template")
targets = [
    Path("/Users/jiamingzhang/Desktop/SNAP_Store_Format_Purchasing_Power_Project"),
    Path("/Users/jiamingzhang/Desktop/cultured_meat_policy_project"),
    Path("/Users/jiamingzhang/Desktop/cultured_meat_policy_project/validation_projects/maha_snap_waiver"),
    Path("/Users/jiamingzhang/Desktop/aeros-template-desktop"),
    Path("/Users/jiamingzhang/Desktop/aeros-pilot-franchise-fraud"),
    Path("/Users/jiamingzhang/Desktop/land-grid-farm"),
    Path("/Users/jiamingzhang/Desktop/AI_Grocery_Recommendation_Audit"),
    Path("/Users/jiamingzhang/Desktop/VLM_Satellite_GDP_Revision_Project"),
    Path("/Users/jiamingzhang/Desktop/LLM_SNAP"),
    Path("/Users/jiamingzhang/Desktop/implementation_mismatch_project"),
]

REQUIRED_FILES = [
    "harness/improvement_backlog.yml",
    "harness/derived_vs_asserted_audit.yml",
    "harness/event_sourcing_policy.yml",
    "harness/evidence_type_lattice.yml",
    "harness/scope_calculus.yml",
    "harness/result_adapter_contract.yml",
    "harness/literature_fulltext_policy.yml",
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
    "templates/update_ledger_entry.md",
    "decisions/update_ledger.md",
    "docs/architecture_v0_5.md",
]

CHECKS = {
    "improvement_backlog": "checks/check_improvement_backlog.py",
    "literature_fulltext_execution": "checks/check_literature_fulltext_execution.py",
    "derived_vs_asserted_audit": "checks/check_derived_vs_asserted_audit.py",
    "event_log_replay": "checks/check_event_log_replay.py",
    "preanalysis_happens_before": "checks/check_preanalysis_happens_before.py",
    "data_first_readiness": "checks/check_data_first_readiness.py",
    "data_probe": "checks/check_data_probe.py",
    "global_state": "checks/check_global_state.py",
    "action_receipts": "checks/check_action_receipts.py",
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

def ensure_list_item_after(text: str, anchor: str, item: str) -> str:
    if item in text:
        return text
    marker = anchor if anchor in text else "required_files:\n"
    if marker in text:
        lines = text.splitlines(keepends=True)
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.strip() == "required_files:":
                indent = line[: len(line) - len(line.lstrip())] + "  "
                out.append(f"{indent}- {item}\n")
                inserted = True
        if inserted:
            return "".join(out)
    return text.rstrip() + f"\nrequired_files:\n  - {item}\n"

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
