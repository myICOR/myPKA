# myPKA Expansion Spec — v1 (locked at scaffold v1.7.0)

This document is the public, **locked** contract for authoring a myPKA Expansion. If you are writing one, this is what you write to. If you are wondering what an Expansion is allowed to do, this is what defines it.

Scaffold this spec ships with: **myPKA v1.7.0**.

> **Vocabulary.** v1.5/1.6 called these "Extensions." v1.7 renames the architecture to **Expansions** end-to-end (folder `Expansions/`, manifest `expansion.yaml`, adapter doc `ADAPT-EXPANSION.md`). The technical contract is otherwise unchanged from v1.5/1.6 except for the schema additions documented below.

---

## What an Expansion is

An Expansion is a single folder that **grows the user's pre-hired team or wires the team to an external system**. Drop the folder into `Expansions/`. Larry detects it on the next session boot, walks the install workstream ([[WS-003-install-an-expansion]]), and the team grows.

Two important framing notes:

1. **Expansions are how the team grows.** This is the user-facing thesis: "install a pack, hire more specialists, stay non-blocking." Some Expansions add agents, some add connectors, some add runtimes — but the through-line is always "the team learns something new it can do."
2. **Expansions are uninstallable.** `rm -rf` the folder (after running uninstall) and the scaffold is back to its prior shape. This is non-negotiable. No silent state writes outside `residual_paths`.

The OSS scaffold's `Expansions/` folder is **structurally empty by design**. It ships with this spec, the README, and an empty INDEX.md template. Real Expansions live in their own private repos and ship as zips. Users drop them into their personal myPKA. None of that ever lands in this repo.

---

## The four shapes (`expansion_type`)

| Shape | Adds | Examples |
|---|---|---|
| `agent_pack` | New specialists (`adds_agents`), their SOPs, optionally Guidelines/Templates | App Developer Pack (Felix + Vex + Vera) |
| `connector` | OAuth/API/webhook wiring, env vars, MCP server registrations. May add SOPs default-owned by Mack. | Notion, Readwise, Linear |
| `runtime` | Long-lived background process (`start.command` / launchd plist). Listener/relay shape. | Slack Expansion, mypka-interface |
| `hybrid` | Combines two of the above. Rare. Permitted only when splitting into two Expansions would produce a worse user experience. | An agent pack that also ships a runtime listener |

---

## `expansion.yaml` — schema v1 (LOCKED)

Every Expansion folder MUST contain an `expansion.yaml` at its root. Larry parses it forgivingly: bad YAML or missing required fields produce an `invalid` row in `INDEX.md` rather than crashing the session.

### Required fields (all expansion types)

| Field | Type | Notes |
|---|---|---|
| `name` | string | Human-readable name. |
| `slug` | string | kebab-case. MUST match the folder name. |
| `version` | semver | `MAJOR.MINOR.PATCH`. |
| `description` | string | One sentence. Goes into `Expansions/INDEX.md`. |
| `category` | string | Free-text tag for the AI Library (e.g., `agents`, `connector`, `productivity`). |
| `expansion_type` | enum | `agent_pack` \| `connector` \| `runtime` \| `hybrid` |
| `requires_scaffold_version` | semver range | e.g. `">=1.7.0 <2.0.0"`. Larry refuses to install on mismatch. |
| `requires_agents` | list | Pre-hired agents this Expansion uses (e.g., `[Larry, Mack]`). Larry blocks install if any are missing. |
| `license` | string | SPDX identifier or short string (`proprietary`, `MIT`, `CC-BY-NC-SA-4.0`, …). |
| `author` | string | Who shipped this Expansion. |

### Conditional / optional fields

