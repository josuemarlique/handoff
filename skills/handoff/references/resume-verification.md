# Resume Verification Reference

This is the procedure the host agent follows when invoked in resume mode (`--resume`). It loads the previous session's handoff, checks for drift since the handoff was created, and presents a structured status report before continuing work.

---

## 1. Locate Handoff

Run Migration Preflight, then read `.handoffs/LATEST.md` in the **current working directory**. This path is always relative to cwd — handoffs do not cross project boundaries, and project memory does not override this scope.

If the file is not found, display the following and stop:

> No previous handoff found. Use `/handoff` at the end of a session to create one.

Do not attempt to search parent directories or other locations. Scoping is strict.

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

If the script is not found, not executable, or exits with an unexpected error, skip to Section 8 (Fallback Procedure) and perform all checks manually. The fallback procedure performs the same checks using inline git and filesystem commands, so functionality is preserved regardless of script availability.

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
- If `stale == true`: list the entries in `files_changed`.
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

Present the full status report using this exact structure. Fill each section from the handoff file content and drift analysis. Do not omit sections — if a section has no content (e.g., no drift), note that explicitly.

Content in the loaded handoff has already been redacted at generation time per `references/handoff-generation.md` Section 10. Resume Mode does not re-scrub — it reads and echoes the file as-is. If the loaded handoff contains `[REDACTED:*]` markers, reproduce them verbatim in the status report.

```markdown
## Handoff Resume — YYYY-MM-DD

**Handoff from:** [created timestamp from frontmatter]
**Mode:** resume
**Context size:** [host-reported context size, or "not available from host"]
**Limits:** [host-reported limits, or "not available from host"]
**Status:** ✅ Fresh (no drift detected)
  — or —
**Status:** ⚠️ Drift detected ([summary of what drifted])

### Where We Left Off
[Refined Intent section from handoff]

### What Was Accomplished
[What Was Built section from handoff, summarized]

### Drift Since Handoff
[Only present if drift detected. List each drift item with narration from Section 3.
If no drift, omit this section or write "No drift detected."]

### Priority for This Session
[What's Next section from handoff. If the handoff contains a `### Carried forward from previous session` subsection, surface it distinctly at the top of this section under the label "**Carried forward (unresolved from prior sessions):**", then list new priorities under "**New this session:**". This makes multi-session drift visible — if an item has been carried for multiple sessions, the user sees it appear repeatedly in successive resume reports.]

### Friction Points to Avoid
[Friction Points section from handoff]
```

The date in the heading is today's date (the resume date), not the handoff creation date. The "Handoff from" line uses the `created` timestamp from the handoff frontmatter.

---

## 5. Memory Update

After presenting the status report, update the host project memory file unless the user has disabled memory updates. Use the current host's memory root:

- Claude Code: `~/.claude`
- Codex: `~/.Codex`
- Other hosts: skip unless the user explicitly provides a memory target

**Path:** `<memory-root>/projects/{project-path}/memory/handoff_state.md`

The `{project-path}` segment mirrors the current working directory path with slashes replaced by hyphens (e.g., `/home/user/Projects/MyApp` becomes `-home-user-Projects-MyApp`).

Add or update the following line in that file:

```
**Last resumed:** YYYY-MM-DD HH:MM
```

Use the current date and time. If the file does not exist, create it with this line as the initial content. If the file exists and already contains a "Last resumed" line, replace it. This entry confirms the handoff was verified and loaded for the current session.

---

## 6. Ready Prompt

End the resume sequence with:

> Ready to continue. Want me to start with [first priority item from What's Next], or do you have something else in mind?

Extract the first item from the "What's Next" section of the handoff and name it specifically. Do not use a generic placeholder.

---

## 7. Edge Cases to Handle

**No previous handoff**
After Migration Preflight, the file `.handoffs/LATEST.md` does not exist. Inform the user and stop. Do not attempt recovery or inference. (See Section 1.)

**Handoff file manually edited**
Attempt to detect by comparing the file's modification time against the `created` timestamp in the frontmatter. If mtime is meaningfully later than `created`, note: "This handoff file appears to have been modified since it was generated."

Known limitation: some editors and tools preserve mtime on save, while others change it without content changes. This check is not guaranteed to catch all edits and may produce false positives or false negatives. Treat it as a best-effort signal, not a definitive flag.

**Resume in a different project**
Scoping is always the current working directory's `.handoffs/LATEST.md`. If the user runs `--resume` in a project that has no handoff, they get the "No previous handoff found" message — not a handoff from a different project. Handoffs never cross project boundaries.

---

## 8. Fallback Procedure

Use this procedure if `freshness-check.sh` is missing, not executable, or exits with an error. Perform each check manually using git and filesystem commands, then produce the same status report format from Section 4.

**Step 1 — Parse frontmatter**
Read `.handoffs/LATEST.md` and extract these fields from the YAML frontmatter block:
- `created`
- `branch`
- `last_commit`
- `uncommitted_changes`

**Step 2 — Commit drift**
```bash
git log --oneline {last_commit}..HEAD
```
If the output is non-empty, commits have been made since the handoff. List them.

**Step 3 — Branch drift**
```bash
git branch --show-current
```
Compare against the `branch` value from frontmatter. If they differ, flag the change.

**Step 4 — Uncommitted changes**
```bash
git status --short
```
Compare against the `uncommitted_changes` list from frontmatter. New untracked or modified files not listed in the handoff represent drift.

**Step 5 — Spec and plan changes**
```bash
find docs/ .handoffs/ .claude/ .Codex/ .codex/ -newer .handoffs/LATEST.md -type f 2>/dev/null
```
Any files returned were modified after the handoff was created. List them as spec drift.

**Step 6 — Dependency changes**
```bash
find . -maxdepth 1 -name "package.json" -newer .handoffs/LATEST.md
find . -maxdepth 1 -name "package-lock.json" -newer .handoffs/LATEST.md
find . -maxdepth 1 -name "yarn.lock" -newer .handoffs/LATEST.md
find . -maxdepth 1 -name "pnpm-lock.yaml" -newer .handoffs/LATEST.md
```
If any match, warn that dependencies may have changed and suggest running the install command.

**Step 7 — Produce report**
Using the results of all six steps above, produce the status report using the same template from Section 4. Label the report as generated via fallback so the user knows the script was not available.
