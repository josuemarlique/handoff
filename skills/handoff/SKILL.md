---
name: handoff
description: >
  Generate context-transfer documents for session continuity. Triggers: "$handoff", "/handoff",
  "hand off", "create a handoff", "prepare handoff", "session handoff", "wrap up session",
  "continue from last handoff", "resume from handoff", "pick up where we left off".
  Produces a structured handoff document, a short goal file sized for /goal, and a
  copy-paste kickoff block for the next chat. Use --resume to verify and load a previous
  handoff at session start.
---

# Handoff Skill

## Identity & Purpose

This skill generates context-transfer documents at the end of a session so that a future session can resume with full situational awareness. It captures what was accomplished, what changed, what decisions were made, what friction was encountered, and what should happen next. In **Resume Mode** (`--resume`), it verifies that a previous handoff exists, loads it, and walks through a structured verification checklist to confirm the project state before continuing work. The goal is zero-loss continuity between sessions regardless of context window limits, time gaps, or focus shifts. A well-executed handoff eliminates the "cold start" problem where a new session wastes its first 10-15 minutes rediscovering context that the previous session already had.

Three things ship with every handoff by default:

1. **The handoff document** - the full record.
2. **The goal file** - a short brief holding the mission, the first three priorities, what to avoid, and a ready-made `/goal` finish-line condition.
3. **The kickoff block** - the exact text to paste into the next chat, printed at the end of the run.

Every handoff also opens with a `## Start Here` block that tells the next session how to write (plain language, TL;DR first) and how to work (fan work out to a team of subagents, keep the main chat small). See `references/next-session-contract.md`.

One thing worth knowing before reading further: `/goal` in Claude Code sets a **finish line**, not a place to store context. It arms a check that runs after each turn and keeps Claude working until the condition is met, and the evaluator can only see the conversation - it cannot read files. That is why the kickoff block leads with a plain message that loads the brief, and treats the `/goal` line as an optional second step. `references/next-session-contract.md` Section 4 has the verified details.

The skill redacts sensitive credential patterns and refuses to quote contents of `.env`/secret files by default; see `references/handoff-generation.md` Section 10 for the full sensitive-data handling rules.

---

## Storage Rules

**There is exactly one correct location for handoff artifacts: `.handoffs/` at the project root.**

This is not negotiable and does not vary by host. Claude Code and Codex both read and write the same path, which is the whole point of it being outside `.claude/`.

Files are organized into day folders so the directory stays readable as history accumulates:

```
.handoffs/
├── LATEST.md                              # pointer - newest handoff
├── LATEST-PROMPT.md                       # pointer - newest continuation prompt
├── LATEST-GOAL.md                         # pointer - newest goal file
├── 2026-08-16/
│   ├── 2026-08-16-14-30-handoff.md
│   ├── 2026-08-16-14-30-prompt.md
│   └── 2026-08-16-14-30-goal.md
└── 2026-08-14/
    └── 2026-08-14-09-05-handoff.md
```

Rules:

- The three `LATEST*.md` pointer files always sit at the top level of `.handoffs/`. Their paths never change, so anything that references them keeps working.
- Every timestamped file goes in a `YYYY-MM-DD/` day folder named for the day it was created.
- Timestamped files keep the full date in their filename even inside a day folder. That way a file stays self-describing if it is copied, shared, or opened on its own.
- Never write a timestamped handoff directly into the top level of `.handoffs/`.

**These locations are wrong. Never write to them:**

| Wrong location | Why it happens |
|---|---|
| `.claude/handoffs/` | The pre-1.2.0 path. Older installs of this skill still say this. |
| `.claude/.handoffs/` | A slip - the leading dot gets carried over from the canonical name. |
| `handoffs/` | Dropping the leading dot. |
| `docs/handoffs/` | Filing it as documentation. |
| `.codex/handoffs/`, `.Codex/handoffs/` | Mirroring the Claude Code layout for Codex. |

