# SOP — Close a Task (Done or Cancelled)

- **Owner:** the agent finishing the task (for done) or the user/Larry (for cancel)
- **Triggered by:** task work shipping or being abandoned
- **Output:** task file archived in `done/<YYYY>/<MM>/` or `cancelled/<YYYY>/<MM>/`; every deliverable in `linked_deliverables` archived alongside
- **References:** [[SOP-rebuild-task-index]], [[SOP-write-journal-entry]], [[GL-004-task-resource-linking]], [[SOP-002-convert-mypka-to-sqlite]]

## Purpose

Closing a task is recording "this resumption point is now history." The `## Outcome` section is the continuity payload — what shipped, where it lives, what follow-ups exist. Future-anyone reading the closed task should be able to reconstruct what was accomplished without opening anything else.

Closing a task also **archives its working deliverables**. Per [[GL-004-task-resource-linking]] the task is the owning artifact for its `linked_deliverables`; when the task moves to `done/` or `cancelled/`, the deliverables it owns move to the archive subtree. The archive keeps the deliverables reachable (wikilinks still resolve by basename) but moves them out of the active working-surface of `Deliverables/`.

The archive-on-close rule's sharing check is cheaper against a current SQLite mirror, if the user maintains one. If your last [[SOP-002-convert-mypka-to-sqlite]] regen is stale (or you don't run the mirror at all), the `grep`-based sharing check below works the same way — it's just slower at scale. **Regen first if you have any doubt.**

## Two sub-procedures

- **§A Done:** terminal success. Move task to `done/<YYYY>/<MM>/`. Archive linked deliverables.
- **§B Cancel:** terminal abandonment. Move task to `cancelled/<YYYY>/<MM>/`. Archive linked deliverables.

Both terminal. Once a task is in `done/` or `cancelled/`, do not move it back. If the work needs to reopen, create a new task with `parent: <old-id>`.

## §A — Mark a task done

### Pre-flight

1. **Verify success criteria.** Re-read the task body's `## Success criteria`. All met? If not, the task isn't done.

2. **Check sub-tasks.**
   ```bash
   grep -rl "parent: <id>" "Team Knowledge/tasks/open" "Team Knowledge/tasks/in-progress"
   ```
   If any sub-tasks are still open or in-progress: surface them. Decide explicitly whether to (a) close them too, (b) leave them as standalone follow-ups, or (c) hold this parent open until they settle. Document the decision in the parent's `## Outcome`.

3. **Check for deliverable sharing.** Read `linked_deliverables` on this task. For each entry, grep the rest of `tasks/open/` and `tasks/in-progress/` for the same slug:
   ```bash
   for d in <linked_deliverables>; do
     grep -rl "$d" "Team Knowledge/tasks/open" "Team Knowledge/tasks/in-progress"
   done
   ```
   If another open or in-progress task references the same deliverable, the deliverable cannot be archived in this close. Decision required — see step 8.

### Steps

1. **Determine the archive path for the task.**
   ```bash
   YEAR=$(date -u +%Y)
   MONTH=$(date -u +%m)
   DEST="Team Knowledge/tasks/done/${YEAR}/${MONTH}"
   mkdir -p "$DEST"
   ```

2. **Move the task file.** Source is `in-progress/`:
   ```bash
   git mv "Team Knowledge/tasks/in-progress/<id>-<slug>.md" "$DEST/<id>-<slug>.md"
   ```

3. **Update frontmatter:** `status: done`, bump `updated`. Clear `blocked_reason` and `blocked_by` if they were set.

4. **Write the `## Outcome` section.** Mandatory. Shape:

   ```markdown
   ## Outcome

   What shipped: <one-paragraph summary>.

   Where it lives: [[<wikilink to commit, file, or session-log>]].

   Follow-ups: [[<sub-task ids if any>]] or "none."

   Lessons: <optional, [[wikilink]] to a journal entry if you wrote one>.

   Archived deliverables: <list — see step 8>.
   ```

5. **Append final update line:**
   ```
   - 2026-05-10 17:42 (<your-name>) — done: <one-line summary>
   ```

6. **If you learned something durable, write a journal entry.** See [[SOP-write-journal-entry]]. Link it from the `## Outcome` section, and add the entry's basename to `linked_journal_entries:` in this task's frontmatter (so future readers of this task get the lesson).

7. **Append the close to the linked session log.** If `linked_session_logs` includes the current session, no extra step. If you closed during a different session, add this session's basename to the array. Continuity needs the session log to know the task closed in this session.

