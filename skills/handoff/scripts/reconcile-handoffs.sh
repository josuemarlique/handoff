#!/bin/sh
# reconcile-handoffs.sh - Find handoff history wherever it ended up, report what
# is wrong with it, and merge it all into ./.handoffs/ day folders.
#
# This is the loud, thorough cousin of migrate-handoffs.sh. The migration script
# runs silently before every handoff and only handles the tidy cases. This one is
# run on purpose, prints a full report, and handles the messy ones:
#
#   - history spread across several folders, including ones nobody planned for
#   - the same file in two places, sometimes with different contents
#   - a LATEST.md that matches no dated file, which means that handoff exists in
#     one copy only and the next run would overwrite it
#   - files that do not follow the YYYY-MM-DD-HH-MM naming
#   - prompt or goal files whose handoff is missing
#
# Usage:
#   reconcile-handoffs.sh            report only, changes nothing
#   reconcile-handoffs.sh --apply    do the merge described by the report
#
# Never deletes anything. Source folders are left exactly as they were.

set -e

CANONICAL_DIR=".handoffs"

APPLY="false"
if [ "$1" = "--apply" ]; then
  APPLY="true"
elif [ -n "$1" ]; then
  echo "Usage: $0 [--apply]" >&2
  exit 1
fi

WORK=""
cleanup() {
  [ -n "$WORK" ] && rm -rf "$WORK"
  WORK=""
}
trap cleanup EXIT HUP INT TERM
WORK=$(mktemp -d)

PLAN="$WORK/plan"          # action <TAB> source <TAB> destination
NOTES="$WORK/notes"        # one problem per line
SOURCES="$WORK/sources"    # one directory per line
CLAIMED="$WORK/claimed"    # destination <TAB> fingerprint, for planned writes
: > "$PLAN"
: > "$NOTES"
: > "$SOURCES"
: > "$CLAIMED"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

day_prefix() {
  printf '%s' "$1" \
    | sed -n 's/^\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\)-.*/\1/p'
}

# A well-formed artifact is YYYY-MM-DD-HH-MM-{handoff,prompt,goal}.md
is_conventional() {
  printf '%s' "$1" | grep -qE \
    '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-(handoff|prompt|goal)\.md$'
}

is_pointer() {
  case "$1" in
    LATEST.md|LATEST-PROMPT.md|LATEST-GOAL.md) return 0 ;;
  esac
  return 1
}

# Where a file belongs inside .handoffs/.
dest_for() {
  _name=$(basename "$1")
  if is_pointer "$_name"; then
    printf '%s/%s' "$CANONICAL_DIR" "$_name"
    return 0
  fi
  _day=$(day_prefix "$_name")
  if [ -n "$_day" ]; then
    printf '%s/%s/%s' "$CANONICAL_DIR" "$_day" "$_name"
  else
    printf '%s/%s' "$CANONICAL_DIR" "$_name"
  fi
}

# Content fingerprint. cksum is in POSIX, unlike md5sum.
fingerprint() {
  cksum < "$1" | awk '{print $1 "-" $2}'
}

# Pull the `created` value out of YAML frontmatter, if there is one.
frontmatter_created() {
  sed -n '/^---$/,/^---$/p' "$1" 2>/dev/null \
    | grep '^created:' | head -1 | sed 's/^created: *//' | tr -d '"'
}

count_matching() {
  find "$1" -type f -name "$2" 2>/dev/null | wc -l | tr -d ' '
}

note() {
  printf '%s\n' "$1" >> "$NOTES"
}

# What is already sitting at, or already planned for, this destination.
# Empty when the destination is free. A dry run writes nothing, so the plan
# has to be consulted as well as the filesystem or collisions go unseen.
occupant_fingerprint() {
  if [ -e "$1" ]; then
    fingerprint "$1"
    return 0
  fi
  awk -F'\t' -v want="$1" '$1 == want { print $2; exit }' "$CLAIMED"
}

claim() {
  printf '%s\t%s\n' "$1" "$2" >> "$CLAIMED"
}

# ---------------------------------------------------------------------------
# Step 1 - find every folder holding handoff artifacts
# ---------------------------------------------------------------------------

# The known locations first, so they are reported in a predictable order.
for _dir in "$CANONICAL_DIR" .claude/handoffs .claude/.handoffs \
            .codex/handoffs .Codex/handoffs docs/handoffs handoffs; do
  if [ -d "$_dir" ]; then
    _hit=$(find "$_dir" -type f -name '*-handoff.md' 2>/dev/null | head -1)
    if [ -n "$_hit" ] || [ -f "$_dir/LATEST.md" ]; then
      printf '%s\n' "$_dir" >> "$SOURCES"
    fi
  fi
done

