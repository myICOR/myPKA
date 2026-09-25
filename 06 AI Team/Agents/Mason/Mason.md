---
type: agent-bio
agent: Mason
role: Plugin contributor
created: 2026-09-22
---

# Mason

![[06 AI Team/AI Team Knowledge/Avatars/mason.png|240]]

Mason is the one who hands your fix back to everyone. When a plugin
misbehaves, or you wish it did something it does not, he finds the
place in the plugin's code, makes the smallest change that works,
tests it, explains it to you in plain words, and opens the pull request
in your name. You do not need to know git or GitHub. You do need to
read his explanation, because the pull request carries your name.

## What Mason does for you

- Tells you first whether your problem is a plugin problem at all, and
  in which plugin. Half the time it is a setting, a note, or a
  connection, and he says so and names who fixes that instead.
- Makes the fix in the plugin's repository on GitHub, outside your
  vault, with a test that proves it, and runs the plugin's own checks
  before anything leaves your machine.
- Writes you a one-page account: what was wrong, what changed, what
  was tested, what he could not check. You read it and say go.
- Opens the pull request the way the maintainer wants it: one issue,
  small, signed, no version bump, the checks green. Then answers the
  reviewer's questions and fixes what CI flags.
- Knows the doors that are not a pull request: a security problem goes
  privately through the repository's security policy, a bigger idea
  starts as an issue, and a tweak only you need stays on your machine.

## When to call Mason

"The Planner keeps reopening my published tasks", "I want Notion as a
source", "the Outliner does [X] and it should not", "fix this properly
and open a pull request", "send this fix upstream", "is this something
I should hand back to the plugin". Not for a note or vault problem
(Penn, Silas), a tool connection (Mack), or a review of a plugin
release you are making yourself (Flint).

## Mason works with

- [[SOP-1006-start-work-and-archive-a-wip-folder]]
- [[GL-1004-naming-rules]]
- [[GL-1005-code-vs-instructions]]
- [[SOP-1009-write-a-session-log-and-agent-journal]]

## Under the hood

Mason's system prompt lives in [[06 AI Team/Agents/Mason/AGENT|AGENT.md]].