| Field | When | Shape |
|---|---|---|
| `homepage` | optional | URL to the Expansion's documentation page. |
| `adds_agents` | `agent_pack` or `hybrid` | List of `{ name, role, folder }`. `folder` is the destination subfolder under `Team/`. |
| `adds_sops` | optional, any type | List of `{ default_owner, file }`. The install workstream auto-numbers (next free `SOP-XXX-`) into `Team Knowledge/SOPs/`. |
| `adds_guidelines` | rare | List of `{ slug, file }`. Most Expansions don't ship Guidelines. |
| `adds_workstreams` | rare | List of `{ slug, file }`. Workstreams are emergent — pre-shipping is the exception, not the rule. Permitted when the Expansion ships canonical day-1 multi-agent flows that the user can't reasonably author themselves. |
| `adds_templates` | optional | List of relative paths under the Expansion folder to copy into `Team Knowledge/Templates/`. |
| `env_vars` | `connector`, `runtime`, `hybrid` | List of `{ key, description, required, sensitive }`. The install workstream prompts the user for `required: true` values; `sensitive: true` values are echoed masked and stored in the Expansion's `.env`. |
| `post_install_steps` | optional | Human-readable list. Larry walks the user through these after install completes. |
| `post_install_validation` | optional | Machine-checkable. Either a shell command to run, or a list of checks (`{ type: "file_exists", path: "…" }`, `{ type: "shell", cmd: "…", expect_exit: 0 }`, `{ type: "http", url: "…", expect_status: 200 }`). |
| `mcp_servers` | optional, any type | List of MCP server configs. Mack registers these with the user's LLM tool (Claude Code config, Codex config, etc.). Schema: `{ name, command, args, env_vars }`. |
| `runtime` | `runtime` or `hybrid` | Object describing the long-lived process. See **runtime block** below. |
| `uninstall` | optional | `{ method: "rm-rf-folder", residual_paths: [...] }`. If omitted, defaults to `rm-rf-folder` with no residuals. |

### Runtime block (when `expansion_type` includes a runtime)

```yaml
runtime:
  start:
    command: ./scripts/start.command          # macOS double-clickable
    sh: ./scripts/start.sh                    # Linux
    bat: ./scripts/start.bat                  # Windows
  launchd_plist: ./scripts/launchd-plist.template  # macOS background daemon (optional)
  port: null                                   # null if no port bound (Socket Mode etc.)
  interactive: false                           # true if the runtime needs a foreground terminal
```

Larry **announces** runtimes. He never auto-launches them. The user double-clicks `start.command` (or platform equivalent) when ready. This rule is enforced by Mack's contract and is a hard line in the scaffold.

---

## Example manifests

### Example 1 — `agent_pack` (App Developer Pack)

```yaml
name: App Developer Pack
slug: app-developer
version: 1.0.0
description: Adds Felix (frontend), Vex (security), Vera (QA) to your team for building, auditing, and quality-gating apps.
category: agents
expansion_type: agent_pack
requires_scaffold_version: ">=1.7.0 <2.0.0"
requires_agents: [Larry, Nolan, Mack]
license: proprietary
author: myICOR

adds_agents:
  - { name: Felix, role: Frontend Developer, folder: "Felix - Frontend Developer" }
  - { name: Vex,   role: Security Engineer,  folder: "Vex - Security Engineer" }
  - { name: Vera,  role: QA Specialist,      folder: "Vera - QA Specialist" }
adds_sops:
  - { default_owner: Felix, file: SOP-felix-build-a-component.md }
  - { default_owner: Vex,   file: SOP-vex-security-audit.md }
  - { default_owner: Vera,  file: SOP-vera-quality-gate.md }
adds_guidelines: []
adds_workstreams: []
adds_templates: []
env_vars: []
post_install_steps:
  - "Larry will introduce the three new specialists in your next session."
  - "If you have a design system, Vera references Team Knowledge/Guidelines/GL-003-design-system.md for visual QA."
post_install_validation:
  - { type: "file_exists", path: "Team/Felix - Frontend Developer/AGENTS.md" }
  - { type: "file_exists", path: "Team/Vex - Security Engineer/AGENTS.md" }
  - { type: "file_exists", path: "Team/Vera - QA Specialist/AGENTS.md" }
```

### Example 2 — `runtime` (Slack Expansion)

