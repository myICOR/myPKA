# INSTALL.md — the myPKA Cockpit install contract

You are an LLM assistant (Claude Code, Codex CLI, Cursor, or similar). The user
has dropped this folder into their knowledge base and said *"install the myPKA
Cockpit."* **This file is the contract you follow, in order, top to bottom.** Do
not skip a step, do not reorder, do not write before the consent gate clears.

> **Run this install with your most capable model.** Installing and adapting the
> cockpit is judgment-heavy wiring — mapping the user's existing data onto the
> cockpit's tables, building correct `[[wikilinks]]` and connections, running the
> SQLite upgrade and mirror regen, extracting social-URL embeds, and adapting to
> whatever folder structure the user actually has. Use your provider's **top
> tier** for this step (e.g. Claude Opus-class, GPT-5 / o-series-class, or Gemini
> 2.5 Pro/Ultra-class — whichever is your provider's frontier model). A cheaper or
> smaller model can *run* the steps but cannot reliably get them **wired
> correctly**; the frontier model is what makes the connections land right. Switch
> down to a lighter model afterward for routine day-to-day use if you like.

> **Where this package comes from.** The Cockpit ships as a member pack
> (`mypka-cockpit-v<version>.zip`) on the myICOR Expansion Packs page (see
> `expansion.yaml` `homepage:`). Before unzipping, verify the download against
> the sha256 shown on that page: `shasum -a 256 <zip>` on macOS/Linux,
> `Get-FileHash <zip>` on Windows. Unzipping yields a single `mypka-cockpit/`
> folder; place it at `Expansions/mypka-cockpit/` inside the user's myPKA
> (Step 2 covers placement and the folder-name rule in detail).

Companion docs you will reference (relative paths):

- [`DISCLAIMER.md`](./DISCLAIMER.md) — the backup / breaking-changes / AS-IS
  notice you surface in **Step 0**.
- [`HOW-IT-WORKS.md`](./HOW-IT-WORKS.md) — the architecture (read-only mirror
  model, two-DB split, ports, CSP, chat bridge). Read it before you modify
  anything.
- [`CUSTOMIZE.md`](./CUSTOMIZE.md) — how to adapt the cockpit to ANY knowledge
  base; the target of **Step 7**.
- [`sqlite-extension/DATA-CONTRACT.md`](./sqlite-extension/DATA-CONTRACT.md) —
  the exact tables/views the cockpit reads; **Steps 3 & 4**.
- [`launcher/GENERATE-LAUNCHER.md`](./launcher/GENERATE-LAUNCHER.md) — how you
  generate the per-OS launcher; **Step 5**. **No launcher ships in this package.**

---

## The four hard rules (they bind YOU, the installing assistant)

1. **Consent before write.** You surface `DISCLAIMER.md` and get explicit user
   confirmation **before your first read or write** to their folder (Step 0).
2. **Backup before write.** You confirm a restorable backup exists — or the user
   explicitly waives it — before any write (Step 1).
3. **Offer, never auto-apply, the SQLite upgrade.** The data upgrade in Step 4 is
   an OFFER. You explain the consequence and wait for a yes.
4. **Never auto-launch.** You GENERATE a launcher and hand it to the user. The
   user starts the cockpit (Step 5). You never run the server for them.

---

## Step 0 — Surface the disclaimer and STOP for consent (before any read or write)

Before you touch a single file, print the full contents of
[`DISCLAIMER.md`](./DISCLAIMER.md) to the user — EN first, DE second, as written
— and **stop**. Installing the cockpit lets you (their assistant) **change files
in their knowledge base** to fit the interface: it may rewrite frontmatter, add
a SQLite index, and create folders. That is the user's responsibility, AS-IS,
with no warranty and no liability (see [`LICENSE`](./LICENSE) Sections 8–10).

> **Machine-readable gate (load-bearing — do not skip):** *Before modifying ANY
> existing file, confirm with the user that they have a backup you can restore
> from. Do not proceed to any write until they confirm or explicitly waive it.*

Require an explicit "yes, proceed" before continuing. If the user does not
consent, stop here — installation does not begin.

> **About the trust anchor (if your install flow offers one).** At install you
> may be asked whether to create a *trust anchor*. That is simply a local
> SHA-256 hash of this manifest, recorded on your own machine at install time. On
> any future install or update it re-hashes the manifest and compares: matching
> bytes verify **GREEN** ("unchanged since you trusted it"), changed or missing
> bytes show **YELLOW** ("unverified — review before trusting"). It is *your own*
> "hasn't-changed-since-I-trusted-it" check, kept locally — not a statement about
> origin. The separate guarantee that this package **genuinely came from myICOR**
> is the **signed GitHub Release + artifact attestation**, not the trust anchor.
> Creating the anchor is optional and entirely your call.

## Step 1 — Recommend a BACKUP first

With consent given, make sure a restorable backup exists before any write:

- If the knowledge base is a **git repo**: `git status` clean? then `git commit`
  / `git stash`, or note the current commit they can reset to.
- Otherwise: copy the entire folder somewhere safe, or make a timestamped zip:
  `zip -r ../mypka-backup-$(date +%Y%m%d-%H%M).zip .` from the scaffold root.

**Offer to perform the backup for the user.** Do not proceed to any write until
the user confirms a backup exists, or explicitly waives it. This rule and Step 0
are a security/safety gate, not just legalese — they protect the user's data.

## Step 2 — Detect placement & resolve the scaffold root

The happy path: this folder sits at `Expansions/mypka-cockpit/` inside the
user's myPKA, so root resolution finds the scaffold automatically.

> **Folder name must be `mypka-cockpit` (lowercase, hyphen — matching the
> manifest `slug`).** The display name "myPKA Cockpit" lives in `expansion.yaml`
> `name:`; the **on-disk folder** is `mypka-cockpit`. If the user downloaded
> this folder named **"myPKA Cockpit"** (with a space and capitals), **rename it
> to `mypka-cockpit`** when placing it — so the path is exactly
> `Expansions/mypka-cockpit/`. This is what the fallback root resolution (item 3
> below, "three levels up from `Expansions/mypka-cockpit/`") and every doc
> reference expect. A space/caps mismatch is the one friction point to remove
> here; rename, do not work around it.

Root resolution is handled at process start by `server/repoRoot.js`, first match
wins (this is the order the launcher and the server BOTH use):

1. **`MYPKA_ROOT` env var** — if set to a real directory, used verbatim. This is
   the override for a relocated cockpit or a scaffold on another volume.
2. **Upward fingerprint search** — walk up from the cockpit folder for a
   directory containing both `AGENTS.md` and `PKM/` (a generated `mypka.db` is
   accepted as a secondary marker).
3. **Fallback** — `Expansions/mypka-cockpit/` → three levels up.

Confirm the resolved root with the user. If the cockpit is NOT under
`Expansions/mypka-cockpit/`, copy [`.env.example`](./.env.example)'s keys into
the scaffold's `Team Knowledge/.env` and set `MYPKA_ROOT` to the absolute
scaffold path so the server and the regen agree. (Secrets live ONLY in
`Team Knowledge/.env`, mode `0600`, gitignored — never in this folder.)

## Step 3 — Detect data / visual gaps (read-only, safe)

The cockpit renders representations (Finance Hub invoices, the graph, planner,
health/workout dashboards) that a **basic** scaffold's `mypka.db` may not
contain. Probe what is present, write nothing:

```sh
python3 sqlite-extension/detect-gaps.py "<resolved-root>/mypka.db"
```

Report the result to the user in plain language — e.g. *"The Finance Hub will be
empty because your mirror has no `v_open_invoices` view"* — and point at
[`sqlite-extension/DATA-CONTRACT.md`](./sqlite-extension/DATA-CONTRACT.md) for
which modules are core (boot-required) vs. optional (degrade to a calm empty
state). A missing optional table is never a crash — see HOW-IT-WORKS §7.

If the scaffold has **no `mypka.db` at all**, that is fine — the upgrade in
Step 4 handles it. The cockpit's own base regen at
[`scripts/regen-mypka-db.py`](./scripts/regen-mypka-db.py) creates the core
tables, and `install-extensions.py` **auto-runs that regen first** when it finds
no (or a coreless) `mypka.db`, so the core schema always exists before the
cockpit's extension tables are added. (There is no root-level
`Team Knowledge/scripts/regen-mypka-db.py` in this package — the base-DB creator
ships here, inside the cockpit, at `scripts/regen-mypka-db.py`.)

