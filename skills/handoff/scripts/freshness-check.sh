#!/bin/sh
# freshness-check.sh - Check whether a handoff document is still fresh
# (matches current git state). POSIX-compliant, no bash required.
#
# Usage: freshness-check.sh <path-to-handoff-file>
# Output: JSON to stdout describing freshness of each dimension.
# Exit 0 on success (even if stale), exit 1 on usage error.

set -e

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Extract a flat YAML frontmatter field value from a file.
# Strips surrounding double-quotes if present.
get_field() {
  sed -n '/^---$/,/^---$/p' "$1" | grep "^$2:" | head -1 \
    | sed "s/^$2: *//" | sed 's/^"//' | sed 's/"$//' | sed 's/[[:space:]]*$//'
}

# Escape a string for safe embedding inside a JSON double-quoted value.
# Handles backslashes first (so we don't double-escape), then double-quotes,
# then control characters that are illegal in JSON strings.
json_escape() {
  printf '%s' "$1" \
    | sed 's/\\/\\\\/g' \
    | sed 's/"/\\"/g' \
    | sed 's/	/\\t/g' \
    | tr '\n' ' '
}

# Print a JSON boolean from a shell true/false string.
jbool() {
  if [ "$1" = "true" ]; then
    printf 'true'
  else
    printf 'false'
  fi
}

# Detect platform capabilities once.
detect_platform() {
  # GNU date supports -d, BSD date uses -j -f
  if date -d "2024-01-01T00:00:00Z" +%s >/dev/null 2>&1; then
    DATE_FLAVOR="gnu"
  else
    DATE_FLAVOR="bsd"
  fi

  # GNU touch supports -d, BSD touch uses -t
  if touch -d "2024-01-01T00:00:00" /dev/null 2>/dev/null; then
    TOUCH_FLAVOR="gnu"
  else
    TOUCH_FLAVOR="bsd"
  fi

  # GNU stat: stat -c %Y, BSD stat: stat -f %m
  if stat -c %Y /dev/null >/dev/null 2>&1; then
    STAT_FLAVOR="gnu"
  else
    STAT_FLAVOR="bsd"
  fi
}

# Convert an ISO-ish timestamp to epoch seconds.
# Accepts formats like: 2024-03-14T12:30:00Z, 2024-03-14 12:30:00, etc.
ts_to_epoch() {
  _ts="$1"
  if [ "$DATE_FLAVOR" = "gnu" ]; then
    date -d "$_ts" +%s 2>/dev/null || echo "0"
  else
    # BSD: try multiple formats
    # Try ISO 8601 with T separator
    _clean=$(printf '%s' "$_ts" | sed 's/T/ /;s/Z$//')
    date -j -f "%Y-%m-%d %H:%M:%S" "$_clean" +%s 2>/dev/null \
      || date -j -f "%Y-%m-%d %H:%M" "$_clean" +%s 2>/dev/null \
      || echo "0"
  fi
}

# Get modification time of a file as a human-readable timestamp.
file_mtime_pretty() {
  if [ "$STAT_FLAVOR" = "gnu" ]; then
    stat -c '%y' "$1" 2>/dev/null | sed 's/\.[0-9]*//'
  else
    stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$1" 2>/dev/null
  fi
}

# Create a reference file whose mtime is set to the given timestamp string.
# Returns the path to the temp file (caller must clean up).
create_reference_file() {
  _ts="$1"
  _ref=$(mktemp)
  if [ "$TOUCH_FLAVOR" = "gnu" ]; then
    touch -d "$_ts" "$_ref" 2>/dev/null || touch "$_ref"
  else
    # BSD touch -t expects YYYYMMDDhhmm.ss
    _fmt=$(printf '%s' "$_ts" \
      | sed 's/T/ /' \
      | sed 's/Z$//' \
      | sed 's/[-:]//g' \
      | sed 's/ //' \
      | sed 's/\([0-9]\{12\}\)\([0-9]\{2\}\)/\1.\2/')
    if [ -n "$_fmt" ]; then
      touch -t "$_fmt" "$_ref" 2>/dev/null || touch "$_ref"
    else
      touch "$_ref"
    fi
  fi
  printf '%s' "$_ref"
}

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

