"""AEROS Drive: daily usefulness entrypoint.

Drive is a product-layer aggregator, not a new authority layer. It chooses one
useful next objective from existing deterministic signals, optionally executes
only safe/read-only previews, and reports what it did, what it did not touch,
and when human authority is needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shlex
import subprocess
from typing import Any

from .broad_capture import summarize_broad_capture
from .citation_radar import build_citation_radar
from .citation_sentence_grounding import build_sentence_citation_grounding
from .current_work import load_current_work_context, preferred_lane
from .next_action import NextAction, compute_next_action
from .research_risk import compile_research_risk
from .submission_driver import build_submission_driver
from .task_preflight import build_task_preflight


DOES_NOT_PROVE = [
    "that the chosen objective is scientifically optimal",
    "that a lead/candidate is evidence",
    "that claim, paper, gate, or release authority is granted",
    "that external provider/API work was performed",
    "that user-perceived usefulness improved without rollout metrics",
]

SAFE_EXECUTION_PREFIXES = (
    ("python3", "checks/"),
    ("python", "checks/"),
    ("python3", "-m", "aeros.cli"),
    ("python", "-m", "aeros.cli"),
)

SAFE_AEROS_COMMAND_MARKERS = (
    "--dry-run",
    " literature status",
    " task preflight",
    " mode recommend",
    " inspect modes",
    " next",
    " data plan",
    " data probe plan",
    " data probe census",
    " data probe official",
    " econ ",
)


@dataclass(frozen=True)
class DriveObjective:
    objective_id: str
    objective: str
    lane: str
    why: str
    command: str
    stop_condition: str
    expected_artifacts: tuple[str, ...]
    can_run_without_human: bool
    needs_human: bool
    status_label: str
    safety: tuple[str, ...]
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "objective": self.objective,
            "lane": self.lane,
            "why": self.why,
            "command": self.command,
            "stop_condition": self.stop_condition,
            "expected_artifacts": list(self.expected_artifacts),
            "can_run_without_human": self.can_run_without_human,
            "needs_human": self.needs_human,
            "status_label": self.status_label,
            "safety": list(self.safety),
            "source": self.source,
        }


def _objective_from_risk(risk: dict[str, Any]) -> DriveObjective:
    return DriveObjective(
        objective_id=str(risk.get("risk_id") or "research_risk"),
        objective=str(risk.get("recommended_action") or "Resolve top research risk."),
        lane=str(risk.get("lane") or "project"),
        why=str(risk.get("why") or "A deterministic research-risk compiler ranked this as the highest current risk."),
        command=str(risk.get("command") or "python3 -m aeros.cli next --json"),
        stop_condition=str(risk.get("stop_condition") or "Stop after the risk is represented as an actionable queue item or explicit human decision."),
        expected_artifacts=tuple(str(item) for item in (risk.get("expected_artifacts") or ())),
        can_run_without_human=bool(risk.get("can_run_without_human", True)),
        needs_human=bool(risk.get("needs_human", False)),
        status_label=str(risk.get("status_label") or "ROUTE_READY"),
        safety=(
            "research-risk ranked advisory; does not approve gates or upgrade claims",
            "recommended command is read-only or preflight-style unless explicitly reviewed",
        ),
        source=str(risk.get("source") or "aeros.runtime.research_risk"),
    )


def _objective_from_next(action: NextAction) -> DriveObjective:
    spec = (action.action_spec or {}) if hasattr(action, "action_spec") else {}
    effect = str(spec.get("effect_class") or "")
    safe = bool("--dry-run" in action.command or effect == "read_only" or action.command.startswith("python3 checks/"))
    return DriveObjective(
        objective_id="next_action",
        objective=action.recommended_next_action,
        lane=action.lane,
        why=action.why_this_next,
        command=action.command,
        stop_condition=action.stop_condition,
        expected_artifacts=tuple(spec.get("expected_outputs") or ()),
        can_run_without_human=safe and not action.blocked,
        needs_human=bool(action.blocked),
        status_label=action.status_label,
        safety=(
            "uses existing deterministic next-action projection",
            "does not approve gates or upgrade claims",
        ),
        source=action.source,
    )


def _objective_from_current_work(context: dict[str, Any]) -> DriveObjective:
    priorities = [str(item).strip() for item in (context.get("priority_order") or []) if str(item).strip()]
    priority = priorities[0]
    lane = str(context.get("active_lane") or "").strip().lower()
    if lane not in {"data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"}:
        lane = "analysis"
    goal = str(context.get("active_goal") or "").strip()
    source_path = str(context.get("source_path") or "CURRENT_WORK.yml")
    return DriveObjective(
        objective_id="current_work_priority",
        objective=priority,
        lane=lane,
        why=(
            "No higher-priority research risk is active, so AEROS selected the first "
            f"operator-declared current-work priority. Active goal: {goal or '<not declared>'}."
        ),
        command=(
            "python3 -m aeros.cli task preflight "
            f"--lane {shlex.quote(lane)} --intent {shlex.quote(priority)} --json"
        ),
        stop_condition=(
            "Stop after preflight reports allowed writes, skill obligations, and any human decision; "
            "drive does not execute the research action."
        ),
        expected_artifacts=(),
        can_run_without_human=True,
        needs_human=False,
        status_label="ROUTE_READY",
        safety=(
            "operator-declared priority is advisory routing context, not scientific authority",
            "preflight only; does not edit research artifacts, approve gates, or upgrade claims",
        ),
        source=f"{source_path}#priority_order[0]",
    )


def _goal_objective(root: Path, goal: str, lane: str) -> DriveObjective:
    if goal in {"capture", "broad-capture", "broad_capture"}:
        summary = summarize_broad_capture(root)
        return DriveObjective(
            objective_id="broad_capture",
            objective="Build or triage a broad-capture lead pool.",
            lane="data",
            why=(
                f"Broad capture is the low-governance path for early source discovery. "
                f"Current leads={summary.get('total_leads')}, candidates={summary.get('total_candidates')}, "
                f"duplicates={summary.get('duplicate_lead_count')}, stale={summary.get('stale_lead_count')}."
            ),
            command='python3 -m aeros.cli task preflight --lane data --intent "broad search lead sweep" --json',
            stop_condition="Stop after the preflight confirms lead/candidate-only surfaces; actual capture must write only lead_queue/candidate_queue/broad_capture audit artifacts.",
            expected_artifacts=(
                "data/backfill/*_lead_queue.csv",
                "data/backfill/*_candidate_queue.csv",
                "audits/broad_capture/**",
            ),
            can_run_without_human=True,
            needs_human=False,
            status_label="CAPTURE_LOGGED",
            safety=(
                "must not touch data/raw, data/intermediate, data/processed, paper, or evidence/claim_registry.md",
                "capture outputs are not evidence and are not claim-supporting",
            ),
            source="aeros.runtime.broad_capture.summarize_broad_capture",
        )
    if goal in {"promote", "source-promotion", "source_promotion"}:
        return DriveObjective(
            objective_id="source_promotion",
            objective="Promote reviewed candidates only after source identity and admissibility checks.",
            lane="data",
            why="Promotion is where broad-capture work becomes expensive: candidates may become staging/canonical candidates only after checks.",
            command="python3 -m aeros.cli artifact stage --canonical --exclude-raw-staging",
            stop_condition="Stop after canonical candidates are listed; require human approval before claim/paper/release-facing use.",
            expected_artifacts=("audits/source_recapture/**", "source_snapshots/**", "data/backfill/*_candidate_queue.csv"),
            can_run_without_human=False,
            needs_human=True,
            status_label="ROUTE_READY",
            safety=("does not admit evidence by itself", "does not update claim_registry or paper"),
            source="manual_goal:source_promotion",
        )
    if goal in {"literature", "fulltext", "full-text"}:
        action = compute_next_action(root, lane="literature")
        return _objective_from_next(action)
    if goal in {"citation-risk", "citation_risk", "submission"}:
        radar = build_citation_radar(root, top=12)
        grounding = build_sentence_citation_grounding(root)
        debt_count = int((grounding.get("counts") or {}).get("citation_debt_rows") or 0)
        blocking_count = int((grounding.get("counts") or {}).get("blocking_rows") or 0)
        if radar.active:
            why = (
                f"{radar.claim_bearing_at_risk} claim-bearing citation(s), "
                f"{radar.unknown} cited source(s) outside the evidence base, and "
                f"{debt_count} sentence-level citation debt row(s) are the top submission risk in "
                f"{radar.manuscript}; grounding them outranks mechanical revalidation."
            )
            status = "RISKS_FOUND" if (radar.unknown or radar.ungrounded or debt_count) else "CLEAN"
        else:
            why = (
                "Submission-stage usefulness is highest when cited manuscript sentences are checked "
                f"against function-specific evidence requirements ({radar.reason}); current citation debt rows={debt_count}."
            )
            status = "RISKS_FOUND" if blocking_count else "INACTIVE"
        return DriveObjective(
            objective_id="citation_risk",
            objective="Run manuscript citation risk and sentence-level citation-function grounding.",
            lane="writing",
            why=why,
            command="python3 checks/check_manuscript_citation_faithfulness.py",
            stop_condition="Stop after citation debt rows are visible; acting on findings (full-text recovery, extraction, interpretation, or claim edits) needs human review.",
            expected_artifacts=("audits/citation_radar/citation_risk_radar.json", "audits/citation_debt_report.csv"),
            can_run_without_human=True,
            needs_human=False,
            status_label=status,
            safety=("read-only/function-grounding advisory", "does not certify scientific truth, edit the paper, or approve gates"),
            source="aeros.runtime.citation_radar+aeros.runtime.citation_sentence_grounding",
        )
    if goal in {"data-probe", "data_probe", "probe"}:
        return DriveObjective(
            objective_id="data_probe",
            objective="Plan the smallest data probe before full collection or analysis.",
            lane="data",
            why="AEROS should test access, parseability, coverage, and join keys on a small sample before full backfill.",
            command="python3 -m aeros.cli data probe plan --dry-run",
            stop_condition="Stop after candidate probes and approval requirements are visible; do not treat probe planning as evidence.",
            expected_artifacts=("audits/data_probe_report.md",),
            can_run_without_human=True,
            needs_human=False,
            status_label="ROUTE_READY",
            safety=("dry-run only", "does not write canonical data or claims"),
            source="manual_goal:data_probe",
        )
    action = compute_next_action(root, lane=lane or "")
    return _objective_from_next(action)


def _auto_objective(root: Path, lane: str) -> DriveObjective:
    risk_report = compile_research_risk(root, lane=lane)
    top_risk = risk_report.get("top_risk")
    if isinstance(top_risk, dict) and int(top_risk.get("score") or 0) > 0:
        return _objective_from_risk(top_risk)

    current_work = load_current_work_context(root)
    if not lane and current_work.get("status") == "active" and current_work.get("priority_order"):
        return _objective_from_current_work(current_work)

    context_lane = preferred_lane(root, fallback="")
    if not lane and context_lane:
        return _objective_from_next(compute_next_action(root, lane=context_lane))

    broad = summarize_broad_capture(root)
    total_leads = int(broad.get("total_leads") or 0)
    if lane in {"", "data"} and broad.get("capture_saturation_stop"):
        return _goal_objective(root, "promote", lane)
    if lane in {"", "data"} and total_leads == 0:
        return _goal_objective(root, "capture", lane)

    action = compute_next_action(root, lane=lane or "")
    return _objective_from_next(action)


def _preflight_intent(objective: DriveObjective) -> str:
    mapping = {
        "broad_capture": "broad search lead sweep",
        "source_promotion": "promote reviewed source candidates",
        "citation_risk": "citation risk audit",
        "data_probe": "data probe plan",
        "econ_job:probe_data": "bounded official public economic-data nonproduction probe into data/probes and provenance",
    }
    return mapping.get(objective.objective_id, objective.objective)


def _is_safe_to_execute(command: str) -> bool:
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    if len(args) < 2:
        return False
    if tuple(args[:2]) in {("python3", "checks/"), ("python", "checks/")}:  # defensive; normally not reached
        return True
    if args[0] in {"python3", "python"} and len(args) >= 2 and args[1].startswith("checks/"):
        return True
    if args[:3] in (["python3", "-m", "aeros.cli"], ["python", "-m", "aeros.cli"]):
        normalized = " " + " ".join(args[3:])
        return any(marker in normalized or marker in command for marker in SAFE_AEROS_COMMAND_MARKERS)
    return False


def _surfaces_blocker(command: str) -> bool:
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    joined = " ".join(args)
    return any(marker in joined for marker in (
        "check_manuscript_citation_faithfulness.py",
        "check_manuscript_citation_interpretation.py",
        "check_literature_wrapper_sync.py",
    ))


def _run_safe_command(root: Path, command: str) -> dict[str, Any]:
    if not _is_safe_to_execute(command):
        return {
            "attempted": False,
            "status": "refused",
            "reason": "command is not in the drive safe-execution allowlist",
            "command": command,
        }
    args = shlex.split(command)
    proc = subprocess.run(args, cwd=root, text=True, capture_output=True, timeout=60)
    status = "pass" if proc.returncode == 0 else "fail"
    if proc.returncode != 0 and _surfaces_blocker(command):
        status = "blocked_found"
    return {
        "attempted": True,
        "status": status,
        "blocked_found": proc.returncode != 0 and _surfaces_blocker(command),
        "exit_code": proc.returncode,
        "command": command,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def _run_official_probe_envelope(root: Path) -> dict[str, Any]:
    from .economic_probe import compile_official_probe_action
    from .execution_envelope import execute_action_spec_in_isolated_worktree
    try:
        spec = compile_official_probe_action(root)
        result = execute_action_spec_in_isolated_worktree(root, spec, timeout_seconds=60)
    except Exception as exc:
        return {"attempted": False, "status": "fail", "reason": str(exc), "command": "compiled official probe"}
    return {
        "attempted": True,
        "status": "pass" if result.ok else "fail",
        "exit_code": result.return_code,
        "command": spec.command,
        "action_spec": spec.to_dict(),
        "observed_writes": list(result.observed_writes),
        "accepted_outputs": list(result.accepted_outputs),
        "denied_writes": list(result.denied_writes),
        "undeclared_writes": list(result.undeclared_writes),
        "missing_expected_outputs": list(result.missing_expected_outputs),
        "worktree_removed": result.worktree_removed,
        "reason": result.message,
    }


def build_drive_report(root: Path | str = Path.cwd(), *, goal: str = "auto", lane: str = "", execute: bool = False, job: str = "") -> dict[str, Any]:
    root = Path(root)
    goal = (goal or "auto").strip().lower()
    lane = (lane or "").strip()
    if job:
        from .econ_pack import compile_drive_job
        objective = DriveObjective(**compile_drive_job(job))
    else:
        objective = _auto_objective(root, lane) if goal == "auto" else _goal_objective(root, goal, lane)
    preflight = build_task_preflight(root, lane=objective.lane if objective.lane in {"data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"} else lane, intent=_preflight_intent(objective))
    broad_summary = summarize_broad_capture(root)
    source_permission = preflight.get("source_capture_permission") or {}
    probe_permission_ok = objective.objective_id != "econ_job:probe_data" or bool(source_permission.get("allowed_without_human_approval"))
    may_execute = execute and objective.can_run_without_human and not objective.needs_human and not preflight.get("needs_human_decision") and probe_permission_ok
    execution = (_run_official_probe_envelope(root) if objective.objective_id == "econ_job:probe_data" else _run_safe_command(root, objective.command)) if may_execute else {
        "attempted": False,
        "status": "not_requested" if not execute else "needs_human_or_not_safe",
        "command": objective.command,
    }
    if execution.get("status") == "fail": status = "FAILED"
    elif objective.needs_human or (execute and not probe_permission_ok): status = "NEEDS_HUMAN"
    else: status = "EXECUTED" if execution.get("attempted") else "READY"
    risk_report = compile_research_risk(root, lane=lane)
    current_work = load_current_work_context(root)
    return {
        "status": status,
        "model": "AEROS-USEFUL-001-drive-mvp",
        "goal": goal,
        "job": job or "auto",
        "chosen_objective": objective.to_dict(),
        "research_risk": risk_report,
        "execution": execution,
        "project_signals": {
            "current_work": current_work,
            "broad_capture": broad_summary,
            "submission_driver_status": build_submission_driver(root).get("status"),
            "preflight": preflight,
        },
        "what_this_does": [
            "selects one useful next objective from existing deterministic AEROS signals",
            "turns scattered next/preflight/mode/submission/broad-capture signals into one packet",
            "executes only allowlisted read-only/dry-run commands or bounded nonproduction probes when --execute is requested",
        ],
        "what_this_does_not_touch": [
            "data/raw/",
            "data/intermediate/",
            "data/processed/",
            "paper/",
            "evidence/claim_registry.md",
            "decisions/approvals/",
        ],
        "does_not_prove": [
            item for item in DOES_NOT_PROVE
            if not (job == "probe_data" and execution.get("status") == "pass" and item == "that external provider/API work was performed")
        ],
    }


def format_drive_report(report: dict[str, Any]) -> str:
    objective = report.get("chosen_objective") or {}
    execution = report.get("execution") or {}
    broad = ((report.get("project_signals") or {}).get("broad_capture") or {})
    lines = [
        "# AEROS DRIVE",
        "",
        f"status: {report.get('status')}",
        f"goal: {report.get('goal')}",
        "",
        "## Chosen objective",
        f"- id: {objective.get('objective_id')}",
        f"- lane: {objective.get('lane')}",
        f"- objective: {objective.get('objective')}",
        f"- why: {objective.get('why')}",
        f"- status_label: {objective.get('status_label')}",
        f"- command: `{objective.get('command')}`",
        f"- stop_condition: {objective.get('stop_condition')}",
        f"- needs_human: {objective.get('needs_human')}",
        "",
        "## Expected artifacts",
    ]
    lines.extend(f"- {item}" for item in objective.get("expected_artifacts") or ["<none declared>"])
    lines.extend([
        "",
        "## Safety",
    ])
    lines.extend(f"- {item}" for item in objective.get("safety") or [])
    lines.extend([
        "",
        "## Execution",
        f"- attempted: {execution.get('attempted')}",
        f"- status: {execution.get('status')}",
    ])
    if execution.get("exit_code") is not None:
        lines.append(f"- exit_code: {execution.get('exit_code')}")
    lines.extend([
        "",
        "## Broad-capture signal",
        f"- leads: {broad.get('total_leads', 0)}",
        f"- candidates: {broad.get('total_candidates', 0)}",
        f"- duplicate_rate: {broad.get('duplicate_lead_rate', 0)}",
        f"- stale_leads: {broad.get('stale_lead_count', 0)}",
        f"- recommended_next_action: {broad.get('recommended_next_action', '')}",
        "",
        "## Does not prove",
    ])
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"


def write_drive_report(root: Path | str, report: dict[str, Any]) -> tuple[Path, Path]:
    root = Path(root)
    out_dir = root / "outputs" / "context"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "drive_packet.md"
    js = out_dir / "drive_packet.json"
    md.write_text(format_drive_report(report), encoding="utf-8")
    js.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return md, js
