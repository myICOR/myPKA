---
# Identity
id: tsk-2026-05-10-001
title: "Welcome — read this and then close me"

# Ownership & priority
assignee: larry
priority: 4

# Status
status: open
blocked_reason: null
blocked_by: null

# Time
created: 2026-05-10T12:00:00Z
updated: 2026-05-10T12:00:00Z
due: null

# Provenance
created_by: scaffold
source: scaffold-seed
parent: null

# Cross-references — three populated to show the pattern
linked_sops: [SOP-create-task, SOP-claim-task, SOP-close-task, SOP-rebuild-task-index]
linked_workstreams: []
linked_guidelines: [GL-001-file-naming-conventions, GL-004-task-resource-linking]
linked_my_life: []
linked_session_logs: []
linked_journal_entries: []
linked_deliverables: []

# Tagging
tags: [scaffold, onboarding]
---

# Welcome — read this and then close me

## What this is
This is a seed task included with the scaffold so you can see what a real task file looks like in this folder. It's intentionally trivial — you read it, you close it. The point is to show the shape: frontmatter with required cross-reference arrays, body with "Context one click away," updates, outcome.

## Context one click away
- Procedure for creating tasks: [[SOP-create-task]]
- Procedure for claiming this: [[SOP-claim-task]]
- Procedure for closing this: [[SOP-close-task]]
- Procedure for keeping the index fresh: [[SOP-rebuild-task-index]]
- Naming standards: [[GL-001-file-naming-conventions]]
- Linking rule: [[GL-004-task-resource-linking]]

## Success criteria
- You read this file and understand the resumption-point principle: a task is a place to pick up from, with all relevant context one wikilink away.
- You read [[SOP-create-task]] and [[SOP-close-task]] to see the lifecycle.
- You close this task via [[SOP-close-task]] (which moves it to `done/2026/05/` and writes an outcome).

## Notes for newcomers
- Task ids follow `tsk-YYYY-MM-DD-NNN`. NNN is a per-day counter.
- Filename is `<id>-<kebab-slug>.md`. The id is canonical; the slug is human-helpful.
- Cross-reference any task with a basename wikilink: `[[tsk-2026-05-09-001-mux-webhook-401]]`. Never include the path — folders change as tasks move.
- The seven `linked_*` arrays in frontmatter are required. Empty arrays are valid. The discipline of confronting "is there a relevant SOP / workstream / guideline / my-life-entry / session-log / journal-entry / deliverable?" at creation is the whole design. See [[GL-004-task-resource-linking]] for the one-way Task → Resource rule.
- The `INDEX.md` in this folder is auto-generated. Don't edit it by hand.

## Updates
- 2026-05-10 12:00 (scaffold) — created as scaffold seed task

## Outcome
_(filled when you close this — see [[SOP-close-task]])_