```yaml
name: Slack Expansion
slug: slack
version: 1.0.0
description: Use Slack as a chat surface for Larry. Inbound DMs and @-mentions land in Team Inbox; replies post back in-thread.
category: connector
expansion_type: runtime
requires_scaffold_version: ">=1.7.0 <2.0.0"
requires_agents: [Larry, Mack]
license: proprietary
author: myICOR
homepage: https://myicor.com/library/slack

adds_agents: []
adds_sops:
  - { default_owner: Larry, file: SOP-slack-incoming-routing.md }
  - { default_owner: Mack,  file: SOP-slack-post-message.md }
  - { default_owner: Mack,  file: SOP-slack-listener-health.md }
adds_guidelines: []
adds_workstreams: []
adds_templates: []
env_vars:
  - { key: SLACK_BOT_TOKEN,         description: "Slack bot token (xoxb-...)",                     required: true,  sensitive: true }
  - { key: SLACK_APP_TOKEN,         description: "Slack app-level token (xapp-...) for Socket Mode", required: true,  sensitive: true }
  - { key: SLACK_DEFAULT_CHANNEL,   description: "Default channel ID for outbound posts",          required: false, sensitive: false }
  - { key: SLACK_NOTIFY_OS,         description: "Surface OS notifications on inbound (true/false)", required: false, sensitive: false }
  - { key: SLACK_AUTORESPONDER_MIN, description: "Minutes before autoresponder fires (default 30)", required: false, sensitive: false }
post_install_steps:
  - "Create a Slack app at https://api.slack.com/apps (paste the manifest from INSTALL.md)."
  - "Enable Socket Mode, install the app to your workspace, copy xoxb and xapp tokens into .env."
  - "Double-click scripts/start.command to launch the listener."
post_install_validation:
  - { type: "shell", cmd: "test -s Expansions/slack/.env", expect_exit: 0 }
runtime:
  start:
    command: ./scripts/start.command
    sh: ./scripts/start.sh
    bat: ./scripts/start.bat
  launchd_plist: ./scripts/launchd-plist.template
  port: null
  interactive: false
uninstall:
  method: rm-rf-folder
  residual_paths:
    - ~/Library/LaunchAgents/com.myicor.mypka-slack-listener.plist
    - Team Knowledge/SOPs/SOP-slack-incoming-routing.md
    - Team Knowledge/SOPs/SOP-slack-post-message.md
    - Team Knowledge/SOPs/SOP-slack-listener-health.md
    - Team Inbox/slack-incoming/
    - Team Inbox/slack-outgoing/
```

### Example 3 — `connector` (Notion-style, illustrative)

```yaml
name: Notion Connector
slug: notion-connector
version: 1.0.0
description: OAuth-authenticated Notion API connector. Mack uses it for imports and live reads.
category: connector
expansion_type: connector
requires_scaffold_version: ">=1.7.0 <2.0.0"
requires_agents: [Larry, Mack, Silas]
license: proprietary
author: myICOR

adds_sops:
  - { default_owner: Mack, file: SOP-notion-fetch.md }
env_vars:
  - { key: NOTION_TOKEN, description: "Notion internal integration token", required: true, sensitive: true }
mcp_servers:
  - name: notion
    command: npx
    args: ["-y", "@notionhq/notion-mcp-server"]
    env_vars: [NOTION_TOKEN]
post_install_steps:
  - "Create an integration at https://www.notion.so/profile/integrations and paste the token into .env."
  - "Share the workspaces / pages you want Larry to access with the integration."
post_install_validation:
  - { type: "shell", cmd: "test -n \"$NOTION_TOKEN\"", expect_exit: 0 }
```

---

## Conventions

- **Folder name = `slug`.** No exceptions.
- **Trinity files at root:** `expansion.yaml`, `README.md`, `ADAPT-EXPANSION.md`. The `ADAPT-EXPANSION.md` is the LLM-facing operating manual (what to do when this Expansion is invoked).
- **Token files never committed.** `.env.example` is committed; `.env` is gitignored and chmod 600 by the install script.
- **SOPs ship as files in the Expansion folder, not pre-numbered.** The install workstream auto-numbers them into the your myPKA. Filename inside the Expansion is descriptive (`SOP-slack-post-message.md`); the installer renames to the next free `SOP-NNN-…` slot.
- **Agent folder names follow `<Name> - <Role>`** to match scaffold convention.
- **No code at the scaffold root.** All Expansion code stays inside the Expansion folder. `runtime/` for long-lived processes; `scripts/` for installers and starters.

---

## Security considerations

| Concern | Rule |
|---|---|
| Token storage | Always env vars in the Expansion's `.env`. Never inline in `expansion.yaml`. Never logged. |
| Sensitive env display | `sensitive: true` env vars are echoed masked and never written to session-logs. |
| Manifest tampering | Tier-2 (myICOR-issued) Expansions are hash-pinned in the canonical `.trusted-sources` registry — maintained in the private `mypka-expansions` repo and generated by the release pipeline. Vex audits before the hash is pinned. Hash mismatch → Larry refuses install. |
| Outbound network defaults | Connectors and runtimes that talk to third-party APIs MUST default to least-permissive options. Slack-specific: `unfurl_links: false` and `unfurl_media: false`. Webhook receivers MUST verify signatures. |
| `requires_agents` enforcement | Larry blocks install if a required pre-hired agent is missing. The user is told which Expansion to install first. |
| Vex security pass | Recommended before public release for any Expansion that touches the network or executes long-lived processes. Required before tier-2 hash-pinning. |

