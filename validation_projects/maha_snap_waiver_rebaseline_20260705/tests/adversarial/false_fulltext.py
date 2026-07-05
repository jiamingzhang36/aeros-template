#!/usr/bin/env python3
"""Adversarial fixture: create a fake full-text candidate page.

The file looks like an HTML page returned by a publisher/security edge, not a
readable article body. AEROS should block it before it becomes an EvidenceUnit or
full-text extraction card.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--kind", choices=["cloudflare", "spa"], default="cloudflare")
    args = parser.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.kind == "spa":
        body = "<html><div id='app'></div><script src='bundle.js'></script></html>"
    else:
        body = "<html><title>Just a moment...</title>Cloudflare checking your browser</html>"
    path.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
