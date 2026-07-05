"""Research graph builder, validator, and query helpers.

The graph is a derived index plus a narrow lane for human-gated assertions. It
must not become a parallel truth source: derived claim/evidence/result edges are
rebuilt from the registries, while human assertions are preserved and validated.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

GRAPH_PATH = Path("evidence/research_graph.yml")
CLAIM_REGISTRY = Path("evidence/claim_registry.md")
EVIDENCE_LEDGER = Path("evidence/evidence_ledger.csv")
RESULT_INDEX = Path("evidence/result_index.csv")
PROVENANCE_DIR = Path("outputs/.provenance")

FINAL_CLAIM_STATUSES = {"supported", "ambiguous", "unsupported"}
ACTIVE_CLAIM_STATUSES = {"draft", "supported", "ambiguous", "unsupported"}
HUMAN_NODE_TYPES = {"rq", "subquestion", "study", "unexplored_area", "paper_section"}

ASSERTION_SIGNATURES = {
    "rq_has_subquestion": ("rq", "subquestion"),
    "subquestion_has_study": ("subquestion", "study"),
    "study_has_result": ("study", "result"),
    "subquestion_has_unexplored_area": ("subquestion", "unexplored_area"),
    "claim_mentions_paper_section": ("claim", "paper_section"),
}

REQUIRED_ASSERTION_FIELDS = ("approved_by", "approved_at", "decision_ref", "notes")


def _sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def split_ids(value: str) -> list[str]:
    out: list[str] = []
    for item in re.split(r"[;,\s]+", value or ""):
        token = item.strip()
        if token and token.upper() not in {"TBD", "NA", "N/A", "NONE", "-"}:
            out.append(token)
    return out


def parse_claim_registry(root: Path) -> list[dict[str, Any]]:
    path = root / CLAIM_REGISTRY
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 8:
            continue
        if cells[0].lower() == "claim id" or set(cells[0]) <= set("-: "):
            continue
        rows.append({
            "claim_id": cells[0],
            "claim": cells[1],
            "type": cells[2].lower(),
            "status": cells[3].lower(),
            "evidence_ids": split_ids(cells[4]),
            "result_ids": split_ids(cells[5]),
            "boundary": cells[6],
            "approved": cells[7],
        })
    return rows


def load_sources(root: Path) -> dict[str, Any]:
    claims = parse_claim_registry(root)
    evidence_rows = _read_csv(root / EVIDENCE_LEDGER)
    result_rows = _read_csv(root / RESULT_INDEX)
    provenance: dict[str, dict[str, Any]] = {}
    provenance_hashes: dict[str, str] = {}
    prov_dir = root / PROVENANCE_DIR
    if prov_dir.exists():
        for path in sorted(prov_dir.glob("*.json")):
            provenance_hashes[str(path.relative_to(root))] = _sha256(path)
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            rid = str(rec.get("result_id", "")).strip()
            if rid:
                rec["_path"] = str(path.relative_to(root))
                provenance[rid] = rec
    return {
        "claims": claims,
        "evidence_rows": evidence_rows,
        "result_rows": result_rows,
        "provenance": provenance,
        "provenance_hashes": provenance_hashes,
    }


def _claim_ids(sources: dict[str, Any]) -> set[str]:
    return {row["claim_id"] for row in sources["claims"] if row.get("claim_id")}


def _evidence_ids(sources: dict[str, Any]) -> set[str]:
    return {row.get("evidence_id", "") for row in sources["evidence_rows"] if row.get("evidence_id")}


def _result_ids(sources: dict[str, Any]) -> set[str]:
    return {row.get("result_id", "") for row in sources["result_rows"] if row.get("result_id")}


def _edge(frm: str, to: str, typ: str, source_file: str) -> dict[str, str]:
    return {"from": frm, "to": to, "type": typ, "source": "derived", "source_file": source_file}


def _node(nid: str, typ: str, derived: bool = True) -> dict[str, Any]:
    return {"id": nid, "type": typ, "derived": derived}


def load_existing_graph(root: Path) -> dict[str, Any]:
    path = root / GRAPH_PATH
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def build_graph(root: Path, *, write: bool = True) -> tuple[Path, dict[str, Any], list[str]]:
    sources = load_sources(root)
    existing = load_existing_graph(root)
    human_assertions = existing.get("human_assertions") or []
    if not isinstance(human_assertions, list):
        human_assertions = []

    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    warnings: list[str] = []

    for claim in sources["claims"]:
        cid = claim["claim_id"]
        nodes[(cid, "claim")] = _node(cid, "claim")
        for eid in claim["evidence_ids"]:
            nodes[(eid, "evidence")] = _node(eid, "evidence")
            edges.append(_edge(cid, eid, "claim_supported_by_evidence", str(CLAIM_REGISTRY)))
        for rid in claim["result_ids"]:
            nodes[(rid, "result")] = _node(rid, "result")
            edges.append(_edge(cid, rid, "claim_supported_by_result", str(CLAIM_REGISTRY)))

    for row in sources["evidence_rows"]:
        eid = row.get("evidence_id", "")
        if not eid:
            continue
        nodes[(eid, "evidence")] = _node(eid, "evidence")
        src = row.get("source_or_path", "")
        if src:
            nodes[(src, "source_or_artifact")] = _node(src, "source_or_artifact")
            edges.append(_edge(eid, src, "evidence_points_to_source", str(EVIDENCE_LEDGER)))

    for row in sources["result_rows"]:
        rid = row.get("result_id", "")
        if not rid:
            continue
        nodes[(rid, "result")] = _node(rid, "result")
        artifact = row.get("path", "")
        if artifact:
            nodes[(artifact, "artifact")] = _node(artifact, "artifact")
            edges.append(_edge(rid, artifact, "result_has_artifact", str(RESULT_INDEX)))
        script = row.get("script_or_source", "")
        if script:
            nodes[(script, "script_or_source")] = _node(script, "script_or_source")
            edges.append(_edge(rid, script, "result_generated_by", str(RESULT_INDEX)))

    for rid, rec in sources["provenance"].items():
        prov_id = f"provenance:{rid}"
        nodes[(rid, "result")] = _node(rid, "result")
        nodes[(prov_id, "provenance")] = _node(prov_id, "provenance")
        edges.append(_edge(rid, prov_id, "result_has_provenance", rec.get("_path", str(PROVENANCE_DIR))))

    for assertion in human_assertions:
        typ = str(assertion.get("type", ""))
        frm_type, to_type = ASSERTION_SIGNATURES.get(typ, ("", ""))
        frm = str(assertion.get("from", "")).strip()
        to = str(assertion.get("to", "")).strip()
        if frm and frm_type in HUMAN_NODE_TYPES:
            nodes[(frm, frm_type)] = _node(frm, frm_type, derived=False)
        if to and to_type in HUMAN_NODE_TYPES:
            nodes[(to, to_type)] = _node(to, to_type, derived=False)

    graph = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "derived_from": {
            "claim_registry_sha256": _sha256(root / CLAIM_REGISTRY),
            "evidence_ledger_sha256": _sha256(root / EVIDENCE_LEDGER),
            "result_index_sha256": _sha256(root / RESULT_INDEX),
            "provenance_files": sources["provenance_hashes"],
        },
        "nodes": sorted(nodes.values(), key=lambda n: (str(n["type"]), str(n["id"]))),
        "edges": sorted(edges, key=lambda e: (e["from"], e["type"], e["to"])),
        "human_assertions": human_assertions,
        "warnings": warnings,
    }
    if write:
        out = root / GRAPH_PATH
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(graph, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return out, graph, warnings
    return root / GRAPH_PATH, graph, warnings


def _pairs_from_claim_registry(sources: dict[str, Any], key: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for claim in sources["claims"]:
        for ref in claim[key]:
            pairs.add((claim["claim_id"], ref))
    return pairs


def _pairs_from_evidence_ledger(sources: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in sources["evidence_rows"]:
        eid = row.get("evidence_id", "")
        for cid in split_ids(row.get("claim_id", "")):
            if cid and eid:
                pairs.add((cid, eid))
    return pairs


def _pairs_from_result_index(sources: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in sources["result_rows"]:
        rid = row.get("result_id", "")
        for cid in split_ids(row.get("linked_claims", "")):
            if cid and rid:
                pairs.add((cid, rid))
    return pairs


def _derived_edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return (str(edge.get("from", "")), str(edge.get("to", "")), str(edge.get("type", "")))


def validate_graph(root: Path) -> list[str]:
    failures: list[str] = []
    graph_path = root / GRAPH_PATH
    sources = load_sources(root)
    graph = load_existing_graph(root)

    has_source_rows = bool(sources["claims"] or sources["evidence_rows"] or sources["result_rows"] or sources["provenance"])
    if not graph:
        if has_source_rows:
            return [f"missing {GRAPH_PATH}; run `aeros graph build`"]
        return []

    _, expected, _ = build_graph(root, write=False)
    expected_edges = {_derived_edge_key(e) for e in expected.get("edges", [])}
    actual_edges = {_derived_edge_key(e) for e in graph.get("edges", []) if e.get("source") == "derived"}
    missing_edges = expected_edges - actual_edges
    extra_edges = actual_edges - expected_edges
    for edge in sorted(missing_edges):
        failures.append(f"research_graph missing derived edge {edge}; run `aeros graph build`")
    for edge in sorted(extra_edges):
        failures.append(f"research_graph has stale derived edge {edge}; run `aeros graph build`")

    cr_evidence = _pairs_from_claim_registry(sources, "evidence_ids")
    ledger_evidence = _pairs_from_evidence_ledger(sources)
    for pair in sorted(cr_evidence - ledger_evidence):
        failures.append(f"claim/evidence drift: claim_registry links {pair[0]} -> {pair[1]} but evidence_ledger.claim_id does not")
    for pair in sorted(ledger_evidence - cr_evidence):
        failures.append(f"claim/evidence drift: evidence_ledger links {pair[0]} -> {pair[1]} but claim_registry Evidence ID(s) does not")

    cr_results = _pairs_from_claim_registry(sources, "result_ids")
    index_results = _pairs_from_result_index(sources)
    for pair in sorted(cr_results - index_results):
        failures.append(f"claim/result drift: claim_registry links {pair[0]} -> {pair[1]} but result_index.linked_claims does not")
    for pair in sorted(index_results - cr_results):
        failures.append(f"claim/result drift: result_index links {pair[0]} -> {pair[1]} but claim_registry Result ID(s) does not")

    result_ids = _result_ids(sources)
    provenance_ids = set(sources["provenance"].keys())
    for rid in sorted(provenance_ids - result_ids):
        failures.append(f"provenance/result_index drift: provenance has {rid} but result_index.csv does not")
    for rid in sorted(result_ids - provenance_ids):
        failures.append(f"provenance/result_index drift: result_index.csv has {rid} but provenance JSON is missing")

    result_by_id = {row.get("result_id", ""): row for row in sources["result_rows"] if row.get("result_id")}
    for rid in sorted(result_ids & provenance_ids):
        row = result_by_id[rid]
        rec = sources["provenance"][rid]
        if row.get("path") and rec.get("output_path") and row["path"] != rec["output_path"]:
            failures.append(f"provenance/result_index drift: {rid} path != output_path")
        if row.get("script_or_source") and rec.get("script_or_source") and row["script_or_source"] != rec["script_or_source"]:
            failures.append(f"provenance/result_index drift: {rid} script_or_source mismatch")

    failures.extend(validate_human_assertions(graph, sources))
    return failures


def validate_human_assertions(graph: dict[str, Any], sources: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    claims = _claim_ids(sources)
    evidence = _evidence_ids(sources)
    results = _result_ids(sources) | set(sources["provenance"].keys())
    node_ids_by_type: dict[str, set[str]] = defaultdict(set)

    for assertion in graph.get("human_assertions") or []:
        if not isinstance(assertion, dict):
            failures.append("human assertion is not a mapping")
            continue
        typ = str(assertion.get("type", ""))
        if typ not in ASSERTION_SIGNATURES:
            failures.append(f"human assertion has unsupported type '{typ}'")
            continue
        frm_type, to_type = ASSERTION_SIGNATURES[typ]
        frm = str(assertion.get("from", "")).strip()
        to = str(assertion.get("to", "")).strip()
        if not frm or not to:
            failures.append(f"human assertion {typ} missing from/to endpoint")
        for field in REQUIRED_ASSERTION_FIELDS:
            if not str(assertion.get(field, "")).strip():
                failures.append(f"human assertion {typ} {frm}->{to} missing required field '{field}'")
        node_ids_by_type[frm_type].add(frm)
        node_ids_by_type[to_type].add(to)
        if frm_type == "claim" and frm not in claims:
            failures.append(f"human assertion references unknown claim '{frm}'")
        if to_type == "claim" and to not in claims:
            failures.append(f"human assertion references unknown claim '{to}'")
        if frm_type == "result" and frm not in results:
            failures.append(f"human assertion references unknown result '{frm}'")
        if to_type == "result" and to not in results:
            failures.append(f"human assertion references unknown result '{to}'")
        if frm_type == "evidence" and frm not in evidence:
            failures.append(f"human assertion references unknown evidence '{frm}'")
        if to_type == "evidence" and to not in evidence:
            failures.append(f"human assertion references unknown evidence '{to}'")

    return failures


def _all_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return list(graph.get("edges") or []) + list(graph.get("human_assertions") or [])


def load_graph_for_query(root: Path) -> dict[str, Any]:
    graph = load_existing_graph(root)
    if graph:
        return graph
    return build_graph(root, write=False)[1]


def format_support(root: Path, claim_id: str) -> str:
    graph = load_graph_for_query(root)
    failures = validate_graph(root)
    claims = {row["claim_id"]: row for row in parse_claim_registry(root)}
    lines = [f"Support chain for {claim_id}"]
    if claim_id not in claims:
        return f"Support chain for {claim_id}\nMISSING: claim not found"
    lines.append(f"claim_status: {claims[claim_id].get('status', '')}")
    outgoing = [e for e in graph.get("edges", []) if e.get("from") == claim_id]
    if not outgoing:
        lines.append("MISSING: no evidence/result edges")
    for edge in outgoing:
        lines.append(f"- {edge['type']}: {edge['to']}")
        for child in graph.get("edges", []):
            if child.get("from") == edge.get("to"):
                lines.append(f"  - {child['type']}: {child['to']}")
    relevant = [f for f in failures if claim_id in f]
    if relevant:
        lines.append("problems:")
        lines.extend(f"- {f}" for f in relevant)
    else:
        lines.append("problems: none detected")
    return "\n".join(lines)


def format_impact(root: Path, target: str) -> str:
    graph = load_graph_for_query(root)
    edges = _all_edges(graph)
    reverse: dict[str, list[str]] = defaultdict(list)
    forward: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        frm = str(edge.get("from", ""))
        to = str(edge.get("to", ""))
        if frm and to:
            reverse[to].append(frm)
            forward[frm].append(to)

    starts = {target}
    for node in graph.get("nodes") or []:
        nid = str(node.get("id", ""))
        if nid == target or nid.endswith(target) or target.endswith(nid):
            starts.add(nid)

    seen = set(starts)
    q = deque(starts)
    while q:
        cur = q.popleft()
        for parent in reverse.get(cur, []):
            if parent not in seen:
                seen.add(parent)
                q.append(parent)

    node_type = {str(n.get("id", "")): str(n.get("type", "")) for n in graph.get("nodes") or []}
    claims = sorted(n for n in seen if node_type.get(n) == "claim" or re.match(r"^C\d+", n))
    studies = sorted(n for n in seen if node_type.get(n) in {"study", "subquestion", "rq"})
    sections: set[str] = set()
    for claim in claims:
        for child in forward.get(claim, []):
            if node_type.get(child) == "paper_section":
                sections.add(child)
    lines = [f"Impact query for {target}", "mode: observe-and-flag only; no claim status changed"]
    lines.append("review_needed_claims: " + (", ".join(claims) if claims else "none"))
    lines.append("review_needed_research_nodes: " + (", ".join(studies) if studies else "none"))
    lines.append("review_needed_sections: " + (", ".join(sorted(sections)) if sections else "none"))
    return "\n".join(lines)


def format_coverage(root: Path) -> str:
    graph = load_graph_for_query(root)
    assertions = graph.get("human_assertions") or []
    subquestions = {a.get("to") for a in assertions if a.get("type") == "rq_has_subquestion" and a.get("to")}
    if not subquestions:
        return "coverage unavailable: no asserted research tree"
    sq_to_studies: dict[str, set[str]] = defaultdict(set)
    study_to_results: dict[str, set[str]] = defaultdict(set)
    for a in assertions:
        if a.get("type") == "subquestion_has_study":
            sq_to_studies[str(a.get("from"))].add(str(a.get("to")))
        if a.get("type") == "study_has_result":
            study_to_results[str(a.get("from"))].add(str(a.get("to")))
    uncovered = []
    for sq in sorted(subquestions):
        studies = sq_to_studies.get(str(sq), set())
        results = {r for st in studies for r in study_to_results.get(st, set())}
        if not studies or not results:
            uncovered.append(str(sq))
    lines = ["Coverage query"]
    lines.append("uncovered_subquestions: " + (", ".join(uncovered) if uncovered else "none"))
    return "\n".join(lines)


def format_orphans(root: Path) -> str:
    graph = load_graph_for_query(root)
    sources = load_sources(root)
    claim_to_results = _pairs_from_claim_registry(sources, "result_ids")
    linked_results = {rid for _, rid in claim_to_results}
    all_results = _result_ids(sources)
    active_claims = [c for c in sources["claims"] if c.get("status") in ACTIVE_CLAIM_STATUSES]
    claims_without_support = [c["claim_id"] for c in active_claims if not c.get("evidence_ids") and not c.get("result_ids")]
    result_artifacts = {e.get("to") for e in graph.get("edges", []) if e.get("type") == "result_has_artifact" and e.get("from") in (all_results - linked_results)}
    lines = ["Orphans query", "mode: advisory only"]
    lines.append("orphan_results: " + (", ".join(sorted(all_results - linked_results)) if all_results - linked_results else "none"))
    lines.append("orphan_artifacts: " + (", ".join(sorted(str(x) for x in result_artifacts if x)) if result_artifacts else "none"))
    lines.append("active_claims_without_evidence_or_result: " + (", ".join(sorted(claims_without_support)) if claims_without_support else "none"))
    return "\n".join(lines)
