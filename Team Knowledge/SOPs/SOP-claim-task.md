# SOP — Claim a Task (with Block / Unblock sub-procedures)

- **Owner:** the agent picking up the task
- **Triggered by:** an agent starting work on an open task, hitting a blocker mid-work, or recording that a blocker has cleared
- **Output:** task file moved from `open/` to `in-progress/` (claim), or frontmatter updated in place (block/unblock)
- **References:** [[SOP-rebuild-task-index]], [[SOP-close-task]], [[SOP-read-own-journal]], [[GL-004-task-resource-linking]]

## Purpose

Claiming a task is recording "I picked this up." The act of claiming is the file move from `open/` to `in-progress/`. That's atomic — either the move succeeds (you own it) or it fails (someone else got there first).

Blocking and unblocking are not state changes — they're frontmatter edits in place. A blocked task stays in `in-progress/` so the assignee's normal queue scan still surfaces it. Hiding a blocked task in a separate folder hurts continuity.

## Three sub-procedures

- **§A Claim:** `open/` → `in-progress/`
- **§B Block:** in-place edit, sets `blocked_reason` and `blocked_by`
- **§C Unblock:** in-place edit, clears `blocked_reason` and `blocked_by`

## §A — Claim a task

### Pre-flight: read the cross-references

Before moving the file, open it and read the seven `linked_*` arrays. The task creator already identified the relevant SOPs, Workstreams, Guidelines, my-life entries, session logs, journal entries, and deliverables. Read at least:

- The first entry in `linked_sops` if any (the procedure that governs this work).
- All `linked_journal_entries` (your prior learning that applies).
- The most recent `linked_session_logs` (where this came up and why).
- Every `linked_deliverables` entry (the working artifacts already in flight — workups, drafts, manifests). These are where the work-in-progress lives; skipping them means re-doing what's already done.

This is the resumption move. Skip it and you start cold. See [[GL-004-task-resource-linking]] for the slug format.

### Steps

1. **Verify the file is still in `open/`.**
   ```bash
   ls "Team Knowledge/tasks/open/<id>-*.md"
   ```
   If it's not there, someone else already claimed it. Re-run [[SOP-list-open-tasks]].

2. **Move the file.**
   ```bash
   git mv "Team Knowledge/tasks/open/<id>-<slug>.md" "Team Knowledge/tasks/in-progress/<id>-<slug>.md"
   ```
   Use `git mv`, not `mv`. Preserves history.

   If `git mv` fails with `bad source`, another agent claimed it between your `ls` and now. Same response: re-list.

3. **Update frontmatter:** set `status: in-progress`, bump `updated` to now (UTC RFC3339).

4. **Append to `## Updates`:**
   ```
   - 2026-05-10 09:15 (<your-name>) — picked up, investigating
   ```

5. **If you read journal entries during pre-flight, note that in the update line:**
   ```
   - 2026-05-10 09:15 (mack) — picked up; loaded priors from [[2026-05-09-tauri-appimage-vs-deb]]
   ```

   This makes the resumption surface auditable. Future-you (or anyone resuming again) sees what priors were carried.

6. **Rebuild the index.** Run [[SOP-rebuild-task-index]].

## §B — Record a block

### When to call

You're working a task in `in-progress/` and hit something you can't resolve right now (waiting on a person, a credential, an upstream service, another task).

### Steps

1. **The file stays in `in-progress/`.** Do not move it. The assignee still owns it, the queue scan still surfaces it.

2. **Edit frontmatter:**
   ```yaml
   blocked_reason: "Waiting on Vercel env var rotation by the user — unblock when MUX_WEBHOOK_SECRET is set in production env"
   blocked_by: null         # or a task basename if the blocker is itself a task
   updated: 2026-05-10T11:42:00Z
   ```

   `blocked_reason` must be a single sentence with a concrete unblock condition. "Blocked, will revisit" is a smell — either the unblock is concrete, or the task should be cancelled.

3. **If the blocker is itself a task** (someone else's open work), create that task via [[SOP-create-task]] and reference it in `blocked_by`:
   ```yaml
   blocked_by: tsk-2026-05-10-002-rotate-vercel-secret
   ```
   The new blocker task gets `linked_*` references back to this one in its own frontmatter.

4. **Append to `## Updates`:**
   ```
   - 2026-05-10 11:42 (mack) — blocked: waiting on Vercel env var rotation by the user; unblock condition: MUX_WEBHOOK_SECRET set in prod env
   ```

5. **Rebuild the index.** The rebuild's "BLOCKED" callout will surface this in the in-progress section.

## §C — Record an unblock

### When to call

The blocker cleared. You're picking the task back up.

### Steps

1. **Edit frontmatter:**
   ```yaml
   blocked_reason: null
   blocked_by: null
   updated: 2026-05-10T14:20:00Z
   ```

2. **Append to `## Updates`:**
   ```
   - 2026-05-10 14:20 (mack) — unblocked: env var rotation confirmed in prod; resuming
   ```

3. **Rebuild the index.**

## Reassignment without claiming

A task in `open/` that just needs a different assignee:

1. Edit `assignee:` in place.
2. Bump `updated`.
3. Append `## Updates`: `- <date> <time> (<your-name>) — reassigned from <old> to <new>: <one-line reason>`.
4. Rebuild the index.

No file move. The task stays in `open/`.

## Worked example (claim)

Mack runs [[SOP-list-open-tasks]] and sees:

```
[priority 1] tsk-2026-05-09-001-mux-webhook-401 — assignee: mack
```

Pre-flight: opens the file, reads `linked_sops: [SOP-claim-task]`, `linked_session_logs: [2026-05-09-22-30_larry_video-launch-coordination]`, `linked_journal_entries: []`, `linked_deliverables: []`. Walks the session log to recover the launch context.

Claims:

```bash
git mv "Team Knowledge/tasks/open/tsk-2026-05-09-001-mux-webhook-401.md" \
       "Team Knowledge/tasks/in-progress/tsk-2026-05-09-001-mux-webhook-401.md"
```

Edits the file: `status: in-progress`, `updated: 2026-05-10T09:15:00Z`. Appends:

```
- 2026-05-10 09:15 (mack) — picked up, investigating; loaded launch context from [[2026-05-09-22-30_larry_video-launch-coordination]]
```

Runs [[SOP-rebuild-task-index]]. Reports back: `Claimed [[tsk-2026-05-09-001-mux-webhook-401]], digging in.`

## Common mistakes

- Using `mv` instead of `git mv`. Loses history attribution.
- Skipping pre-flight and reading the cross-references. The whole point of `linked_*` is to be read at claim time, not at create time only. **Including `linked_deliverables`** — skipping it means re-discovering working artifacts that already exist.
- Editing `status:` in frontmatter without moving the file. Now folder and frontmatter disagree. Validation script catches it but agents downstream see stale data.
- Setting `blocked_reason` without a concrete unblock condition. If the unblock isn't concrete, the task should be cancelled instead.
- Moving a blocked task into a separate `blocked/` folder. There is no `blocked/` folder. Blocking is a frontmatter edit; the file stays in `in-progress/`.
- Skipping the index rebuild because "it's just one transition." Index drift compounds.