8. **Archive linked deliverables.** (Per [[GL-004-task-resource-linking]].) For each entry in `linked_deliverables`:
   ```bash
   YEAR=$(date -u +%Y)
   MONTH=$(date -u +%m)
   ARCHIVE_ROOT="Deliverables/_archive/${YEAR}/${MONTH}"
   mkdir -p "$ARCHIVE_ROOT"
   ```

   For a deliverable slug of shape `<folder-slug>/<file-slug>` (multi-file folder), the **entire folder** moves once:
   ```bash
   # If folder hasn't been moved yet this close:
   git mv "Deliverables/<folder-slug>" "$ARCHIVE_ROOT/<folder-slug>"
   ```

   Move-the-folder-not-the-file rule: when multiple `linked_deliverables` entries share the same `<folder-slug>` prefix, move the folder once. Do not split a multi-file folder across active and archive.

   **Sharing check (from pre-flight step 3).** If another open or in-progress task also references one of this task's deliverables, the deliverable stays in `Deliverables/`. Record the deferred archive in `## Outcome`:
   ```markdown
   Archived deliverables:
     - `2026-05-12-mcp-install/` → archived to `Deliverables/_archive/2026/05/2026-05-12-mcp-install/`
     - `2026-05-12-research-brief/` → archive deferred (still referenced by [[tsk-2026-05-15-002-...]])
   ```

   The next task that closes and shares the deliverable archives it then. If the deliverable still has open references at the end of the closing session, that is fine — it stays active until the last referencing task closes.

9. **Rebuild the index.**

## §B — Cancel a task

### When to call

Requirements changed. Duplicate of another task. Permanent blocker. User decided otherwise.

### Steps

1. **Determine task archive path.**
   ```bash
   YEAR=$(date -u +%Y)
   MONTH=$(date -u +%m)
   DEST="Team Knowledge/tasks/cancelled/${YEAR}/${MONTH}"
   mkdir -p "$DEST"
   ```

2. **Move the task file.** Source can be `open/` or `in-progress/`:
   ```bash
   git mv "Team Knowledge/tasks/<source>/<id>-<slug>.md" "$DEST/<id>-<slug>.md"
   ```

3. **Update frontmatter:** `status: cancelled`, bump `updated`. Clear `blocked_reason` and `blocked_by`.

4. **Write `## Outcome` explaining the cancellation.**
   ```markdown
   ## Outcome (cancelled)

   Reason: <why we cancelled>.

   Superseded by: [[<other-task-id>]] (if applicable, otherwise "n/a").

   Archived deliverables: <list>.
   ```

5. **Archive linked deliverables.** Identical procedure to §A.8 above. A cancelled task's deliverables are still historical record — archive them, don't delete them. Sharing check from pre-flight applies the same way.

6. **Append final update:**
   ```
   - 2026-05-10 16:00 (<your-name>) — cancelled: <one-line reason>
   ```

7. **Rebuild the index.**

## "Done-ish but not really"

You shipped most of the work but a piece slipped to a follow-up. Two options:

- **Close as done, create a new task for the follow-up** with `parent: <this-id>`. Preferred — keeps each task scoped to one outcome. **The follow-up task's `linked_deliverables` should reference the same deliverables**, which means the close cannot archive those deliverables yet (sharing check in pre-flight step 3 will catch this). Record the deferred archive in the closing task's outcome.
- **Set `blocked_reason` on this task** with the follow-up as `blocked_by`. Use only if the follow-up is small and same-day. Otherwise `in-progress/` stagnates.

## Worked example (done, no deliverables)

Mack closes the mux-webhook task:

```bash
mkdir -p "Team Knowledge/tasks/done/2026/05"
git mv "Team Knowledge/tasks/in-progress/tsk-2026-05-09-001-mux-webhook-401.md" \
       "Team Knowledge/tasks/done/2026/05/tsk-2026-05-09-001-mux-webhook-401.md"
```

Frontmatter: `status: done`, `updated: 2026-05-10T17:42:00Z`.

Body, `## Outcome`:

```markdown
## Outcome

What shipped: rotated MUX_WEBHOOK_SECRET in Vercel prod env, redeployed `/api/mux-webhook`, verified 200 on signed test payload. Root cause: secret was rotated in Mux dashboard but the Vercel env var was set via the team's old "manual paste" flow which wasn't part of the rotation runbook.

Where it lives: commit ab12cd3. Session-log [[2026-05-10-09-15_mack_mux-webhook-recovery]].

Follow-ups: [[tsk-2026-05-10-001-document-secret-rotation-runbook]].

Lessons: [[2026-05-10-secret-rotation-discipline]] (journal).

Archived deliverables: none (this task had `linked_deliverables: []`).
```

