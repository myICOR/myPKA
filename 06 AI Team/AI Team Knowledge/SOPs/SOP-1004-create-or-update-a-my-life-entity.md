---
type: sop
id: SOP-1004
title: Create or update a My Life entity
created: 2026-08-27
owner: penn
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1004-naming-rules]]"]
---

# SOP-1004 Create or update a My Life entity

Covers Goals, Key Elements, Topics, Projects, Habits. You can create
one yourself from the matching template
([[GL-1007-capture-and-where-things-go|GL-1007]] "Doing it by hand");
this SOP is the same moves run by the team.

1. [JUDGEMENT] Decide which of the five concepts the thing is. A pillar
   of life is a Key Element; a subject of interest is a Topic; a bounded
   endeavor with an end state is a Project; a direction with a target is
   a Goal; a recurring behavior is a Habit. When two fit, ask.
2. [SCRIPT-CHECKED] The content source's `find-entity` tool with
   `"<name>"` (its path: `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool find-entity`,
   [[GL-1013-sources-and-the-resolver|GL-1013]]) searches every
   entity folder, names and aliases, before anything is created; a hit
   means update, not create. One entity, one note, forever. By hand:
   the quick switcher (Cmd+O, or Ctrl+O on Windows).
3. [SCRIPT] Create with the `new-entity` tool (path: `resolve.py --tool
   new-entity`) `<type> "<Title>" --link "[[X]]"`: the script owns the folder, the natural-title
   filename, and the frontmatter skeleton from the type's template
   ([[GL-1002-frontmatter-conventions|GL-1002]]). By hand: right-click
   the folder, New note, insert the template. Then [JUDGEMENT] a short
   body describing what it is, wikilinks to related entities. Projects
   get their external PM links (ClickUp, Asana) in `external_links`;
   the scaffold never tracks their tasks.
4. **Goals** start with `status: not-achieved`. When the user reports
   a goal reached, flip it to `achieved` and offer a journal entry for
   the moment.
5. **Projects need a goal, always.** Before creating a project, ask
   which goal it serves and set the `goal` wikilink. No fitting goal:
   create the goal first (SOP-1004 on itself, one question). Set
   `start_date` at creation; set `end_date` and the final status when
   it closes. A project without a goal fails validation, by design:
   if the user cannot name the goal, that is a conversation, not a
   skipped field.
6. Update: edit frontmatter fields and append to the body; never rewrite
   the user's own sentences in place.
7. Cross-link both directions where the schema has fields for it
   (person <-> key element, goal <-> key element).
