# Changelog

All notable changes to the myPKA Cockpit are documented here.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version in `expansion.yaml` is the single source of truth for a release; the
root `package.json` and `package-lock.json` mirror it.

## [Unreleased]

### Changed

- **Distribution: the Cockpit ships inside the myPKA scaffold again** (Tom
  ruling 2026-07-23). Every scaffold download carries this pack at
  `Expansions/mypka-cockpit/` (scaffold v5.1.0 and later); there is no
  standalone zip on the Expansion Packs page, no bucket object, and no catalog
  row. The 1.3.0 note below ("first standalone Expansion Pack release")
  described an intent that was never executed: no release pipeline, bucket
  object, or catalog row ever existed, so 1.3.0 was never distributed anywhere
  and no member migration concern exists.
- **Source of truth consolidated into the scaffold repo** (Tom ruling
  2026-07-23, train 3). Cockpit source now lives directly in `myICOR/myPKA` at
  `Expansions/mypka-cockpit/` — this folder IS the live source, not a synced
  copy. The historical `myICOR/mypka-cockpit` repo is archived as read-only
  history, and the cross-repo sync machinery (its `release-pack.yml` sync job
  and the AUTO-28 snapshot-notify pathway) is retired. Cockpit changes ride
  the scaffold release train: every scaffold release builds this folder from
  source and verifies it (slug/version lockstep, fresh `web/dist` build gate,
  deterministic source-shape pack, `.trusted-sources` pin match) before the
  scaffold artifact is cut. Version bumps here bump `expansion.yaml`,
  `package.json`, and `web/package.json` in lockstep plus the
  `Expansions/.trusted-sources` pin, all in the same scaffold PR.

## [1.4.0] - 2026-07-23

### Changed

- **INKLINE re-skin: the Cockpit moves from the retired GL-003 v4 "Graphite" design
  to the GL-003 v5.32 INKLINE brand ("a calm teacher's blackboard at dusk").** UI
  layer only; no behavior, data, API, or schema changes. By layer:
  - **Tokens** (`web/src/index.css`): the dark default becomes the ink room
    (`#0C0E12` ink / `#12151B` card / `#181C24` muted / `#1C212B` overlay, plus
    `ink_deep` for the rail), the warm paper voice ladder (`#F6F3EC` /
    `#C9C4B8` / `#8E897D` at full alpha per the GL-003 §2.8 quiet-voice floor),
    and paper-alpha hairlines. The light theme becomes the paper room (GL-003
    §2.2 cream grounds, warm ink foregrounds, A150 room chrome). **Brass is
    retired; the marker (`#FF5A2D`, light `#D43F16` fills with the `#B93613`
    small-text step per ruling A148) is THE accent** - every `--accent-brass`
    family token is renamed to `--accent-marker*` and all consumers swept.
    Status doctrine per GL-003 §2.5: destructive keeps red with the A146/A147
    small-text steps, warning amber is icon-voice, success and info ride the
    quiet ink voice with a `success-dot` green carve-out. Graphite category
    hues (oxblood, teal, concept wheel, sticky palette) are remapped onto the
    §2.6 calmed lenses and folder palette.
  - **Typography** (self-hosted via `@fontsource-variable`, bundled by Vite,
    zero CDN requests): Inter is replaced by Instrument Sans (body), JetBrains
    Mono by Spline Sans Mono (mono kicker voice), Bricolage Grotesque added as
    the display voice (headlines, page titles at 640 / -0.015em), Caveat added
    as the hand voice (empty-state notes per §6.5). The Google Fonts links are
    removed from `index.html`; the app runs fully offline. The §3.2 17px root
    is adopted. The quotation serif collapses onto the display face per the
    §3.1 no-serif law.
  - **Chrome** (`web/src/cockpit.css` + view sheets): the sidebar becomes the
    ink_deep rail with the §5.5 marker-light wash; active nav rows take the
    §6.1 pressed well + marker glyph; the blueprint dot grid, crosshair
    corners, gradient hairlines, top-lit card gradients, and static edge fades
    are retired (§5.3 flatness, §10.3 banlist); glass surfaces speak the
    room's own ground (§2.2 scrim doctrine); focus rings become the 2px marker
    outline (§6.2 "focus is the pen"); selection and scrollbars take the §2.1 /
    A150 recipes; the §5.5 room wash replaces the Graphite atmosphere; floating
    shadows split per room (dark black-based, paper warm-ink per §5.3);
    passive hover borders step to the emphasis hairline instead of the accent;
    corner radii snap to the §5.2 ladder (10 / 16 / 20 / pill, data-viz cells
    at the A137 2px micro rung); marker text steps ride `--accent-marker-text`
    so small strings clear the §2.8 4.5:1 floor in both rooms; several
    opacity-dial text dims are replaced by full-alpha ladder steps (§2.8).
  - **Charts and map**: Recharts colors route through tokens (`var()` in SVG);
    the workout map inverts to the §4.2 line doctrine (routes rest in paper,
    the selected route turns marker; the info-blue selection is retired per
    the §2.4 de-blue doctrine).
