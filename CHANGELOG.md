# Changelog

All notable changes to the myPKA scaffold are tracked here. Versions follow semver: MAJOR for breaking structural changes, MINOR for additions, PATCH for fixes.

## [2.2.0] - 2026-05-26

**Adds the one-way Task → Resource linking rule and its `linked_deliverables` slot.** A task now carries seven `linked_*` arrays in its frontmatter — the new `linked_deliverables` joins `linked_sops`, `linked_workstreams`, `linked_guidelines`, `linked_my_life`, `linked_session_logs`, `linked_journal_entries` — and the task is the one place that records which deliverable folder a workflow owns. When a task closes (done or cancelled), every deliverable in its `linked_deliverables` cascades into `Deliverables/_archive/<YYYY>/<MM>/`. Resources (deliverables, journal entries, session logs, SOPs, Workstreams, Guidelines, My Life entries) never carry a back-pointer to a task — the link is one-way. Additive, non-breaking; existing tasks need a one-line frontmatter addition (see Migration).

### Added

- **`GL-004-task-resource-linking.md`** in `Team Knowledge/Guidelines/`. The canonical rule: task → resource, never the reverse. Defines what counts as a resource, the seven-array frontmatter contract, the `linked_deliverables` slug format (`<folder-slug>/<file-slug>` or `<folder-slug>`), the archive-on-close cascade, the sharing escape hatch for deliverables referenced by multiple tasks, and the orphan-deliverable rule.
- **`linked_deliverables: []`** field in `Team Knowledge/tasks/_template.md`. The seventh `linked_*` array. The template's `## Context one click away` body section gains a `Working artifacts:` sub-bullet group that mirrors the array.
- **`Deliverables/_archive/.gitkeep`** — seeds the archive folder so it ships in the scaffold on first clone.
- **Lifecycle section in `Deliverables/README.md`** — documents the archive-on-close cascade, the orphan-deliverable rule, and the shared-deliverable behavior. Wikilinks to GL-004 and SOP-close-task.

### Changed

- **`Team Knowledge/SOPs/SOP-create-task.md`** bumped to v1.1. Step 4's cross-reference walk table gains a `linked_deliverables` row. "Six linked_* arrays" copy bumps to "seven" throughout (inputs table, step 4 paragraph, step 5 bullet, common-mistakes section). A second worked example shows a task with `linked_deliverables` populated (the minimal mux-webhook example stays as-is for the empty-arrays case). References list adds `[[GL-004-task-resource-linking]]`.
- **`Team Knowledge/SOPs/SOP-close-task.md`** bumped to v1.1. New §A.3 pre-flight step: check deliverable sharing across other open/in-progress tasks before archiving. New §A.8 / §B.5 archive steps: move each `linked_deliverables` folder to `Deliverables/_archive/<YYYY>/<MM>/`. The "move the folder, not the file" rule is documented. The `## Outcome` shape gains an `Archived deliverables:` line. A second worked example walks the archive-on-close path; the original mux-webhook example stays as the no-deliverables case. References list adds `[[GL-004-task-resource-linking]]` and `[[SOP-002-convert-mypka-to-sqlite]]`.
- **`Team Knowledge/SOPs/SOP-claim-task.md`** — small update. Pre-flight read list adds `linked_deliverables` ("the working artifacts already in flight — skipping them means re-doing what's already done"). References list adds `[[GL-004-task-resource-linking]]`. Common-mistakes section notes that skipping `linked_deliverables` in pre-flight is a resumption hazard.
- **`Team Knowledge/tasks/open/EXAMPLE-tsk-2026-05-10-001-welcome-to-tasks.md`** — seeded teaching task updated to the seven-array shape (`linked_deliverables: []` added; `GL-004` added to `linked_guidelines`; "six arrays" copy in the body bumped to "seven"; an additional `Linking rule: [[GL-004-task-resource-linking]]` bullet appears in `## Context one click away`).
- **`Team Knowledge/Guidelines/INDEX.md`** — gains a row for GL-004 between GL-002 and the reserved-GL-003 note. The reserved note for GL-003 (Designer Expansion Pack) is unchanged.

