# Session Goal - ModernPageBuilder

**Full context:** read `.handoffs/LATEST.md` before you start working.
**Verify first:** run `/handoff --resume` to check this against the current project state.

## How to write back to me

Plain, everyday language, like you are explaining it to a smart middle school student. Spell out every short form the first time you use it, with the short form in parentheses. Start every reply with a short TL;DR (too long, didn't read) of 2 to 5 bullets and end with a one-line TL;DR. No em dash characters.

## How to work

Use an agent team for independent pieces of work and run them at the same time - saying "fan out subagents" starts one in Claude Code. Teammates are individually addressable, so let them message each other directly. Keep the main chat for decisions and review so its context stays small. Do small or strictly ordered work yourself.

## The mission

Build out Phase 2D, the media and data modules, on top of the parent-child module system that Phase 2C just finished. Every module follows the same 6-file pattern, so this is repeatable work that splits well across teammates.

## Do these, in this order

1. Video module - embed support for YouTube and Vimeo, plus a custom player with controls and autoplay/loop settings.
2. Audio module - same shape as Video but audio only, with an optional waveform display.
3. Gallery module - grid, masonry, and carousel layouts with a lightbox.

All three are independent. One module per teammate is a good split. Land the registry line in `packages/module-library/src/modules/index.ts` last so teammates do not collide on it.

## Do not do

- Do not import `ChildRenderer` directly from builder-ui into module-library. It creates a circular dependency that only shows up at runtime, and it cost most of a session last time. Go through `ChildRendererContext` in the core package instead.
- Do not animate expand and collapse with a CSS `max-height` transition. It janks on variable content. Use the existing `useExpandCollapse` hook, which measures real height.

## Where we are

Branch `master` at `042df07`. 214 tests passing and the production build is green at 357KB. Nothing uncommitted, no blockers.

## Finish line

Paste this into Claude Code to make the session keep working until the job is actually done:

    /goal The Video module renders a YouTube embed in both edit mode and view mode, and `pnpm test` exits 0 with the summary line shown in this conversation.

Clear it any time with `/goal clear`. Check it with `/goal`.

<!--
Size check for this example: the body above is roughly 2,500 characters
and the /goal condition itself is 153 characters,
comfortably inside the 3,000 character budget in
references/next-session-contract.md Section 5.2, and well inside the
4,000 character ceiling /goal enforces on a condition. This comment is
not part of the template and should not appear in generated goal files.
-->
