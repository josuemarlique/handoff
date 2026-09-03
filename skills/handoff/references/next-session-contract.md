# Next Session Contract Reference

This file holds the exact text blocks that tell the **next** session how to behave. They are reused in several places, so they live here once:

1. The `## Start Here` block at the very top of every handoff document body.
2. The `## TL;DR` block right under it.
3. The goal file (`*-goal.md` / `LATEST-GOAL.md`) - the short brief for the next session.
4. The kickoff block printed at the end of the run, which is what the user actually copies.

Load this file in Generate Mode. Also load it in Resume Mode, because the resuming session must re-state the working agreement out loud before it starts working.

---

## 1. Why this exists

A fresh session starts with no memory and defaults to writing like a senior engineer talking to another senior engineer. That is the wrong register for this user. It also defaults to doing everything inside one context window, which fills up fast and forces another handoff sooner than necessary.

The contract fixes both. It is short, it is always at the top, and it is repeated in the goal file so it survives even when the handoff document itself is not read.

---

## 2. The `## Start Here` block

Emit this block verbatim as the **first** section of the handoff body, immediately after the YAML frontmatter and before `## TL;DR`. Do not paraphrase it, shorten it, or move it. It is identical in every mode, including `--compact`.

```markdown
## Start Here

**Read this before anything else. These rules apply for the whole session, not just the first reply.**

**How to write back to me**

- Use plain, everyday language. Write like you are explaining it to a smart middle school student.
- Spell things out. The first time you use a short form, write the full name and put the short form in parentheses, like "continuous integration (CI)". After that the short form is fine.
- Start every reply with a short `TL;DR` (too long, didn't read) of 2 to 5 bullets, then the details, then repeat a one-line `TL;DR` at the end.
- Say what is done, what is not done, and what you need from me. No hedging.
- Never use the em dash character. Use a plain dash instead.

**How to do the work**

- Use an agent team for work that splits into independent pieces, and run those pieces at the same time. Saying "fan out subagents" is a reliable way to start one in Claude Code.
- Give each teammate one clear job and ask it for a short result, not a file dump.
- Teammates are individually addressable, so they can message each other directly instead of routing everything back through me.
- Keep the main chat for decisions and review. Its context stays small on purpose, which is what makes this session last longer before it needs another handoff.
- If a piece of work is small, or has to happen in a fixed order, just do it yourself. A team is for parallel work, not for everything.

**Before you start working**

1. Run the Handoff skill in resume mode: `/handoff --resume` in Claude Code, or `$handoff --resume` in Codex.
2. Tell me what drifted, if anything.
3. Confirm the first priority with me before you begin.
```

### Rules

- The block is required. `--no-priority`, `--compact`, and `--no-goal` do not remove it.
- If the user has passed `--note` text that changes the working agreement (for example "stop using subagents on this repo"), append a short `**This session only:**` line to the end of the block rather than editing the standard text.

---

## 3. The `## TL;DR` block

Emit this immediately after `## Start Here`. It is the 15-second version of the whole handoff.

```markdown
## TL;DR

- **Where we are:** [one line - phase or milestone, plus branch and commit]
- **What got done:** [one line - the headline deliverable, not a list]
- **What is next:** [one line - the single first thing to do]
- **Watch out for:** [one line - the top friction point or blocker]
- **State:** [tests, build, uncommitted work - one line]
```

Keep it to five bullets. If a bullet has nothing to report, write "nothing" rather than dropping the bullet, so the shape stays predictable.

---

## 4. How `/goal` actually works

Get this right, because the obvious guess is wrong and produces a session that either loops forever or stops early.

`/goal` is **not** a place to paste context. It sets a **finish line**. Verified behavior in Claude Code:

| Fact | Detail |
|---|---|
| What it does | `/goal <condition>` arms a session-scoped stop check. After each turn, a separate evaluator decides whether the condition is met. Claude keeps working until it is. |
| Size limit | 4,000 characters. Over that, Claude Code refuses with "Goal condition is limited to 4000 characters (got N)". |
| What the evaluator can see | **The conversation only.** It cannot run commands and it cannot read files. |
| How many | One at a time. Setting a new goal replaces the current one. |
| Check status | `/goal` with no arguments. Shows the active condition and the reason from the last check. |
| Stop it | `/goal clear`. |
| Requirements | A trusted workspace. It also refuses to run when hooks are turned off by settings or policy. |
| Where it works | Interactive sessions, print mode (`-p`), and Remote Control. Added in Claude Code v2.1.139. |

Two consequences that shape everything below:

1. **A goal must be a measurable end state, not an instruction.** "Follow the brief in `.handoffs/LATEST-GOAL.md`" is a bad goal - the evaluator cannot open that file, so it can never confirm it. "The Video module renders in edit and view mode and `pnpm test` exits 0, with that result shown in this conversation" is a good goal.
2. **The finish state has to be visible in the chat.** If the proof of done is a command's output, say so in the condition, so the session knows it has to run the command and show the result rather than just claiming success.

`/goal` is a Claude Code feature. Other hosts, including Codex, may not have it. The goal file is written either way, because it is a plain markdown file any agent can read.

---

## 5. The goal file

### 5.1 What it is for

The goal file is the **short brief**: mission, first three priorities, what not to do, and where things stand. It is what the next session reads to get going, and it is small enough to paste whole into a chat box if reading a file is inconvenient.

It also carries the ready-made `/goal` condition in its `## Finish line` section, so the user can copy that one line without composing it themselves.

It is written on every handoff unless `--no-goal` is passed.

### 5.2 Hard size budget

**The goal file body must stay at or under 3,000 characters.** It is a brief, not a second copy of the handoff. The handoff document is where detail belongs.

Count the characters before writing. If the draft is over budget, cut in this order:

1. Drop the "Do not do" list to the single most important item.
2. Reduce priorities from three to two.
3. Shorten the "Where we are" line to a single clause.

Never cut the writing-style rules, the agent team line, or the `## Finish line` section - those are the reason the file exists.

The file does **not** get longer in `--long` mode and does **not** get shorter in `--compact` mode. It is a fixed-size artifact in every mode. The mode flags change the handoff document, not the goal file.

### 5.3 Template

```markdown
# Session Goal - [project name]

**Full context:** read `.handoffs/LATEST.md` before you start working.
**Verify first:** run the Handoff skill in resume mode (`/handoff --resume` in Claude Code or `$handoff --resume` in Codex) to check this against the current project state.

## How to write back to me

Plain, everyday language, like you are explaining it to a smart middle school student. Spell out every short form the first time you use it, with the short form in parentheses. Start every reply with a short TL;DR (too long, didn't read) of 2 to 5 bullets and end with a one-line TL;DR. No em dash characters.

## How to work

Use an agent team for independent pieces of work and run them at the same time - saying "fan out subagents" starts one in Claude Code. Teammates are individually addressable, so let them message each other directly. Keep the main chat for decisions and review so its context stays small. Do small or strictly ordered work yourself.

## The mission

[One or two sentences. What this stretch of work is actually for, in the user's terms.]

## Do these, in this order

1. [First priority - specific enough to start on]
2. [Second priority]
3. [Third priority]

[One line naming which of these are independent and can go to separate teammates, or "these are sequential".]

## Do not do

- [Top thing to avoid, taken from Friction Points - include the reason]
- [Second thing to avoid, only if it fits the budget]

## Where we are

Branch `[branch]` at `[commit]`. [Tests and build in one clause.] [Blocker, if any.]

## Finish line

Paste this into Claude Code to make the session keep working until the job is actually done:

    /goal [one measurable end state with its check, written so someone reading only the chat can confirm it]

Clear it any time with `/goal clear`. Check it with `/goal`.
```

### 5.4 Writing the `## Finish line` condition

Build it from the first item in `## What's Next` plus whatever proves that item is done.

Rules:

- **State an end state, not a task.** "Video module implemented" is weak. "The Video module renders a YouTube embed in edit mode and view mode, and `pnpm test` exits 0" is checkable.
- **Name the proof and say it must appear in the conversation.** The evaluator reads the chat, nothing else. End the condition with something like "with the test output shown in this conversation".
- **Keep it to one goal.** If the first three priorities are separate deliverables, write the condition for priority 1 only. A goal that covers three things will not finish.
- **Stay well under 4,000 characters.** Aim for one or two sentences. Long conditions are harder for the evaluator to judge, not easier.
- **Do not reference files as the condition.** Referencing a file for *context* inside a longer condition is fine, but the thing being checked must be visible in the chat.

Good:

    /goal The Video module renders a YouTube embed in both edit mode and view mode, and `pnpm test` exits 0 with the summary line shown in this conversation.

Bad, and why:

| Bad condition | Problem |
|---|---|
| `/goal Follow .handoffs/LATEST-GOAL.md` | The evaluator cannot read files, so it can never confirm this. |
| `/goal Finish Phase 2D` | Six deliverables in one goal. It will not finish. |
| `/goal Make the code better` | Nothing measurable to check. |

### 5.5 Redaction

The goal file is generated content, so it passes through the same Rule 2 redaction filter defined in `handoff-generation.md` Section 10. Redactions inside the goal file count toward the same `redactions_applied` total recorded in the handoff frontmatter. Never put a credential in a `/goal` condition - it would be echoed back by every status check.

---

## 6. The kickoff block

After all files are written, the last thing shown to the user is the copy-paste block for the next chat. This is the payoff of the whole skill, so make it impossible to miss.

### 6.1 Format

````markdown
## Paste this into your next chat

**1. Start here** - this loads the context:

```
Read .handoffs/LATEST-GOAL.md and then .handoffs/LATEST.md, then run the Handoff skill in resume mode (`/handoff --resume` in Claude Code or `$handoff --resume` in Codex) and tell me what drifted. Follow the writing and working rules in those files for the whole session.
```

**2. Optional - set the finish line** so the session keeps working until the job is done:

```
/goal [the condition from the goal file's Finish line section]
```

Check it any time with `/goal`. Turn it off with `/goal clear`.
````

### 6.2 Rules

- **Line 1 is a plain message, not a slash command.** It is what actually loads the brief, so it comes first and is never skipped.
- Line 1 must be a single line with no newlines inside it. Most hosts submit on enter, so a multi-line kickoff would be sent as several separate messages.
- Point at `LATEST-GOAL.md` and `LATEST.md`, never at the timestamped files. The `LATEST*` paths stay correct as new handoffs are written.
- **Line 2 is optional and is presented that way.** A goal that does not fit the session is worse than no goal, because it makes Claude refuse to stop.
- Copy the `/goal` condition from the goal file's `## Finish line` section verbatim. Do not rewrite it here - one source, no drift.
- If `--no-goal` was passed, drop both the goal file reference and line 2. Line 1 becomes: "Read `.handoffs/LATEST.md`, then run the Handoff skill in resume mode (`/handoff --resume` in Claude Code or `$handoff --resume` in Codex) and tell me what drifted." Add a one-line note that no goal file was written this run.
- Add this note under the block whenever line 2 is present:

  > `/goal` is a Claude Code feature and needs a trusted workspace. If it is not available, skip step 2 - step 1 is the part that matters.

- Nothing goes after this block. It is the last thing on screen.

---

## 7. Resume Mode use

When resuming, the session must not silently absorb the contract - it has to show the user that it took it on board. After the status report and before the ready prompt, print:

```markdown
### Working agreement for this session

- Plain language, short forms spelled out, TL;DR at the top and bottom of every reply.
- Independent work goes to a team of subagents running in parallel; the main chat stays small and handles decisions and review.
```

Then behave that way for the rest of the session, including the resume report itself.

If the handoff being resumed has a `## Finish line` section in its goal file and no goal is currently active, offer it once:

> There's a ready-made finish line in `.handoffs/LATEST-GOAL.md`. Want to set it with `/goal` so I keep working until it's met?

Ask once. Do not repeat the offer later in the session.
