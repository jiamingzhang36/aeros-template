"""The AEROS runtime loop: contract -> agent -> checks -> retry/escalate -> state."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import yaml
from functools import partial
from pathlib import Path

from . import identity
from . import state as state_mod
from .agent import build_prompt, run_agent
from .checks import format_feedback, run_checks
from .contract import Contract, load_contract
from .report import AttemptRecord, RunRecord, write_run_report

print = partial(print, flush=True)


def find_project_root(start: Path) -> Path:
    """Walk up from a contract path to the dir containing project_manifest.yml."""
    for parent in [start, *start.parents]:
        if (parent / "project_manifest.yml").exists():
            return parent
    raise FileNotFoundError(
        "could not locate project root (no project_manifest.yml above "
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
            digest.update(hashlib.sha256(file_path.read_bytes()).digest())
    return digest.hexdigest()


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


def _stale_reason(
    state: dict,
    contract: Contract,
    project_root: Path,
    contracts: dict,
) -> str:
    entry = state_mod.task_entry(state, contract.task_id)
    current_input = _fingerprint_paths(project_root, contract.inputs)
    current_dep = _dependency_fingerprint(project_root, contract, contracts)
    current_output = _fingerprint_paths(project_root, contract.allowed_outputs)

    # Existing passed tasks are bootstrapped on first run after this feature.
    if not entry.get("input_fingerprint"):
        entry["input_fingerprint"] = current_input
        entry["dependency_fingerprint"] = current_dep
        entry["output_fingerprint"] = current_output
        return ""
    if entry.get("input_fingerprint") != current_input:
        return "input_changed"
    if entry.get("dependency_fingerprint") != current_dep:
        return "dependency_output_changed"
    if entry.get("output_fingerprint") != current_output:
        return "output_changed"
    return ""


AWAITING_GATE = 7  # pipeline halted at a gate boundary, waiting for human approval


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


def run_pipeline(
    project_root: Path,
    stage: str = "discovery",
    *,
    dry_run: bool = False,
    stop_gate: str | None = None,
    task_timeout_override: int | None = None,
    max_retries_override: int | None = None,
) -> int:
    """Run a stage's contracts in dependency order, stopping at the first
    escalation. Returns 0 if all passed (or dry-run), non-zero on stop."""
    state = state_mod.load_state(project_root)
    approved_for_execution = (
        state.get("gate_status") in {"approved", "blocked"}
        and state_mod._gate_rank(str(state.get("current_gate", "G0"))) >= state_mod._gate_rank("G3")
    )
    if stage == "execution" and not dry_run and not approved_for_execution:
        print(
            "[pipeline] execution requires a human-approved gate. "
            "Run: aeros gate approve G3 --stage discovery --owner <name> --note <why>"
        )
        return 2
    contracts = discover_contracts(project_root, stage)
    all_contracts = discover_contracts(project_root)
    if not contracts:
        print(f"[pipeline] no contracts for stage {stage!r}")
        return 1
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
                print(f"  ! {tid} is stale ({stale_reason}) — re-running")
                state_mod.set_status(state, tid, "stale")
                state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                state_mod.save_state(project_root, state)
                task_status = "stale"
            else:
                print(f"  ✓ {tid} (already passed — skipping)")
                state_mod.recompute_candidate_gate(state, _task_gates(all_contracts))
                skipped += 1
                continue
        # Gate-tiered reconciliation (autonomous mode): auto-advance through
        # earned mechanical gates, halt only at an earned human gate. This stops
        # the loop before it works PAST an un-ratified judgment gate.
        if not dry_run and identity.enforcement_enabled(project_root):
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
    if identity.enforcement_enabled(project_root):
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
        return 0

    if contract.run_command:
        cwd = (project_root / contract.run_cwd).resolve()
        print(f"[kernel] deterministic command: {' '.join(contract.run_command)}")
        result = subprocess.run(
            contract.run_command,
            cwd=str(cwd),
            timeout=task_timeout_override or contract.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            feedback = f"Deterministic command failed with exit code {result.returncode}"
            path = _escalate(project_root, contract, feedback)
            state_mod.set_status(state, contract.task_id, "escalated")
            state_mod.save_state(project_root, state)
            print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
            return 2

    from .checks import run_checks, format_feedback
    passed, results = run_checks(project_root, contract.checks)
    for r in results:
        print(f"[kernel]   check {r.name}: {'PASS' if r.passed else 'FAIL'}")
    if passed:
        state_mod.set_status(state, contract.task_id, "passed")
        contracts = discover_contracts(project_root)
        _record_task_fingerprints(state, contract, project_root, contracts)
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
    state = state_mod.load_state(project_root)
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
        run = RunRecord(
            contract=contract, final_status=status, attempts=attempts_log,
            run_calls=run_calls, run_cost_usd=run_cost,
            run_input_tokens=run_in, run_output_tokens=run_out,
        )
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

        result = run_agent(prompt, project_root,
                           timeout=task_timeout_override or contract.timeout_seconds,
                           max_budget_usd=call_cap)
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

        if not result.ok:
            print(f"[kernel] agent error: {result.error}")
            attempts_log.append(AttemptRecord(
                attempt=attempt + 1, agent_ok=False, agent_error=result.error,
                checks=[], feedback="",
            ))
            feedback = f"Agent invocation failed: {result.error}"
            continue

        passed, results = run_checks(project_root, contract.checks)
        for r in results:
            print(f"[kernel]   check {r.name}: {'PASS' if r.passed else 'FAIL'}")

        attempt_feedback = "" if passed else format_feedback(results)
        attempts_log.append(AttemptRecord(
            attempt=attempt + 1, agent_ok=True, agent_error="",
            checks=[(r.name, r.passed, r.failures) for r in results],
            feedback=attempt_feedback,
        ))

        if passed:
            state_mod.set_status(state, contract.task_id, "passed")
            contracts = discover_contracts(project_root)
            _record_task_fingerprints(state, contract, project_root, contracts)
            state_mod.recompute_candidate_gate(state, _task_gates(contracts))
            print(f"[kernel] task {contract.task_id} PASSED.")
            _finish("passed")
            return 0

        feedback = attempt_feedback

    path = _escalate(project_root, contract, feedback or "")
    state_mod.set_status(state, contract.task_id, "escalated")
    print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
    _finish("escalated")
    return 2
