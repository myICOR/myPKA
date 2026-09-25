---
type: sop
id: SOP-1002
title: Process an Inbox capture
created: 2026-08-27
owner: penn
uses: ["[[GL-1001-the-six-rooms]]", "[[GL-1002-frontmatter-conventions]]", "[[GL-1003-journal-entry-anatomy]]", "[[GL-1007-capture-and-where-things-go]]"]
---

# SOP-1002 Process an Inbox capture

You can do all of this yourself, without the AI; the moves are in
[[GL-1007-capture-and-where-things-go|GL-1007]] "Doing it by hand", and
each script step below names its by-hand twin.

Runs when the user says "process my inbox" (or via [[WS-1001-daily-processing-run|WS-1001]]). Covers web
clips, scans, audio memos, and manual drops in `concept:inbox`,
`concept:inbox/outer_world`, and `concept:inbox/scanner` (the scanner's
watch folder; scanned files are binaries and follow step 3).

Two shapes of capture, two routes, never both on one item:

- a MARKDOWN capture is its own note: it carries the stamp and moves to
  `Outer World/archive/` (steps 4 to 6);
- a BINARY capture (scan, photo, audio memo, PDF) cannot carry
  frontmatter: its wrapper note carries the stamp and the move to
  the Assets (`concept:assets`) IS its archive (step 3; [[GL-1002-frontmatter-conventions|GL-1002]],
  ruling 2026-09-04). A binary is never copied into `Outer World/archive/`.

1. [SCRIPT] List every file in the active Inbox (excluding
   `Outer World/archive/`). By hand: look at the folder.
2. [JUDGEMENT] Per item, identify what it is: a clip with the user's
   thought, a document, an audio memo, a loose file. The user's thought
   is read from the `my_thought` property when the clip came through
   the Web Clipper template (`Templates/web-clipper-outer-world.json`),
   else from the body; an empty `my_thought` and no line of the user's
   own in the body is a capture without a thought (step 5).
3. Binary files: [SCRIPT] copy to the matching Assets slot
   via `Scripts/import-file.py <binary> --dest "concept:assets/<slot>/<name>"`.
   By hand: drag the file into that slot's folder (a move, so
   nothing stays in the Inbox). Then [JUDGEMENT] create the wrapper note that explains it: a
   `type: document` note in `concept:notes` whose
   `source_file` wikilinks the shelf copy (`doc_type: other` for a photo
   or an audio memo), and connect it to the right Topic, Key Element,
   Project or Contact. Then [SCRIPT] stamp the wrapper note and finish
   the move with the content source's `stamp-processed` tool (path:
   `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool stamp-processed`, [[GL-1013-sources-and-the-resolver|GL-1013]]):
   run that path with `<wrapper-note> --summary "..."
   --into "[[...]]" --capture "concept:inbox/<...>/<binary>"`. The script
   compares the shelf copy with the inbox original by sha256 and removes
   the original only on a match; a mismatch removes nothing. By hand:
   stamp the wrapper note in its Properties panel; the file already
   moved in the first move of this step. The binary
   is done at this point and does not reach step 6.
4. Captures with a thought from the user: [SCRIPT] create the journal
   entry with the content source's `new-journal-entry` tool (get its
   path with `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool new-journal-entry`,
   then run that path; the thought is the
   `--original`; by hand: right-click the month folder, New note,
   insert the `journal` template, the thought under `## Original
   Text`), then [JUDGEMENT] connect it to the right Topic, Key
   Element, or Project, updating those notes.
5. Captures without a thought: no journal entry is invented for the
   user. [JUDGEMENT] Decide which Topic, Key Element or Project the
   reference serves. If it serves one, create a `type: note`,
   `note_type: reference` note in `concept:notes` carrying
   `source_url` (from the capture), `consumed: false`, and the wikilink
   in `topics`, `key_elements` or `projects`; the clip's text stays in
   the archived capture, the note holds the reference and the link, and
   the entity note shows it through `Notes.base`. If it serves none, it
   failed the Capturing Beast ([[GL-1007-capture-and-where-things-go|GL-1007]]):
   archive it in step 6 without a note. Either way the clip is archived.
6. [SCRIPT] Stamp and archive each processed MARKDOWN capture (steps 4
   and 5): run the `stamp-processed` tool (path:
   `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool stamp-processed`) with `<capture> --summary "..."
   --into "[[...]]" --archive`. The original moves verbatim to
   `concept:inbox/outer_world_archive`. By hand: tick `processed`, fill
   `processed_summary` and `processed_into` in the Properties panel
   ([[GL-1002-frontmatter-conventions|GL-1002]] "The processed stamp"),
   then drag the capture into `Outer World/archive/`. Binaries were stamped and moved in
   step 3; the script refuses `--archive` and `--capture` together.
7. Report. The active Inbox must be empty at the end; if an item could
   not be processed, say so and leave it visible, never hide it.
