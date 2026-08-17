# Handoff Generation Reference

Detailed procedure for generating a handoff document in Generate Mode.

---

## 1. Context Gathering Procedure

Run all tool-based commands in parallel where dependencies allow. LLM-generated content comes from the conversation context window - never from tool extraction.

### Tool-Gathered (via Bash/Read)

Run these in parallel as a first batch:

```bash
git log --oneline -20
# If LATEST.md exists, scope to commits since the last handoff commit hash found in its frontmatter
git status
git diff --stat
```

Test and build command discovery - apply this heuristic in order, stopping at the first match:

1. Read `package.json` - look for `scripts.test` and `scripts.build`
2. Read `Makefile` - look for `test` and `build` targets
3. Read `Cargo.toml` - infer `cargo test` and `cargo build`
4. Read `go.mod` - infer `go test ./...` and `go build ./...`
5. Read `pyproject.toml` - infer `pytest`

Once discovered, run test and build commands and capture full output. Run them in parallel if independent.

Also read in parallel:
- `docs/**` for specs, plans, roadmaps
- `.handoffs/LATEST.md` for previous handoff context when present
- `.claude/features/*/prd.md`, `.claude/features/*/architecture.md` for feature context
- `.Codex/features/**/*.md`, `.codex/features/**/*.md` for Codex feature context
- Host project memory for phase and status context. Claude Code keeps this at `~/.claude/projects/{project-path}/memory/MEMORY.md`. Other hosts store memory differently or not at all - read it through whatever memory tool the host exposes, and skip this input if there is none.

### LLM-Generated (from conversation context window)

These are synthesized by the model - do NOT attempt to extract them with file tools:

- **Refined intent** - What the session set out to accomplish after any clarification exchanges, not the raw first message
- **Decisions made** - Architecture and design choices surfaced during the session, with the reasoning behind each
- **Friction points** - Problems encountered, failed approaches, and the solutions that worked. Load `references/sentiment-analysis.md` for detection patterns before scanning
- **Sentiment scan** - Frustration signals, repeated attempts, rollbacks, expressions of confusion or blocked progress
- **Open questions** - Anything raised and left unanswered. Required in `long` mode, optional otherwise

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
mode: compact/full/long
goal_file: "<path to the timestamped goal file, or omit when --no-goal>"
---
```

### Body Sections

Sections appear in this order. The first two are required in every mode and are never suppressed by a flag.

| # | Section | Required | Notes |
|---|---|---|---|
| 1 | `## Start Here` | Always | Verbatim from `references/next-session-contract.md` Section 2 |
| 2 | `## TL;DR` | Always | Five bullets, from `references/next-session-contract.md` Section 3 |
| 3 | `## Refined Intent` | Always | |
| 4 | `## What Was Built` | Always | |
| 5 | `## Decisions Made` | Always | |
| 6 | `## Friction Points` | Always | |
| 7 | `## Current State` | Always | |
| 8 | `## What's Next` | Unless `--no-priority` | |
| 9 | `## Environment Notes` | Always | |
| 10 | `## User Notes` | Only when notes exist | |
| 11 | `## File-By-File Notes` | `long` mode only | |
| 12 | `## Commands That Matter` | `long` mode only | |
| 13 | `## Open Questions` | `long` mode only | |
| 14 | `## Glossary` | `long` mode only | |

**`## Start Here`**

Copy the block from `references/next-session-contract.md` Section 2 verbatim. Do not rewrite it to match the session's tone. It is the same text every time on purpose - the next session should be able to recognize it instantly.

**`## TL;DR`**

Five bullets, using the shape in `references/next-session-contract.md` Section 3. Write this **last**, after every other section exists, so it summarizes what is actually there rather than what you planned to write.

**`## Refined Intent`**

What this session set out to accomplish - the clarified understanding after any back-and-forth, not the raw first message. One to three sentences. Captures the "why" behind the work, not just the tasks.

**`## What Was Built`**

Concrete deliverables grouped logically, not chronologically. Subsections as needed:

- Files created and modified (with brief description of purpose)
- Features implemented
- Tests added

Avoid blow-by-blow narration. Group by concern.

**`## Decisions Made`**

Architecture and design decisions with reasoning. Format each entry as:

```
**[Decision title]:** [What was decided]. [Why - the tradeoff, constraint, or goal that drove it].
```

Prioritize "why" over "what". Skip trivial or purely mechanical choices.

**`## Friction Points`**

Problems encountered, failed approaches, workarounds. Use the entry format from `references/sentiment-analysis.md`. Each entry includes:

- What the problem was
- What was tried (including failed attempts)
- What worked (or current status if unresolved)

The top entry here also becomes the "Do not do" line in the goal file, so make the first entry the one that would waste the most time if repeated.

**`## Current State`**

- Branch name and latest commit hash + message
- Test results (from automatically-run test command): pass/fail count, suite breakdown
- Build status (from automatically-run build command)
- Description of any uncommitted changes present

**`## What's Next`**

Priority-ordered list derived from specs/plans/roadmap context plus conversation signals. Behavior varies by the `--reason` flag (see Section 8 here, and the `--reason` Behavioral Impact table in SKILL.md). Each item should be actionable - specific enough that the next session knows where to start without re-reading everything.

**Carry-forward from the previous handoff:** after the Storage Preflight, if `.handoffs/LATEST.md` exists and contains a parseable `## What's Next` section, evaluate each previous priority against this session's signals (commit messages since the previous `last_commit`, paths in `git diff --name-only`, conversation topics). An item is considered **addressed** when two or more signal categories match, OR when the model is confident from the conversation that the item was completed or explicitly abandoned. Everything else is **unaddressed** and carried forward. Bias: on ambiguity, carry forward.

