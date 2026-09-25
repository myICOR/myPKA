---
type: sop
id: SOP-1009
title: Write a session log and an agent journal entry
created: 2026-08-27
owner: larry
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1004-naming-rules]]"]
---

# SOP-1009 Write a session log and an agent journal entry

The team's long-term memory. Runs at every session close (AGENTS.md
hard rule 9) and whenever the user says "keep this in mind".

1. [SCRIPT] `Scripts/new-session-log.py --agent <lead-agent>
   --slug <what-happened>` creates the skeleton in
   `Session Logs/YYYY/MM/`.
2. [JUDGEMENT] Fill the three sections: What happened (facts, files
   touched), Decisions (what the user ruled, quotes where wording
   matters), Open threads (what a future session must know).
3. [JUDGEMENT] Each agent that learned something durable appends a short
   dated entry to its own `Agents/<Name>/Journal/` (one file per
   insight, `YYYY-MM-DD-<slug>.md`, type journal-entry). Agents re-read
   their journal before starting related work.
4. Session logs are append-only: never edited after the session, never
   deleted.
