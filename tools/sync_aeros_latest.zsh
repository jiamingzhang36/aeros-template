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
SCRIPT_DIR="${0:A:h}"
SRC="${AEROS_TEMPLATE_ROOT:-${SCRIPT_DIR:h}}"
export AEROS_TEMPLATE_ROOT="$SRC"
AEROS_SYNC_PYTHON="${AEROS_SYNC_PYTHON:-}"
if [ -z "$AEROS_SYNC_PYTHON" ]; then
  if [ -x "/Users/jiamingzhang/opt/anaconda3/bin/python" ]; then
    AEROS_SYNC_PYTHON="/Users/jiamingzhang/opt/anaconda3/bin/python"
  else
    AEROS_SYNC_PYTHON="python3"
  fi
fi

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
  mkdir -p "$T/docs" "$T/docs/design" "$T/templates" "$T/tests/adversarial" "$T/tests/parser" "$T/tests/evidence_units" "$T/decisions"
  if [ ! -f "$T/CURRENT_STATE.md" ]; then
    rsync -a "$SRC/templates/CURRENT_STATE.md" "$T/CURRENT_STATE.md"
  fi
  if [ ! -f "$T/CONTEXT_BUNDLE.md" ]; then
    rsync -a "$SRC/templates/CONTEXT_BUNDLE.md" "$T/CONTEXT_BUNDLE.md"
  fi
  [ -f "$SRC/docs/architecture_v0_5.md" ] && rsync -a "$SRC/docs/architecture_v0_5.md" "$T/docs/architecture_v0_5.md"
  [ -f "$SRC/docs/design/architecture_freeze_v1.md" ] && rsync -a "$SRC/docs/design/architecture_freeze_v1.md" "$T/docs/design/architecture_freeze_v1.md"
  [ -f "$SRC/docs/design/profile_ab_protocol.md" ] && rsync -a "$SRC/docs/design/profile_ab_protocol.md" "$T/docs/design/profile_ab_protocol.md"
  if [ ! -f "$T/decisions/update_ledger.md" ]; then
    [ -f "$SRC/decisions/update_ledger.md" ] && rsync -a "$SRC/decisions/update_ledger.md" "$T/decisions/update_ledger.md"
  fi
  # Do not copy the template's hash-chain into a project. The chain hashes the
  # project-local update ledger, so it must be initialized/re-anchored per
  # target by the postprocessor below.
  if [ ! -f "$T/decisions/human_gate_queue.yml" ]; then
    rsync -a "$SRC/decisions/human_gate_queue.yml" "$T/decisions/human_gate_queue.yml"
  fi
  [ -d "$SRC/templates" ] && rsync -a "$SRC/templates/" "$T/templates/"
  mkdir -p "$T/tools/hooks"
  [ -d "$SRC/tools/hooks" ] && rsync -a "$SRC/tools/hooks/" "$T/tools/hooks/"
  [ -f "$SRC/tools/install_aeros_git_hooks.zsh" ] && rsync -a "$SRC/tools/install_aeros_git_hooks.zsh" "$T/tools/install_aeros_git_hooks.zsh"
  [ -d "$SRC/tests/adversarial" ] && rsync -a "$SRC/tests/adversarial/" "$T/tests/adversarial/"
  [ -d "$SRC/tests/parser" ] && rsync -a "$SRC/tests/parser/" "$T/tests/parser/"
  [ -d "$SRC/tests/evidence_units" ] && rsync -a "$SRC/tests/evidence_units/" "$T/tests/evidence_units/"
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
  [ -f "$T/discovery/route_decision.yml" ] || rsync -a "$SRC/discovery/route_decision.yml" "$T/discovery/route_decision.yml"
  [ -f "$SRC/discovery/literature/AGENTS.md" ] && rsync -a "$SRC/discovery/literature/AGENTS.md" "$T/discovery/literature/AGENTS.md"
  mkdir -p "$T/discovery/literature/extraction_cards" "$T/discovery/literature/synthesis"
  [ -f "$SRC/discovery/literature/extraction_cards/TEMPLATE_extraction_card.md" ] && rsync -a "$SRC/discovery/literature/extraction_cards/TEMPLATE_extraction_card.md" "$T/discovery/literature/extraction_cards/TEMPLATE_extraction_card.md"
  [ -f "$SRC/discovery/literature/literature_rules.md" ] && rsync -a "$SRC/discovery/literature/literature_rules.md" "$T/discovery/literature/literature_rules.md"
  [ -f "$SRC/discovery/literature/function_taxonomy.md" ] && rsync -a "$SRC/discovery/literature/function_taxonomy.md" "$T/discovery/literature/function_taxonomy.md"
  [ -f "$T/discovery/literature/search_log.csv" ] || rsync -a "$SRC/discovery/literature/search_log.csv" "$T/discovery/literature/search_log.csv"
  [ -f "$T/discovery/literature/paper_registry.csv" ] || rsync -a "$SRC/discovery/literature/paper_registry.csv" "$T/discovery/literature/paper_registry.csv"
  [ -f "$T/discovery/literature/citation_audit.md" ] || rsync -a "$SRC/discovery/literature/citation_audit.md" "$T/discovery/literature/citation_audit.md"
  [ -f "$T/discovery/literature/citation_snowball_queue.csv" ] || rsync -a "$SRC/discovery/literature/citation_snowball_queue.csv" "$T/discovery/literature/citation_snowball_queue.csv"
  [ -f "$T/discovery/literature/fulltext_ready_queue.csv" ] || rsync -a "$SRC/discovery/literature/fulltext_ready_queue.csv" "$T/discovery/literature/fulltext_ready_queue.csv"
  [ -f "$T/discovery/literature/missing_fulltext_queue.csv" ] || rsync -a "$SRC/discovery/literature/missing_fulltext_queue.csv" "$T/discovery/literature/missing_fulltext_queue.csv"
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
"$AEROS_SYNC_PYTHON" - <<'PY'
import os
from pathlib import Path
import yaml