## Step 4 — OFFER the SQLite upgrade (offer, never automatic)

If Step 3 found gaps the user wants filled, OFFER to run the additive,
idempotent installer. Explain first: it **adds** the cockpit's tables/views to
`mypka.db`; it never drops a table/column or modifies a row; back up `mypka.db`
first (Step 1 already covers this).

```sh
python3 sqlite-extension/install-extensions.py "<resolved-root>/mypka.db" --all      # installs every cockpit module (also the no-flag default)
python3 sqlite-extension/install-extensions.py "<resolved-root>/mypka.db" --with-health --with-food  # opt INTO a deliberate subset instead
python3 sqlite-extension/install-extensions.py "<resolved-root>/mypka.db" --dry-run  # show the plan, write nothing
```

With **no module flag** the installer installs every cockpit module — `--all` is
the explicit alias of that default, so the cockpit ships fully wired out of the
box. Pass one or more `--with-…` flags only when you deliberately want a subset.

**The base DB is handled automatically.** The installer ADDS its tables on top
of a core `mypka.db`. If none exists yet (the common fresh-scaffold case, or a
`mypka.db` that lacks the core `journal` table), the installer **auto-runs the
base regen ([`scripts/regen-mypka-db.py`](./scripts/regen-mypka-db.py)) first**
to create the core schema, then applies the extensions — in one command, with no
manual pre-step. The sequence is always: **create base DB → add extensions.**
The regen needs PyYAML (`pip3 install --user pyyaml`); if it is missing, the
installer stops with the exact command to run, never a bare "no such database".
(If you ever point the installer at a `mypka.db` that is NOT at the scaffold
root, it can't auto-create the right file there — it then prints the exact regen
command to run first. The happy path under `Expansions/mypka-cockpit/` is fully
automatic.)

