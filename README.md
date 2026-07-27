<!--
myPKA Scaffold - © 2026 Paperless Movement®, S.L.
Licensed under the terms in LICENSE. Per-subtree map: LICENSE-MAP.md
ICOR® and Paperless Movement® are registered trademarks. See NOTICE.md
-->

# myPKA

**An AI powered Personal Knowledge Assistance system, based on our business-proven ICOR methodology. Plain markdown. Any LLM. Yours forever.**

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](LICENSE)
![Version](https://img.shields.io/badge/version-5.3.0-blue)
![Built on ICOR](https://img.shields.io/badge/built%20on-ICOR-C99A57)

myPKA is a folder. You drop it on your machine, point your LLM at it, and you have a **six-specialist AI team** that organizes your life end to end. **It works on its own.** No database to set up, no SaaS to log into, no vendor to lose your data to.

This scaffold is the **basic structure you need to build your own AI team**: the core agents everyone needs (**Larry, Nolan, Pax, Penn, Mack, Silas**), the folder architecture they operate on, the contracts that hold it all together, and the **myPKA Cockpit**: a local, navigable, wikilink-aware interface over your whole scaffold, included and free. It is free, and it stays free. From here you can build whatever you like on top: hire your own specialists through Nolan, or add ready-made **Expansion Packs** (the Designer Pack, the App Developer Pack, and more), which are part of the **myICOR membership** and install from the Expansion Packs page in the myICOR app. See [Expansion Packs (membership)](#expansion-packs-membership) below.

**Watch on YouTube** (newest first):

[![My AI Team Now Has an Interface. All 12 Agents. One Folder.](github/youtube/launch-thumbnail.png)](https://www.youtube.com/watch?v=FwPlAQeJcXI)

- **[My AI Team Now Has an Interface. All 12 Agents. One Folder.](https://www.youtube.com/watch?v=FwPlAQeJcXI)** — the Cockpit launch
- **[Claude just killed ALL Note-Taking, Planner, and Health Apps. Here is proof.](https://www.youtube.com/watch?v=5ZgvLBxDqyI)** — the Cockpit reveal
- **[One Life. One Folder.](https://www.youtube.com/watch?v=51ZVWAjHurI)**

> **Why this is different from other scaffolds.** Most folder structures are someone's preference dressed up as a system. myPKA is the working slice of **ICOR**, a methodology Paperless Movement S.L. and thousands of professionals world wide have been running their own business on for years. Every folder, every routing decision, every specialist contract maps to a piece of that framework. The structure is not arbitrary. The reasoning is teachable. Both matter when you scale past the first week.

## What's new in v5.0.0

**The scaffold returns to its basic shape: the six core specialists plus the myPKA Cockpit, free forever.** Earlier downloads also bundled two agent packs into this repo. Those now live where the rest of the growing pack library lives: on the **Expansion Packs page of the myICOR app**, as part of the myICOR membership.

What this means in practice:

- **This repo ships the base team**: Larry, Nolan, Pax, Penn, Mack, Silas, with their contracts, SOPs, Workstreams, and Guidelines. Everything you need to run your knowledge, your journal, your CRM, and your tasks with an AI team. Nothing about the scaffold went paid.
- **The myPKA Cockpit stays included and free**, preinstalled at `Expansions/mypka-cockpit/`. A local, navigable, wikilink-aware viewer over your whole scaffold (reads the SQLite mirror read-only). It runs entirely on your machine, uses **your own Claude key**, and never sends your data anywhere. No auto-launch — you generate a one-click launcher and start it yourself.
- **The Expansion mechanism stays built in.** `Expansions/`, the install Workstream ([[WS-003-install-an-expansion]]), and the authoring spec (`Expansions/docs/expansion-spec.md`) all remain, so any pack you download (or write yourself) drops in cleanly.
- **The Designer Pack (Iris, Charta, Pixel) and the App Developer Pack (Felix, Vex, Vera)** are available with the myICOR membership on the Expansion Packs page, alongside new packs as they release.
- **Why it's a MAJOR bump.** The default download's team roster and SOP/Guideline set change shape versus the previous bundled download. If you already run a bundled folder, nothing is taken away from you: your installed packs are your state, they keep working, and they update through their own Expansion update paths.

Everything else carries forward: the task system, per-agent journals, the four-buckets-plus-Goals My Life doctrine, local version history, the self-updater, and the LLM-readable migration changelog. Plain markdown, any LLM, yours forever.

## Get going now

1. Clone or download the repo into a folder you'll actually use.
2. Open the folder in your LLM tool (Claude Code, Codex CLI, Gemini CLI, Cursor, or Obsidian + chat plugin).
3. As your first message, say: **"Read `ADAPTER-PROMPT.md` and follow it to set yourself up."** (This is the reliable bootstrap on every tool — and the fallback if a bare `/init` ever overwrites the shipped `CLAUDE.md` with a generic summary.)
4. The LLM reads `ADAPTER-PROMPT.md`, personalizes the folder, writes a tool-specific pointer file (`CLAUDE.md`, `GEMINI.md`, etc.), **builds the Cockpit dashboard so it's ready to launch**, and reports the team is online. It will ask once for your first name and one "proceed?" consent — everything runs and stays on your machine, nothing is uploaded. When it finishes, double-click the generated launcher in `Expansions/mypka-cockpit/` to open the Cockpit.
5. Ask "Who are you?" and you'll see Larry is at your service.
6. Ask "What's open?" and Larry walks the new `Team Knowledge/tasks/open/` folder for you.

That's the whole setup. There is no install step.

Once you have the team online and start using it, you'll hit moments where you wonder why a folder is shaped the way it is. That's where the courses come in. They teach the WHY behind every folder choice, so you understand why the team is built like real humans operating on the **ICOR methodology**, not just another AI scaffold. More on that below.

## What you get

A working knowledge system, fully assembled, that does this on day one:

- **Organizes your life from a single daily journal.** You write what happened. The team files the people, projects, decisions, and ideas where they belong. Connections between notes are made for you.
- **Remembers unfinished work for you.** When something can't finish in one turn, the team writes it down as a task in `Team Knowledge/tasks/`. Next session, Larry walks `tasks/open/` and surfaces what's waiting. The team genuinely picks up where it left off.
- **Carries learning forward.** Each specialist keeps a journal of durable insights at `Team/<Name>/journal/`. When a task references one of their entries, they re-read their own past thinking before starting work.
- **Runs in any LLM you already use.** Claude Code (and Claude Cowork), Codex CLI, Gemini CLI, Cursor, ChatGPT, Obsidian with a chat plugin. The same scaffold, the same team, the same files. You change models. Your knowledge doesn't move. Session-log triggers (`close session`, `keep this in mind`, `let's realign`, etc.) work with any LLM that reads `AGENTS.md` — ChatGPT, Claude, Gemini, Cursor, Cline, Codex, and the rest. Not Claude-only.
- **Stays in plain markdown.** Every note is a `.md` file. You can read it without the AI. You can grep it. You can sync it with Dropbox or git. You can open it in Obsidian and keep working with no AI at all.
- **Upgrades to SQLite when you outgrow plain files.** Once your myPKA gets large, paste the prompt at `Team Knowledge/SOPs/SOP-002-convert-mypka-to-sqlite.md` into your LLM. Markdown stays canonical. SQLite becomes a fast lookup layer on top.
- **Imports from any PKM tool.** Drop your existing notes (Heptabase backup, Notion export, Obsidian vault, Roam graph, Logseq folder, Apple Notes export, Evernote dump, Tana via MCP, etc.) anywhere on disk, then ask your LLM something like *"import my Notion export from `~/Downloads/notion.zip`"* or *"how do I bring in my Heptabase backup?"*. The scaffold ships with [[Team Knowledge/Workstreams/WS-002-import-external-knowledge-base]] — the LLM follows it to extract entities (people, organizations, projects, goals, habits, topics, key elements, documents), normalize wikilinks to the slug form, copy attachments into `PKM/Images/YYYY/MM/`, and place files into the right folders, asking clarifying questions where needed and never overwriting your myPKA without explicit approval. Works with any LLM that reads `AGENTS.md`.

There is no lock-in. The whole system is text on your disk. It works in Obsidian today. It upgrades to SQLite when you want it. It runs on whichever model or LLM you prefer, and it keeps running when you switch.

## Who this is for

- **Knowledge workers** who want a local folder setup instead of handing over their knowledge to Notion, Tana etc. and want an AI team that actually files things. Transparent and accessible.
- **Founders and operators** running multiple projects who need a knowledge system that thinks across People, Topics, Goals, Habits, and Key Elements without manual cross-linking.
- **Parents and generalists** with too many inputs (school stuff, health stuff, ideas, contacts) and no structure to hold it.
- **AI tinkerers** who want a real reference architecture for a multi-agent setup, not a toy demo.

If you've ever opened a blank Obsidian vault and didn't know where to put anything, this is for you. (Yes — myPKA is fully Obsidian-compatible. Open the folder as an Obsidian vault and everything just works.)

## Meet the team

**Six specialists ship pre-loaded.** These are the core agents everyone needs. **You only ever talk to Larry.** Larry routes.

<table>
<tr>
<td width="140" align="center"><img src="github/team/larry.png" width="120" alt="Larry the Red Fox - Team Leader and Orchestrator" /></td>
<td><b>Larry - Team Leader & Orchestrator</b><br/><i>A Red Fox. Sharp ears, sharper instincts.</i><br/><br/>Every request you make lands with Larry first. He clarifies, picks the right specialist, hands off the brief, and synthesizes the answer back to you. He's also the team's <b>Librarian</b> (keeps the wiki clean, fixes broken <code>[[wikilinks]]</code>, enforces the SSOT Golden Rule), <b>Session-Log Author</b> (writes a daily log of what the team did and what changed), and the team's <b>Task Walker</b> (surfaces what's open at session start). Larry never executes specialist work himself - that's the iron rule.</td>
</tr>
<tr>
<td width="140" align="center"><img src="github/team/nolan.png" width="120" alt="Nolan the Pitbull - Talent Acquisition" /></td>
<td><b>Nolan - Talent Acquisition</b><br/><i>A Pitbull in glasses. Loyal, methodical, allergic to lazy hires.</i><br/><br/>When you outgrow the six shipped specialists, Nolan handles the hire end-to-end: briefs Pax for research, drafts the new specialist's contract (<code>AGENTS.md</code>), validates against the SOP, and gets your sign-off before adding anyone to the roster. Nolan is the reason your team scales without diluting.</td>
</tr>
<tr>
<td width="140" align="center"><img src="github/team/pax.png" width="120" alt="Pax the Raven - Deep Research" /></td>
<td><b>Pax - Deep Research</b><br/><i>A Raven. Patient, source-cited, allergic to a single-source answer.</i><br/><br/>When something matters - a hire, a market read, a "is this actually true" - Pax goes wide before going deep. Returns a triangulated brief in <code>Deliverables/</code>, never a one-shot opinion.</td>
</tr>
<tr>
<td width="140" align="center"><img src="github/team/penn.png" width="120" alt="Penn the Owl - Journal Writer" /></td>
<td><b>Penn - Journal Writer</b><br/><i>A Barn Owl. Quiet, watchful, careful filer.</i><br/><br/>Penn handles the team's scribe duties. Drop screenshots, voice memos, business cards, or rough thoughts into <code>Team Inbox/</code>. Penn files everything into the right corner of <code>PKM/</code> with the right <code>[[wikilinks]]</code>. He never forgets where things go and never assumes you're done thinking when you drop something in.</td>
</tr>
<tr>
<td width="140" align="center"><img src="github/team/mack.png" width="120" alt="Mack - Automation and Integration Specialist" /></td>
<td><b>Mack - Automation & Integration Specialist</b><br/><i>The connection layer. Quiet when it works, loud when it breaks.</i><br/><br/>Mack wires your myPKA to the rest of the world. MCP server setup, API integrations, webhook receivers, OAuth flows, and any automation that needs to run reliably in the background. When an external knowledge import needs an authenticated fetch first (Notion API, Apple Notes export, a live MCP server), Mack establishes the connection, lands the bytes at a path, and hands off to Silas to run the actual import. Idempotency, retries, structured logs, credentials in <code>.env</code> — never in code.</td>
</tr>
<tr>
<td width="140" align="center"><img src="github/team/silas.png" width="120" alt="Silas - Database Architect" /></td>
<td><b>Silas - Database Architect</b><br/><i>Schema is destiny. Slugs are primary keys.</i><br/><br/>Silas guards the structural integrity of your knowledge base. He runs external knowledge imports (drop a Notion zip, a Heptabase backup, an Obsidian vault, a Roam graph — Silas runs <code>WS-002</code> and lands the entities in the right folders), audits frontmatter against <code>GL-002</code>, catches schema drift before it spreads, and runs the markdown-to-SQLite conversion (<code>SOP-002</code>) when your myPKA outgrows plain files. Markdown stays canonical; the SQLite mirror is a regenerable performance layer. Silas never invents fields, never silently rewrites content, and never lets ad-hoc YAML keys accumulate.</td>
</tr>
</table>

Each specialist has a contract at `Team/<Name> - <Role>/AGENTS.md` and a `journal/` folder for durable insights. Full routing table at `Team/agent-index.md`.

> Want more hands? Grow the team two ways: hire your own specialists through Nolan (the team walks you through it), or add ready-made **Expansion Packs** with the myICOR membership at [myicor.com](https://myicor.com).

## What lives where

- `PKM/` is your knowledge. `My Life/` holds the five life concepts (Goals, Habits, Topics, Projects, Key Elements). `Documents/`, `CRM/`, `Images/`, and `Journal/` sit alongside it. Notes connect through `[[wikilinks]]`, not nested folders.
- `Team/` holds your specialists. One folder per agent. Each has its own `AGENTS.md` and its own `journal/` for durable cross-session insights.
- `Team Knowledge/` holds the team's playbook. SOPs are atomic procedures. Workstreams orchestrate multi-agent flows. Guidelines are static reference info. `tasks/` holds unfinished work the team is tracking across sessions (`open/`, `in-progress/`, `done/<YYYY>/<MM>/`, `cancelled/<YYYY>/<MM>/`).
- `Expansions/` holds add-on packs. The **myPKA Cockpit** ships preinstalled at `Expansions/mypka-cockpit/`; packs you install later land alongside it. See `Expansions/README.md`.
- `Deliverables/` is where the team puts work-in-progress and finished artifacts - research briefs, hire workups, multi-file projects. Time-stamped, ephemeral, the team's working surface. **Pax** drops research here. **Nolan** drops hire workups here. **Larry** collects multi-specialist work here.
- `Team Inbox/` is your drop zone for raw inputs. Drop screenshots, voice memos, business cards, links, or a quick braindump and the team files them into PKM. *"I have something, not sure where"* goes here. **Penn** usually picks it up, **Larry** routes it.
- `AGENTS.md` at the root is the source of truth for how the whole team behaves.

> **Note on note shape.** Every entity note (a Person, an Organization, a Project, a Goal, a Habit, a Topic, a Key Element, a Document) starts from a template in `Team Knowledge/Templates/`. Structured data lives in YAML frontmatter at the top of the file; narrative lives in the body. The canonical field schemas are in [[Team Knowledge/Guidelines/GL-002-frontmatter-conventions]]. The Cockpit's Properties tab and the SQLite migration both read frontmatter — keep your facts there, your stories in the body.

## How a task flows

Here's the whole shape, in plain English.

You ask the team to do something that won't finish in one turn. Larry (or whoever picked up the request) writes a small markdown file into `Team Knowledge/tasks/open/`. The frontmatter names who it's for, why it matters, and what context already exists: which SOP applies, which workstream it belongs to, which session log birthed it, which life entry it touches, which journal entry the assignee should re-read first. The body restates the work in your words.

When the assignee picks it up, the file moves from `open/` to `in-progress/` and they leave a one-line update inside it. They keep working. If they get blocked, they write the reason in the frontmatter so they (or someone else) know what to chase. When it's done, the file moves to `done/<year>/<month>/` with the outcome written in.

Next session, Larry walks `tasks/open/` and `tasks/in-progress/` first, before doing anything else. The team starts the day knowing what's waiting and where things stood. Nothing falls on the floor between sessions.

The journal sits next to this. When the assignee learns something durable while working a task — a build pattern that worked, an anti-pattern they want to remember, a rule of thumb — they write a short entry in their `journal/`. The next time a task references that entry, they re-read their own past thinking before starting. Learning compounds across sessions.

## Principles

A few things we believe, that the folder is shaped around.

- **Continuity over ceremony.** The team should be able to pick up where it left off, across sessions, even when a different specialist takes over. Tasks and journals serve that, nothing else. There is no lifecycle theater.
- **The folder is the database.** Plain markdown, on your disk, readable without the AI. Frontmatter is the machine-readable layer. Wikilinks are the navigation layer. All three reinforce each other so any one of them is enough to act.
- **Portability is the point.** You can swap LLM tools without migrating. You can sync the folder with Dropbox, iCloud, or git. You can open it in Obsidian on your phone. Your knowledge follows you, not the vendor.
- **LLM-agnostic by construction.** Anything the team does, any agent can do, with `mv`, `mkdir`, `grep`, `awk`. No model-specific magic. No proprietary tool calls. If you can read markdown, you can run myPKA.
- **Additive upgrades only.** When the scaffold gains a capability, older folders gain it without losing anything. Migration is plain-text recipes you can audit. Nothing destructive without your explicit OK.

## Coming from another tool?

- **Obsidian users**: open your myPKA folder as an Obsidian vault. Wikilinks, tags, and Markdown work as you expect. The scaffold adds an AI team on top of the folder you already understand.
- **Notion users**: the closest analogue is "Pages with AI inside, but the pages are files on your disk." You lose Notion's database views. You gain ownership of every byte and the ability to swap LLMs without migrating.
- **Roam / Logseq users**: same daily-note instinct. The team handles the cross-linking you used to do by hand.

## The deeper story: ICOR methodology

If you want to really manage your life efficiently and run this folder structure the way it is meant to work, the methodology is the missing layer.

myPKA is built on the **My Life** part of the **ICOR methodology**. ICOR is tool-agnostic Paperless Movement S.L. and thousands of professionals use to run both personal life and business: five life concepts on one side, five business concepts on the other, with a shared way of capturing, processing, and acting on information. We have been running on it for years. The scaffold you just downloaded is one slice of that framework, made operational.

Watch the deep-dive walkthrough where Dr. Thomas Rödl builds the system from scratch and explains the reasoning behind each folder, each agent, and each routing rule:

**[Watch the deep-dive on YouTube](https://www.youtube.com/watch?v=FwPlAQeJcXI)**

The full courses live at **[myicor.com](https://myicor.com)**. They cover:

- **The Personal half (myPKA)**: the WHY behind every folder in this scaffold, how the five life concepts (Goals, Habits, Topics, Projects, Key Elements) connect, and how to operate the team so it actually saves you time instead of becoming another tool to manage.
- **The Business half**: the same framework extended to companies, including the operating system Paperless Movement S.L. runs on internally.

The scaffold works on its own. The course is for people who want to understand why it works, so they can extend it without breaking the model.

## Expansion Packs (membership)

The scaffold you are looking at is genuinely complete: six core specialists, the full folder architecture, the myPKA Cockpit interface, and the built-in Expansion mechanism. **Expansion Packs** are how the team grows beyond it, and they are part of the **myICOR membership**. Members download them from the **Expansion Packs page** inside the myICOR app ([myicor.com](https://myicor.com)); each pack drops into your `Expansions/` folder and installs via the built-in [[WS-003-install-an-expansion]] flow, with integrity hashes shown on the Expansion Packs page at download time. Available packs include:

- **Designer Pack**: adds Iris (Design System Architect), Charta (Infographic Designer), and Pixel (Visual Specialist), plus their SOPs and the design-system Guideline.
- **App Developer Pack**: adds Felix (Frontend Developer), Vex (Security Engineer), and Vera (QA Specialist), plus their SOPs.
- **More packs on a published cadence**: connector Expansions for the tools you already live in, Obsidian optimizations tuned to the scaffold, and further agent packs (Marketing, Customer Support, Bookkeeping, and others).

Membership also includes office hours and walkthroughs with the team that builds this scaffold. Membership-gated is honest, not a bait: the scaffold here stays free and complete, and you can always build your own packs with `Expansions/docs/expansion-spec.md`. The membership is for people running serious work on top of it.

## License and trademarks

> **Built on the myPKA™ Scaffold by Paperless Movement® / ICOR®.**
> Source: https://github.com/myICOR/myPKA
> Licensed under CC BY-SA 4.0. See [`LICENSE`](LICENSE), [`NOTICE.md`](NOTICE.md), [`TRADEMARK.md`](TRADEMARK.md), and [`LICENSE-MAP.md`](LICENSE-MAP.md).

- **Content and code**: [CC BY-SA 4.0](LICENSE). Free to use for any purpose, including commercially and inside your own business, with attribution and share-alike. Per-subtree license boundaries (base scaffold and the bundled Cockpit) are mapped in [`LICENSE-MAP.md`](LICENSE-MAP.md); Expansion Packs installed from the myICOR app carry their own licenses.
- **Registered trademarks (US)**:
  - PAPERLESS MOVEMENT® - USPTO Reg. No. 6,689,873
  - ICOR® - USPTO Reg. Nos. 6,607,819 and 6,608,200
- **Common-law marks**: myICOR™, myPKA™
- See [NOTICE.md](NOTICE.md) and [TRADEMARK.md](TRADEMARK.md) for trademark usage guidelines.
- Trademark permission and OEM licensing: contact@myicor.com

## Disclaimer

The myPKA scaffold is a teaching artifact and a starting point, not a production system. It is provided as is, without warranty of any kind, express or implied. We make no guarantees about fitness for a particular purpose, about how any LLM or AI agent will behave when pointed at this folder, or about the integrity of your data over time.

You are responsible for what you do with this scaffold. That includes your own backups, your own data hygiene, your choice of LLM and AI tooling, and what you allow those tools to read or write on your machine. We are not liable for data loss, downtime, broken setups, or any other damage arising from use of the scaffold or its examples. Use at your own risk.

The binding legal terms are in the [LICENSE](LICENSE) (CC BY-SA 4.0), which includes the full disclaimer of warranties and limitation of liability. This section is the plain-English version of what that license already says.

## Built by

myPKA is built by **Dr. Thomas Rödl** and **Paco Cantero** at **Paperless Movement S.L.**, the company behind myICOR and the ICOR methodology. We use this scaffold every day. The version you're looking at is the version we run.

If it helps you, the best thank-you is to come learn the methodology at [myicor.com](https://myicor.com).
