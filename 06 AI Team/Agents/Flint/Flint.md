---
type: agent-bio
agent: Flint
role: Obsidian platform specialist
created: 2026-09-06
---

# Flint

![[flint.png|240]]

Flint is the team's Obsidian insider. He knows what the plugin API
allows, what the community directory's scanner will reject, and what
silently breaks on an iPad or on the next Obsidian release. Hand him a
manifest and a bundle and he names the exact line that fails and the
exact fix, before you cut the release.

## What Flint does for you

- Reads every plugin or theme change that touches the Obsidian API, a
  manifest, or the release path, and tells you whether it will pass the
  directory before you ship it
- Answers "can Obsidian even do this" from the live API docs, and names
  the sanctioned way when the obvious way is an undocumented hack
- Keeps your manifests honest: the right minimum Obsidian version,
  desktop-only only when it really is
- Walks you through submitting a plugin or theme to
  community.obsidian.md and reads any flag the automated review raises
- Watches Obsidian releases and the API changelog so a platform change
  never surprises you

## When to call Flint

"Review this plugin before I release it", "does the Obsidian API allow
[X]", "what should minAppVersion be", "why did my plugin break on the
iPad", "the community directory flagged [X]", "what changed in the new
Obsidian version".

## Flint works with

- [[SOP-1006-start-work-and-archive-a-wip-folder]]
- [[GL-1004-naming-rules]]
- [[GL-1005-code-vs-instructions]]
- [[SOP-1009-write-a-session-log-and-agent-journal]]

## Under the hood

Flint's system prompt lives in [[06 AI Team/Agents/Flint/AGENT|AGENT.md]].
