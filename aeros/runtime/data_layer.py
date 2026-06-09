"""Data-integrity layer: fetch official data, record provenance, reconcile.

Mirror of the number-integrity layer, applied to data acquisition (see
docs/data_layer_roadmap.md). The discipline is the same: every datum that enters
the project must trace to a source with a verifiable URL, a retrieval timestamp,
and a content hash -- so a value can be re-checked, not trusted on faith.

Hard rule: fetch() ALWAYS verifies TLS. A value pulled over an unverified
connection cannot be claimed as provenance from its named source, which defeats
the entire purpose. There is deliberately no "disable verification" option.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_INDEX = Path("evidence/data_index.csv")
PROVENANCE_DIR = Path("outputs/.data_provenance")
DATA_INDEX_COLS = ["data_id", "variable", "source", "source_url",
                   "output_path", "retrieved_at", "sha256", "note"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def fetch(url: str, *, timeout: int = 30, headers: dict | None = None) -> bytes:
    """HTTP(S) GET with TLS verification ALWAYS on. Returns raw bytes.

    Uses requests if available (verify=True is its default), else urllib with the
    default (verifying) SSL context. Never disables verification.
    """
    hdrs = {"User-Agent": "aeros-data-layer"} | (headers or {})
    try:
        import requests  # type: ignore
        resp = requests.get(url, timeout=timeout, headers=hdrs)  # verify=True default
        resp.raise_for_status()
        return resp.content
    except ImportError:
        import urllib.request
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as r:  # default ctx verifies
            return r.read()


def record_provenance(project_root: Path, data_id: str, *, source: str,
                      source_url: str, sha256: str, output_path: str | None = None,
                      retrieved_at: str | None = None, extra: dict | None = None) -> Path:
    """Write outputs/.data_provenance/<data_id>.json (mirror of result provenance)."""
    rec = {
        "data_id": data_id,
        "source": source,
        "source_url": source_url,
        "retrieved_at": retrieved_at or now_utc(),
        "sha256": sha256,
        "output_path": output_path or "",
        "tls_verified": True,
    }
    if extra:
        rec.update(extra)
    d = project_root / PROVENANCE_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{data_id}.json"
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return path


def register(project_root: Path, data_id: str, *, variable: str, source: str,
             source_url: str, sha256: str, output_path: str = "", note: str = "") -> Path:
    """Append/replace a row in evidence/data_index.csv (mirror of result_index)."""
    path = project_root / DATA_INDEX
    rows: list[dict] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("data_id") != data_id]
    rows.append({
        "data_id": data_id, "variable": variable, "source": source,
        "source_url": source_url, "output_path": output_path,
        "retrieved_at": now_utc(), "sha256": sha256, "note": note,
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DATA_INDEX_COLS)
        w.writeheader()
        w.writerows(rows)
    return path


def reconcile(api_value: float, project_value: float, *, rel_tol: float = 0.01
              ) -> tuple[bool, str]:
    """Compare a freshly-pulled value against the project's hand-built value.

    A mismatch is often a vintage/revision or 口径 (definition) difference, not a
    bug -- which is exactly the kind of thing the data layer should surface for a
    human, not silently paper over.
    """
    try:
        a, p = float(api_value), float(project_value)
    except (TypeError, ValueError):
        return False, f"non-numeric: api={api_value!r} project={project_value!r}"
    if p == 0:
        ok = a == 0
    else:
        ok = abs(a - p) / abs(p) <= rel_tol
    pct = (abs(a - p) / abs(p) * 100.0) if p else float("inf")
    detail = f"api={a} vs project={p} ({pct:.2f}% diff, tol {rel_tol*100:.0f}%)"
    if not ok:
        detail += " — likely vintage/revision or 口径 difference; review before use"
    return ok, detail