If you find handoffs in any of those places, do not read from them directly and do not start writing there to match. Run the Storage Preflight below, which copies them into `.handoffs/` for you.

If a project's `CLAUDE.md`, `AGENTS.md`, or user instruction explicitly demands a different path, follow the user's instruction and say out loud which path you used and that it differs from the skill default.

---

## Storage Preflight

Run this preflight once at the start of every invocation, before Generate Mode, Resume Mode, or `--list` handling:

1. Locate `scripts/migrate-handoffs.sh` relative to this skill's directory.
2. Run it from the current project root.
3. If the script prints anything, reproduce that output to the user before continuing.

The script does two jobs and is safe to run repeatedly:

- **Sweeps stray folders.** It copies handoff history out of every wrong location listed above into `.handoffs/`. It only touches a folder that actually contains handoff artifacts, and it never deletes the original. Old folders are left in place as archives, and the notice tells the user when it is safe to delete them.
- **Folds loose files into day folders.** Any timestamped file sitting directly in `.handoffs/` is moved into its `YYYY-MM-DD/` folder. Pointer files are left alone.

When it has nothing to do, it prints nothing.

If the script is unavailable, perform the same work manually:

```bash
mkdir -p .handoffs

# 1. Sweep stray folders (copy only, never delete).
for legacy in .claude/handoffs .claude/.handoffs .codex/handoffs .Codex/handoffs docs/handoffs handoffs; do
  [ -d "$legacy" ] || continue
  ls "$legacy"/*-handoff.md >/dev/null 2>&1 || [ -f "$legacy/LATEST.md" ] || continue
  cp -Rn "$legacy"/. .handoffs/ 2>/dev/null || true
done

# 2. Fold loose dated files into day folders.
for f in .handoffs/*-handoff.md .handoffs/*-prompt.md .handoffs/*-goal.md; do
  [ -f "$f" ] || continue
  day=$(basename "$f" | cut -c1-10)
  mkdir -p ".handoffs/$day"
  mv -n "$f" ".handoffs/$day/"
done
```

Then tell the user which folders were swept, that they were left in place as archives, and that they can be deleted once `.handoffs/` looks complete.

---

## Reconcile Mode

The Storage Preflight above runs silently and only handles tidy cases. `--reconcile` is the loud version, run on purpose, for when history is genuinely scattered. Reach for it when:

- A project has handoffs in more than one folder.
- The project has been through several versions of this skill.
- Something looks missing, duplicated, or renamed.
- The user says any of: "fix my handoffs", "merge my handoffs", "my handoffs are everywhere", "clean up the handoff folder".

### What it finds that the silent preflight does not

| Problem | Why it matters |
|---|---|
| History spread across several folders | Each folder has a partial `LATEST.md`, so resume reads whichever one it happens to find |
| The same filename in two folders with different content | A plain copy would silently drop one of them |
| A `LATEST.md` matching no dated file | That handoff exists in exactly one copy, and the next run overwrites it. This is real data loss and it has happened. |
| Off-convention filenames | `--list` and the freshness check skip them, so they are invisible |
| A prompt or goal file whose handoff is gone | Half a handoff, which is worth knowing about |
| Handoffs in a folder nobody planned for | Not covered by the automatic sweep at all |

### Procedure

1. Locate `scripts/reconcile-handoffs.sh` relative to this skill's directory.
2. Run it with no arguments from the project root. **This changes nothing.** It prints where handoffs live now, what is wrong, and what it would do.
3. Show the user that report as-is. Do not summarize it away - the problem list is the point.
4. Ask whether to go ahead. If the report shows nothing to do, say so and stop; do not ask a pointless question.
5. On approval, run it again with `--apply`.
6. Report what moved, and remind the user that no source folder was deleted so they can delete the old ones themselves once satisfied.

Never run `--apply` without showing the report first. The report is what makes the change reviewable.

The script never deletes anything. Files already inside `.handoffs/` are moved into their day folder; everything from anywhere else is copied, leaving the original in place. A name collision is kept side by side rather than overwritten. Running it twice is safe - the second run finds nothing to do.

