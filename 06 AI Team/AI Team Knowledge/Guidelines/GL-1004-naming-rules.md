---
type: guideline
id: GL-1004
title: Naming rules
created: 2026-08-27
---

# GL-1004 Naming rules

Names in this scaffold use generic words anyone understands without a
lesson. Checkable rules are enforced by the content source's
`validate-scaffold` tool (the content rooms; path:
`python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool validate-scaffold`) and the team's
`Scripts/validate-team.py` (the team folders: session logs, tasks, agent
folders).

## Folder names

1. **Never an ICOR stage name**: no Input, Control, Output, Refine as a
   folder name, at any level. The folder tree and the methodology are
   two parallel narratives; mixing them confuses both.
2. The top-level rooms are fixed and number-prefixed for sort
   order. Their folder names in an ICOR for Life folder are the mode A
   default homes in [[GL-1013-sources-and-the-resolver|GL-1013]] §2.1; the team
   addresses them as concepts, never by folder name. Users may add
   rooms; agents may not.
3. Date-nested shapes are `YYYY/MM/` (the Daily Scratchpad, Journal,
   Session Logs, Tasks/done, Tasks/cancelled).
4. **Who creates a folder.** The rooms and their fixed subfolders are
   the Scaffold's; they arrive with the download and are never renamed.
   Date folders (`YYYY/MM/`) under the Daily Scratchpad, Journal,
   Session Logs, the task
   archives, and the Assets' `images` slot when you nest it, may be created by
   hand (right-click the parent, New folder, `2026`, then `09`) or by
   the scripts. Anything else asks the AI first, so the folder lands in
   the right room with the right name.

## File names

| Kind | Pattern | Example |
| --- | --- | --- |
| Daily note | `YYYY/MM/YYYY-MM-DD.md` | `2026/08/2026-08-27.md` |
| Quick capture | `YYYY/MM/YYYYMMDDHHmm.md` | `2026/08/202608271432.md` |
| Journal entry | `YYYY-MM-DD_<slug>.md` | `2026-08-27_best-business-partner.md` |
| WiP work, one file | `<bucket>/YYYY-MM-DD-<slug>.md` | `Operations/2026-08-27-pivot-video.md` |
| WiP work, two files or more | `<bucket>/YYYY-MM-DD-<slug>/` | `Operations/2026-08-27-pivot-video/` |
| Task | `YYYY-MM-DD-<slug>.md` | `2026-08-27-seed-example-notes.md` |
| Session log | `YYYY-MM-DD-HH-MM_<agent>_<slug>.md` | `2026-08-27-21-30_larry_scaffold-build.md` |
| SOP / WS / GL, yours | `SOP-NNN-<slug>.md` etc., `001` to `999` | `SOP-001-weekly-invoice-run.md` |
| SOP / WS / GL, shipped by the scaffold | `SOP-1NNN-<slug>.md` etc., `1001` to `1999` | `SOP-1001-process-the-daily-scratchpad.md` |
| SOP / WS / GL, shipped by an Expansion pack | `EP-SOP-2NNN-<slug>.md` etc., `2001` to `2999`, frontmatter `id: SOP-2NNN` | `EP-SOP-2011-build-a-ui-component.md` |
| Script | `<verb>-<slug>.py` | `stamp-processed.py` |
| Agent bio | `<Name>.md` inside `Agents/<Name>/` | `Penn.md` |
| Agent avatar | `AI Team Knowledge/Avatars/<name>.png`; a pack ships it as `Agents/<Name>/<name>.png` | `penn.png` |

**Two number ranges, one rule.** The knowledge docs the scaffold ships
carry numbers from `1001` up; the ones you write carry `001` to `999`. The
ranges never meet, so a scaffold update can never land a `GL-001` on top of
the `GL-001` you wrote last year. Nobody writes a thousand of their own,
which is why the boundary sits there. When you hire a specialist or write a
procedure, take the next free number below `1000`; never number your own
work in the `1NNN` range, because the next scaffold version may ship a doc
with that number. Expansion packs take a third range, `2001` to `2999`,
behind the `EP-` prefix the installer requires ([[GL-1012-ai-team-expansions|GL-1012]]),
so a pack never lands on a scaffold number or on yours.
| Base (live table) | `<Collection>.base` inside the folder it views | `People.base` |
| Entity note | natural title | `Alex Rivera.md`, `Run a marathon.md` |

