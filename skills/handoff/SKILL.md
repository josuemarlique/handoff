---
name: handoff
description: >
  Generate context-transfer documents for session continuity. Triggers: "/handoff",
  "hand off", "create a handoff", "prepare handoff", "session handoff", "wrap up session",
  "continue from last handoff", "resume from handoff", "pick up where we left off".
  Produces a structured handoff document and optional continuation prompt.
  Use --resume to verify and load a previous handoff at session start.
---

# Handoff Skill

## Identity & Purpose

This skill generates context-transfer documents at the end of a session so that a future session can resume with full situational awareness. It captures what was accomplished, what changed, what decisions were made, what friction was encountered, and what should happen next. In **Resume Mode** (`--resume`), it verifies that a previous handoff exists, loads it, and walks through a structured verification checklist to confirm the project state before continuing work. The goal is zero-loss continuity between sessions regardless of context window limits, time gaps, or focus shifts. A well-executed handoff eliminates the "cold start" problem where a new session wastes its first 10-15 minutes rediscovering context that the previous session already had. The skill redacts sensitive credential patterns and refuses to quote contents of `.env`/secret files by default; see `references/handoff-generation.md` Section 10 for the full sensitive-data handling rules.

---

## Mode Detection

Determine the operating mode from the user's invocation. The two modes are mutually exclusive -- a single invocation is always one or the other.

1. **If the arguments contain `--resume`** --> **Resume Mode**
   - Load and follow `references/resume-verification.md`
   - Do NOT load generation or sentiment references.
   - The skill will run the migration preflight, locate the latest handoff at `LATEST.md` in `.handoffs/`, read it, and then systematically verify each section against the current project state (git log, file system, test results). Any drift between the handoff and reality is flagged before work begins.

2. **Otherwise** --> **Generate Mode**
   - Load and follow `references/handoff-generation.md`
   - Load `references/sentiment-analysis.md` (used for friction/blocker detection by scanning the conversation history for signs of struggle, repeated attempts, or abandoned approaches)
   - If `--compact` is present, also load `references/prompt-engineering.md` (for token-efficient formatting that preserves information density while reducing token count)
   - The skill will scan the full conversation, git history since session start, and any project specs to produce the handoff document.

If no flags are provided at all, default to Generate Mode with reason `context-limit`.

---

## Flag Parsing

| Flag | Default | Description |
|------|---------|-------------|
| *(no flags)* | -- | Full Generate Mode. Assumes `--reason context-limit`. |
| `--resume` | Off | Resume Mode. Loads the latest handoff and runs verification. |
| `--compact` | Off | Token-conscious formatting. Shorter sections, denser structure, no prose padding. |
| `--reason <reason>` | `context-limit` | Stop reason that shapes the "What's Next" section. Valid values: `context-limit`, `done-for-day`, `switching-focus`, `blocked`, `phase-complete`. |
| `--interactive` | Off | Pause to ask 2-3 clarifying questions before generating the handoff. |
| `--note "text"` | None | Inject custom context into the handoff. Repeatable: `--note "X" --note "Y"`. Each note appears in the "User Notes" section. |
| `--no-prompt` | Off | Skip generating the continuation prompt file. |
| `--no-memory` | Off | Skip updating the project memory file (`handoff_state.md`). |
| `--no-priority` | Off | Skip the "What's Next" section entirely. |
| `--list` | Off | List past handoffs and exit. Mutually exclusive with all other flags. See `references/handoff-generation.md` Section 11. |
| `--note-raw "text"` | None | Like `--note` but skips the Rule 2 redaction filter. Repeatable. Tracked via `raw_notes_count` frontmatter field. |
| `--no-carryforward` | Off | Skip automatic carry-forward of unresolved priorities from the previous handoff's "What's Next". |

---

## Host Compatibility

This skill is usable from Claude Code and Codex. Keep project handoff artifacts in `.handoffs/` for cross-agent continuity.

Project memory is host-specific:

- Claude Code: update `~/.claude/projects/{project-path}/memory/`
- Codex: update `~/.Codex/projects/{project-path}/memory/`
- Other hosts: skip global memory updates unless the user explicitly provides a target

The handoff document, `LATEST.md`, continuation prompt, and resume verification always use the shared project-local `.handoffs/` path. The legacy `.claude/handoffs/` path is copied into `.handoffs/` during migration and then left in place as an archive.