---

## Mode Detection

Determine the operating mode from the user's invocation. The modes are mutually exclusive - a single invocation is always exactly one of them.

1. **If the arguments contain `--reconcile`** --> **Reconcile Mode**
   - Follow the Reconcile Mode section below. Do not load any other reference.
   - This is the repair mode. It is the one to reach for when handoffs are scattered, when a project has been through several versions of this skill, or when something looks lost.

2. **If the arguments contain `--list`** --> **List Mode**
   - Run the Storage Preflight, then follow `references/handoff-generation.md` Section 11.
   - Do not load any other reference.

3. **If the arguments contain `--resume`** --> **Resume Mode**
   - Load and follow `references/resume-verification.md`.
   - Also load `references/next-session-contract.md` - the resuming session has to state the working agreement out loud and then follow it.
   - Do NOT load generation or sentiment references.
   - The skill runs the Storage Preflight, locates the latest handoff at `.handoffs/LATEST.md`, reads it, and systematically verifies each section against the current project state (git log, file system, test results). Any drift between the handoff and reality is flagged before work begins.

4. **Otherwise** --> **Generate Mode**
   - Load and follow `references/handoff-generation.md`.
   - Load `references/next-session-contract.md` for the `## Start Here` block, the `## TL;DR` block, the goal file template, and the kickoff block.
   - Load `references/sentiment-analysis.md` (used for friction/blocker detection by scanning the conversation history for signs of struggle, repeated attempts, or abandoned approaches).
   - Load `references/prompt-engineering.md` whenever the verbosity mode is not the default - that is, for both `--compact` and `--long`.
   - The skill scans the full conversation, git history since session start, and any project specs to produce the handoff document.

If no flags are provided at all, default to Generate Mode at `full` verbosity with reason `context-limit`.

---

## Flag Parsing

| Flag | Default | Description |
|------|---------|-------------|
| *(no flags)* | -- | Generate Mode at `full` verbosity. Assumes `--reason context-limit`. Writes the goal file. |
| `--resume` | Off | Resume Mode. Loads the latest handoff and runs verification. |
| `--long` | Off | Maximum-detail handoff. Nothing is summarized away. See the Verbosity Modes section. |
| `--compact` | Off | Token-conscious formatting. Shorter sections, denser structure, no prose padding. |
| `--mode <level>` | `full` | Sets verbosity explicitly. Valid values: `compact`, `full`, `long`. Equivalent to the flags above. |
| `--reason <reason>` | `context-limit` | Stop reason that shapes the "What's Next" section. Valid values: `context-limit`, `done-for-day`, `switching-focus`, `blocked`, `phase-complete`. |
| `--interactive` | Off | Pause to ask 2-3 clarifying questions before generating the handoff. |
| `--note "text"` | None | Inject custom context into the handoff. Repeatable: `--note "X" --note "Y"`. Each note appears in the "User Notes" section. |
| `--note-raw "text"` | None | Like `--note` but skips the Rule 2 redaction filter. Repeatable. Tracked via `raw_notes_count` frontmatter field. |
| `--no-goal` | Off | Skip the goal file and the `/goal` line in the kickoff block. |
| `--no-prompt` | Off | Skip generating the continuation prompt file. |
| `--no-memory` | Off | Skip updating the project memory file (`handoff_state.md`). |
| `--no-priority` | Off | Skip the "What's Next" section entirely. |
| `--no-carryforward` | Off | Skip automatic carry-forward of unresolved priorities from the previous handoff's "What's Next". |
| `--list` | Off | List past handoffs and exit. Mutually exclusive with all other flags. See `references/handoff-generation.md` Section 11. |
| `--reconcile` | Off | Find handoffs everywhere they ended up, report what is wrong, and merge them into `.handoffs/`. Reports first, changes nothing until you say go. Mutually exclusive with all other flags. |

### Bare word aliases

