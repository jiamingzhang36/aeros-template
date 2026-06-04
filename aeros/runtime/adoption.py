"""Universal research intake/adoption for AEROS.

An idea, a memo file, or an existing project folder are all treated as an
initial research state. Adoption inventories that state, maps it to AEROS
artifacts, proposes a candidate gate, and leaves formal gate approval to humans.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import yaml

from .init_project import init_project
from .state import load_state, save_state


TEXT_SUFFIXES = {".md", ".txt", ".rst", ".csv", ".tsv", ".yml", ".yaml", ".json", ".py", ".r", ".do", ".jl"}
DOC_SUFFIXES = {".docx"}
PDF_SUFFIXES = {".pdf"}
DATA_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".dta", ".rds", ".feather"}
CODE_SUFFIXES = {".py", ".r", ".do", ".ipynb", ".jl", ".sql", ".sh"}
MAX_FILES = 400
MAX_TEXT_CHARS = 24000


@dataclass(frozen=True)
class AdoptionArgs:
    idea: str
    source: str
    target: str
    mode: str
    dry_run: bool
    deep: bool = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _gate_rank(gate: str) -> int:
    match = re.match(r"^G(\d+)$", str(gate).split()[0])
    return int(match.group(1)) if match else -1


def _slug(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (lowered[:60].strip("-") or "aeros-intake")


def _kind_for_path(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    parts = {p.lower() for p in path.parts}
    if suffix in PDF_SUFFIXES:
        return "pdf"
    if suffix in DOC_SUFFIXES:
        return "memo"
    if "table" in name or "figure" in name or "result" in name or "output" in parts or "outputs" in parts:
        return "result"
    if "draft" in name or "paper" in parts or "manuscript" in name:
        return "paper"
    if "license" in name or "irb" in name or "ethic" in name or "terms" in name or "compliance" in parts:
        return "compliance"
    if suffix in DATA_SUFFIXES or "data" in parts:
        return "data"
    if suffix in CODE_SUFFIXES or "code" in parts or "scripts" in parts:
        return "code"
    if "claim" in name or "hypothesis" in name:
        return "claim"
    if "method" in name or "design" in name or "identification" in name:
        return "method"
    if "literature" in name or "citation" in name or "bib" in name or "references" in name:
        return "literature"
    if suffix in TEXT_SUFFIXES:
        return "note"
    return "other"


def _read_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        words = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
        return "\n".join(words)[:MAX_TEXT_CHARS]
    except Exception:  # noqa: BLE001
        return ""


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in DOC_SUFFIXES:
        return _read_docx(path)
    if suffix in TEXT_SUFFIXES:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_CHARS]
        except Exception:  # noqa: BLE001
            return ""
    return ""


def _inventory(idea: str, source: Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if idea:
        rows.append({"path": "(idea)", "kind": "idea", "suffix": "", "size_bytes": len(idea.encode()), "readable": True})
    if source is None:
        return rows
    paths = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
    for path in paths[:MAX_FILES]:
        try:
            stat = path.stat()
        except OSError:
            continue
        suffix = path.suffix.lower()
        rows.append({
            "path": str(path),
            "kind": _kind_for_path(path),
            "suffix": suffix,
            "size_bytes": stat.st_size,
            "readable": suffix in TEXT_SUFFIXES or suffix in DOC_SUFFIXES,
        })
    return rows


def _sample_texts(idea: str, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    if idea:
        samples.append({"path": "(idea)", "kind": "idea", "text": idea})
    for row in rows:
        if row.get("path") == "(idea)" or not row.get("readable"):
            continue
        text = _extract_text(Path(str(row["path"])))
        if text.strip():
            samples.append({"path": str(row["path"]), "kind": str(row.get("kind", "note")), "text": text[:6000]})
        if sum(len(sample["text"]) for sample in samples) >= MAX_TEXT_CHARS:
            break
    return samples


def _deterministic_synthesis(samples: list[dict[str, str]], risk: str = "") -> dict[str, Any]:
    joined = "\n\n".join(sample["text"] for sample in samples)
    first_line = next((line.strip() for line in joined.splitlines() if line.strip()), "")
    preview = joined[:1200].strip()
    return {
        "engine": "deterministic",
        "available": False,
        "idea": first_line[:300],
        "research_question": "",
        "candidate_claims": [],
        "methods": [],
        "data_or_results": [],
        "risks": [risk or "Deep synthesis unavailable or disabled; human review required."],
        "missing_evidence": [],
        "source_preview": preview,
    }


def _codex_synthesis(samples: list[dict[str, str]]) -> dict[str, Any]:
    payload = {
        "instruction": (
            "Extract advisory research-state facts for AEROS intake. Return JSON only with keys: "
            "idea, research_question, candidate_claims, methods, data_or_results, risks, missing_evidence. "
            "Do not certify claims or gates."
        ),
        "samples": samples,
    }
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json", delete=False) as out:
        out_path = Path(out.name)
    try:
        subprocess.run(
            [
                "codex", "-a", "never", "exec", "--ephemeral", "--ignore-rules",
                "--sandbox", "read-only", "--output-last-message", str(out_path),
                json.dumps(payload, ensure_ascii=False),
            ],
            check=True,
            timeout=180,
            capture_output=True,
            text=True,
            # codex reads stdin; without EOF it hangs in unattended runs.
            stdin=subprocess.DEVNULL,
        )
        text = out_path.read_text(encoding="utf-8", errors="ignore").strip()
        match = re.search(r"\{.*\}", text, flags=re.S)
        data = json.loads(match.group(0) if match else text)
        if not isinstance(data, dict):
            raise ValueError("Codex synthesis did not return a JSON object")
        data["engine"] = "codex-cli"
        data["available"] = True
        data.setdefault("source_preview", "")
        return data
    except Exception as exc:  # noqa: BLE001
        return _deterministic_synthesis(samples, f"Codex synthesis unavailable: {exc}")
    finally:
        try:
            out_path.unlink()
        except OSError:
            pass


def _category_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        kind = str(row.get("kind", "other"))
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _candidate_gate(counts: dict[str, int], synthesis: dict[str, Any]) -> tuple[str, str]:
    gate = "G0"
    reason = "idea-only or insufficient mapped evidence"
    if counts.get("data") or counts.get("literature"):
        gate, reason = "G1", "data or literature assets found"
    if counts.get("method") or synthesis.get("methods"):
        gate, reason = "G3", "method/design signals found"
    if counts.get("code") and (counts.get("result") or synthesis.get("data_or_results")):
        gate, reason = "G6", "code and result signals found"
    if counts.get("claim"):
        gate, reason = "G7", "claim-like artifacts found"
    if counts.get("paper"):
        gate, reason = "G10", "paper/draft artifacts found"
    if counts.get("compliance"):
        gate, reason = "G13", "compliance/release artifacts found"
    return gate, reason


def _evidence_map(rows: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        kind = str(row.get("kind", "other"))
        artifacts.setdefault(kind, []).append({
            "source": row["path"],
            "confidence": "high" if kind in {"idea", "data", "code", "memo"} else "medium",
            "action": "review_required" if kind in {"claim", "result", "paper", "compliance"} else "link",
        })
    return {"artifacts": artifacts}


def _gap_plan(candidate_gate: str, counts: dict[str, int], synthesis: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    recommended: list[str] = []
    if counts.get("memo") and not synthesis.get("available"):
        missing.append("memo/docx deep review")
        recommended.append("rerun adoption with Codex deep synthesis or manually review extracted_drafts.md")
    if not counts.get("literature"):
        missing.append("literature registry / citation audit")
        recommended.append("run discovery literature tasks")
    if not counts.get("data"):
        missing.append("data inventory / diagnostics")
        recommended.append("run data scouting and data diagnostics")
    if not counts.get("method"):
        missing.append("method card / design selection")
        recommended.append("run design options and method card tasks")
    if _gate_rank(candidate_gate) >= _gate_rank("G6") and not counts.get("claim"):
        missing.append("formal claim registry")
        recommended.append("run result validation and claim audit")
    if not counts.get("compliance"):
        missing.append("compliance / release review")
        recommended.append("run compliance gate before public release")
    return {"candidate_gate": candidate_gate, "missing": missing, "recommended_next": recommended}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_inventory(path: Path, rows: list[dict[str, Any]], counts: dict[str, int]) -> None:
    lines = ["# Adoption Inventory", "", "## Summary", ""]
    for kind in sorted(counts):
        lines.append(f"- {kind}: {counts[kind]}")
    lines.extend(["", "## Files", ""])
    for row in rows:
        lines.append(f"- `{row['path']}` | kind={row['kind']} | suffix={row['suffix'] or '-'} | readable={row['readable']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_extracted(path: Path, synthesis: dict[str, Any]) -> None:
    lines = [
        "# Extracted Drafts",
        "",
        "These are advisory intake drafts. They do not update the formal claim registry or approve any gate.",
        "",
        f"- Engine: {synthesis.get('engine', 'unknown')}",
        f"- Available: {synthesis.get('available', False)}",
        "",
        "## Idea",
        "",
        str(synthesis.get("idea", "")),
        "",
        "## Research Question",
        "",
        str(synthesis.get("research_question", "")),
        "",
    ]
    if synthesis.get("source_preview"):
        lines.extend(["## Source Preview", "", str(synthesis.get("source_preview", "")), ""])
    for title, key in (
        ("Candidate Claims", "candidate_claims"),
        ("Methods", "methods"),
        ("Data / Results Signals", "data_or_results"),
        ("Risks", "risks"),
        ("Missing Evidence", "missing_evidence"),
    ):
        lines.extend([f"## {title}", ""])
        for item in synthesis.get(key, []) or []:
            lines.append(f"- {item}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_packet(path: Path, *, mode: str, source: str, candidate_gate: str,
                  reason: str, counts: dict[str, int], gap: dict[str, Any],
                  synthesis: dict[str, Any]) -> None:
    lines = [
        "# Adoption Packet",
        "",
        f"- Mode: {mode}",
        f"- Source: {source or '(idea-only)'}",
        f"- Candidate gate: {candidate_gate}",
        "- Formal current gate after adoption: G0",
        "- Gate status after adoption: open",
        f"- Candidate reason: {reason}",
        f"- Deep synthesis: {synthesis.get('engine', 'unknown')} / available={synthesis.get('available', False)}",
        "",
        "## Intake Interpretation",
        "",
    ]
    if counts.get("memo") and not synthesis.get("available"):
        lines.extend([
            "- Memo/docx material was found, but deep synthesis was unavailable or disabled.",
            "- AEROS kept the candidate gate conservative and requires human review of the source memo.",
            "- The source preview below is advisory only and does not satisfy any gate criterion.",
            "",
        ])
    elif synthesis.get("available"):
        lines.extend([
            "- Deep synthesis completed and produced advisory drafts.",
            "- Extracted claims/methods/results remain drafts until human review and formal checks.",
            "",
        ])
    else:
        lines.extend([
            "- Intake used deterministic inventory only.",
            "- Candidate gate is based on mapped file categories, not substantive certification.",
            "",
        ])
    if synthesis.get("source_preview"):
        lines.extend(["## Source Preview", "", str(synthesis.get("source_preview", ""))[:1200], ""])
    lines.extend([
        "## Inventory Summary",
        "",
    ])
    for kind in sorted(counts):
        lines.append(f"- {kind}: {counts[kind]}")
    lines.extend(["", "## Missing / Unreviewed Criteria", ""])
    for item in gap.get("missing", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Next Actions", ""])
    for item in gap.get("recommended_next", []):
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Human Gate Actions",
        "",
        "- Review this packet and extracted drafts.",
        "- Approve only gates whose criteria you have explicitly reviewed.",
        "- Do not treat candidate claims as supported claims until claim audit passes.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bootstrap_target(template_root: Path, target: Path) -> None:
    init_project(target)
    if template_root.resolve() == target.resolve():
        return
    for rel in ("tasks", "checks", "harness"):
        src = template_root / rel
        if src.exists():
            shutil.copytree(src, target / rel, dirs_exist_ok=True)
    for rel in (
        "project_manifest.yml",
        "AGENTS.md",
        "CLAUDE.md",
        "discovery/AGENTS.md",
        "discovery/literature/AGENTS.md",
        "execution/AGENTS.md",
    ):
        src = template_root / rel
        dst = target / rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _default_target(project_root: Path, idea: str, source: Path | None) -> Path:
    basis = idea or (source.stem if source and source.is_file() else source.name if source else "aeros-intake")
    return project_root / "validation_projects" / _slug(basis)


def run_adoption(project_root: Path, args: AdoptionArgs) -> int:
    if not args.idea and not args.source:
        print("FAIL: provide --idea or --from")
        return 1
    source = Path(args.source).expanduser().resolve() if args.source else None
    if source is not None and not source.exists():
        print(f"FAIL: source not found: {source}")
        return 1

    target = Path(args.target).expanduser() if args.target else _default_target(project_root, args.idea, source)
    if not target.is_absolute():
        target = (project_root / target).resolve()
    mode = args.mode
    if mode == "inplace":
        target = source if source and source.is_dir() else project_root

    rows = _inventory(args.idea, source)
    samples = _sample_texts(args.idea, rows)
    synthesis = _codex_synthesis(samples) if args.deep and samples else _deterministic_synthesis(samples)
    counts = _category_counts(rows)
    candidate_gate, reason = _candidate_gate(counts, synthesis)
    evidence = _evidence_map(rows)
    gap = _gap_plan(candidate_gate, counts, synthesis)

    print(f"[adopt] mode: {mode}")
    print(f"[adopt] target: {target}")
    print(f"[adopt] source: {source or '(idea-only)'}")
    print(f"[adopt] candidate gate: {candidate_gate} ({reason})")
    print("[adopt] formal current gate remains G0/open")
    if args.dry_run or mode == "readonly-audit":
        print("[adopt] dry-run/readonly: no files or state were written")
        return 0

    _bootstrap_target(project_root, target)
    adoption_dir = target / "adoption"
    _write_yaml(adoption_dir / "source_manifest.yml", {
        "adopted_at": _now(),
        "mode": mode,
        "source": str(source) if source else "",
        "source_type": "idea" if args.idea and not source else "file" if source and source.is_file() else "folder",
        "raw_data_copied": False,
        "formal_gate_approval": "not granted by adoption",
    })
    _write_inventory(adoption_dir / "inventory_report.md", rows, counts)
    _write_yaml(adoption_dir / "evidence_map.yml", evidence)
    _write_extracted(adoption_dir / "extracted_drafts.md", synthesis)
    _write_yaml(adoption_dir / "gap_plan.yml", gap)
    _write_packet(target / "decisions" / "adoption" / "adoption_packet.md",
                  mode=mode, source=str(source) if source else "", candidate_gate=candidate_gate,
                  reason=reason, counts=counts, gap=gap, synthesis=synthesis)

    idea_text = synthesis.get("idea") or args.idea
    if idea_text:
        idea_path = target / "discovery" / "idea_memo.md"
        idea_path.parent.mkdir(parents=True, exist_ok=True)
        idea_path.write_text("# Idea Memo\n\n## Starting Idea\n\n" + str(idea_text).strip() + "\n", encoding="utf-8")

    manifest_path = target / "project_manifest.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if not isinstance(manifest, dict):
        manifest = {}
    research = manifest.setdefault("research", {})
    if isinstance(research, dict):
        research["topic"] = str(idea_text or args.idea or (source.name if source else "Adopted research state"))[:120]
        research["one_sentence_question"] = str(synthesis.get("research_question") or idea_text or args.idea or "")
        research.setdefault("current_stage", "discovery")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")

    state = load_state(target)
    state["current_stage"] = "discovery"
    state["current_gate"] = "G0"
    state["gate_status"] = "open"
    state["candidate_stage"] = "execution" if _gate_rank(candidate_gate) >= _gate_rank("G4") else "discovery"
    state["candidate_gate"] = candidate_gate
    state.setdefault("tasks", {})
    state.setdefault("gate_history", [])
    state.setdefault("candidate_gate_history", []).append({
        "at": _now(),
        "stage": state["candidate_stage"],
        "gate": candidate_gate,
        "task_id": "adoption",
        "reason": reason,
    })
    state.setdefault("gate_decisions", [])
    state["adoption"] = {
        "mode": mode,
        "source": str(source) if source else "",
        "candidate_gate_reason": reason,
        "human_approval_required": True,
    }
    save_state(target, state)
    print(f"[adopt] wrote {adoption_dir.relative_to(target)}")
    print("[adopt] no gate was approved automatically")
    return 0