# Then anywhere else in the project, in case it landed somewhere unplanned.
find . -type d \( -name .git -o -name node_modules -o -name .venv \) -prune -o \
  -type f -name '*-handoff.md' -print 2>/dev/null \
  | sed 's|^\./||' \
  | while IFS= read -r _f; do
      dirname "$_f"
    done \
  | sed 's|/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$||' \
  | sort -u >> "$WORK/found-dirs"

if [ -f "$WORK/found-dirs" ]; then
  while IFS= read -r _d; do
    [ -n "$_d" ] || continue
    if ! grep -qxF "$_d" "$SOURCES" 2>/dev/null; then
      printf '%s\n' "$_d" >> "$SOURCES"
      note "Unexpected location: \`$_d/\` holds handoff files. It is not one of the folders the automatic sweep knows about."
    fi
  done < "$WORK/found-dirs"
fi

if [ ! -s "$SOURCES" ]; then
  echo "No handoff files found anywhere in this project."
  echo "Run /handoff at the end of a session to create the first one."
  exit 0
fi

# ---------------------------------------------------------------------------
# Step 2 - build the plan, one source at a time
# ---------------------------------------------------------------------------

COPY_COUNT=0
FOLD_COUNT=0
SAME_COUNT=0
CONFLICT_COUNT=0
RESCUE_COUNT=0

while IFS= read -r _src; do
  [ -n "$_src" ] || continue

  _files=$(find "$_src" -type f -name '*.md' 2>/dev/null | sort || true)
  [ -n "$_files" ] || continue

  printf '%s\n' "$_files" > "$WORK/filelist"
  while IFS= read -r _file; do
    [ -n "$_file" ] || continue
    _name=$(basename "$_file")

    # Flag naming problems while we are here.
    if ! is_pointer "$_name" && ! is_conventional "$_name"; then
      case "$_name" in
        README.md|INDEX.md) : ;;
        *) note "Off-convention name: \`$_file\`. Expected YYYY-MM-DD-HH-MM-handoff.md and similar." ;;
      esac
    fi

    _dest=$(dest_for "$_file")
    _fp=$(fingerprint "$_file")

    # Already exactly where it belongs.
    if [ "$_file" = "$_dest" ]; then
      SAME_COUNT=$((SAME_COUNT + 1))
      claim "$_dest" "$_fp"
      continue
    fi

    _occupant=$(occupant_fingerprint "$_dest")
    if [ -n "$_occupant" ]; then
      if [ "$_fp" = "$_occupant" ]; then
        # Same file in two places. Keeping one copy is the whole point.
        SAME_COUNT=$((SAME_COUNT + 1))
      else
        _alt="${_dest%.md}.from-$(printf '%s' "$_src" | tr './' '__').md"
        if [ "$(occupant_fingerprint "$_alt")" = "$_fp" ]; then
          # Already resolved on an earlier run. Both copies are safe.
          SAME_COUNT=$((SAME_COUNT + 1))
        else
          CONFLICT_COUNT=$((CONFLICT_COUNT + 1))
          note "Name collision: \`$_file\` and \`$_dest\` share a name but hold different content. The incoming copy would be kept as \`$_alt\` so neither is lost."
          printf 'copy\t%s\t%s\n' "$_file" "$_alt" >> "$PLAN"
          claim "$_alt" "$_fp"
        fi
      fi
      continue
    fi

    # Files already inside .handoffs/ get moved into their day folder.
    # Files from anywhere else get copied, so the original stays put.
    case "$_file" in
      "$CANONICAL_DIR"/*)
        printf 'move\t%s\t%s\n' "$_file" "$_dest" >> "$PLAN"
        FOLD_COUNT=$((FOLD_COUNT + 1))
        ;;
      *)
        printf 'copy\t%s\t%s\n' "$_file" "$_dest" >> "$PLAN"
        COPY_COUNT=$((COPY_COUNT + 1))
        ;;
    esac
    claim "$_dest" "$_fp"
  done < "$WORK/filelist"
done < "$SOURCES"

# ---------------------------------------------------------------------------
# Step 3 - hunt for orphans
# ---------------------------------------------------------------------------

# 3a. A LATEST.md whose content matches no dated handoff means that handoff
#     exists in exactly one copy and the next run would overwrite it.
while IFS= read -r _src; do
  [ -n "$_src" ] || continue
  _latest="$_src/LATEST.md"
  [ -f "$_latest" ] || continue

  _fp=$(fingerprint "$_latest")
  _match=""
  _dated=$(find "$_src" -type f -name '*-handoff.md' 2>/dev/null || true)
  if [ -n "$_dated" ]; then
    printf '%s\n' "$_dated" > "$WORK/dated"
    while IFS= read -r _d; do
      [ -n "$_d" ] || continue
      if [ "$(fingerprint "$_d")" = "$_fp" ]; then
        _match="$_d"
        break
      fi
    done < "$WORK/dated"
  fi

  if [ -z "$_match" ]; then
    _created=$(frontmatter_created "$_latest")
    _stamp=$(printf '%s' "$_created" \
      | sed -n 's/^\([0-9-]\{10\}\)T\([0-9][0-9]\):\([0-9][0-9]\).*/\1-\2-\3/p')
    if [ -n "$_stamp" ]; then
      _day=$(day_prefix "$_stamp-x")
      _rescue="$CANONICAL_DIR/$_day/$_stamp-handoff.md"
      if [ -z "$(occupant_fingerprint "$_rescue")" ]; then
        note "Rescue: \`$_latest\` matches no dated file, so that handoff exists in one copy only and the next run would overwrite it. It would be saved as \`$_rescue\`."
        printf 'copy\t%s\t%s\n' "$_latest" "$_rescue" >> "$PLAN"
        claim "$_rescue" "$_fp"
        RESCUE_COUNT=$((RESCUE_COUNT + 1))
      fi
    else
      note "Rescue needed but not possible: \`$_latest\` matches no dated file and has no readable \`created:\` timestamp. Copy it somewhere safe by hand before the next handoff run."
    fi
  fi
