"""Make derived artifacts first-class: bind each to its sources by fingerprint.

A derived file (counts, pp transforms, reshaped tables) is only as trustworthy as
its freshness: if a source changes and the derived file is not regenerated, every
number injected from it silently goes stale. This module lets a generator stamp
its output with the sha256 of each source it read (`<output>.sources.json`), and
lets check_derived_fresh recompute those hashes to detect drift.

Contract: a generator calls stamp_sources(output, [sources], generator_name)
right after writing `output`. check_freshness then flags any derived whose
recorded source hash no longer matches the file on disk.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _sidecar_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".sources.json")


def stamp_sources(output: Path, sources: list[Path], generator: str) -> Path:
    """Record the sha256 of each source next to a freshly written derived file."""
    record = {
        "derived": str(output),
        "generator": generator,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "sources": [
            {"path": str(s), "sha256": _sha256(s) if s.exists() else None}
            for s in sources
        ],
    }
    sidecar = _sidecar_path(output)
    sidecar.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return sidecar


def check_freshness(project_root: Path, derived_dir: Path | None = None) -> list[str]:
    """Return a list of staleness problems across all *.sources.json sidecars."""
    base = derived_dir or (project_root / "evidence" / "derived")
    problems: list[str] = []
    if not base.exists():
        return problems
    for sidecar in sorted(base.glob("*.sources.json")):
        try:
            record = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{sidecar.name}: unreadable sidecar ({exc})")
            continue
        derived = project_root / record.get("derived", "")
        if not derived.exists():
            problems.append(f"{sidecar.name}: derived file missing ({record.get('derived')})")
        for src in record.get("sources", []):
            spath = project_root / src.get("path", "")
            if not spath.exists():
                problems.append(f"{sidecar.name}: source missing ({src.get('path')})")
                continue
            recorded = src.get("sha256")
            actual = _sha256(spath)
            if recorded is not None and recorded != actual:
                problems.append(
                    f"{sidecar.name}: source changed since generation -- regenerate "
                    f"{record.get('derived')} ({src.get('path')})"
                )
    return problems