if [ $# -lt 1 ]; then
  echo "Error: missing argument. Usage: $0 <handoff-file>" >&2
  exit 1
fi

HANDOFF_FILE="$1"

if [ ! -f "$HANDOFF_FILE" ]; then
  echo "Error: handoff file not found: $HANDOFF_FILE" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Initialise
# ---------------------------------------------------------------------------

detect_platform

# Parse frontmatter fields
FM_CREATED=$(get_field "$HANDOFF_FILE" "created")
FM_BRANCH=$(get_field "$HANDOFF_FILE" "branch")
FM_LAST_COMMIT=$(get_field "$HANDOFF_FILE" "last_commit")
FM_UNCOMMITTED=$(get_field "$HANDOFF_FILE" "uncommitted_changes")

# Check if we are inside a git repo
IN_GIT="true"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  IN_GIT="false"
fi

# Overall freshness — start true, any stale check flips it
OVERALL_FRESH="true"

# ---------------------------------------------------------------------------
# Check 1: Commit drift
# ---------------------------------------------------------------------------

CD_STALE="false"
CD_HANDOFF_COMMIT="$FM_LAST_COMMIT"
CD_CURRENT_HEAD=""
CD_COMMITS_SINCE=0
CD_SUMMARIES=""
CD_ERROR=""

if [ "$IN_GIT" = "true" ]; then
  CD_CURRENT_HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

  if [ "$CD_HANDOFF_COMMIT" != "$CD_CURRENT_HEAD" ]; then
    CD_STALE="true"
    OVERALL_FRESH="false"

    # Try to count commits between handoff and HEAD
    if git rev-parse "$CD_HANDOFF_COMMIT" >/dev/null 2>&1; then
      CD_COMMITS_SINCE=$(git rev-list --count "${CD_HANDOFF_COMMIT}..HEAD" 2>/dev/null || echo "0")
      # Get up to 20 most recent one-line summaries
      _raw_summaries=$(git log --oneline "${CD_HANDOFF_COMMIT}..HEAD" -20 2>/dev/null || true)
    else
      CD_ERROR="handoff commit ${CD_HANDOFF_COMMIT} not found in repository"
    fi
  fi
fi

# Build commit_summaries JSON array
CD_SUMMARIES_JSON="["
_first="true"
if [ -n "$_raw_summaries" ]; then
  # Process line by line via a temp file to stay POSIX
  _sumfile=$(mktemp)
  printf '%s\n' "$_raw_summaries" > "$_sumfile"
  while IFS= read -r _line; do
    [ -z "$_line" ] && continue
    _escaped=$(json_escape "$_line")
    if [ "$_first" = "true" ]; then
      CD_SUMMARIES_JSON="${CD_SUMMARIES_JSON}\"${_escaped}\""
      _first="false"
    else
      CD_SUMMARIES_JSON="${CD_SUMMARIES_JSON}, \"${_escaped}\""
    fi
  done < "$_sumfile"
  rm -f "$_sumfile"
fi
CD_SUMMARIES_JSON="${CD_SUMMARIES_JSON}]"

# Build commit_drift JSON object
CD_JSON=$(printf '{\n      "stale": %s,\n      "handoff_commit": "%s",\n      "current_head": "%s",\n      "commits_since": %s,\n      "commit_summaries": %s' \
  "$(jbool "$CD_STALE")" \
  "$(json_escape "$CD_HANDOFF_COMMIT")" \
  "$(json_escape "$CD_CURRENT_HEAD")" \
  "$CD_COMMITS_SINCE" \
  "$CD_SUMMARIES_JSON")
if [ -n "$CD_ERROR" ]; then
  CD_JSON=$(printf '%s,\n      "error": "%s"' "$CD_JSON" "$(json_escape "$CD_ERROR")")
fi
CD_JSON=$(printf '%s\n    }' "$CD_JSON")

# ---------------------------------------------------------------------------
# Check 2: Branch drift
# ---------------------------------------------------------------------------

BD_STALE="false"
BD_HANDOFF_BRANCH="$FM_BRANCH"
BD_CURRENT_BRANCH="unknown"

if [ "$IN_GIT" = "true" ]; then
  BD_CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
  # Detached HEAD returns empty string
  if [ -z "$BD_CURRENT_BRANCH" ]; then
    BD_CURRENT_BRANCH="(detached HEAD)"
  fi
  if [ "$BD_HANDOFF_BRANCH" != "$BD_CURRENT_BRANCH" ]; then
    BD_STALE="true"
    OVERALL_FRESH="false"
  fi
fi

BD_JSON=$(printf '{\n      "stale": %s,\n      "handoff_branch": "%s",\n      "current_branch": "%s"\n    }' \
  "$(jbool "$BD_STALE")" \
  "$(json_escape "$BD_HANDOFF_BRANCH")" \
  "$(json_escape "$BD_CURRENT_BRANCH")")

# ---------------------------------------------------------------------------
# Check 3: Uncommitted changes
# ---------------------------------------------------------------------------

UC_STALE="false"
UC_HAS_CHANGES="false"
UC_FILES_JSON="["

if [ "$IN_GIT" = "true" ]; then
  _porcelain=$(git status --porcelain 2>/dev/null || true)
  if [ -n "$_porcelain" ]; then
    UC_HAS_CHANGES="true"
    # Mark stale if the handoff said there were no uncommitted changes
    # but now there are, or vice versa. Any uncommitted changes is potentially
    # stale context.
    UC_STALE="true"
    OVERALL_FRESH="false"

    _first="true"
    _ucfile=$(mktemp)
    printf '%s\n' "$_porcelain" > "$_ucfile"
    while IFS= read -r _line; do
      [ -z "$_line" ] && continue
      # Strip the leading status chars (first 3 characters)
      _fname=$(printf '%s' "$_line" | sed 's/^...//')
      _escaped=$(json_escape "$_fname")
      if [ "$_first" = "true" ]; then
        UC_FILES_JSON="${UC_FILES_JSON}\"${_escaped}\""
        _first="false"
      else
        UC_FILES_JSON="${UC_FILES_JSON}, \"${_escaped}\""
      fi
    done < "$_ucfile"
    rm -f "$_ucfile"
  fi
fi
UC_FILES_JSON="${UC_FILES_JSON}]"

UC_JSON=$(printf '{\n      "stale": %s,\n      "has_changes": %s,\n      "files_changed": %s\n    }' \
  "$(jbool "$UC_STALE")" \
  "$(jbool "$UC_HAS_CHANGES")" \
  "$UC_FILES_JSON")

# ---------------------------------------------------------------------------
# Check 4: Spec / plan changes
# ---------------------------------------------------------------------------

SC_STALE="false"
SC_FILES_JSON="["

if [ -n "$FM_CREATED" ]; then
  _reffile=$(create_reference_file "$FM_CREATED")

  _spec_files=""
  for _dir in docs .handoffs .claude .Codex .codex; do
    if [ -d "$_dir" ]; then
      _found=$(find "$_dir" -type f -newer "$_reffile" 2>/dev/null || true)
      if [ -n "$_found" ]; then
        _spec_files="${_spec_files}
${_found}"
      fi
    fi
  done

  rm -f "$_reffile"

  _first="true"
  if [ -n "$_spec_files" ]; then
    SC_STALE="true"
    OVERALL_FRESH="false"

    _scfile=$(mktemp)
    printf '%s\n' "$_spec_files" > "$_scfile"
    while IFS= read -r _path; do
      [ -z "$_path" ] && continue
      _mtime=$(file_mtime_pretty "$_path")
      _epath=$(json_escape "$_path")
      _etime=$(json_escape "$_mtime")
      if [ "$_first" = "true" ]; then
        SC_FILES_JSON="${SC_FILES_JSON}{\"path\": \"${_epath}\", \"modified\": \"${_etime}\"}"
        _first="false"
      else
        SC_FILES_JSON="${SC_FILES_JSON}, {\"path\": \"${_epath}\", \"modified\": \"${_etime}\"}"
      fi
    done < "$_scfile"
    rm -f "$_scfile"
  fi
fi
SC_FILES_JSON="${SC_FILES_JSON}]"

SC_JSON=$(printf '{\n      "stale": %s,\n      "modified_files": %s\n    }' \
  "$(jbool "$SC_STALE")" \
  "$SC_FILES_JSON")

# ---------------------------------------------------------------------------
# Check 5: Dependency changes
# ---------------------------------------------------------------------------

DC_STALE="false"
DC_FILES_JSON="["

DEP_FILES="package.json pnpm-lock.yaml yarn.lock package-lock.json Cargo.lock go.sum requirements.txt pyproject.toml"

if [ -n "$FM_CREATED" ]; then
  _reffile=$(create_reference_file "$FM_CREATED")

  _first="true"
  for _dep in $DEP_FILES; do
    if [ -f "$_dep" ]; then
      _escaped=$(json_escape "$_dep")
      if [ "$_first" = "true" ]; then
        DC_FILES_JSON="${DC_FILES_JSON}\"${_escaped}\""
        _first="false"
      else
        DC_FILES_JSON="${DC_FILES_JSON}, \"${_escaped}\""
      fi

      # Check if modified after handoff creation
      _newer=$(find . -maxdepth 1 -name "$_dep" -newer "$_reffile" 2>/dev/null || true)
      if [ -n "$_newer" ]; then
        DC_STALE="true"
        OVERALL_FRESH="false"
      fi
    fi
  done

  rm -f "$_reffile"
fi
DC_FILES_JSON="${DC_FILES_JSON}]"

DC_JSON=$(printf '{\n      "stale": %s,\n      "files_checked": %s\n    }' \
  "$(jbool "$DC_STALE")" \
  "$DC_FILES_JSON")

# ---------------------------------------------------------------------------
# Assemble final JSON
# ---------------------------------------------------------------------------

_handoff_date_escaped=$(json_escape "$FM_CREATED")

printf '{\n'
printf '  "fresh": %s,\n' "$(jbool "$OVERALL_FRESH")"
printf '  "git": %s,\n' "$(jbool "$IN_GIT")"
printf '  "handoff_date": "%s",\n' "$_handoff_date_escaped"
printf '  "checks": {\n'
printf '    "commit_drift": %s,\n' "$CD_JSON"
printf '    "branch_drift": %s,\n' "$BD_JSON"
printf '    "uncommitted_changes": %s,\n' "$UC_JSON"
printf '    "spec_changes": %s,\n' "$SC_JSON"
printf '    "dependency_changes": %s\n' "$DC_JSON"
printf '  }\n'
printf '}\n'

exit 0