A bare word is accepted in place of the mode flag, because typing `/handoff long` is faster than `/handoff --mode long`:

| Typed | Means |
|---|---|
| `/handoff long` | `/handoff --mode long` |
| `/handoff compact` | `/handoff --mode compact` |
| `/handoff full` | `/handoff --mode full` |
| `/handoff resume` | `/handoff --resume` |
| `/handoff list` | `/handoff --list` |
| `/handoff reconcile` | `/handoff --reconcile` |

Any other bare word is treated as free-form context and folded into User Notes as if it had been passed with `--note`.

---

## Verbosity Modes

Three levels. They change the handoff document only. The goal file is a fixed size in every mode, and the `## Start Here` and `## TL;DR` blocks are required in every mode.

| Mode | When to use | What changes |
|---|---|---|
| `compact` | The next session has a small context budget, or the session was short and simple. | Same sections, abbreviated headers, terse bullets, `file:line` shorthand, no reasoning prose. |
| `full` *(default)* | Normal end-of-session handoff. | Complete sentences, narrative friction points, full reasoning for each decision. |
| `long` | Complex sessions, long gaps before resuming, or handing to someone who was not here. Also the right pick when the user says "make it long" or "don't leave anything out". | Everything in `full`, plus four extra sections: `## File-By-File Notes`, `## Commands That Matter`, `## Open Questions`, and `## Glossary`. Nothing is summarized away and no detail is dropped for length. |

If both `--compact` and `--long` are passed, warn and stop:

> "You passed both `--compact` and `--long`. Pick one: `--compact` for the short version, `--long` for the full-detail version. Re-run with just one of them."

---

## Flag Validation Rules

**Invalid combinations -- warn the user and do not proceed:**

- `--resume` combined with any of `--compact`, `--long`, `--mode`, `--reason`, `--note`, `--no-goal`: Resume Mode reads an existing handoff; it does not generate one. These flags are generation-only. Emit a warning:
  > "The `--resume` flag enters Resume Mode, which loads and verifies an existing handoff. Generation flags like `--compact`, `--long`, `--reason`, `--note`, and `--no-goal` do not apply and will be ignored. Did you mean to run without `--resume`?"

- `--list` combined with any other flag: `--list` is a read-only browse mode and does not combine with generation or resume flags. Emit a warning:
  > "The `--list` flag only lists past handoffs and does not combine with generation or resume flags. Re-run with `--list` alone."

- `--compact` combined with `--long`: see the Verbosity Modes section above.

- `--reconcile` combined with any other flag: reconcile is a repair mode that neither generates nor resumes. Emit a warning:
  > "The `--reconcile` flag repairs where handoffs are stored and does not combine with generation or resume flags. Re-run with `--reconcile` alone."


**Legal but confirm intent:**

- `--no-prompt` combined with `--no-memory` combined with `--no-goal`: this produces a handoff document and nothing else - no continuation prompt, no goal file, no memory update. The handoff file is still written. Confirm:
  > "You've turned off the continuation prompt, the goal file, and the memory update. You'll get the handoff document only, and the next chat will have to find it on its own. Continue?"

All other combinations are valid.

---

## `--reason` Behavioral Impact

The `--reason` value is written to the `stop_reason` frontmatter field and shapes the tone and content of the "What's Next" section.

| Reason | Effect on "What's Next" |
|--------|------------------------|
| `context-limit` | Default. Lists priorities in execution order. Neutral, task-focused tone. Assumes the next session picks up immediately. |
| `done-for-day` | Adds a brief session recap tone. No urgency language. Priorities framed as "when you return" rather than "immediately". |
| `switching-focus` | Emphasizes where to resume *this specific workstream*. Notes the switching point clearly so the user can context-switch back without re-reading everything. |
| `blocked` | Leads with the blocker: what it is, what's needed to unblock, who or what can provide it, and what parallel work can proceed in the meantime. |
| `phase-complete` | Pulls the next phase from any roadmap, PRD (product requirements document), or architecture spec found in the project. Includes a brief note on what was completed. Frames next steps as the new phase's objectives. |

