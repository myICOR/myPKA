# SOP — List Open Tasks

- **Owner:** any agent (Larry runs this at every session boot)
- **Triggered by:** session start, status check, "where did we leave off?"
- **Output:** a printable summary of open and in-progress tasks (with blocked tasks called out)
- **References:** [[SOP-rebuild-task-index]]

## Purpose

This is the resumption-at-scale SOP. At session start, we need to answer: "What's unfinished, who owns it, what's blocked, and what just shipped?" Without this answer, every new session starts cold.

## Two ways to do this

- **§A Fast:** read `Team Knowledge/tasks/INDEX.md`. The index is auto-rebuilt by every task-touching SOP, so it's almost always fresh.
- **§B Authoritative:** walk the folders directly with grep. Use this when you don't trust the index, or when you need a filter the index doesn't render.

Default to §A. Fall back to §B when needed.

## §A — Read the index

```bash
cat "Team Knowledge/tasks/INDEX.md"
```

Sections: Summary, Open (by priority), In progress (with blocked callouts), By assignee, Recently closed.

If the index `_Last rebuilt:_` timestamp is older than the newest file in `tasks/`, run [[SOP-rebuild-task-index]] first.

```bash
INDEX_MTIME=$(stat -f %m "Team Knowledge/tasks/INDEX.md" 2>/dev/null || stat -c %Y "Team Knowledge/tasks/INDEX.md")
NEWEST=$(find "Team Knowledge/tasks" -name "tsk-*.md" -type f -exec stat -f %m {} \; 2>/dev/null | sort -n | tail -1)
[ "$NEWEST" -gt "$INDEX_MTIME" ] && echo "stale, rebuild first"
```

(macOS uses `stat -f`; Linux uses `stat -c`. Both shown for portability.)

## §B — Walk the folders directly

### List all open tasks (any assignee)

```bash
for f in "Team Knowledge/tasks/open"/tsk-*.md; do
  [ -f "$f" ] || continue
  awk '/^---$/{c++; next} c==1 && /^(id|title|assignee|priority): /' "$f"
  echo "---"
done
```

### List my open and in-progress tasks (everything I'm currently on the hook for)

```bash
ME=mack
grep -rlE "^assignee: ${ME}\b" \
  "Team Knowledge/tasks/open" \
  "Team Knowledge/tasks/in-progress"
```

### List blocked tasks (in-progress only — that's where they live)

```bash
grep -rlE "^blocked_reason: [^n]" "Team Knowledge/tasks/in-progress"
```

(The pattern `[^n]` excludes `null`. A blocked task has a non-null `blocked_reason`.)

### List urgent (priority 1) anywhere not yet done

```bash
grep -rlE "^priority: 1\b" \
  "Team Knowledge/tasks/open" \
  "Team Knowledge/tasks/in-progress"
```

### List tasks created in this session

```bash
SESSION=2026-05-09-22-30_larry_video-launch-coordination
grep -rlE "^linked_session_logs:.*${SESSION}" "Team Knowledge/tasks"
```

## Larry's session-boot routine

At the start of every session, Larry runs:

1. `cat "Team Knowledge/tasks/INDEX.md"` — get the lay of the land.
2. Filter mentally to "Open priority 1" and "In-progress with assignee likely active" — surface those to {{USER_NAME}} first.
3. Check the "BLOCKED" callouts — any of them now unblockable given today's context?
4. If any open tasks have been sitting >7 days, or any in-progress tasks have been blocked >3 days without movement, surface them for triage.

The output {{USER_NAME}} sees at boot is a one-paragraph summary:

> Morning. Open: one urgent for Mack (mux-webhook 401). In progress: Penn mid-batch on inbox captures, Silas has the secret-rotation task blocked on Vercel env access (3rd day — want to nudge?). Closed yesterday: 4 tasks. No follow-ups stranded.

That's the resumption surface. {{USER_NAME}} knows where to start without re-reading anything else.

## Other agents' session-boot routine

Each specialist activated for work runs:

```bash
ME=<my-agent-name>
grep -rlE "^assignee: ${ME}\b" \
  "Team Knowledge/tasks/in-progress" \
  "Team Knowledge/tasks/open"
```

…to find every task they own. Read the highest-priority in-progress one first (that's where you left off). Then open tasks.

For each task picked up, also read the task's `linked_journal_entries` — see [[SOP-read-own-journal]] for the discipline.

## Common mistakes

- Trusting the index when something just changed in the same session. Re-run [[SOP-rebuild-task-index]] if you've been editing.
- Greppping for assignee without `\b` boundary — matches `mackenzie` if the assignee is `mack`. Use `^assignee: mack\b` or `^assignee: mack$`.
- Forgetting that blocked tasks live in `in-progress/`, not in a separate folder. Look for `blocked_reason: ` not equal to `null`.
- Not surfacing long-blocked or long-stale tasks. The triage prompt at session boot is what keeps the queue alive.
