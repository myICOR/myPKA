---
type: sop
id: SOP-1006
title: Start, work, and archive a WiP folder
created: 2026-08-27
owner: larry
uses: ["[[GL-1001-the-six-rooms]]", "[[GL-1002-frontmatter-conventions]]", "[[GL-1004-naming-rules]]"]
---

# SOP-1006 Start, work, and archive a WiP folder

1. On "let's work on X", two decisions, in this order.
   [JUDGEMENT] **The bucket.** Read the list in `concept:wip/README.md` from
   the top and stop at the first line that fits: `Workstreams/<Name>/`,
   then `AI Team/`, then `Projects/<Project note name>/`, then
   `Operations/`. First match wins. Bounded work that no Project note
   names belongs in `Operations/` and does not need a Project note opened
   for it.
   [SCRIPT-CHECKED] **The shape**, inside that bucket, dated
   ([[GL-1004-naming-rules|GL-1004]] naming): one file
   `YYYY-MM-DD-<slug>.md`, or a folder `YYYY-MM-DD-<slug>/` when the work
   is two files or more. Everything the work produces lives with it. A
   single file that grows a second file becomes a folder of the same
   name, with the file moved in as its `README.md` and the links
   repointed.
2. Larry routes the work to the owning agent(s) per the agent index;
   drafts and iterations stay with it.
3. [JUDGEMENT] Work that runs past one session, or past one step, gets a
   progress report in its folder (below). The team creates it unasked.
4. On "done / ship it":
   [JUDGEMENT] decide what the results ARE: knowledge (migrate into the
   Inner World via [[SOP-1003-create-a-journal-entry|SOP-1003]]/004/005), an external deliverable (hand it
   over and note where it went), or scrap.
   [SCRIPT-CHECKED] move the whole working folder, or the single file, to
   `concept:wip/archive/<the same bucket>/`. The archive mirrors the buckets,
   so the path is kept and nothing is renamed.
5. Work in the WiP room untouched for 30 days is raised in the weekly review
   ([[WS-1002-weekly-review|WS-1002]]), never archived silently. The
   buckets themselves are never raised, only the dated work inside them,
   and `Operations/` is read first: it is the bucket nothing closes from
   the outside.

## The progress report

One `progress-report.md` per piece of work, written and maintained by the
team so the user can open the work on any device and see where it
stands. It is a status VIEW, not a report to read: a diagram first,
then short lines. Never a paragraph.

1. [SCRIPT] Create it:
   `Scripts/new-progress-report.py --wip <bucket>/<folder> --title "..."
   --phase "..." --phase "..." [--plan "[[the-plan-note]]"]`.
   Location, frontmatter, mermaid skeleton and scoreboard rows are the
   script's; the phase names are yours.
2. [JUDGEMENT] The mermaid diagram is the primary view and stays
   accurate. State is written INTO the node label
   (`p1["1 Free tier - RUNNING"]`), never as a color, and the single
   `:::mark` accent sits on the phase running now and moves with the
   work (authoring rules in `06 AI Team/README.md`). Legend:
   DONE / RUNNING / QUEUED / BLOCKED.
3. [JUDGEMENT] The scoreboard table supports the diagram: one row per
   phase, what it delivers in a few words, the same state.
4. [JUDGEMENT] Append at every milestone under a newest-on-top
   `### YYYY-MM-DD HH:MM` heading. One fact per line, short sentences.
   What the user ruled goes under Decisions, one line per ruling.
   BLOCKED is never left silent; it is said in the next answer too.
5. [SCRIPT] Re-stamp the header after every append:
   `Scripts/new-progress-report.py --wip <folder> --touch`.
6. The report retires with its folder (step 4): set `status: closed`
   on the way to `_archive/`.
