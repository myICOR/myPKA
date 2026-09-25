---
type: sop
id: SOP-1008
title: Track work across sessions
created: 2026-08-27
owner: larry
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1004-naming-rules]]", "[[GL-1005-code-vs-instructions]]"]
---

# SOP-1008 Track work across sessions

Tasks are the team's continuity between sessions. They live in
`AI Team Knowledge/Tasks/{open,in-progress,done,cancelled}`.

1. [SCRIPT] Create: `Scripts/new-task.py new --slug ... --title ...
   --assignee ...`. Anything unfinished at session end becomes a task
   BEFORE the session closes (AGENTS.md hard rule 7).
2. [SCRIPT] Move: `Scripts/new-task.py move <name> --to in-progress`
   when picked up, `--to done` when delivered, `--to cancelled` when the
   user drops it. The script keeps status field and folder in sync and
   files done/cancelled under YYYY/MM/.
3. [JUDGEMENT] At session start Larry walks `open/` and `in-progress/`
   and tells the user where things stand.
4. A task is one outcome. Two outcomes is two tasks.