### Migration

**Existing scaffold users with active tasks need a one-line frontmatter addition per task** to bring them up to the seven-array shape. A one-shot grep + sed pattern is suggested in the migration prompt exposed as the "upgrade" button in the myPKA course at https://myicor.com.

Tasks already in `done/` or `cancelled/` are historical record and do not need migration. The walk in [[SOP-create-task]] step 4 starts using all seven slots immediately from v2.2.0 onward.

Resources written before v2.2.0 may carry a pre-GL-004 `linked_tasks` field. Per the new one-way rule, that field is retired — remove it on touch. New writes never add it.

### Version files

- `VERSION` → `2.2.0`
- `.scaffold-version` → `2.2.0`

## [2.1.2] - 2026-05-20

**Repository moved to myICOR org for corporate ownership; remains public and free.** The canonical home of the myPKA scaffold is now `https://github.com/myICOR/myPKA` (transferred from `TomSolid/myPKA`). The repo stays public under CC BY-NC-SA 4.0 and continues to be the free distribution channel; the myicor.com SaaS layer remains the paid product. Stars, forks, issues, and the old URL are preserved by GitHub's transfer redirects, so existing clones and bookmarks keep working. No code or content changes vs 2.1.0 — this release exists solely to publish the org-owned canonical artifact at `releases/latest/download/mypka-scaffold-latest.zip`. (AUTO-175)

### Version files

- `VERSION` → `2.1.2`
- `.scaffold-version` → `2.1.2`

## [2.1.0] - 2026-05-19

**Slash commands become adapter-generated.** The `/close-session` command is no longer pre-baked into the scaffold as a Claude-only file. The adapter now generates it at setup time from the canonical close-session protocol in `AGENTS.md`, so the scaffold ships host-neutral and every host gets the right thing: Claude Code gets the slash command, hosts without slash commands skip it and rely on the natural-language triggers. Additive, non-breaking — Claude Code users get the command regenerated idempotently on next activation. (COU-272)

### Added

- **ADAPTER-PROMPT §7-bis "Bind host-native slash commands."** New idempotent setup step: if the host supports native slash commands (Claude Code → `.claude/commands/close-session.md`), the adapter generates `close-session.md` from the canonical close-session protocol in `AGENTS.md`. Hosts without slash commands (Codex CLI, Gemini CLI, Cursor, chat-only) skip generation and the tool-specific pointer file notes the natural-language triggers instead. Skip-if-exists — never overwrites a user-customized command file.
- **`SLASH COMMANDS BOUND:` report-back field** in ADAPTER-PROMPT — the adapter now reports whether the close-session command was written, skipped (already exists), or not applicable for the host.

### Removed

- **`.claude/commands/close-session.md` is no longer tracked in the repo.** It was a Claude-Code-only pre-baked file; it is now adapter-generated per §7-bis. Removing it from the scaffold makes the repo host-neutral. (Note: `.claude/agents/*.md` shims are in the same pre-baked-Claude-only category and a candidate for the same treatment — tracked separately, not part of this release.)

### Changed

- `AGENTS.md` (root) — close-session trigger row gains the member-facing phrases "close this session", "wrap", "log this session". The slash-command-optionality line is tightened: `/close-session` is explicitly a Claude-Code-only convenience generated at setup (ADAPTER-PROMPT §7-bis), not required and not shipped; the natural-language triggers are the canonical universal path.
- `validation-script.sh` — `.scaffold-version` check widened from the `2.0.x` line to the full `2.x` line; v2.1.0 introduces no structural changes the script must enforce.

### Version files

- `VERSION` → `2.1.0`
- `.scaffold-version` → `2.1.0`

## [2.0.0] - 2026-05-18