Any other value is written to frontmatter as-is with no special tone adjustment.

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
- Answers to question 2 directly shape the priority ordering in "What's Next" and the ordered list in the goal file.
- Answers to question 3 feed into "Friction Log", the goal file's "Do not do" list, and cautionary notes.
- Answers to question 4 feed into "User Notes" verbatim and may also appear in "Session Context".

---

## Host Compatibility

This skill is usable from Claude Code and Codex. Project handoff artifacts always live in `.handoffs/` for cross-agent continuity, as described in Storage Rules.

Invocation syntax is host-specific: Claude Code uses `/handoff`; Codex uses `$handoff`. Flags and bare-word aliases work the same way after either name. Canonical generated templates name both forms explicitly so the next session cannot inherit a command for the wrong host. In conversational instructions where the current host is known, use that host's form and keep the arguments unchanged.

Project memory is host-specific:

- Claude Code: update `~/.claude/projects/{project-path}/memory/`
- Codex: use the host's own memory tool if it exposes one. Codex stores memory in a database under `~/.codex/`, not in a markdown tree, so there is no path to write to. If no memory tool is available, skip the update.
- Other hosts: skip global memory updates unless the user explicitly provides a target

`/goal` is a Claude Code feature and needs a trusted workspace. Handoff always writes the goal file regardless of host, because it is a plain markdown file any agent can read, and because the part that loads the context is a plain message rather than a slash command. Only the optional second line of the kickoff block depends on `/goal`. See `references/next-session-contract.md` Sections 4 and 6.

---

## Generated Files

Each Generate Mode invocation produces up to five files.

| File | Purpose |
|------|---------|
| `.handoffs/YYYY-MM-DD/YYYY-MM-DD-HH-MM-handoff.md` | Timestamped handoff document. Permanent record. Never overwritten. |
| `.handoffs/YYYY-MM-DD/YYYY-MM-DD-HH-MM-prompt.md` | Timestamped continuation prompt. Permanent record. Skipped with `--no-prompt`. |
| `.handoffs/YYYY-MM-DD/YYYY-MM-DD-HH-MM-goal.md` | Timestamped goal file. Permanent record. Skipped with `--no-goal`. |
| `.handoffs/LATEST.md` | Copy of the most recent handoff. Overwritten each run. This is the file Resume Mode reads. |
| `.handoffs/LATEST-PROMPT.md` | Copy of the most recent continuation prompt. Overwritten each run. Skipped with `--no-prompt`. |
| `.handoffs/LATEST-GOAL.md` | Copy of the most recent goal file. Overwritten each run. Skipped with `--no-goal`. This is the file the kickoff block points at. |

Use the system clock for timestamps. Format: `YYYY-MM-DD-HH-MM` in local time (24-hour clock). The day folder name is the first 10 characters of that timestamp.

### File creation order

The authoritative procedure is `references/handoff-generation.md` Section 4. The summary here exists so the shape is visible without opening that file; where they differ, Section 4 wins.

**Read the clock exactly once and reuse the result.** Every file from one run must carry the same `YYYY-MM-DD-HH-MM` stamp as the `created` field in the frontmatter. Calling `date` again per file lets a run that straddles a minute boundary produce mismatched names, which breaks the freshness check's ability to recognize its own output.

```bash
TS=$(date +%Y-%m-%d-%H-%M)
DAY=$(date +%Y-%m-%d)
```

1. Generate content for the handoff document.
2. Create the day folder: `mkdir -p ".handoffs/$DAY"`.
3. Write the handoff to `.handoffs/$DAY/$TS-handoff.md`.
4. Copy it to `.handoffs/LATEST.md`.
5. If `--no-prompt` is not set: write `.handoffs/$DAY/$TS-prompt.md` and copy it to `.handoffs/LATEST-PROMPT.md`.
6. If `--no-goal` is not set: write `.handoffs/$DAY/$TS-goal.md` and copy it to `.handoffs/LATEST-GOAL.md`.
7. If `--no-memory` is not set: update memory (see Memory Integration below).
8. Report the file paths to the user, then print the kickoff block last.

