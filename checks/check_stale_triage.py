#!/usr/bin/env python3
"""Validate deterministic stale triage plumbing."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeros.runtime.stale_triage import (  # noqa: E402
    BUCKETS,
    _cap_propagated_impact,
    _classify,
    _output_claim_impact,
    _propagate_descendant_claims,
    format_stale_triage,
    triage_stale_tasks,
)


def main() -> int:
    failures: list[str] = []
    policy_path = ROOT / "harness/stale_triage_policy.yml"
    if not policy_path.exists():
        failures.append("missing harness/stale_triage_policy.yml")
    else:
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        buckets = set((data.get("buckets") or {}).keys())
        if buckets != BUCKETS:
            failures.append(f"policy buckets mismatch: {sorted(buckets)}")
        text = policy_path.read_text(encoding="utf-8").lower()
        for marker in ["no llm", "deterministic", "must not mark tasks stale", "must not"]:
            if marker not in text:
                failures.append(f"policy missing boundary marker {marker!r}")
    try:
        result = triage_stale_tasks(ROOT, stage="discovery", lane="")
        rendered = format_stale_triage(result)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"stale triage failed: {exc}")
        result = None
        rendered = ""
    if result is not None:
        for item in result.items:
            if item.bucket not in BUCKETS:
                failures.append(f"{item.task_id}: invalid bucket {item.bucket}")
            if item.bucket == "rerun_required" and "--dry-run" not in item.command:
                failures.append(f"{item.task_id}: rerun_required command must be dry-run")
            if item.bucket == "revalidate_free" and " recover " not in f" {item.command} " and "--check" not in item.command:
                failures.append(f"{item.task_id}: revalidate_free command must use recover --check")
            if item.bucket == "suppress_as_irrelevant" and item.command.lower() != "no action":
                failures.append(f"{item.task_id}: suppressed stale item must not execute anything")
            if item.bucket == "suppress_as_irrelevant" and (item.frontier_connected or item.output_changed):
                failures.append(f"{item.task_id}: suppressed item is not proven irrelevant")
            if item.claim_bound and item.impact_level != "high":
                failures.append(f"{item.task_id}: claim-bound stale item must be high impact")
            if item.impact_scope == "paper_global_review" and item.impacted_claims:
                failures.append(f"{item.task_id}: paper-global review must not invent impacted claims")
            if item.volatile_only_outputs and item.bucket == "rerun_required":
                failures.append(f"{item.task_id}: volatile-only outputs must not require provider/API rerun")
    fake_links = {
        "active_claims": ["C001", "C002", "C003"],
        "result_to_claims": {"R001": {"C001"}},
        "result_paths": [("R001", "paper/tables/table1.csv", "code/make_table1.py")],
        "evidence_to_claims": {"E002": {"C002"}},
        "evidence_paths": [("E002", "data/processed/evidence_snapshot.csv")],
    }
    claim_bound, impacted, scope = _output_claim_impact(["paper/draft.md"], fake_links)
    if claim_bound or impacted or scope != "paper_global_review":
        failures.append("paper artifact without deterministic claim link must be paper_global_review only")
    claim_bound, impacted, scope = _output_claim_impact(["paper/tables/table1.csv"], fake_links)
    if not claim_bound or impacted != ["C001"] or scope != "specific_claims":
        failures.append(f"paper result path should localize only C001, got scope={scope} impacted={impacted}")
    claim_bound, impacted, scope = _output_claim_impact(["evidence/claim_registry.md"], fake_links)
    if not claim_bound or impacted or scope != "claim_registry_unknown":
        failures.append("claim registry changes must be high-risk unknown scope, not all active claims")
    # v3 registrar edge: a result-registry writer resolves to the concrete claims
    # its registry links, even when its allowed_outputs don't path-match the
    # per-result artifact paths (the CMPD coarse-output case).
    claim_bound, impacted, scope = _output_claim_impact(["evidence/result_index.csv"], fake_links)
    if not claim_bound or impacted != ["C001"] or scope != "specific_claims":
        failures.append(f"result-registry writer should resolve linked claims, got scope={scope} impacted={impacted}")
    # Conservative fallback: when the registry links no claims, stay registry_unknown
    # (high but unscoped) rather than collapsing to none.
    empty_links = {
        "active_claims": ["C001"],
        "result_to_claims": {},
        "result_paths": [],
        "evidence_to_claims": {},
        "evidence_paths": [],
    }
    claim_bound, impacted, scope = _output_claim_impact(["evidence/result_index.csv"], empty_links)
    if not claim_bound or impacted or scope != "registry_unknown":
        failures.append(f"empty result registry must stay registry_unknown, got scope={scope} impacted={impacted}")
    # v3 Phase 2: depth-1 descendant propagation + over-attribution cap.
    from types import SimpleNamespace  # noqa: PLC0415
    fake_contracts = {
        "PROD": (SimpleNamespace(allowed_outputs=["evidence/result_index.csv"], depends_on=["UP"]), None),
        "SUBSET": (SimpleNamespace(allowed_outputs=["paper/tables/table1.csv"], depends_on=["UP2"]), None),
    }
    direct = {"UP": {"PROD"}, "UP2": {"SUBSET"}, "PROD": set(), "SUBSET": set()}
    claims, srcs = _propagate_descendant_claims("UP", fake_contracts, direct, fake_links)
    if claims != {"C001"} or srcs != ["PROD"]:
        failures.append(f"depth-1 propagation should inherit producer claims, got {claims} from {srcs}")
    # A task whose direct dependent has no specific scope must not propagate.
    no_prop, no_srcs = _propagate_descendant_claims("PROD", fake_contracts, direct, fake_links)
    if no_prop or no_srcs:
        failures.append(f"leaf producer must not propagate, got {no_prop} from {no_srcs}")
    # Cap: a genuine subset stays specific; covering all active claims downgrades.
    imp, sc = _cap_propagated_impact({"C001"}, {"C001", "C002", "C003"})
    if imp != ["C001"] or sc != "specific_claims":
        failures.append(f"subset propagation must stay specific, got {sc} {imp}")
    imp, sc = _cap_propagated_impact({"C001", "C002"}, {"C001", "C002"})
    if imp or sc != "registry_unknown":
        failures.append(f"all-active propagation must downgrade to registry_unknown, got {sc} {imp}")
    imp, sc = _cap_propagated_impact(set(), {"C001"})
    if imp or sc != "none":
        failures.append(f"empty propagation must be none, got {sc} {imp}")
    bucket, _level, command = _classify(
        output_changed=True,
        volatile_only_outputs=True,
        frontier_connected=False,
        claim_bound=False,
        impacted_claims=[],
        impact_scope="none",
    )
    if bucket != "revalidate_free" or "recover" not in command or "--check" not in command:
        failures.append("volatile-only output changes must route to recover --check")
    bucket, _level, command = _classify(
        output_changed=False,
        volatile_only_outputs=False,
        frontier_connected=False,
        claim_bound=False,
        impacted_claims=[],
        impact_scope="none",
    )
    if bucket != "suppress_as_irrelevant" or command.lower() != "no action":
        failures.append(f"suppressed item command must be the no-op sentinel, got {command!r}")
    for marker in ["STALE_TRIAGE", "does_not_prove", "does not run agents"]:
        if marker not in rendered:
            failures.append(f"rendered stale triage missing {marker!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    count = len(result.items) if result is not None else 0
    print(f"PASS: stale triage is valid ({count} item(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
