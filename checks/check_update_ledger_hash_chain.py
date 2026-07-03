#!/usr/bin/env python3
"""Validate the local update-ledger hash chain."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("FAIL: PyYAML is required for check_update_ledger_hash_chain.py") from exc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.ledger_hash_chain import canonical_record_hash, validate_chain  # noqa: E402


ROOT = Path.cwd()
POLICY = ROOT / "harness/update_ledger_hash_chain_policy.yml"
CHAIN = ROOT / "decisions/update_ledger_chain.jsonl"


def _git_show_head_chain() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{CHAIN.as_posix()}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None


def main() -> int:
    failures: list[str] = []
    if not POLICY.exists():
        failures.append("missing harness/update_ledger_hash_chain_policy.yml")
    else:
        data = yaml.safe_load(POLICY.read_text(encoding="utf-8")) or {}
        for key in ["policy", "chain_file", "record_required_fields", "protected_subjects", "does_not_prove"]:
            if not data.get(key):
                failures.append(f"{POLICY}: missing {key}")
        required = set(data.get("record_required_fields") or [])
        expected = {"version", "seq", "entry_id", "subject", "subject_sha256", "prev_hash", "payload", "entry_hash"}
        missing = expected - required
        if missing:
            failures.append(f"{POLICY}: record_required_fields missing {', '.join(sorted(missing))}")
        if "scientific validity" not in (data.get("does_not_prove") or []):
            failures.append(f"{POLICY}: does_not_prove missing scientific-validity boundary")

    result = validate_chain(ROOT, CHAIN)
    failures.extend(result.failures)

    if CHAIN.exists():
        current_text = CHAIN.read_text(encoding="utf-8")
        head_text = _git_show_head_chain()
        if head_text:
            normalized_head = head_text if head_text.endswith("\n") else head_text + "\n"
            if not current_text.startswith(normalized_head):
                failures.append(
                    "ledger chain is not append-only relative to HEAD; current file must preserve HEAD as a prefix"
                )
        records = [
            json.loads(raw)
            for raw in current_text.splitlines()
            if raw.strip()
        ]
        if records:
            latest = records[-1]
            recomputed = canonical_record_hash(latest)
            if recomputed != latest.get("entry_hash"):
                failures.append("latest ledger-chain record cannot be independently recomputed")
            payload = latest.get("payload") or {}
            if "does_not_prove" not in payload:
                failures.append("latest ledger-chain payload lacks does_not_prove boundary")

    if failures:
        print("FAIL: update ledger hash-chain check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: update ledger hash chain is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
