#!/usr/bin/env python3
"""Adversarial fixture: exits successfully while producing no declared output.

This simulates a common false-completion failure mode: a script returns exit 0
but the artifact a task claims as its allowed output is absent.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--declared-output", required=True)
    args = parser.parse_args()
    # Resolve the path to prove the argument is syntactically usable, but do not
    # create the parent directory or file. The point is to return success while
    # leaving the promised artifact absent.
    Path(args.declared_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
