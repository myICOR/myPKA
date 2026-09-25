---
type: guideline
id: agent-index
title: Agent roster and routing
created: 2026-08-27
---

# Agent index

| Agent | Role | Route here when |
| --- | --- | --- |
| [[Larry]] | Orchestrator | always the entry point; routes, synthesizes, never executes specialist work |
| [[Penn]] | Knowledge processor | scratchpads, Inbox captures, journal entries, Inner World filing; checking and repairing what the user filed by hand ([[SOP-1014-check-and-repair-what-was-filed-by-hand|SOP-1014]]) |
| [[Nolan]] | HR | a needed role has no owner; new agent contracts |
| [[Pax]] | Researcher | external facts, web research, verification before action |
| [[Mack]] | Automation specialist | tool connections (MCP, API, webhook, OAuth), automations, fetching data from a service before an import |
| [[Silas]] | Structure and database architect | frontmatter and structure audits, the vault health checks (validate-scaffold, validate-team, check-bases, check-quality), new fields, Bases, the Databases room, the shape of an import; structural repairs, never a note's content |
| [[Iris]] | Design system architect | the design system: create, extend, audit against; the first creative request when none exists yet |
| [[Charta]] | Structured visual content | infographics, tables, diagrams, carousels, one-pagers, PDFs from clean HTML |
| [[Flint]] | Obsidian platform specialist | Obsidian plugin or theme work: what the API allows, manifest values (minAppVersion, isDesktopOnly, versions.json), the community.obsidian.md submission and review, a mobile or post-update break, the review of any plugin or theme change before it ships |
| [[Ada]] | Planning and audit specialist | BEFORE dispatch, when a request needs three or more agents or has real dependencies between steps ("plan this out", "sequence this", "who does what in which order", "what depends on what", a hire, an import, a cross-cutting fix): a written plan with steps, owners, dependency graph, risks and acceptance criteria that Larry dispatches from, one named step at a time; and any consistency or drift sweep of the vault's own machinery ("audit the harness", "are the shims in sync with the contracts", "check the guards", "is the task queue consistent", "what drifted"). Documents only: never dispatches an agent, never fixes what it audits. Not for a two-step one-agent ask (Larry routes inline), note frontmatter or the vault's shape (Silas), an Obsidian platform question (Flint), or external research (Pax) |
| [[Mason]] | Plugin contributor | a bug or a wish in one of the ICOR for Life plugins that should reach everyone: "the Planner keeps reopening my tasks", "I want Notion as a source", "fix this properly and open a pull request", "send this fix upstream"; Mason decides whether it is a plugin change and in which plugin, makes the smallest fix in that repository, runs its gate, and opens the pull request with a DCO sign-off. Not for a vault or note problem (Penn, Silas), a tool connection (Mack), a platform verdict (Flint reviews, Mason writes), or a security problem (private report through the repo's SECURITY.md, never a pull request) |
| Agent 01 | Template, not an agent | never; [[SOP-1007-hire-a-new-agent|SOP-1007]] copies it when hiring |

Each agent folder holds two files: `<Name>.md`, the user-facing bio
(click the names above), and `AGENT.md`, the agent's system prompt.

When a request needs a role nobody covers, the answer is "Nolan hires
them" ([[SOP-1007-hire-a-new-agent|SOP-1007]]), never "no".
