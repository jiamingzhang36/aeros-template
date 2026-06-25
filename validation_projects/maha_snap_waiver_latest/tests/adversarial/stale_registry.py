#!/usr/bin/env python3
"""Adversarial fixture: mutate a registered output without syncing provenance."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--content", default="mutated-after-provenance\n")
    args = parser.parse_args()
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(args.content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
