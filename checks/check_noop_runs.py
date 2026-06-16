#!/usr/bin/env python3
"""Detect completed tasks that look like no-op completions."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.contract import load_contract  # noqa: E402
from aeros.runtime.skill_receipt import receipt_path  # noqa: E402
from aeros.runtime.state import load_state  # noqa: E402

PLACEHOLDER_MARKERS = {"placeholder", "todo", "tbd", "template", "fill me", "lorem ipsum"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _is_substantive(path: Path) -> bool:
    if not path.exists() or path.is_dir():
        return False
    if path.stat().st_size == 0:
        return False
    if path.stat().st_size > 1024 * 1024:
        return True
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return False
    lowered = text.lower()
    nonempty = [line.strip() for line in text.splitlines() if line.strip()]
    if len(nonempty) <= 2 and any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return False
    return True


def _contracts(root: Path) -> dict[str, tuple[Any, Path]]:
    out = {}
    for path in sorted((root / "tasks").rglob("*.yml")):
        try:
            contract = load_contract(path)
        except Exception:
            continue
        out[contract.task_id] = (contract, path)
    return out


def main() -> int:
    root = Path.cwd()
    state = load_state(root)
    contracts = _contracts(root)
    failures: list[str] = []
    for task_id, entry in sorted((state.get("tasks") or {}).items()):
        if entry.get("status") != "passed" or task_id not in contracts:
            continue
        contract, _path = contracts[task_id]
        outputs = [p for p in contract.allowed_outputs if p and p != "agent_runs"]
        if outputs and not any(_is_substantive(root / p) for p in outputs):
            failures.append(f"{task_id}: passed but no substantive allowed output exists")
        sr = receipt_path(root, task_id)
        if sr.exists():
            payload = _load_yaml(sr)
            rec = [s for s in (contract.recommended_skills or []) if s]
            req = [s for s in (getattr(contract, "required_skill_classes", []) or []) if s]
            waivers = payload.get("skill_waivers") or []
            if (rec or req) and not payload.get("skills_used") and not waivers:
                failures.append(f"{task_id}: passed with recommended/required skills but no skill invocation or waiver")
    if failures:
        print("FAIL: possible no-op task completions detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: no passed task appears to be a no-op")
    return 0


if __name__ == "__main__":
    sys.exit(main())
