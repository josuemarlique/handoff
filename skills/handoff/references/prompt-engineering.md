# Formatting Reference

Formatting rules for the three verbosity modes: `compact`, `full`, and `long`. Load this file whenever the mode is not the default. All templates and rules here supplement `handoff-generation.md` - they govern shape and density, not content decisions.

Two things are identical in all three modes and are never compressed or expanded:

- The `## Start Here` block (`next-session-contract.md` Section 2).
- The goal file (`next-session-contract.md` Section 5), which is size-capped regardless of mode.

---

## 1. Full Mode Formatting Rules (Default)

Default behavior. No token restrictions. Apply when neither `--compact` nor `--long` is set.

**Section headers:** Full markdown headers that spell out the section name.

```markdown
## Start Here
## TL;DR
## Refined Intent
## What Was Built
## Decisions Made
## Friction Points
## Current State
## What's Next
## Environment Notes
## User Notes
```

**Descriptions:** Full sentences with context and explanation. Assume the reader has no memory of the session.

**Friction points:** Narrative format with subsections per entry.

```markdown
### [Short description of the problem]
- **What happened:** [Full context - what the situation was, what triggered the problem]
- **What was tried:** [Each failed approach on its own line, enough detail to avoid repeating it]
- **What worked:** [Solution that resolved it, or current status if unresolved]
- **Severity:** High/Medium/Low - [brief justification for the rating]
```

**Decisions:** Reasoning paragraphs explaining the "why" behind each choice. Include the tradeoff evaluated, the constraint that forced the decision, or the goal that drove it. Do not stop at describing what was decided.

**What's Next:** Priority-ordered items with context and reasoning for the ordering. Each item should explain not just what to do but why it is first - what depends on it or what risk it mitigates. Call out which items are independent of each other, so the next session knows what it can hand to parallel teammates.

**Code references:** Full file paths with a one-line description of what each file does or why it was touched.

```markdown
- `src/components/Canvas/CanvasRoot.tsx` - Root drag-and-drop surface; modified to accept pointer events from mobile
```

**Environment notes:** Explanatory prose about why changes were made, not just what changed.

```markdown
Added `@use-gesture/react` because the native pointer event API does not normalize touch vs. mouse deltas across browsers. This replaces the hand-rolled event listeners in `src/hooks/useDrag.ts`.
```

**Sensitive data:** all content passes through the redaction rules defined in `handoff-generation.md` Section 10 before being written. Full mode does not suppress or relax any redaction; matched credentials appear as `[REDACTED:<type>]` markers regardless of section.

---

## 2. Compact Mode Formatting Rules (`--compact`)

Token-conscious variant. Same information, terse formatting. Apply throughout the document.

**Section headers:** Abbreviated single-line headers. Drop adjectives; keep the noun.

| Full | Compact |
|------|---------|
| `## Start Here` | `## Start Here` *(never abbreviated)* |
| `## TL;DR` | `## TL;DR` *(never abbreviated)* |
| `## Refined Intent` | `## Intent` |
| `## What Was Built` | `## Built` |
| `## Decisions Made` | `## Decisions` |
| `## Friction Points` | `## Friction` |
| `## Current State` | `## State` |
| `## What's Next` | `## Next` |
| `## Environment Notes` | `## Env` |
| `## User Notes` | `## Notes` |

**Descriptions:** Terse bullet points. Sentence fragments are acceptable. Omit filler phrases ("In order to", "It was determined that"). Front-load the meaningful noun or verb.

**Friction points:** One-liner format per entry.

```
- **[description]:** ❌ approach1, ❌ approach2 → ✅ working solution
```

If an item is unresolved, end with `→ unresolved` instead of a working solution.

**Decisions:** Single-line format.

```
Decision: X because Y
```

**What's Next:** Numbered list. No elaboration or ordering rationale. Mark independent items with `[parallel]` so the agent-teams hint survives compression.

```markdown
1. Implement drag handle persistence
2. Fix z-index collision on nested blocks [parallel]
3. Wire undo/redo to keyboard shortcuts [parallel]
```

**Code references:** `file:line` shorthand when a specific line is relevant. File path only when the whole file is the reference.

```
src/store/canvasSlice.ts:142
src/components/Canvas/CanvasRoot.tsx
```

**Environment notes:** Key-value pairs only. No explanatory prose.

```
dep added: @use-gesture/react@10.3
config changed: vite.config.ts - added resolve alias for @canvas
script added: scripts/generate-tokens.ts
```

**Frontmatter:** Unchanged in all modes. It is already flat, single-line, and machine-readable. Do not compress or modify it.

**Sensitive data:** Compact mode applies the same Section 10 redaction. Redaction markers are identical (`[REDACTED:<type>]`) and are not further abbreviated - the purpose is legibility to a future reader, not density.

---

## 3. Long Mode Formatting Rules (`--long`)

Maximum-detail variant. Everything full mode does, plus more depth and four extra sections. Nothing is trimmed for length. Use when the next session may be far away in time, when the work is complex, or when the user asks for "everything".

**Section headers:** Same as full mode, plus the four long-only sections at the end.

**Depth rules:**

