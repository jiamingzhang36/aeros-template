#!/usr/bin/env python3
"""Validate the lightweight context graph layer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeros.runtime.context_graph import build_context_graph, format_context_graph  # noqa: E402


def main() -> int:
    failures: list[str] = []
    policy = ROOT / "harness/context_graph_policy.yml"
    if not policy.exists():
        failures.append("missing harness/context_graph_policy.yml")
    try:
        graph = build_context_graph(ROOT, lane="project")
        rendered = format_context_graph(graph)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"context graph generation failed: {exc}")
        graph = {}
        rendered = ""
    if graph:
        if graph.get("policy") != "AEROS-CONTEXT-GRAPH-001":
            failures.append("context graph has wrong policy marker")
        if not graph.get("nodes"):
            failures.append("context graph has no nodes")
        if not graph.get("edges"):
            failures.append("context graph has no edges")
        forbidden = {"supports", "claim_support", "approves", "downgrades"}
        for edge in graph.get("edges") or []:
            if edge.get("relation") in forbidden:
                failures.append(f"context graph uses research-authority relation {edge.get('relation')}")
    for marker in ["CONTEXT_GRAPH", "not the research evidence graph"]:
        if marker not in rendered:
            failures.append(f"rendered context graph missing {marker!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: context graph plumbing is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
