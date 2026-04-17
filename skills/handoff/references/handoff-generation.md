# Handoff Generation Reference

Detailed procedure for generating a handoff document in default mode.

---

## 1. Context Gathering Procedure

Run all tool-based commands in parallel where dependencies allow. LLM-generated content comes from the conversation context window — never from tool extraction.

### Tool-Gathered (via Bash/Read)

Run these in parallel as a first batch:

```bash
git log --oneline -20
# If LATEST.md exists, scope to commits since the last handoff commit hash found in its frontmatter
git status
git diff --stat
```

Test and build command discovery — apply this heuristic in order, stopping at the first match:

1. Read `package.json` — look for `scripts.test` and `scripts.build`
2. Read `Makefile` — look for `test` and `build` targets
3. Read `Cargo.toml` — infer `cargo test` and `cargo build`
4. Read `go.mod` — infer `go test ./...` and `go build ./...`
5. Read `pyproject.toml` — infer `pytest`

Once discovered, run test and build commands and capture full output. Run them in parallel if independent.

Also read in parallel:
- `docs/**` for specs, plans, roadmaps
- `.claude/features/*/prd.md`, `.claude/features/*/architecture.md` for feature context
- `.claude/projects/*/memory/MEMORY.md` for phase and status context

### LLM-Generated (from conversation context window)

These are synthesized by the model — do NOT attempt to extract them with file tools:

- **Refined intent** — What the session set out to accomplish after any clarification exchanges, not the raw first message
- **Decisions made** — Architecture and design choices surfaced during the session, with the reasoning behind each
- **Friction points** — Problems encountered, failed approaches, and the solutions that worked. Load `references/sentiment-analysis.md` for detection patterns before scanning
- **Sentiment scan** — Frustration signals, repeated attempts, rollbacks, expressions of confusion or blocked progress

---

## 2. Handoff Document Template

### YAML Frontmatter

All fields are flat and single-line. No multi-line values, no nested keys.

```yaml
---
created: YYYY-MM-DDTHH:MM:SS
branch: <current branch>
last_commit: <short hash>
last_commit_message: "<message>"
uncommitted_changes: true/false
test_summary: "<X passing (breakdown)>"
build_status: passing/failing/skipped
stop_reason: <value from --reason flag, or "not specified">
phase: "<current phase if detectable from memory or conversation>"
---
```

### Body Sections

All 8 sections are required unless a flag suppresses one (see Section 7).

**`## Refined Intent`**

What this session set out to accomplish — the clarified understanding after any back-and-forth, not the raw first message. One to three sentences. Captures the "why" behind the work, not just the tasks.

**`## What Was Built`**

Concrete deliverables grouped logically, not chronologically. Subsections as needed:

- Files created and modified (with brief description of purpose)
- Features implemented
- Tests added

Avoid blow-by-blow narration. Group by concern.

**`## Decisions Made`**

Architecture and design decisions with reasoning. Format each entry as:

```
**[Decision title]:** [What was decided]. [Why — the tradeoff, constraint, or goal that drove it].
```

Prioritize "why" over "what". Skip trivial or purely mechanical choices.

**`## Friction Points`**

Problems encountered, failed approaches, workarounds. Use the entry format from `references/sentiment-analysis.md`. Each entry includes:

- What the problem was
- What was tried (including failed attempts)
- What worked (or current status if unresolved)

**`## Current State`**

- Branch name and latest commit hash + message
- Test results (from automatically-run test command): pass/fail count, suite breakdown
- Build status (from automatically-run build command)
- Description of any uncommitted changes present

**`## What's Next`**

Priority-ordered list derived from specs/plans/roadmap context plus conversation signals. Behavior varies by `--reason` flag (see Section 7). Each item should be actionable — specific enough that the next session knows where to start without re-reading everything.

**Carry-forward from the previous handoff:** if `.claude/handoffs/LATEST.md` exists and contains a parseable `## What's Next` section, evaluate each previous priority against this session's signals (commit messages since the previous `last_commit`, paths in `git diff --name-only`, conversation topics). An item is considered **addressed** when two or more signal categories match, OR when the model is confident from the conversation that the item was completed or explicitly abandoned. Everything else is **unaddressed** and carried forward. Bias: on ambiguity, carry forward.

