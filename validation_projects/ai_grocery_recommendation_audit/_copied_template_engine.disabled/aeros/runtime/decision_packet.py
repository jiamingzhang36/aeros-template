"""Human gate decision packets for AEROS.

A packet is an auditable recommendation bundle. It never approves a gate; it
summarizes the machine state so a human can approve, block, revise, or stop.
"""

from __future__ import annotations

import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from . import state as state_mod

GATES = [f"G{i}" for i in range(10)]


def _gate_rank(gate: str) -> int:
    return state_mod._gate_rank(gate)


def _gates_through(target_gate: str) -> list[str]:
    target = _gate_rank(target_gate)
    if target < 0:
        return [target_gate]
    return [gate for gate in GATES if _gate_rank(gate) <= target]


def _checks_dir(project_root: Path) -> Path:
    project_checks = project_root / "checks"
    if project_checks.exists():
        return project_checks
    # Validation projects may live under the template repo without carrying a
    # duplicate checks/ directory. Fall back to the repository-level checks next
    # to the installed/source AEROS package.
    return Path(__file__).resolve().parents[2] / "checks"


def _evaluate_gate(project_root: Path, gate: str) -> tuple[bool, list[str]]:
    checks_dir = _checks_dir(project_root)
    sys.path.insert(0, str(checks_dir))
    previous_checks_dir = os.environ.get("AEROS_CHECKS_DIR")
    os.environ["AEROS_CHECKS_DIR"] = str(checks_dir)
    try:
        from check_gate_exit import evaluate_through_gate  # type: ignore  # noqa: E402

        ok, failures = evaluate_through_gate(gate, project_root=str(project_root))
        return bool(ok), list(failures or [])
    except Exception as exc:  # noqa: BLE001 - packet should report, not crash
        return False, [f"could not evaluate gate criteria: {exc}"]
    finally:
        if previous_checks_dir is None:
            os.environ.pop("AEROS_CHECKS_DIR", None)
        else:
            os.environ["AEROS_CHECKS_DIR"] = previous_checks_dir


def _front_matter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _claim_ceiling(project_root: Path) -> str:
    fm = _front_matter(project_root / "discovery" / "design_selection.md")
    return str(fm.get("earned_claim_ceiling") or "none")


def _recommendation(ok: bool, target_gate: str, state: dict[str, Any]) -> str:
    already_approved = (
        state.get("gate_status") == "approved"
        and _gate_rank(str(state.get("current_gate", "G0"))) >= _gate_rank(target_gate)
    )
    if already_approved and ok:
        return f"{target_gate} is already human-approved and current criteria still pass."
    if already_approved and not ok:
        return (
            f"{target_gate} was previously approved, but current criteria no longer pass; "
            "revise, block, or re-approve only after human review."
        )
    if ok:
        return f"Approve {target_gate} if the human reviewer accepts the evidence packet."
    return f"Do not approve {target_gate} yet; revise, rerun, downgrade, block, or stop."


def build_decision_packet(project_root: Path, target_gate: str, *, stage: str = "") -> str:
    state = state_mod.load_state(project_root)
    gate_results: list[tuple[str, bool, list[str]]] = []
    for gate in _gates_through(target_gate):
        ok, failures = _evaluate_gate(project_root, gate)
        gate_results.append((gate, ok, failures))

    target_ok = gate_results[-1][1] if gate_results else False
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stage_label = stage or str(state.get("current_stage", "?"))

    lines = [
        f"# Human Gate Decision Packet: {target_gate}",
        "",
        f"Generated: {stamp}",
        f"Stage: {stage_label}",
        f"Current gate: {state.get('current_gate', '?')}",
        f"Gate status: {state.get('gate_status', 'open')}",
        f"Candidate gate: {state.get('candidate_stage', '?')} / {state.get('candidate_gate', '?')}",
        f"Earned claim ceiling: {_claim_ceiling(project_root)}",
        "",
        "## Recommendation",
        "",
        _recommendation(target_ok, target_gate, state),
        "",
        "## Gate Criteria Status",
        "",
        "| Gate | Status | Notes |",
        "|---|---|---|",
    ]
    for gate, ok, failures in gate_results:
        note = "all criteria satisfied" if ok else f"{len(failures)} unmet criterion/criteria"
        lines.append(f"| {gate} | {'PASS' if ok else 'FAIL'} | {note} |")

    lines.extend(["", "## Failed / Missing Criteria", ""])
    any_failures = False
    for gate, ok, failures in gate_results:
        if ok:
            continue
        any_failures = True
        lines.append(f"### {gate}")
        lines.append("")
        for failure in failures:
            lines.append(f"- {failure}")
        lines.append("")
    if not any_failures:
        lines.append("None. All criteria through the target gate passed.")
        lines.append("")

    lines.extend([
        "## Key Risks for Human Review",
        "",
        "- Check whether the evidence actually supports the proposed claim strength.",
        "- Check whether the selected design and data diagnostics match the project intent.",
        "- Check whether any forced overrides, stale tasks, or missing provenance should block approval.",
        "",
        "## Human Actions",
        "",
        f"- Approve: `aeros gate approve {target_gate} --stage {stage_label} --owner <name> --note <why>`",
        f"- Block: `aeros gate block {target_gate} --stage {stage_label} --owner <name> --reason <why>`",
        "- Revise: edit the relevant artifacts or task contracts, then rerun `aeros iterate`.",
        "- Stop: record the reason in `decisions/issue_log.csv` or the project log.",
        "",
    ])
    return "\n".join(lines)


def write_decision_packet(project_root: Path, target_gate: str, *, stage: str = "") -> Path:
    out_dir = project_root / "decisions" / "gates"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{target_gate}_decision_packet.md"
    path.write_text(build_decision_packet(project_root, target_gate, stage=stage), encoding="utf-8")
    return path