src = Path(os.environ["AEROS_TEMPLATE_ROOT"])
targets = [Path(p) for p in os.environ.get("AEROS_SYNC_TARGETS", "").splitlines() if p.strip()]

source_meta = {}
for path in sorted((src / "tasks").rglob("*.yml")):
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    task_id = str(data.get("task_id", "")).strip()
    if task_id:
        source_meta[task_id] = {
            "allowed_skills": list(data.get("allowed_skills") or []),
            "recommended_skills": list(data.get("recommended_skills") or []),
            "required_skill_classes": list(data.get("required_skill_classes") or []),
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
        new = replace_block(new, "required_skill_classes", meta["required_skill_classes"])
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"skill metadata updated: {root} ({changed} task file(s))")
PY

# Post-process 2: ensure each project's manifest wires the required framework
# files and checks.
"$AEROS_SYNC_PYTHON" - <<'PYMANIFEST'
import os
from pathlib import Path

src = Path(os.environ["AEROS_TEMPLATE_ROOT"])
targets = [Path(p) for p in os.environ.get("AEROS_SYNC_TARGETS", "").splitlines() if p.strip()]

REQUIRED_FILES = [
    "harness/improvement_backlog.yml",
    "harness/derived_vs_asserted_audit.yml",
    "harness/update_ledger_hash_chain_policy.yml",
    "harness/evidence_sufficiency_audit_policy.yml",
    "harness/event_sourcing_policy.yml",
    "harness/sqlite_journal_policy.yml",
    "harness/evidence_type_lattice.yml",
    "harness/scope_calculus.yml",
    "harness/result_adapter_contract.yml",
    "harness/literature_fulltext_policy.yml",
    "harness/external_tool_registry.yml",
    "harness/econ_literature_discovery_policy.yml",
    "harness/econ_method_advisory_policy.yml",
    "harness/aea_replication_policy.yml",
    "harness/completion_attestation_policy.yml",
    "harness/protected_path_commit_policy.yml",
    "harness/skill_obligation_policy.yml",
    "harness/research_profiles.yml",
    "harness/evidence_unit_policy.yml",
    "harness/claim_vector_policy.yml",
    "harness/claim_upgrade_policy.yml",
    "harness/paper_readiness_policy.yml",
    "harness/run_envelope_policy.yml",
    "harness/agent_envelope_policy.yml",
    "harness/execution_mode_policy.yml",
    "harness/task_mode_policy.yml",
    "harness/output_intent_policy.yml",
    "harness/source_capture_permission_policy.yml",
    "harness/status_label_policy.yml",
    "harness/context_budget.yml",
    "harness/context_graph_policy.yml",
    "harness/check_profiles.yml",
    "harness/stale_triage_policy.yml",
    "harness/rollout_playbook.md",
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
    "templates/evidence_unit.yml",
    "templates/result_admission.yml",
    "templates/claim_vector.yml",
    "templates/CURRENT_STATE.md",
    "templates/NEXT_ACTION.md",
    "templates/update_ledger_entry.md",
    "templates/evidence_sufficiency_audit.yml",
    "discovery/route_decision.yml",
    "decisions/update_ledger.md",
    "decisions/update_ledger_chain.jsonl",
    "decisions/human_gate_queue.yml",
    "docs/architecture_v0_5.md",
    "docs/design/architecture_freeze_v1.md",
    "tools/hooks/pre-commit-aeros-protected-paths",
    "tools/install_aeros_git_hooks.zsh",
]

