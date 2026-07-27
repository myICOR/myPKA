# Changelog

All notable changes to the myPKA scaffold are tracked here. Versions follow semver: MAJOR for breaking structural changes, MINOR for additions, PATCH for fixes.

## [5.1.2] - 2026-07-27

**The Slack Expansion is discontinued.** myICOR no longer offers or supports it. Its pin is gone from the shipped trust registry, every scaffold surface that presented it as an available official pack has been reworded, and the security gate now has an explicit way to say "withdrawn" instead of falling back to the much weaker "not pinned yet." No structural changes; nothing in your folder moves.

> **This is not a security advisory.** No vulnerability was found in the pack, nothing was exploited, and no data leaked. It is retired because an always-on background listener holding live Slack workspace tokens is more than we are willing to keep standing behind, and because it was the most complicated thing we shipped. There is no newer version to move to: the supported path is to retire it, not to upgrade.

> **If you already run it, nothing breaks and nothing is removed.** `Expansions/*/` is user state and the scaffold updater never touches it. Your installed pack keeps running exactly as it did. What changes is that it is unsupported, no longer downloadable, and a fresh install is now refused by the security gate. To retire it: stop the listener (`Expansions/slack/scripts/uninstall.sh`, or unload `~/Library/LaunchAgents/com.mypka.slack-listener.plist`), then **revoke the tokens at Slack**, which is the step that actually matters. Open `api.slack.com/apps`, select your app, delete it: that invalidates the `xoxb` and `xapp` tokens in one move and removes the bot from your workspace. Deleting the local `.env` does none of that, because a copy survives in backups and the bot stays installed. Then clear `Expansions/slack/` and, if you do not want the captured message history, `Team Inbox/slack-incoming/` and `slack-outgoing/`. [[WS-003-install-an-expansion]] §Uninstall walks the scaffold side with you, and the full notice ships in `Expansions/.trusted-sources`.

### Removed

- **`slack@1.0.6` is no longer pinned in `Expansions/.trusted-sources`.** The shipped file is a mirror of the versions currently served, and Slack is no longer one of them. Historical Slack pins remain in the canonical registry in the private `mypka-expansions` repo: that registry is an append-only audit record, and members who still hold a downloaded artifact must keep being able to verify its bytes.
- **Slack removed from the roadmap and membership surfaces in `WAY-FORWARD.md`.** The "Slack integration" line in the AI Library section and the Slack mention in the out-of-scope list both described an offering that no longer exists.

### Added

- **A `WITHDRAWN` block in `Expansions/.trusted-sources`, and a matching resolution in WS-003 §2 check 1.** Removing a pin on its own is not a withdrawal signal. An absent pin resolves YELLOW, which means "this version has not been audited yet, override if you are sure" and reads as a temporary state a member is invited to click past. That is the opposite of what withdrawal means. A slug named in the new `WITHDRAWN` block now resolves **RED with no override path**, regardless of hash: a matching hash proves the bytes are authentic, never that the pack is still supported. Line format is `<slug> WITHDRAWN <YYYY-MM-DD> reason=<token>`, deliberately without a `sha256=` field so it can never be mistaken for a pin.
- **The withdrawal notice ships with the pin registry and is the gate's source text.** The comment block above each withdrawn slug is what the gate reads out, rather than wording improvised per session. WS-003 §2 now carries hard rules for that copy: withdrawal is a posture decision, so the gate never claims a vulnerability was found, never manufactures urgency, and never points a member at a newer version of a withdrawn pack. Where the notice names credential-revocation steps, the gate delivers them verbatim, because removing local files does not revoke a credential a third-party service still honors.
- **The reinstall-your-own-copy case is answered in the notice, not with an override.** A member restoring after a machine move still gets RED. Someone who already holds live third-party credentials is not made safer by a smooth reinstall, so the answer is the offboarding steps; the retained pin in the canonical registry stays available for byte-verifying the copy they hold.
- **A withdrawn pack that is already installed gets a status line, once.** The install gate only fires on an install, so it never reaches the person still running the pack. Larry's Expansion Discovery now marks that row `withdrawn` in `Expansions/INDEX.md` with the withdrawal date, and states the notice a single time; if the previous INDEX already recorded it as withdrawn, he stays quiet. No re-install flow, no folder changes, no recurring reminder. Your installed Expansions are yours, and withdrawal never reaches in and removes anything.

### Changed

- **The `slack/` slug stays RESERVED** in the `Expansions/docs/expansion-spec.md` naming table, now marked withdrawn. Withdrawing a pack must not free its slug: an unreserved `slack/` could be claimed by a third-party Expansion trading on the myICOR name. Reservation plus refusal is the correct end state, not deletion.
- **Expansion-spec Example 2 is now a generic, clearly illustrative chat-relay runtime** (`acme-chat-relay`, MIT, third-party author) instead of the Slack Expansion manifest. The old example doubled as advertising, carried a `homepage:` URL that no longer resolves, and presented `author: myICOR` on a pack that is no longer issued. Every schema feature it demonstrated (runtime block, launchd plist, sensitive env vars, `residual_paths`) is preserved.
- **Slack dropped from the install-trigger examples** in root `AGENTS.md`, `Team/Larry - Orchestrator/AGENTS.md`, and WS-003's trigger contract, and from Larry's AI Library answer. The triggers themselves are unchanged; only the illustrative pack name moved to one that is actually offered.
- **The manifest-tampering security table in the Expansion spec gains a "Withdrawn packs" row**, and root `AGENTS.md` plus Larry's Expansion Discovery routine now name the withdrawn-slug refusal alongside the hash check.

