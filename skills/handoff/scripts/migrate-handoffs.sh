#!/bin/sh
# migrate-handoffs.sh - Copy legacy handoff history into the neutral path.
# Leaves .claude/handoffs untouched as an archive.

set -e

CANONICAL_DIR=".handoffs"
LEGACY_DIR=".claude/handoffs"

if [ -d "$CANONICAL_DIR" ]; then
  exit 0
fi

if [ ! -d "$LEGACY_DIR" ]; then
  exit 0
fi

mkdir -p "$CANONICAL_DIR"

# Copy contents, including dotfiles, without removing the legacy archive.
cp -pR "$LEGACY_DIR"/. "$CANONICAL_DIR"/

cat <<'MSG'
Migrated handoff history from `.claude/handoffs/` to `.handoffs/`.
The old `.claude/handoffs/` folder was left in place as an archive.
When you have confirmed the new `.handoffs/` history is complete, you can delete `.claude/handoffs/`.
MSG