---

## Migration Preflight

Run this preflight once at the start of every invocation, before Generate Mode, Resume Mode, or `--list` handling:

1. Locate `scripts/migrate-handoffs.sh` relative to this skill's directory.
2. Run it from the current project root.
3. If the script prints a migration notice, reproduce that notice to the user before continuing.

The migration script copies `.claude/handoffs/` into `.handoffs/` only when `.handoffs/` does not already exist. It never deletes `.claude/handoffs/`. Tell the user that `.claude/handoffs/` was left in place as an archive and that they can delete `.claude/handoffs/` after confirming `.handoffs/` contains their history.

If the script is unavailable, perform the same fallback manually:

```bash
if [ ! -d .handoffs ] && [ -d .claude/handoffs ]; then
  mkdir -p .handoffs
  cp -pR .claude/handoffs/. .handoffs/
fi
```

Then print the same archive/delete notice.

---

## Flag Validation Rules

**Invalid combinations -- warn the user and do not proceed:**

- `--resume` combined with any of `--compact`, `--reason`, `--note`: Resume Mode reads an existing handoff; it does not generate one. These flags are generation-only. Emit a warning:
  > "The `--resume` flag enters Resume Mode, which loads and verifies an existing handoff. The flags `--compact`, `--reason`, and `--note` only apply to Generate Mode and will be ignored. Did you mean to run without `--resume`?"

- `--list` combined with any other flag: `--list` is a read-only browse mode and does not combine with generation or resume flags. Emit a warning:
  > "The `--list` flag only lists past handoffs and does not combine with generation or resume flags. Re-run with `--list` alone."

**Legal but confirm intent:**

- `--no-prompt` combined with `--no-memory`: This produces a handoff document with no continuation prompt and no memory update. The handoff file is still written, but nothing else persists. Confirm:
  > "You've passed both `--no-prompt` and `--no-memory`. The handoff document will be generated but no continuation prompt or memory update will be created. Continue?"

All other combinations are valid.

---

## `--reason` Behavioral Impact

The `--reason` value shapes the tone and content of the "What's Next" section in the generated handoff.

| Reason | Effect on "What's Next" |
|--------|------------------------|
| `context-limit` | Default. Lists priorities in execution order. Neutral, task-focused tone. Assumes the next session picks up immediately. |
| `done-for-day` | Adds a brief session recap tone. No urgency language. Priorities framed as "when you return" rather than "immediately". |
| `switching-focus` | Emphasizes where to resume *this specific workstream*. Notes the switching point clearly so the user can context-switch back without re-reading everything. |
| `blocked` | Leads with the blocker: what it is, what's needed to unblock, who or what can provide it, and what parallel work can proceed in the meantime. |
| `phase-complete` | Pulls the next phase from any roadmap, PRD, or architecture specs found in the project. Includes a brief celebration of what was completed. Frames next steps as the new phase's objectives. |

---

## `--interactive` Questions

When `--interactive` is set, pause before generating and ask up to 3 questions from this pool. Select dynamically based on what was already auto-detected from the conversation and project state -- skip questions whose answers are already obvious. For example, if the conversation explicitly discussed blockers, do not ask about them.

**Question pool:**

1. "Anything the next session should know that isn't captured in the code or commits?"
2. "What should the next session prioritize first?"
3. "Any approaches you'd recommend avoiding or trying differently?"
4. "Is there context from outside this project (Slack, docs, conversations) that matters?"

Present the selected questions in a single numbered message and wait for the user to respond. Do not generate the handoff until answers are received (or the user explicitly skips with "none" or similar).

Incorporate answers into the "User Notes" section of the handoff and let them inform the tone and priorities of other sections. Specifically:
- Answers to question 1 feed into "Session Context" and "Decisions & Rationale".
- Answers to question 2 directly shape the priority ordering in "What's Next".
- Answers to question 3 feed into "Friction Log" and cautionary notes.
- Answers to question 4 feed into "User Notes" verbatim and may also appear in "Session Context".

---

## Output Directory

All handoff artifacts are written to the project root under:

```
.handoffs/
```

Auto-create the directory on first use if it does not exist. Use `mkdir -p` to handle nested creation safely.

### Generated files

Each invocation produces up to four files:

| File | Purpose |
|------|---------|
| `YYYY-MM-DD-HH-MM-handoff.md` | Timestamped handoff document. Permanent record. Never overwritten by future invocations. |
| `YYYY-MM-DD-HH-MM-prompt.md` | Timestamped continuation prompt. Permanent record. Skipped with `--no-prompt`. |
| `LATEST.md` | Copy of the most recent handoff. Overwrites the previous `LATEST.md` on each invocation. This is the file Resume Mode reads by default. |
| `LATEST-PROMPT.md` | Copy of the most recent continuation prompt. Overwrites previous. Skipped with `--no-prompt`. |

Use the system clock for timestamps. Format: `YYYY-MM-DD-HH-MM` in local time (24-hour clock).

### File creation order

1. Generate content for the handoff document.
2. Write the timestamped handoff file.
3. Copy it to `LATEST.md`.
4. If `--no-prompt` is not set, generate the continuation prompt, write the timestamped prompt file, and copy to `LATEST-PROMPT.md`.
5. If `--no-memory` is not set, update memory (see Memory Integration below).
6. Report the file paths to the user.

---

## Memory Integration

Unless `--no-memory` is set, update persistent project memory after generating the handoff. Use the current host's memory root: `~/.claude` for Claude Code, `~/.Codex` for Codex. If the host is neither Claude Code nor Codex, skip global memory updates unless the user explicitly provides a target.

1. **Write or update** `<memory-root>/projects/{project-path}/memory/handoff_state.md` with a concise summary:
   - Current phase/milestone
   - Key progress made this session
   - Top 3 next priorities
   - Active blockers (if any)
   - Path to the latest handoff file

2. **Check the MEMORY.md index** at `<memory-root>/projects/{project-path}/memory/MEMORY.md`:
   - If an entry for `handoff_state.md` already exists, leave it.
   - If no entry exists, append:
     ```
     - [handoff_state.md](handoff_state.md) — Latest session handoff state — phase, progress, next priorities
     ```

The `{project-path}` is derived from the current working directory, matching the convention used by the host's project memory system (typically the absolute path with slashes replaced by dashes, e.g., `-home-jmarlique-Projects-MyApp`).

---

## Not in Scope

This skill intentionally does not handle:

- **Cross-project handoffs** -- each handoff is scoped to the current project.
- **Auto-triggering** -- the user must invoke the skill manually.
- **Handoff cleanup or rotation** -- old files in `.handoffs/` accumulate. Manual cleanup is expected.
- **Multi-user or team workflows** -- handoffs are single-user, single-session continuity documents.
- **External integrations** -- no Slack, Linear, GitHub Issues, or other platform integrations.

---

## References to Load

Load the appropriate reference files based on the detected mode. These files contain the detailed procedures, templates, and checklists that this SKILL.md intentionally does not duplicate. All reference paths are relative to this skill's directory (the directory containing this SKILL.md file).

### Generate Mode

Load these files at the start of generation, before scanning the conversation or project state:

- `references/handoff-generation.md` -- Full generation procedure, section-by-section template, required and optional fields, and the complete output format specification. This is the primary procedural document for Generate Mode.
- `references/sentiment-analysis.md` -- Friction detection rules and heuristics for scanning conversation history. Defines what constitutes a struggle signal (repeated errors, backtracking, abandoned approaches, explicit frustration) and how to surface those in the Friction Log section.
- If `--compact` is set: `references/prompt-engineering.md` -- Token-efficient formatting guidelines. Covers compression techniques (abbreviation conventions, section collapsing, implicit-over-explicit patterns) that reduce token count while preserving all information needed for session continuity.

### Resume Mode

Load this file before reading the handoff:

- `references/resume-verification.md` -- Verification checklist, state-comparison procedure against git and file system, drift detection rules, and recovery steps for when reality diverges from the handoff.

---

## Examples to Consult

Before generating output, review the appropriate example for formatting and tone:

- `examples/handoff-full.md` -- Full-format handoff (default, no `--compact`).
- `examples/handoff-compact.md` -- Compact-format handoff (when `--compact` is set).

These are reference examples, not rigid templates. Adapt structure and length to the actual session content. A short session with one task completed may produce a handoff half the length of the example. A complex multi-feature session may exceed it. The examples establish tone, section ordering, and the level of detail expected -- not a fixed word count.
