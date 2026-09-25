---
type: workstream
id: WS-1005
title: Checkpoint (end a session on purpose)
created: 2026-09-06
owner: larry
skill_name: checkpoint
skill_summary: 'Ends a session on purpose: reads the checkpoint report, closes or carries every task the session touched, rules on each WiP folder with the user, links the dates the session wrote, writes the session log and asserts it exists before the session is allowed to be over.'
skill_triggers:
  - 'checkpoint'
  - 'close the session'
  - 'wrap up'
  - 'we are done for today'
  - 'end the session'
  - 'let us stop here'
skill_prerun: 'python3 "06 AI Team/AI Team Knowledge/Scripts/checkpoint.py" --json'
uses: ["[[SOP-1008-track-work-across-sessions]]", "[[SOP-1006-start-work-and-archive-a-wip-folder]]", "[[SOP-1009-write-a-session-log-and-agent-journal]]", "[[WS-1002-weekly-review]]", "[[GL-1005-code-vs-instructions]]", "[[GL-1011-date-mentions-link-to-daily-notes]]"]
---
# WS-1005 Checkpoint

A session ends when you close the terminal, and nothing fires on its own.
The checkpoint is the forcing function: **you** type `/checkpoint`, and the
team answers five questions before the session is allowed to be over. Run it
whenever you stop for the day, and whenever a piece of work is done.

1. [SCRIPT] `Scripts/checkpoint.py` prints the facts: the last session
   log, which tasks changed since it, and every piece of work in the WiP room
   with its age and whether any open task still names it. Read it; do not
   re-derive it. The buckets themselves never leave, only the dated work
   inside them, and `Operations/` is read first because it is the bucket
   nothing closes from the outside.
2. [JUDGEMENT] **Tasks.** For each task the report lists as touched: if
   its work shipped, move it to `Tasks/done/YYYY/MM/` with a one-line
   outcome ([[SOP-1008-track-work-across-sessions|SOP-1008]]); if it is
   still open, leave it and write the unfinished part into the session
   log's Open threads. Unfinished work that has no task yet gets one now
   (`Scripts/new-task.py`). Propose cancelling what is dead; the user rules.
3. [JUDGEMENT] **WiP.** For each folder the report flags `LEAVE?`, propose
   archiving it ([[SOP-1006-start-work-and-archive-a-wip-folder|SOP-1006]]
   step 4). Archive only what the user confirms; a folder they name as
   ongoing stays, and the reason goes in the log.
4. [SCRIPT] **Date links.** Get the path of the content source's
   `link-dates-to-daily-notes` tool with
   `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool link-dates-to-daily-notes`
   ([[GL-1013-sources-and-the-resolver|GL-1013]]), then run that path
   with `--fix`. It turns every date this session wrote into a note body into
   `[[YYYY-MM-DD]]` and creates the daily notes behind them
   ([[GL-1011-date-mentions-link-to-daily-notes|GL-1011]]). It runs before
   the log is written, so the log's own dates are linked too. Additive and
   idempotent; nothing to rule on.
5. [SCRIPT] **Session log.** `Scripts/new-session-log.py --agent larry
   --slug <what-happened>`, then fill it per
   [[SOP-1009-write-a-session-log-and-agent-journal|SOP-1009]]: what
   happened, decisions, open threads. Agents that learned something
   durable append to their own `Journal/`.
6. [SCRIPT] **The receipt.** `Scripts/checkpoint.py --write-receipt
   --output "<the session log you just wrote>"` records what this session
   closed: the workflow, the session id, the outputs and their hashes, and
   anything knowingly left open (`--unresolved "..."`, repeatable).
7. [SCRIPT] `Scripts/checkpoint.py --assert-logged --assert-dates-linked`
   must exit 0. `--assert-logged` reads the receipt for THIS session, so a
   log written this morning can no longer close a session that ran this
   afternoon and wrote nothing. A checkpoint that ends without its own log
   is not a checkpoint, and neither is one that leaves a date pointing at
   nothing.

   On a runtime with no session start hook there is no session id, and the
   assert says so and names the lever. Use `--assert-logged-today` there,
   knowing it is weaker: it proves a file exists with today's date on it
   and nothing else.

**What it does not do.** It does not process the Inbox or the Scratchpad
(that is [[WS-1001-daily-processing-run|WS-1001]], on your word), and it
does not look back over the week ([[WS-1002-weekly-review|WS-1002]] does,
with the same script at a 30-day window). It does not touch your task
tools outside this vault.

**Why a command and not a habit.** `CLAUDE.md` used to carry a three-line
"session close ritual" that fired when the model decided a session was
ending. Sessions do not announce their ending, so it rarely fired. A command
you type fires every time.