The manifest is **informational only**. Its declarations are not verified, enforced, or guaranteed by Paperless Movement S.L. or by Larry beyond hash-pinning at tier-2. The user is solely responsible for evaluating an Expansion's trustworthiness before installation.

---

## Trust model — three tiers

| Tier | Source | Larry's action on detection |
|---|---|---|
| 1 — Bundled | `author: myICOR` and ships in scaffold | Auto-trust. No prompt. (None ship in v1.7.) |
| 2 — myICOR-issued | `author: myICOR`, manifest hash matches the canonical `.trusted-sources` registry (in `mypka-expansions`, pipeline-generated) | Calm announcement. Auto-trust on hash match; warn on mismatch. |
| 3 — Community / unknown | Anything else | Interactive prompt: declared permissions + three actions (`trust` / `skip` / `inspect`). Decision cached in `Expansions/.trust.yaml`. Re-prompt on major version bump. |

Trust is granted to a `(slug, version)` pair. Major version bumps re-prompt.

---

## Naming convention

| Pattern | Use case |
|---|---|
| `slack/`, `app-developer/` | RESERVED for myICOR-issued Expansions. Brand-protected via `author: myICOR` + hash pinning. |
| `community-<name>/` | Community Expansions seeking visibility under the umbrella. |
| `<author>-<name>/` | Default third-party namespace. |

---

## Uninstall expectations

Symmetric to install. The uninstall flow ([[WS-003-install-an-expansion]] §uninstall):

1. Larry detects an uninstall request ("uninstall the Slack Expansion", "remove App Developer pack").
2. Nolan reverses the team merge (removes the Expansion's agents from `Team/`, restores `Team/agent-index.md`).
3. Mack tears down connector wiring (stops runtimes, removes launchd plists, deregisters MCP servers).
4. Silas validates the post-uninstall myPKA state.
5. Larry archives the Expansion folder to `Expansions/_uninstalled/<slug>-<version>/.manifest.json` and writes the session-log entry.

`uninstall.method: rm-rf-folder` plus `residual_paths` is the uninstall contract. Anything not declared in `residual_paths` will be left behind — that's a bug in the Expansion, not the scaffold.

---

## Compatibility — refuse-to-install on mismatch

`requires_scaffold_version` is a semver range checked against the scaffold's `VERSION`. The install workstream refuses to proceed when:

- The field is missing or malformed → `invalid` row in `INDEX.md`, install blocked.
- The scaffold version sits outside the declared range → `incompatible` row, install blocked.
- A required pre-hired agent listed in `requires_agents` is not in `Team/agent-index.md` → install blocked with a "install X first" message.

Larry never silently coerces.

---

## Authoring checklist

Before zipping your Expansion and shipping it:

- Folder name matches `slug`.
- `expansion.yaml` validates against the schema above.
- All required fields present.
- `license` declared; SPDX where possible.
- `requires_scaffold_version` is honest. Test against the scaffold versions you claim.
- `env_vars` match what the runtime/connector actually reads.
- `adds_sops` files exist in the Expansion folder and are LLM-agnostic.
- `adds_agents` folders match `Team/<Name> - <Role>/AGENTS.md` shape.
- `uninstall.residual_paths` lists every path written outside the Expansion folder.
- `README.md` at the folder root: human-facing, in the user's voice, what it does + how to remove it.
- `ADAPT-EXPANSION.md` at the folder root: LLM-facing operating manual.
- Optional but recommended: `INSTALL.md` walking the user through any external setup (creating an OAuth app, generating tokens, etc.).
- Vex security pass before tier-2 hash pinning.

---

## What the OSS scaffold does NOT ship

- No Expansion code in this repo. Ever.
- No Expansion binaries.
- No Expansion manifests beyond the empty `INDEX.md` template.

Expansions live in their own private repos. The OSS scaffold ships only this spec, the contract, and Larry's discovery routine + WS-003 install workstream.
