# Prompt Engineering Reference

Formatting rules for full and compact handoff output. Load this file when `--compact` is set. All templates and rules here supplement `handoff-generation.md` — they govern shape and density, not content decisions.

---

## 1. Full Mode Formatting Rules (Default)

Default behavior. No token restrictions. Apply when `--compact` is absent.

**Section headers:** Full markdown headers that spell out the section name.

```markdown
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
- **What happened:** [Full context — what the situation was, what triggered the problem]
- **What was tried:** [Each failed approach on its own line, enough detail to avoid repeating it]
- **What worked:** [Solution that resolved it, or current status if unresolved]
- **Severity:** High/Medium/Low — [brief justification for the rating]
```

**Decisions:** Reasoning paragraphs explaining the "why" behind each choice. Include the tradeoff evaluated, the constraint that forced the decision, or the goal that drove it. Do not stop at describing what was decided.

**What's Next:** Priority-ordered items with context and reasoning for the ordering. Each item should explain not just what to do but why it is first — what depends on it or what risk it mitigates.

**Code references:** Full file paths with a one-line description of what each file does or why it was touched.

```markdown
- `src/components/Canvas/CanvasRoot.tsx` — Root drag-and-drop surface; modified to accept pointer events from mobile
```

**Environment notes:** Explanatory prose about why changes were made, not just what changed.

```markdown
Added `@use-gesture/react` because the native pointer event API does not normalize touch vs. mouse deltas across browsers. This replaces the hand-rolled event listeners in `src/hooks/useDrag.ts`.
```

---

## 2. Compact Mode Formatting Rules (`--compact`)

Token-conscious variant. Same information, terse formatting. Apply throughout the entire document when `--compact` is set.

**Section headers:** Abbreviated single-line headers. Drop adjectives; keep the noun.

| Full | Compact |
|------|---------|
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

**What's Next:** Numbered list. No elaboration or ordering rationale.

```markdown
1. Implement drag handle persistence
2. Fix z-index collision on nested blocks
3. Wire undo/redo to keyboard shortcuts
```

**Code references:** `file:line` shorthand when a specific line is relevant. File path only when the whole file is the reference.

```
src/store/canvasSlice.ts:142
src/components/Canvas/CanvasRoot.tsx
```

**Environment notes:** Key-value pairs only. No explanatory prose.

```
dep added: @use-gesture/react@10.3
config changed: vite.config.ts — added resolve alias for @canvas
script added: scripts/generate-tokens.ts
```

**Frontmatter:** Unchanged in both modes. It is already flat, single-line, and machine-readable. Do not compress or modify it.

---

## 3. Full Continuation Prompt Template

Use this template when generating the continuation prompt in full (default) mode.

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

---

## 4. Compact Continuation Prompt Template

Use this template when `--compact` is set.

```
Continue from .claude/handoffs/LATEST.md — run /handoff --resume first.
Project: [name] | Branch: [branch] | Phase: [phase]
Last: [one-line summary] | Next: [one-line priority]
Avoid: [one-line top friction point]
```

---

## 5. Side-by-Side Comparison

| Aspect | Full | Compact |
|--------|------|---------|
| Section headers | Full names (`## Refined Intent`) | Abbreviated (`## Intent`) |
| Descriptions | Full sentences, context included | Terse bullet points, fragments OK |
| Friction points | Problem / tried / worked / severity narrative | `❌ approach → ✅ fix` one-liners |
| Decisions | Reasoning paragraphs with tradeoffs | `Decision: X because Y` single lines |
| What's Next | Priority-ordered with context and ordering rationale | Numbered list, no elaboration |
| Code references | Full file path with description of purpose | `file:line` shorthand |
| Environment notes | Explanatory prose about why changes were made | Key-value pairs only |
| Frontmatter | Same | Same (machine-readable, already minimal) |
| Continuation prompt | Multi-line with labeled fields | Four-line dense format |

---

## 6. Length Advisory Rule

Append the following line at the end of the user-facing output when the session was high-volume. Do not append it otherwise.

> "This handoff is lengthy — consider `--compact` if you're working with limited context."

**Trigger conditions — apply if any one is true:**

- 10 or more commits since the last handoff
- 5 or more distinct friction points
- 3 or more major decisions

**Implementation notes:**

- Evaluate these conditions against the data already gathered during context gathering (git log count, friction point list length, decision count). No additional scanning needed.
- The suggestion is informational. Do not automatically switch to compact mode.
- The trigger is based on input volume indicators, not a post-generation word count. Evaluate before writing output, not after.
- If `--compact` was already passed, suppress the advisory — it is not relevant.
