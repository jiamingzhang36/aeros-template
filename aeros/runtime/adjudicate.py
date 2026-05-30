"""Deterministic design-selection / claim-adjudication engine.

The 'earn the claim' step of the empirical pipeline, done mechanically: given the
candidate designs (each with a structured viability_test + max_claim) and the
measured data diagnostics, it prunes non-viable designs, selects the
lowest-priority survivor, and sets the EARNED claim ceiling to that design's
max_claim. No agent: once conditions and diagnostics are structured, earning the
claim is a computation, not a judgment.

Writes discovery/design_selection.md. The claim ceiling RATCHETS DOWN to the
surviving design — if only the descriptive floor survives, the claim is
descriptive, regardless of the original ambition.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

OPTIONS = "discovery/design_options.md"
DIAGNOSTICS = "discovery/data_diagnostics.yml"
SELECTION = "discovery/design_selection.md"

# claim strength order, weakest -> strongest
CLAIM_ORDER = ["descriptive", "measurement", "associational", "causal"]
OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "always": lambda a, b: True,
}


def _front_matter(path: Path) -> dict:
    t = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, flags=re.S)
    if not m:
        return yaml.safe_load(t) or {}
    return yaml.safe_load(m.group(1)) or {}


def _evaluate(option: dict, diagnostics: dict) -> tuple[bool, str]:
    vt = option.get("viability_test") or {}
    metric = vt.get("metric", "always")
    op = vt.get("op", "always")
    threshold = vt.get("threshold", 0)
    if op == "always" or metric == "always":
        return True, "always viable"
    if metric not in diagnostics:
        return False, f"diagnostic '{metric}' not measured"
    value = diagnostics[metric]
    fn = OPS.get(op)
    if fn is None:
        return False, f"unknown op '{op}'"
    ok = fn(value, threshold)
    return ok, f"{metric}={value} {op} {threshold} -> {'PASS' if ok else 'FAIL'}"


def adjudicate(project_root: Path) -> dict:
    opts = _front_matter(project_root / OPTIONS).get("options", []) or []
    diag_doc = _front_matter(project_root / DIAGNOSTICS)
    diagnostics = diag_doc.get("diagnostics", {}) or {}
    diag_status = str(diag_doc.get("status", "stub"))

    evaluated = []
    for o in opts:
        if str(o.get("decision", "proposed")).strip().lower() == "drop":
            continue
        viable, reason = _evaluate(o, diagnostics)
        evaluated.append({
            "id": o.get("id"), "name": o.get("name"), "priority": o.get("priority", 999),
            "max_claim": o.get("max_claim", "descriptive"),
            "is_floor": bool(o.get("is_fallback_floor", False)),
            "viable": viable, "reason": reason,
        })

    viable = [e for e in evaluated if e["viable"]]
    selected = min(viable, key=lambda e: e["priority"]) if viable else None
    earned_claim = selected["max_claim"] if selected else None

    # what was ratcheted down: the strongest max_claim among pruned higher-priority designs
    pruned_stronger = [e for e in evaluated if not e["viable"]
                       and CLAIM_ORDER.index(e["max_claim"]) > (
                           CLAIM_ORDER.index(earned_claim) if earned_claim else -1)]

    return {
        "diag_status": diag_status, "evaluated": evaluated,
        "selected": selected, "earned_claim": earned_claim,
        "ratcheted_from": [e["id"] for e in pruned_stronger],
    }


def write_selection(project_root: Path, result: dict) -> Path:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sel = result["selected"]
    lines = [
        "---",
        "status: filled",
        f"diagnostics_status: {result['diag_status']}",
        f"selected_design: {sel['id'] if sel else 'none'}",
        f"earned_claim_ceiling: {result['earned_claim'] or 'none'}",
        f"ratcheted_from: {result['ratcheted_from']}",
        "---",
        "# Design Selection / Claim Adjudication",
        "",
        f"Adjudicated: {now}",
        "",
        ("> NOTE: diagnostics are STUBBED — this selection does not earn a real "
         "claim until data_diagnostics.yml status is 'measured'."
         if result["diag_status"] != "measured" else
         "Diagnostics are measured; this selection earns the claim ceiling below."),
        "",
        "## Candidate adjudication",
        "",
        "| Priority | Design | Max claim | Viable? | Why |",
        "| --- | --- | --- | --- | --- |",
    ]
    for e in sorted(result["evaluated"], key=lambda x: x["priority"]):
        mark = "✓" if e["viable"] else "✗"
        lines.append(f"| {e['priority']} | {e['id']} {e['name']} | {e['max_claim']} | {mark} | {e['reason']} |")
    lines += [
        "",
        "## Selected design",
        "",
        (f"**{sel['id']} — {sel['name']}** (lowest-priority viable design)." if sel
         else "No viable design (not even a floor)."),
        "",
        "## Earned claim ceiling",
        "",
        (f"**{result['earned_claim']}** — the claim may not exceed this. "
         + (f"Ratcheted DOWN from the stronger ambition of {', '.join(result['ratcheted_from'])} "
            "(pruned by the data)." if result["ratcheted_from"] else "No stronger design was pruned.")
         if sel else "No claim is earned."),
        "",
    ]
    path = project_root / SELECTION
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
