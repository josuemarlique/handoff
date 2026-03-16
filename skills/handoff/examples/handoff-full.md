---
created: 2026-03-14T02:30:00
branch: master
last_commit: 042df07
last_commit_message: "feat(module-library): add Dropdown with hover/click trigger modes"
uncommitted_changes: false
test_summary: "214 passing (129 core + 85 style-engine)"
build_status: passing
stop_reason: context-limit
phase: "2C - Interactive Modules"
---

## Refined Intent

This session aimed to implement Phase 2C of the ModernPageBuilder project — adding interactive modules that support parent-child relationships. The goal was to build 5 parent modules (Toggle, Accordion, Tabs, Slider, Dropdown) and 3 child module types (AccordionItem, Tab, Slide), along with the core infrastructure to support parent-child module patterns (containment rules, child rendering context, shared animation hooks).

## What Was Built

**Core Infrastructure:**
- Extended containment rules for 5 interactive types + 3 child types
- Extended `ModuleDefinition` type with `rendersOwnChildren`, `showInInserter`, `insertPreset`
- Added conditional child rendering in `BlockRenderer` (one-line change)
- Created `ChildRendererContext` in core package (solves circular dependency between builder-ui and module-library)
- Built `useExpandCollapse` shared hook with scrollHeight-based animation
- Updated `ModuleInserter` with preset integration + child module filtering

**Module Registrations (8 total):**
- Toggle — standalone expand/collapse leaf module
- Accordion + AccordionItem — configurable single/multi-open, React Context for parent-child state
- Tabs + Tab — horizontal/vertical layout, activeTabId-based tracking (stable across reorder/delete)
- Slider + Slide — fade/slide transitions, arrows, pagination dots, auto-play in View mode, swipe via @use-gesture/react
- Dropdown — always-expanded in edit mode, hover/click trigger in View with directional positioning

**Tests:**
- 9 new containment rule tests
- Total: 214 passing (129 core + 85 style-engine)

## Decisions Made

**1. ChildRendererContext in core to solve circular dependency**

Importing ChildRenderer directly from builder-ui into module-library would create a circular dependency (module-library → builder-ui → module-library). Instead, we created a React Context in the core package that builder-ui provides and module-library consumes. This adds one level of indirection but cleanly breaks the cycle.

**2. scrollHeight-based animation instead of CSS transitions**

CSS `max-height` transitions require a fixed value, which produces janky animation when the content height doesn't match. Using `scrollHeight` measurement via the `useExpandCollapse` hook gives pixel-perfect animation regardless of content size. The hook is shared across Toggle, Accordion, and Dropdown.

**3. String-based activeTabId instead of index-based tab tracking**

Using the tab's block ID as the active identifier instead of a numeric index. Indices break when tabs are reordered or deleted; string IDs remain stable. This is slightly more complex but prevents a class of bugs.

**4. Dropdown always-expanded in edit mode**

In View mode, the dropdown opens on hover/click. But in edit mode, it's always expanded so the user can see and edit the content. This avoids the frustrating pattern of having to click to reveal content you want to edit.

## Friction Points

### Circular dependency between builder-ui and module-library

- **What happened:** When implementing the first parent-child module (Accordion), importing `ChildRenderer` from builder-ui into module-library created a circular dependency that broke the build. The error surfaced as a runtime undefined during test execution, not at compile time.
- **What was tried:** Direct import from builder-ui (circular), barrel re-export through a shared types package (still circular because of runtime dependency)
- **What worked:** Created `ChildRendererContext` in the core package as a React Context intermediary — module-library consumes the context, builder-ui provides it. One-line change in each package.
- **Severity:** High — took multiple attempts and a design rethink to resolve

### Toggle animation approach

- **What happened:** The initial CSS `max-height` transition for the Toggle expand/collapse produced visible janking — the animation speed varied based on how far the actual height was from the `max-height` value.
- **What was tried:** Fixed `max-height: 2000px` (too slow for short content), CSS grid `grid-template-rows: 0fr/1fr` trick (browser support concerns)
- **What worked:** Built `useExpandCollapse` hook that measures actual `scrollHeight` and applies it directly. Smooth animation at consistent speed regardless of content size.
- **Severity:** Medium — two approaches tried before landing on the solution

## Current State

- **Branch:** master @ 042df07
- **Tests:** 214 passing (129 core + 85 style-engine) — all green
- **Build:** Production build succeeds (357KB bundle, up from 310KB)
- **Uncommitted work:** None — all changes committed in 8 clean, incremental commits

## What's Next

Priority-ordered list for Phase 2D:

1. **Video module** — Embed support (YouTube, Vimeo), custom video player with controls, autoplay/loop settings
2. **Audio module** — Similar to Video but audio-only, waveform visualization option
3. **Gallery module** — Grid/masonry/carousel layouts, lightbox integration
4. **Counter module** — Animated number counting with scroll trigger
5. **Progress Bar module** — Horizontal/circular variants with animation
6. **Map module** — Google Maps / OpenStreetMap embed with marker customization

Each module follows the established 6-file pattern: `index.ts`, `schema.ts`, `settings.ts`, `styles.ts`, `Edit.tsx`, `View.tsx`.

## Environment Notes

- Added `@use-gesture/react@10.3.1` dependency for Slider swipe support
- All interactive modules registered in `packages/module-library/src/modules/index.ts`
- The `useExpandCollapse` hook is at `packages/module-library/src/hooks/useExpandCollapse.ts` — shared by Toggle, Accordion, and Dropdown
- Production build size increased from 310KB to 357KB (+47KB) due to @use-gesture/react and 8 new module registrations

## User Notes

- The Divi5 source for Slider is at `visual-builder/packages/module-library/src/components/slider/` — useful reference for transition patterns
- Phase 2D modules are listed in the roadmap at `docs/prd.md` under "Phase 2D: Media + Data Modules"
