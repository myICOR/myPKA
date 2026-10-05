---
type: sop
id: SOP-2021
title: Run the quality gate on visual or UI work
created: 2026-09-26
owner: vera
uses: ["[[GL-1005-code-vs-instructions]]", "[[SOP-1006-start-work-and-archive-a-wip-folder]]"]
skill_name: vera-quality-gate
skill_summary: "Check a visual deliverable, a web UI or a UI code change before it ships, and return evidenced findings and a verdict."
skill_triggers:
  - "check this before I send it"
  - "is this ready to ship"
  - "run the quality gate"
  - "audit accessibility"
  - "QA this"
---

# SOP-2021 Run the quality gate on visual or UI work

Vera's gate for any visual deliverable, web UI or UI code change before
it ships. Shipped by the Vera expansion pack; the pack number range is
explained in the pack's README.

Runs when a maker (Charta, Pixel, Felix, or the user) finishes visual
or UI work and Larry calls the gate, and when the user says "check this
before I send it", "is this ready to ship", "audit accessibility",
"responsive check", "this feels off but I cannot say why".

The phases run in order; accessibility problems hide behind visual
ones, and visual ones hide behind layout ones.

1. [JUDGEMENT] **Prepare.**
   - Open the user's design-system guideline, every time. None yet:
     that is the first finding, and Iris is its fix.
   - Read what the deliverable was supposed to do and who receives it:
     only the user, or another person (a client, a doctor, an office,
     family)? Screen, print or video? The recipient sets the bar.
   - Open the deliverable itself: the file, the running page, the
     preview, or for a code change the branch or commit (write its id
     into the report; the gate is about exactly that version).
2. [JUDGEMENT] **Check the instruments.** For every script, test,
   scanner or search this gate will rely on that you have not yet seen
   fail: plant one known defect in a scratch copy and watch it report
   it. Say for each what question it answers, and whether that is the
   question you have. Note how many items it looked at out of how many
   exist; a clean result over a fraction is a finding about the check.
3. [SCRIPT-CHECKED] **Capture evidence.** Render or screenshot the
   deliverable in its main state, every state it has (loading, empty,
   error, hover, focus, disabled), at 375, 768 and 1280 px for UI, and
   in both colour modes where they exist. Use a headless browser when
   one is available and measure the real viewport width first (browser
   automation can be pinned to one size); a width you could not render
   is listed as not covered. Otherwise ask the user for screenshots.
   For a video, check a low-resolution proof for layout and timing
   first, then the final master. Save the captures beside the report.
   No evidence, no gate.
4. [SCRIPT-CHECKED] **Code changes: reproduce, then run it live.** For
   a UI code change, check it out into a scratch copy and run the
   project's own type check, linter, tests and build there. Only for a
   change written by the user or by their own agents. A change from
   anyone else, or one that adds or bumps a dependency no one has
   reviewed, goes through Vex's gate first when his pack is installed
   (otherwise the user decides), because type checks, tests and builds
   run the change's code; until that review is done, it runs only
   inside a sandbox the user approved (a throwaway VM, container or
   cloud sandbox). Run with no production credentials in the
   environment. Then run
   the changed flow in the browser with the console captured, against
   the test environment the user names:
   - an error in the console during a flow that looks fine is a
     finding;
   - saved state (a bookmark, a like, a setting) is created, the page
     reloaded cold, and the state must show before any click;
   - where the flow writes data, count the rows before and after each
     action, so the toast on screen is backed by evidence;
   - a claim in the maker's report ("same as the existing feature") is
     checked against the whole shape it rests on, not the part the
     maker queried.
5. [JUDGEMENT] **Visual check against the design system.** For each
   capture:
   - Every colour, type role, spacing step and radius resolves to a
     token in the guideline. An off-system value is a finding; a value
     the guideline lists as banned is CRITICAL.
   - Imagery matches the guideline's imagery direction.
   - Hierarchy reads right: the primary action is the most prominent,
     destructive actions are marked, headings step down in order.
   - Alignment and rhythm hold; icons come from one set.
   - Empty, error and loading states exist, are on-system, and offer a
     way forward.
   - Words inside the visual follow the guideline's voice rules (the
     content itself is the user's, not Vera's to judge).
   - Where computed styles and the rendered pixels disagree, zoom the
     screenshot; the pixels are the evidence.
