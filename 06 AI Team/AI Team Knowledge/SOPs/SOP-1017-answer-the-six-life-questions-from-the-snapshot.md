---
type: sop
id: SOP-1017
title: Answer the six life questions from the snapshot
created: 2026-09-15
owner: mack
uses: ["[[GL-1005-code-vs-instructions]]", "[[GL-1008-the-machine-layer]]"]
skill_name: answer-the-six-life-questions
skill_summary: 'Answers the six everyday life questions (my goals, what to focus on, the weekly priorities, the highlight of today, my key elements, what has my attention) from the one regenerated snapshot file, and never by walking the folders.'
skill_triggers:
  - 'what are my goals'
  - 'what should I focus on'
  - 'weekly priorities'
  - 'highlight of today'
  - 'my key elements'
  - 'what am I paying attention to'
skill_prerun: 'python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool life-snapshot'
---

# SOP-1017 Answer the six life questions from the snapshot

Six questions a member asks all the time. Each one is answered by reading
one file a script wrote, out loud, in the member's own words. None of them
is answered by opening the Inner World concepts.

1. What are my goals?
2. What should I focus on?
3. What are my weekly priorities?
4. What is the highlight of today?
5. What are my key elements?
6. What am I paying attention to?

## 0. The one rule this procedure exists to hold

**The folders are not the answer. The snapshot is.** Five of the six used to
cost a folder walk plus judgement every time: slow, different every time, and
wrong the moment the model gets tired. `life-snapshot.py` measures all six and
renders them. This procedure is the reading of that render. The sorting test in
[[GL-1005-code-vs-instructions|GL-1005]] came back "code" on five of the six.

## 1. [SCRIPT] The prerun found the script; run it

`life-snapshot` is a tool of the content source, not a team script
([[GL-1013-sources-and-the-resolver|GL-1013]]), so it sits beside the team in
mode A and in the sibling ICOR for Life folder in mode B. The generated skill
injects and runs this before step 1, from the folder that holds `AGENTS.md`,
in any mode:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool life-snapshot
```

It prints one absolute path and runs nothing. Run that path with your shell
tool, same folder:

```
python3 "<the path it printed>" --write --brief
```

A prerun that printed an `E_` code instead of a path means no tool is in
reach: that is the missing-report answer of step 4.

The snapshot script writes `concept:life_state/snapshot.json`, under the content source's
root (the machine layer,
[[GL-1008-the-machine-layer|GL-1008]]: per device, regenerated, never tracked
and never shipped) and prints about sixteen lines. The same brief is printed at
every session start by `Scripts/session-start.py`. If it is already in context
and fresh, do not run the script again.

## 2. [SCRIPT] Read the state line before anything else

| What the file says | What you say first, in one line |
|---|---|
| fresh, no degraded rows | nothing extra. Answer. |
| `stale` | `Snapshot is from <date time>; run life-snapshot.py --write for a fresh one.` Then answer from it. Never present stale as fresh. |
| a `Degraded` row touching the question asked | answer what is there and name the empty source using that row's `effect` text. |
| no snapshot, unreadable, or `schema` is not 1 | the missing-file answer in step 4. |

## 3. [SCRIPT] One question, one field

Read it out in plain words. Do not re-rank, do not drop entries, do not improve
an order: the order rules are in the file.

| Question | Field in `snapshot.json` |
|---|---|
| what are my goals | `goals.open` |
| what should I focus on | `projects.focus`, then `projects.active_count` |
| weekly priorities | `weekly_goals.items`, with `done` per item |
| highlight of today | `highlight.text` and `highlight.done` |
| my key elements | `key_elements` |
| what am I paying attention to | `topics.hot`, with each score |

Two pieces of context belong with the attention answer every time it is given:
the window is 30 days, and the score weights each dated link by how recent it
is. A raw number with no unit invites the member to read it as a percentage.

Never quote file modification time as attention. A bulk edit, a sync client or
a migration rewrites hundreds of files in one second, and every one of them
then looks like it just had the member's attention. The script does not count
it and neither do you.

## 4. [SCRIPT] The missing-report answer, verbatim

```
No life snapshot on this device yet. Run: python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool life-snapshot, then python3 "<the path it printed>" --write (on Windows: py -3 "06 AI Team\AI Team Knowledge\Scripts\resolve.py" --tool life-snapshot, then py -3 "<the path it printed>" --write). Until then I would have to read the folders, which is slower and less reliable; say the word and I will.
```

An absent file means the script did not run. It never means the life is empty.
That is [[GL-1008-the-machine-layer|GL-1008]]'s missing-file rule applied to
this report, and the gate that watches it is `life-snapshot-missing-report` in
`Scripts/run-red-tests.py`.

## 5. [JUDGEMENT] Proposing a focus rank

Runs only when `projects.focus` is empty, or when the member asks what to focus
on while it is empty.

From `projects.active` (name, its goal and that goal's status,
`planner_open_this_week`, `attention.score`, `days_to_target`), propose at most
three projects for `focus_rank` with one reason each. Ask the member to
confirm. On a yes, write it. **Never write `focus_rank` without the yes.** It is
the member's decision stored as data; the model proposes only into an empty
field.

## 6. [JUDGEMENT] Proposing a retrospective highlight

Runs only when the member asks what the highlight of today WAS and
`highlight.text` is empty.

Read only the paths in `today.journal_entries` and `today.scratchpads`. Propose
one sentence. Ask the member to confirm. On a yes, write it to today's row in
the weekly note. Never write the highlights table from a guess.

## 7. What this procedure does not cover

- **Which goals or topics deserve attention.** A review, not a retrieval
  question, and out of scope here.
- **Re-ranking what the file already ordered.** "Which goal matters most" is a
  fresh judgement question and gets an answer marked as one, beside the list
  rather than instead of it.
- **Fixing the data.** A `Findings` row is reported and routed. This procedure
  never silently corrects a note.

## 8. The gates behind this

Both are named on the `session-start-ritual` row in `hooks-rules.json` (the team's Scripts folder)
and both were watched go red before they were trusted:

- `life-snapshot-fixtures`: the content source's fixture suite, the
  `test-life-snapshot` tool (path: `python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool test-life-snapshot`),
  passes, and its own `--break-me` proves it can still fail.
- `life-snapshot-missing-report`: with `snapshot.json` and the script gone, the
  session start ritual prints the step 4 line and prints no goal list beside it.

**What a green run does not prove:** that the model obeyed step 4. The script
prints the line; reading it instead of answering from memory is judgement, and
no gate here checks judgement.
