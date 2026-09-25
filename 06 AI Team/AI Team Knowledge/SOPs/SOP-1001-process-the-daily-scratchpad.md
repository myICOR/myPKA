---
type: sop
id: SOP-1001
title: Process the Daily Scratchpad
created: 2026-08-27
owner: penn
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1003-journal-entry-anatomy]]", "[[GL-1005-code-vs-instructions]]", "[[GL-1007-capture-and-where-things-go]]"]
---

# SOP-1001 Process the Daily Scratchpad

You can do all of this yourself, without the AI; the moves are in
[[GL-1007-capture-and-where-things-go|GL-1007]] "Doing it by hand", and
each script step below names its by-hand twin.

Runs when the user says "process my scratchpad" (or via [[WS-1001-daily-processing-run|WS-1001]]). Never
runs silently.

1. [SCRIPT] Locate today's note: `concept:scratchpad/YYYY/MM/YYYY-MM-DD.md`. If
   the user names another day, use that date. By hand: open it from the
   file explorer.
2. [JUDGEMENT] Read the whole note. For each section or bullet decide
   what it IS: journal-worthy reflection, meeting notes, a quote, a
   project update, a contact fact, a task, or noise to leave alone.
3. [JUDGEMENT] Confirm the plan with the user in one short list
   ("2 journal entries, 1 project update, ok?") unless the user asked
   for autopilot.
4. [SCRIPT] For each journal-worthy piece run the content source's
   `new-journal-entry` tool (get its path with
   `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool new-journal-entry`,
   [[GL-1013-sources-and-the-resolver|GL-1013]], then run that path)
   with the user's EXACT words as `--original`. The script owns path, name, and skeleton. By hand:
   right-click the month folder, New note, `YYYY-MM-DD_<slug>`, insert
   the `journal` template, your words under `## Original Text`.
5. [JUDGEMENT] Write the Expansion section and fill the linked_* fields
   in each created entry ([[GL-1003-journal-entry-anatomy|GL-1003]]).
6. [JUDGEMENT] Apply other extractions: update the Topic, Project, or
   Contact notes concerned ([[SOP-1004-create-or-update-a-my-life-entity|SOP-1004]], [[SOP-1005-create-or-update-a-contact|SOP-1005]]); create tasks via
   `Scripts/new-task.py` for detected action items. By hand: an action
   item goes into your own task tool; the Planner syncs it.
7. [SCRIPT] Stamp the scratchpad: get the path of the content
   source's `stamp-processed` tool with
   `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool stamp-processed` ([[GL-1013-sources-and-the-resolver|GL-1013]]),
   then run that path with `<note> --summary "..." --into "[[...]]"`,
   one --into per created or updated note. NO --archive:
   scratchpads stay in place forever. By hand: tick `processed`, fill
   `processed_summary` and `processed_into` in the Properties panel
   ([[GL-1002-frontmatter-conventions|GL-1002]] "The processed stamp").
8. [SCRIPT] Link the dates in the notes THIS run created or updated, and
   in nothing else: get the path of the `link-dates-to-daily-notes` tool
   with `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool link-dates-to-daily-notes`,
   then run that path with `--fix --path <note>` and one
   `--path` per note from steps 4 to 6
   ([[GL-1011-date-mentions-link-to-daily-notes|GL-1011]]). `--path` is
   not optional here. Without it the linker walks the whole vault, so
   processing one scratchpad rewrites date mentions across every note in
   the Inner World, the WiP room and the Inbox as a side effect. The
   scratchpad itself is not in the list: GL-1011 keeps
   `concept:scratchpad` out of scope on purpose, because a daily note
   does not link to itself.
9. Report to the user what was created, with links.

The scratchpad body is never edited. If a piece is ambiguous, ask; do
not guess it into the Inner World.