6. [JUDGEMENT] **Layout at every width** (UI and screen deliverables).
   No unintended horizontal scroll; tap targets at least 24 by 24 CSS
   px (WCAG 2.2 AA, 2.5.8), 44 by 44 recommended on touch; text never
   shrinks below the guideline's minimum or overflows its box; boxes
   do not overlap each other; columns collapse in reading order; media
   keeps its aspect ratio.
7. [SCRIPT-CHECKED] **Accessibility, WCAG 2.2 AA.** Contrast is
   measured on the rendered colours, not read off the token sheet:
   4.5:1 for body text, 3:1 for large text (18 pt, or 14 pt bold) and
   UI parts. Ask for every accent colour "icon or text here?": a colour
   that passes as an icon (3:1) fails as a small label (4.5:1). For UI
   also: visible focus on everything focusable, full keyboard operation
   in visual order, Escape closes overlays, focus trapped in modals,
   semantic elements, a label on every input, correct ARIA,
   `prefers-reduced-motion` honoured, meaningful images described and
   decorative ones marked `alt=""`. For any visual: no meaning carried
   by colour alone (it must survive a colour-blindness simulation).
8. [JUDGEMENT] **Print, when printed.** Bleed margin present; export at
   300 dpi (600 for fine type); colour space right for the printer (RGB
   for digital print, CMYK for offset); page count fits the binding.
9. [JUDGEMENT] **Recipient fitness**, when someone else receives it:
   understandable without inside context, in the recipient's language,
   no assumption about what they already know.
10. [JUDGEMENT] **Write the report** beside the deliverable, in the WiP
    folder that asked
    ([[SOP-1006-start-work-and-archive-a-wip-folder|SOP-1006]]), named
    `YYYY-MM-DD-<deliverable-slug>-qa-report.md`. Verdict first (one
    verdict per step when the work is a pipeline of several steps, each
    with its owner), then the count per severity, then each finding in
    this shape:

    ```
    ### [SEVERITY] <short title>
    Where: <file, page, width, state, commit>
    Evidence: <the capture, the measurement and where it was taken>
    Rule: <design-system section, or WCAG 2.2 criterion>
    Fix: <specific, copy-pastable where it can be>
    Verify: <the check that will confirm the fix>
    ```

    Close with "What passed", so the maker knows what works, and "Not
    covered", listing what this gate did not check, so silence is never
    read as a pass.
11. [JUDGEMENT] **Deliver the verdict** (APPROVED, CONDITIONAL, BLOCKED;
    the rules are in Vera's contract). A CRITICAL finding is said in the
    first line, never left at the bottom. CONDITIONAL quotes the user's
    acceptance.
12. [JUDGEMENT] **Re-verify after fixes.** Run the same check that
    produced each finding against the new version, and add the check
    the first round could not run (a cold reload, a width that was not
    reachable). Label every measurement with the version it was taken
    on. Before calling a defect new, check whether the previous version
    had it too; that changes who fixes it. The gate closes only on
    Vera's own re-check.

## Severity

- **CRITICAL**: blocks use or breaks the system. Primary text fails
  contrast, keyboard use is broken, a screen reader cannot reach core
  content, a banned value is back, the recipient cannot read it, a
  saved action silently does not save.
- **HIGH**: clear drift from the design system, a broken layout at a
  main width, missing focus indicators, print file at screen
  resolution, stale state after a cold reload, an error in the console
  on the main flow.
- **MEDIUM**: minor drift, a missing hover state, weak but working
  accessibility, uneven spacing rhythm.
- **LOW**: polish and follow-up ideas.

Inflating a severity to look thorough destroys trust in the gate as
surely as missing one.

A recurring pattern goes into Vera's `Journal/`; the session itself is
logged by Larry at close.
