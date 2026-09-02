#!/usr/bin/env python3
"""Exercise lawful full-text recovery on local fixtures without network access."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from aeros.runtime.literature_adapter import (  # noqa: E402
    FULLTEXT_RECOVERY_COLUMNS,
    PAPER_REGISTRY_COLUMNS,
    FulltextRecoveryArgs,
    recover_fulltext,
)


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAPER_REGISTRY_COLUMNS)
        writer.writeheader()
        writer.writerow({"paper_id": "P001", "title": "A verified economics paper about benefit access", "authors": "Example, Ada", "year": "2026", "doi": "10.1234/example.2026", "full_text_available": "no", "reading_depth": "not_read", "status": "discovered"})


def _header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def main() -> int:
    failures: list[str] = []
    policy, cli, adapter = (ROOT / "harness/literature_fulltext_recovery_policy.yml", ROOT / "aeros/cli.py", ROOT / "aeros/runtime/literature_adapter.py")
    for path in [policy, cli, adapter]:
        if not path.exists():
            failures.append(f"missing {path}")
    if policy.exists():
        text = policy.read_text(encoding="utf-8")
        for marker in ["openalex_oa", "unpaywall_oa", "cloudflare_bypass", "staging-only", "SHA-256"]:
            if marker not in text:
                failures.append(f"{policy}: missing policy marker {marker!r}")
    if cli.exists() and "literature_recover" not in cli.read_text(encoding="utf-8"):
        failures.append(f"{cli}: missing literature recover command wiring")

    with tempfile.TemporaryDirectory(prefix="aeros-fulltext-recovery-") as temporary:
        root = Path(temporary)
        registry = root / "discovery/literature/paper_registry.csv"
        _write_registry(registry)
        article = root / "fixture.html"
        article.write_text("<html><body><h1>A verified economics paper about benefit access</h1>DOI: 10.1234/example.2026 " + ("evidence " * 400) + "</body></html>", encoding="utf-8")
        before = registry.read_bytes()
        result = recover_fulltext(root, FulltextRecoveryArgs(paper_id="P001", candidate_urls=(article.as_uri(),), max_bytes=1_000_000))
        if result.get("status") != "RECOVERED":
            failures.append(f"verified local HTML fixture did not recover: {result}")
        writes = result.get("writes") or []
        if not any(str(path).startswith("work/literature_recovery/P001/") for path in writes):
            failures.append(f"verified recovery did not stage a candidate artifact: {writes}")
        if registry.read_bytes() != before:
            failures.append("recovery must not mutate the paper registry")
        queue = root / "discovery/literature/fulltext_recovery_queue.csv"
        if not queue.exists() or _header(queue) != FULLTEXT_RECOVERY_COLUMNS:
            failures.append("recovery queue header is missing or changed")
        manifest_paths = list((root / "work/literature_recovery/P001").glob("*.recovery.json"))
        if not manifest_paths:
            failures.append("verified recovery is missing a durable recovery manifest")
        elif "staging_only" not in json.loads(manifest_paths[0].read_text(encoding="utf-8")).get("recovery_boundary", ""):
            failures.append("recovery manifest does not retain the staging-only boundary")

        blocked = root / "blocked.html"
        blocked.write_text("<html>Just a moment... Cloudflare checking your browser</html>", encoding="utf-8")
        blocked_result = recover_fulltext(root, FulltextRecoveryArgs(paper_id="P001", candidate_urls=(blocked.as_uri(),), max_bytes=1_000_000))
        statuses = [row.get("recovery_status", "") for row in blocked_result.get("attempts") or []]
        if "blocked_security_challenge" not in statuses:
            failures.append(f"security challenge fixture was not blocked: {blocked_result}")
        if len(list((root / "work/literature_recovery/P001").glob("*.html"))) != 1:
            failures.append("blocked HTML must not be persisted as a recovered full text")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: lawful full-text recovery resolver, identity checks, and staging boundary are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
