"""Keep the provenance layer in sync with the result index.

Rigor gap this closes: result_index.csv can be appended by hand (or by a real
pipeline) faster than the provenance layer is written, so check_provenance drifts
into failure even though the artifacts are real. Registration and provenance must
move together. `sync_provenance` derives a provenance record per registered
result -- output_path, created_at, script_or_source, sha256 -- straight from the
index and the artifact on disk, so the two layers cannot silently diverge.

It never invents results: it only writes provenance for index rows whose file
exists, and it recomputes sha256 from the actual bytes.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

RESULT_INDEX = Path("evidence/result_index.csv")
PROVENANCE_DIR = Path("outputs/.provenance")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sync_provenance(project_root: Path) -> tuple[list[str], list[str]]:
    """Write/refresh one provenance JSON per registered result with an existing file.

    Returns (written_result_ids, skipped_messages).
    """
    index = project_root / RESULT_INDEX
    written: list[str] = []
    skipped: list[str] = []
    if not index.exists():
        return written, [f"missing {RESULT_INDEX}"]

    prov_dir = project_root / PROVENANCE_DIR
    prov_dir.mkdir(parents=True, exist_ok=True)

    with index.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rid = (row.get("result_id") or "").strip()
            rel = (row.get("path") or "").strip()
            if not rid or not rel:
                continue
            artifact = project_root / rel
            if not artifact.exists() or not artifact.is_file():
                skipped.append(f"{rid}: artifact missing, no provenance written ({rel})")
                continue
            created_at = (row.get("created_date") or "").strip()
            if not created_at:
                created_at = datetime.fromtimestamp(
                    artifact.stat().st_mtime, tz=timezone.utc
                ).isoformat()
            record = {
                "result_id": rid,
                "output_path": rel,
                "created_at": created_at,
                "script_or_source": (row.get("script_or_source") or "").strip()
                or "unknown (registered without script_or_source)",
                "sha256": _sha256(artifact),
                "synced_by": "aeros provenance sync",
            }
            (prov_dir / f"{rid}.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )
            written.append(rid)
    return written, skipped