**Breaking structural change.** The base scaffold roster moves from **nine specialists to six**. The three creative specialists — Iris (Design System Architect), Charta (Infographic Designer), Pixel (Visual Specialist) — and everything they own come out of the base scaffold and into the optional **Designer Expansion Pack** from the AI Library. The base now ships Larry, Nolan, Pax, Penn, Mack, and Silas. A user updating an existing myPKA from 1.10.x to 2.0.0 loses the three creative agents from their base roster — install the Designer Expansion Pack to keep them. (COU-261)

### Removed

- **Three creative specialists.** `Team/Iris - Design System Architect/`, `Team/Charta - Infographic Designer/`, `Team/Pixel - Visual Specialist/` — agent folders, contracts, and per-agent `journal/` templates.
- **Three Claude sub-agent boot files.** `.claude/agents/iris.md`, `.claude/agents/charta.md`, `.claude/agents/pixel.md`.
- **Four design SOPs.** `SOP-007-build-an-infographic`, `SOP-008-generate-a-styled-image`, `SOP-009-author-a-design-system`, `SOP-010-audit-content-for-design-system-compliance`. The `SOP-007`–`SOP-010` slots are now vacated and reserved; per the no-renumber rule the gap is intentional. A fresh Designer Pack install claims the lowest free slots starting at `SOP-003`.
- **`GL-003-design-system`.** The design-system Guideline (the visual identity SSOT) moves into the Designer Expansion Pack, which now ships it via `adds_guidelines`. It is no longer part of the base Guidelines set.
- **Three team-portrait images.** `github/team/iris.png`, `github/team/charta.png`, `github/team/pixel.png`.

### Changed

- `Team/agent-index.md` — routing table down to six rows; "nine specialists" → "six specialists"; Mack's row drops the Pixel-handoff parenthetical.
- `Team/Larry - Orchestrator/AGENTS.md` — routing cheatsheet drops the four design rows; "What Larry does not do" drops the two design/GL-003 lines.
- `AGENTS.md` (root) — "The team (9 specialists)" → "The team (6 specialists)"; team table down to six rows; "the current 9 specialists" → "6".
- `README.md` — "nine"/"9" roster references → "six"/"6" (×5 including version badge); three creative team-card blocks removed; added a Designer Pack pointer note.
- `WAY-FORWARD.md` — roster lines and the "When … specialists isn't enough" section updated to six; capability list drops infographic layout, image stylization, and design-system authoring (now pack capabilities).
- `Team Knowledge/SOPs/INDEX.md` — four design-SOP rows removed; Reserved line extended to "SOP-003 onward".
- `Team Knowledge/Guidelines/INDEX.md` — `GL-003` row removed; replaced with a Reserved note pointing at the Designer Pack.
- `validation-script.sh` — structural version check moved from the `1.10.x` line to the `2.0.x` line.

### Migration

Updating from 1.10.x to 2.0.0 is **breaking** — the base roster shrinks by three. If you do brand or visual work, install the **Designer Expansion Pack** (Iris, Charta, Pixel + the four design SOPs + `GL-003-design-system`) from the AI Library; it restores the full creative capability as an opt-in pack. Users who do only PKM, journaling, research, automation, or database work need no action — the six-specialist base covers them. Existing session logs that reference the removed agents or SOP-007–010 are left untouched as historical record.

### Version files

- `VERSION` → `2.0.0`
- `.scaffold-version` → `2.0.0`

## [1.10.2] - 2026-05-15

Restores the seeded sample content the myICOR myPKA course walks through. v1.10.x shipped the `PKM/My Life/`, `PKM/CRM/`, `PKM/Documents/`, `PKM/Journal/`, and `PKM/Images/` folders empty (`.gitkeep` placeholders), but the course curriculum references concrete files inside them by name — `morning-build-session.md`, `ship-mvp-by-q3.md`, and others. Learners following along found the files missing and assumed the download was broken. This release closes that gap. No folder structure, schema, or SOP changes — content only, so v1.10.x validation is unaffected.

### Added

