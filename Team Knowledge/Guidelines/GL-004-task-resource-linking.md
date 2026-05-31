# GL-004 - Task-Resource Linking (One-Way)

> **This Guideline is a general rule every agent reads on every relevant action.** Every task created, claimed, blocked, unblocked, or closed reads this file. Every agent who writes a journal entry, session log, deliverable, SOP, Workstream, Guideline, or My Life note reads this file. SOPs and Workstreams `[[wikilink]]` here rather than restating the rule.

## The rule

**Tasks hold pointers to all resources needed to do the work. Resources never carry a back-pointer to a task. One-way: Task → Resource.**

Resources, for the purpose of this Guideline:

- **Deliverables** under `Deliverables/<YYYY-MM-DD-slug>/` (active) and `Deliverables/_archive/YYYY/MM/<original-folder>/` (archived).
- **Journal entries** under `PKM/Journal/YYYY/MM/` and `Team/<Name>/journal/`.
- **Session logs** under `Team Knowledge/session-logs/YYYY/MM/`.
- **SOPs** under `Team Knowledge/SOPs/`.
- **Workstreams** under `Team Knowledge/Workstreams/`.
- **Guidelines** under `Team Knowledge/Guidelines/`.
- **My Life entries** under `PKM/My Life/{Goals,Habits,Topics,Projects,Key Elements}/`.

## Why one-way

Tasks die — they close, get archived, get superseded. Resources persist as durable knowledge. A bidirectional link forces resources to track task state, which:

- creates write-amplification on every task status flip (every close, every claim, every block ripples to N resources),
- pollutes resource frontmatter with operational noise (an SOP shouldn't know which task last invoked it),
- breaks the resource's role as durable knowledge (an SOP / journal entry / deliverable should read identically across the lifetime of the tasks that touched it),
- and inverts the dependency direction (knowledge should not depend on workflow).

Task-side is the right place: a task is the operational artifact that needs to *find* its supporting context. Once the task closes, the resources remain untouched and reusable for the next task.

The pattern matches mature file-backed PKM tools (Obsidian, Logseq, Roam, Foam, Anytype) — all five derive backlinks by graph traversal rather than storing them in the target file. This scaffold sits in that camp by construction: markdown is canonical, any database-mirror layer is derived.

## The optional dependency on a SQLite mirror

The one-way rule works without a database, but it works *best* when a derived back-view layer exists. Standing in `Deliverables/` and asking "what task produced this?" is then a query rather than a frontmatter read:

```sql
SELECT task_id FROM task_resources WHERE resource_slug = ?
```

If the user has installed [[SOP-002-convert-mypka-to-sqlite]] and maintains a `mypka.db` mirror, the back-view query is deterministic and cheap. The mirror must be current before any close-task archive that depends on the sharing check (see "The archive-on-close rule" below).

If the user does NOT maintain a SQLite mirror, the back-view question is answered by `grep` across `tasks/open/` and `tasks/in-progress/` instead. Same answer, slower at scale. The one-way write rule itself is unaffected.

## The frontmatter contract

A task carries **seven** `linked_*` arrays in its YAML frontmatter:

```yaml
linked_sops: []                    # SOPs the task draws on
linked_workstreams: []             # Workstreams the task fits inside
linked_guidelines: []              # Guidelines that constrain the work
linked_my_life: []                 # PKM/My Life context (Topics, Goals, Projects, Habits, Key Elements)
linked_session_logs: []            # session(s) that birthed or touched the task
linked_journal_entries: []         # prior learning relevant to the assignee
linked_deliverables: []            # Deliverables that hold the working artifacts for this task
```

Empty arrays are valid. **The discipline is walking all seven slots when creating, claiming, blocking, unblocking, or closing the task** — not finding something to put in every slot. See [[SOP-create-task]] step 4 for the walk.

### What the resource side never carries

The following resource types **MUST NOT** carry a `linked_tasks` array, a `linked_task` field, or any other back-pointer to a task:

- Deliverables (cover memos, manifests, or any file under `Deliverables/`).
- Journal entries (PKM journals and per-specialist journals under `Team/<Name>/journal/`).
- Session logs.
- SOPs, Workstreams, Guidelines.
- My Life entries (Topics, Goals, Projects, Habits, Key Elements).

If you find a `linked_tasks` field on any of the above, it is a pre-GL-004 violation that should be removed via cleanup. Do not add new ones.

### What about session logs that touched a task?

If your scaffold predates GL-004, session logs may carry `linked_tasks` to mirror the tasks' `linked_session_logs`. **This is now retired.** Continuity is preserved by:

- The task's `linked_session_logs` array (one-way: task→session log).
- The session log's update line under `## Updates` (free-text wikilinks for human reading).
- A grep — `grep -rl "<task-id>" "Team Knowledge/session-logs/"` returns every session that touched the task.
- A SQL query against `mypka.db.wikilinks` returns the same set deterministically when the mirror is installed.

Both discovery paths exist; the frontmatter on the resource side does not need to mirror.

## Foreign-key format (storing the slug)

Each entry in a `linked_*` array is a **bare basename / folder-slug**, never a path, never wrapped in `[[wikilinks]]`. Consistent with [[GL-002-frontmatter-conventions]] §4.

### Slug format per resource type

| Field | Slug format | Source |
|---|---|---|
| `linked_sops` | `SOP-NNN-<slug>` or unnumbered procedural name (e.g. `SOP-create-task`) | The SOP's basename without `.md` |
| `linked_workstreams` | `WS-NNN-<slug>` | The Workstream's basename without `.md` |
| `linked_guidelines` | `GL-NNN-<slug>` | The Guideline's basename without `.md` |
| `linked_my_life` | `<slug>` | Bare slug (e.g. `ai-tooling`) |
| `linked_session_logs` | `YYYY-MM-DD-HH-MM_<agent>_<topic>` | The session-log's basename without `.md` |
| `linked_journal_entries` | `<slug>` (PKM) or `<slug>` (specialist journal) | Basename without `.md` |
| `linked_deliverables` | `<folder-slug>/<file-slug>` (for sub-files) **or** `<folder-slug>` (when the deliverable is a single-file deliverable or you mean the folder as a whole) | See examples below |

### `linked_deliverables` slug examples

- A single-file deliverable in `Deliverables/2026-05-12-research-brief.md` → `2026-05-12-research-brief`.
- A multi-file deliverable folder `Deliverables/2026-05-12-mcp-install/workup.md` → `2026-05-12-mcp-install/workup`.
- The manifest of a multi-file folder `Deliverables/2026-05-12-mcp-install/manifest.md` → `2026-05-12-mcp-install/manifest`.

The leading date prefix is retained in the slug. This matches the Deliverables README convention (folder named `YYYY-MM-DD-<slug>/`, file inside named `<slug>.md` or `manifest.md`).

When the deliverable is archived, **the slug does not change** — the file moves to `Deliverables/_archive/YYYY/MM/2026-05-12-mcp-install/workup.md` but the basename `workup` remains. Obsidian-style wikilinks resolve by basename. The frontmatter slug `2026-05-12-mcp-install/workup` still uniquely identifies the file inside the archived folder.

## Body mirror

The frontmatter `linked_*` arrays are for machine reading. The task body's `## Context one click away` section mirrors them as `[[wikilinks]]` for human reading. Both populated, kept in sync. Deliverable entries appear under their own bullet (or grouped under `Working artifacts:` when there are several):

```markdown
## Context one click away

- Procedure: [[SOP-create-task]]
- Guideline: [[GL-004-task-resource-linking]]
- Working artifacts:
  - [[workup]]
  - [[shim-amendments]]
  - [[user-checklist]]
- Birthed in: [[2026-05-12-23-15_nolan_shim-tool-allowlist-audit]]
```

## The archive-on-close rule

When a task moves to `done/` or `cancelled/`, every deliverable in `linked_deliverables` moves to `Deliverables/_archive/YYYY/MM/<original-folder>/`. The procedure is in [[SOP-close-task]] §A.8 and §B.5; the rationale lives here.

### Disclosure: this is a myPKA invariant, not borrowed prior art

No mature task system surveyed (Linear, Jira, Asana, ClickUp, Trello, GitHub Issues, Things 3, TaskWarrior, Notion) implements "deliverable archives when its task closes." They all archive the task itself; linked artifacts stay where they are. The closest analog is Tiago Forte's PARA — when a project closes, its *folder* moves to `Archive/` — but PARA operates at the project level, not the task level, and the moved artifacts are self-contained inside the project folder.

myPKA adopts this rule because two preconditions hold that the surveyed task systems don't have:

1. **Markdown is canonical and the user owns both ends of every edge.** Renames, moves, and archives are safe because the system controls both files.
2. **A SQLite mirror (if installed) is regenerable.** Any "what tasks referenced this archived deliverable?" question becomes a SQL query against the wikilinks table.

If you copy this Guideline to a scaffold that does not maintain a SQLite mirror, **the archive-on-close rule still works** — the sharing check just runs via `grep` instead of SQL. The cascade archive itself depends only on the one-way link direction, not on the database.

### The sharing escape hatch

A deliverable may be referenced by multiple tasks (e.g., a recurring hire-research brief reused by a later hire). Before archiving any deliverable on close, [[SOP-close-task]] §A.3 runs a mandatory sharing check:

```bash
for d in <linked_deliverables>; do
  grep -rl "$d" "Team Knowledge/tasks/open" "Team Knowledge/tasks/in-progress"
done
```

If another open or in-progress task references the same deliverable, the deliverable cannot be archived in this close. It stays in active `Deliverables/` until the last referencing task closes.

The query is cheap because the link direction is one-way: ask the tasks, never ask the resource. If pointers were bi-directional, this check would be ambiguous on which side to trust.

### Cancelled tasks archive their deliverables too

Cancellation is terminal abandonment, but the working artifacts are still historical record. Archive them, don't delete them. The user may later mine cancelled-task deliverables for what-we-almost-did context.

## Orphan deliverables (no owning task)

If a deliverable was created without a task wrapping it — e.g., the user drops a research brief directly into `Deliverables/` as shared input across multiple potential tasks — that deliverable is **never owned** by a task and therefore **never archived** by a close. It sits in active `Deliverables/` indefinitely.

This is correct behavior. The deliverable is shared input; archiving it on the first task close would be wrong. If `Deliverables/` ever needs a stale-orphan triage policy, that is a separate procedure outside GL-004's scope.

## When this Guideline gets read

- [[SOP-create-task]] step 4 — the cross-reference walk covers seven slots.
- [[SOP-claim-task]] pre-flight — the claiming agent reads `linked_deliverables` to know what working artifacts already exist.
- [[SOP-close-task]] §A.8 / §B.5 — the archival ritual reads `linked_deliverables` to know what to move.
- [[SOP-rebuild-task-index]] — may surface `linked_deliverables` counts as a quality signal (optional).
- Anyone writing a session log, journal entry, deliverable, SOP, WS, or GL — to confirm they MUST NOT add a `linked_tasks` field on the resource side.

## Cross-references

- [[GL-001-file-naming-conventions]] — slug rules. `linked_deliverables` slugs follow GL-001's kebab-case + ISO-date-prefix rule.
- [[GL-002-frontmatter-conventions]] §4 — foreign keys store slugs, not titles. GL-004 extends the same principle to task `linked_*` arrays.
- [[SOP-create-task]], [[SOP-claim-task]], [[SOP-close-task]], [[SOP-rebuild-task-index]] — the four task SOPs that read this rule.
- [[SOP-002-convert-mypka-to-sqlite]] — the optional mirror regen procedure. The archive-on-close rule's sharing check is cheaper against a current mirror.

## Updates to this Guideline

If the rule changes, update this file. Do not duplicate the change into any SOP, Workstream, or template. They `[[wikilink]]` here and inherit the change automatically.
