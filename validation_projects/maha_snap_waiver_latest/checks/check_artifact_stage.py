#!/usr/bin/env python3
"""Check canonical artifact staging excludes raw/staging captures."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.artifact_stage import classify_artifacts, stage_canonical_artifacts


def _run(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if _run(root, ["init"]).returncode != 0:
            print("FAIL: could not initialize fixture git repo")
            return 1
        _run(root, ["config", "user.email", "aeros@example.test"])
        _run(root, ["config", "user.name", "AEROS Test"])
        (root / "README.md").write_text("fixture\n", encoding="utf-8")
        _run(root, ["add", "README.md"])
        _run(root, ["commit", "-m", "fixture"])

        for path, text in {
            "evidence/result_registry.csv": "result_id\nR001\n",
            "paper/draft.md": "# Draft\n",
            "work/recapture_x/raw.html": "<html></html>\n",
            "data/raw/source.csv": "x\n1\n",
            "scratch.tmp": "tmp\n",
        }.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

        report = classify_artifacts(root)
        if "evidence/result_registry.csv" not in report["canonical"] or "paper/draft.md" not in report["canonical"]:
            print("FAIL: canonical artifacts were not selected")
            return 1
        if "work/recapture_x/raw.html" not in report["excluded_raw_staging"] or "data/raw/source.csv" not in report["excluded_raw_staging"]:
            print("FAIL: raw/staging artifacts were not excluded")
            return 1
        if "scratch.tmp" not in report["unclassified"]:
            print("FAIL: unclassified artifact was not preserved as unclassified")
            return 1

        applied = stage_canonical_artifacts(root, apply=True, canonical=True, exclude_raw_staging=True)
        if applied["status"] != "PASS" or not applied["applied"]:
            print("FAIL: canonical staging did not apply")
            return 1
        staged = _run(root, ["diff", "--cached", "--name-only"]).stdout.splitlines()
        if sorted(staged) != ["evidence/result_registry.csv", "paper/draft.md"]:
            print(f"FAIL: staged wrong paths: {staged}")
            return 1

    print("PASS: artifact stage selector check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