- **`PKM/My Life/` concept samples** — one seeded file per subsection: `Topics/ai-tooling.md`, `Habits/morning-build-session.md`, `Goals/ship-mvp-by-q3.md`, `Projects/side-project-mvp.md`, `Key Elements/health.md`. Each is the canonical shape its concept follows and is cross-linked to the others via `[[wikilinks]]`.
- **Per-subfolder `INDEX.md`** for each of the five `My Life` subsections (`Topics/`, `Habits/`, `Goals/`, `Projects/`, `Key Elements/`). The course (lesson "Habits — The Rhythms the Team Supports") references these directly.
- **`PKM/CRM/` samples** — `People/dr-schmidt.md` and `Organizations/dr-schmidt-clinic.md`, the SSOT demo pair the course walks through.
- **`PKM/Documents/passport.md`** — seeded document-stub sample.
- **`PKM/Journal/2026/05/2026-05-04-first-day.md`** — seeded journal entry, the one referenced in the Dr. Schmidt demo.
- **`PKM/Images/2026/05/`** — two seeded sample images (`2026-05-04-dr-schmidt-business-card.png`, `2026-05-04-sample-screenshot.png`), embedded by the CRM and Journal samples.
- **Course-sample banner** — each seeded file opens with an Obsidian `[!example]` callout marking it as a worked sample to adapt or replace, so it is never mistaken for the learner's own content.

### Changed

- `PKM/My Life/INDEX.md`, `PKM/My Life/README.md` — replaced the "ships empty" / "Dean is seeding…" placeholder copy with the actual seeded-sample listing.
- `PKM/Documents/INDEX.md`, `PKM/CRM/INDEX.md`, `PKM/Journal/INDEX.md`, `PKM/Images/INDEX.md` — "Active files" sections now list the seeded samples.

### Trust registry

- `Expansions/.trusted-sources` — pinned `slack@1.0.3` (`sha256=6b5d09ad46328af92e7e6d99706033af2304b13825de00ad391691f617756260`). Slack Expansion v1.0.3 is a packaging/docs-only release (JSON manifest, `slack/` folder rename, `install.sh` quarantine clear); `runtime/index.js` is byte-identical to v1.0.2, so Vex's GREEN audit carries over. Restores the WS-003 §2 trust check to GREEN (silent auto-trust) for v1.0.3 installs. Existing `app-developer@1.0.1` and `slack@1.0.2` entries retained. (AUTO-26)
- Removed `.gitkeep` placeholders from folders that now hold seeded content.

### Version files

- `VERSION` → `1.10.2`
- `.scaffold-version` → `1.10.2`

## [1.10.1] - 2026-05-10

Wires v1.10.0's task system and journal SOPs into the agent contracts. v1.10.0 shipped the folder structure, templates, validation script, and 8 SOPs — but the AGENTS.md files were not updated, which meant the boot-walk and journal-read only happened if the LLM discovered the SOPs on its own. v1.10.1 closes that gap. No new SOPs, no new folders, no new behaviors — only contract-level wiring of what v1.10.0 already shipped.

### Changed

- `Team/Larry - Orchestrator/AGENTS.md` — adds `## Session boot — task-walk first` before `## Three duties`. Larry now walks `Team Knowledge/tasks/open/` + `tasks/in-progress/` per [[SOP-list-open-tasks]] at every session boot and surfaces open priority-1 / in-progress / blocked / stale items in the greeting. Tom no longer has to ask "what's open?" — the team picks up where it left off automatically.
- `Team/Larry - Orchestrator/AGENTS.md` — Duty 1 step 4 (Brief) now requires Larry to create a task via [[SOP-create-task]] before delegating any work that won't finish in-turn, populating all six `linked_*` arrays. The specialist resumes from the task file, not from chat scrollback.
- All 8 specialist AGENTS.md (Nolan, Pax, Penn, Mack, Silas, Charta, Pixel, Iris) — adds a shared `## Task discipline (v1.10.1)` section right after the agent's "When Larry routes to <Name>" section. The block wires three behaviors at dispatch:
  1. Read your `linked_journal_entries` and the matching files in `Team/<your-name>/journal/` per [[SOP-read-own-journal]] before starting work. Auditable via a `## Updates` line that names the priors you carried.
  2. When you create a task, populate all six `linked_*` arrays per [[SOP-create-task]].
  3. When you close a task, write the `## Outcome` and, if there's a durable lesson, write a journal entry per [[SOP-write-journal-entry]] and link it from the closed task.