### Not changed, deliberately

- **Generic Slack references survive.** The WS-003 §2 check 5 and spec security rule about `unfurl_links: false` / `unfurl_media: false` are guidance for anyone building a chat relay against the Slack API, not an offer of a myICOR pack. Prose examples elsewhere in the folder that merely name Slack as a tool are untouched.
- **Historical CHANGELOG entries are not rewritten.** Earlier releases that pinned `slack@1.0.2` / `1.0.3` / `1.0.6` describe what actually shipped on those dates. A changelog that edits its own past is worth less than one that does not.

### Version files

- `manifest.json` → `scaffold_version` `5.1.2` (authoritative SSOT), `breaking: false`.
- `VERSION` → `5.1.2` (mirror of the manifest).
- `.scaffold-version` → `5.1.2` (mirror of the manifest).

## [5.1.1] - 2026-07-23

**Consolidation patch.** The bundled Cockpit's source of truth moves into this repository and the release pipeline now builds and verifies it on every cut; the bundled Cockpit becomes **1.4.1** (docs-only patch: the 1.4.0 install docs still described a standalone download that never existed). No functional changes for members beyond corrected install docs.

### Changed

- **The myPKA Cockpit's source of truth now lives in this repository** at `Expansions/mypka-cockpit/` (consolidation, 2026-07-23). What ships is what you see: the bundled Cockpit folder IS the live source, not a copy synced from elsewhere. The historical `myICOR/mypka-cockpit` repository is archived as read-only history, and the cross-repo sync machinery is retired. Every scaffold release now builds and verifies the Cockpit from this in-repo source before the scaffold artifact is cut: slug/version lockstep across `expansion.yaml` / `package.json` / `web/package.json`, a fresh `web/dist` build as a verification gate (the scaffold still ships source-shape; your assistant builds on install), a byte-stable deterministic pack check, and a hard match between `expansion.yaml` and its `Expansions/.trusted-sources` pin. Licensing is unchanged: the Cockpit folder remains under the myICOR Cockpit Personal-Use License (based on PolyForm Noncommercial 1.0.0) per its own `LICENSE` file and the per-path scheme in `LICENSE-MAP.md`; the rest of the scaffold stays CC BY-NC-SA 4.0.
- **Bundled Cockpit docs refreshed** to the bundled-distribution wording (Cockpit `CHANGELOG.md`, `INSTALL.md`, `README.md`): the Cockpit ships inside the scaffold, there is no separate download or checksum step, and its version bumps ride the scaffold release train — released as Cockpit **1.4.1** so no two artifacts ever claim the same version with different bytes.

## [5.1.0] - 2026-07-23

**Install-friction release.** Closes the five scaffold-side findings from the end-to-end member install simulation of v5.0.1 (deliverable 14, 2026-07-23). Conducted as part of Marshall's release train; the bundled Cockpit updates to 1.4.0 on the same train (see the Cockpit's own CHANGELOG).

### Added

