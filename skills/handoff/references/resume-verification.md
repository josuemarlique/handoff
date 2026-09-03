# Resume Verification Reference

This is the procedure the host agent follows when invoked in resume mode (`--resume`). It loads the previous session's handoff, checks for drift since the handoff was created, and presents a structured status report before continuing work.

Resume Mode is also where the working agreement gets adopted. Load `references/next-session-contract.md` Section 7 alongside this file, and follow the plain-language and TL;DR rules **in the resume report itself** - not starting from the next message.

---

## 1. Locate Handoff

Run the Storage Preflight from SKILL.md, then read `.handoffs/LATEST.md` in the **current working directory**. This path is always relative to cwd - handoffs do not cross project boundaries, and project memory does not override this scope.

`LATEST.md` always lives at the top level of `.handoffs/`, never inside a day folder. If it is missing but day folders exist, the previous session was interrupted before the pointer was written. In that case:

```bash
find .handoffs -type f -name '*-handoff.md' | sort | tail -1
```

Read the newest file that turns up, and tell the user that `LATEST.md` was missing so you fell back to the newest timestamped handoff.

If nothing is found at all, display the following and stop:

> No previous handoff found. Use the Handoff skill (`/handoff` in Claude Code or `$handoff` in Codex) at the end of a session to create one.

Do not attempt to search parent directories or other projects. Scoping is strict.

---

## 2. Run Freshness Script

Execute the freshness check script against the located handoff file. The script is located in the `scripts/` subdirectory relative to where this skill is installed. Locate it by finding `freshness-check.sh` in the `scripts/` sibling directory of the `references/` directory containing this file.

```bash
# The script path is relative to the skill's installation directory.
# When installed as a standalone skill: ~/.claude/skills/handoff/scripts/freshness-check.sh
# When installed as a plugin: the plugin's cache directory under skills/handoff/scripts/
# Resolve the path dynamically from the skill directory, then run:
<skill-dir>/scripts/freshness-check.sh .handoffs/LATEST.md
```

The script outputs a JSON object with one key per check. Each check contains at minimum a `stale` boolean. Some checks include additional fields (file lists, commit summaries, counts) when stale.

The script deliberately ignores the skill's own footprint, so the report is about your project rather than about the handoff:

- The handoff, prompt, and goal files written at the same timestamp, plus the three `LATEST*.md` pointers, are not counted as spec drift.
- The whole `.handoffs/` folder is not counted as uncommitted work. It is usually untracked, and flagging it on every resume would drown out real changes.
- The old archive folders (`.claude/handoffs/` and friends) are ignored entirely. They are archives by definition.

A handoff written by a *different* session still shows up as drift, which is the case worth surfacing.

If the script is not found, not executable, or exits with an unexpected error, skip to Section 9 (Fallback Procedure) and perform all checks manually. The fallback performs the same checks using inline git and filesystem commands, so functionality is preserved regardless of script availability.

---

## 3. Interpret Results

Parse the JSON output and evaluate each check independently. Present findings in the Drift section of the status report (Section 4). Rules per check:

**`commit_drift`**
- If `stale == true`: list the entries in `commit_summaries`. Note the `commits_since` count.
  - Narration: "N commits have been made since this handoff."

**`branch_drift`**
- If `stale == true`: surface the previous and current branch values.
  - Narration: "Branch changed from X to Y. Was this intentional?"

**`uncommitted_changes`**
- If `stale == true`: list the entries in `files_changed`. Handoff artifacts are already filtered out, so everything listed here is real project work.
  - Narration: "There are uncommitted changes not captured in the handoff."

**`spec_changes`**
- If `stale == true`: list the paths in `modified_files`.
  - Narration: "These spec or plan files were modified since the handoff was created."

**`dependency_changes`**
- If `stale == true`: flag the affected lockfile or manifest.
  - Narration: "Dependencies may have changed. Consider running the install command before continuing."

**Error fields**
- If any check contains an `error` field, note the error in the report but do not treat that check as stale. Errors indicate the check could not run, not that drift exists.

If all checks have `stale == false` and no errors, status is Fresh.

---

## 4. Status Report Template

