"""Drift report: surface when an injected number's source cell moved (C).

A2 catches the case where the paper value disagrees with the data *right now*.
But once you update numbers.yml to match, the change is invisible -- and a moved
coefficient may quietly invalidate the prose around it. Phase C records the
accepted cell value in a lock file (paper/numbers.lock.yml) and, on every later
run, compares the current cell value to that baseline so "republican_any_pp:
3.83 -> 3.91 (data moved)" appears in the gate decision packet instead of being
caught (or missed) by eye.

The lock is advanced only by an explicit human action (`aeros number drift
--update`), the same way you accept a refreshed dependency lock.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .number_injection import load_numbers, read_cell_value

LOCK = Path("paper/numbers.lock.yml")
ACCEPT_LOG = Path("decisions/number_acceptances.csv")


@dataclass
class Drift:
    name: str
    status: str          # "new" | "unchanged" | "changed" | "unresolved"
    baseline: float | None
    current: float | None
    detail: str = ""

    @property
    def moved(self) -> bool:
        return self.status in {"new", "changed"}


def load_lock(project_root: Path) -> dict[str, float]:
    path = project_root / LOCK
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    cells = data.get("cells", data) if isinstance(data, dict) else {}
    out: dict[str, float] = {}
    if isinstance(cells, dict):
        for k, v in cells.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
    return out


def compute_drift(project_root: Path, registry: dict | None = None) -> list[Drift]:
    if registry is None:
        registry = load_numbers(project_root)
    baseline = load_lock(project_root)
    drifts: list[Drift] = []
    for name, spec in registry.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("source"), dict):
            continue
        current, detail = read_cell_value(project_root, spec)
        if current is None:
            drifts.append(Drift(name, "unresolved", baseline.get(name), None, detail))
            continue
        if name not in baseline:
            drifts.append(Drift(name, "new", None, current))
        elif abs(baseline[name] - current) > 1e-9:
            drifts.append(Drift(name, "changed", baseline[name], current))
        else:
            drifts.append(Drift(name, "unchanged", baseline[name], current))
    return drifts


def write_lock(project_root: Path, registry: dict | None = None) -> Path:
    """Snapshot the current cell value of every cell-sourced entry into the lock."""
    if registry is None:
        registry = load_numbers(project_root)
    cells: dict[str, float] = {}
    for name, spec in registry.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("source"), dict):
            continue
        current, _ = read_cell_value(project_root, spec)
        if current is not None:
            cells[name] = current
    path = project_root / LOCK
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# Accepted source-cell values for injected numbers (Phase C drift lock).\n"
        "# Advance only via `aeros number drift --update` after reviewing changes.\n"
        "cells:\n"
        + "".join(f"  {name}: {value!r}\n" for name, value in sorted(cells.items()))
    )
    path.write_text(body, encoding="utf-8")
    return path


def unaccepted(project_root: Path, registry: dict | None = None) -> list[Drift]:
    """Drifts that a human must resolve before a gate can pass: moved or unresolved."""
    return [d for d in compute_drift(project_root, registry)
            if d.moved or d.status == "unresolved"]


def record_acceptance(project_root: Path, drifts: list[Drift],
                      owner: str, note: str = "") -> Path:
    """Append an append-only audit row per accepted change (who/when/old->new)."""
    path = project_root / ACCEPT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    ts = datetime.now(tz=timezone.utc).isoformat()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if fresh:
            writer.writerow(["accepted_at", "owner", "note", "name", "old", "new"])
        for d in drifts:
            if d.moved:
                writer.writerow([
                    ts, owner, note, d.name,
                    "" if d.baseline is None else d.baseline, d.current,
                ])
    return path


def format_drift(drifts: list[Drift], only_moved: bool = False) -> str:
    rows = [d for d in drifts if d.moved or d.status == "unresolved"] if only_moved else drifts
    if not rows:
        return "no injected-number drift vs lock"
    lines: list[str] = []
    for d in sorted(rows, key=lambda x: (x.status != "changed", x.name)):
        if d.status == "changed":
            lines.append(f"  CHANGED  {d.name}: {d.baseline} -> {d.current}")
        elif d.status == "new":
            lines.append(f"  NEW      {d.name}: {d.current} (not yet in lock)")
        elif d.status == "unresolved":
            lines.append(f"  UNRESOLVED {d.name}: {d.detail}")
        else:
            lines.append(f"  ok       {d.name}: {d.current}")
    return "\n".join(lines)
