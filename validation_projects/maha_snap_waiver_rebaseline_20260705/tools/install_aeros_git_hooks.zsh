#!/bin/zsh
# Install local AEROS git hooks for this repository.
#
# This is intentionally opt-in. Template sync must not silently mutate a
# downstream project's .git/hooks behavior.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/tools/hooks/pre-commit-aeros-protected-paths"
DEST="$ROOT/.git/hooks/pre-commit"
MARKER="AEROS-PROTECTED-PATH-HOOK-001"

if [ ! -f "$SRC" ]; then
  print -u2 "missing hook template: $SRC"
  exit 1
fi

if [ -f "$DEST" ] && ! grep -q "$MARKER" "$DEST"; then
  print -u2 "refusing to overwrite existing non-AEROS pre-commit hook: $DEST"
  print -u2 "move it aside or merge $SRC manually."
  exit 1
fi

cp "$SRC" "$DEST"
chmod +x "$DEST"
echo "installed AEROS protected-path pre-commit hook -> $DEST"
echo "override for a human-approved protected commit: AEROS_ALLOW_PROTECTED_COMMIT=1 git commit ..."

