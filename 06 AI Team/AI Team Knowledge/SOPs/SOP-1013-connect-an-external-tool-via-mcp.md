---
type: sop
id: SOP-1013
title: Connect an external tool via MCP
created: 2026-08-28
owner: pax
uses: ["[[GL-1005-code-vs-instructions]]"]
---

# SOP-1013 Connect an external tool via MCP

Gives the team live access to the user's real tools (email, calendar,
task manager, project management). Research by Pax, approval by the
user, wiring by code, run by Mack.

1. [JUDGEMENT] The user names the tool (from the [[WS-1003-onboarding-first-launch|WS-1003]] interview or
   any time later). Larry routes to Pax.
2. **Pax researches the integration.** Hard constraint: **only
   official MCP servers, provided by the tool's own developer.**
   Community or third-party MCP servers are reported as existing but
   NOT offered for install; an unofficial server touching the user's
   email or calendar is an attack surface, not a convenience. Pax
   verifies: publisher identity, official docs URL, auth method (API
   key, OAuth), data scope, and returns a short brief with sources.
   No official server: Pax says so, and the tool stays linked-only
   (URLs in project notes) until the vendor ships one.
3. [JUDGEMENT] The user approves the connection per tool, seeing what
   data the server can reach.
4. [SCRIPT] Mack runs `Scripts/add-mcp-server.py`, which writes the
   `.mcp.json` entry
   and the `.env` placeholder. The script refuses secret-shaped
   values in the config: secrets live ONLY in `.env`, referenced as
   `${VAR}`.
5. **The user fills the key into `.env` themselves, in a text
   editor.** Agents never ask for a key in chat, never echo `.env`
   contents, and never write key values into notes, session logs, or
   manifests.
6. Mack restarts the AI runtime, verifies the server lists its tools,
   and records the connection (tool, server, scopes; never the key) in the
   session log.
