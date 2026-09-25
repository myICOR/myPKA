---
agent_id: pax
type: journal-entry
created: 2026-09-14T00:00:00Z
updated: 2026-09-14T00:00:00Z
topic: journal-opened
tags: []
linked_session_logs: []
related_journal_entries: []
status: durable
---

# The Journal folder was created with the 2026-09-14 harness upgrade

## Context
This folder was created on 2026-09-14, when the harness layer was rebuilt and
`Scripts/check-hire.py` check 06 reported that none of the shipped specialists
had a Journal at all. Version control drops an empty folder, so an empty
Journal never survives a clone, and a specialist with no journal reads as a
specialist who has learned nothing.

## What I learned
Nothing yet. This entry holds the folder open. The next entry is the first
real one: written by Pax after doing the work, in the shape of
`_template.md` beside this file.

## When this applies
Never. It is a placeholder, and it should be the shortest-lived file here.

## When this does NOT apply
Everywhere else.
