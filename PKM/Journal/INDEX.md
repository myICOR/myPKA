# Journal - Index

The inbox of your myPKA. One markdown file per day. Penn (Journal Writer) writes here when the user shares thoughts, screenshots, photos, or voice notes.

## Structure

`PKM/Journal/YYYY/MM/YYYY-MM-DD-<slug>.md`

- One file per day.
- Filename: ISO date prefix plus a kebab-case slug for the day's main theme.
- If the day already has an entry, Penn appends a section to the existing file rather than creating a second one.

Auto-create rule: when Penn writes today's Journal entry and the `YYYY/` or `MM/` subfolder does not exist, Penn creates it.

## How entries are written

See [[WS-001-daily-journaling]] for the full Workstream. Short version:

- Penn writes the entry in plain markdown.
- People, organizations, topics, projects, and goals are linked via `[[wikilinks]]` to their canonical files.
- Images are embedded via `![[Images/YYYY/MM/...]]`. The image lives in `PKM/Images/`, the journal entry references it.

## Active files

- `2026/05/` — [[2026-05-04-first-day]] — seeded course sample. The entry referenced in the Dr. Schmidt SSOT demo.

Penn appends or adds entries here as you share journal input.

## Subfolders by year

- `2026/` (current year, with `05/` pre-created)

## SSOT inside the Journal

The Journal is the place where new information first arrives. Once a person, organization, or topic appears in the Journal, the canonical home for that fact is in `PKM/CRM/` or `PKM/My Life/`. The Journal entry links to the canonical file via `[[wikilinks]]`. Do not restate the person's role or the topic's definition inside the Journal entry.

See [[GL-001-file-naming-conventions]] for naming.
