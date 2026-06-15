#!/bin/zsh
set -euo pipefail
SRC="/Users/jiamingzhang/aeros-template"
TARGETS=(
  "/Users/jiamingzhang/Desktop/cultured_meat_policy_project"
  "/Users/jiamingzhang/Desktop/cultured_meat_policy_project/validation_projects/maha_snap_waiver"
  "/Users/jiamingzhang/Desktop/aeros-template-desktop"
  "/Users/jiamingzhang/Desktop/aeros-pilot-franchise-fraud"
  "/Users/jiamingzhang/Desktop/LLM_SNAP"
)
for T in "${TARGETS[@]}"; do
  [ -f "$T/project_manifest.yml" ] || continue
  echo "==> sync framework to $T"
  mkdir -p "$T"
  rsync -a "$SRC/aeros/" "$T/aeros/"
  rsync -a "$SRC/checks/" "$T/checks/"
  rsync -a "$SRC/harness/" "$T/harness/"
  rsync -a "$SRC/examples/" "$T/examples/"
  mkdir -p "$T/agent_runs"
  rsync -a "$SRC/agent_runs/TEMPLATE_agent_run_report.md" "$T/agent_runs/TEMPLATE_agent_run_report.md"
  rsync -a "$SRC/agent_runs/TEMPLATE_critic_report.md" "$T/agent_runs/TEMPLATE_critic_report.md"
  rsync -a "$SRC/AGENTS.md" "$T/AGENTS.md"
  mkdir -p "$T/discovery/literature" "$T/execution" "$T/tasks"
  [ -f "$SRC/discovery/AGENTS.md" ] && rsync -a "$SRC/discovery/AGENTS.md" "$T/discovery/AGENTS.md"
  [ -f "$SRC/discovery/literature/AGENTS.md" ] && rsync -a "$SRC/discovery/literature/AGENTS.md" "$T/discovery/literature/AGENTS.md"
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
    Path("/Users/jiamingzhang/Desktop/LLM_SNAP"),
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

targets = [
    Path("/Users/jiamingzhang/Desktop/cultured_meat_policy_project"),
    Path("/Users/jiamingzhang/Desktop/cultured_meat_policy_project/validation_projects/maha_snap_waiver"),
    Path("/Users/jiamingzhang/Desktop/aeros-template-desktop"),
    Path("/Users/jiamingzhang/Desktop/aeros-pilot-franchise-fraud"),
    Path("/Users/jiamingzhang/Desktop/LLM_SNAP"),
]

def ensure_manifest_wiring(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    original = text
    required = "harness/improvement_backlog.yml"
    check_line = "  improvement_backlog: checks/check_improvement_backlog.py\n"
    if required not in text:
        lines = text.splitlines(keepends=True)
        inserted = False
        out = []
        for line in lines:
            out.append(line)
            if not inserted and line.lstrip().startswith("required_files:"):
                indent = line[: len(line) - len(line.lstrip())] + "  "
                out.append(f"{indent}- {required}\n")
                inserted = True
        if inserted:
            text = "".join(out)
        elif "harness:" in text:
            text = text.replace("harness:\n", f"harness:\n  required_files:\n    - {required}\n", 1)
    if "improvement_backlog: checks/check_improvement_backlog.py" not in text:
        if "checks:\n" in text:
            text = text.replace("checks:\n", "checks:\n" + check_line, 1)
        else:
            text = text.rstrip() + "\nchecks:\n" + check_line
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False

for root in targets:
    changed = ensure_manifest_wiring(root / "project_manifest.yml")
    print(f"manifest wiring {'updated' if changed else 'ok'}: {root}")
PYMANIFEST