When at least one item is carried forward, structure the `What's Next` section as two subsections:

    ### Carried forward from previous session

    - [item text, verbatim from prior handoff] — not touched this session
    - [item text, verbatim] — partially addressed: [one-line note]
    - [item text, verbatim] — blocked: [one-line reason, if detected]

    ### New priorities

    1. [New priority #1]
    2. [New priority #2]

When nothing is carried forward, use the original single-list format (no subsection headings).

Suppressed by `--no-carryforward`. Also suppressed when `--no-priority` is set (there's no What's Next section to attach to).

**`## Environment Notes`**

- Dependencies installed during the session
- Configuration changes made
- New tools, scripts, or aliases introduced
- Anything about the local environment that future sessions need to know

**`## User Notes`**

Custom context from `--note` flags or `--interactive` mode answers. Only include this section if the user provided notes. If absent, omit the section entirely.

---

## 3. Continuation Prompt Templates

### Full Mode

```
You are continuing a previous session. Read the handoff document at
.claude/handoffs/LATEST.md for full context, then run /handoff --resume
to verify freshness before proceeding.

Key context:
- Project: [name]
- Phase: [current phase]
- Branch: [branch]
- Last session accomplished: [1-2 sentence summary]
- Priority for this session: [first item from What's Next]
- Critical friction to avoid: [top friction point]

For full details including all decisions, friction points, and
environment notes, see the handoff document.
```

### Compact Mode

```
Continue from .claude/handoffs/LATEST.md — run /handoff --resume first.
Project: [name] | Branch: [branch] | Phase: [phase]
Last: [one-line summary] | Next: [one-line priority]
Avoid: [one-line top friction point]
```

---

## 4. File Writing Procedure

Execute these steps in order:

1. Generate a timestamp: `date +%Y-%m-%d-%H-%M`
2. Create the handoffs directory if it does not exist: `mkdir -p .claude/handoffs`
3. Write the handoff document to `.claude/handoffs/{timestamp}-handoff.md`
4. Copy the same content to `.claude/handoffs/LATEST.md` (full copy, not a symlink)
5. If `--no-prompt` was not passed: write the continuation prompt to `.claude/handoffs/{timestamp}-prompt.md`
6. If `--no-prompt` was not passed: copy the continuation prompt to `.claude/handoffs/LATEST-PROMPT.md`

---

## 5. Memory Update Procedure

Skip this entire procedure if `--no-memory` was passed.

**Target path:** `~/.claude/projects/{project-path}/memory/handoff_state.md`

Where `{project-path}` is the project directory path with `/` replaced by `-` (e.g., `/home/user/Projects/MyApp` becomes `-home-user-Projects-MyApp`).

Write or overwrite the file with this template:

```markdown
---
name: handoff_state
description: Latest session handoff state — phase, progress, next priorities
type: project
---

**Last handoff:** YYYY-MM-DD HH:MM
**Stop reason:** <reason>
**Branch:** <branch> @ <commit>
**Phase:** <phase>

**Accomplished:** [Summary of what was built]

**Next priority:** [First item from What's Next]

**Top friction to avoid:** [Top friction point with solution]

**Handoff file:** .claude/handoffs/YYYY-MM-DD-HH-MM-handoff.md
```

---

## 6. User Presentation

After all files are written, display to the user:

1. **Confirmation block** — List all file paths written (handoff document, LATEST.md, prompt file if generated, LATEST-PROMPT.md if generated, handoff_state.md if memory updated)

2. **Continuation prompt content** — Print the full prompt text so the user can copy it directly. Label it clearly.

3. **Test and build summary** — One or two lines: pass/fail counts, build status. Do not reproduce full test output unless it was very short.

4. **Length advisory** — If the session was high-volume (10 or more commits, 5 or more friction points, or 3 or more major decisions), append: "This handoff is lengthy — consider `--compact` if you're working with limited context."

---

## 7. Flag-Specific Behavior

### `--compact`

Load `references/prompt-engineering.md` for compact formatting rules before writing. Apply those rules throughout the document. Use the compact continuation prompt template instead of the full template.

### `--reason <value>`

Set `stop_reason` in the YAML frontmatter to the provided value. Adjust the tone of "What's Next" based on the reason:

- `done` — Frame as optional next steps or polish; the core work is complete
- `blocked` — Lead with what is blocking and what context the next session needs to unblock it
- `interrupted` — Lead with current in-progress state; make it easy to pick up mid-task
- `handoff` — Write for a different person who has no session context; be more explicit about background
- Any other value — Use as-is in frontmatter, no special tone adjustment

### `--interactive`

Before gathering any context, pause and present up to 3 questions from the pool defined in SKILL.md. Wait for answers. Inject answers into the User Notes section. Use answers to inform and sharpen all other sections (especially Refined Intent and What's Next).

### `--note "text"`

Each `--note` value is appended as a bullet in the User Notes section. Multiple `--note` flags produce multiple bullets. Notes are appended after passing through the Rule 2 redaction filter defined in Section 10. If you need to bypass redaction for a specific note, use `--note-raw` instead.

### `--note-raw "text"`

Identical to `--note` but skips the Rule 2 redaction filter defined in Section 10. The text is appended to User Notes verbatim with no scrubbing. Intended as a consent-based escape hatch when the user needs to inject content they know contains a pattern match but do not want redacted. Each occurrence increments the frontmatter `raw_notes_count` counter.

### `--no-prompt`

Skip steps 5 and 6 of the File Writing Procedure. Do not generate or write any prompt file. Still display confirmation and test/build summary in user presentation.

### `--no-memory`

Skip the Memory Update Procedure (Section 5) entirely. Still write all handoff and prompt files. Still perform the MEMORY.md index update (Section 9).

### `--no-priority`

Omit the "What's Next" section from the handoff document body. Do not include a placeholder — remove the section heading entirely. The continuation prompt should still reference "next priority" as "(see handoff for context)" if `--no-priority` was used.

### `--no-carryforward`

Suppresses the carry-forward logic described in Section 2. The new `What's Next` section is generated using only this session's signals, ignoring any unresolved items from `LATEST.md`. Use when the user has pivoted focus or is explicitly closing out stale priorities.

---

## 8. Edge Cases to Handle

**No git repo detected**

Skip all git-dependent gathering: `git log`, `git status`, `git diff`. Set `branch`, `last_commit`, and `last_commit_message` to `"n/a"` in frontmatter. Set `uncommitted_changes` to `false`. Warn the user: "No git repository detected — git context skipped." Still generate the document from conversation context.

**No test or build command detected**

Skip test and build execution. In the Current State section, note "Test command not detected" and/or "Build command not detected" rather than leaving the fields blank. Set `test_summary` to `"not detected"` and `build_status` to `"skipped"` in frontmatter.

**Very short session**

Still generate a complete handoff. Even brief sessions may contain a meaningful decision or a friction point worth preserving. Do not skip sections — use "None" or "N/A" only if a section genuinely has no content.

**`.claude/handoffs/` directory does not exist**

Create it automatically in step 2 of the File Writing Procedure. Do not prompt the user or ask for confirmation.

**No `docs/` or spec files found**

The "What's Next" section relies on conversation context and memory only. Add a note at the top of What's Next: "No specs or plans found — priorities derived from conversation context."

**LATEST.md already exists from a prior session**

Read the `last_commit` field from its frontmatter to scope `git log` to commits since that hash. This avoids re-summarizing history that was already captured.

---

## 9. MEMORY.md Index Update

This is a distinct final step, separate from the Memory Update Procedure in Section 5. Perform it regardless of `--no-memory`.

1. Determine the project memory path: `~/.claude/projects/{project-path}/memory/MEMORY.md`
2. Read the file
3. Search for the string `handoff_state.md` in the file contents
4. If not found, append this line to the file:

```
- [handoff_state.md](handoff_state.md) — Latest session handoff state — phase, progress, next priorities
```

5. If already found, leave MEMORY.md unchanged

Do not modify any other entries in MEMORY.md. Only append the missing line.

---

## 10. Sensitive Data Handling

This skill MUST NOT leak credentials into generated handoffs. Apply these four rules during generation, before any file is written. Every rule applies in both Full and Compact modes identically.

### 10.1 Rule 1 — Never quote file contents from sensitive paths

Do not read-and-embed contents from files matching any of these patterns:

| Category | Patterns |
|---|---|
| Env files | `.env`, `.env.*`, `*.env` (in any directory) |
| Secrets | `**/secrets.*`, `**/credentials.*`, `**/*-secrets.*` |
| Keys | `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*.p12`, `*.pfx` |
| Tool credential stores | `.netrc`, `.aws/credentials`, `.ssh/config`, `.ssh/id_*` |

Also treat as sensitive: any file in `.gitignore` whose path matches one of the categories above. Gitignored files in other categories (build artifacts, caches, `node_modules`) remain referenceable by path — the `.gitignore` check is only used to catch project-specific secret conventions.

**Allowed:** variable names and filenames. Example: "added `OPENAI_API_KEY` entry to `.env`" is fine. Embedding the value is not.

### 10.2 Rule 2 — Redact credential patterns in pulled content

Any text synthesized from the conversation window, tool output, or read non-sensitive files MUST pass through this pattern filter before landing in the output. Matches are replaced with `[REDACTED:<type>]`. For `assignment-secret` and `db-url-credential`, replace only the value portion and preserve the key name or URL scheme.

| Type | Pattern |
|---|---|
| `openai-key` | `sk-[A-Za-z0-9_-]{20,}` |
| `github-pat` | `gh[puso]_[A-Za-z0-9]{36,}` |
| `slack-token` | `xox[bpa]-[A-Za-z0-9-]+` |
| `aws-access-key` | `(AKIA\|ASIA)[0-9A-Z]{16}` |
| `jwt` | `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` |
| `bearer-token` | `Bearer\s+[A-Za-z0-9._~+/=-]{20,}` |
| `assignment-secret` | `(?i)\b(password\|passwd\|pwd\|token\|secret\|api[_-]?key\|auth[_-]?token\|access[_-]?token)\b\s*[:=]\s*["']?([^\s"'<>]{8,})` |
| `db-url-credential` | `\b(postgres\|postgresql\|mysql\|mongodb\|mongodb\+srv\|redis\|rediss\|amqp\|amqps)://([^:@\s/]+):([^@\s/]+)@` |
| `private-key-header` | `-----BEGIN (RSA \|EC \|DSA \|OPENSSH \|PGP )?PRIVATE KEY-----` (if matched, drop the entire block through the matching END line and replace with `[REDACTED:private-key]`) |

Maintain a running count of redactions applied. Write the total to the YAML frontmatter as `redactions_applied: <N>`. Emit this field only when N > 0.

### 10.3 Rule 3 — `--note` values pass through Rule 2

Each `--note "<text>"` value is appended verbatim to User Notes **after** passing through the Rule 2 filter. This replaces the original "appended verbatim, not paraphrased" rule in Section 7.

**Escape hatch — `--note-raw "<text>"`:** skips Rule 2 for that single note. The user explicitly asks for no scrubbing. When any `--note-raw` is used, write `raw_notes_count: <N>` to the frontmatter so the bypass is visible. Emit this field only when N > 0.

### 10.4 Rule 4 — Test/build output is capped and filtered

Before embedding captured test or build output into the Current State section or the `test_summary` frontmatter field:

1. Cap the output at 40 lines per command. If the original exceeded 40 lines, keep the first 20 and last 20 joined by a `... <N> lines elided ...` marker.
2. Pass the capped output through the Rule 2 filter.

### 10.5 Failure mode

If the redaction filter errors on a specific field (regex engine failure, malformed input, unicode issue), drop that field's content and replace with the marker `[content dropped: redaction error]`. Do not pass the original content through. Do not abort generation for other fields — the rest of the handoff should still be produced.

### 10.6 Frontmatter additions

Two new optional fields:

```yaml
redactions_applied: 3   # omit when 0
raw_notes_count: 1      # omit when 0
```

Existing frontmatter fields are unchanged. The `freshness-check.sh` script ignores unknown fields, so older handoffs without these fields remain compatible with Resume Mode.

---

## 11. `--list` Mode

When the `--list` flag is passed, skip generation entirely. This mode is a read-only browse of past handoffs.

### 11.1 Procedure

1. List files in `.claude/handoffs/` matching the glob `*-handoff.md`. Exclude `LATEST.md`, `LATEST-PROMPT.md`, and any `*-prompt.md` files.
2. For each file, parse the YAML frontmatter.
3. Sort by the `created` field, descending (newest first).
4. Print the output described in Section 11.2.

### 11.2 Output format

```
Handoffs in .claude/handoffs/ (N total)

2026-04-17 14:22  main         @ a3b2c1d  phase-complete    "Wrapped Phase 2D media modules"
2026-04-10 09:15  feature/x    @ 7f3d21e  context-limit     "Started slider swipe work"
2026-04-08 17:40  feature/x    @ 22aa91f  done-for-day      "Bug triage, no commits"
```

Columns:

| # | Field | Source | Format |
|---|---|---|---|
| 1 | Timestamp | frontmatter `created` | `YYYY-MM-DD HH:MM` |
| 2 | Branch | frontmatter `branch` | left-padded to at least 10 chars |
| 3 | Commit | frontmatter `last_commit` | `@ <short-hash>` |
| 4 | Reason | frontmatter `stop_reason` | left-padded for column alignment (computed from the longest value in the current set) |
| 5 | Summary | first sentence of `## Refined Intent` (or `## Intent` in compact) | truncated to 60 chars with ellipsis if longer |

If the summary cannot be extracted (malformed file, missing section), fall back to the filename.

### 11.3 Flag validation

`--list` is mutually exclusive with every other flag. If combined with any of `--resume`, `--compact`, `--reason`, `--interactive`, `--note`, `--note-raw`, `--no-prompt`, `--no-memory`, `--no-priority`, `--no-carryforward`, emit:

> "The `--list` flag only lists past handoffs and does not combine with generation or resume flags. Re-run with `--list` alone."

Then stop. Do not proceed.

### 11.4 Edge cases

| Case | Behavior |
|---|---|
| `.claude/handoffs/` does not exist | Print "No handoffs found — directory does not exist." and exit cleanly. |
| Directory exists but no matching files | Print "No handoffs found in `.claude/handoffs/`." and exit cleanly. |
| One or more files have unparseable frontmatter | Skip those files in the list. After the list, append "Skipped N file(s) with unparseable frontmatter: [paths]." |
