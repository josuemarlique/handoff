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

Each `--note` value is appended as a bullet in the User Notes section. Multiple `--note` flags produce multiple bullets. Notes are appended verbatim, not paraphrased.

### `--no-prompt`

Skip steps 5 and 6 of the File Writing Procedure. Do not generate or write any prompt file. Still display confirmation and test/build summary in user presentation.

### `--no-memory`

Skip the Memory Update Procedure (Section 5) entirely. Still write all handoff and prompt files. Still perform the MEMORY.md index update (Section 9).

### `--no-priority`

Omit the "What's Next" section from the handoff document body. Do not include a placeholder — remove the section heading entirely. The continuation prompt should still reference "next priority" as "(see handoff for context)" if `--no-priority` was used.

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
