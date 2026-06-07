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
import csv

from . import state as state_mod

GATES = [f"G{i}" for i in range(14)]  # G0..G13


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


def _discover_contract_ids(project_root: Path) -> set[str]:
    ids: set[str] = set()
    from .contract import load_contract

    for path in sorted((project_root / "tasks").rglob("*.yml")):
        try:
            ids.add(load_contract(path).task_id)
        except Exception:  # noqa: BLE001
            continue
    return ids


def _result_rows(project_root: Path) -> list[dict[str, str]]:
    path = project_root / "evidence" / "result_index.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("result_id", "").strip()]


def _claim_rows(project_root: Path) -> list[dict[str, str]]:
    path = project_root / "evidence" / "claim_registry.md"
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| C") or line.startswith("| Claim ID"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        rows.append({
            "claim_id": cells[0],
            "claim": cells[1],
            "type": cells[2],
            "status": cells[3],
            "evidence_ids": cells[4],
            "result_ids": cells[5],
            "boundary": cells[6],
            "approved": cells[7],
        })
    return rows


def _protocol_summary(project_root: Path) -> tuple[dict[str, Any], str]:
    path = project_root / "execution" / "protocol" / "main_execution_protocol.md"
    if not path.exists():
        return {}, ""
    text = path.read_text(encoding="utf-8")
    fm = _front_matter(path)
    match = re.search(r"^## Claim Boundary\n(?P<body>.*?)(?=^## |\Z)", text, flags=re.S | re.M)
    boundary = match.group("body").strip().replace("\n", " ") if match else ""
    return fm, boundary


def _evidence_overview(project_root: Path, state: dict[str, Any], target_gate: str) -> list[str]:
    lines: list[str] = ["## Evidence Overview", ""]

    contract_ids = _discover_contract_ids(project_root)
    tasks = state.get("tasks", {}) or {}
    passed = sorted(task_id for task_id, entry in tasks.items() if entry.get("status") == "passed")
    stale_state = sorted(task_id for task_id in tasks if task_id not in contract_ids)
    if passed:
        lines.extend(["### Passed Runtime Tasks", ""])
        for task_id in passed:
            suffix = " (no current contract)" if task_id in stale_state else ""
            lines.append(f"- {task_id}{suffix}")
        lines.append("")
    if stale_state:
        lines.extend([
            "### State Hygiene",
            "",
            "The state contains task entries whose contracts no longer exist:",
            "",
        ])
        for task_id in stale_state:
            lines.append(f"- {task_id}")
        lines.extend(["", "Run `aeros state prune` if these are historical artifacts.", ""])

    protocol_fm, boundary = _protocol_summary(project_root)
    if protocol_fm or boundary:
        lines.extend(["### Execution Protocol", ""])
        lines.append(f"- Status: {protocol_fm.get('status', 'unknown')}")
        ceiling = (protocol_fm.get('claim_ceiling')
                   or protocol_fm.get('earned_claim_ceiling') or 'unknown')
        lines.append(f"- Claim ceiling: {ceiling}")
        result_ids = protocol_fm.get("result_ids") or []
        lines.append(f"- Planned result IDs: {', '.join(result_ids) if result_ids else '(none)'}")
        if boundary:
            lines.append(f"- Claim boundary: {boundary}")
        lines.append("")

    results = _result_rows(project_root)
    lines.extend(["### Registered Results", ""])
    if not results:
        lines.append("- None registered yet.")
    else:
        for row in results:
            notes = row.get("notes", "")
            lines.append(
                f"- {row.get('result_id')}: {row.get('description') or row.get('path')} "
                f"(`{row.get('path')}`; claims: {row.get('linked_claims') or 'none'}"
                f"{'; ' + notes if notes else ''})"
            )
    lines.append("")

    claims = _claim_rows(project_root)
    lines.extend(["### Claim Registry Summary", ""])
    if not claims:
        lines.append("- No claims registered yet.")
    else:
        for row in claims:
            lines.append(
                f"- {row['claim_id']} [{row['type']}, {row['status']}, approved={row['approved']}]: "
                f"{row['claim']} Boundary: {row['boundary']}"
            )
    lines.append("")

    if _gate_rank(target_gate) >= _gate_rank("G4"):
        lines.extend([
            "### Gate-Specific Review Focus",
            "",
            "- Confirm whether this is smoke execution or final empirical execution.",
            "- Confirm every registered result has provenance and a bounded claim.",
            "- Confirm draft claims are not being treated as supported manuscript claims.",
            "",
        ])
    return lines