- **Decisions:** include the options that were considered and rejected, not just the one chosen. State what would have to change for the rejected option to win. That is what stops the next session from relitigating the same choice.
- **Friction points:** include every entry detected, including Low severity. Full mode may drop Low-severity items; long mode does not. Add a **How to spot it again** line to each entry describing the symptom, so the next session recognizes the problem before spending time on it.
- **What Was Built:** keep the grouped-by-concern structure, but add the "why now" for each group.
- **Test and build output:** the cap rises from 40 to 120 lines per command (see `handoff-generation.md` Section 10.4).

### 3.1 `## File-By-File Notes`

Every file created, modified, or deleted this session. One row per file.

```markdown
| File | Change | Why it matters next session |
|---|---|---|
| `src/store/canvasSlice.ts` | Added `activeTabId` selector | Anything reading tab state must go through this selector now, not the raw index |
| `src/hooks/useDrag.ts` | Deleted | Replaced by `@use-gesture/react`; do not resurrect it |
```

Derive the file list from `git diff --name-status` plus any uncommitted changes. If more than 40 files changed, group by directory and describe the group, then list individually only the files whose change is not obvious from the group description.

### 3.2 `## Commands That Matter`

Copy-paste ready commands, with a one-line description of each. Include the ones that were hard to get right, not just the standard ones.

```markdown
| Command | What it does |
|---|---|
| `pnpm install` | Install dependencies. Needed after the lockfile change this session. |
| `pnpm test -- --filter=core` | Run only the core suite. The full run takes 4 minutes. |
| `pnpm build && pnpm preview` | Reproduce the production bundle-size number quoted in Current State. |
```

Never include a command with a credential in it. Replace the value with a placeholder and note where the real value lives, without quoting the file's contents.

### 3.3 `## Open Questions`

Things raised and not settled. Each entry names who or what can answer it, so the next session knows whether it can decide alone.

```markdown
- **Should the slider auto-play in edit mode?** Currently off. Needs a product call from the user - do not decide this in code.
- **Is the 357KB bundle acceptable?** No budget defined yet. Check `docs/prd.md` or ask.
```

If there are none, write "None - nothing was left hanging." Do not omit the section.

### 3.4 `## Glossary`

Every project-specific term, internal name, and short form used anywhere in this handoff, with a plain-language definition. This section is what makes the `## Start Here` rule about spelling out short forms achievable - the next session can look terms up instead of guessing.

```markdown
| Term | Plain meaning |
|---|---|
| Module | One draggable block on the page, like a heading or an image |
| PRD | Product requirements document - the spec at `docs/prd.md` |
| Containment rule | The setting that says which modules are allowed inside which other modules |
```

Sort alphabetically. If a term appears only once and is already explained inline, it still belongs here.

---

## 4. Continuation Prompt Templates

The canonical templates live in `handoff-generation.md` Section 3. `full` and `long` share the same template; `compact` uses the short one. All three include the writing-style and agent-teams lines - those are never dropped, because a continuation prompt without them produces a session that ignores the working agreement.

---

## 5. Side-by-Side Comparison

| Aspect | Compact | Full | Long |
|--------|---------|------|------|
| Section headers | Abbreviated (`## Intent`) | Full names (`## Refined Intent`) | Full names, plus four extra sections |
| Descriptions | Terse bullets, fragments OK | Full sentences with context | Full sentences plus "why now" |
| Friction points | `❌ approach → ✅ fix` one-liners | Problem / tried / worked / severity | Same, plus rejected options and "how to spot it again"; Low severity included |
| Decisions | `Decision: X because Y` | Reasoning paragraphs with tradeoffs | Reasoning plus rejected alternatives and what would flip the call |
| What's Next | Numbered, `[parallel]` markers | Priority-ordered with rationale | Same as full, nothing trimmed |
| Code references | `file:line` shorthand | Full path with purpose | Full `## File-By-File Notes` table |
| Environment notes | Key-value pairs | Explanatory prose | Prose plus `## Commands That Matter` |
| Extra sections | None | None | File-By-File, Commands, Open Questions, Glossary |
| Test/build output cap | 40 lines | 40 lines | 120 lines |
| `## Start Here` | Verbatim | Verbatim | Verbatim |
| `## TL;DR` | Five bullets | Five bullets | Five bullets |
| Goal file | Same, capped at 3,000 chars | Same, capped at 3,000 chars | Same, capped at 3,000 chars |
| Frontmatter | Same | Same | Same |

---

## 6. Length Advisory Rule

Append the following line at the end of the user-facing output when the session was high-volume. Do not append it otherwise.

> "This handoff is lengthy - consider `--compact` if the next session is working with limited context."

**Trigger conditions - apply if any one is true:**

- 10 or more commits since the last handoff
- 5 or more distinct friction points
- 3 or more major decisions

**Implementation notes:**

- Evaluate these conditions against the data already gathered during context gathering (git log count, friction point list length, decision count). No additional scanning needed.
- The suggestion is informational. Do not automatically switch modes.
- The trigger is based on input volume indicators, not a post-generation word count. Evaluate before writing output, not after.
- Suppress the advisory when the mode is already `compact` - it is not relevant.
- Suppress it when the mode is `long` - the user asked for length on purpose. Instead note: "Long mode - the goal file at `.handoffs/LATEST-GOAL.md` is the short version if the next session needs to start small."