Then re-run `detect-gaps.py` to confirm. **Wait for the user's yes before
running it.** Silas owns this installer and its schema
([`sqlite-extension/`](./sqlite-extension/)); this step only triggers it and
explains the consequence.

> **Known limitation (v1.0):** the cockpit's base regen
> ([`scripts/regen-mypka-db.py`](./scripts/regen-mypka-db.py)) does not produce
> the optional health tables (`health_mood`, and `habits` without
> `started_on`/`status`). Those modules are fed by an external ingest, not
> markdown, and **degrade gracefully to honest empty states** when absent
> (HOW-IT-WORKS §7). This is expected on a fresh scaffold — not an error.

## Step 5 — Generate the launcher per-OS (NO shipped executable)

**This package ships zero executables** — no `.command`, `.sh`, `.bat`, or
`.ps1`. You GENERATE the right launcher locally, on the user's machine, from the
text-only reference templates. This is a deliberate anti-malware-warning posture
(a downloaded launcher trips Gatekeeper / SmartScreen; one your assistant writes
from a reviewed template does not).

Follow [`launcher/GENERATE-LAUNCHER.md`](./launcher/GENERATE-LAUNCHER.md):

1. Detect the OS (`node -e "console.log(process.platform)"`).
2. Adapt the matching template in `launcher/templates/` (`macos.command.txt`,
   `linux.sh.txt`, `windows.ps1.txt`, `windows.bat.txt`) to the real cockpit
   path and port.
3. Write the launcher into the cockpit root, `chmod +x` where it applies.
4. **Tell the user how to start it — do not start it yourself.**

The generated launcher performs, in order: resolve dir → **ensure `mypka.db`
exists with the core schema** (fast-path regen-refresh when it already exists;
otherwise create it via `install-extensions.py "<root>/mypka.db" --all`, which
auto-bootstraps the base DB + all modules — and stops with an actionable message
if Python 3 / PyYAML is missing on that first run, rather than letting the server
crash) → first-run install+build → free the port → open the browser → start the
server loopback-only.

## Step 6 — Wire & first run

Do the build steps now (the launcher also does these on first run, but doing
them here surfaces problems while you can still fix them):

```sh
npm run install:all          # server deps + web deps
npm run build                # build the React app → web/dist/
```

Confirm `mypka.db` exists and is current at `<resolved-root>/mypka.db`. Then have
the **user** run the launcher they got in Step 5. It binds `127.0.0.1:4317`
(loopback only) and opens `http://127.0.0.1:4317/`. Confirm the loopback-only
posture with the user; LAN exposure is a separate, PIN-gated opt-in
(`COCKPIT_BIND_LAN=1` + `npm run set-pin`) — never a launch default.

Sanity-check once it is up:

```sh
curl -s http://127.0.0.1:4317/api/health      # → { ok: true, ... }
```

## Step 7 — Adapt to ANY knowledge base

The cockpit is a **templated starting point**, not a fixed product. Point the
user (and yourself) at [`CUSTOMIZE.md`](./CUSTOMIZE.md): how to re-point the
cockpit at a different folder (`MYPKA_ROOT`), map a different markdown /
frontmatter convention onto the DATA-CONTRACT, add or remove UI modules, and add
a connector. Adapting to a wildly different knowledge base is LLM-assisted work
the user owns — you provide the pattern and the contract, not a guarantee.

---

## Saving Outer World content from a URL (read this before you save a link)

This is a **usage** instruction, not an install step — but it belongs here because
the cockpit ships a tool you must use, and getting this wrong is the single most
common capture mistake. When the user shares **any social post or article URL** to
save into their Outer World (the saved-from-outside library — X/Twitter posts,
articles, YouTube/Vimeo videos, TikTok/LinkedIn/Instagram posts), follow these
three steps. Do not improvise a different path.