- **Aligned to GL-003 v5.33 (rulings A159-A164).** Three post-canonization
  deltas on top of the re-skin: the key-element concept color moves off the
  gold hex onto dusty indigo (`#8087A6` dark / `#565E7E` light, A159 - an
  assigned category palette never hands out the gold); warning amber leaves
  text strings entirely and stays on icons, edge rails, state dots, soft
  tints, and pulse rings (A162 - amber never carries the string); the voice
  orb's listening and connecting states move from marker-tinted to the quiet
  paper voice (A163 - the room listens in paper, the pen speaks in marker),
  with the orb's listening glow now var-driven per room (`--orb-listen-glow`)
  instead of hardcoded.
- **The Mind section's legacy mood-word fallback defaults to English.** The
  free-text mood-word matcher (used only for journal entries that predate the
  language-neutral `mood_valence` field) now matches common English mood words;
  unmatched words stay neutral. Users journaling in another language can extend
  the word lists locally - `mood_valence` remains the primary, language-neutral
  signal.

### Added

- **Four self-hosted font dependencies** (`@fontsource-variable/bricolage-grotesque`,
  `instrument-sans`, `spline-sans-mono`, `caveat`). Bundled as woff2 by Vite;
  no CDN request is ever made.

## [1.3.0] - 2026-07-07

### Added

- **First standalone Expansion Pack release.** From this version the Cockpit ships
  as its own pack (`mypka-cockpit-v<version>.zip`) on the myICOR Expansion Packs
  page, installed into an existing myPKA scaffold per INSTALL.md. Version 1.2.1
  was the last bundled-only version: it shipped only inside the all-in-one myPKA
  scaffold (scaffold releases v3.0.0 through v4.1.1) and was never distributed on
  its own. The scaffold returns to basic-only and no longer carries the Cockpit;
  this repo and its releases are now the single source of truth for Cockpit code.
- **Getting-the-pack note in INSTALL.md.** The install contract now opens with
  where the zip comes from, the sha256 verification step against the value shown
  on the Expansion Packs page, and the unzip-to-`Expansions/mypka-cockpit/`
  placement.

### Changed

- **Repo brought up to the QA'd bundled state of scaffold v4.1.1.** The
  consolidated bundle fixes (pending since 2026-06-21) land in this repo: the
  launcher templates now guarantee a core `mypka.db` before the server starts
  (creating it via `install-extensions.py --all` when missing, with an actionable
  message when Python 3 or PyYAML is absent instead of a server crash),
  `install-extensions.py` installs every module pack by default (`--all` is the
  explicit alias of the no-flag default), INSTALL.md documents the auto-bootstrap
  flow, DISCLAIMER.md and INSTALL.md add the auth-mode note for automated chat
  bridge use (an Anthropic API key under Commercial Terms, never a consumer
  Pro/Max OAuth login), `scripts/UPDATE-COCKPIT.md` documents the Cockpit-code
  update lifecycle as a spec, and `docs/db-contract.md` plus
  `sqlite-extension/DATA-CONTRACT.md` document the governance-doc tables.
- **The schema-tolerant governance list endpoint is retained.** This repo's
  `server/teamKnowledgeApi.js` and `web/src/views/TeamKnowledgeListView.tsx`
  (schema tolerance, 2026-06-22) stay as they are; the bundled v4.1.1 copies
  predated that fix and were not allowed to overwrite it. The endpoint keeps
  working against both the pack's own regen shape and a user's richer private
  mirror shape.
- **Version mirrors reconciled.** `expansion.yaml` stays the single source of
  truth; the root `package.json` and `package-lock.json` and the web
  `package.json` and `package-lock.json` now all mirror it (the root lockfile had
  been stuck at 1.0.0 and the web pair at 1.2.0).

### Fixed

- **Corrupted `react-leaflet@4.2.1` integrity hash in `web/package-lock.json`.**
  The repo lockfile carried an integrity value that does not match the npm
  registry, which breaks `npm ci` verification on a fresh install. Restored to
  the canonical registry value.

## [1.2.1] - 2026-06-23

### Fixed

