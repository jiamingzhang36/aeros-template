"""The AEROS runtime loop: contract -> agent -> checks -> retry/escalate -> state."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import yaml
from functools import partial
from pathlib import Path
from types import SimpleNamespace

from . import critic as critic_mod
from . import identity
from . import state as state_mod
from .agent import AgentResult, build_prompt, run_agent
from .candidate_workspace import (
    execute_callback_in_candidate_worktree,
    format_candidate_workspace_failure,
    load_candidate_policy,
    write_candidate_workspace_audit,
)
from .checks import format_feedback, run_checks
from .completion import write_completion_receipt, validate_completion_receipts
from .completion_review import build_review_packet, classify_completion_review, render_review_evidence
from .contract import Contract, load_contract
from .execution_envelope import ExecutionEnvelope, execute_in_isolated_worktree
from .profile_runtime import runtime_check_plan
from .report import AttemptRecord, RunRecord, write_run_report
from .skill_receipt import write_skill_invocation_receipt
from .task_preflight import build_task_preflight
from .work_lane import lane_matches, normalize_lane

print = partial(print, flush=True)


def find_project_root(start: Path) -> Path:
    """Walk up to a manifest, attached adapter, or Git project root."""
    for parent in [start, *start.parents]:
        if (
            (parent / "project_manifest.yml").exists()
            or (parent / ".aeros/project.yml").exists()
            or (parent / ".aeros/adapter.yml").exists()
        ):
            return parent
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError(
        "could not locate project root (no project manifest, .aeros adapter, or Git root above "
        f"{start})"
    )


def discover_contracts(project_root: Path, stage: str | None = None) -> dict:
    """Load all task contracts (optionally filtered by stage), keyed by task_id."""
    out: dict[str, tuple[Contract, Path]] = {}
    for p in sorted((project_root / "tasks").rglob("*.yml")):
        try:
            c = load_contract(p)
        except Exception:  # noqa: BLE001 - skip unparseable contracts
            continue
        if stage and c.stage != stage:
            continue
        out[c.task_id] = (c, p)
    return out


def topo_order(contracts: dict) -> list[str]:
    """Dependency order (Kahn). Gates are checkpoints; execution follows depends_on,
    which can differ from gate number (e.g. G2 variable construction depends on the
    G3 design options that name the variables)."""
    from collections import deque
    deps = {tid: set(c.depends_on) & set(contracts) for tid, (c, _) in contracts.items()}
    order: list[str] = []
    ready = deque(sorted(t for t, d in deps.items() if not d))
    queued = set(ready)
    while ready:
        t = ready.popleft()
        order.append(t)
        for other, d in deps.items():
            if t in d:
                d.discard(t)
                if not d and other not in order and other not in queued:
                    ready.append(other); queued.add(other)
    for t in sorted(contracts):  # any cycle leftovers, deterministically appended
        if t not in order:
            order.append(t)
    return order


def _task_gates(contracts: dict) -> dict[str, str]:
    return {tid: c.gate for tid, (c, _) in contracts.items()}


def _contract_block_reason(contract: Contract) -> str:
    if contract.automation_class == "approval_required" and contract.gate_status.startswith("blocked_"):
        return (
            f"{contract.automation_class}/{contract.gate_status}; "
            "requires explicit human approval before automatic rerun"
        )
    return ""


def _revalidation_skill_waivers(contract: Contract, stale_reason: str = "") -> list[dict]:
    """Record why recommended skills were not invoked during check-only refresh."""
    names = sorted({
        str(s).strip()
        for s in [
            *(contract.raw.get("recommended_skills") or []),
            *(contract.raw.get("required_skill_classes") or []),
        ]
        if str(s).strip()
    })
    reason = (
        "Task was not re-run by an external worker because existing allowed "
        "outputs passed the task's required checks during AEROS revalidation. "
        "No skill-derived evidence is being claimed for this refresh."
    )
    if stale_reason:
        reason += f" Staleness trigger: {stale_reason}."
    return [
        {
            "skill_class": name,
            "waiver_reason": reason,
            "waiver_scope": "fingerprint_refresh_only",
        }
        for name in names
    ]


def _with_dependency_closure(selected: dict, all_contracts: dict) -> dict:
    out = dict(selected)
    changed = True
    while changed:
        changed = False
        for contract, _path in list(out.values()):
            for dep in contract.depends_on:
                if dep in all_contracts and dep not in out:
                    out[dep] = all_contracts[dep]
                    changed = True
    return out


# Sections of project_manifest.yml that govern GATE PASSAGE and harness wiring,
# not task EXECUTION. Changing which checks a gate requires (gate_exit_criteria)
# or the check name->path map (checks) must not invalidate task outputs: a task's
# output depends only on its own substantive inputs, and the gate evaluator reads
# gate_exit_criteria live at gate time. Excluding them from the per-task input
# fingerprint stops an unrelated gate-criteria edit from marking every task stale.
_MANIFEST_NONTASK_KEYS = ("gate_exit_criteria", "checks")


def _manifest_fingerprint_bytes(path: Path) -> bytes:
    """Canonical manifest bytes for task-staleness, with gate-evaluation-only
    sections removed. Falls back to raw bytes if the manifest cannot be parsed
    (never weaker than hashing the whole file)."""
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            trimmed = {k: v for k, v in data.items() if k not in _MANIFEST_NONTASK_KEYS}
            return yaml.safe_dump(trimmed, sort_keys=True).encode("utf-8")
    except Exception:
        pass
    return path.read_bytes()


def _fingerprint_paths(project_root: Path, rel_paths: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in sorted(str(item).rstrip("/") for item in rel_paths if item):
        # agent_runs is an audit side effect, not a semantic task output.
        if rel == "agent_runs" or rel.startswith("agent_runs/"):
            continue
        # pending manual prompts are runtime control artifacts, not semantic
        # research outputs. Including them makes manual recovery invalidate
        # broad task outputs such as outputs/.
        if rel == "outputs/pending_tasks" or rel.startswith("outputs/pending_tasks/"):
            continue
        path = project_root / rel
        digest.update(rel.encode("utf-8"))
        if not path.exists():
            digest.update(b"\0MISSING")
            continue
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for file_path in files:
            rel_file = file_path.relative_to(project_root).as_posix()
            if rel_file == "outputs/pending_tasks" or rel_file.startswith("outputs/pending_tasks/"):
                continue
            digest.update(rel_file.encode("utf-8"))
            digest.update(b"\0")
            if rel_file == "project_manifest.yml":
                digest.update(hashlib.sha256(_manifest_fingerprint_bytes(file_path)).digest())
            else:
                file_digest = hashlib.sha256()
                with file_path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        file_digest.update(chunk)
                digest.update(file_digest.digest())
    return digest.hexdigest()


def _stat_guard_paths(project_root: Path, rel_paths: list[str]) -> str:
    """Cheap change detector used before content hashing large artifacts.

    It has no admission authority: a stat match only permits runtime reuse of
    an already content-hashed acceptance. New acceptance, promotion, and
    release continue to use SHA-256 and artifact-specific validators.
    """
    records: list[tuple] = []
    for rel in sorted(str(item).rstrip("/") for item in rel_paths if item):
        if rel == "agent_runs" or rel.startswith("agent_runs/"):
            continue
        if rel == "outputs/pending_tasks" or rel.startswith("outputs/pending_tasks/"):
            continue
        path = project_root / rel
        if not path.exists():
            records.append((rel, "MISSING"))
            continue
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for file_path in files:
            rel_file = file_path.relative_to(project_root).as_posix()
            if rel_file == "outputs/pending_tasks" or rel_file.startswith("outputs/pending_tasks/"):
                continue
            stat = file_path.stat()
            records.append((rel_file, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino))
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode("utf-8")).hexdigest()


def _dependency_fingerprint(project_root: Path, contract: Contract, contracts: dict) -> str:
    deps: dict[str, str] = {}
    for dep in sorted(contract.depends_on):
        dep_record = contracts.get(dep)
        if not dep_record:
            deps[dep] = "missing-contract"
            continue
        dep_contract, _ = dep_record
        deps[dep] = _fingerprint_paths(project_root, dep_contract.allowed_outputs)
    return hashlib.sha256(json.dumps(deps, sort_keys=True).encode("utf-8")).hexdigest()


def _dependency_stat_guard(project_root: Path, contract: Contract, contracts: dict) -> str:
    deps: dict[str, str] = {}
    for dep in sorted(contract.depends_on):
        dep_record = contracts.get(dep)
        if not dep_record:
            deps[dep] = "missing-contract"
            continue
        dep_contract, _ = dep_record
        deps[dep] = _stat_guard_paths(project_root, dep_contract.allowed_outputs)
    return hashlib.sha256(json.dumps(deps, sort_keys=True).encode("utf-8")).hexdigest()


def _record_task_fingerprints(
    state: dict,
    contract: Contract,
    project_root: Path,
    contracts: dict,
) -> None:
    entry = state_mod.task_entry(state, contract.task_id)
    entry["input_fingerprint"] = _fingerprint_paths(project_root, contract.inputs)
    entry["output_fingerprint"] = _fingerprint_paths(project_root, contract.allowed_outputs)
    entry["dependency_fingerprint"] = _dependency_fingerprint(project_root, contract, contracts)
    entry["input_stat_guard"] = _stat_guard_paths(project_root, contract.inputs)
    entry["output_stat_guard"] = _stat_guard_paths(project_root, contract.allowed_outputs)
    entry["dependency_stat_guard"] = _dependency_stat_guard(project_root, contract, contracts)


def _stale_reason(
    state: dict,
    contract: Contract,
    project_root: Path,
    contracts: dict,
) -> str:
    entry = state_mod.task_entry(state, contract.task_id)
    current_input_stat = _stat_guard_paths(project_root, contract.inputs)
    current_dep_stat = _dependency_stat_guard(project_root, contract, contracts)
    current_output_stat = _stat_guard_paths(project_root, contract.allowed_outputs)
    if (
        entry.get("input_stat_guard") == current_input_stat
        and entry.get("dependency_stat_guard") == current_dep_stat
        and entry.get("output_stat_guard") == current_output_stat
        and entry.get("input_fingerprint")
        and entry.get("dependency_fingerprint")
        and entry.get("output_fingerprint")
    ):
        return ""
    current_input = _fingerprint_paths(project_root, contract.inputs)
    current_dep = _dependency_fingerprint(project_root, contract, contracts)
    current_output = _fingerprint_paths(project_root, contract.allowed_outputs)

    # Existing passed tasks are bootstrapped on first run after this feature.
    if not entry.get("input_fingerprint"):
        entry["input_fingerprint"] = current_input
        entry["dependency_fingerprint"] = current_dep
        entry["output_fingerprint"] = current_output
        entry["input_stat_guard"] = current_input_stat
        entry["dependency_stat_guard"] = current_dep_stat
        entry["output_stat_guard"] = current_output_stat
        return ""
    if entry.get("input_fingerprint") != current_input:
        return "input_changed"
    if entry.get("dependency_fingerprint") != current_dep:
        return "dependency_output_changed"
    if entry.get("output_fingerprint") != current_output:
        return "output_changed"
    entry["input_stat_guard"] = current_input_stat
    entry["dependency_stat_guard"] = current_dep_stat
    entry["output_stat_guard"] = current_output_stat
    return ""


AWAITING_GATE = 7  # pipeline halted at a gate boundary, waiting for human approval


def _agent_provenance(project_root: Path) -> tuple[str, str, float | None]:
    """Best-effort provenance for the worker agent, read from the manifest.
    Records what is actually known; never fabricates a model/temperature."""
    manifest_path = project_root / "project_manifest.yml"
    if not manifest_path.exists():
        return "", "", None
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    auto = manifest.get("automation", {}) or {}
    provider = str(auto.get("agent_provider", "") or "")
    model = str(auto.get("agent_model", "") or "")
    temp = auto.get("temperature", None)
    try:
        temp = float(temp) if temp is not None else None
    except (TypeError, ValueError):
        temp = None
    return provider, model, temp


def _critic_config(project_root: Path) -> dict:
    """Read automation.critic config. Default: disabled (opt-in)."""
    manifest_path = project_root / "project_manifest.yml"
    if not manifest_path.exists():
        return {"enabled": False}
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    cfg = (manifest.get("automation", {}) or {}).get("critic", {}) or {}
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "provider": str(cfg.get("provider", "mock")),
        "model": str(cfg.get("model", "mock-critic")),
        "blocking": bool(cfg.get("blocking", False)),
        "timeout_seconds": int(cfg.get("timeout_seconds", 120)),
    }


def _run_critic_pass(
    project_root: Path,
    contract: "Contract",
    state: dict,
    candidate_run: object,
    check_results: list,
) -> tuple[bool, str]:
    """Independent verification pass after the worker passes deterministic checks.
    Returns True if the run may proceed (advisory, or no blocking finding), False
    if a blocking critic finding should escalate. Records a summary in state."""
    cfg = _critic_config(project_root)
    entry = state_mod.task_entry(state, contract.task_id)
    accepted = tuple(getattr(candidate_run, "accepted_outputs", ()) or ())
    plan = classify_completion_review(contract, accepted)
    if not plan.should_run(advisory_enabled=cfg["enabled"]):
        entry["critic"] = {
            "verdict": "not_required",
            "risk": plan.risk,
            "required": False,
            "human_gate_required": False,
            "reasons": list(plan.reasons),
        }
        return True, ""

    packet = build_review_packet(
        project_root,
        contract,
        candidate_run,
        check_results,
        reviewer_identity={"provider": cfg["provider"], "model": cfg["model"]},
    )
    review_key = str(packet["review_key"])
    verdict = critic_mod.load_cached_verdict(project_root, review_key)
    if verdict is None:
        verdict = critic_mod.run_critic(
            task_id=contract.task_id,
            goal=contract.goal,
            evidence=render_review_evidence(packet),
            provider=cfg["provider"],
            model=cfg["model"],
            timeout_seconds=cfg["timeout_seconds"],
        )
        verdict.review_key = review_key
        if verdict.verdict != "unverified":
            critic_mod.save_cached_verdict(project_root, verdict)
    report = critic_mod.write_critic_report(
        project_root,
        contract.task_id,
        verdict,
        risk=plan.risk,
        required=plan.required,
        human_gate_required=plan.human_gate_required,
    )
    entry["critic"] = {
        "verdict": verdict.verdict,
        "concern_modes": verdict.concern_modes,
        "blocking": verdict.has_blocking,
        "risk": plan.risk,
        "required": plan.required,
        "human_gate_required": plan.human_gate_required,
        "review_key": review_key,
        "cached": verdict.cached,
        "report": str(report.relative_to(project_root)),
    }
    print(f"[kernel]   critic ({verdict.provider}): {verdict.verdict}"
          + (f" — concerns: {', '.join(verdict.concern_modes)}" if verdict.concern_modes else ""))
    if plan.human_gate_required:
        return False, "Critical completion requires an independent critic and a human gate."
    if plan.required and verdict.verdict == "unverified":
        return False, "Required independent critic was unavailable or unparseable."
    if (plan.required or cfg["blocking"]) and verdict.has_blocking:
        return False, "Independent critic raised a high-severity integrity concern."
    return True, ""


def _gate_lifecycle(project_root: Path) -> dict:
    manifest_path = project_root / "project_manifest.yml"
    if not manifest_path.exists():
        return {}
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    return manifest.get("gate_lifecycle", {}) or {}


def _active_profile(project_root: Path) -> tuple[str, dict, dict]:
    """Return (profile_name, profile_config, gate_lifecycle)."""
    gl = _gate_lifecycle(project_root)
    name = str(gl.get("profile", "full"))
    prof = (gl.get("profiles", {}) or {}).get(name, {}) or {}
    return name, prof, gl


def _gate_config(project_root: Path) -> tuple[dict[int, str], set[int]]:
    """Return (rank -> gate label, set of human-gate ranks).

    Human gates come from the active profile if it sets them, else from
    `gate_lifecycle.human_gates`. If neither is set, every gate is human
    (conservative legacy behavior)."""
    name, prof, gl = _active_profile(project_root)
    rank_to_label: dict[int, str] = {}
    for label in gl.get("gates", []) or []:
        rank_to_label[state_mod._gate_rank(str(label))] = str(label)
    human = prof.get("human_gates", gl.get("human_gates", None))
    if human is None:
        human_ranks = set(rank_to_label)
    else:
        human_ranks = {state_mod._gate_rank(str(h)) for h in human}
    return rank_to_label, human_ranks


def _active_gate_ranks(project_root: Path) -> set[int] | None:
    """Ranks of gates active under the current profile, or None for 'all'.

    A 'lite' profile names a coherent subset; the pipeline still pulls in any
    task that an active task depends on (dependency closure), so a slimmed
    profile can never break the task DAG."""
    name, prof, gl = _active_profile(project_root)
    active = prof.get("active_gates", None)
    if active in (None, "all", "*"):
        return None
    return {state_mod._gate_rank(str(g)) for g in active}


def _human_gate_halt_enabled(project_root: Path) -> bool:
    """Whether the pipeline should STOP at a configured human gate.

    Separates two concerns the system used to bundle together:
      - *halting* the frontier at a judgment gate (workflow: do not pre-run work
        past an un-ratified human gate), and
      - the git-committer *trust anchor* (who may grant the approval).
    The trust anchor stays gated on enforcement_enabled; halting also turns on
    when the profile/lifecycle EXPLICITLY declares human_gates, so a project can
    get "human decides at key nodes" without first setting up distinct agent and
    approver git identities. Projects that want full autonomy set human_gates: [].
    """
    if identity.enforcement_enabled(project_root):
        return True
    _name, prof, gl = _active_profile(project_root)
    return prof.get("human_gates") is not None or gl.get("human_gates") is not None


def _reconcile_frontier(state: dict, project_root: Path, stage: str,
                        tid: str, context: str) -> bool:
    """Advance current_gate through earned MECHANICAL gates; halt at the first
    earned HUMAN gate by writing an approval request. Returns True if halted.

    The agent writes the request but never commits it, so it cannot grant its
    own gate. `context` describes what comes next (for the request note)."""
    rank_to_label, human_ranks = _gate_config(project_root)
    current_rank = state_mod._gate_rank(str(state.get("current_gate", "G0")))
    candidate_rank = state_mod._gate_rank(str(state.get("candidate_gate", "G0")))
    r = current_rank + 1
    while r <= candidate_rank:
        gate_label = rank_to_label.get(r, f"G{r}")
        if r in human_ranks:
            slug = identity.gate_slug(gate_label)
            # Auto-generate the decision packet so the human's judgment is fast
            # and informed (counter Bainbridge's deskilling): what you're
            # approving, the evidence, the unmet criteria, the risks.
            packet_rel = ""
            try:
                from .decision_packet import write_decision_packet
                packet = write_decision_packet(project_root, slug, stage=stage)
                packet_rel = str(packet.relative_to(project_root))
            except Exception as exc:  # noqa: BLE001 - packet is advisory, never fatal
                print(f"  (decision packet could not be generated: {exc})")
            note = f"Autonomous loop earned {gate_label} (human gate); {context}"
            if packet_rel:
                note += f"\n\nDecision packet (what you are approving): {packet_rel}"
            artifact = identity.write_approval_request(
                project_root, gate=gate_label, stage=stage, requested_by="agent", note=note,
            )
            rel = artifact.relative_to(project_root)
            print(f"[pipeline] AWAITING HUMAN GATE: earned {gate_label} (judgment gate).")
            if packet_rel:
                print(f"  decision packet: {packet_rel}  <- read this first")
            print(f"  request written: {rel}")
            print("  To grant (as the human / approver identity):")
            print(f"    git add {rel} && git commit -m \"approve {slug}\"")
            print(f"    aeros gate approve \"{gate_label}\" --stage \"{stage}\"")
            print("  Then re-run the pipeline to resume.")
            return True
        state_mod.auto_advance_current_gate(state, stage=stage, gate=gate_label, task_id=tid)
        state_mod.save_state(project_root, state)
        print(f"  ✓ auto-advanced to {gate_label} (mechanical gate, no human stop)")
        current_rank = r
        r += 1
    return False


FOUNDATION_GATE = "G3"  # discovery's last gate; all execution gates rank above it


def _foundation_ok(project_root: Path) -> tuple[bool, list[str]]:
    """Re-evaluate the discovery-foundation gates (G0..G3) as a hard precondition
    for execution. Generalizes data-readiness: gate-exit criteria are otherwise
    only rendered in the decision packet (informational), so a foundation gate
    that regresses (data not complete, anchor/design/variable-construction broken)
    would not actually BLOCK downstream work. _evaluate_gate is cumulative, so
    evaluating FOUNDATION_GATE checks the whole foundation in one call. Capped at
    G3 (not the candidate) so the in-progress execution gate is never evaluated as
    its own precondition (which would deadlock). Returns (ok, unmet_reasons)."""
    try:
        from .decision_packet import _evaluate_gate
        return _evaluate_gate(project_root, FOUNDATION_GATE)
    except Exception:  # noqa: BLE001 - precondition must never crash the run
        return True, []


def run_pipeline(
    project_root: Path,
    stage: str = "discovery",
    *,
    dry_run: bool = False,
    stop_gate: str | None = None,
    task_timeout_override: int | None = None,
    max_retries_override: int | None = None,
    lane: str = "",
) -> int:
    """Run a stage's contracts in dependency order, stopping at the first
    escalation. Returns 0 if all passed (or dry-run), non-zero on stop."""
    state = state_mod.load_state(project_root)
    # Execution may run once a human has approved the G3 (design/claim) gate.
    # Check the gate HISTORY for that approval, not the latest gate_status:
    # once execution starts, the pipeline auto-advances mechanical gates and
    # flips gate_status to "auto_advanced", which must not retroactively revoke
    # the standing G3 approval on the next run.
    g3_rank = state_mod._gate_rank("G3")

    def _human_approved_g3_plus() -> bool:
        for entry in state.get("gate_history", []) or []:
            if (str(entry.get("reason", "")).strip() == "human_approved"
                    and state_mod._gate_rank(str(entry.get("gate", "G0"))) >= g3_rank):
                return True
        return False

    approved_for_execution = _human_approved_g3_plus() or (
        state.get("gate_status") in {"approved", "blocked"}
        and state_mod._gate_rank(str(state.get("current_gate", "G0"))) >= g3_rank
    )
    if stage == "execution" and not dry_run and not approved_for_execution:
        print(
            "[pipeline] execution requires a human-approved gate. "
            "Run: aeros gate approve G3 --stage discovery --owner <name> --note <why>"
        )
        return 2
    # Data-readiness is a HARD precondition, not just a packet line: re-evaluate
    # the G1 exit checks every run. Otherwise a gate that "passed" historically
    # (before, say, check_data_complete existed) lets execution proceed on data
    # that is no longer certified complete. Data not complete -> do not advance.
    if stage == "execution" and not dry_run:
        ok_foundation, unmet = _foundation_ok(project_root)
        if not ok_foundation:
            print("[pipeline] execution BLOCKED: discovery-foundation gate(s) G0-G3 "
                  "not met — resolve before running execution:")
            for u in unmet[:6]:
                print(f"  - {u}")
            return 2
    contracts = discover_contracts(project_root, stage)
    all_contracts = discover_contracts(project_root)
    if not contracts:
        print(f"[pipeline] no contracts for stage {stage!r}")
        return 1
    active_lane = normalize_lane(lane)
    if lane and not active_lane:
        print(f"[pipeline] invalid work lane {lane!r}")
        return 2
    if stop_gate:
        target_rank = state_mod._gate_rank(stop_gate)
        contracts = {
            task_id: record
            for task_id, record in contracts.items()
            if state_mod._gate_rank(record[0].gate or "") <= target_rank
        }
        contracts = _with_dependency_closure(contracts, all_contracts)
    active_ranks = _active_gate_ranks(project_root)
    if active_ranks is not None:
        before = len(contracts)
        contracts = {
            tid: rec for tid, rec in contracts.items()
            if state_mod._gate_rank(rec[0].gate or "") in active_ranks
        }
        contracts = _with_dependency_closure(contracts, all_contracts)
        prof_name = _active_profile(project_root)[0]
        print(f"[pipeline] profile '{prof_name}': {len(contracts)} of {before} "
              f"{stage} task(s) active (incl. dependencies)")
    if active_lane:
        before = len(contracts)
        contracts = {
            tid: rec for tid, rec in contracts.items()
            if lane_matches(rec[0], active_lane)
        }
        print(f"[pipeline] lane '{active_lane}': {len(contracts)} of {before} "
              f"{stage} task(s) selected")
    order = topo_order(contracts)
    print(f"[pipeline] {stage}: {len(order)} task(s) in dependency order")
    skipped = 0
    for tid in order:
        c, path = contracts[tid]
        deps = ", ".join(c.depends_on) or "—"
        blocked_reason = _contract_block_reason(c)
        if blocked_reason:
            print(f"  ! {tid} blocked ({blocked_reason})")
            if dry_run:
                continue
            print("[pipeline] stopped before blocked approval-required task")
            return 2
        # Skip tasks already passed in a previous run (idempotent resume).
        task_status = state_mod.task_entry(state, tid).get("status", "pending")
        if task_status == "passed":
            stale_reason = _stale_reason(state, c, project_root, all_contracts)
            if stale_reason:
                # Staleness is only a heuristic for "might need re-running". Re-running
                # a non-deterministic agent regenerates slightly different output, which
                # changes its output fingerprint and cascades staleness to every
                # downstream task -> wasted agent quota on each iterate. So first
                # re-validate the EXISTING outputs: if the task's own checks still pass,
                # refresh the fingerprints and keep it passed (no agent call). Only
                # re-run the agent when the existing outputs actually fail.
                revalidated = False
                if not dry_run and c.checks:
                    passed_now, _results = run_checks(project_root, c.checks)
                    revalidated = passed_now
                if revalidated:
                    _record_task_fingerprints(state, c, project_root, all_contracts)
                    receipt = write_completion_receipt(
                        project_root, c, mode="revalidation", check_results=_results,
                        skill_receipt_path=write_skill_invocation_receipt(
                            project_root, c, skills_used=[], run_report_path=None,
                            skill_waivers=_revalidation_skill_waivers(c, stale_reason),
                        ),
                        input_fingerprint=state_mod.task_entry(state, tid).get("input_fingerprint", ""),
                        output_fingerprint=state_mod.task_entry(state, tid).get("output_fingerprint", ""),
                        dependency_fingerprint=state_mod.task_entry(state, tid).get("dependency_fingerprint", ""),
                    )
                    if not receipt.passed:
                        print(f"  ! {tid} completion receipt failed during revalidation:")
                        for failure in receipt.failures:
                            print(f"      - {failure}")
                        state_mod.set_status(state, tid, "escalated")
                        state_mod.save_state(project_root, state)
                        return 2
                    print(f"  ✓ {tid} (stale: {stale_reason}; existing outputs still pass "
                          f"checks — refreshing fingerprint, not re-running)")
                    state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                    state_mod.save_state(project_root, state)
                    skipped += 1
                    continue
                print(f"  ! {tid} is stale ({stale_reason}) — re-running")
                state_mod.set_status(state, tid, "stale")
                state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                state_mod.save_state(project_root, state)
                task_status = "stale"
            else:
                receipt_problems = validate_completion_receipts(
                    project_root, {tid: (c, path)}, {"tasks": {tid: state_mod.task_entry(state, tid)}}
                )
                if receipt_problems:
                    print(f"  ! {tid} is passed but completion receipt is invalid — revalidating")
                    if not dry_run and c.checks:
                        passed_now, results_now = run_checks(project_root, c.checks)
                    else:
                        passed_now, results_now = False, []
                    if passed_now:
                        _record_task_fingerprints(state, c, project_root, all_contracts)
                        receipt = write_completion_receipt(
                            project_root, c, mode="revalidation", check_results=results_now,
                            skill_receipt_path=write_skill_invocation_receipt(
                                project_root, c, skills_used=[], run_report_path=None,
                                skill_waivers=_revalidation_skill_waivers(c, "completion receipt repair"),
                            ),
                            input_fingerprint=state_mod.task_entry(state, tid).get("input_fingerprint", ""),
                            output_fingerprint=state_mod.task_entry(state, tid).get("output_fingerprint", ""),
                            dependency_fingerprint=state_mod.task_entry(state, tid).get("dependency_fingerprint", ""),
                        )
                        if receipt.passed:
                            print(f"  ✓ {tid} completion receipt repaired by revalidation")
                            state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                            state_mod.save_state(project_root, state)
                            skipped += 1
                            continue
                    print(f"  ! {tid} completion receipt invalid; re-running")
                    state_mod.set_status(state, tid, "stale")
                    state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                    state_mod.save_state(project_root, state)
                    task_status = "stale"
                    # fall through to run task
                else:
                    print(f"  ✓ {tid} (already passed — skipping)")
                    state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                    skipped += 1
                    continue
        # Gate-tiered reconciliation (autonomous mode): auto-advance through
        # earned mechanical gates, halt only at an earned human gate. This stops
        # the loop before it works PAST an un-ratified judgment gate.
        if not dry_run and _human_gate_halt_enabled(project_root):
            if _reconcile_frontier(state, project_root, stage, tid,
                                   context=f"halting before {c.gate} task {tid}."):
                return AWAITING_GATE
        print(f"  -> {tid} (gate {c.gate or '?'}, after: {deps})")
        if dry_run:
            continue
        rc = run_task(path, dry_run=False,
                      task_timeout_override=task_timeout_override,
                      max_retries_override=max_retries_override)
        # Reload state after each task (run_task writes it).
        state = state_mod.load_state(project_root)
        if rc != 0:
            print(f"[pipeline] stopped at {tid} (escalated). Fix/approve, then re-run.")
            return rc
        task_gates = _task_gates(all_contracts)
        state_mod.recompute_candidate_gate(state, task_gates)
        state_mod.save_state(project_root, state)
    if dry_run:
        print("[pipeline] (dry-run: no tasks executed)")
        return 0
    # Final reconciliation: the last gate's own tasks may have earned a human
    # gate that no later task forced us to ratify. Halt for it now.
    if _human_gate_halt_enabled(project_root):
        if _reconcile_frontier(state, project_root, stage, "end-of-stage",
                               context="all stage tasks complete; ratify to continue."):
            return AWAITING_GATE
    state_mod.save_state(project_root, state)
    print(f"[pipeline] all tasks passed. ({skipped} skipped as already-passed)")
    return 0


def _read_inputs(project_root: Path, contract: Contract) -> str:
    blocks: list[str] = []
    for rel in contract.inputs:
        p = project_root / rel
        if p.is_dir():
            files = sorted(x for x in p.rglob("*") if x.is_file())
            listing = "\n".join(f"- {x.relative_to(project_root).as_posix()}" for x in files[:200])
            if len(files) > 200:
                listing += f"\n- ... ({len(files) - 200} more file(s))"
            blocks.append(f"--- {rel} (DIRECTORY) ---\n{listing or '(empty directory)'}")
        elif p.exists():
            blocks.append(f"--- {rel} ---\n{p.read_text(encoding='utf-8')}")
        else:
            blocks.append(f"--- {rel} (MISSING) ---")
    return "\n\n".join(blocks)


def _escalate(project_root: Path, contract: Contract, feedback: str) -> Path:
    out_dir = project_root / "decisions" / "escalations"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{contract.task_id}.md"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    why = "Automated retries exhausted; checks still failing."
    if "Agent invocation failed" in (feedback or ""):
        why = "Automated retries exhausted after agent invocation failure."
    path.write_text(
        f"# Escalation: {contract.task_id}\n\n"
        f"Raised: {stamp}\n\n"
        f"## Why\n{why}\n\n"
        f"## Last check feedback\n\n{feedback or '(no structured feedback)'}\n\n"
        f"## Human options\n- approve (accept current state)\n"
        f"- revise: <instruction>\n- pause\n- drop\n",
        encoding="utf-8",
    )
    return path


def _contract_envelope(contract: "Contract") -> ExecutionEnvelope:
    allowed = tuple(str(path).strip() for path in contract.allowed_outputs if str(path).strip())
    deny = (
        "data/raw/",
        "decisions/approvals/",
        "aeros/state/",
    )
    return ExecutionEnvelope(
        read_roots=(".",),
        write_roots=allowed,
        deny_roots=deny,
        expected_outputs=allowed,
        runtime_profile="task-local-isolated-worktree",
    )


def _envelope_feedback(result) -> str:
    parts = [f"ExecutionEnvelope blocked deterministic command: {result.message}"]
    if result.return_code:
        parts.append(f"return_code={result.return_code}")
    if result.denied_writes:
        parts.append("denied_writes=" + ", ".join(result.denied_writes))
    if result.undeclared_writes:
        parts.append("undeclared_writes=" + ", ".join(result.undeclared_writes))
    if result.unexpected_outputs:
        parts.append("unexpected_outputs=" + ", ".join(result.unexpected_outputs))
    if result.missing_expected_outputs:
        parts.append("missing_expected_outputs=" + ", ".join(result.missing_expected_outputs))
    if result.unproduced_expected_outputs:
        parts.append("unproduced_expected_outputs=" + ", ".join(result.unproduced_expected_outputs))
    if result.failed_acceptance_checks:
        parts.append("failed_acceptance_checks=" + ", ".join(result.failed_acceptance_checks))
    if result.validator_modified_outputs:
        parts.append("validator_modified_outputs=" + ", ".join(result.validator_modified_outputs))
    if result.copyback_error:
        parts.append("copyback_error=" + result.copyback_error)
    return "\n".join(parts)


def _run_deterministic_task(contract: "Contract", project_root: Path,
                             state: dict, dry_run: bool,
                             task_timeout_override: int | None = None) -> int:
    """Run a zero-agent-calls contract by executing its check scripts directly.

    Tasks with max_agent_calls=0 are deterministic probes (e.g. API calls,
    data downloads). They produce output via a standalone script listed in the
    contract's goal; we just run the checks and report pass/fail.
    """
    import subprocess
    if dry_run:
        command = " ".join(contract.run_command) if contract.run_command else "(no command)"
        print(f"[kernel] DRY RUN: deterministic task {contract.task_id}")
        print(f"[kernel]   command: {command}")
        print(f"[kernel]   checks : {contract.checks}")
        print(f"[kernel]   envelope: isolated worktree; allowed outputs={contract.allowed_outputs}")
        return 0

    accepted_paths: list[str] = []
    if contract.run_command:
        print(f"[kernel] deterministic command under ExecutionEnvelope: {' '.join(contract.run_command)}")
        result = execute_in_isolated_worktree(
            project_root,
            contract.run_command,
            _contract_envelope(contract),
            timeout_seconds=task_timeout_override or contract.timeout_seconds,
            cwd_rel=contract.run_cwd,
            acceptance_checks=tuple(contract.checks),
        )
        if not result.ok:
            feedback = _envelope_feedback(result)
            path = _escalate(project_root, contract, feedback)
            state_mod.set_status(state, contract.task_id, "escalated")
            state_mod.save_state(project_root, state)
            print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
            return 2
        accepted_paths = list(result.accepted_outputs)
        print("[kernel]   envelope accepted outputs: "
              f"{', '.join(result.accepted_outputs) or '(none)'}")

    from .checks import run_checks, format_feedback
    check_names = list(contract.checks)
    if accepted_paths:
        plan = runtime_check_plan(
            project_root,
            contract_checks=contract.checks,
            observed_paths=[*accepted_paths, *contract.inputs],
        )
        check_names = list(plan.checks)
        print(f"[kernel]   profile={plan.profile}; checks={plan.strategy}")
    passed, results = run_checks(project_root, check_names)
    for r in results:
        print(f"[kernel]   check {r.name}: {'PASS' if r.passed else 'FAIL'}")
    if passed:
        review_candidate = result if contract.run_command else SimpleNamespace(
            accepted_outputs=tuple(accepted_paths),
            observed_writes=tuple(accepted_paths),
            denied_writes=(),
            undeclared_writes=(),
        )
        critic_ok, critic_feedback = _run_critic_pass(
            project_root, contract, state, review_candidate, results
        )
        if not critic_ok:
            path = _escalate(project_root, contract, critic_feedback)
            state_mod.set_status(state, contract.task_id, "escalated")
            state_mod.save_state(project_root, state)
            print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
            return 2
        contracts = discover_contracts(project_root)
        _record_task_fingerprints(state, contract, project_root, contracts)
        entry = state_mod.task_entry(state, contract.task_id)
        skill_receipt = write_skill_invocation_receipt(
            project_root, contract, skills_used=[], run_report_path=None
        )
        receipt = write_completion_receipt(
            project_root, contract, mode="deterministic", check_results=results,
            skill_receipt_path=skill_receipt,
            input_fingerprint=entry.get("input_fingerprint", ""),
            output_fingerprint=entry.get("output_fingerprint", ""),
            dependency_fingerprint=entry.get("dependency_fingerprint", ""),
        )
        if not receipt.passed:
            feedback = "Completion receipt failed: " + "; ".join(receipt.failures)
            path = _escalate(project_root, contract, feedback)
            state_mod.set_status(state, contract.task_id, "escalated")
            state_mod.save_state(project_root, state)
            print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
            return 2
        state_mod.set_status(state, contract.task_id, "passed")
        state_mod.recompute_candidate_gate(state, _task_gates(contracts))
        state_mod.record_run_summary(state, contract.task_id, calls=0, cost_usd=0.0)
        state_mod.save_state(project_root, state)
        print(f"[kernel] task {contract.task_id} PASSED (deterministic).")
        return 0
    # Not passed — escalate immediately (no retries for deterministic tasks)
    feedback = format_feedback(results)
    path = _escalate(project_root, contract, feedback)
    state_mod.set_status(state, contract.task_id, "escalated")
    state_mod.save_state(project_root, state)
    print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
    return 2


def run_task(contract_path: str | Path, *, dry_run: bool = False,
             max_retries_override: int | None = None,
             task_timeout_override: int | None = None) -> int:
    contract = load_contract(contract_path)
    project_root = find_project_root(Path(contract_path).resolve())
    # Import lazily: context compilation reaches next_action/controller, which
    # already imports kernel for task planning. The execution boundary is the
    # only caller that needs this dependency.
    from .context_episode import bind_execution_context
    try:
        context_basis = bind_execution_context(
            project_root,
            task_id=contract.task_id,
            lane=contract.work_lane,
            goal=contract.goal,
        )
    except RuntimeError as exc:
        print(f"[kernel] task {contract.task_id} BLOCKED: {exc}")
        return 2
    print(
        f"[kernel] context episode {context_basis['episode_id']} "
        f"(lane={context_basis['lane']}, status={context_basis['status']})"
    )
    state = state_mod.load_state(project_root)
    entry = state_mod.task_entry(state, contract.task_id)
    if entry.get("status") == "passed" and entry.get("output_fingerprint"):
        contracts = discover_contracts(project_root)
        stale_reason = _stale_reason(state, contract, project_root, contracts)
        if not stale_reason:
            state_mod.save_state(project_root, state)
            print(
                f"[kernel] task {contract.task_id} already PASSED with unchanged "
                "inputs/dependencies/outputs; reusing accepted artifacts without an agent, provider, or data rerun."
            )
            return 0
        state_mod.set_status(state, contract.task_id, "stale")
        state_mod.task_entry(state, contract.task_id)["stale_reason"] = stale_reason
        state_mod.save_state(project_root, state)
    preflight = build_task_preflight(
        project_root,
        task_id=contract.task_id,
        lane=contract.work_lane,
        intent=contract.goal,
        campaign_id=contract.campaign_id,
    )
    if preflight.get("status") == "BLOCKED":
        reasons = [str(item) for item in (preflight.get("stop_before_work_if") or [])]
        feedback = "Task preflight blocked execution:\n- " + "\n- ".join(reasons)
        path = _escalate(project_root, contract, feedback)
        state_mod.set_status(state, contract.task_id, "escalated")
        state_mod.save_state(project_root, state)
        print(f"[kernel] task {contract.task_id} BLOCKED by preflight -> {path}")
        return 2
    state_mod.set_status(state, contract.task_id, "running")

    # Deterministic probe tasks (max_agent_calls=0) skip the agent loop entirely.
    if contract.max_agent_calls == 0:
        return _run_deterministic_task(contract, project_root, state, dry_run,
                                       task_timeout_override=task_timeout_override)

    max_retries = (max_retries_override if max_retries_override is not None
                   else contract.max_retries)
    inputs_text = _read_inputs(project_root, contract)
    feedback: str | None = None
    attempts_log: list[AttemptRecord] = []

    # Per-run budget counters (enforced locally so a re-run is never blocked by
    # a previous run's spend). State keeps cumulative totals for the audit trail.
    run_calls = 0
    run_cost = 0.0
    run_in = 0
    run_out = 0

    def _finish(status: str) -> None:
        """Persist the run report and per-run summary on both pass and escalate."""
        state_mod.record_run_summary(state, contract.task_id,
                                     calls=run_calls, cost_usd=run_cost)
        state_mod.save_state(project_root, state)
        prov_provider, prov_model, prov_temp = _agent_provenance(project_root)
        tools_used = sorted({name for rec in attempts_log for name, _, _ in rec.checks})
        run = RunRecord(
            contract=contract, final_status=status, attempts=attempts_log,
            run_calls=run_calls, run_cost_usd=run_cost,
            run_input_tokens=run_in, run_output_tokens=run_out,
            agent_provider=prov_provider, agent_model=prov_model,
            temperature=prov_temp, tools_used=tools_used,
            context_episode_id=str(context_basis.get("episode_id") or ""),
            context_hash=str(context_basis.get("context_hash") or ""),
            context_binding_path=str(context_basis.get("binding_path") or ""),
        )
        skill_receipt = write_skill_invocation_receipt(
            project_root, contract, skills_used=[], run_report_path=None
        )
        run.skill_receipt_path = skill_receipt.relative_to(project_root).as_posix()
        report_path = write_run_report(project_root, run)
        print(f"[kernel] run report -> {report_path.relative_to(project_root)} "
              f"(cost ${run_cost:.4f}, {run_calls} call(s))")

    for attempt in range(max_retries + 1):
        if run_calls >= contract.max_agent_calls:
            print(f"[kernel] call budget exhausted ({contract.max_agent_calls} calls). Escalating.")
            break
        if run_cost >= contract.max_dollars:
            print(f"[kernel] cost budget exhausted (${run_cost:.4f} >= "
                  f"${contract.max_dollars:.2f}). Escalating.")
            break

        prompt = build_prompt(contract, inputs_text, feedback, project_root)

        if dry_run:
            print("=" * 70)
            print(f"[DRY RUN] task={contract.task_id} attempt={attempt + 1} "
                  f"budget: {contract.max_agent_calls} calls / ${contract.max_dollars:.2f}")
            print("=" * 70)
            print(prompt)
            print("=" * 70)
            print(f"[DRY RUN] would run: claude -p <prompt>  (cwd={project_root})")
            print(f"[DRY RUN] would then run checks: {contract.checks}")
            state_mod.set_status(state, contract.task_id, "dry_run")
            state_mod.save_state(project_root, state)
            return 0

        # Hard-cap this call at the run's remaining budget so a single runaway
        # call cannot overshoot max_dollars (claude --max-budget-usd).
        call_cap = round(contract.max_dollars - run_cost, 2)
        print(f"[kernel] attempt {attempt + 1}/{max_retries + 1}: invoking agent "
              f"(spent ${run_cost:.4f}/{contract.max_dollars:.2f}, call cap ${call_cap:.2f})...")

        agent_policy = load_candidate_policy(project_root)
        expected_outputs = tuple(
            path for path in contract.allowed_outputs
            if not str(path).startswith(("agent_runs/", "decisions/", "aeros/state/"))
        ) or tuple(contract.allowed_outputs)
        candidate_run = execute_callback_in_candidate_worktree(
            project_root,
            lambda candidate_root: run_agent(
                prompt,
                candidate_root,
                timeout=task_timeout_override or contract.timeout_seconds,
                max_budget_usd=call_cap,
            ),
            allowed_outputs=tuple(contract.allowed_outputs),
            expected_outputs=expected_outputs,
            deny_roots=tuple(agent_policy.get("deny_roots") or ()),
        )
        result = candidate_run.callback_value
        if not isinstance(result, AgentResult):
            result = AgentResult(False, "", candidate_run.callback_error or "candidate agent callback returned no AgentResult")
        # Account for spend regardless of outcome (a failed call can still cost).
        run_calls += 1
        run_cost += result.cost_usd
        run_in += result.input_tokens
        run_out += result.output_tokens
        state_mod.record_agent_call(state, contract.task_id, result.cost_usd)
        state_mod.save_state(project_root, state)  # crash-safe: persist spend immediately
        if result.cost_usd:
            print(f"[kernel]   call cost ${result.cost_usd:.4f} "
                  f"({result.input_tokens} in / {result.output_tokens} out)")

        if not candidate_run.boundary_ok:
            audit_path = write_candidate_workspace_audit(project_root, contract.task_id, candidate_run)
            feedback = format_candidate_workspace_failure(candidate_run)
            print(f"[kernel] agent envelope violation -> {audit_path.relative_to(project_root)}")
            attempts_log.append(AttemptRecord(
                attempt=attempt + 1,
                agent_ok=result.ok,
                agent_error="",
                checks=[],
                feedback=feedback,
            ))
            continue

        if not result.ok:
            print(f"[kernel] agent error: {result.error}")
            attempts_log.append(AttemptRecord(
                attempt=attempt + 1, agent_ok=False, agent_error=result.error,
                checks=[], feedback="",
            ))
            feedback = f"Agent invocation failed: {result.error}"
            continue

        plan = runtime_check_plan(
            project_root,
            contract_checks=contract.checks,
            observed_paths=[*candidate_run.accepted_outputs, *contract.inputs],
        )
        print(f"[kernel]   profile={plan.profile}; checks={plan.strategy}")
        passed, results = run_checks(project_root, list(plan.checks))
        for r in results:
            print(f"[kernel]   check {r.name}: {'PASS' if r.passed else 'FAIL'}")

        attempt_feedback = "" if passed else format_feedback(results)
        attempts_log.append(AttemptRecord(
            attempt=attempt + 1, agent_ok=True, agent_error="",
            checks=[(r.name, r.passed, r.failures) for r in results],
            feedback=attempt_feedback,
        ))

        if passed:
            # Independent verification pass (separate from the worker) before the
            # task is accepted. Advisory by default; can block on high-severity.
            critic_ok, critic_feedback = _run_critic_pass(
                project_root, contract, state, candidate_run, results
            )
            if not critic_ok:
                feedback = critic_feedback
                state_mod.save_state(project_root, state)
                break
            contracts = discover_contracts(project_root)
            _record_task_fingerprints(state, contract, project_root, contracts)
            temp_run = RunRecord(
                contract=contract, final_status="passed", attempts=attempts_log,
                run_calls=run_calls, run_cost_usd=run_cost,
                run_input_tokens=run_in, run_output_tokens=run_out,
                agent_provider=_agent_provenance(project_root)[0],
                agent_model=_agent_provenance(project_root)[1],
                temperature=_agent_provenance(project_root)[2],
                tools_used=sorted({name for rec in attempts_log for name, _, _ in rec.checks}),
                context_episode_id=str(context_basis.get("episode_id") or ""),
                context_hash=str(context_basis.get("context_hash") or ""),
                context_binding_path=str(context_basis.get("binding_path") or ""),
            )
            skill_receipt = write_skill_invocation_receipt(
                project_root,
                contract,
                skills_used=list(contract.raw.get("skills_used") or []),
                skill_waivers=list(contract.raw.get("skill_waivers") or []),
                run_report_path=None,
            )
            temp_run.skill_receipt_path = skill_receipt.relative_to(project_root).as_posix()
            report_path = write_run_report(project_root, temp_run)
            skill_receipt = write_skill_invocation_receipt(
                project_root,
                contract,
                skills_used=list(contract.raw.get("skills_used") or []),
                skill_waivers=list(contract.raw.get("skill_waivers") or []),
                run_report_path=report_path,
            )
            entry = state_mod.task_entry(state, contract.task_id)
            receipt = write_completion_receipt(
                project_root, contract, mode="agent_run", check_results=results,
                run_report_path=report_path, skill_receipt_path=skill_receipt,
                input_fingerprint=entry.get("input_fingerprint", ""),
                output_fingerprint=entry.get("output_fingerprint", ""),
                dependency_fingerprint=entry.get("dependency_fingerprint", ""),
            )
            if not receipt.passed:
                feedback = "Completion receipt failed: " + "; ".join(receipt.failures)
                continue
            state_mod.set_status(state, contract.task_id, "passed")
            state_mod.recompute_candidate_gate(state, _task_gates(contracts))
            print(f"[kernel] task {contract.task_id} PASSED.")
            state_mod.record_run_summary(state, contract.task_id,
                                         calls=run_calls, cost_usd=run_cost)
            state_mod.save_state(project_root, state)
            print(f"[kernel] run report -> {report_path.relative_to(project_root)} "
                  f"(cost ${run_cost:.4f}, {run_calls} call(s))")
            print(f"[kernel] completion receipt -> {receipt.path.relative_to(project_root)}")
            return 0

        feedback = attempt_feedback

    path = _escalate(project_root, contract, feedback or "")
    state_mod.set_status(state, contract.task_id, "escalated")
    print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
    _finish("escalated")
    return 2