1. **Extract the content with the shipped fetcher — never plain-`fetch` the page,
   never open a browser.** Run:

   ```sh
   node scripts/fetch-embed.mjs "<url>" --note <short-slug>
   ```

   The fetcher pulls the content the right way: **oEmbed / Open-Graph with no
   login and no browser** (X/Twitter via `publish.x.com` / `publish.twitter.com`
   oEmbed; YouTube/Vimeo/Loom via their public oEmbed; everything else via an
   Open-Graph scrape). **Do NOT plain-`fetch` a social URL** — the tweet/post page
   itself is auth-walled and answers `402`, which is *expected* and is exactly why
   the fetcher exists. **And do NOT fall back to opening Chrome or any browser** —
   that path is both wrong and unnecessary; the fetcher already has the no-auth,
   no-browser route covered. If a platform genuinely needs a token the fetcher
   doesn't have, it **degrades to a minimal card** (kind `link` + domain +
   `source_url`) and prints it — take that honest minimal card; do not reach for a
   browser to "do better."

2. **Store the EXTRACTED TEXT plus the flat `embed_*` fields only — never the raw
   embed HTML or any `<script>`.** The fetcher emits an `embed_*` frontmatter block
   (the tweet/post text already stripped to inert TEXT, plus `embed_title`,
   `embed_image`, `embed_author`, etc.). Splice that block into the new Outer World
   note's frontmatter; the note **body** is the extracted text plus the user's own
   annotation (their `tom_context`). The cockpit renders the rich card *offline*
   from the flat `embed_*` fields. **Never paste a raw embed blockquote, widget,
   or `<script>` tag into the note** — the cockpit's CSP blocks inline scripts, so
   a raw embed does not render and the card errors. Text-plus-`embed_*` is the only
   shape that works.

3. **Regenerate the mirror so the Outer World grid picks it up.** From the
   resolved scaffold root, run the cockpit's regen (it finds the scaffold root
   from its own location, so it works run from anywhere):

   ```sh
   python3 "Expansions/mypka-cockpit/scripts/regen-mypka-db.py"
   ```

   The new item now appears in the cockpit's Outer World view with its card.

The full fetcher reference (flags, per-platform behavior, the security posture)
is in [`docs/outer-world-embed-fetcher.md`](./docs/outer-world-embed-fetcher.md).
The capture flow this slots into — the Inner-vs-Outer routing fork, the Capturing
Beast filter, and the bucket-linking that turns a saved link into a
graph-connected library entry — is designed in the scaffold's Outer World capture
SOP (the `SOP-NNN-capture-outer-world-content` Penn authors as a branch of
WS-001). This file owns only the "extract-store-regen" mechanics; the routing and
filtering live there.

---

## Connectors and LAN mode are OFF by default

- **External connectors** (Todoist / ClickUp / iCal / IMAP) ship as **disabled
  example source**. They activate only when `CONNECTORS_ENABLED=1` AND the user
  has stored a key via the Connections page. Do NOT enable them during install —
  it is a deliberate, separate decision. See
  [`server/connectors/README.md`](./server/connectors/README.md) (read its
  finance/bank disclaimer first).
- **The chat bridge is BYO-key.** When the cockpit hands a note or a
  connector-wiring brief to Claude, it spawns the user's OWN local `claude` CLI
  (their login, their key). No key ships in this package; nothing is pooled,
  proxied, or sent to a server the cockpit controls. See HOW-IT-WORKS §8.

  > **Auth mode matters.** Interactive use through your own `claude` CLI is fine
  > on your normal login. But if you run the bridge in any automated, scheduled,
  > or unattended way, that path must authenticate with an **Anthropic API key**
  > (Commercial Terms), not your Pro/Max subscription OAuth login — Anthropic's
  > Consumer Terms require a human to drive each interaction and do not cover
  > programmatic clients.
- **Using Codex / Gemini / another CLI instead of Claude?** The cockpit is
  Claude-first but LLM-agnostic by config: set `COCKPIT_LLM_CMD` (in
  `Team Knowledge/.env`; default `claude`) to your CLI command. Full steps and
  the one prompt-passing caveat are in [`CUSTOMIZE.md`](./CUSTOMIZE.md) §5.

## Uninstall

Delete this folder. The user's markdown is untouched. `mypka.db` (regenerable)
and `mypka-cockpit.db` (the cockpit's local planner/settings state) and
`PKM/Fleeting Notes/` (the user's own notes) remain — the user removes them only
if they want to. See [`expansion.yaml`](./expansion.yaml) `uninstall.residual_paths`.
