#!/usr/bin/env python3
"""Check that replication-package scaffolding exists."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_PATHS = [
    Path("README_replication.md"),
    Path("project_manifest.yml"),
    Path("Makefile"),
    Path("requirements.txt"),
    Path("environment.yml"),
    Path("data/README_data.md"),
    Path("code/99_make_all.py"),
    Path("evidence/result_index.csv"),
    Path("paper/draft.md"),
]


def main() -> int:
    missing = [str(path) for path in REQUIRED_PATHS if not path.exists()]
    if missing:
        print("FAIL: replication package scaffolding is missing:")
        print("\n".join(missing))
        return 1

    print("PASS: replication package scaffolding exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