- `validation-script.sh` — version check loosened from a hard `1.10.0` literal to a `1.10.x` glob so v1.10.x patch releases pass the same structural check. v1.10.0 folders still pass.

### Migration

None required. v1.10.1 is contract-only — no folder structure, schemas, or SOPs change.

### Version files

- `VERSION` → `1.10.1`
- `.scaffold-version` → `1.10.1`

## [1.10.0] - 2026-05-10

Adds task management, per-agent journals, and an LLM-readable migration changelog. Additive — no breaking changes from v1.9.x. v1.9.x folders gain new directories and templates; nothing existing is moved, renamed, or modified.

### Added

- `Team Knowledge/tasks/` — markdown-first task management for unfinished work the team carries across sessions. Folder location encodes status (`open/`, `in-progress/`, `done/<YYYY>/<MM>/`, `cancelled/<YYYY>/<MM>/`). One `.md` file per task. Frontmatter holds six required cross-reference arrays (`linked_sops`, `linked_workstreams`, `linked_guidelines`, `linked_my_life`, `linked_session_logs`, `linked_journal_entries`) so any agent or human reopening a task is one wikilink away from the full working context.
- `Team Knowledge/tasks/_template.md` — starter file for new tasks. Frontmatter schema is locked: every task uses the same fields with the same names so grep, parse, and rebuild are deterministic.
- `Team Knowledge/tasks/INDEX.md` — auto-generated summary view (open by priority, in-progress by assignee, recently closed). Rebuilt at the end of every task-touching SOP and re-checked at session boot.
- `Team Knowledge/tasks/{open,in-progress,done,cancelled}/.gitkeep` — placeholders so empty folders survive in git.
- Task ID scheme: `tsk-YYYY-MM-DD-NNN`. Lexical sort matches chronological sort. Date-prefixed filenames stay self-describing when referenced from session logs months later.
- `Team/<Name> - <Role>/journal/` — per-agent durable insight notes. One folder per shipped specialist (Larry, Nolan, Pax, Penn, Mack, Silas, Charta, Pixel, Iris). The agent commits an entry when they learn something cross-session: a lesson, a decision rule, an anti-pattern. Journal entries are topical, not chronological.
- `Team/<Name> - <Role>/journal/_template.md` — starter file for journal entries. Locked frontmatter (`agent_id`, `type`, `topic`, `tags`, `linked_session_logs`, `linked_tasks`, `related_journal_entries`, `status`).
- `.scaffold-version` — plain-text file at the repo root containing `1.10.0`. Single source of truth for which migrations apply.
- `CHANGELOG-MIGRATION.md` — machine-actionable upgrade spec. Per-version sections with numbered, idempotent recipes any LLM can follow to upgrade an older myPKA folder. Includes a validation script that exits 0 on a structurally valid migration.
- `validation-script.sh` — bash script at the repo root that verifies a folder is v1.10.0-compliant. Exits 0 on success, 1 on failure.
- New SOPs in `Team Knowledge/SOPs/`:
  - `SOP-create-task.md` — confronts all six cross-reference arrays at creation.
  - `SOP-claim-task.md` — atomic claim via `git mv`. Loser retries on a re-list.
  - `SOP-close-task.md` — moves to `done/` with outcome filled in. Surfaces open sub-tasks for explicit decision.
  - `SOP-list-open-tasks.md` — folder walk that Larry runs at session boot.
  - `SOP-rebuild-task-index.md` — awk-based, sub-500ms target on 1,000 tasks.
  - `SOP-write-journal-entry.md` — trigger test, body shape, supersession rules.
  - `SOP-read-own-journal.md` — what each agent runs before starting work on a task.
  - `SOP-write-session-log.md` — extended to reference any tasks created or touched.

### Changed