Slugs: lowercase, hyphenated, 3-6 content-bearing words, no articles.

## Reference linking

Whenever a note body mentions an SOP, Workstream, or Guideline, the
mention is a WIKILINK, never bare text or backticked code:
`[[SOP-1004-create-or-update-a-my-life-entity|SOP-1004]]`. The alias
keeps prose readable; the link makes the reference clickable and
backlinked, so every knowledge doc shows where it is used. The same
holds for frontmatter `uses:` lists (full quoted wikilinks). Code
blocks and this guideline's naming-example tables stay literal.

## Quick captures and folder creation (ruling 2026-08-28, amended 2026-09-10)

**The Daily Scratchpad is date-nested, exactly like the Journal.** Everything
lands in `concept:scratchpad/YYYY/MM/`; nothing stays loose at the room root.
A room whose files pile up flat stops being a room and becomes a drawer, and
the first thing anyone does with a drawer is stop opening it.

Three legal shapes, all inside `YYYY/MM/`:

| What | Name | Written by |
| --- | --- | --- |
| Daily note | `YYYY-MM-DD.md` | Obsidian's Daily notes core plugin |
| Quick capture | `YYYYMMDDHHmm.md`, optionally ` - Title` added later by you, ` 1` or ` 2` on a same-minute collision | ICOR for Life - Scratchpad (` 2`), or Obsidian's Unique note setting behind Cmd+Alt+N (Ctrl+Alt+N on Windows) and the myICOR Connect new-note button (` 1`); the check accepts both |
| Canvas | `YYYY-MM-DD_canvas.canvas`, plus whatever you title or number it | the toolbar |

**The name is the minute, not the subject.** A quick capture is stamped
`YYYYMMDDHHmm` because at capture time you do not yet know what the thing is,
and being asked for a title is the friction the room exists to remove
([[GL-1007-capture-and-where-things-go|GL-1007]]). You may append ` - Title`
afterwards once you do know; the timestamp stays at the front so the folder
sorts chronologically.

**A title-named note does not live here.** `Omarchy.md` or `Vo UU.md` sitting
in the Scratchpad is a note that has a subject and therefore has a home in
the Notes (`concept:notes`), or an entity that belongs in My Life
(`key_elements`, `goals`, `projects`, `habits`, `topics`) or Contacts
(`people`, `companies`). Obsidian creates these by accident every time you click a
`[[wikilink]]` that has no note behind it, because the new-file location points
at this room. Process them out; do not file them here.

**Three settings must agree with this page**, and they are the reason the rule
reads the way it does rather than the other way round:

- `.obsidian/daily-notes.json`: `folder:` the home of `concept:scratchpad` (mode A default in [[GL-1013-sources-and-the-resolver|GL-1013]] §2.1), `format: YYYY/MM/YYYY-MM-DD`
- `.obsidian/plugins/icor-for-life-scratchpad/data.json`: `subfolderFormat: YYYY/MM`, `newNoteFormat: YYYYMMDDHHmm`
- `.obsidian/zk-prefixer.json` (the Unique note setting): `folder:` the home of `concept:scratchpad`, `format: YYYY/MM/YYYYMMDDHHmm`

The `validate-scaffold` tool enforces the shapes AND the nesting, walking the
whole room rather than its root. It walked only the root until 2026-09-10,
which meant that the moment a vault nested its scratchpads correctly the check
matched zero files and went green by finding nothing. A guard whose green is
reachable without the thing being true is worse than no guard.

- Folders: rule 4 under Folder names above. A new month under the Scratchpad or
  the Journal is yours to make; a new kind of folder is a question to the AI.