CHECKS = {
    "architecture_freeze": "checks/check_architecture_freeze.py",
    "progress_semantics": "checks/check_progress_semantics.py",
    "execution_envelope": "checks/check_execution_envelope.py",
    "agent_envelope": "checks/check_agent_envelope.py",
    "evidence_units": "checks/check_evidence_units.py",
    "parser_benchmark": "checks/check_parser_benchmark.py",
    "claim_vector": "checks/check_claim_vector.py",
    "claim_upgrade": "checks/check_claim_upgrade.py",
    "operating_dashboard": "checks/check_operating_dashboard.py",
    "next_action": "checks/check_next_action.py",
    "stale_triage": "checks/check_stale_triage.py",
    "context_bundle": "checks/check_context_bundle.py",
    "harness_profiles": "checks/check_harness_profiles.py",
    "cockpit": "checks/check_cockpit.py",
    "context_graph": "checks/check_context_graph.py",
    "improvement_backlog": "checks/check_improvement_backlog.py",
    "update_ledger_hash_chain": "checks/check_update_ledger_hash_chain.py",
    "literature_fulltext_execution": "checks/check_literature_fulltext_execution.py",
    "literature_adapters": "checks/check_literature_adapters.py",
    "harness_observed_receipts": "checks/check_harness_observed_receipts.py",
    "protected_path_hook": "checks/check_protected_path_hook.py",
    "evidence_sufficiency_audit": "checks/check_evidence_sufficiency_audit.py",
    "derived_vs_asserted_audit": "checks/check_derived_vs_asserted_audit.py",
    "event_log_replay": "checks/check_event_log_replay.py",
    "sqlite_journal": "checks/check_sqlite_journal.py",
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
    "skill_coverage": "checks/check_skill_coverage.py",
    "noop_runs": "checks/check_noop_runs.py",
    "approval_integrity": "checks/check_approval_integrity.py",
    "exception_scope": "checks/check_exception_scope.py",
    "provenance_boundary": "checks/check_provenance_boundary.py",
    "analysis_ledger": "checks/check_analysis_ledger.py",
    "claim_toulmin_schema": "checks/check_claim_toulmin_schema.py",
    "identification_gate": "checks/check_identification_gate.py",
    "meta_monitor": "checks/check_meta_monitor.py",
    "paper_readiness": "checks/check_paper_readiness.py",
    "execution_mode": "checks/check_execution_mode.py",
    "task_mode": "checks/check_task_mode.py",
    "task_preflight": "checks/check_task_preflight.py",
    "source_capture_permission": "checks/check_source_capture_permission.py",
    "source_id_consistency": "checks/check_source_id_consistency.py",
    "artifact_stage": "checks/check_artifact_stage.py",
    "output_intent": "checks/check_output_intent.py",
    "route_early_gate": "checks/check_route_early_gate.py",
    "improve_harvest": "checks/check_improve_harvest.py",
    "sync_doctor": "checks/check_sync_doctor.py",
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
                for i, line in enumerate(lines):
                    out.append(line)
                    if not inserted and line.strip() == "required_files:":
                        key_indent = line[: len(line) - len(line.lstrip())]
                        # Match the EXISTING list-item indentation, not a hardcoded
                        # key+2. A manifest whose items sit at the key's own indent
                        # would otherwise get a mismatched insert and break YAML.
                        item_indent = key_indent + "  "
                        for nxt in lines[i + 1:]:
                            s = nxt.strip()
                            if not s:
                                continue
                            if s.startswith("- "):
                                item_indent = nxt[: len(nxt) - len(nxt.lstrip())]
                            break
                        out.append(f"{item_indent}- {required}\n")
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

# Post-process 3: merge route-decision scaffold fields without overwriting the
# project's current selected route / decision metadata.
"$AEROS_SYNC_PYTHON" - <<'PYROUTE'
import os
from pathlib import Path
import yaml

src = Path(os.environ["AEROS_TEMPLATE_ROOT"])
targets = [Path(p) for p in os.environ.get("AEROS_SYNC_TARGETS", "").splitlines() if p.strip()]
template_path = src / "discovery" / "route_decision.yml"
template = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}