- **Drop a task before or after a calendar event in the day planner.** Events and
  tasks now share one ordering space inside each day-half lane, so you can drop a
  task ABOVE an event, not just below it. Previously the before/after model had no
  way to name an event as a neighbour, so a task dropped above an event snapped
  back below it on the next paint.
- **Dragging a task up or down within the same column now sticks.** Reordering an
  already-placed task inside its own column lands it at the new spot and persists
  across reloads. Previously a same-column drag was silently a no-op because the
  insert index ignored the drag direction.
- **New migration `008-unified-position-space.sql`.** Introduces the unified
  events+tasks position space behind the two fixes above. It applies automatically
  on the next cockpit boot: the planner's built-in migration runner discovers
  `migrations/NNN-*.sql` and applies any new ones in ascending order, idempotently,
  inside a single transaction each. No manual step; nothing to run.

## [1.2.0] - 2026-06-23

### Added

- **Theme bootstrap externalized to a CSP-safe `web/public/theme-bootstrap.js`.**
  The first-paint theme-resolution script moves out of an inline `<script>` in
  `web/index.html` to a same-origin `/theme-bootstrap.js` asset, so it runs under
  the server's strict `script-src 'self'` CSP without a per-build nonce or hash to
  drift. Behavior is unchanged (no flash of the wrong theme at first paint).

### Changed

- **Graphite reskin: the Cockpit's dark theme is retuned from warm charcoal to cool
  graphite.** The default dark theme moves to a cool, near-black graphite canvas
  (hue 250, near-zero chroma so it reads neutral, never pure black) with a cool
  near-white text ramp, while **brass (`#C99A4F`) is retained as the single
  signature accent**, recontextualised on the cool field. This is a pure visual
  refresh delivered as two decoupled CSS files (`web/src/index.css` design-token
  retune plus `web/src/cockpit.css` chrome). No behavior, data, API, or schema
  changes; no new dependencies. Source of truth: Iris's GL-003 v4 "Graphite"
  design language.

## [1.1.0] - 2026-06-22

### Added

- **"My AI Team" fly-out menu.** The Cockpit sidebar gains a dedicated Team fly-out
  with five destinations: **Team** (the roster), **Session Log**, **Workstreams**,
  **SOPs**, and **Guidelines**. The team is now first-class navigation, not buried.
- **Workstreams / SOPs / Guidelines are indexed and browsable.** The
  `regen-mypka-db.py` mirror gains new tables for the governance docs
  (`workstreams`, `sops`, `guidelines`), and the Cockpit renders each family as a
  browsable list view backed by a new read-only endpoint:
  **`GET /api/cockpit/team-knowledge/:family`** (`:family` ∈
  `workstreams` | `sops` | `guidelines`), served by the new
  `server/teamKnowledgeApi.js`.

### Changed

- **Session Log and Roster are now separate, full-height pages.** Previously both
  shared one cramped view; they are now two distinct routes, each using the full
  viewport height. Team pages no longer crop their content.

### Migration (existing installs)

- Pull the new Cockpit source (the `web/src` team views, `server/teamKnowledgeApi.js`,
  `scripts/regen-mypka-db.py`), then **re-run the mirror regen** to populate the new
  governance tables:
  `python3 "Expansions/mypka-cockpit/scripts/regen-mypka-db.py"`.
  Then **rebuild and restart** the Cockpit (`npm run serve`) so the new server route
  and the rebuilt `web/dist` are live. No scaffold-wide change is required.

## [1.0.1] - 2026-06-22

> *Renumbered 2026-06-22: this entry was originally mislabeled `[3.0.1]` (the
> scaffold version), but the Cockpit CHANGELOG tracks `expansion.yaml` — which was
> `1.0.1` for this fix. Corrected to keep the Cockpit's own version series
> (`1.0.0` → `1.0.1` → `1.1.0`) consistent with its SSOT.*

### Fixed

- **Fleeting-note + journal capture no longer fails for non-Latin titles.**
  `slugifyTitle()` is ASCII-only, so a non-empty title made entirely of non-Latin
  script (Korean / Chinese / Japanese / Cyrillic / Greek / Arabic / Hebrew / Thai),
  emoji, or punctuation slugified to an empty string — and `createWorkbenchDoc()`
  (Fleeting Notes) and `createJournalEntry()` (Journal composer) then rejected the
  capture with `bad-title` (HTTP 400). Capture was blocked purely on the title's
  character set. Both create paths now fall back to a safe generated slug that
  passes the slug whitelist and the containment jail — `fleeting-<YYYY-MM-DD-HHMMSS>`
  for a fleeting note, `<date>-entry` for a journal entry — instead of refusing.
