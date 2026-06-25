#!/usr/bin/env python3
"""Validate progress domain/class semantics."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.completion import progress_domain_for  # noqa: E402


STATUS_POLICY = Path("harness/status_label_policy.yml")
COMPLETION_POLICY = Path("harness/completion_attestation_policy.yml")
TEMPLATE = Path("templates/completion_attestation.yml")


def _load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    failures: list[str] = []
    for path in [STATUS_POLICY, COMPLETION_POLICY, TEMPLATE]:
        if not path.exists():
            failures.append(f"missing {path}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    status = _load(STATUS_POLICY)
    labels = status.get("labels") or {}
    if "DECISION_RECORDED" not in labels:
        failures.append("status policy missing DECISION_RECORDED")
    final_rule = str((status.get("final_response_rule") or {}).get("instruction", ""))
    if "DECISION_RECORDED" not in final_rule:
        failures.append("final response rule must mention DECISION_RECORDED")

    completion = _load(COMPLETION_POLICY)
    minimal = set(completion.get("minimal_attestation_fields") or [])
    if "progress_domain" not in minimal:
        failures.append("completion policy missing progress_domain attestation field")
    domains = set(completion.get("progress_domains") or {})
    if not {"research", "runtime", "governance"}.issubset(domains):
        failures.append("completion policy missing required progress domains")
    classes = set(completion.get("progress_classes") or {})
    if "decision" not in classes:
        failures.append("completion policy missing decision progress class")
    labels_policy = completion.get("outcome_labels") or {}
    if "DECISION_RECORDED" not in labels_policy:
        failures.append("completion policy missing DECISION_RECORDED outcome label")
    decision_text = str(labels_policy.get("DECISION_RECORDED", "")).lower()
    if "not" not in decision_text or "substantive" not in decision_text:
        failures.append("DECISION_RECORDED must state that it is not research-substantive output")

    template = _load(TEMPLATE)
    if "progress_domain" not in template:
        failures.append("completion attestation template missing progress_domain")

    if progress_domain_for("harness", authority_status="no_new_authority") != "runtime":
        failures.append("harness lane should map to runtime progress_domain")
    if progress_domain_for("data", authority_status="no_new_authority") != "research":
        failures.append("data lane should map to research progress_domain")
    if progress_domain_for("claim", authority_status="human_decision_recorded") != "governance":
        failures.append("human_decision_recorded should map to governance progress_domain")

    if failures:
        print("FAIL: progress semantics problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: progress domain/class semantics are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