Mack also writes the journal entry [[2026-05-10-secret-rotation-discipline]] and adds it to this task's `linked_journal_entries`. He adds the current session log to `linked_session_logs`.

Final update line:

```
- 2026-05-10 17:42 (mack) — done: rotated secret + verified webhook 200
```

Rebuild index. Report to Larry: `Closed [[tsk-2026-05-09-001-mux-webhook-401]]. One follow-up: [[tsk-2026-05-10-001-document-secret-rotation-runbook]]. Journal: [[2026-05-10-secret-rotation-discipline]]. No deliverables to archive.`

## Worked example (done, with deliverable archive)

Mack closes the MCP install task whose `linked_deliverables` referenced four files under `Deliverables/2026-05-12-mcp-install/`:

```bash
mkdir -p "Team Knowledge/tasks/done/2026/05"
git mv "Team Knowledge/tasks/in-progress/tsk-2026-05-12-001-install-mcp.md" \
       "Team Knowledge/tasks/done/2026/05/tsk-2026-05-12-001-install-mcp.md"
```

Frontmatter: `status: done`, `updated: 2026-05-13T11:00:00Z`.

Body, `## Outcome`:

```markdown
## Outcome

What shipped: MCP server installed and smoke-tested; 14 shims amended per shim-amendments.md v2.

Where it lives: commit cd34ef5. Session-log [[2026-05-13-10-15_mack_mcp-install-complete]].

Follow-ups: [[tsk-2026-05-13-001-settings-audit]].

Lessons: [[2026-05-13-mcp-server-registered-not-running-discovery]] (journal).

Archived deliverables:
  - `2026-05-12-mcp-install/` (entire folder, contains workup, workup-v2, shim-amendments, user-checklist) → archived to `Deliverables/_archive/2026/05/2026-05-12-mcp-install/`
```

Archive moves:
```bash
mkdir -p "Deliverables/_archive/2026/05"
git mv "Deliverables/2026-05-12-mcp-install" \
       "Deliverables/_archive/2026/05/2026-05-12-mcp-install"
```

(One `git mv` of the whole folder, not four separate moves. The four `linked_deliverables` entries all share the same `<folder-slug>` prefix.)

Sharing check confirmed nothing else under `tasks/open/` or `tasks/in-progress/` referenced any of the four `linked_deliverables` slugs. Good — they all archive together.

Final update line:

```
- 2026-05-13 11:00 (mack) — done: MCP installed, smoke-tested, 14 shims amended; folder archived to _archive/2026/05/
```

Rebuild index. Report to Larry: `Closed [[tsk-2026-05-12-001-install-mcp]]. Four deliverables archived together as one folder move. One follow-up: [[tsk-2026-05-13-001-settings-audit]].`

## Common mistakes

- Closing without writing `## Outcome`. The future archaeologist learns nothing from this archive.
- Closing a parent while children are still open without acknowledging them.
- Marking done when blocker resolved but success criteria not actually re-checked. Resist.
- Cancelling without a reason. "Cancelled" with no `## Outcome` is indistinguishable from data loss.
- Forgetting to add a journal entry's basename to `linked_journal_entries` when you wrote one. The body wikilink points there but a future task that wants to find related learning will grep frontmatter, not bodies.
- **Skipping the archive step.** A closed task with active deliverables in `Deliverables/` is a half-archived workflow. The deliverables clutter the active surface forever.
- **Splitting a deliverable folder across active and archive.** If two `linked_deliverables` entries share a folder prefix, move the folder once, not the files individually.
- **Archiving a deliverable that another open task still references.** Run the pre-flight sharing check. If the sharing check is skipped because `mypka.db` is stale (or you don't run the mirror at all), you may miss references — regen the mirror first if you have any doubt, or fall back to the `grep` form of the check.
- **Adding `linked_tasks` to the deliverables you just archived** (e.g. "let me record on the workup file that it belonged to tsk-2026-05-12-001"). Forbidden by [[GL-004-task-resource-linking]]. The owning task is recorded one-way: the task points at the deliverable, never the reverse. To find which task owned an archived deliverable, grep the closed task tree for the deliverable's slug, or query `mypka.db.wikilinks` if the mirror is installed.
