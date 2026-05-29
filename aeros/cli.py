"""AEROS runtime CLI.

    python3 -m aeros.cli run tasks/discovery/D001_literature_search.yml --dry-run
    python3 -m aeros.cli run tasks/discovery/D001_literature_search.yml
"""

from __future__ import annotations

import argparse
import sys

from .runtime.kernel import run_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeros", description="AEROS runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a single task contract")
    run.add_argument("contract", help="path to a task contract .yml")
    run.add_argument("--dry-run", action="store_true",
                     help="print the agent prompt and planned checks; do not call the agent")
    run.add_argument("--max-retries", type=int, default=None,
                     help="override the contract's retry_policy.max_retries")

    args = parser.parse_args(argv)
    if args.command == "run":
        return run_task(args.contract, dry_run=args.dry_run,
                        max_retries_override=args.max_retries)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
