"""SHA256 artifact manifest for reproducibility/audit.

AutoResearchClaw ships "SHA256 checksums for all stage artifacts; immutable
manifests for verification". This is the same idea for AEROS: snapshot the
content hash of every registered result artifact so any later change is
detectable. Combined with the anti-fabrication check (numbers must trace to a
result) and check_output_reproducibility (a result must name its script), this
gives a tamper-evident chain from script -> artifact -> number in the paper.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

RESULT_INDEX = Path("evidence/result_index.csv")
MANIFEST = Path("evidence/artifact_manifest.json")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _registered_paths(project_root: Path) -> list[str]:
    index = project_root / RESULT_INDEX
    if not index.exists():
        return []
    out: list[str] = []
    with index.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            p = (row.get("path") or "").strip()
            if p:
                out.append(p)
    return out


def build_manifest(project_root: Path) -> tuple[Path, int]:
    """Hash every existing registered artifact and write the manifest."""
    entries = []
    for rel in _registered_paths(project_root):
        p = project_root / rel
        if p.exists() and p.is_file():
            entries.append({"path": rel, "sha256": _sha256(p), "size": p.stat().st_size})
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algorithm": "sha256",
        "artifacts": sorted(entries, key=lambda e: e["path"]),
    }
    out = project_root / MANIFEST
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out, len(entries)


def verify_manifest(project_root: Path) -> list[str]:
    """Return a list of drift problems; empty means every artifact matches."""
    out = project_root / MANIFEST
    if not out.exists():
        return []
    data = json.loads(out.read_text(encoding="utf-8")) or {}
    problems: list[str] = []
    for entry in data.get("artifacts", []) or []:
        rel = entry.get("path", "")
        p = project_root / rel
        if not p.exists():
            problems.append(f"{rel}: in manifest but missing on disk")
            continue
        actual = _sha256(p)
        if actual != entry.get("sha256"):
            problems.append(f"{rel}: sha256 changed since manifest "
                            f"({entry.get('sha256','')[:12]}.. -> {actual[:12]}..)")
    return problems