---

## Memory Integration

Unless `--no-memory` is set, update persistent project memory after generating the handoff.

**Host memory is not portable. Do not invent a path.**

- **Claude Code:** write to `~/.claude/projects/{project-path}/memory/`. This is a real directory tree of markdown files.
- **Codex:** there is no equivalent markdown tree. Codex keeps memory in a database under `~/.codex/`, not in `~/.Codex/projects/.../memory/`. If the host exposes a memory tool, use that tool. If it does not, skip the global memory update and say so in one line.
- **Any other host:** skip the global memory update unless the user names a target.

Skipping is safe. The durable record is `.handoffs/`, which every host reads the same way.

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
     - [handoff_state.md](handoff_state.md) - Latest session handoff state - phase, progress, next priorities
     ```

The `{project-path}` is derived from the current working directory, matching the convention used by the host's project memory system (typically the absolute path with slashes replaced by dashes, e.g., `-home-jmarlique-Projects-MyApp`).

---

## Not in Scope

This skill intentionally does not handle:

- **Cross-project handoffs** -- each handoff is scoped to the current project.
- **Auto-triggering** -- the user must invoke the skill manually.
- **Deleting old handoffs** -- history accumulates. Day folders keep it readable; pruning is a manual decision.
- **Multi-user or team workflows** -- handoffs are single-user, single-session continuity documents.
- **External integrations** -- no Slack, Linear, GitHub Issues, or other platform integrations.

---

## References to Load

Load the appropriate reference files based on the detected mode. These files contain the detailed procedures, templates, and checklists that this SKILL.md intentionally does not duplicate. All reference paths are relative to this skill's directory (the directory containing this SKILL.md file).

### Generate Mode

Load these files at the start of generation, before scanning the conversation or project state:

- `references/handoff-generation.md` -- Full generation procedure, section-by-section template, required and optional fields, and the complete output format specification. This is the primary procedural document for Generate Mode.
- `references/next-session-contract.md` -- The `## Start Here` block, the `## TL;DR` block, how `/goal` actually works, the goal file template and size budget, and the kickoff block format. Required in every mode.
- `references/sentiment-analysis.md` -- Friction detection rules and heuristics for scanning conversation history. Defines what constitutes a struggle signal (repeated errors, backtracking, abandoned approaches, explicit frustration) and how to surface those in the Friction Log section.
- `references/prompt-engineering.md` -- Formatting rules per verbosity level. Load whenever the mode is `compact` or `long`. Covers the compression techniques used by `compact` and the extra sections and depth required by `long`.

### Resume Mode

Load these files before reading the handoff:

- `references/resume-verification.md` -- Verification checklist, state-comparison procedure against git and file system, drift detection rules, and recovery steps for when reality diverges from the handoff.
- `references/next-session-contract.md` -- Sections 4 and 7. Section 4 explains how `/goal` really works, so the resume report can offer the finish line correctly. Section 7 is the working agreement the resuming session states out loud and then follows.

### List Mode

No references beyond `references/handoff-generation.md` Section 11.

---

## Examples to Consult

Before generating output, review the appropriate example for formatting and tone:

- `examples/handoff-full.md` -- Full-format handoff (default).
- `examples/handoff-compact.md` -- Compact-format handoff (`--compact`).
- `examples/handoff-long.md` -- Long-format handoff (`--long`), including the four long-only sections.
- `examples/goal.md` -- Goal file, showing the size budget in practice.

These are reference examples, not rigid templates. Adapt structure and length to the actual session content. A short session with one task completed may produce a handoff half the length of the example. A complex multi-feature session may exceed it. The examples establish tone, section ordering, and the level of detail expected -- not a fixed word count. The one exception is the goal file, which is genuinely size-capped; see `references/next-session-contract.md` Section 5.2.
