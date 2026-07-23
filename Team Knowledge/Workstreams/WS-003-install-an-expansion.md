# WS-003 - Install an Expansion

- **Status:** Active (since v1.7.0)
- **Type:** Workstream — a multi-agent composition. The agents below collaborate to deliver the outcome. New Workstreams emerge when patterns repeat across session-logs; this one ships pre-canonicalized because Expansions are a day-1 install/uninstall flow that needs the multi-agent choreography (Larry → Vex → Nolan → Mack → Silas → Larry) wired correctly out of the box. **Pre-canonicalized exception**, alongside [[WS-001-daily-journaling]] and [[WS-002-import-external-knowledge-base]].
- **Owners:** **Larry** (orchestrator, pre-flight, post-install validation, archive, announcement). **Vex** (security review — gate; Vex ships with the App Developer Pack — when Vex is not installed, Larry executes the §2 security checklist himself and records the verdict; the gate never disappears). **Nolan** (team merge — copies agents, SOPs, guidelines, templates into your myPKA). **Mack** (connector wiring — env vars, MCP servers, runtime announcement). **Silas** (post-merge integrity check).
- **References:** `Expansions/docs/expansion-spec.md` (locked manifest schema), [[GL-001-file-naming-conventions]], [[GL-002-frontmatter-conventions]], [[SOP-001-how-to-add-a-new-specialist]] (Nolan's hire procedure — adapted here for pack-shaped hires), [[Team/agent-index]].
- **Triggered by:** any user phrasing that signals "install or uninstall an Expansion." See **Trigger contract** below. Also: Larry detects new folders in `Expansions/` on session boot and offers to run this workstream.

## Purpose

Take a folder dropped into `Expansions/`, validate it, security-review it, merge its contents into the your myPKA (agents, SOPs, guidelines, templates), wire any connectors or runtimes, validate the result, and announce the new capability — without leaving your myPKA in an inconsistent state on failure. Symmetric uninstall flow returns your myPKA to its prior shape.

## What this Workstream does not do

- Does not author Expansion manifests. That's the Expansion author's job (per `Expansions/docs/expansion-spec.md`).
- Does not bypass the security review. Tier-2 (myICOR-issued) Expansions verify against the integrity hash published on the myICOR Expansion Packs page (or a local `Expansions/.trusted-sources` pin, if you keep one), only after the review clears them. Tier-3 (community) Expansions get an interactive trust prompt. Either way, §2 is the gate — run by Vex if installed (e.g. via the App Developer Pack), otherwise executed by Larry himself.
- Does not silently overwrite existing files in the your myPKA. If a merge target already exists, the workstream stops and asks.
- Does not auto-launch runtime Expansions. That rule is hard. Mack announces; the user launches.

## Trigger contract

| User says (or implies) | Action |
|---|---|
| "install the [X] Expansion" / "install Slack" / "install the [X] pack" | Run this workstream from §1 |
| "I dropped the [X] pack into Expansions/" / "there's a new folder in Expansions" | Detect → confirm → run §1 |
| "uninstall [X]" / "remove the [X] Expansion" / "rip out [X]" | Run **§Uninstall** |
| (Larry-detected at session boot — new folder in `Expansions/` with valid `expansion.yaml` and not yet recorded in `Expansions/INDEX.md`) | Announce + offer to run §1 |

## Pre-flight (before any agent does anything)

Larry confirms the Expansion folder exists at `Expansions/<slug>/` and contains an `expansion.yaml` at its root. If not, Larry tells the user what's missing and stops.

---

## Step 1 — Larry: detect, parse, present preview

Larry reads `Expansions/<slug>/expansion.yaml` and validates against the schema in `Expansions/docs/expansion-spec.md`:

1. **Required fields present?** `name`, `slug`, `version`, `description`, `category`, `expansion_type`, `requires_agents`, `license`, `author`. Missing or malformed → `invalid` row in `INDEX.md`, install blocked, surface the error to the user. A `requires_scaffold_version` field is tolerated if present but **ignored** — it is no longer part of the spec (removed in 5.0.1) and never blocks an install.
2. **`requires_agents` present?** Larry checks each entry against `Team/agent-index.md`. Missing pre-hire → block install with "install [X] Expansion first" or "run SOP-001 to hire [X]".
3. **Folder name = `slug`?** If not, Larry stops and asks the user to rename.

If all checks pass, Larry presents the **install preview** to the user:

```
Expansion: <name> v<version>
Author: <author>           License: <license>
Type: <expansion_type>     Category: <category>

Adds:
  - N agents: <names>
  - M SOPs: <count, with default owners>
  - K guidelines, L workstreams, P templates (if any)
  - Q env vars (X required, Y sensitive)
  - R MCP servers (if any)
  - Runtime: yes/no
Post-install steps: <count>

Trust tier: <bundled / myICOR-verified / community>
Manifest hash: <sha256 first 12 chars>

Proceed? [y/n/inspect]
```

User answers `y` → §2. `n` → stop, write a session-log entry capturing the abort. `inspect` → Larry opens the folder for the user to read, then re-prompts.

---

## Step 2 — Vex: security review (the gate)

Vex audits the Expansion folder before any merge happens. This is a hard gate — Larry does not advance to §3 until Vex returns green or the user explicitly accepts a yellow flag.

**Fallback when Vex is not on the team.** Vex ships with the App Developer Pack (a membership Expansion), so a fresh scaffold does not have Vex yet. The gate does not disappear: Larry executes this §2 checklist himself, item by item, records the verdict in the install session-log, and applies the same GREEN / YELLOW / RED outcomes below. The gate is the checklist, not the agent. Once Vex is installed, Vex owns this step again.

Vex's checks:

1. **Trust tier check.** If `author: myICOR`, compute sha256 of `expansion.yaml` and verify it against the integrity hash published on the myICOR Expansion Packs page for that pack version (or against a local `Expansions/.trusted-sources` pin, if you keep one; the scaffold does not ship this file). Match → green (auto-trust). Mismatch → red (refuse). No published hash found → yellow (Vex hasn't audited this version yet — proceed only with explicit user override).
2. **Token handling sweep.** Grep the Expansion folder for any committed token-shaped string (`xoxb-`, `xapp-`, `sk-`, `ghp_`, etc.). Hit → red (block install — author shipped a credential).
3. **`.env.example` review.** Confirm `.env.example` lists only env-var keys, no values, no real tokens.
4. **Permission surface review.** For `connector` and `runtime` types: confirm the manifest's `env_vars`, `mcp_servers`, and runtime block match what the Expansion code actually does (no smuggled-in network calls, no unannounced spawns).
5. **Outbound network defaults.** Slack-shaped Expansions: confirm `unfurl_links: false` and `unfurl_media: false`. Webhook receivers: confirm signature verification is wired.
6. **Scripts review.** `install.sh`, `uninstall.sh`, `start.command`/`.sh`/`.bat` — read for shell injection risks, hard-coded paths outside the Expansion folder, or overly permissive `chmod`.

Vex returns one of:

- **GREEN** → §3 (proceed).
- **YELLOW** → Larry surfaces the flag to the user with Vex's reasoning. User overrides → §3. User declines → stop.
- **RED** → install blocked. Larry tells the user why. No override path.

---

## Step 3 — Nolan: merge agents, SOPs, guidelines, templates, workstreams

Nolan executes the file-level merge. Read-and-confirm each operation before writing.

### 3.1 Agents (`adds_agents`)

For each `{ name, role, folder }` entry:

1. Confirm `Expansions/<slug>/agents/<folder>/AGENTS.md` exists.
2. Check `Team/<folder>/` does not already exist. Collision → stop, ask user (rename / skip / overwrite).
3. Copy the entire `Expansions/<slug>/agents/<folder>/` directory to `Team/<folder>/`.
4. Append a row to `Team/agent-index.md` for the new specialist (name, folder, role description). Format: match the existing index's row shape.
5. Update root `AGENTS.md` "The team" table to bump the count and add the new row.
6. Update `Team/Larry - Orchestrator/AGENTS.md` routing cheatsheet with any triggers the new agent should own (pulled from the agent's own AGENTS.md or from the Expansion's `ADAPT-EXPANSION.md` hint table).

### 3.2 SOPs (`adds_sops`) — auto-numbered

For each `{ default_owner, file }` entry:

1. Read the next free `SOP-NNN` slot by scanning `Team Knowledge/SOPs/` (zero-padded, no skips per [[GL-001-file-naming-conventions]]).
2. Copy `Expansions/<slug>/sops/<file>` (or wherever the manifest points) to `Team Knowledge/SOPs/SOP-NNN-<derived-slug>.md`. Slug derived from the source filename minus the descriptive `SOP-` prefix the author used (e.g. `SOP-slack-post-message.md` → slug `slack-post-message` → `SOP-NNN-slack-post-message.md`).
3. Update `Team Knowledge/SOPs/INDEX.md` with a new row: number, title, default owner, one-line description.
4. If the SOP body references its own filename (back-pointers, internal links), Nolan rewrites those references to the new auto-numbered name. **All internal `[[wikilinks]]` are checked.**

### 3.3 Guidelines (`adds_guidelines`)

Same shape as SOPs, with `GL-NNN-` prefix. Index update at `Team Knowledge/Guidelines/INDEX.md`.

### 3.4 Workstreams (`adds_workstreams`)

Same shape as SOPs, with `WS-NNN-` prefix. Index update at `Team Knowledge/Workstreams/INDEX.md`. **Reminder:** workstreams are normally emergent; an Expansion shipping a workstream is the exception, not the rule.

### 3.5 Templates (`adds_templates`)

Copy each path under `Team Knowledge/Templates/`. If a template with the same name exists, stop and ask. Update `Team Knowledge/Templates/INDEX.md`.

### 3.6 Failure rollback

If any step in §3 fails after writes have started, Nolan rolls back: undo every file copy, restore every modified `INDEX.md` and root file from git (or from the pre-merge snapshot Nolan took at the start of §3). Vault returns to pre-install state.

---

## Step 4 — Silas: post-merge integrity check

Silas validates your myPKA state after Nolan's merge:

1. **Frontmatter compliance.** Any new template added under `Team Knowledge/Templates/` must validate against [[GL-002-frontmatter-conventions]]. Any new agent's AGENTS.md gets a structural sanity check (has Identity, Role, etc. sections).
2. **`agent-index.md` consistency.** Every folder under `Team/` is listed in the index, and every index row points to an existing folder.
3. **Wikilink resolution.** Every `[[wikilink]]` in the new files resolves to an existing target. Broken links → flag to Larry, do not auto-fix.
4. **INDEX.md consistency.** SOPs, Workstreams, Guidelines, Templates indexes match the actual folder contents.
5. **No SSOT violations introduced.** New SOPs/Guidelines/Workstreams don't duplicate existing rules. Soft warning if Silas detects overlap.

Silas returns one of:

- **PASS** → §5.
- **FAIL** → Larry surfaces the failure list. Two paths: (a) Nolan rolls back; (b) user accepts a known issue and proceeds (rare; logged in session-log).

---

## Step 5 — Mack: connector wiring (only if `connector` / `runtime` / `hybrid`)

Skip this step for pure `agent_pack` Expansions.

### 5.1 Env vars

For each `env_vars` entry:

1. If `required: true` and not already set in `Expansions/<slug>/.env`, prompt the user. Echo `sensitive: true` values masked.
2. Write to `Expansions/<slug>/.env`. `chmod 600` the file.
3. Confirm `Expansions/<slug>/.env` is gitignored (the Expansion's own `.gitignore` should cover this; if not, Mack adds the entry to your myPKA root `.gitignore`).

### 5.2 MCP servers

For each `mcp_servers` entry:

1. Detect the user's LLM tool (Claude Code → `~/.claude.json` or local `.mcp.json`; Cursor → `.cursor/mcp.json`; Codex → its config).
2. Write the registration block (`name`, `command`, `args`, env-var pass-through).
3. Verify the server starts: spawn it, confirm it responds to the MCP `initialize` handshake, terminate.
4. Document the registration in the install session-log entry.

### 5.3 Runtime announcement

For `expansion_type: runtime` or `hybrid` with a runtime block:

1. **Do not auto-launch.** Hard rule.
2. Tell the user: "To start the listener, double-click `Expansions/<slug>/scripts/start.command`" (macOS) or platform equivalent.
3. If the manifest provides a `launchd_plist` template, ask the user whether they want autostart. Yes → render the plist with the Expansion's actual path, copy to `~/Library/LaunchAgents/com.myicor.<slug>.plist`, `launchctl load` it. No → skip.
4. Hand the user the `SOP-<expansion>-listener-health.md` reference if the Expansion ships one.

---

## Step 6 — Larry: post-install validation

Larry runs `post_install_validation` from the manifest:

- Each `{ type: "file_exists", path: "..." }` → check.
- Each `{ type: "shell", cmd: "...", expect_exit: 0 }` → run, check exit code.
- Each `{ type: "http", url: "...", expect_status: 200 }` → curl, check status.

Failures → Larry surfaces them to the user. Two paths: (a) re-run the failing step (typically a re-prompt for env vars); (b) accept and continue with the issue logged.

---

## Step 7 — Larry: archive + announce

1. **Write session-log entry.** `Team Knowledge/session-logs/YYYY/MM/YYYY-MM-DD-HH-MM_larry_install-<slug>-v<version>.md`. Capture: which Expansion, version, agents added, SOPs added (with their new SOP-NNN numbers), Vex's verdict, env vars set (keys only, never values), runtime announced (yes/no), validation results, anomalies.
2. **Archive the Expansion folder.** Move the live install marker to `Expansions/_installed/<slug>-<version>/.manifest.json` so the active `Expansions/` slot is freed (the actual files merged into `Team/` and `Team Knowledge/` are the canonical home now). The `.manifest.json` is a snapshot of `expansion.yaml` plus the install metadata (timestamp, who installed, sha256). This is what Larry reads to detect "is this Expansion installed?" on future session boots.
3. **Update `Expansions/INDEX.md`.** Add a row for the newly installed Expansion.
4. **Announce the new specialists / capabilities** to the user. For agent packs: introduce each new agent by name and role. For connectors: tell the user which triggers now route to the connector and the SOP they own. For runtimes: confirm how to launch.
5. **Walk through `post_install_steps`.** Larry reads each step aloud (figuratively) and either executes it or hands it to the user.

Done. The install workstream returns control to whatever the user asked for next.

---

## Uninstall

Symmetric. Triggered by "uninstall [X] Expansion", "remove [X]", "rip out [X]".

### U1 — Larry: confirm + present uninstall preview

Larry reads `Expansions/_installed/<slug>-<version>/.manifest.json`. If not found, the Expansion is not installed — Larry tells the user. If found, Larry presents the **uninstall preview**:

```
Will remove:
  - N agents from Team/
  - M SOPs from Team Knowledge/SOPs/ (with their SOP-NNN numbers)
  - K guidelines, L workstreams, P templates
  - Runtime: yes/no (will stop the listener)
  - launchd plist: yes/no (will unload + remove)
  - MCP server registrations: <list>
  - Env vars in Expansions/<slug>/.env: <count, keys only>

Will keep (per residual_paths):
  - Team Inbox/<slug>-incoming/ (your data)
  - <other residuals>

Proceed? [y/n]
```

### U2 — Mack: stop runtime + tear down connector

For runtime Expansions: `launchctl unload` the plist (macOS); kill the foreground process (Linux/Windows). Remove the plist from `~/Library/LaunchAgents/`. Deregister MCP servers from the user's LLM config. Clear `Expansions/<slug>/.env`.

### U3 — Nolan: reverse the merge

For each `adds_agents` entry: remove `Team/<folder>/`, remove the row from `Team/agent-index.md`, remove the row from root `AGENTS.md` team table. Decrement the team count.

For each `adds_sops` entry: identify the installed `SOP-NNN-<slug>.md` (via the install session-log or by slug match), remove the file, remove the index row. **Do not renumber existing SOPs** — `[[GL-001-file-naming-conventions]]` says no skips, but uninstall produces a gap. The gap is acceptable. The next install fills the next free slot, which may be the gap.

For each `adds_guidelines`, `adds_workstreams`, `adds_templates`: same shape.

### U4 — Silas: post-uninstall integrity check

Same as install §4, but checking that removed files left no dangling wikilinks, INDEX rows, or `agent-index` rows. Flag any orphans for Larry to clean up.

### U5 — Larry: archive + session-log

Move `Expansions/_installed/<slug>-<version>/` to `Expansions/_uninstalled/<slug>-<version>/` (preserves the install record). If the Expansion folder itself is still present in `Expansions/` (the user dropped it back in to trigger uninstall, or it was never archived), `rm -rf` it. Anything in the manifest's `uninstall.residual_paths` that the user said `keep` to is left alone; everything else is removed.

Write the uninstall session-log entry. Update `Expansions/INDEX.md` to remove the row.

---

## Edge cases

| Situation | Behaviour |
|---|---|
| Vex flags YELLOW, user overrides | Logged in the session-log with explicit user-consent line. Vex re-audits if the Expansion is later updated. |
| Vex flags RED | Install blocked. No override. Larry tells the user the specific concern. |
| Vex is not installed (no App Developer Pack) | The §2 gate stays hard: Larry executes the §2 security checklist himself before any Expansion install, records the verdict in the session-log, and applies the same GREEN/YELLOW/RED outcomes. |
| `requires_agents` missing | Install blocked. Larry tells the user "install <X> Expansion first" or "run SOP-001 to hire <X>". |
| Collision: `Team/<folder>/` already exists | Nolan stops at §3. User chooses: rename (suffix `-from-<slug>`), skip that agent, or abort install. |
| Collision: SOP slug already taken | Nolan auto-resolves by appending `-<slug>` to the SOP slug (e.g., `SOP-NNN-post-message-slack.md`). |
| Mid-install failure | Nolan rolls back §3 writes. Mack rolls back §5 if reached. Vault returns to pre-install state. Failure logged. |
| Post-install validation fails | Larry surfaces; user chooses re-run or accept. |
| User uninstalls then reinstalls a different version | The `_installed` archive shows the old version's footprint. New install proceeds normally; auto-numbering picks new SOP slots. |

---

## Owner agency

Each agent in this workstream owns their step. If Vex's audit logic improves, Vex updates §2 directly (and tells Larry); when Vex is not installed, §2 as written is the canonical checklist Larry executes himself. If Nolan finds a better merge sequence, Nolan updates §3. Larry owns the orchestration shell (§1, §6, §7) and the trigger contract.

The Expansion author owns their `expansion.yaml`, their bundled files, and the `post_install_validation` rules. They do not own this workstream — the scaffold owns the install procedure, every Expansion plugs into the same one.
