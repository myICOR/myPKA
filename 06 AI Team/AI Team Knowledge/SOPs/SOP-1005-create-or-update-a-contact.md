---
type: sop
id: SOP-1005
title: Create or update a Contact
created: 2026-08-27
owner: penn
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1006-bases-and-live-views]]"]
---

# SOP-1005 Create or update a Contact

Covers `concept:people` and `concept:companies`. You can
create a contact yourself from the `person` or `company` template
([[GL-1007-capture-and-where-things-go|GL-1007]] "Doing it by hand");
this SOP is the same moves run by the team.

1. [SCRIPT-CHECKED] The content source's `find-entity` tool with
   `"<name>"` (its path: `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool find-entity`,
   [[GL-1013-sources-and-the-resolver|GL-1013]]) searches People
   and Companies (names AND aliases) before anything is created; a hit
   means update, not create. One person, one note. By hand: the quick
   switcher (Cmd+O, or Ctrl+O on Windows). Create with
   the `new-entity` tool (path: `resolve.py --tool new-entity`)
   `person "<Name>"`
   (or `company`), which owns the folder, the filename and the
   frontmatter skeleton from the template.
2. A contact note holds PROPERTIES, not stories: role, relation,
   companies, aliases, email, birthday ([[GL-1002-frontmatter-conventions|GL-1002]]). What the user writes
   about a person lives in the Journal and links back via linked_people.
3. Companies and people cross-reference through the `companies` and
   `people` frontmatter fields; a person can belong to several
   companies and vice versa.
4. When a journal entry, scratchpad, or capture mentions a new person
   who plainly matters, confirm with the user before creating the note.
5. [SCRIPT] People and Companies are browsed through `People.base` and
   `Companies.base`, live tables over the frontmatter above. Bases are
   stamped by the content source's `new-base` tool (path:
   `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool new-base`), never hand-authored
   ([[GL-1006-bases-and-live-views|GL-1006]]); a new column means
   updating [[GL-1002-frontmatter-conventions|GL-1002]] first.
