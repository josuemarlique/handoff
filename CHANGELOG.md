# Changelog

## 1.3.0 - 2026-08-16

### Added
- **Day folders** - timestamped handoffs now land in `.handoffs/YYYY-MM-DD/` instead of piling up flat. The three `LATEST*.md` pointer files stay at the top level, so any path that referenced them still works. Existing flat files are folded into day folders automatically on the next run.
- **Goal file** - every handoff now also writes a short brief (`*-goal.md` and `LATEST-GOAL.md`) holding the mission, the top three priorities, what to avoid, where things stand, and a ready-written `/goal` finish-line condition. Capped at 3,000 characters in every mode. Disable with `--no-goal`.
- **Kickoff block** - each run ends by printing the exact text to paste into the next chat: one plain message that loads the brief, plus an optional `/goal` line. Replaces the old "here is your continuation prompt" ending.
- **`## Start Here` block** - every handoff, in every mode, now opens with the working agreement for the next session: plain middle-school language, short forms spelled out, a `TL;DR` at the top and bottom of every reply, no em dashes, and independent work split across an agent team so the main chat's context stays small. No flag removes it.
- **`## TL;DR` block** - five fixed bullets directly under `## Start Here`: where we are, what got done, what is next, what to watch out for, and current state.
- **`--long` mode** - a third size alongside `--compact` and the default. Adds `## File-By-File Notes`, `## Commands That Matter`, `## Open Questions`, and a `## Glossary`. Test output capture rises from 40 to 120 lines. Passing both `--compact` and `--long` is now rejected rather than guessed at.
- **`--mode <level>`** - set the size explicitly as `compact`, `full`, or `long`.
- **Bare word aliases** - `/handoff long`, `/handoff compact`, `/handoff full`, `/handoff resume`, `/handoff list`, and `/handoff reconcile` all work without the leading dashes.
- **`--reconcile`** - a repair mode for projects whose history ended up scattered. Reports before it touches anything: where handoffs live now, name collisions between folders, a `LATEST.md` that matches no dated file (a real data-loss case), off-convention filenames, orphaned prompt and goal files, and handoffs in folders nobody planned for. Applies only on a second explicit run. New `scripts/reconcile-handoffs.sh`.
- **`examples/handoff-long.md`** and **`examples/goal.md`**.
- **`references/next-session-contract.md`** - single source for the `## Start Here` block, the `## TL;DR` block, how `/goal` really behaves, the goal file template, and the kickoff block.

### Changed
- **`.handoffs/` is now enforced, not just preferred.** SKILL.md names every wrong location that has been seen in the wild and states plainly that none of them may be written to.
- **The migration sweep covers six folders**, up from one: `.claude/handoffs/`, `.claude/.handoffs/`, `.codex/handoffs/`, `.Codex/handoffs/`, `docs/handoffs/`, and a plain `handoffs/`. A folder is only touched when it actually contains handoff artifacts, so an unrelated folder named `handoffs` is left alone. Sources are copied, never deleted, and repeat runs are silent.
- **`--list` walks day folders** and groups output by day, with a mode column.
- **The `--reason` value set is consistent** between SKILL.md and the generation reference. The two files previously listed different valid values.
- Documentation and examples no longer contain em dash characters, matching the writing rule the skill hands to the next session.

### Fixed
- **Resume no longer reports the handoff run's own files as project drift.** The handoff, prompt, and goal files written at the same timestamp, plus the three `LATEST*.md` pointers, are excluded from the spec-change check.
- **The untracked `.handoffs/` folder no longer counts as uncommitted work**, which previously fired on every single resume and buried real changes.
- **Archived folders left behind by migration are ignored** by both the uncommitted-changes and spec-change checks. They are archives by definition.
- **Codex memory instructions were writing to a path that cannot exist.** The skill told hosts to write `~/.Codex/projects/{path}/memory/`; the real Codex directory is lowercase `~/.codex` and it stores memory in a database rather than a markdown tree. Hosts without a markdown memory tree now skip the step and say so instead of inventing a path.
- **The file creation order in SKILL.md re-read the clock per file**, which could give the handoff, prompt, and goal files different minute stamps on a slow run and break the freshness check's ability to recognize its own output. The timestamp is now read once and reused.
- Corrected a cross-reference in the generation reference that pointed at the wrong section for `--reason` behavior.
- Documented what happens when `--no-priority` is combined with `--reason blocked`, so the blocker is not silently dropped along with the priority section.

### Compatibility
- Handoffs written by earlier versions still load. Missing `mode` is treated as `full`, and a handoff with no `## Start Here` block resumes normally with a one-line note that it predates the working agreement.
- Nothing is deleted or renamed in place. Flat files move into day folders; the `LATEST*.md` paths do not change.
- Upgrading from a pre-1.2 install that wrote to `.claude/handoffs/` is handled on first run, and `--reconcile` is available if the history needs more than a straight copy.

## 1.2.0 — 2026-06-29

### Added
- **Codex plugin support** — added `.codex-plugin/plugin.json` so the plugin can be installed by Codex.
- **Neutral handoff directory** — `.handoffs/` is now the canonical project-local handoff path for Claude Code and Codex.
- **Legacy migration** — first use copies `.claude/handoffs/` into `.handoffs/`, leaves the old folder in place as an archive, and tells the user when it is safe to delete it.
- **Resume status metadata** — resume reports now include mode, context size, and limits when the host exposes them.
- **Contract tests** — added dependency-free tests covering Codex metadata, path migration, freshness checks, and resume status fields.

### Changed
- Repository identity is now `josuemarlique/handoff`.
- Freshness checks include `.handoffs/` alongside legacy `.claude/` and Codex project directories.

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
