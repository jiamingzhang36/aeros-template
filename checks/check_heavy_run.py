#!/usr/bin/env python3
"""Exercise heavy-run cache reuse and unchanged-failure plateau behavior."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import yaml

from aeros.runtime.heavy_run import run_heavy_job


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros-heavy-run-") as temporary:
        root = Path(temporary)
        (root / ".aeros").mkdir()
        producer = root / "producer.py"
        producer.write_text(
            "from pathlib import Path\n"
            "counter=Path('counter.txt')\n"
            "n=int(counter.read_text()) if counter.exists() else 0\n"
            "counter.write_text(str(n+1))\n"
            "Path('result.txt').write_text('accepted\\n')\n",
            encoding="utf-8",
        )
        failing = root / "failing.py"
        failing.write_text("raise SystemExit(7)\n", encoding="utf-8")
        config = {
            "version": 1,
            "jobs": {
                "fixture": {
                    "command": [sys.executable, "producer.py"],
                    "cost_class": "heavy",
                    "hash_inputs": ["producer.py"],
                    "expected_outputs": ["result.txt"],
                },
                "failure": {
                    "command": [sys.executable, "failing.py"],
                    "cost_class": "very_heavy",
                    "max_attempts": 1,
                    "hash_inputs": ["failing.py"],
                    "expected_outputs": ["never.txt"],
                },
            },
        }
        (root / ".aeros" / "heavy_jobs.yml").write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
        )
        first = run_heavy_job(root, "fixture")
        second = run_heavy_job(root, "fixture")
        if first.status != "ACCEPTED" or second.status != "CACHE_HIT":
            failures.append(
                f"expected ACCEPTED then CACHE_HIT, got "
                f"{first.status}/{second.status}"
            )
        if (root / "counter.txt").read_text(encoding="utf-8") != "1":
            failures.append("cache hit spawned the producer a second time")
        accepted = json.loads(
            (root / second.accepted_manifest).read_text(encoding="utf-8")
        )
        if accepted.get("outputs", [{}])[0].get("sha256") == "":
            failures.append("accepted output was not content-addressed")

        failed = run_heavy_job(root, "failure")
        plateau = run_heavy_job(root, "failure")
        if failed.status != "PLATEAU" or plateau.status != "PLATEAU":
            failures.append(
                f"very-heavy unchanged failure did not plateau: "
                f"{failed.status}/{plateau.status}"
            )

        blocked_root = root / "blocked"
        (blocked_root / ".aeros").mkdir(parents=True)
        (blocked_root / ".aeros" / "heavy_jobs.yml").write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "jobs": {
                        "external": {
                            "command": [sys.executable, "producer.py"],
                            "working_root": ".",
                            "artifact_root": ".",
                            "required_mounts": ["/definitely/not/mounted/aeros"],
                            "expected_outputs": ["result.txt"],
                        }
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        blocked = run_heavy_job(blocked_root, "external")
        if blocked.status != "BLOCKED_EXTERNAL_INPUT" or blocked.ok:
            failures.append(
                f"missing external root was not a structured blocker: "
                f"{blocked.status}"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: heavy jobs are single-flight, cache-reused, and plateau-bounded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