- **`Expansions/.trusted-sources` ships with the scaffold.** A read-only mirror of the canonical pin registry (private `mypka-expansions` repo, pipeline-generated), carrying the current official-pack pins: `app-developer@1.0.4`, `converter-pack@1.1.2`, `designer-pack@1.1.2`/`1.1.3`, `slack@1.0.6`, `handwritten-collaboration-loop@1.0.2`, and `mypka-cockpit@1.4.0` (the bundled Cockpit's first-run install now also rides the GREEN auto-trust path). This makes the WS-003 §2 GREEN (auto-trust) path reachable for members out of the box — previously every official pack install ended in a YELLOW security override, training members to click through the gate. The file is on the updater's framework allow-list, so pins refresh with each scaffold update.
- **WS-003 §3.6 "Host subagent shims".** The install workstream now explicitly creates the host-layer shim for each pack-installed agent (idempotent, per activated host, pointer-only — same walk as the activation prompt's host-binding step). Previously a by-the-book install left new specialists rostered but undispatchable until the user happened to re-activate. Failure rollback is now §3.7 and includes shims.

### Fixed

- **Post-install validator honesty trap.** The agnosticism audit no longer scans `Team Knowledge/session-logs/**` (user-generated operational record — a session log truthfully documenting shim work by path must not fail the member's validator), `Expansions/**`, or the `Team/<folder>/AGENTS.md` contracts of agents installed by an Expansion (pack-shipped bytes must not be able to fail or warn the member's scaffold validator; folders are read from the installed-pack manifests). This also removes the permanent 1-WARN floor the served Designer Pack's Pixel contract caused.
- **Personalization scope was self-contradictory.** ADAPTER-PROMPT step 4 said "replace every `{{USER_NAME}}` token" while four files carry instructional mentions of the token that must survive, and two genuine tokens live inside an `AGENTS.md` that Hard Rule 1 forbids touching. The step now defines the exact replacement scope (everything except the four documentation files: `ADAPTER-PROMPT.md`, root `AGENTS.md` Personalization section, `CHANGELOG.md`, the tool-pointer file), scopes the already-personalized grep check accordingly, and names the substitution as the single sanctioned `AGENTS.md` edit. Hard Rule 1 also now defers explicitly to canonical-Workstream instructions (e.g. WS-003 roster updates), removing the install-time contradiction.

### Changed

- WS-003 §2 trust-tier check, root `AGENTS.md` security-gate rule, and `Expansions/README.md` reworded around the shipped pin registry (local pins first, Expansion Packs page hash as fallback for newer versions).

## [5.0.1] - 2026-07-23

**Install-experience patch.** A fresh v5.0.0 download failed its own `validation-script.sh` out of the box (1 FAIL, 2 WARN) and the canonical Expansion-install path mandated an agent that no longer ships with the base scaffold. This patch makes a fresh download validate clean (exit 0, zero FAIL, zero WARN) and closes the reported install-path gaps. No structural changes.

### Fixed

- **Fresh-download validation failure (community report, 2026-07-15).** Five documentation lines that legitimately cite the host-adapter layer (`Team Knowledge/Guidelines/INDEX.md` GL-005 row; four shim-authoring lines in `Team/Nolan - HR/AGENTS.md`) now carry the validator's own `agnosticism-audit:allow` marker. The agnosticism-audit no longer hard-fails a clean install.
- **Expansion security gate referenced a non-shipped agent (community report, 2026-07-10).** WS-003 mandated Vex as the install security gate, but Vex ships with the App Developer Pack (a membership Expansion), not the base scaffold. WS-003 §2, its owner line and edge-case table, root `AGENTS.md`, Larry's contract, and the Workstreams INDEX now carry the fallback: security review routes to Vex if installed (e.g. via the App Developer Pack); otherwise Larry executes the §2 security checklist himself before any Expansion install and records the verdict. The gate stays hard; the missing-agent dependency is gone.
- **Internal session log leaked into the download.** Removed `Team Knowledge/session-logs/2026/06/2026-06-22-13-26_silas_governance-docs-mirror-tables.md`, a myICOR-internal dev-instance log that shipped inside every member download. Session logs seed empty again (`2026/05/.gitkeep`).
- **Validator check 7 matched its own documentation.** The path-based-task-wikilink check flagged the `CHANGELOG-MIGRATION.md` checklist line that quotes the forbidden pattern in backticks. Backtick-quoted documentation citations are now excluded.
- **Validator MCP-caveat check over-breadth.** Generic prose about MCP servers ("MCP servers (if any)", "5.2 MCP servers", "set up MCP servers", "deregister MCP servers", "MCP server registrations") no longer trips the named-MCP-server warning. The four genuinely named MCP references (Larry's myICOR MCP, Mack's Tana/Mem/Readwise MCP examples) now carry explicit harness-config caveats.
- **Stale agent names in core docs.** `GL-002` no longer names Iris for frontmatter audits (Silas runs them), `SOP-list-open-tasks`'s example output no longer narrates Pixel as active (now Penn), and the Workstreams INDEX no longer uses a Charta+Pixel handoff as its canonical example.

### Changed

- **`requires_scaffold_version` removed from the Expansion manifest spec** (deliberate backport of the 2026-06-16 spec change from the private reference instance). The field is no longer required and no longer enforced anywhere: WS-003 §1, Larry's Expansion Discovery, and `Expansions/docs/expansion-spec.md` (required-fields table, examples, compatibility section, authoring checklist) all drop it. Manifests that still carry the field are tolerated; the field is ignored and never blocks an install. Compatibility testing is the Expansion author's responsibility, not an install-time gate.

### Version files

- `manifest.json` → `scaffold_version` `5.0.1` (authoritative SSOT), `breaking: false`.
- `VERSION` → `5.0.1` (mirror of the manifest).
- `.scaffold-version` → `5.0.1` (mirror of the manifest).

## [5.0.0] - 2026-07-07

**The scaffold returns to its basic shape: the six core specialists plus the bundled myPKA Cockpit, free.** The two agent packs that earlier downloads bundled into this repo (the App Developer Pack and the Designer Pack) are unbundled. They are now Expansion Packs, part of the myICOR membership, available on the **Expansion Packs page** in the myICOR app. The scaffold itself, including the Cockpit, stays free: it is the basic structure you need to build your AI team, with the core agents everyone needs, and you can build whatever you like on top of it.

> **BREAKING.** The default download's team roster and SOP/Guideline set change shape versus 4.1.1. **Existing folders lose nothing:** `Expansions/*/` is user-state, the scaffold updater never removes an installed pack, and packs you already run keep working and update via their own Expansion update paths. Fresh downloads simply no longer include the two agent packs.

### Removed

- **App Developer Pack unbundled** (was preinstalled since 3.0.0): the `Team/` folders and `.claude/agents/` shims for **Felix** (Frontend Developer), **Vex** (Security Engineer), **Vera** (QA Specialist), their SOPs (`SOP-003`, `SOP-004`, `SOP-005`), and the pack source under `Expansions/app-developer/`. Available with the myICOR membership on the Expansion Packs page.
- **Designer Pack unbundled** (was preinstalled since 3.0.0): the `Team/` folders and `.claude/agents/` shims for **Iris** (Design System Architect), **Charta** (Infographic Designer), **Pixel** (Visual Specialist), their SOPs (`SOP-006` through `SOP-009`), the `GL-003-design-system` Guideline, and the pack source under `Expansions/designer-pack/`. Available with the myICOR membership on the Expansion Packs page.
- **`Expansions/.trusted-sources`** no longer ships in the repo. The canonical hash registry is maintained in the private Expansion release pipeline, and integrity hashes surface on the Expansion Packs page at download time. The bundled Cockpit ships in-tree and needs no install-time hash check. (This makes the existing statement in `Expansions/README.md` accurate.)

### Changed

- **Team roster: 12 → 6 specialists.** Root `AGENTS.md`, `Team/agent-index.md`, and the Team Knowledge indexes list the six core specialists: **Larry, Nolan, Pax, Penn, Mack, Silas**. The team grows by hiring through Nolan or by installing Expansion Packs via [[WS-003-install-an-expansion]] (the mechanism is unchanged and stays built in).
- **The myPKA Cockpit stays bundled and free** at `Expansions/mypka-cockpit/` (cockpit version `1.2.1`, unchanged). First-run activation still builds it under the single upfront consent (ADAPTER-PROMPT § 8-ter); the agent-pack install/verification steps are gone.
- **SOP/Guideline numbering:** SOP-003 through SOP-009 and GL-003 are vacated by the unbundled packs. A pack installed later reclaims free slots at install time per WS-003; do not back-fill them locally without coordinating.
- **README, AGENTS.md, CLAUDE.md, ADAPTER-PROMPT.md, LICENSE-MAP.md, Expansions/INDEX.md** rewritten for the basic-plus-Cockpit shape. No copy anywhere claims the agent packs are bundled, preinstalled, or free.

### Fixed

- **`update_check.remote_version_url` pointed at a non-existent repository** (`myICOR/mypka-scaffold`), so the boot-time update check never found the remote version (issue #15). It now points at `https://raw.githubusercontent.com/myICOR/myPKA/main/VERSION`.

### Version files

- `manifest.json` → `scaffold_version` `5.0.0` (authoritative SSOT), `breaking: true`; `expansions.items` reduced to the bundled Cockpit.
- `VERSION` → `5.0.0` (mirror of the manifest).
- `.scaffold-version` → `5.0.0` (mirror of the manifest).

## [4.1.1] - 2026-06-23

**Cockpit day-planner drag-and-drop fix (critical).** A patch release that ships a
fixed bundled myPKA Cockpit. Two day-planner drag-and-drop defects are resolved: you
can now drop a task before or after a calendar event in a day-half lane, and dragging
an already-placed task up or down within the same column now lands and persists. This
is a Cockpit fix only: there are no structural changes to the scaffold and no changes
to your PKM, journals, tasks, or any of your own content.

### Fixed

- **Bundled Cockpit day-planner drag-and-drop fixed** (`Expansions/mypka-cockpit/`,
  cockpit version `1.2.0` -> `1.2.1`). Unified events+tasks position space (drop a
  task before/after an event) and direction-aware same-column reorder. Ships a new
  migration `008-unified-position-space.sql` that applies automatically on the next
  Cockpit boot via the planner's idempotent, append-only migration runner. No
  behavior changes outside the planner; no new dependencies.
- **Version mirrors bumped to `4.1.1`** (`manifest.json` is authoritative; `VERSION`
  and `.scaffold-version` mirror it). The bundled Cockpit's `expansion_yaml_version`
  in `manifest.json` is updated to `1.2.1` to match.

### Notes

- The Cockpit is a runtime Expansion and is updated on its own version, separate from
  the scaffold version. The scaffold self-updater never overwrites Cockpit code; it
  defers to the Cockpit's own update path. This release simply ships the newer Cockpit
  inside the scaffold download.

## [4.1.0] - 2026-06-23

**The Graphite Cockpit.** The bundled myPKA Cockpit gets a full visual redesign. Its default dark theme moves from a warm charcoal to a cool, near-black **Graphite** canvas, with a cool near-white text ramp and **brass retained as the single signature accent**. The result is a calmer, more precise instrument that keeps the one colour that points (brass) while adopting a quieter, more neutral field around it.

This is a visual-only release: there are no structural changes to the scaffold, no changes to your PKM, journals, tasks, or any of your own content, and nothing new to learn. If you run the Cockpit, the next time you build it you will see the new look.

### Changed

- **Bundled Cockpit redesigned to the "Graphite" dark theme** (`Expansions/mypka-cockpit/`, cockpit version `1.1.0` -> `1.2.0`). A pure CSS reskin: a design-token retune (`web/src/index.css`) plus chrome refinements (`web/src/cockpit.css`). No behavior, data, API, or schema changes; no new dependencies. The Cockpit web bundle is built at install time, so the new theme appears on your next Cockpit build.
- **Version mirrors bumped to `4.1.0`** (`manifest.json` is authoritative; `VERSION` and `.scaffold-version` mirror it). The bundled Cockpit's `expansion_yaml_version` in `manifest.json` is updated to `1.2.0` to match.

### Notes

- The Cockpit is a runtime Expansion and is updated on its own version, separate from the scaffold version. The scaffold self-updater never overwrites Cockpit code; it defers to the Cockpit's own update path. This release simply ships the newer Cockpit inside the scaffold download.

## [4.0.0] - 2026-06-22

**The self-updating, model-agnostic, self-improving release.** myPKA stops being a folder you manually re-sync and becomes a product that can update itself. The line between the framework (ours, upgradable) and your own state (yours, sacred) is now written down as machine-readable data, so an update can confidently overwrite our files while never touching yours. One command (or one sentence to your assistant) shows you exactly what will change before anything happens, and the scaffold tells you on boot when a new version exists.

> **BREAKING.** This is the first myPKA release that is not purely additive. It introduces a real framework/user-state seam. Members on 3.1.0 take a one-time bridged update that lays down `manifest.json` and the `.mypka/` control folder. The bridge is numbered, idempotent, and auditable: see the `3.1.0 -> 4.0.0` recipe in `CHANGELOG-MIGRATION.md`. Your own content (PKM, journals, tasks, session logs, Expansions, secrets, databases) is never moved or modified by the bridge.

### Added

- **A machine-readable `manifest.json` at the scaffold root: the new version SSOT and the framework/user-state seam as data.** It declares `scaffold_version` (now authoritative), `framework_paths` (the allow-list of files the updater MAY overwrite), and `user_state_paths` (the sacred list the updater will NEVER write). Every fact about "what is ours vs. what is yours" now lives in one inspectable file instead of in tribal knowledge.
- **A one-command updater: `/update-scaffold` (and the portable trigger "update myPKA"), backed by a plain script `scripts/update-scaffold.py`.** The script is python3 stdlib only (no pip, no npm) so it runs without an LLM. It diffs only `framework_paths`, prints a plain-English plan ("3 new SOPs, 1 changed guideline, 0 of your files touched"), is **dry-run by default**, applies only on `--apply`, **backs up any locally modified framework file to `.mypka/backups/<timestamp>/` before overwriting** (never a silent overwrite of your edit), refuses to write outside `framework_paths`, and is fully offline-safe and fail-closed.
- **A boot-time update notification: `scripts/check-version.py`.** Announced-on by default (Tom's decision). It is the only network reach in the update core: it fetches a single version string over HTTPS, read-only, **sends no data about you or your vault**, fails silently offline, and prints one line only when a newer version exists. It never downloads or applies anything. Disclosed in the script header and in `manifest.json` under `update_check`; turn it off with `update_check.enabled: false`.
- **A separable cockpit-code update path.** The Cockpit (and every Expansion) is versioned on its own `expansion.yaml` SemVer, not on the scaffold version. The scaffold updater detects a behind cockpit and **defers** to the cockpit's own updater instead of touching Expansion code. The cockpit updater lifecycle is specified in `Expansions/mypka-cockpit/scripts/UPDATE-COCKPIT.md` (marked clearly as a SPEC: the working updater plus versioned DB migrations are still to be built and security-reviewed before they ship).
- **The new `model:` frontmatter field** (Silas is adding it to `GL-002` in parallel). This records which model an agent contract was authored/validated against, supporting the LLM-agnostic posture below. Reference `GL-002` for the field's authoritative definition.
- **The LLM-agnostic portable-core / adapter rule, plus an agnosticism audit** (Nolan and Silas are adding the Guideline and the audit Workstream in parallel). The portable core is the model-neutral contract; the adapter layer (for example `ADAPTER-PROMPT.md` and the `.claude/` shims) is where a specific host binds. Reference the new Guideline and the audit once landed.
- **The Team Retro self-improvement Workstream** (Nolan is adding it in parallel): a recurring, structured retro that lets the team improve its own operating knowledge over time. Reference the new `WS` once landed.
- **The `.mypka/` control folder.** A small hidden folder the updater creates on first run, holding `backups/`, an `update-log.txt`, and a copy of the active manifest. It is user-state: never overwritten by an update.

### Changed

- **`VERSION` and `.scaffold-version` are now mirrors, not the source of truth.** They still exist for back-compat with older tooling and both now read `4.0.0`, but `manifest.json` is authoritative. If they ever disagree, `manifest.json` wins (documented in the manifest's `version_files` block).

### Why this is a major version

Until now an update meant "re-download the folder and hope you remembered which files you changed." That works while the folder is purely additive. It breaks the moment we need to ship a changed framework file safely. v4.0.0 draws the framework/user-state boundary explicitly and in data, so the updater can act on it without guessing. That boundary is the breaking change, and it is the foundation every later self-update builds on. The Hermes-Agent lesson applies: separate the engine directory from the state directory, and never write user data into the engine.

### Version files

- `manifest.json` → new; `scaffold_version` `4.0.0`, authoritative SSOT.
- `VERSION` → `4.0.0` (was `3.1.0`; now a mirror of the manifest).
- `.scaffold-version` → `4.0.0` (was `3.1.0`; now a mirror of the manifest).

## [3.1.0] - 2026-06-22

**The Cockpit gets a "My AI Team" section: browse your team, session log, and governance docs (Workstreams / SOPs / Guidelines) right inside the local viewer.** This is a Cockpit-feature release — the base scaffold structure is unchanged. It also folds in the v3.0.1 slug fix. New features ship as **source**; the Cockpit rebuilds its UI bundle (`web/dist`) on first run, so an existing install picks the features up by pulling the new files, regenerating the mirror, and rebuilding/restarting (steps below).

### Added

- **Cockpit "My AI Team" fly-out menu.** A new sidebar fly-out exposes five team destinations: **Team** (the roster), **Session Log**, **Workstreams**, **SOPs**, and **Guidelines**. Your specialists and your operating knowledge are now first-class navigation in the Cockpit, not invisible to the viewer.
- **Workstreams, SOPs, and Guidelines are now indexed in the `mypka.db` mirror.** `Expansions/mypka-cockpit/scripts/regen-mypka-db.py` gains new tables for the three governance-doc families (`workstreams`, `sops`, `guidelines`), so they are queryable in the mirror and browsable in the Cockpit. **You must re-run the regen for these to populate** (command below).
- **New read-only Cockpit endpoint `GET /api/cockpit/team-knowledge/:family`** (`:family` ∈ `workstreams` | `sops` | `guidelines`), served by the new `Expansions/mypka-cockpit/server/teamKnowledgeApi.js`. Read-only; serves the indexed governance docs to the new list views.

### Changed

- **Session Log and Roster are now separate, full-height pages.** They were previously crammed into a single cramped view; each is now its own route. Team pages use the full viewport height, fixing the content crop.

### Fixed

- **Includes the v3.0.1 fix:** Cockpit Fleeting-Note and Journal capture no longer fails with `title produced an empty slug` for titles made entirely of non-Latin script (Korean / Chinese / Japanese / Cyrillic / Greek / Arabic / Hebrew / Thai), emoji, or punctuation. The capture now falls back to a safe generated slug (`fleeting-<timestamp>` / `<date>-entry`) and preserves the original title in the note. All security guards intact. (Full detail under `[3.0.1]` below.)

### Files of note (so an existing install's LLM can pull just this)

This is a **Cockpit-only** change set — no base-scaffold files change. The new/changed Cockpit files are:

- **New UI views** — `Expansions/mypka-cockpit/web/src/views/SessionLogView.tsx`, `web/src/views/TeamKnowledgeListView.tsx`, `web/src/views/team/SessionLogFeed.tsx`, plus updated `web/src/views/RosterView.tsx` and `web/src/views/FileView.tsx`.
- **Sidebar fly-out + routing + strings** — `web/src/components/Sidebar.tsx`, `web/src/lib/router.ts`, `web/src/App.tsx`, `web/src/lib/strings.ts`, `web/src/cockpit.css`, `web/src/views/team.css`.
- **New server endpoint** — `Expansions/mypka-cockpit/server/teamKnowledgeApi.js` (and its wiring in `server/server.js`).
- **Mirror regen with the new tables** — `Expansions/mypka-cockpit/scripts/regen-mypka-db.py` (plus the contract docs `docs/db-contract.md` and `sqlite-extension/DATA-CONTRACT.md`).

**To pull this into an existing install (no full re-download needed):**

1. Replace/add the Cockpit files listed above with their v3.1.0 versions.
2. **Re-run the mirror regen** to create + populate the new governance tables:
   `python3 "Expansions/mypka-cockpit/scripts/regen-mypka-db.py"`
3. **Rebuild and restart the Cockpit** so the new UI and the new server route load:
   `cd Expansions/mypka-cockpit && npm run serve` (this runs `npm run build` → rebuilds `web/dist` → starts the server).

Note: `web/dist` and `mypka.db` are intentionally **not** shipped in the release archive (both are gitignored, regenerable). The release ships UI **source**; the Cockpit builds `web/dist` on first run and regenerates `mypka.db` from your real scaffold. This is why steps 2–3 are required after pulling.

### Version files

- `VERSION` → `3.1.0` (was `3.0.1`)
- `.scaffold-version` → `3.1.0` (was `3.0.1`)
- `Expansions/mypka-cockpit/expansion.yaml` → `1.1.0` (was `1.0.1`)
- Cockpit `package.json` / `web/package.json` / `package-lock.json` → `1.1.0` (mirror `expansion.yaml`; reconciled — they had drifted at `1.0.0`)
- Cockpit `CHANGELOG.md` adds `[1.1.0]` and renumbers the prior slug-fix entry from the mislabeled `[3.0.1]` to `[1.0.1]` (the Cockpit CHANGELOG tracks `expansion.yaml`, not the scaffold version)

## [3.0.1] - 2026-06-22

**Hotfix: the Cockpit can now create Fleeting Notes and Journal entries for non-Latin / emoji / punctuation-only titles.** Cockpit-only fix — no scaffold-wide structural change. Two server files change; nothing else in the scaffold is touched.

### Fixed

- **The bug.** In the myPKA Cockpit, creating a **Fleeting Note** or a **Journal entry** failed with the error **`title produced an empty slug`** (HTTP 400) whenever the title was made entirely of **non-Latin script** (Korean / Chinese / Japanese / Cyrillic / Greek / Arabic / Hebrew / Thai / etc.), **emoji**, or **punctuation only**. The Cockpit derives the note's filename from the title by slugifying it, and the slugifier is ASCII-only — so a title like `한글 메모`, `中文笔记`, `🎉🎉`, or `!!!` slugified to an empty string and the capture was rejected purely on the title's character set.
- **The fix.** When a title slugifies to empty, the Cockpit now **falls back to a safe generated slug** instead of refusing the capture: `fleeting-<YYYY-MM-DD-HHMMSS>` for a Fleeting Note and `<date>-entry` for a Journal entry. The **original title is preserved in the note** — a Fleeting Note prepends it as an H1 (so it is recovered as the note's title), and a Journal entry records it verbatim in the `title:` frontmatter field. ASCII titles are unchanged (`Test Note` → `test-note`, `café` → `cafe`). All security guards are intact: a path-like title (`..`, `/`, `\`, NUL) is still refused, reserved names are still reserved, and there is still no silent overwrite.

### Files changed (exactly two)

- `Expansions/mypka-cockpit/server/workbench.js` — Fleeting Notes create path (`fleeting-<timestamp>` fallback + H1 title preservation).
- `Expansions/mypka-cockpit/server/journalEntries.js` — Journal create path (`<date>-entry` fallback; title preserved in `title:` frontmatter).

A regression test (`Expansions/mypka-cockpit/server/workbench.slug.test.mjs`) and the Cockpit's own `Expansions/mypka-cockpit/CHANGELOG.md` accompany the fix.

### How to pull this into an existing install

This is a **Cockpit-only** fix. If you already run the Cockpit and only want this fix, you do **not** need to re-download the whole scaffold:

1. Replace these two files with the v3.0.1 versions (or apply the slug-fallback change to each):
   - `Expansions/mypka-cockpit/server/workbench.js`
   - `Expansions/mypka-cockpit/server/journalEntries.js`
2. **Restart the Cockpit** (stop the local server and start it again) so the new server code loads.

No `mypka.db` regeneration, no team change, and no other scaffold edits are required. Existing notes are unaffected.

### Version files

- `VERSION` → `3.0.1` (was `3.0.0`)
- `.scaffold-version` → `3.0.1` (was `3.0.0`)
- `Expansions/mypka-cockpit/expansion.yaml` → `1.0.1` (was `1.0.0`)

## [3.0.0] - 2026-06-21

**Historical entry (download withdrawn).** v3.0.0 introduced the bundled download era: it added the myPKA Cockpit v1.0.0 at `Expansions/mypka-cockpit/` (which remains bundled and free today) and it bundled two agent packs (App Developer: Felix/Vex/Vera + SOP-003..005; Designer: Iris/Charta/Pixel + SOP-006..009 + GL-003) directly into the download. As of **5.0.0** those two agent packs are unbundled and available with the myICOR membership on the Expansion Packs page; the bundled-era release downloads (3.0.0 through 4.1.1) were withdrawn. This release also relicensed the base scaffold to **CC BY-NC-SA 4.0** and introduced `LICENSE-MAP.md` and the Cockpit's own license (myICOR Cockpit Personal-Use License, PolyForm-Noncommercial-based), which remain in force.

### Version files

- `VERSION` → `3.0.0` (was `2.4.0`)
- `.scaffold-version` → `3.0.0` (was `2.4.0`)

## [2.4.0] - 2026-06-18

**Ships local version history out of the box.** First-time initialization now offers to switch on local git versioning — a plain-language "time machine" for the folder — so new downloads get a roll-back safety net from day one. The offer is opt-in but strongly recommended: the adapter asks the user once, explains in non-technical terms that the history stays entirely on their computer (nothing uploaded or shared unless they later deliberately choose to) and that it lets them undo changes and roll back if an edit ever breaks something, and on yes runs a local-only `git init` + initial commit. The shipped `.gitignore` is hardened so that "nothing is shared / safe rollback" is actually true — it now excludes secrets, the derived database mirror, dependencies, build artifacts, and logs while still tracking the keys-only `.env.example`. The `VERSION` / `.scaffold-version` mismatch left by the 2.3.0 release is reconciled.

### Added

- **ADAPTER-PROMPT new step 5 "Offer local version history."** Inserted immediately after personalization (step 4) and before the tool-pointer-file step, so the first commit captures a clean, personalized baseline and everything after it is versioned. The adapter asks the user exactly once, in plain language, framing git as a local time machine / version history; covers (a) it stays entirely on the user's machine, nothing uploaded or shared unless they later deliberately choose to, (b) it lets them undo changes and roll back to any earlier state if an edit breaks something, (c) it is strongly recommended from the very start. Opt-in but recommended-yes; declining is fine and re-offer on a later activation is allowed. On yes: verify git is available, confirm the protective `.gitignore` is in place **before** committing, then `git init` → `git add -A` → `git commit -m "chore: initialize myPKA version history"`, with **no remote and no push** (local only). Idempotent: if a `.git` folder already exists, skip init and note it. Host-agnostic (plain shell `git`); hosts that cannot run shell commands hand the user the exact commands to paste. Includes a safety note that any later off-machine backup/sync must be a deliberate, reviewed choice using a **private** repo because the folder holds personal data.
- **`VERSION HISTORY:` report-back field** in ADAPTER-PROMPT — the adapter now reports the outcome of the version-history offer as `initialized` | `declined` | `already a git repo`.

### Changed

- **`.gitignore` hardened.** Previously OS/editor cruft only (`.DS_Store`, `__MACOSX/`, `*.swp`, Obsidian workspace/cache). Now also excludes: `.env` / `.env.*` at any depth (e.g. installed-Expansion secrets at `Expansions/<slug>/.env`) with a negation that keeps the keys-only `.env.example` template tracked; local MCP server configs that may embed credentials (`.mcp.json`, `**/.mcp.json`, `.cursor/mcp.json`); private keys/certs (`*.key`, `*.pem`, `id_rsa`); the derived SQLite mirror and sidecars (`*.db`, `*.db-wal`, `*.db-shm`, `*.sqlite`, `*.sqlite3`); dependencies and build artifacts (`node_modules/`, `dist/`, `build/`, `.next/`, `.cache/`, `*.tsbuildinfo`); and logs/runtime state (`*.log`, `logs/`, `tmp/`, `*.pid`). This is the safety dependency for the version-history offer: the user-facing "nothing is shared / safe rollback" claim is only true if the very first commit cannot capture secrets or runtime state.
- **ADAPTER-PROMPT step renumbering.** Former steps 5–9 become 6–10; the slash-command sub-step heading `### 7-bis` becomes `### 8-bis`; the "skip to step 5" personalization cross-reference and the step-10 roster-confirmation line are updated accordingly.

### Migration

Existing vaults need no action. Local version history is opt-in and can be turned on at any time — re-run the adapter prompt (it will offer it), or run it yourself from the folder root with the shipped `.gitignore` already in place: `git init` → `git add -A` → `git commit -m "chore: initialize myPKA version history"` (local only — do not add a remote or push). Vaults that are already git repos are detected and left untouched. If you upgrade an existing clone, refresh your local `.gitignore` from this release so the hardened exclusions apply before your next commit.

### Version files

- `VERSION` → `2.4.0` (was `2.3.0`)
- `.scaffold-version` → `2.4.0` (reconciliation: the 2.3.0 release bumped `VERSION` to `2.3.0` but left `.scaffold-version` at `2.2.0`; both are now realigned at `2.4.0`)

## [2.3.0] - 2026-06-03

**Aligns the "My Life" doctrine with the canonical ICOR / "PKM like a Pro" model.** The scaffold previously framed My Life as five peer buckets (Topics, Habits, Goals, Projects, Key Elements). It is now corrected to **four buckets — Key Elements, Projects, Habits, Topics — plus Goals as the operating layer**, with the relational laws the framework actually runs on made explicit and the schema updated to encode them. Adds the canonical teaching examples (a "lose 20 kg → Health" Goal carried by a Project or Habit; a "French" Topic that graduates into a Key Element) so any LLM reading the scaffold grasps the rules. Additive to the schema; one rule (Goal anchor) becomes required — see Migration.

### Changed

- **`PKM/My Life/README.md`, `INDEX.md`, and all six bucket `INDEX.md`s** — rewritten from "five buckets/shapes" to "four buckets + the Goals operating layer." State the **anchoring law** (every Goal anchors to exactly one Key Element — never a Project, never a Topic), the **carrier rule** (a Goal is achieved through exactly one of two sibling shapes — a Project OR a Habit; no third), **Topic → Key Element promotion** (and the reverse: a Key Element that leaves your life is archived), and the **filter test** (content fitting none of the four buckets doesn't belong in the PKM). Projects and Habits are reframed as *thinking spaces, not trackers*.
- **`Team Knowledge/Guidelines/GL-002-frontmatter-conventions.md`** — encodes the doctrine: Goal `key_element` is now **required and Key-Element-only**; the Project-or-Habit carrier rule is documented; new optional fields land for the promotion pipeline.
- **`Team Knowledge/Workstreams/WS-001-daily-journaling.md`** — Step-4 routing now enforces the anchor + single-carrier rules, runs the filter test before stubbing a My Life note, and proposes Topic → Key Element promotion when a Topic becomes a measurable pursuit.
- **`AGENTS.md`** (root) and **`Team/Penn - Journal Writer/AGENTS.md`** — taxonomy + routing map corrected to four-buckets-plus-Goals-layer, pointing to GL-002 for the relational doctrine.

### Added

- **`promoted_to` + `lifecycle`** (exploring | promoted | dormant) optional fields on **Topic** — encode the Topic → Key Element promotion pipeline.
- **`promoted_from` + an `archived` status** on **Key Element** — the reverse pointer and the "left my life" state.
- **`linked_goals`** on **Habit**, and a documented **`linked_topics`** on **Project** — the carrier and context relations.
- Canonical illustrative examples woven into GL-002, the templates, and the My Life docs (the "lose 20 kg → Health" Goal and the "French" Topic-to-Key-Element promotion).

### Migration

- Existing vaults: every **Goal** note now requires a `key_element` field pointing to a Key Element (never a Project or Topic). Add the anchor to any Goal that lacks one. All other changes are additive optional fields — no action required.

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
