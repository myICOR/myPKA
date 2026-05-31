# Deliverables

Where the team puts work-in-progress and finished artifacts the user can review.

When a specialist produces something substantial - a research brief, a draft document, a hire workup, a multi-file plan - it lands here, not in PKM. Deliverables is the team's working surface: time-stamped, often dated by folder, often created and discarded across sessions.

## When to use it

- **Pax** delivers a research report -> `Deliverables/YYYY-MM-DD-<topic-slug>.md`
- **Nolan** delivers a hire workup -> `Deliverables/YYYY-MM-DD-<role-slug>-hire-research.md`
- A new specialist delivers a multi-file project -> `Deliverables/YYYY-MM-DD-<project-slug>/`
- **Larry** collects briefs from multiple specialists for a single initiative -> one folder per initiative, named by date and slug

## When NOT to use it

- Personal life facts (people, projects, goals, habits) -> `PKM/`
- Daily journal entries -> `PKM/Journal/`
- Reference material the team needs forever (SOPs, Workstreams, Guidelines) -> `Team Knowledge/`

Naming convention: see `Team Knowledge/Guidelines/GL-001-file-naming-conventions.md`.

## Lifecycle: active and archived

A deliverable lives in active `Deliverables/` while its owning task is open or in-progress. When the owning task closes (done or cancelled), the deliverable moves to `Deliverables/_archive/<YYYY>/<MM>/<original-folder>/`. The closing task records the archive path in its `## Outcome` section.

This is the **archive-on-close cascade**, enforced by [[SOP-close-task]] and governed by [[GL-004-task-resource-linking]]. The link from task to deliverable is one-way (task -> deliverable, never the reverse) — see GL-004 for why. To find which task owned an archived deliverable, grep the closed task tree for the deliverable's slug, or query `mypka.db.wikilinks` if you maintain the SQLite mirror.

### Orphan deliverables

A deliverable created without a task wrapping it (e.g., a research brief dropped here directly as shared input) is **never owned** by a task and therefore **never archived** by a close. It sits in active `Deliverables/` indefinitely. This is correct behavior; the deliverable is shared input.

### Shared deliverables

A deliverable referenced by multiple tasks (in `linked_deliverables`) is **not archived** when the first of those tasks closes. The sharing check in [[SOP-close-task]] pre-flight catches this. The deliverable archives only when the last referencing task closes.