- `VERSION` bumped from `1.9.0` to `1.10.0`. Minor bump — purely additive, no existing files break.
- Expansions targeting v1.10.0+ should declare `mypka_compat: ">=1.10.0 <2.0.0"`.

### Notes

- Continuity is the principle this release is built on. The team should be able to pick up where it left off across sessions, even when a different specialist takes over. Tasks and journals serve that. There is no lifecycle theater.
- Folder location, frontmatter, and body are redundant on purpose. An agent reading any one of the three can reconstruct enough to act. A grep walker can classify without opening files. A human can `cat` and understand.
- There is no `blocked/` folder. Blocked tasks stay in `in-progress/` with `blocked_reason:` and `blocked_by:` set in frontmatter, so they surface in the assignee's normal queue scan rather than hiding in a folder no one greps.
- Wikilinks use basenames only, never paths. Files can move across folders without breaking links. Same convention as the rest of the scaffold.
- A SQLite mirror for tasks is sketched but deliberately not shipped in v1.10.0. Markdown stays canonical. The existing `SOP-002-convert-mypka-to-sqlite` is the right surface to extend when that need lands.
- Backwards-compatible: v1.9.x Expansions and SOPs continue to work unchanged. The boot routine and per-agent `AGENTS.md` files are unchanged in v1.10.0; the task-walk and journal-read behaviors are codified in the new SOPs and surface naturally as the team discovers them.

## [1.9.0] - 2026-05-09

**Host subagent binding ships out of the box.** First activation now generates host-specific subagent shims so the eight deputies (Penn, Pax, Nolan, Mack, Silas, Charta, Pixel, Iris) can dispatch in parallel via the host's agent runtime — not role-played in a single context. Larry is excluded (he's the main-session identity, not a dispatched subagent).

The contract: **two layers, never three.** The wiki contract at `Team/<Name>/AGENTS.md` is canonical and host-agnostic. The host shim (`.claude/agents/<slug>.md` for Claude Code; `.codex/agents/<slug>.md` for Codex if supported; per-spec for Gemini) is a thin pointer that the host runtime reads to dispatch the specialist. We do NOT add a third layer (e.g. a `CLAUDE.md` inside each `Team/<Name>/`) — that violates SSOT.

### Added

- `.claude/agents/{charta,iris,mack,nolan,pax,penn,pixel,silas}.md` — Claude Code subagent shims for the eight deputies. YAML frontmatter (`name`, `description`, `tools`) + body that points back to the wiki contract via path. ~30-60 lines each. Larry is intentionally excluded.
- `ADAPTER-PROMPT.md` Step 7 (new) — host-agnostic procedure to walk `Team/`, derive each slug, and generate host-specific shims on first init. Per-host matrix: Claude Code → `.claude/agents/`, Codex CLI → `.codex/agents/` (when supported), Gemini CLI → per spec, Cursor / chat-only → noted limitation. **Idempotent** — re-running Step 7 skips any pre-existing shims (never overwrites user customizations). Report-back template adds `HOST SUBAGENT BINDING` field listing written + skipped.

### Changed

- `Team/Nolan - HR/AGENTS.md` — every hire now ships two artifacts: the wiki contract AND the host shim(s) for every host the user has activated. Detection by pointer-file presence (`CLAUDE.md`, `AGENTS.md.codex`, `GEMINI.md`, `.cursor/rules/main.md`).
- `Team Knowledge/SOPs/SOP-001-how-to-add-a-new-specialist.md` §5 — host-agnostic principle plus host-specific shim path matrix. Two artifacts always go together.
- `VERSION` 1.8.2 → 1.9.0.

### Notes

- No code, schema, or contract changes vs 1.8.x. Host bindings are additive; the wiki contracts are unchanged.
- The `mypka-scaffold-latest.zip` URL pattern is preserved.
- Existing v1.8.x users who upgrade get the eight shims AND the new Step 7 in the next adapter run. The idempotency rule means any manual customizations to existing shim paths are preserved.

## [1.8.2] - 2026-05-09

