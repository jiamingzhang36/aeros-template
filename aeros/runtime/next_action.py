"""Deterministic next-action projection for AEROS.

This module is deliberately not an LLM planner. It derives a small recommendation
from current project state, human-gate queue, recent harness summaries, and task
contracts. It does not execute tasks, approve gates, or modify runtime state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from .contract import Contract
from .controller import build_iterate_plan
from .kernel import discover_contracts
from .stale_triage import triage_item_for_task


VALID_LABELS = {"CHECK_PASS", "ROUTE_READY", "SUBSTANTIVE_DONE"}
LANE_ORDER = ["data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"]
STAGES = ["discovery", "execution"]

REGRESSION_CHECK_HINTS = {
    "check_stage_agents",
    "check_operating_dashboard",
    "check_skill_layer",
    "check_skill_invocations",
    "check_update_ledger",
    "check_git_guardrails",
    "check_task_contract",
    "check_task_automation_policy",
    "check_work_lanes",
    "check_completion_receipts",
    "check_noop_runs",
    "check_pipeline_runs",
}

GAP_OR_DECISION_CHECK_HINTS = {
    "check_gate_exit",
    "check_data_first_readiness",
    "check_data_inventory",
    "check_data_probe",
    "check_literature_tools",
    "check_literature_fulltext_execution",
    "check_claim_registry",
    "check_claim_ceiling",
    "check_identification_gate",
    "check_research_graph",
}


@dataclass(frozen=True)
class NextAction:
    recommended_next_action: str
    why_this_next: str
    lane: str
    status_label: str
    command: str
    stop_condition: str
    source: str = "deterministic"
    blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _project_has_idea(root: Path) -> bool:
    manifest = _read_yaml(root / "project_manifest.yml") or {}
    project_name = str((manifest.get("project") or {}).get("name", "")).strip()
    research = manifest.get("research") or {}
    for key in ("topic", "one_sentence_question", "question"):
        if str(research.get(key, "")).strip():
            return True
    if project_name == "AEROS project":
        return False
    idea_memo = root / "discovery" / "idea_memo.md"
    if idea_memo.exists():
        text = idea_memo.read_text(encoding="utf-8").strip()
        if text and "test idea" not in text.lower() and "TODO" not in text[:200]:
            return True
    return False


def _pending_human_gate_item(root: Path) -> dict[str, Any] | None:
    data = _read_yaml(root / "decisions" / "human_gate_queue.yml") or {}
    for item in data.get("items") or []:
        if isinstance(item, dict) and str(item.get("status", "")).strip() == "pending":
            return item
    return None


def _latest_harness_failure(root: Path) -> dict[str, str] | None:
    logs_dir = root / "outputs" / "logs"
    if not logs_dir.exists():
        return None
    candidates = sorted(
        logs_dir.glob("harness_check_summary*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        failures: list[dict[str, str]] = []
        for key in ("failures", "failed", "checks", "results"):
            value = data.get(key) if isinstance(data, dict) else None
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, str):
                    failures.append({"check": item, "detail": ""})
                elif isinstance(item, dict):
                    status = str(item.get("status", "")).lower()
                    failed = status == "fail" or bool(item.get("failed")) or bool(item.get("failures"))
                    if failed:
                        failures.append({
                            "check": str(item.get("check") or item.get("name") or item.get("script") or "unknown"),
                            "detail": str(item.get("detail") or item.get("message") or item.get("failures") or ""),
                        })
        if failures:
            first = failures[0]
            first["summary_path"] = path.as_posix()
            return first
    return None


def _check_kind(check_name: str) -> str:
    stem = Path(check_name).stem
    if stem in REGRESSION_CHECK_HINTS:
        return "regression"
    if stem in GAP_OR_DECISION_CHECK_HINTS:
        return "gap_or_decision"
    return "unknown"


def _rel(root: Path, path: Path | str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _contract_map(root: Path) -> dict[str, tuple[Contract, Path]]:
    return discover_contracts(root)


def _label_for_contract(contract: Contract) -> str:
    outputs = " ".join(contract.allowed_outputs).lower()
    goal = contract.goal.lower()
    if any(token in outputs for token in (
        "data/",
        "discovery/data_inventory",
        "discovery/data_diagnostics",
        "extraction_cards",
        "evidence/result",
        "outputs/tables",
        "outputs/model_outputs",
        "paper/",
    )):
        if "packet" not in goal and "plan only" not in goal:
            return "SUBSTANTIVE_DONE"
    if "packet" in goal or "plan" in goal or "audit" in goal or "review" in goal:
        return "ROUTE_READY"
    return "CHECK_PASS"


def _command_for(stage: str, lane: str) -> str:
    lane_part = f" --lane {lane}" if lane else ""
    return f"python3 -m aeros.cli iterate --stage {stage}{lane_part} --to-next-gate --dry-run"


def _from_plan(root: Path, *, stage: str, lane: str) -> NextAction | None:
    plan = build_iterate_plan(root, stage, to_next_gate=True, lane=lane)
    if not plan.can_run:
        if plan.reason:
            return NextAction(
                recommended_next_action=f"Resolve blocker before running {stage}{'/' + lane if lane else ''}.",
                why_this_next=plan.reason,
                lane=lane or "project",
                status_label="ROUTE_READY",
                command=f"python3 -m aeros.cli gate packet {plan.target_gate} --stage {stage}",
                stop_condition="Stop after the packet or blocker record identifies the human decision, credential, source snapshot, or missing prerequisite.",
                blocked=True,
            )
        return None
    contracts = _contract_map(root)
    for step in plan.steps:
        if step.action == "skip":
            continue
        contract = contracts.get(step.task_id, (None, None))[0]
        completion_label = _label_for_contract(contract) if contract else "ROUTE_READY"
        # `aeros next` is advisory. It previews the next controller step instead
        # of handing agents a default command that spends provider budget.
        label = "ROUTE_READY"
        if step.action == "blocked":
            return NextAction(
                recommended_next_action=f"Escalate blocked task {step.task_id}.",
                why_this_next=step.stale_reason or "The task contract says this step is blocked.",
                lane=step.lane or lane or "project",
                status_label="ROUTE_READY",
                command=f"python3 -m aeros.cli gate packet {step.gate} --stage {stage}",
                stop_condition="Stop after the human decision packet or queue item states what approval, credential, source snapshot, or boundary is needed.",
                blocked=True,
            )
        if step.action == "rerun":
            triage = triage_item_for_task(root, stage=stage, lane=step.lane or lane, task_id=step.task_id)
            if triage and triage.bucket == "suppress_as_irrelevant":
                continue
            if triage and triage.bucket == "revalidate_free":
                return NextAction(
                    recommended_next_action=f"Free revalidate stale task {triage.task_id} before any rerun.",
                    why_this_next=(
                        f"Stale reason: {triage.stale_reason}. {triage.rationale} "
                        f"Output changed={triage.output_changed}; frontier_connected={triage.frontier_connected}; "
                        f"claim_bound={triage.claim_bound}; impact_scope={triage.impact_scope}."
                    ),
                    lane=triage.lane,
                    status_label="CHECK_PASS",
                    command=triage.command,
                    stop_condition="Stop after recover --check passes or reports the first failing check; do not call a provider/API for this stale item first.",
                    source="deterministic_stale_triage",
                    blocked=False,
                )
            if triage and triage.bucket == "rerun_required":
                if triage.impacted_claims:
                    claims = f" Impacted claims: {', '.join(triage.impacted_claims)}."
                elif triage.impact_scope in {"claim_registry_unknown", "registry_unknown"}:
                    claims = " Impacted claims: unknown."
                else:
                    claims = ""
                return NextAction(
                    recommended_next_action=f"Preview high/visible stale rerun path for {triage.task_id}.",
                    why_this_next=(
                        f"Stale reason: {triage.stale_reason}. {triage.rationale} "
                        f"Output changed={triage.output_changed}; frontier_connected={triage.frontier_connected}; "
                        f"impact={triage.impact_level}; impact_scope={triage.impact_scope}.{claims}"
                    ),
                    lane=triage.lane,
                    status_label="ROUTE_READY",
                    command=triage.command,
                    stop_condition="Stop after the dry-run plan shows the exact task/check path; require explicit human choice before a provider/API rerun.",
                    source="deterministic_stale_triage",
                    blocked=False,
                )
            if triage is None:
                continue
        action_word = "Rerun stale task" if step.action == "rerun" else "Run next task"
        stale = f" Stale reason: {step.stale_reason}." if step.stale_reason else ""
        return NextAction(
            recommended_next_action=f"{action_word} {step.task_id}.",
            why_this_next=(
                f"It is the first non-skipped {stage} task in the deterministic plan for lane "
                f"{step.lane or lane or 'all'}, gate {step.gate}. "
                f"Preview first; if run for real later, expected outcome label is {completion_label}.{stale}"
            ),
            lane=step.lane or lane or "project",
            status_label=label,
            command=_command_for(stage, step.lane or lane),
            stop_condition=(
                "Stop when the dry-run previews the allowed-output/check path, or AEROS emits a blocker/decision packet. "
                "Do not treat route output as substantive progress."
            ),
        )
    return None



def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    import csv
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _paper_ids_from_text(text: str) -> list[str]:
    ids: list[str] = []
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text)
    for token in cleaned.split():
        if len(token) == 4 and token.startswith("P") and token[1:].isdigit() and token not in ids:
            ids.append(token)
    return ids


def _literature_fulltext_blockers(root: Path) -> list[str]:
    blockers: list[str] = []
    for row in _csv_rows(root / "discovery/literature/search_log.csv"):
        if str(row.get("follow_up", "")).strip() != "blocked_fulltext":
            continue
        text = " ".join(str(value) for value in row.values())
        for paper_id in _paper_ids_from_text(text):
            if paper_id not in blockers:
                blockers.append(paper_id)

    for row in _csv_rows(root / "discovery/literature/missing_fulltext_queue.csv"):
        status = str(row.get("status", "")).lower()
        reason = str(row.get("reason", "")).lower()
        if "blocked" not in status and "blocked" not in reason:
            continue
        paper_id = str(row.get("paper_id", "")).strip()
        if paper_id and paper_id not in blockers:
            blockers.append(paper_id)
    return sorted(blockers)


def _literature_next(root: Path) -> NextAction | None:
    registry = _csv_rows(root / "discovery/literature/paper_registry.csv")
    searches = _csv_rows(root / "discovery/literature/search_log.csv")
    papers = [row for row in registry if row.get("paper_id", "").strip()]
    search_count = len([row for row in searches if any(str(v).strip() for v in row.values())])
    included = [row for row in papers if row.get("screening_decision", "").strip() == "include"]
    extracted = [row for row in papers if row.get("extraction_card", "").strip() == "yes"]
    synthesized = [row for row in papers if row.get("used_in_synthesis", "").strip() == "yes"]
    fulltext_blockers = _literature_fulltext_blockers(root)
    if fulltext_blockers:
        paper_list = ", ".join(fulltext_blockers)
        return NextAction(
            recommended_next_action=f"Stop on unresolved literature full-text blockers: {paper_list}.",
            why_this_next=(
                "The literature lane has explicit blocked_fulltext retrieval records. "
                "Do not rerun stale literature discovery or synthesize from abstract-only rows until these blockers are resolved, waived, or queued for manual/Zotero/institutional PDF intake."
            ),
            lane="literature",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli literature status",
            stop_condition="Stop here; provide verified full text, connect Zotero/manual attachments, or record a bounded blocker. Do not treat metadata or cache files as full-text evidence.",
            source="discovery/literature/search_log.csv",
            blocked=True,
        )
    if not search_count and not papers:
        return NextAction(
            recommended_next_action="Run a literature discovery search into the registry before claiming literature progress.",
            why_this_next="The literature lane has no search log or paper candidates; full review cannot start until candidate discovery is recorded.",
            lane="literature",
            status_label="ROUTE_READY",
            command='python3 -m aeros.cli literature search --source openalex --query "<topic keywords>" --limit 25 --dry-run',
            stop_condition="Stop after candidates are previewed or logged into search_log.csv/paper_registry.csv; do not write synthesis from metadata.",
            source="discovery/literature/search_log.csv",
        )
    if papers and not included:
        return NextAction(
            recommended_next_action="Screen literature candidates by function and stable source before full-text extraction.",
            why_this_next="Paper candidates exist, but none are marked include; this is screening work, not synthesis.",
            lane="literature",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli literature status",
            stop_condition="Stop when selected papers have screening_decision=include/maybe and citation_audit.md records their verification needs.",
            source="discovery/literature/paper_registry.csv",
        )
    if included and not extracted:
        return NextAction(
            recommended_next_action="Run function-specific full-text extraction for included literature candidates.",
            why_this_next="Included papers exist, but no extraction cards are recorded; bookkeeping cannot support synthesis.",
            lane="literature",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli next --lane literature --write",
            stop_condition="Stop after LIT-FULL extraction cards cite opened source/date and page/section-bound evidence, or record full_text_unavailable.",
            source="discovery/literature/extraction_cards/",
        )
    if extracted and not synthesized:
        return NextAction(
            recommended_next_action="Synthesize extracted papers by literature function before paper positioning.",
            why_this_next="Extraction cards exist, but no paper is marked used_in_synthesis; synthesis can now cite full-text evidence.",
            lane="literature",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli literature status",
            stop_condition="Stop after function-specific synthesis states what each cited paper can and cannot support.",
            source="discovery/literature/synthesis/",
        )
    return None



def _data_next(root: Path) -> NextAction | None:
    inventory_rows = _csv_rows(root / "discovery/data_inventory.csv")
    has_data_state = (root / "data/data_state.yml").exists()
    has_gap_plan = (root / "data/data_gap_plan.yml").exists()
    has_probe_report = (root / "audits/data_probe_report.md").exists()
    has_backfill_queue = (root / "data/backfill/backfill_queue.yml").exists()
    if not inventory_rows and not has_data_state:
        return NextAction(
            recommended_next_action="Scan project data/source artifacts before doing literature, methods, or writing work.",
            why_this_next="AEROS is data-first: no data inventory or data_state exists, so later research lanes would be ungrounded.",
            lane="data",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli data scan --dry-run",
            stop_condition="Stop after data_state/inventory coverage is previewed or written; do not claim data feasibility yet.",
            source="data/data_state.yml",
        )
    if has_data_state and not has_gap_plan:
        return NextAction(
            recommended_next_action="Derive the data gap plan from the scanned data state.",
            why_this_next="Data state exists, but missing/blocked/runnable gaps are not yet formalized into a queueable plan.",
            lane="data",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli data gaps --dry-run",
            stop_condition="Stop after gaps are classified as runnable, approval-required, missing credential, or missing snapshot.",
            source="data/data_gap_plan.yml",
        )
    if (inventory_rows or has_data_state) and not has_probe_report:
        return NextAction(
            recommended_next_action="Plan a small data probe before full collection or analysis.",
            why_this_next="AEROS should test access/parseability/coverage on a small sample before large backfill or paper-facing results.",
            lane="data",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli data probe plan --dry-run",
            stop_condition="Stop after candidate probes and required approvals are visible; do not treat probe planning as data evidence.",
            source="audits/data_probe_report.md",
        )
    if has_gap_plan and not has_backfill_queue:
        return NextAction(
            recommended_next_action="Generate the data backfill queue from the gap plan.",
            why_this_next="Known data gaps should become explicit runnable or approval-required queue items instead of informal TODOs.",
            lane="data",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli data backfill --dry-run",
            stop_condition="Stop after local-cache-safe versus source-limited items are separated with approval/receipt needs.",
            source="data/backfill/backfill_queue.yml",
        )
    return None


def _analysis_next(root: Path) -> NextAction | None:
    registry_rows = _csv_rows(root / "evidence/result_registry.csv")
    index_rows = _csv_rows(root / "evidence/result_index.csv")
    if registry_rows and not index_rows:
        return NextAction(
            recommended_next_action="Sync registered results into the result index/provenance layer.",
            why_this_next="Paper-facing results exist in result_registry, but the derived result_index/provenance path is not visible.",
            lane="analysis",
            status_label="CHECK_PASS",
            command="python3 -m aeros.cli paper-ci sync-result-index --dry-run",
            stop_condition="Stop after the sync preview shows result_index/provenance targets; run for real only when source artifacts exist.",
            source="evidence/result_registry.csv",
        )
    return None


def _claim_next(root: Path) -> NextAction | None:
    graph = root / "evidence/research_graph.yml"
    claim_registry = root / "evidence/claim_registry.md"
    if claim_registry.exists() and not graph.exists():
        return NextAction(
            recommended_next_action="Build the derived research graph before claim audit.",
            why_this_next="Claim/evidence/result relationships should be observable as a graph before G7-style claim review.",
            lane="claim",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli graph build --dry-run",
            stop_condition="Stop after impact/support/orphan relationships are visible; do not downgrade or approve claims from graph output.",
            source="evidence/research_graph.yml",
        )
    return None


def _writing_next(root: Path) -> NextAction | None:
    draft = root / "paper/draft.md"
    if not draft.exists():
        return NextAction(
            recommended_next_action="Do not draft the paper yet; route through claim and number readiness first.",
            why_this_next="Writing should be claim-bound and number-bound, not a free-standing paper factory output.",
            lane="writing",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli next --lane claim",
            stop_condition="Stop after claim support/limits are visible; draft only bounded prose tied to registered claims and numbers.",
            source="paper/draft.md",
            blocked=True,
        )
    return None


def _compliance_next(root: Path) -> NextAction | None:
    manifest = root / "replication/aea_data_package_manifest.yml"
    if not manifest.exists():
        return NextAction(
            recommended_next_action="Prepare replication/release alignment before public release claims.",
            why_this_next="Compliance/release readiness needs a manifest for data availability, licenses, environment, and reproducibility boundaries.",
            lane="compliance",
            status_label="ROUTE_READY",
            command="python3 checks/run_harness_checks.py --profile lane:compliance --timeout 20",
            stop_condition="Stop after missing replication/compliance artifacts are explicit; do not infer release readiness from analysis success.",
            source="harness/aea_replication_policy.yml",
        )
    return None


def _lane_specific_next(root: Path, lane: str) -> NextAction | None:
    if lane == "data":
        return _data_next(root)
    if lane == "literature":
        return _literature_next(root)
    if lane == "method":
        return _method_next(root)
    if lane == "analysis":
        return _analysis_next(root)
    if lane == "claim":
        return _claim_next(root)
    if lane == "writing":
        return _writing_next(root)
    if lane == "compliance":
        return _compliance_next(root)
    return None

def _method_next(root: Path) -> NextAction:
    return NextAction(
        recommended_next_action="Run method advisory routing before empirical analysis, using econ-specific DiD/IV/RDD/panel rules.",
        why_this_next="Method work needs economics defaults and stop rules, but advisory policies cannot certify identification or approve claims.",
        lane="method",
        status_label="ROUTE_READY",
        command="python3 -m aeros.cli skills plan --stage execution",
        stop_condition="Stop after method risks, blocking questions, estimator defaults, and human-confirm fields are recorded; do not run final estimates from advisory alone.",
        source="harness/econ_method_advisory_policy.yml",
    )

def compute_next_action(root: Path, *, lane: str = "") -> NextAction:
    root = root.resolve()

    failure = _latest_harness_failure(root)
    if failure:
        check = failure.get("check", "unknown")
        kind = _check_kind(check)
        if kind == "regression":
            return NextAction(
                recommended_next_action=f"Fix the failing regression/process check: {check}.",
                why_this_next="A recent harness summary reports a process-style red light; this should be repaired before advancing research work.",
                lane="harness",
                status_label="CHECK_PASS",
                command=f"python3 {check if check.endswith('.py') else 'checks/' + check + '.py'}",
                stop_condition="Stop when the specific check passes, then rerun the smallest relevant harness slice.",
                source=failure.get("summary_path", "harness_summary"),
            )
        return NextAction(
            recommended_next_action=f"Escalate or route the failing research/gap check: {check}.",
            why_this_next="The latest harness red light appears to represent a missing evidence, gate, data, literature, claim, or decision condition rather than a simple regression.",
            lane="project",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli next --write",
            stop_condition="Stop after the blocker is represented in CURRENT_STATE.md or decisions/human_gate_queue.yml; do not paper over the red light.",
            source=failure.get("summary_path", "harness_summary"),
            blocked=True,
        )

    pending = _pending_human_gate_item(root)
    if pending:
        return NextAction(
            recommended_next_action=f"Resolve pending human gate request for {pending.get('project', 'this project')}.",
            why_this_next=str(pending.get("why_human_needed", "A human decision is pending.")),
            lane="human_gate",
            status_label="ROUTE_READY",
            command="python3 -m aeros.cli gate status",
            stop_condition="Stop after the human approves, blocks, supersedes, or narrows the queued request.",
            source="decisions/human_gate_queue.yml",
            blocked=True,
        )

    if not _project_has_idea(root):
        return NextAction(
            recommended_next_action="Adopt or enter a research idea before running lane tasks.",
            why_this_next="No research topic/question is recorded yet, so running data, literature, or writing tasks would be route churn.",
            lane="discovery",
            status_label="ROUTE_READY",
            command='python3 -m aeros.cli adopt --idea "<your research idea>" --dry-run',
            stop_condition="Stop after the adoption preview shows the candidate gate, gap plan, and next discovery route.",
            source="project_manifest.yml",
        )


    if lane:
        action = _lane_specific_next(root, lane)
        if action:
            return action

    if lane:
        for stage in STAGES:
            action = _from_plan(root, stage=stage, lane=lane)
            if action:
                return action
        return NextAction(
            recommended_next_action=f"No deterministic next task is currently visible for lane {lane}.",
            why_this_next=(
                "A lane-specific next-action request must not drift into another lane. "
                "Run the lane harness/profile or choose a different lane explicitly."
            ),
            lane=lane,
            status_label="CHECK_PASS",
            command=f"python3 checks/run_harness_checks.py --profile lane:{lane} --timeout 30",
            stop_condition="Stop when the lane-scoped checks pass or report the first concrete blocker.",
            source="deterministic_lane_scope",
        )

    for preferred_lane in LANE_ORDER:
        action = _lane_specific_next(root, preferred_lane)
        if action:
            return action
        for stage in STAGES:
            action = _from_plan(root, stage=stage, lane=preferred_lane)
            if action:
                return action

    for stage in STAGES:
        action = _from_plan(root, stage=stage, lane="")
        if action:
            return action

    return NextAction(
        recommended_next_action="Run a status and harness smoke check; no deterministic next task is currently visible.",
        why_this_next="AEROS found no failing checks, pending human gate item, missing idea, or non-skipped task in the deterministic controller plan.",
        lane="harness",
        status_label="CHECK_PASS",
        command="python3 checks/run_harness_checks.py --profile smoke --timeout 30",
        stop_condition="Stop when the harness passes or reports the first concrete blocker.",
    )


def format_next_action(action: NextAction) -> str:
    data = action.to_dict()
    return "\n".join(f"{key}: {value}" for key, value in data.items())


def next_action_markdown(action: NextAction) -> str:
    data = action.to_dict()
    lines = ["# NEXT_ACTION", ""]
    for key in [
        "recommended_next_action",
        "why_this_next",
        "lane",
        "status_label",
        "command",
        "stop_condition",
        "source",
        "blocked",
    ]:
        lines.append(f"{key}: {data.get(key)}")
    lines.append("")
    lines.append("This is a deterministic recommendation. It does not execute tasks, approve gates, or certify research substance.")
    return "\n".join(lines)


def write_next_action(root: Path, action: NextAction) -> Path:
    path = root / "NEXT_ACTION.md"
    path.write_text(next_action_markdown(action), encoding="utf-8")
    return path