Present the full status report using this exact structure. Fill each section from the handoff file content and drift analysis. Do not omit sections - if a section has no content (for example, no drift), say so explicitly.

Write the report itself in plain language. This is the first thing the user reads in the new session, so it is also the first proof that the working agreement was picked up.

Content in the loaded handoff has already been redacted at generation time per `references/handoff-generation.md` Section 10. Resume Mode does not re-scrub - it reads and echoes the file as-is. If the loaded handoff contains `[REDACTED:*]` markers, reproduce them verbatim.

```markdown
## Handoff Resume - YYYY-MM-DD

### TL;DR

- **Picking up:** [one line - phase, branch, and what the last session was doing]
- **Status:** ✅ Fresh, nothing moved. Or: ⚠️ Drift detected, [what moved, in one clause]
- **First thing to do:** [first item from What's Next]
- **Watch out for:** [top friction point]
- **Needs your call:** [anything the drift check raised that only the user can settle, or "nothing"]

**Handoff from:** [created timestamp from frontmatter]
**Handoff file:** [path to the file actually read]
**Mode:** resume (source handoff was written in [compact/full/long] mode)
**Context size:** [host-reported context size, or "not available from host"]
**Limits:** [host-reported limits, or "not available from host"]

### Working agreement for this session

- Plain language, short forms spelled out, TL;DR at the top and bottom of every reply.
- Independent work goes to a team of subagents running in parallel; the main chat stays small and handles decisions and review.

### Where We Left Off
[Refined Intent section from handoff]

### What Was Accomplished
[What Was Built section from handoff, summarized]

### Drift Since Handoff
[Only present if drift detected. List each drift item with narration from Section 3.
If no drift, write "No drift detected."]

### Priority for This Session
[What's Next section from handoff. If the handoff contains a `### Carried forward from previous session` subsection, surface it distinctly at the top of this section under the label "**Carried forward (unresolved from prior sessions):**", then list new priorities under "**New this session:**". This makes multi-session drift visible - if an item has been carried for multiple sessions, the user sees it appear repeatedly in successive resume reports.]

**Can run in parallel:** [items that do not depend on each other, or "nothing - these are sequential"]

### Friction Points to Avoid
[Friction Points section from handoff]
```

The date in the heading is today's date (the resume date), not the handoff creation date.

---

## 5. Goal Check

If `.handoffs/LATEST-GOAL.md` exists, read it and compare it against the drift findings. See `references/next-session-contract.md` Section 4 for how `/goal` actually behaves - it is a finish-line check, not stored context, and its evaluator can only see the conversation.

- **No drift and the brief still matches reality:** offer the ready-made finish line once.

  > There's a finish line ready in `.handoffs/LATEST-GOAL.md`: "[condition from its `## Finish line` section]". Want to set it with `/goal` so I keep working until it's met?

  Ask once. If the user says no or says nothing, drop it.

- **Drift found that changes the priorities:** do **not** offer the finish line, because it now describes the wrong end state. Say so plainly instead - "The finish line in the goal file is out of date because [reason]. Want me to generate a fresh handoff and goal now, or work from the corrected priorities above?"

- **A goal is already active:** leave it alone. `/goal` holds one condition at a time, and setting a new one silently replaces it. Just report what is active.

- **File missing:** say nothing. The previous session used `--no-goal`, which is a valid choice.

Do not silently rewrite `LATEST-GOAL.md` during resume. Goal files are written by Generate Mode only, so the timestamped record and the pointer never disagree. Never set a goal on the user's behalf - `/goal` changes when the session is allowed to stop, so it is the user's call.

---

## 6. Memory Update

After presenting the status report, update the host project memory unless the user has disabled memory updates. See `references/handoff-generation.md` Section 6 for the host rules - the short version is that Claude Code has a markdown memory tree and other hosts generally do not, so on those hosts you skip this step rather than inventing a path.

**Claude Code path:** `~/.claude/projects/{project-path}/memory/handoff_state.md`

The `{project-path}` segment mirrors the current working directory path with slashes replaced by hyphens (for example, `/home/user/Projects/MyApp` becomes `-home-user-Projects-MyApp`).

Add or update the following line in that file:

```
**Last resumed:** YYYY-MM-DD HH:MM
```

Use the current date and time. If the file does not exist, create it with this line as the initial content. If the file exists and already contains a "Last resumed" line, replace it. This entry confirms the handoff was verified and loaded for the current session.

---

## 7. Ready Prompt

End the resume sequence with:

> Ready to continue. Want me to start with [first priority item from What's Next], or do you have something else in mind?

Extract the first item from the "What's Next" section of the handoff and name it specifically. Do not use a generic placeholder.

When two or more priorities are independent, add one line offering the parallel route:

> Items [N] and [M] don't depend on each other. I can put them on separate teammates and run them at the same time if you want to move faster.

---

## 8. Edge Cases to Handle

**No previous handoff**
After the Storage Preflight, neither `.handoffs/LATEST.md` nor any `*-handoff.md` file exists. Inform the user and stop. Do not attempt recovery or inference. (See Section 1.)

**Handoffs in a wrong location**
The Storage Preflight copies them into `.handoffs/` before this procedure starts. Reproduce its notice, then continue normally. Never read a handoff straight out of `.claude/handoffs/` or any other stray folder - that is how the wrong path spreads.

**`LATEST.md` missing but day folders present**
Fall back to the newest `*-handoff.md` found anywhere under `.handoffs/` and say that you did. (See Section 1.)

**Handoff file manually edited**
Attempt to detect by comparing the file's modification time against the `created` timestamp in the frontmatter. If mtime is meaningfully later than `created`, note: "This handoff file appears to have been modified since it was generated."

Known limitation: some editors and tools preserve mtime on save, while others change it without content changes. This check is not guaranteed to catch all edits and may produce false positives or false negatives. Treat it as a best-effort signal, not a definitive flag.

**Handoff has no `## Start Here` block**
It was written by an older version of the skill. Do not treat this as an error. Print the working agreement from `references/next-session-contract.md` Section 7 anyway, and note in one line that the handoff predates the working-agreement block.

**Resume in a different project**
Scoping is always the current working directory's `.handoffs/`. If the user runs `--resume` in a project that has no handoff, they get the "No previous handoff found" message - not a handoff from a different project. Handoffs never cross project boundaries.

---

## 9. Fallback Procedure

Use this procedure if `freshness-check.sh` is missing, not executable, or exits with an error. Perform each check manually using git and filesystem commands, then produce the same status report format from Section 4.

**Step 1 - Parse frontmatter**
Read the handoff file and extract these fields from the YAML frontmatter block:
- `created`
- `branch`
- `last_commit`
- `uncommitted_changes`

**Step 2 - Commit drift**
```bash
git log --oneline {last_commit}..HEAD
```
If the output is non-empty, commits have been made since the handoff. List them.

**Step 3 - Branch drift**
```bash
git branch --show-current
```
Compare against the `branch` value from frontmatter. If they differ, flag the change.

**Step 4 - Uncommitted changes**
```bash
git status --short
```
Compare against the `uncommitted_changes` value from frontmatter. New untracked or modified files not described in the handoff represent drift.

**Step 5 - Spec and plan changes**
```bash
find docs/ .handoffs/ .claude/ .Codex/ .codex/ -newer .handoffs/LATEST.md -type f 2>/dev/null
```
Any files returned were modified after the handoff was created. Ignore the handoff run's own artifacts - the three `LATEST*.md` pointers and any file whose name starts with the same `YYYY-MM-DD-HH-MM` timestamp as the handoff you are checking. List everything else as spec drift.

**Step 6 - Dependency changes**
```bash
find . -maxdepth 1 -name "package.json" -newer .handoffs/LATEST.md
find . -maxdepth 1 -name "package-lock.json" -newer .handoffs/LATEST.md
find . -maxdepth 1 -name "yarn.lock" -newer .handoffs/LATEST.md
find . -maxdepth 1 -name "pnpm-lock.yaml" -newer .handoffs/LATEST.md
```
If any match, warn that dependencies may have changed and suggest running the install command.

**Step 7 - Produce report**
Using the results of all six steps above, produce the status report using the same template from Section 4. Label the report as generated via fallback so the user knows the script was not available.
