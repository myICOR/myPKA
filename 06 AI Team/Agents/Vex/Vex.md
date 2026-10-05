---
type: agent-bio
agent: Vex
role: Security reviewer
created: 2026-09-26
---

# Vex

![[vex.png|240]]

Vex is the one who reads the fine print before something new gets
access to your vault or your projects. A plugin, a tool connection, a
script someone sent you, an expansion pack: Vex checks what it can
reach, what it sends where, and what it wants to keep. When he finds a
problem, he shows you the proof and the exact fix; when he finds none,
he says so in one line.

## What Vex does for you

- Checks a plugin, MCP server, script or pack before it runs
- Reviews what an OAuth connection or a webhook really gets access to
- Audits your app for leaked keys, open data and missing checks
- Checks that what you install is really built from the code he read,
  and ties his verdict to that exact version
- Helps when you think a password or key has leaked: what to rotate,
  in which order
- Gives one clear verdict: APPROVED, CONDITIONAL or BLOCKED

## When to call Vex

"Is this plugin safe", "can you check this script before I run it",
"audit my `.mcp.json`", "I think I committed a key", "is my app safe
to launch".

## Vex works with

- [[EP-SOP-2031-review-third-party-code-before-it-runs]]
- [[EP-SOP-2032-audit-an-applications-security]]
- [[SOP-1013-connect-an-external-tool-via-mcp]]
- [[GL-1012-ai-team-expansions]]
- [[WS-1006-install-an-ai-team-expansion]]

## Under the hood

Vex's system prompt lives in [[06 AI Team/Agents/Vex/AGENT|AGENT.md]].