done < "$SOURCES"

# 3b. Prompt or goal files whose handoff is missing.
while IFS= read -r _src; do
  [ -n "$_src" ] || continue
  _partners=$(find "$_src" -type f \( -name '*-prompt.md' -o -name '*-goal.md' \) 2>/dev/null || true)
  [ -n "$_partners" ] || continue
  printf '%s\n' "$_partners" > "$WORK/partners"
  while IFS= read -r _p; do
    [ -n "$_p" ] || continue
    _base=$(basename "$_p")
    is_pointer "$_base" && continue
    _stem=$(printf '%s' "$_base" | sed 's/-\(prompt\|goal\)\.md$//')
    if [ ! -f "$_src/$_stem-handoff.md" ] && \
       [ ! -f "$_src/$(day_prefix "$_stem")/$_stem-handoff.md" ]; then
      note "Orphan: \`$_p\` has no matching handoff document."
    fi
  done < "$WORK/partners"
done < "$SOURCES"

# ---------------------------------------------------------------------------
# Step 4 - report
# ---------------------------------------------------------------------------

echo "Handoff reconcile"
echo "================="
echo

echo "Where your handoffs live now"
while IFS= read -r _src; do
  [ -n "$_src" ] || continue
  _h=$(count_matching "$_src" '*-handoff.md')
  _p=$(count_matching "$_src" '*-prompt.md')
  _g=$(count_matching "$_src" '*-goal.md')
  if [ "$_src" = "$CANONICAL_DIR" ]; then
    _tag="correct"
  else
    _tag="needs merging"
  fi
  printf '  %-28s %3s handoff, %3s prompt, %3s goal   (%s)\n' \
    "$_src/" "$_h" "$_p" "$_g" "$_tag"
done < "$SOURCES"
echo

if [ -s "$NOTES" ]; then
  echo "Things worth knowing"
  _n=0
  while IFS= read -r _line; do
    [ -n "$_line" ] || continue
    _n=$((_n + 1))
    printf '  %s. %s\n' "$_n" "$_line"
  done < "$NOTES"
  echo
else
  echo "Things worth knowing"
  echo "  Nothing unusual. No orphans, no name collisions, no odd filenames."
  echo
fi

echo "The plan"
printf '  %s file(s) copied in from other folders (originals stay where they are)\n' "$COPY_COUNT"
printf '  %s file(s) already in .handoffs/ moved into their day folder\n' "$FOLD_COUNT"
printf '  %s file(s) already correct, nothing to do\n' "$SAME_COUNT"
printf '  %s name collision(s) kept side by side instead of overwriting\n' "$CONFLICT_COUNT"
printf '  %s handoff(s) rescued from a LATEST.md with no dated copy\n' "$RESCUE_COUNT"
echo

TOTAL=$(wc -l < "$PLAN" | tr -d ' ')

if [ "$APPLY" != "true" ]; then
  echo "Nothing was changed. This was a report."
  if [ "$TOTAL" -gt 0 ]; then
    echo "Re-run with --apply to carry out the plan above."
  fi
  exit 0
fi

# ---------------------------------------------------------------------------
# Step 5 - apply
# ---------------------------------------------------------------------------

if [ "$TOTAL" -eq 0 ]; then
  echo "Nothing to do."
  exit 0
fi

DONE=0
while IFS="$(printf '\t')" read -r _action _from _to; do
  [ -n "$_action" ] || continue
  mkdir -p "$(dirname "$_to")"
  if [ -e "$_to" ]; then
    continue
  fi
  case "$_action" in
    copy) cp -p "$_from" "$_to" ;;
    move) mv "$_from" "$_to" ;;
  esac
  DONE=$((DONE + 1))
done < "$PLAN"

echo "Done. $DONE file(s) written into \`$CANONICAL_DIR/\`."
echo "No source folder was deleted. Once you have checked \`$CANONICAL_DIR/\` looks complete,"
echo "the old folders listed above are safe to delete yourself."

exit 0
