# SOP — Create a Task

- **Owner:** any agent
- **Triggered by:** an agent or the user identifying a unit of work that won't finish this turn and should be picked up later
- **Output:** a new file in `Team Knowledge/tasks/open/`
- **References:** [[SOP-rebuild-task-index]], [[SOP-claim-task]], [[GL-001-file-naming-conventions]], [[GL-004-task-resource-linking]]

## Purpose

A task is a **resumption point**. Whoever opens this file later — the user, the assignee, a different agent — should be able to reconstruct the full working context one wikilink away. Creating a task well means making that resumption easy. The discipline of populating cross-references at creation is the whole job.

A task is also the **owning artifact for its working deliverables**. A Deliverables folder by itself is a working surface with no clean record of which workflow owns it. The owning task is the one place that record lives. See [[GL-004-task-resource-linking]].

## When to call this

You're talking to the user (or another agent) and a piece of work is identified that:
- Will not be finished in this turn, AND
- Should be remembered/handed off, AND
- Is not already covered by an existing task (grep first).

If those three are true, create a task. Otherwise just do it now.

## Inputs you need

| Input | Required | Notes |
|---|---|---|
| Title | yes | One sentence. No trailing period. |
| What this is | yes | A paragraph: what the work is, what success looks like. |
| Assignee | yes | Agent name or `unassigned` if routing is uncertain. |
| Priority | no | 1=urgent, 2=high, 3=normal (default), 4=low. |
| Tags | no | Lowercase, kebab- or snake-case. |
| Source | no | Where the request originated. |
| Parent | no | Task id of the parent if this is a sub-task. |
| Due date | no | ISO date. |
| **Cross-references** | **yes (each may be empty)** | The seven `linked_*` arrays. See step 4 below. |

## Steps

### 1. Check for duplicates

```bash
grep -ril "<keyword from title>" \
  "Team Knowledge/tasks/open" \
  "Team Knowledge/tasks/in-progress"
```

If a task already exists, append an update line to its `## Updates` section instead of creating a duplicate. Done.

### 2. Generate the task id

```bash
TODAY=$(date -u +%Y-%m-%d)
NEXT=$(find "Team Knowledge/tasks" -name "tsk-${TODAY}-*.md" 2>/dev/null | wc -l | awk '{printf "%03d", $1+1}')
ID="tsk-${TODAY}-${NEXT}"
```

If creation later fails because the file already exists (race with another agent), increment `NEXT` and retry. Up to 5 retries.

### 3. Slug the title

```bash
SLUG=$(echo "<title>" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-50 | sed -E 's/-+$//')
FILENAME="${ID}-${SLUG}.md"
```

### 4. Confront the cross-references (the heart of this SOP)

Before writing the file, walk through the **seven** reference types and decide what applies. Empty arrays are valid; the discipline is doing the walk, not finding something to put in every slot. See [[GL-004-task-resource-linking]] for the one-way rule and slug formats.

| Reference type | Ask yourself |
|---|---|
| `linked_sops` | Is there an existing procedure in `Team Knowledge/SOPs/` that governs this kind of work? List the basenames. |
| `linked_workstreams` | Is there an active arc in `Team Knowledge/Workstreams/` that this fits inside? |
| `linked_guidelines` | Are there standards in `Team Knowledge/Guidelines/` that constrain how this should be done? |
| `linked_my_life` | Is there a Topic / Habit / Goal / Project / Key Element in `PKM/My Life/` that gives the user's context for why this is happening? |
| `linked_session_logs` | Which session(s) birthed or touched this? At minimum, the session you're in right now. |
| `linked_journal_entries` | Has the assignee (or anyone) written a journal entry that's relevant prior learning? Especially if the assignee is going to read this cold later. |
| `linked_deliverables` | Does this task have working artifacts in `Deliverables/`? Workups, manifests, briefs, drafts, attachments? List every single one. If the task births new deliverables later, **append them to `linked_deliverables` mid-work, do not wait for close** — the task is the one place that owns the deliverable→workflow link. |

For each, list basenames. Use grep when uncertain:

```bash
ls "Team Knowledge/SOPs/" | grep -i <keyword>
ls "Team Knowledge/Workstreams/"
ls "Team Knowledge/Guidelines/"
find "PKM/My Life" -name "*.md" | grep -i <keyword>
find "Team Knowledge/session-logs" -name "*.md" | tail -5
find "Team" -path "*/journal/*.md" | grep -i <keyword>
ls "Deliverables/" | grep -i <keyword>           # for linked_deliverables
```

Slug format for `linked_deliverables`: per [[GL-004-task-resource-linking]] — `<folder-slug>/<file-slug>` for sub-files inside a multi-file Deliverables folder, or `<folder-slug>` when pointing at the folder as a whole, or `<folder-slug>/manifest` when pointing at the manifest of a multi-file folder.

### 5. Write the file

Copy `Team Knowledge/tasks/_template.md` to `Team Knowledge/tasks/open/${FILENAME}`. Fill in:

- All identity, ownership, status, time, provenance fields
- All **seven** `linked_*` arrays (use `[]` if genuinely none — but only after walking step 4)
- Tags
- Body: `## What this is`, `## Context one click away`, `## Success criteria`, `## Updates`

The `## Context one click away` section in the body must mirror the frontmatter `linked_*` arrays as `[[wikilinks]]` — that's how the human reader gets one-click navigation. For `linked_deliverables`, use the `Working artifacts:` sub-bullet pattern in the template. Frontmatter is for machine reading; body wikilinks are for humans. Both populated, kept in sync.

`created` and `updated` are RFC3339 UTC: `date -u +%Y-%m-%dT%H:%M:%SZ`.

### 6. Append the first update line

```markdown
- 2026-05-10 12:34 (<your-agent-name>) — created
```

### 7. Rebuild the index

Run [[SOP-rebuild-task-index]]. Always.

### 8. Report back

Tell the calling user/agent:

```
Created [[<id>-<slug>]] (priority <N>, assignee <name>).
Cross-refs: <count of populated linked_* arrays>/7 populated.
```

## Worked example (minimal — no deliverables yet)

User to Larry: "Mack, the mux-webhook is throwing 401s — please look into MUX_WEBHOOK_SECRET drift."

Larry's call:

```bash
TODAY=2026-05-09
NEXT=001
ID=tsk-2026-05-09-001
SLUG=mux-webhook-401
FILENAME=tsk-2026-05-09-001-mux-webhook-401.md
```

Step 4 — Larry walks the cross-references:

- `linked_sops` — `[SOP-claim-task]` (Mack will follow this when picking up).
- `linked_workstreams` — `[]` (no active workstream covers this; it's a one-off fire).
- `linked_guidelines` — `[]` (no standards apply; it's a config drift fix).
- `linked_my_life` — `[]` (this is internal infrastructure, not user life context).
- `linked_session_logs` — `[2026-05-09-22-30_larry_video-launch-coordination]` (the session it surfaced in).
- `linked_journal_entries` — `[]` (Mack hasn't written a webhook journal entry yet — this task may birth one).
- `linked_deliverables` — `[]` (no working artifacts yet; this is a fix-in-place task, not a multi-file workup).

File written to `Team Knowledge/tasks/open/tsk-2026-05-09-001-mux-webhook-401.md`:

```markdown
---
id: tsk-2026-05-09-001
title: "Fix mux-webhook 401 / MUX_WEBHOOK_SECRET drift"
assignee: mack
priority: 1
status: open
blocked_reason: null
blocked_by: null
created: 2026-05-09T22:37:11Z
updated: 2026-05-09T22:37:11Z
due: null
created_by: larry
source: larry-session-2026-05-09
parent: null
linked_sops: [SOP-claim-task]
linked_workstreams: []
linked_guidelines: []
linked_my_life: []
linked_session_logs: [2026-05-09-22-30_larry_video-launch-coordination]
linked_journal_entries: []
linked_deliverables: []
tags: [infrastructure, mux, urgent]
---

# Fix mux-webhook 401 / MUX_WEBHOOK_SECRET drift

## What this is
The mux-webhook endpoint started returning 401 mid-launch. Suspected MUX_WEBHOOK_SECRET rotation that didn't propagate to the Vercel env var. User-visible impact: Mux callbacks for video processing aren't being delivered.

## Context one click away
- Procedure: [[SOP-claim-task]]
- Birthed in: [[2026-05-09-22-30_larry_video-launch-coordination]]

## Success criteria
- mux-webhook returns 200 on a test signed payload
- Env var documented so this can't recur silently
- Root cause noted

## Updates
- 2026-05-09 22:37 (larry) — created

## Outcome
_(filled when status flips to done)_
```

Then `SOP-rebuild-task-index` and report: `Created [[tsk-2026-05-09-001-mux-webhook-401]] (priority 1, assignee mack). Cross-refs: 2/7 populated (linked_sops, linked_session_logs).`

## Worked example (with `linked_deliverables` populated)

User to Larry: "Mack, install a new MCP server — there's a workup in Deliverables already, plus a security check pending."

Mack identifies the task wraps four working artifacts already on disk under `Deliverables/2026-05-12-mcp-install/`. The seven-array walk produces:

```yaml
---
id: tsk-2026-05-12-001
title: "Install <name> MCP (workup → security check → keys → install → smoke test)"
assignee: mack
priority: 2
status: open
blocked_reason: awaiting security re-verification + user API keys
blocked_by: null
created: 2026-05-12T12:56:20Z
updated: 2026-05-12T18:30:00Z
due: null
created_by: mack
source: larry-brief-2026-05-12
parent: null
linked_sops:
  - SOP-create-task
  - SOP-claim-task
  - SOP-close-task
  - SOP-write-session-log
linked_workstreams:
  - WS-003-install-an-expansion
linked_guidelines:
  - GL-004-task-resource-linking
linked_my_life: []
linked_session_logs:
  - 2026-05-12-23-15_nolan_shim-tool-allowlist-audit
linked_journal_entries: []
linked_deliverables:
  - 2026-05-12-mcp-install/workup
  - 2026-05-12-mcp-install/workup-v2
  - 2026-05-12-mcp-install/shim-amendments
  - 2026-05-12-mcp-install/user-checklist
tags: [mcp, install, ws-003, blocked-on-user-keys]
---
```

The body's `## Context one click away` block mirrors:

```markdown
- Procedure (install): [[WS-003-install-an-expansion]]
- Procedure (task moves): [[SOP-claim-task]], [[SOP-close-task]]
- Procedure (session-log at install): [[SOP-write-session-log]]
- Guideline: [[GL-004-task-resource-linking]]
- Most recent context: [[2026-05-12-23-15_nolan_shim-tool-allowlist-audit]]
- Working artifacts:
  - [[workup]]
  - [[workup-v2]]
  - [[shim-amendments]]
  - [[user-checklist]]
```

Report back: `Created [[tsk-2026-05-12-001-install-mcp]] (priority 2, assignee mack). Cross-refs: 5/7 populated (sops, workstreams, guidelines, session_logs, deliverables).`

## Common mistakes

- **Skipping the cross-reference walk** because "I don't know what applies." That's exactly when the walk matters most — the walk forces you to grep and confirm. Empty arrays are fine; not having walked is not.
- Creating a task for something you're about to do this turn. Just do it.
- Skipping the duplicate check.
- Forgetting `created_by`. The audit trail dies without it.
- Putting the assignee in the body instead of the frontmatter. Frontmatter is the source of truth for routing.
- Listing wikilinks in the body but forgetting to mirror them in `linked_*` frontmatter (or vice versa). They have to match.
- Wrapping basenames in `[[...]]` inside YAML frontmatter — Obsidian doesn't render YAML wikilinks reliably. YAML uses bare basenames; the body uses `[[basename]]`.
- **Adding `linked_tasks` to a resource** (deliverable / journal / session log / SOP / WS / GL / My Life entry). Pre-GL-004 violation. The link is one-way: task→resource, never the reverse. See [[GL-004-task-resource-linking]].
- **Forgetting to add a deliverable to `linked_deliverables` when you create it mid-task.** The task is the *only* place a deliverable's owning workflow is recorded. If you wrote a workup at 2pm and forgot to append it to the task's `linked_deliverables` until close, the deliverable was orphan for the entire afternoon — anyone resuming the task in between had no way to find it from frontmatter.