- **The human title is preserved when the slug falls back.** A fleeting note
  prepends the original title as an H1 (so it survives in the note body and is
  recovered as the note's title); a journal entry already records it in the
  `title:` frontmatter field. So a note titled `한글 메모` keeps `한글 메모` even
  though its filename slug is the generated form.
- **All security guards are unchanged.** A path-like title (`/`, `\`, NUL, `..`)
  is still refused with `bad-title` — a path is never a real title and never falls
  back. Reserved names, collision (no silent overwrite), the slug whitelist, and
  realpath containment are all intact; the generated fallback slug itself passes
  every check. ASCII behavior is identical (`c` → `c`, `Test Note` → `test-note`,
  `café` → `cafe`). Covered by `server/workbench.slug.test.mjs`.

## [1.0.0] - 2026-06-17

First public **standalone** release of the myPKA Cockpit as a community-
distributable Expansion. Public version history starts here. The cockpit
previously lived inside the author's private myPKA instance and reached an
internal `1.7.0` (finance example tracking, Hub modules, runtime Settings page,
the move to a source-available license); that lineage is pre-history and is not
re-numbered into this public series.

### Added

- **Standalone, drop-in distribution.** The cockpit now ships as its own
  Expansion folder you drop into `Expansions/mypka-cockpit/`, with the manifest
  (`expansion.yaml`) as the version SSOT and `INSTALL.md` as the install
  contract your LLM assistant follows.
- **`INSTALL.md` — the keystone install contract.** A deterministic 8-step
  procedure (Step 0 consent → Step 1 backup → Step 2 resolve root → Step 3
  detect gaps → Step 4 offer the SQLite upgrade → Step 5 generate the launcher →
  Step 6 wire & first run → Step 7 adapt to any KB), with four hard rules baked
  in: consent-before-write, backup-before-write, offer-not-auto upgrade, and
  never auto-launch.
- **`DISCLAIMER.md`** — bilingual (EN+DE) backup / breaking-changes / AS-IS
  install disclaimer, surfaced by `INSTALL.md` Step 0 before any write.
- **`HOW-IT-WORKS.md`** and **`CUSTOMIZE.md`** — the architecture reference and
  the "adapt the cockpit to any knowledge base" guide.
- **`sqlite-extension/`** — the additive, idempotent SQLite upgrade area:
  `DATA-CONTRACT.md` (the exact tables/views the cockpit reads), `detect-gaps.py`
  (read-only probe of what will render vs. be empty), and `install-extensions.py`
  (additive installer; never drops a table/column or modifies a row).
- **`launcher/GENERATE-LAUNCHER.md` + text-only templates** — per-OS launcher
  generation. The package ships **zero executables**; your assistant writes the
  launcher locally from a reviewed template (anti-malware-warning posture).
- **Dynamic root resolution** (`server/repoRoot.js`): `MYPKA_ROOT` env →
  upward fingerprint search (`AGENTS.md` + `PKM/`) → three-levels-up fallback,
  so the cockpit no longer assumes a fixed `Expansions/mypka-cockpit/` depth.
- **`LICENSE` + `NOTICE` + `SECURITY.md`** at the package root.

### Changed

- **Version reset to `1.0.0`** for the first public standalone release (internal
  lineage reached `1.7.0`; not carried into the public numbering).
- **Connectors ship as disabled example source.** The example task/PM/calendar
  connectors (Todoist / ClickUp / iCal / IMAP) load only when
  `CONNECTORS_ENABLED=1` AND a key resolves — off by default.
- **Removed the shipped `start-cockpit.command`.** No launcher ships; it is
  generated per-OS at install (see `launcher/`).
- **Manifest reconciled to the standalone Expansion schema v1:** dropped the
  deprecated `requires_scaffold_version` gate, set `runtime.start` to `null`
  (the machine-readable signal that no launcher ships), and updated
  `post_install_steps` / `post_install_validation` to the standalone tree.

### Security

- Loopback-default binding (`127.0.0.1:4317`); LAN mode hard-gated on a
  configured PIN. Reads `mypka.db` strictly read-only (`readonly` open flag +
  `query_only` pragma). The only vault write surface is Fleeting Notes
  (`PKM/Fleeting Notes/`), behind a flag.
- **BYO-key:** the chat bridge spawns the user's own local `claude` CLI — no key
  ships in the package, nothing is pooled, proxied, or centrally stored.
- Connector and tool secrets are stored by reference only in a gitignored local
  `Team Knowledge/.env` (mode `0600`), resolved in-process by name.

[1.0.0]: https://myicor.com/library/mypka-cockpit
