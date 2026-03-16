# Sentiment Analysis Reference — Handoff Skill

This file defines how Claude detects friction and frustration patterns when scanning conversation history to produce a handoff summary.

---

## 1. Signal Categories

| Category | Severity | Patterns to Detect |
|----------|----------|-------------------|
| Repeated attempts | High | Same file edited 3+ times for the same issue, same test run repeatedly with same failure, rollback-then-retry cycles, "let me try again" |
| Explicit frustration | Medium | "this doesn't work", "that's wrong", "no not that", "ugh", "again?", "why isn't this working", "that's not what I asked" |
| Approach abandonment | High | "let's try a different approach", "scrap that", "forget that idea", "that's not going to work", "let's go back to", "never mind that" |
| Error loops | High | Same error message appearing multiple times in tool output, same test failing repeatedly with the same assertion, build errors recurring after attempted fixes |
| Workarounds | Medium | "for now let's just", "hack around", "temporary fix", "we'll come back to", "good enough for now", "skip this for now" |
| Corrections | Low | User correcting Claude's understanding: "I meant", "no I said", "that's not what I mean", "I was talking about", "not that one" |
| Blockers | High | "blocked by", "can't because", "waiting on", "dependency issue", "need X before we can", "this requires", "no access to" |

---

## 2. Detection Instructions

Scan the conversation using this process:

1. Review the conversation chronologically, focusing on user messages and tool output
2. Look for the specific text patterns from the table above
3. Also look for behavioral patterns: same file appearing in multiple edit tool calls, same bash command run multiple times, git revert/reset commands
4. Note the context around each detected signal — what was being worked on, what the goal was
5. Group related signals into friction point entries (don't create separate entries for "ugh" and "this doesn't work" if they're about the same problem)
6. Prioritize by severity: High items always included, Medium items if they have solutions, Low items only if they represent significant misunderstandings

---

## 3. Friction Point Output Format (Full Mode)

Use this format when producing a detailed handoff summary.

```markdown
### [Short description of the friction]
- **What happened:** [Context — what was being worked on when the friction occurred]
- **What was tried:** [List of approaches that failed or were abandoned]
- **What worked:** [The solution that ultimately resolved it, or "Unresolved — [current status]" if still open]
- **Severity:** High/Medium/Low — [brief justification for the severity level]
```

---

## 4. Friction Point Output Format (Compact Mode)

Use this format when producing a brief or inline handoff summary.

```markdown
- **[Short description]:** failed-approach-1, failed-approach-2 → working-solution
```

If unresolved:

```markdown
- **[Short description]:** approach-1, approach-2 → unresolved
```

---

## 5. Key Principles

- **Neutral and solution-oriented** — This is a "don't step on this rake" map, not a judgment. Frame friction points as information for the next session, not criticism.
- **Include solutions, not just problems** — A friction point without a solution is only half useful. If the problem was resolved, say how. If it wasn't, say what the current state is.
- **Group related signals** — Don't list every individual "ugh" or retry. Group them into the overarching friction event they belong to.
- **Prioritize high-severity first** — Order friction points by severity (High then Medium then Low) in the output.
- **Don't fabricate friction** — Only report friction that actually happened in the conversation. If the session was smooth, the Friction Points section can be empty or say "No significant friction detected."
- **Context matters more than count** — One high-severity blocker that consumed 30 minutes is more important than five low-severity corrections.