def _critic_overview(state: dict[str, Any]) -> list[str]:
    """Surface independent-critic verdicts so the human gate sees flagged tasks."""
    tasks = state.get("tasks", {}) or {}
    flagged = []
    for task_id, entry in tasks.items():
        critic = (entry or {}).get("critic")
        if isinstance(critic, dict) and critic.get("verdict") in {"concerns", "unverified"}:
            flagged.append((task_id, critic))
    if not flagged:
        return []
    lines = ["## Independent Critic Findings", "",
             "An independent critic pass (separate from the worker) flagged these. "
             "It is advisory — confirm or dismiss each before approving:", ""]
    for task_id, critic in sorted(flagged):
        modes = ", ".join(critic.get("concern_modes") or []) or "unverified"
        block = " [BLOCKING]" if critic.get("blocking") else ""
        report = critic.get("report", "")
        lines.append(f"- {task_id}: {critic.get('verdict')}{block} — {modes}"
                     + (f" (see {report})" if report else ""))
    lines.append("")
    return lines


# Judgment artifacts whose actual CONTENT a human should read at a gate — not
# just whether a check passed. Surfacing excerpts here systematizes the "read the
# substance" review (it is how a human catches hollow/placeholder content that a
# presence-check waves through).
_EXCERPT_ARTIFACTS = [
    ("Research question / idea", "discovery/idea_memo.md", 25),
    ("Anchor (4 components)", "discovery/anchor.yml", 14),
    ("Design selection (adjudicated)", "discovery/design_selection.md", 22),
    ("Method card", "docs/method_card.md", 45),
    ("Variable construction", "discovery/variable_construction.md", 30),
]


def _artifact_excerpts(project_root: Path) -> list[str]:
    blocks: list[str] = []
    for label, rel, max_lines in _EXCERPT_ARTIFACTS:
        p = project_root / rel
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        excerpt = raw[:max_lines]
        truncated = len(raw) > max_lines
        # Use a fence longer than any backtick run in the excerpt, so artifacts
        # that themselves contain ``` code/yaml fences don't break the packet.
        longest_run = max((len(run) for run in re.findall(r"`+", "\n".join(excerpt))), default=0)
        fence = "`" * max(3, longest_run + 1)
        blocks.append(f"### {label} — `{rel}`")
        blocks.append("")
        blocks.append(fence)
        blocks.extend(excerpt)
        if truncated:
            blocks.append(f"... ({len(raw) - max_lines} more line(s); open the file)")
        blocks.append(fence)
        blocks.append("")
    if not blocks:
        return []
    return ["## Artifact Excerpts — read the substance, not just the PASS marks", "",
            "A check confirms a section *exists*; it cannot confirm it *says something*. "
            "Read these before approving — hollow, duplicated, or placeholder content here "
            "is a reason to block even when every check is green.", ""] + blocks


def _number_drift_overview(project_root: Path) -> list[str]:
    """Surface injected numbers whose source cell moved since the accepted lock."""
    try:
        from .number_drift import compute_drift
        drifts = compute_drift(project_root)
    except Exception:  # noqa: BLE001 - packet must never be fatal
        return []
    moved = [d for d in drifts if d.moved]
    unresolved = [d for d in drifts if d.status == "unresolved"]
    if not moved and not unresolved:
        return []
    lines = [
        "## Injected-Number Drift — a result moved since last accepted",
        "",
        "These paper numbers are sourced from result cells that changed (or no "
        "longer resolve) versus `paper/numbers.lock.yml`. A moved coefficient can "
        "invalidate the surrounding prose. Review, then accept with "
        "`aeros number drift --update`.",
        "",
    ]
    for d in moved:
        if d.status == "changed":
            lines.append(f"- CHANGED `{d.name}`: {d.baseline} → {d.current}")
        else:
            lines.append(f"- NEW `{d.name}`: {d.current} (not yet locked)")
    for d in unresolved:
        lines.append(f"- UNRESOLVED `{d.name}`: {d.detail}")
    lines.append("")
    return lines


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

    lines.extend(_evidence_overview(project_root, state, target_gate))

    lines.extend(_critic_overview(state))

    lines.extend(_artifact_excerpts(project_root))

    lines.extend(_number_drift_overview(project_root))

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