def merge_unique(existing, incoming):
    out = []
    for item in list(existing or []) + list(incoming or []):
        if item not in out:
            out.append(item)
    return out

for root in targets:
    path = root / "discovery" / "route_decision.yml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"route decision scaffold initialized: {root}")
        continue
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    original = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    data.setdefault("version", template.get("version", "0.1"))
    data.setdefault("policy", template.get("policy", "AEROS-DISCOVERY-ROUTE-DECISION-001"))
    data["allowed_routes"] = merge_unique(data.get("allowed_routes"), template.get("allowed_routes"))
    rules = data.setdefault("route_rules", {})
    for route, rule in (template.get("route_rules") or {}).items():
        rules.setdefault(route, rule)
    hypotheses = data.setdefault("route_hypotheses", {})
    for route, hypothesis in (template.get("route_hypotheses") or {}).items():
        hypotheses.setdefault(route, hypothesis)
    data["negative_seed_keywords"] = merge_unique(data.get("negative_seed_keywords"), template.get("negative_seed_keywords"))
    data["does_not_prove"] = merge_unique(data.get("does_not_prove"), template.get("does_not_prove"))
    rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    if rendered != original:
        path.write_text(rendered, encoding="utf-8")
        print(f"route decision scaffold merged: {root}")
    else:
        print(f"route decision scaffold ok: {root}")
PYROUTE

# Post-process 4: initialize or re-anchor each project's local update-ledger
# hash chain. This must be project-specific because subject_sha256 points to the
# project's own decisions/update_ledger.md.
"$AEROS_SYNC_PYTHON" - <<'PYCHAIN'
import hashlib
import json
import os
from pathlib import Path

targets = [Path(p) for p in os.environ.get("AEROS_SYNC_TARGETS", "").splitlines() if p.strip()]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_hash(record: dict) -> str:
    payload = {k: v for k, v in record.items() if k != "entry_hash"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            records.append(json.loads(raw))
    return records

def append_record(root: Path, entry_id: str, scope: list[str], reason: str) -> bool:
    ledger = root / "decisions" / "update_ledger.md"
    if not ledger.exists():
        return False
    chain = root / "decisions" / "update_ledger_chain.jsonl"
    records = load_records(chain)
    current_hash = sha256_file(ledger)
    if records and records[-1].get("subject") == "decisions/update_ledger.md" and records[-1].get("subject_sha256") == current_hash:
        return False
    prev_hash = records[-1].get("entry_hash") if records else "GENESIS"
    record = {
        "version": 1,
        "seq": len(records) + 1,
        "entry_id": entry_id,
        "subject": "decisions/update_ledger.md",
        "subject_sha256": current_hash,
        "prev_hash": prev_hash,
        "payload": {
            "commit_refs": ["sync-local"],
            "scope": scope,
            "verification_strength": "local_hash_chain_over_observed_subject_file",
            "reason": reason,
            "does_not_prove": [
                "scientific validity",
                "claim support",
                "gate approval",
                "external transparency",
                "malicious actor cannot rewrite both ledger and chain",
            ],
        },
    }
    record["entry_hash"] = canonical_hash(record)
    chain.parent.mkdir(parents=True, exist_ok=True)
    with chain.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return True

for root in targets:
    changed = append_record(
        root,
        "sync-local-update-ledger-chain-anchor",
        ["project_specific_update_ledger_chain_anchor"],
        "sync initialized or re-anchored the project-local ledger chain after framework rollout",
    )
    print(f"ledger chain {'anchored' if changed else 'ok'}: {root}")
PYCHAIN
