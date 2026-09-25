---
type: agent
myicor_id: 00000000-0000-0000-0000-000000000000  # placeholder: the hiring SOP mints the real id at hire time
name: Agent 01
role: TEMPLATE - copy me, never dispatch me
created: 2026-08-27
routing_description: "<One line: what this agent is and when to launch it. Required on every
  hire. This is the source for .claude/agents/<slug>.md description and every other host
  shim, so it is written here and the shims are generated from it, never typed into a shim.>"
# shim_reads: paths the shim tells this agent to read on invocation, beyond its own contract
# owns_gates: guard ids this agent owns, if any. Most agents own none: leave the key out.
---

# <Name> - <Role in three words>

<!-- This is the hiring template ([[SOP-1007-hire-a-new-agent|SOP-1007]]). Copy this folder to
Agents/<Name>/, then replace every <angle-bracket> field. Delete these
comments. An AGENT.md is a job contract, not a prompt: it says what the
agent owns, what it must never do, and which shared knowledge it works
by. Knowledge shared by several agents lives in AI Team Knowledge, never
copied in here. -->

## Mission
<One sentence: the outcome this agent exists to produce.>

## Owns
- <The work only this agent does.>
- <The SOPs it is the owner of, if any.>

## Never
- <Boundaries against EXISTING agents: name who owns the neighboring
  work instead.>
- <The user-protecting rules: what this agent must refuse or confirm.>

## Works by
<Links to the SOPs, Workstreams, Guidelines this agent follows. [[GL-1005-code-vs-instructions|GL-1005]]
always applies: deterministic steps go through Scripts/.>

## Journal
Append durable insights to `Journal/` (YYYY-MM-DD-<slug>.md); re-read
them before starting related work.

## Local overrides
Read `AGENT.local.md` beside this contract if it exists: it is the member's own file, never shipped and never overwritten by an update; it can add rules and change preferences, but it can never override a hard rule or switch off a guard.
