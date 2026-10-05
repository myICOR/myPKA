---
type: sop
id: SOP-2011
title: Build a UI component
created: 2026-09-26
owner: felix
uses: ["[[GL-1005-code-vs-instructions]]", "[[SOP-1006-start-work-and-archive-a-wip-folder]]", "[[SOP-1013-connect-an-external-tool-via-mcp]]"]
skill_name: felix-build-ui-component
skill_summary: "Build or fix one web UI component in the user's code project, on the design system, typed, accessible and reviewed."
skill_triggers:
  - "build me a component"
  - "build this component"
  - "I need a form in the UI"
  - "extract this into a component"
  - "fix this UI bug"
---

# SOP-2011 Build a UI component

Felix's build procedure for one UI component, from reading the spec to
the hand-off for review. Any agent building a component can follow it.
Shipped by the Felix expansion pack; the pack number range is explained
in the pack's README.

Runs when the user says "build me a [component / form / card / modal /
panel]", "I need a [thing] in the UI", "extract this into a component".
A bug fix on an existing component uses steps 1, 5, 6, 8, 9 and 10.

The code lives in the user's project folder, never in this vault.

1. [JUDGEMENT] **Confirm the spec.** What the component does, its
   inputs, and its states (loading, empty, error, success, disabled).
   Anything ambiguous is one question to the user before a line is
   written; building the wrong thing fast is slower than asking once.
2. [JUDGEMENT] **Read the design system, then the codebase.** Open the
   user's design-system guideline if Iris has written one and note the
   tokens this component needs (colour, type, spacing, radius, motion)
   and any banned patterns. Then find the closest existing component in
   the project and match its file layout, naming, import style and prop
   style. Do not introduce a second pattern.
3. [JUDGEMENT] **Place it.** Global (used across the app), shared (two
   or more apps, not all), or app-specific (one app, never imported
   elsewhere). Take the narrowest scope that fits today; promoting later
   is cheap, promoting early is not.
4. [JUDGEMENT] **Build on tokens only.** No hardcoded colour
   (`bg-[#000]`, `bg-zinc-900/15`), no hardcoded size (`text-[14px]`),
   no magic spacing, no browser dialog in place of a designed surface,
   no constant the project keeps in one place typed again. A missing
   token stops the build: propose it to Iris or the user and wait. If a
   component-registry or motion MCP is connected, query it before
   building a primitive or choosing a curve, and cite the query; if
   none is connected, say where each value came from and offer the
   connection ([[SOP-1013-connect-an-external-tool-via-mcp|SOP-1013]]).
   A node graph follows the rules in Felix's contract.
5. [SCRIPT-CHECKED] **Type everything.** Every prop, callback, and the
   request and response shape of any data the component fetches or
   mutates. No `any`, no implicit any. The project's own type check and
   linter must pass; they answer this step, not a reading of the code
   ([[GL-1005-code-vs-instructions|GL-1005]]).
6. [JUDGEMENT] **Handle every state and every input path.**
   - States: loading, empty, error (with a way to recover), success,
     disabled, and hover, focus, focus-visible, active.
   - Keyboard: every interactive element reachable and operable, tab
     order matches the visual order, Escape closes overlays, focus is
     trapped in a modal and returns to its trigger.
   - Semantics: a button is a `<button>`, a link an `<a>`, headings in
     order, every input has a label (a placeholder is not a label).
   - Contrast: WCAG 2.2 AA, 4.5:1 for body text, 3:1 for large text and
     UI parts. A token that passes as an icon (3:1) can fail as a small
     text label (4.5:1): check which one this use is.
   - Motion respects `prefers-reduced-motion`.
7. [JUDGEMENT] **Performance as a reflex.** Lazy load heavy children
   (modals, charts, editors); memoize only where the cost is measured;
   mutate through the project's state layer, never from the component
   into the database. Suspect a slowdown: profile it, do not guess.
8. [SCRIPT-CHECKED] **Test it, and watch the test fail once.** Every
   bug fix gets a test that reproduces the bug. Run it against the old
   code and see it fail, then fix, then see it pass. A new component
   gets a test for its main behaviour and one state, run the same way
   against a deliberately broken version. The project's test runner
   answers this step.
9. [JUDGEMENT] **Look at it.** Run the project's dev server and view
   the component at 375, 768 and 1280 px, in both colour modes if the
   project has them; tab through it; trigger every state from step 6
   with the browser console open. An error in the console during a
   flow that looks successful is a bug. If the component shows saved
   state (a bookmark, a like, a read marker), create the state, reload
   the page cold and check it shows before any click. A compiler that
   is happy is necessary, not sufficient.
10. [JUDGEMENT] **Hand off for review.** A note in the WiP folder that
   asked ([[SOP-1006-start-work-and-archive-a-wip-folder|SOP-1006]])
   names what was built, the commit, which tokens it uses or proposes,
   the test from step 8, and what was not checked. Larry routes it to
   Vera's quality gate when her pack is installed; otherwise the user
   checks it against the list below. Findings are fixed and the
   component goes back for review. The gate is not argued.

## Definition of done

- Lives in the right layer (global, shared, app-specific).
- Semantic tokens only; no hardcoded colour, size, spacing, motion or
  single-source constant.
- Fully typed; the project's type check and linter pass.
- Every state from step 6 handled and visible; saved state survives a
  cold reload.
- Keyboard operable with visible focus; contrast clears WCAG 2.2 AA.
- Correct at mobile, tablet and desktop widths, and in both colour
  modes where the project has them; no console errors.
- A test covers it and was seen to fail once.
- Reviewed and signed off. Until then it is "in progress", not done.

A durable lesson from the build goes into Felix's `Journal/`; the
session itself is logged by Larry at close.