**Personalization placeholder + Tom-stand-in cleanup.** The scaffold's user-stand-in mentions of "Tom" are replaced with `{{USER_NAME}}` placeholder tokens. `ADAPTER-PROMPT.md` now captures the user's first name on first activation and substitutes the placeholder across the scaffold, saving the value to `PKM/.user.yaml` for future reference. Authorship credits ("Tom builds the system from scratch" video walkthrough) keep the formal name "Dr. Thomas Rödl". App Developer Pack `BUILD-NOTES.md` swept the same way.

### Changed

- `Team/Larry - Orchestrator/AGENTS.md` — "Tom double-clicks `start.command`" → "{{USER_NAME}} double-clicks `start.command`".
- `Team Knowledge/session-logs/_template.md` — example follow-up items "Tom reviews v1" → "{{USER_NAME}} reviews v1".
- `Team Knowledge/Workstreams/WS-003-install-an-expansion.md` — "Tom-approved canonical exception" → "Pre-canonicalized exception".
- `README.md`, `WAY-FORWARD.md` — "Tom builds the system" → "Dr. Thomas Rödl builds the system" (formal authorship credit).
- `ADAPTER-PROMPT.md` — new step 4: detect `{{USER_NAME}}` placeholders, ask user for first name, substitute across the scaffold, save to `PKM/.user.yaml`. Report-back template adds a `PERSONALIZATION` field.
- `AGENTS.md` — new "Personalization" section codifies the substitution rule for future content (e.g., Expansions that ship with `{{USER_NAME}}` tokens).
- App Developer Pack 1.0.1 `BUILD-NOTES.md` — swept "Tom" stand-ins to "the user" / "the maintainer".
- `VERSION` 1.8.1 → 1.8.2.

### Notes

- No code, schema, or contract changes. The `mypka-scaffold-latest.zip` URL pattern is preserved.
- App Developer Pack 1.0.1 manifest hash unchanged (only BUILD-NOTES.md edited; expansion.yaml bytes are identical).

## [1.8.1] - 2026-05-09

**Initial public release.** myPKA ships with a 9-person pre-hired AI team (Larry, Nolan, Pax, Penn, Mack, Silas, Charta, Pixel, Iris), full Personal Knowledge Architecture folder structure (PKM/My Life, PKM/CRM, PKM/Documents, PKM/Journal, PKM/Images), Team Knowledge layer (SOPs, Workstreams, Guidelines, Templates, session-logs), and the Expansions architecture for downloadable agent + connector packs.

### Highlights

- **Plain markdown.** Every note is a `.md` file. Works in Claude Code, Codex CLI, Gemini CLI, Cursor, ChatGPT, Obsidian + chat plugin, or any LLM that reads `AGENTS.md`.
- **Session-log triggers (LLM-agnostic).** Natural-language phrases like `close session`, `keep this in mind`, `let's realign` route the team's auto-memory across any LLM — not Claude-only.
- **External knowledge import.** [[WS-002-import-external-knowledge-base]] lets the team pull from Heptabase, Notion, Obsidian, Roam, Logseq, Mem, Capacities, Apple Notes, Evernote, Tana via MCP, or any SQLite-backed PKM tool.
- **Expansions architecture.** Day-1 packs (App Developer Pack, Slack Expansion) ship via the AI Library at [myicor.com](https://myicor.com). [[WS-003-install-an-expansion]] codifies the multi-agent install flow.
- **Frontmatter discipline.** `GL-002` defines field schemas for all eight entity types (Person, Organization, Project, Goal, Habit, Topic, Key Element, Document); `Team Knowledge/Templates/` ships the matching starters.
- **SQLite upgrade path.** [[SOP-002-convert-mypka-to-sqlite]] generates a derived SQLite mirror when the markdown layer outgrows plain files. Markdown stays canonical.
- **Design system primitive.** `GL-003` ships as an empty template; Iris populates it with the user via [[SOP-009-author-a-design-system]] on first creative request, then Charta/Pixel read from it for consistent style.

The `mypka-scaffold-latest.zip` URL pattern is non-negotiable — the myicor.com AI Library download button keeps serving `latest` with zero config changes across releases.
