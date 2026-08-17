#!/bin/sh
# migrate-handoffs.sh - Normalize where handoff files live.
#
# Two jobs, both safe to run over and over:
#   1. Copy handoff history out of any old folder into ./.handoffs/
#      (copy only - the old folder is never deleted).
#   2. Move loose dated files sitting directly in ./.handoffs/ into
#      ./.handoffs/YYYY-MM-DD/ day folders so the folder stays readable.
#
# Prints a short notice only when it actually changed something.
# Exit code is always 0 unless the shell itself fails.

set -e

CANONICAL_DIR=".handoffs"

# Temp files are tracked here so an early exit under `set -e` cannot leave
# litter behind.
SCRATCH=""
cleanup() {
  [ -n "$SCRATCH" ] && rm -f "$SCRATCH"
  SCRATCH=""
}
trap cleanup EXIT HUP INT TERM

# Every folder a coding agent has been known to write handoffs into.
# A folder is only migrated when it actually contains handoff artifacts.
LEGACY_DIRS=".claude/handoffs .claude/.handoffs .codex/handoffs .Codex/handoffs docs/handoffs handoffs"

COPIED_FROM=""
FOLDERED=0
COLLISIONS=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# True when the directory holds something that looks like handoff history.
# This guard keeps us from swallowing an unrelated folder that happens to be
# named "handoffs".
looks_like_handoff_dir() {
  _dir="$1"
  if [ ! -d "$_dir" ]; then
    return 1
  fi
  if [ -f "$_dir/LATEST.md" ]; then
    return 0
  fi
  _hit=$(find "$_dir" -type f -name '*-handoff.md' 2>/dev/null | head -1)
  if [ -n "$_hit" ]; then
    return 0
  fi
  return 1
}

# Pull the leading YYYY-MM-DD out of a file name. Empty when there is none.
day_prefix() {
  printf '%s' "$1" \
    | sed -n 's/^\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\)-.*/\1/p'
}

# Work out where a file should end up inside .handoffs/.
# Pointer files stay at the top level, dated files go into their day folder,
# and anything else keeps the path it already had.
# Args: <relative-path-inside-source>
dest_for() {
  _rel="$1"
  _name=$(basename "$_rel")

  case "$_name" in
    LATEST.md|LATEST-PROMPT.md|LATEST-GOAL.md|README.md|INDEX.md)
      printf '%s/%s' "$CANONICAL_DIR" "$_name"
      return 0
      ;;
  esac

  _day=$(day_prefix "$_name")
  if [ -n "$_day" ]; then
    printf '%s/%s/%s' "$CANONICAL_DIR" "$_day" "$_name"
  else
    printf '%s/%s' "$CANONICAL_DIR" "$_rel"
  fi
}

# Copy every file from $1 into the canonical folder, routing each one through
# dest_for so a repeat run lands on the same path and is skipped.
# Never overwrites a file that already exists at the destination.
copy_tree() {
  _src="$1"
  COPIED_COUNT=0
  _list=$(find "$_src" -type f 2>/dev/null || true)
  [ -n "$_list" ] || return 0

  SCRATCH=$(mktemp)
  printf '%s\n' "$_list" > "$SCRATCH"
  while IFS= read -r _file; do
    [ -n "$_file" ] || continue
    _relpath=${_file#"$_src"/}
    _target=$(dest_for "$_relpath")
    if [ -e "$_target" ]; then
      continue
    fi
    mkdir -p "$(dirname "$_target")"
    cp -p "$_file" "$_target"
    COPIED_COUNT=$((COPIED_COUNT + 1))
  done < "$SCRATCH"
  cleanup
}

# ---------------------------------------------------------------------------
# Step 1 - pull history out of old locations
# ---------------------------------------------------------------------------

for _legacy in $LEGACY_DIRS; do
  if looks_like_handoff_dir "$_legacy"; then
    mkdir -p "$CANONICAL_DIR"
    copy_tree "$_legacy"
    if [ "$COPIED_COUNT" -gt 0 ]; then
      COPIED_FROM="${COPIED_FROM}${_legacy}
"
    fi
  fi
done

# ---------------------------------------------------------------------------
# Step 2 - fold loose dated files into day folders
# ---------------------------------------------------------------------------

if [ -d "$CANONICAL_DIR" ]; then
  for _file in "$CANONICAL_DIR"/*.md; do
    [ -f "$_file" ] || continue

    _base=$(basename "$_file")
    case "$_base" in
      LATEST.md|LATEST-PROMPT.md|LATEST-GOAL.md|README.md|INDEX.md) continue ;;
    esac

    # Only fold files whose name starts with a YYYY-MM-DD date.
    _day=$(day_prefix "$_base")
    [ -n "$_day" ] || continue

    mkdir -p "$CANONICAL_DIR/$_day"
    if [ -e "$CANONICAL_DIR/$_day/$_base" ]; then
      COLLISIONS=$((COLLISIONS + 1))
      continue
    fi
    mv "$_file" "$CANONICAL_DIR/$_day/$_base"
    FOLDERED=$((FOLDERED + 1))
  done
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

if [ -n "$COPIED_FROM" ]; then
  printf 'Migrated handoff history into `%s/`.\n' "$CANONICAL_DIR"
  printf 'Copied from:\n'
  printf '%s' "$COPIED_FROM" | while IFS= read -r _src; do
    [ -n "$_src" ] || continue
    printf '  - `%s/`\n' "$_src"
  done
  printf 'Each old folder was left in place as an archive.\n'
  printf 'Once you have confirmed `%s/` has everything, you can delete `.claude/handoffs/` and any other old folder listed above.\n' "$CANONICAL_DIR"
fi

if [ "$FOLDERED" -gt 0 ]; then
  printf 'Organized %s handoff file(s) into day folders under `%s/YYYY-MM-DD/`.\n' \
    "$FOLDERED" "$CANONICAL_DIR"
fi

if [ "$COLLISIONS" -gt 0 ]; then
  printf 'Left %s file(s) in place because a file with the same name already existed in the day folder.\n' \
    "$COLLISIONS"
fi

exit 0
