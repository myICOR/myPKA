---
type: sop
id: SOP-1003
title: Create a journal entry
created: 2026-08-27
owner: penn
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1003-journal-entry-anatomy]]"]
---

# SOP-1003 Create a journal entry

Runs when the user asks for a journal entry, or as a step inside [[SOP-1001-process-the-daily-scratchpad|SOP-1001]]
and [[SOP-1002-process-an-inbox-capture|SOP-1002]].

1. [JUDGEMENT] Identify the user's exact words that ARE the entry. If
   the user gave none (e.g. a bare screenshot), ask for one sentence;
   never author the Original Text for them. Pick the entry's type, one
   of the four in [[GL-1003-journal-entry-anatomy|GL-1003]]
   (interaction/note/thought/milestone) - never a fifth.
2. [SCRIPT] Get the path of the content source's `new-journal-entry`
   tool with `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool new-journal-entry`
   ([[GL-1013-sources-and-the-resolver|GL-1013]]), then run that path
   with `--date ... --slug ... --journal-type ... --original "<exact words>"`. Add `--format`
   (voice/photo/meeting-notes/other) only when the entry arrived as
   something other than plain text. The script owns the YYYY/MM path,
   the filename, the frontmatter skeleton, and writes the Original Text
   section verbatim.
3. [JUDGEMENT] Write the Expansion: context from linked entities, what
   the team knows around it. In the user's language, warm, no invention
   presented as fact.
4. [JUDGEMENT] Fill linked_people, linked_topics, linked_projects with
   wikilinks, and set `key_element` when the entry's subject is a Key
   Element ([[GL-1003-journal-entry-anatomy|GL-1003]] §Type and
   Subject); create missing entities via [[SOP-1004-create-or-update-a-my-life-entity|SOP-1004]] or [[SOP-1005-create-or-update-a-contact|SOP-1005]] first if
   the user confirms they matter.
5. If the entry came from a scratchpad or capture, the calling SOP
   stamps the source. If created directly, nothing else changes.
