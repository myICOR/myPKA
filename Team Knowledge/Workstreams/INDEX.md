# Workstreams - Index

**Workstreams are multi-agent compositions.** A Workstream describes how more than one specialist (often plus the user) collaborates to deliver a recurring outcome. Where an SOP is a single-agent skill, a Workstream is the choreography that strings skills together — think of Workstreams the way Claude plugins compose skills into a flow.

Workstreams are **emergent**. The scaffold ships only the canonical flows that need to work on day one (daily journaling, external knowledge import). New Workstreams get authored by the team when a multi-agent pattern repeats — Larry detects the pattern across session-logs and proposes the Workstream to the user.

Workstreams reference SOPs and Guidelines via `[[wikilinks]]`. They never duplicate the steps or rules those files contain.

Filename pattern: `WS-NNN-<title>.md`. See [[GL-001-file-naming-conventions]] for slug rules.

## Active Workstreams

| WS | Title | Owners | Description |
|---|---|---|---|
| WS-001 | [[WS-001-daily-journaling]] | Penn + Larry | How daily inputs (text, image, audio) flow into Journal, Images, and CRM. References [[SOP-001-how-to-add-a-new-specialist]] and [[GL-001-file-naming-conventions]]. |
| WS-002 | [[WS-002-import-external-knowledge-base]] | Silas (primary executor) + Mack (connection-half when source needs OAuth/API/MCP) + Pax (research for unfamiliar formats) | How an existing knowledge base (Heptabase, Notion, Obsidian, Roam, Logseq, Mem, Capacities, Apple Notes, Evernote, Tana via MCP, etc.) gets imported into your myPKA. Triggered by natural-language phrases (see root `AGENTS.md`). References [[GL-001-file-naming-conventions]], [[GL-002-frontmatter-conventions]], [[SOP-002-convert-mypka-to-sqlite]]. |
| WS-003 | [[WS-003-install-an-expansion]] | Larry (orchestrator) + Vex (security gate — route to Vex if installed, e.g. via the App Developer Pack; otherwise Larry executes the §2 security checklist himself before any install) + Nolan (team merge) + Mack (connector wiring) + Silas (integrity check) | How an Expansion folder dropped into `Expansions/` gets validated, security-reviewed, merged into the user's team (agents, SOPs, guidelines, templates), wired (env vars, MCP servers, runtimes), validated, and announced. Symmetric uninstall flow. References `Expansions/docs/expansion-spec.md`, [[GL-001-file-naming-conventions]], [[GL-002-frontmatter-conventions]], [[SOP-001-how-to-add-a-new-specialist]]. |
| WS-004 | [[WS-004-team-retro-and-self-improvement-loop]] | Larry (orchestrator) + every specialist (capture + propose) + named implementers + Silas (regen) + the user (gate) | The human-gated three-tier self-improvement loop: Tier 0 autonomous in-session journal capture, Tier 1 in-session proposal written to `tasks/open/` (folded into close-session), Tier 2 on-demand Team Retro mining all `Team/*/journal/` + `session-logs/` into a ranked proposal doc in `Deliverables/`. Hard invariant: the team proposes, it never self-rewrites the framework. References [[GL-005-llm-agnostic-portable-core]], [[GL-001-file-naming-conventions]], [[SOP-create-task]], [[SOP-close-task]], [[SOP-002-convert-mypka-to-sqlite]]. |

## When to write a new Workstream

- More than one specialist is involved.
- The activity recurs on a schedule or on a recurring trigger.
- The choreography (who hands off to whom) matters as much as the steps.

If only one specialist is involved, write an SOP instead — single-agent procedures are skills, not workstreams.
If the rule is static and never executed, write a Guideline instead.
If a multi-agent handoff (say, Mack fetching bytes that Silas then imports, or any other recurring pattern) repeats often enough to need codifying, that's the moment to author a new Workstream — not before.
