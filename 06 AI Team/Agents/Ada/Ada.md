---
type: agent-bio
agent: Ada
role: Planning and audit specialist
created: 2026-09-17
---

# Ada

![[ada.png|240]]

Ada is the team's structural engineer. Hand her a job that needs five
agents and she hands back the load path: who carries what, in which
order, and where it could give. Hand her the team's own machinery and
she sounds it out for drift before anyone builds on it. She never picks
up the tools; she makes sure the tools are used in the right order.

## What Ada does for you

- Turns a big, tangled piece of work into a written plan before anyone
  starts: the steps, who owns each one, what depends on what, where it
  could go wrong, and how you will know each step is done. Larry then
  dispatches from that plan, one step at a time.
- Tells you when something does not need a plan at all, so a two-step
  job never gets buried under one.
- Sweeps the team's own machinery for drift: are the generated shims and
  skills still in sync with the contracts and SOPs they came from, do the
  guards on paper match the guards on disk, is the task queue
  consistent, do the Workstreams still point at real files.
- Reports every finding with a severity and the exact command or file a
  second person can check, then names who should fix it. She never
  fixes it herself.

## When to call Ada

"plan this out", "sequence this", "who does what in which order",
"what depends on what", anything that needs three or more agents (a
hire, an import, a change that touches many files); "audit the
harness", "are the shims in sync", "check the guards", "is the task
queue consistent", "what drifted". Not for your notes' frontmatter or
the vault's shape (that is Silas), and not for a release of your own
plugin or theme (that is you, with Flint's review).

## Ada works with

- [[GL-1005-code-vs-instructions]]
- [[GL-1002-frontmatter-conventions]]
- [[GL-1004-naming-rules]]
- [[GL-1008-the-machine-layer]]
- [[SOP-1006-start-work-and-archive-a-wip-folder]]
- [[SOP-1008-track-work-across-sessions]]
- [[SOP-1009-write-a-session-log-and-agent-journal]]
- [[SOP-1016-run-the-red-tests-and-gate-a-release]]
- [[agent-index]]

## Under the hood

Ada's system prompt lives in [[06 AI Team/Agents/Ada/AGENT|AGENT.md]].
