#!/usr/bin/env python3
"""Exercise the AEROS drive usefulness entrypoint."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    proc = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "drive", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        failures.append("aeros drive --json exited nonzero: " + (proc.stderr or proc.stdout)[-1000:])
    else:
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"aeros drive --json emitted invalid JSON: {exc}")
            report = {}
        objective = report.get("chosen_objective") or {}
        for key in ["objective_id", "objective", "lane", "why", "command", "stop_condition", "status_label"]:
            if not objective.get(key):
                failures.append(f"drive objective missing {key}")
        if report.get("model") != "AEROS-USEFUL-001-drive-mvp":
            failures.append("drive report does not declare AEROS-USEFUL-001 model")
        if "project_signals" not in report or "broad_capture" not in (report.get("project_signals") or {}):
            failures.append("drive report must include broad_capture project signal")
        risk = report.get("research_risk") or {}
        if risk.get("model") != "AEROS-RESEARCH-RISK-002":
            failures.append("drive report must include AEROS-RESEARCH-RISK-002 research_risk projection")
        if not isinstance(risk.get("risk_vector"), dict):
            failures.append("drive report must include research risk vector")
        if "data/processed/" not in (report.get("what_this_does_not_touch") or []):
            failures.append("drive report must state protected data/processed boundary")
        if not report.get("does_not_prove"):
            failures.append("drive report must include does_not_prove boundaries")
        preflight = ((report.get("project_signals") or {}).get("preflight") or {})
        if objective.get("objective_id") == "broad_capture" and preflight.get("task_mode") != "broad_capture":
            failures.append("drive broad_capture objective must use broad_capture preflight")

    proc2 = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "drive", "--goal", "citation-risk", "--execute", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc2.returncode != 0:
        failures.append("aeros drive citation-risk --execute failed: " + (proc2.stderr or proc2.stdout)[-1000:])
    else:
        payload = json.loads(proc2.stdout)
        execution = payload.get("execution") or {}
        if execution.get("attempted") is not True:
            failures.append("drive citation-risk --execute should run the read-only citation check")
        if execution.get("status") not in {"pass", "blocked_found"}:
            failures.append("drive citation-risk execution should pass or surface a blocker")

    fixture_code = r"""
from pathlib import Path
import json, sys, tempfile
sys.path.insert(0, str(Path.cwd()))
from aeros.runtime.drive import build_drive_report
with tempfile.TemporaryDirectory(prefix='aeros_drive_risk_') as raw:
    root = Path(raw)
    (root/'tex').mkdir(parents=True)
    (root/'harness').mkdir(parents=True)
    (root/'discovery/literature').mkdir(parents=True)
    (root/'harness/citation_function_requirements.yml').write_text((Path.cwd()/'harness/citation_function_requirements.yml').read_text(), encoding='utf-8')
    (root/'tex/paper.tex').write_text(r'We find a significant result \citep{p2025}.', encoding='utf-8')
    (root/'discovery/literature/paper_registry.csv').write_text('paper_id,citation_key,title,full_text_available,extraction_card\nP001,p2025,Paper,abstract_only,\n', encoding='utf-8')
    report = build_drive_report(root)
    print(json.dumps(report))
"""
    proc3 = subprocess.run(
        [sys.executable, "-c", fixture_code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc3.returncode != 0:
        failures.append("drive risk fixture failed: " + (proc3.stderr or proc3.stdout)[-1000:])
    else:
        payload = json.loads(proc3.stdout)
        objective = payload.get("chosen_objective") or {}
        risk = payload.get("research_risk") or {}
        if objective.get("objective_id") != "submission_truth_risk":
            failures.append(f"citation debt should outrank mechanical fallback, got {objective.get('objective_id')}")
        if (risk.get("top_risk") or {}).get("risk_id") != "submission_truth_risk":
            failures.append("research risk fixture did not rank submission_truth_risk first")

    candidate_fixture = r"""
from pathlib import Path
import json, sys, tempfile
sys.path.insert(0, str(Path.cwd()))
from aeros.runtime.drive import build_drive_report
with tempfile.TemporaryDirectory(prefix='aeros_drive_candidates_') as raw:
    root = Path(raw)
    backfill = root/'data/backfill'
    backfill.mkdir(parents=True)
    rows = [f'C{i:03d},L{i:03d},https://example.test/{i}' for i in range(1, 21)]
    (backfill/'ready_candidate_queue.csv').write_text(
        'candidate_id,lead_id,source_url\n' + '\n'.join(rows) + '\n', encoding='utf-8'
    )
    print(json.dumps(build_drive_report(root)))
"""
    proc4 = subprocess.run(
        [sys.executable, "-c", candidate_fixture],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc4.returncode != 0:
        failures.append("drive candidate-pool fixture failed: " + (proc4.stderr or proc4.stdout)[-1000:])
    else:
        payload = json.loads(proc4.stdout)
        objective = payload.get("chosen_objective") or {}
        broad = (payload.get("project_signals") or {}).get("broad_capture") or {}
        if objective.get("objective_id") != "capture_efficiency_risk":
            failures.append(f"sufficient candidate pool should surface capture_efficiency_risk, got {objective.get('objective_id')}")
        if "triage" not in str(objective.get("command") or "") or "broad search" in str(objective.get("command") or ""):
            failures.append("sufficient candidate pool must route to candidate triage rather than another broad search")
        if broad.get("lead_to_candidate_rate") is not None:
            failures.append("drive exposed an inflated zero-lead conversion rate")
        if not broad.get("candidate_backlog_ready") or not broad.get("broad_capture_pause_recommended"):
            failures.append("drive did not expose the downgraded candidate-backlog/pause semantics")

    if failures:
        print("FAIL: drive entrypoint problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: drive entrypoint is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
