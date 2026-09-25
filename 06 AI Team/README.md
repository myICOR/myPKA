# AI Team

The staff quarters: everything the AI needs to operate the other five
rooms, cleanly separated from your knowledge.

- `Agents/` - one folder per agent: its `AGENT.md` contract and its
  `Journal/` of durable insights. `agent-index.md` is the roster.
- `AI Team Knowledge/` - shared operational know-how:
  - `SOPs/` - atomic procedures
  - `Workstreams/` - multi-step orchestrations (see "A Workstream is not
    a Project" below)
  - `Guidelines/` - static rules and reference
  - `Scripts/` - the deterministic half of the SOPs (code, not prose)
  - `Skills/` - the canonical home for generated skills, one folder per
    skill; the host folders hold links into it
  - `Avatars/` - the agents' profile images, embedded in their bios
  - `Tasks/` - cross-session work continuity (open, in-progress, done,
    cancelled)
  - `Session Logs/` - append-only record of every session, the team's
    long-term memory
- `AI Sessions/` - the record of your conversations with the team: one
  folder per conversation, transcripts kept with their session ids.
- `Expansions/` - optional packs that add capabilities to the AI Team;
  see [[GL-1012-ai-team-expansions]] and
  [[WS-1006-install-an-ai-team-expansion]].

Knowledge lives OUTSIDE the agents so several agents can share one
procedure. The operating law: code for anything a machine could check,
instructions only for judgement ([[GL-1005-code-vs-instructions|GL-1005]]).

## A Workstream is not a Project

A Project is bounded and ends: it has a finish line, its note in
`concept:projects` reaches `done`, and its working files
live in `concept:wip/projects/<name>/` until then. A Workstream is a
repeatable process that never ends: the same choreography run again and
again (the daily processing run, the weekly review, a video made every
week), one result per run, no finish line. A Workstream can carry a
Goal the way a Project can, through the results it keeps producing
(`workstreams` on the goal, [[GL-1002-frontmatter-conventions|GL-1002]]),
and when it runs continuously it keeps its running state in a standing
folder `concept:wip/workstreams/<Name>/` named in its `wip_folder`. The test
when filing: is this one run of something that repeats, or a step
toward a finish line? Work on the team itself is neither, and has its
own bucket, `concept:wip/ai_team/`. The four buckets, the order they are read
in and a worked example each: the WiP room's `README.md` (`concept:wip/README.md`).

## Authoring rules

- **Every Workstream MUST contain at least one mermaid diagram** of
  its process steps, placed after the intro so the shape of the run
  is visible before the prose. The diagram represents the steps as
  written; it never invents steps.
- SOPs and Guidelines stay prose-first; the diagram rule binds
  Workstreams.
- **How to author a mermaid diagram so it stays INKLINE** (Iris's
  rules, final):
  1. Flowchart TD or LR for processes, sequenceDiagram for handoffs
     between people or agents. Any other diagram type needs a theme
     check before first use.
  2. Few nodes, real names: 5 to 9 nodes per diagram, every node
     labeled in brackets (`triage["Triage"]`). Single-letter ids never
     appear as visible text.
  3. The theme owns the look. No inline style directives, no classDef
     colors, no `%%{init}%%` theme blocks in the mermaid source. Ever.
  4. One accent per diagram: mark exactly one node `:::start` (the
     entry point) or `:::mark` (the one thing to see). Never two. The
     theme renders it as the marker; you only name it.
  5. Quote every label that carries special characters:
     `x["Actionable?"]`, edge labels as `-->|yes|` and `-->|no|`.
  6. A flow wider than about 9 nodes splits into two diagrams instead
     of one long chain. The theme shrinks wide diagrams to fit, and
     past that width the labels stop being readable.
  7. In sequence diagrams, use activate/deactivate for the working
     party (the theme washes it in marker) and `Note over` for margin
     commentary (the theme sets it in handwriting).

## Learn the concept

The AI Team is ICOR's automation layer: everything repeatable handed to
a system, judgement kept where it belongs.
From [Automation like a Pro](https://app.myicor.com/courses/automation):

- [Process, Workflow, Workstream, Procedure, and SOP](https://app.myicor.com/lessons/process-workflow-workstream-procedure-and-sop-52) -
  the exact vocabulary of the AI Team Knowledge folder
- [The Right Approach to Automation](https://app.myicor.com/lessons/the-right-approach-to-automation-49) -
  what to hand to the system and what to keep
- [How to Map Your Business Processes](https://app.myicor.com/lessons/how-to-map-your-business-processes-699) -
  turning your own routines into SOPs and Workstreams
- [The Concept of Single Source Of Truth (SSOT) in ICOR](https://app.myicor.com/lessons/the-concept-of-single-source-of-truth-ssot-in-icor-696) -
  why knowledge lives once, outside the agents
