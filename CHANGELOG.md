# Changelog

## 1.1.0 — 2026-04-17

### Added
- **Credential redaction** — handoffs now scrub credential patterns (OpenAI, GitHub, Slack, AWS, JWTs, bearer tokens, DB URLs, PEM blocks, generic `password=`/`token=` assignments) and never quote contents of `.env`/secret/key files. Redaction count surfaces in frontmatter as `redactions_applied`.
- **`--list` flag** — browse past handoffs without opening files. Prints timestamp, branch, commit, stop reason, and one-line summary per handoff, newest first.
- **Carry-forward of unresolved priorities** — when `LATEST.md` exists and its "What's Next" contains items not addressed this session, they appear in a new `### Carried forward from previous session` subsection in the new handoff. Resume Mode surfaces them distinctly so multi-session drift is visible.
- **`--note-raw "text"`** — companion to `--note` that bypasses the redaction filter for explicit consent-based injection. Frontmatter records `raw_notes_count`.
- **`--no-carryforward`** — suppresses automatic carry-forward for sessions where priorities have pivoted.

### Changed
- `--note` values now pass through the credential redaction filter before being written.
- Captured test/build output is capped at 40 lines per command before embedding.

### Compatibility
- Fully backwards-compatible. New frontmatter fields (`redactions_applied`, `raw_notes_count`) are optional and emitted only when non-zero. Existing handoffs on disk continue to load correctly in Resume Mode. No freshness-check script changes.

## 1.0.0 — 2026-03-16

### Added
- Initial release
- **Generate mode**: creates structured handoff documents with YAML frontmatter
- **Resume mode**: loads and verifies previous handoffs with drift detection
- **Flags**: `--compact`, `--reason`, `--interactive`, `--note`, `--no-prompt`, `--no-memory`, `--no-priority`
- **Freshness check**: POSIX-compatible shell script with GNU/BSD cross-platform support
- **Sentiment detection**: scans conversation history for friction signals, repeated errors, abandoned approaches
- **Memory integration**: updates Claude's project memory system for ambient cross-session awareness
- **Dual formatting**: full mode (default, no token restrictions) and compact mode (token-conscious)
- **Example outputs**: full and compact format samples in `skills/handoff/examples/`