When at least one item is carried forward, structure the `What's Next` section as two subsections:

    ### Carried forward from previous session

    - [item text, verbatim from prior handoff] - not touched this session
    - [item text, verbatim] - partially addressed: [one-line note]
    - [item text, verbatim] - blocked: [one-line reason, if detected]

    ### New priorities

    1. [New priority #1]
    2. [New priority #2]

When nothing is carried forward, use the original single-list format (no subsection headings).

Suppressed by `--no-carryforward`. Also suppressed when `--no-priority` is set (there's no What's Next section to attach to).

**Flag work that should be split across an agent team.** When two or more priorities are independent of each other, say so explicitly, for example: "Items 2 and 3 do not depend on each other - good candidates to run as parallel teammates." This is what makes the agent-teams instruction in `## Start Here` actionable instead of abstract.

**`## Environment Notes`**

- Dependencies installed during the session
- Configuration changes made
- New tools, scripts, or aliases introduced
- Anything about the local environment that future sessions need to know

**`## User Notes`**

Custom context from `--note` flags or `--interactive` mode answers. Only include this section if the user provided notes. If absent, omit the section entirely.

### Long-mode-only sections

These four sections appear only when the mode is `long`. See `references/prompt-engineering.md` Section 3 for the formatting rules.

**`## File-By-File Notes`** - Every file touched this session, with what changed in it and why it matters to the next session.

**`## Commands That Matter`** - The exact commands needed to work on this project: install, test, build, lint, run, plus any one-off command that was hard to get right. Copy-paste ready.

**`## Open Questions`** - Anything raised and not settled, with who or what can answer it.

**`## Glossary`** - Project-specific terms, short forms, and internal names used anywhere in this handoff, each with a plain-language definition. This exists so the next session can follow the `## Start Here` rule about spelling out short forms.

---

## 3. Continuation Prompt Templates

The continuation prompt is the long-form partner to the kickoff block. The kickoff block is one line the user pastes; this file is there for when the user wants to hand over real context in a message instead of pointing at a path.

### Full and long modes

```
You are continuing a previous session.

How to write back to me: plain, everyday language, like you are explaining it to a
smart middle school student. Spell out every short form the first time you use it.
Start every reply with a short TL;DR of 2 to 5 bullets and end with a one-line TL;DR.

How to work: use agent teams for independent pieces of work and run them in parallel.
Let teammates message each other when their work overlaps. Keep this main chat for
decisions and review so its context stays small.

First, read .handoffs/LATEST.md for full context, then run /handoff --resume to verify
freshness before proceeding.

Key context:
- Project: [name]
- Phase: [current phase]
- Branch: [branch]
- Last session accomplished: [1-2 sentence summary]
- Priority for this session: [first item from What's Next]
- Critical friction to avoid: [top friction point]
- Work that can run in parallel: [items that are independent, or "none"]

For full details including all decisions, friction points, and environment notes,
see the handoff document.
```

### Compact mode

```
Continue from .handoffs/LATEST.md - run /handoff --resume first.
Write plain, middle-school level, spell out short forms, TL;DR first and last.
Use agent teams for parallel work; keep this chat small.
Project: [name] | Branch: [branch] | Phase: [phase]
Last: [one-line summary] | Next: [one-line priority]
Avoid: [one-line top friction point]
```

---

## 4. File Writing Procedure

Execute these steps in order.

1. Generate a timestamp: `TS=$(date +%Y-%m-%d-%H-%M)` and a day: `DAY=$(date +%Y-%m-%d)`.
2. Create the day folder: `mkdir -p ".handoffs/$DAY"`.
3. Write the handoff document to `.handoffs/$DAY/$TS-handoff.md`.
4. Copy the same content to `.handoffs/LATEST.md` (full copy, not a symlink).
5. If `--no-prompt` was not passed: write the continuation prompt to `.handoffs/$DAY/$TS-prompt.md` and copy it to `.handoffs/LATEST-PROMPT.md`.
6. If `--no-goal` was not passed: write the goal file to `.handoffs/$DAY/$TS-goal.md` and copy it to `.handoffs/LATEST-GOAL.md`.

Never write a timestamped file to the top level of `.handoffs/`. Never write a `LATEST*.md` file inside a day folder. See SKILL.md Storage Rules.

---

## 5. Goal File Procedure

Skip this entire procedure if `--no-goal` was passed.

1. Load `references/next-session-contract.md` Sections 4 and 5 - Section 4 for how `/goal` really works, Section 5 for the template, the size budget, and the rules for writing the `## Finish line` condition.
2. Fill the template from sections that already exist in the handoff:
   - "The mission" comes from `## Refined Intent`, rewritten in the user's terms.
   - "Do these, in this order" comes from the first three items of `## What's Next`. When carry-forward produced two subsections, take carried-forward items first - they have been waiting longest.
   - "Do not do" comes from the top one or two entries of `## Friction Points`, each written as an instruction with its reason.
   - "Where we are" comes from `## Current State`.
3. Pass the whole file through the Rule 2 redaction filter from Section 10. Count any redactions toward the same `redactions_applied` total.
4. Count the characters. If the body is over 3,000, cut using the order given in `next-session-contract.md` Section 5.2 and count again.
5. Write the file, then copy it to `.handoffs/LATEST-GOAL.md`.
6. Record the timestamped path in the handoff frontmatter as `goal_file`.

The goal file is the same size in every verbosity mode. `--long` does not make it longer.

---

## 6. Memory Update Procedure

Skip this entire procedure if `--no-memory` was passed.

**Host memory is not portable. Do not invent a path.**

- **Claude Code:** write to `~/.claude/projects/{project-path}/memory/`. This is a real directory tree of markdown files.
- **Codex:** there is no equivalent markdown tree. Codex keeps memory in a database under `~/.codex/`, not in `~/.Codex/projects/.../memory/`. If the host exposes a memory tool, use that tool. If it does not, skip the global memory update and say so in one line.
- **Any other host:** skip the global memory update unless the user names a target.

Skipping is safe. The durable record is `.handoffs/`, which every host reads the same way.

**Claude Code target path:** `~/.claude/projects/{project-path}/memory/handoff_state.md`

Where `{project-path}` is the project directory path with `/` replaced by `-` (e.g., `/home/user/Projects/MyApp` becomes `-home-user-Projects-MyApp`).

Write or overwrite the file with this template:

```markdown
---
name: handoff_state
description: Latest session handoff state - phase, progress, next priorities
type: project
---

**Last handoff:** YYYY-MM-DD HH:MM
**Stop reason:** <reason>
**Mode:** <compact|full|long>
**Branch:** <branch> @ <commit>
**Phase:** <phase>

**Accomplished:** [Summary of what was built]

**Next priority:** [First item from What's Next]

**Top friction to avoid:** [Top friction point with solution]

**Handoff file:** .handoffs/YYYY-MM-DD/YYYY-MM-DD-HH-MM-handoff.md
**Goal file:** .handoffs/LATEST-GOAL.md
```

---

## 7. User Presentation

After all files are written, display to the user in this order.

1. **Confirmation block** - List every file path written: the handoff document, `LATEST.md`, the prompt file and `LATEST-PROMPT.md` if generated, the goal file and `LATEST-GOAL.md` if generated, and `handoff_state.md` if memory was updated.

2. **Test and build summary** - One or two lines: pass/fail counts, build status. Do not reproduce full test output unless it was very short.

3. **Length advisory** - If the session was high-volume (10 or more commits, 5 or more friction points, or 3 or more major decisions) and the mode was not already `compact`, append: "This handoff is lengthy - consider `--compact` if the next session is working with limited context."

4. **The kickoff block - always last.** Use the exact format in `references/next-session-contract.md` Section 6. Nothing goes after it. It is the thing the user came for, so it should be the last thing on screen, ready to copy.

---

## 8. Flag-Specific Behavior

### `--mode compact` / `--compact`

Load `references/prompt-engineering.md` and apply its Section 2 rules throughout the document. Use the compact continuation prompt template. `## Start Here` and `## TL;DR` are still emitted in full - they are not compressed.

### `--mode long` / `--long`

Load `references/prompt-engineering.md` and apply its Section 3 rules. Emit the four extra sections listed in Section 2 of this file. Do not drop detail for length anywhere in the document.

### `--mode full` / no mode flag

Default. Load `references/prompt-engineering.md` only if you need the Section 1 formatting reminders.

### `--reason <value>`

Set `stop_reason` in the YAML frontmatter to the provided value and adjust the tone of "What's Next" using the table in SKILL.md under "`--reason` Behavioral Impact". Values are `context-limit`, `done-for-day`, `switching-focus`, `blocked`, and `phase-complete`. Any other value is written to frontmatter as-is with no tone adjustment.

### `--interactive`

Before gathering any context, pause and present up to 3 questions from the pool defined in SKILL.md. Wait for answers. Inject answers into the User Notes section. Use answers to inform and sharpen all other sections, especially Refined Intent, What's Next, and the goal file's ordered list.

### `--note "text"`

Each `--note` value is appended as a bullet in the User Notes section. Multiple `--note` flags produce multiple bullets. Notes are appended after passing through the Rule 2 redaction filter defined in Section 10. If you need to bypass redaction for a specific note, use `--note-raw` instead.

### `--note-raw "text"`

Identical to `--note` but skips the Rule 2 redaction filter defined in Section 10. The text is appended to User Notes verbatim with no scrubbing. Intended as a consent-based escape hatch when the user needs to inject content they know contains a pattern match but do not want redacted. Each occurrence increments the frontmatter `raw_notes_count` counter.

### `--no-goal`

Skip Section 5 entirely. Omit the `goal_file` frontmatter field. In the kickoff block, drop the `/goal` line and point line 1 at `.handoffs/LATEST.md` only, with a one-line note that no goal file was written this run.

### `--no-prompt`

Skip step 5 of the File Writing Procedure. Do not generate or write any prompt file. Still display confirmation, test/build summary, and the kickoff block.

### `--no-memory`

Skip the Memory Update Procedure (Section 6) and the MEMORY.md index update (Section 10.7) entirely. Still write all handoff, prompt, and goal files.

### `--no-priority`

Omit the "What's Next" section from the handoff document body. Do not include a placeholder - remove the section heading entirely. The `## TL;DR` "What is next" bullet becomes "see handoff for context".

**With `--reason blocked`:** the blocker still has to land somewhere. Put it in `## Current State` instead, as a line starting `**Blocked by:**`, and make it the "Watch out for" bullet in `## TL;DR`. Losing the blocker because the priority section was suppressed is the one failure this combination can cause. The continuation prompt references "next priority" as "(see handoff for context)". The goal file's ordered list falls back to the top items from `## Open Questions` or `## Friction Points`; if neither yields anything, the goal file is still written with the mission and working agreement, and the ordered list says "Confirm priorities with me before starting."

### `--no-carryforward`

Suppresses the carry-forward logic described in Section 2. The new `What's Next` section is generated using only this session's signals, ignoring any unresolved items from `LATEST.md`. Use when the user has pivoted focus or is explicitly closing out stale priorities.

---

## 9. Edge Cases to Handle

**No git repo detected**

Skip all git-dependent gathering: `git log`, `git status`, `git diff`. Set `branch`, `last_commit`, and `last_commit_message` to `"n/a"` in frontmatter. Set `uncommitted_changes` to `false`. Warn the user: "No git repository detected - git context skipped." Still generate the document from conversation context.

**No test or build command detected**

Skip test and build execution. In the Current State section, note "Test command not detected" and/or "Build command not detected" rather than leaving the fields blank. Set `test_summary` to `"not detected"` and `build_status` to `"skipped"` in frontmatter.

**Very short session**

Still generate a complete handoff. Even brief sessions may contain a meaningful decision or a friction point worth preserving. Do not skip sections - use "None" or "N/A" only if a section genuinely has no content. `## Start Here`, `## TL;DR`, and the goal file are still written.

**`.handoffs/` directory does not exist**

Create it automatically in step 2 of the File Writing Procedure. Do not prompt the user or ask for confirmation.

**Handoffs found in a wrong location**

Run the Storage Preflight from SKILL.md before reading or writing handoff files. It copies stray history into `.handoffs/`, leaves the originals in place as archives, and folds loose files into day folders. Reproduce its notice to the user. Never start writing into the wrong location just because history is already there.

**A day folder already exists**

Expected - several handoffs a day is normal. `mkdir -p` is safe. Only overwrite a timestamped file if the exact same minute is hit twice; in that case append `-2` to the timestamp rather than clobbering the earlier file.

**No `docs/` or spec files found**

The "What's Next" section relies on conversation context and memory only. Add a note at the top of What's Next: "No specs or plans found - priorities derived from conversation context."

**LATEST.md already exists from a prior session**

Read the `last_commit` field from `.handoffs/LATEST.md` frontmatter to scope `git log` to commits since that hash. This avoids re-summarizing history that was already captured.

---

## 10. Sensitive Data Handling

This skill MUST NOT leak credentials into generated handoffs. Apply these rules during generation, before any file is written. Every rule applies identically in `compact`, `full`, and `long` modes, and to the goal file and continuation prompt as well as the handoff document.

### 10.1 Rule 1 - Never quote file contents from sensitive paths

Do not read-and-embed contents from files matching any of these patterns:

| Category | Patterns |
|---|---|
| Env files | `.env`, `.env.*`, `*.env` (in any directory) |
| Secrets | `**/secrets.*`, `**/credentials.*`, `**/*-secrets.*` |
| Keys | `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*.p12`, `*.pfx` |
| Tool credential stores | `.netrc`, `.aws/credentials`, `.ssh/config`, `.ssh/id_*` |

Also treat as sensitive: any file in `.gitignore` whose path matches one of the categories above. Gitignored files in other categories (build artifacts, caches, `node_modules`) remain referenceable by path - the `.gitignore` check is only used to catch project-specific secret conventions.

**Allowed:** variable names and filenames. Example: "added `OPENAI_API_KEY` entry to `.env`" is fine. Embedding the value is not.

### 10.2 Rule 2 - Redact credential patterns in pulled content

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

Maintain a running count of redactions applied across the handoff document, the continuation prompt, and the goal file. Write the total to the YAML frontmatter as `redactions_applied: <N>`. Emit this field only when N > 0.

### 10.3 Rule 3 - `--note` values pass through Rule 2

Each `--note "<text>"` value is appended verbatim to User Notes **after** passing through the Rule 2 filter.

**Escape hatch - `--note-raw "<text>"`:** skips Rule 2 for that single note. The user explicitly asks for no scrubbing. When any `--note-raw` is used, write `raw_notes_count: <N>` to the frontmatter so the bypass is visible. Emit this field only when N > 0. Raw notes are never copied into the goal file, because the goal file is meant to be pasted into a chat box.

### 10.4 Rule 4 - Test/build output is capped and filtered

Before embedding captured test or build output into the Current State section or the `test_summary` frontmatter field:

1. Cap the output at 40 lines per command. If the original exceeded 40 lines, keep the first 20 and last 20 joined by a `... <N> lines elided ...` marker.
2. Pass the capped output through the Rule 2 filter.

In `long` mode the cap rises to 120 lines per command, using the same first-half/last-half elision. The Rule 2 filter still applies.

### 10.5 Failure mode

If the redaction filter errors on a specific field (regex engine failure, malformed input, unicode issue), drop that field's content and replace with the marker `[content dropped: redaction error]`. Do not pass the original content through. Do not abort generation for other fields - the rest of the handoff should still be produced.

### 10.6 Frontmatter additions

Two optional fields:

```yaml
redactions_applied: 3   # omit when 0
raw_notes_count: 1      # omit when 0
```

The `freshness-check.sh` script ignores unknown fields, so older handoffs without these fields remain compatible with Resume Mode.

### 10.7 MEMORY.md Index Update

This is a distinct final step, separate from the Memory Update Procedure in Section 6. Skip it when `--no-memory` was passed. It applies to Claude Code only, because it edits a markdown index file that other hosts do not have.

1. Determine the project memory path: `~/.claude/projects/{project-path}/memory/MEMORY.md`
2. Read the file
3. Search for the string `handoff_state.md` in the file contents
4. If not found, append this line:

```
- [handoff_state.md](handoff_state.md) - Latest session handoff state - phase, progress, next priorities
```

5. If already found, leave MEMORY.md unchanged

Do not modify any other entries in MEMORY.md. Only append the missing line.

---

## 11. `--list` Mode

When the `--list` flag is passed, skip generation entirely. This mode is a read-only browse of past handoffs.

### 11.1 Procedure

1. Run the Storage Preflight.
2. Find handoff files recursively: every file under `.handoffs/` matching `*-handoff.md`, including files inside `YYYY-MM-DD/` day folders. Exclude `LATEST.md`, `LATEST-PROMPT.md`, `LATEST-GOAL.md`, and any `*-prompt.md` or `*-goal.md` file.

   ```bash
   find .handoffs -type f -name '*-handoff.md' | sort -r
   ```

3. For each file, parse the YAML frontmatter.
4. Sort by the `created` field, descending (newest first).
5. Print the output described in Section 11.2.

### 11.2 Output format

Group by day folder so the printed list mirrors the folder layout.

```
Handoffs in .handoffs/ (N total across M days)

2026-08-16
  14:22  main         @ a3b2c1d  phase-complete   long     "Wrapped Phase 2D media modules"
  09:15  main         @ 7f3d21e  context-limit    full     "Started slider swipe work"

2026-08-14
  17:40  feature/x    @ 22aa91f  done-for-day     compact  "Bug triage, no commits"
```

Columns, after the day heading:

| # | Field | Source | Format |
|---|---|---|---|
| 1 | Time | frontmatter `created` | `HH:MM` |
| 2 | Branch | frontmatter `branch` | left-padded to at least 10 chars |
| 3 | Commit | frontmatter `last_commit` | `@ <short-hash>` |
| 4 | Reason | frontmatter `stop_reason` | left-padded for column alignment (computed from the longest value in the current set) |
| 5 | Mode | frontmatter `mode` | `full` when the field is missing (handoffs written before modes existed) |
| 6 | Summary | first sentence of `## Refined Intent` (or `## Intent` in compact) | truncated to 60 chars with ellipsis if longer |

If the summary cannot be extracted (malformed file, missing section), fall back to the filename.

### 11.3 Flag validation

`--list` is mutually exclusive with every other flag. If combined with any other flag, emit:

> "The `--list` flag only lists past handoffs and does not combine with generation or resume flags. Re-run with `--list` alone."

Then stop. Do not proceed.

### 11.4 Edge cases

| Case | Behavior |
|---|---|
| `.handoffs/` does not exist | Print "No handoffs found - directory does not exist." and exit cleanly. |
| Directory exists but no matching files | Print "No handoffs found in `.handoffs/`." and exit cleanly. |
| Files still sitting loose at the top level | The Storage Preflight folds them into day folders first, so this resolves itself. If a file has no date prefix and cannot be folded, list it under a `(undated)` heading. |
| One or more files have unparseable frontmatter | Skip those files in the list. After the list, append "Skipped N file(s) with unparseable frontmatter: [paths]." |
