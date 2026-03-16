# claude-handoff

Session handoff skill for zero-loss continuity across Claude Code conversations.

Generate structured context-transfer documents at the end of a session, then verify and resume from them at the start of the next. No more cold starts.

## What It Does

When you hit a context limit or wrap up for the day, `/handoff` captures everything the next session needs:

- **What was built** — commits, files changed, features implemented
- **Decisions made** — architecture choices with reasoning
- **Friction points** — failed approaches and what actually worked (so you don't repeat mistakes)
- **What's next** — priority-ordered tasks derived from your specs and roadmap
- **Current state** — test results, build status, uncommitted work

When you start a new session, `/handoff --resume` loads the latest handoff, runs freshness checks against git state, and tells you exactly where to pick up.

## Installation

```bash
# Add the marketplace
/plugin marketplace add josuemarlique/claude-handoff

# Install the plugin
/plugin install handoff@jmarlique-tools
```

## Quick Start

### End of session — generate a handoff

```
/handoff
```

This generates a timestamped handoff document and a continuation prompt in `.claude/handoffs/`.

### Start of next session — resume

```
/handoff --resume
```

Or just say: "continue from last handoff" / "pick up where we left off"

This reads the latest handoff, compares it against current git state (commit drift, branch changes, dependency updates, spec modifications), and presents a verified status report before you start working.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| *(no flags)* | — | Full generate mode, assumes context-limit as stop reason |
| `--resume` | Off | Resume mode — load and verify latest handoff |
| `--compact` | Off | Token-conscious formatting (same content, terse prose) |
| `--reason <reason>` | `context-limit` | Stop reason: `context-limit`, `done-for-day`, `switching-focus`, `blocked`, `phase-complete` |
| `--interactive` | Off | Ask 2-3 clarifying questions before generating |
| `--note "text"` | None | Inject custom context (repeatable) |
| `--no-prompt` | Off | Skip generating the continuation prompt file |
| `--no-memory` | Off | Skip updating project memory |
| `--no-priority` | Off | Skip the "What's Next" section |

### Common combinations

```bash
# Quick handoff at end of a completed phase
/handoff --compact --reason phase-complete

# Detailed handoff with extra context
/handoff --interactive --note "the API schema changed mid-session"

# Resume and verify at session start
/handoff --resume
```

## How It Works

### Generate Mode (default)

1. **Gathers context automatically** — git log, git diff/status, test results, build status, conversation history, existing specs/plans
2. **Detects friction** — scans conversation for frustration signals, repeated attempts, abandoned approaches, error loops
3. **Produces the handoff document** — structured markdown with YAML frontmatter (machine-parseable for verification)
4. **Generates a continuation prompt** — ready to paste into a new session
5. **Updates project memory** — so the next session has ambient awareness even without running `--resume`

### Resume Mode (`--resume`)

1. **Reads latest handoff** from `.claude/handoffs/LATEST.md`
2. **Runs freshness checks** via a POSIX shell script that compares the handoff's frontmatter against current git state:
   - Commit drift (new commits since handoff)
   - Branch drift (different branch than handoff)
   - Uncommitted changes
   - Spec/plan file modifications
   - Dependency changes (package.json, lockfiles)
3. **Presents a status report** with drift warnings
4. **Ready prompt** — names the first priority item from "What's Next"

### Compact vs Full

**Full mode** (default): Complete sentences, narrative friction points, full reasoning paragraphs. No token restrictions.

**Compact mode** (`--compact`): Same sections, same information. Terse bullets, abbreviated headers, `file:line` shorthand. Token-conscious for smaller context windows.

## Output Structure

```
.claude/handoffs/
├── LATEST.md                    # Always points to most recent handoff
├── LATEST-PROMPT.md             # Always points to most recent prompt
├── 2026-03-14-02-30-handoff.md  # Timestamped handoff (permanent)
├── 2026-03-14-02-30-prompt.md   # Timestamped prompt (permanent)
└── ...                          # History accumulates
```

## Handoff Document Format

Each handoff contains a YAML frontmatter block (for machine parsing) and these sections:

1. **Refined Intent** — What the session set out to accomplish
2. **What Was Built** — Concrete deliverables grouped by concern
3. **Decisions Made** — Architecture choices with reasoning
4. **Friction Points** — Problems, failed approaches, and solutions
5. **Current State** — Branch, commit, tests, build status
6. **What's Next** — Priority-ordered list for next session
7. **Environment Notes** — Dependencies, configs, tools introduced
8. **User Notes** — Custom context from `--note` or `--interactive`

See [examples/](skills/handoff/examples/) for full and compact format samples.

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Git (for freshness checks and context gathering)

## License

MIT — see [LICENSE](LICENSE)
