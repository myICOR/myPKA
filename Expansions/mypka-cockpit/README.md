# myPKA Cockpit

A local web app that turns your myPKA folder into a **navigable, wikilink-aware
cockpit**. It opens on the **Hub** — your My Life dashboard (Projects, Key
Elements, Topics, Goals, Habits as living cards) — and gives you your journal,
every note with clickable `[[wikilinks]]` and backlinks, your team roster, and
**Fleeting Notes**: a capture space for thoughts and work-in-progress documents
with an outliner editor (type `#`, `**bold**`, `*italic*` — it formats as you
type, Obsidian-style) and **whiteboards** where your notes live as sticky cards
on an infinite canvas.

Everything runs **on your machine**. No account, no API key, no cloud. The
server binds to `127.0.0.1` and your notes never leave your computer.

## Quickstart

You don't install this by hand — **your LLM assistant does it for you**:

1. **It's already in your myPKA.** The Cockpit ships bundled with the myPKA
   scaffold (v5.1.0 and later) at `Expansions/mypka-cockpit/` - no separate
   download. If you obtained this folder another way, place it at exactly that
   path (the folder name must match the slug `mypka-cockpit`, lowercase with a
   hyphen).
2. **Point your assistant at [`INSTALL.md`](./INSTALL.md)** (Claude Code, Codex
   CLI, Cursor, …).
3. **Say:** *"Install the myPKA Cockpit."*

> **⚠ Back up your folder first.** Installing lets your assistant **change files
> in your knowledge base** to fit the interface. Before you start, make a
> complete, restorable backup. `INSTALL.md` Step 0 surfaces the full
> [`DISCLAIMER.md`](./DISCLAIMER.md) and stops for your consent — and Step 1
> makes you back up — before any write happens.

Your assistant follows `INSTALL.md`: it gets your consent, has you back up,
resolves your scaffold root, detects which modules will have data, OFFERS the
SQLite upgrade (never auto-applies it), generates an OS-appropriate launcher,
and tells you when to start the cockpit. It **never auto-launches** — you start
it.

What it will ask you about: if your myPKA doesn't have a `mypka.db` yet, it will
propose the scaffold's **SQLite upgrade**. That's a derived index over your
markdown — your notes stay untouched and stay the source of truth; the database
can be regenerated or deleted at any time.

**Prerequisites:** Node.js v20+ · Python 3 with PyYAML.

## How to launch

The cockpit ships **no launcher** — your assistant generates one for your OS
during install (a macOS `.command`, a Linux `.sh`, or a Windows `.bat`/`.ps1`),
from a reviewed text template, into this folder. You then run it: it refreshes
the database from your markdown, builds the app if needed, starts the local
server, and opens `http://127.0.0.1:4317/`. Stop it with Ctrl-C or by closing
the Terminal window.

> **Why no pre-made launcher?** A downloaded `.command`/`.exe`/`.bat` trips
> Gatekeeper (macOS) and SmartScreen (Windows). A launcher your own assistant
> writes from a template you can read carries none of that friction.

## What's inside

| Section | What it shows |
|---|---|
| **Hub** | The landing dashboard: today's planned actions + calendar events, **open invoices** (overdue first, then due-soon), your My Life buckets with note + whiteboard counts, **recently scanned documents**, pinned fleeting notes, the ready-for-team row, latest documents + journal |
| **Journal** | Your dated entries, newest first, with mood/energy chips and image strips |
| **Fleeting Notes** | Capture + WIP space in `PKM/Fleeting Notes/`: sticky-style notes with a pin, a color, and a status (**capture → working → ready** — "ready" is your signal to the team to integrate the note into your PKM), an outliner editor with live markdown, and **whiteboards** for spatial thinking |
| **Actions & Planning** | A weekly day planner over your own tools — read-only, with deep links to edit at the source; your plan layout stays local |
| **Connections** | Connect any task / PM / calendar tool: paste an API key once, it's stored only on your machine. Tools the cockpit doesn't know yet? Ask your AI assistant to wire them |
| **Knowledge** | Every entity type — People, Topics, Projects, Key Elements, Habits, Goals, Organizations, Documents, Deliverables — with live counts |
| **Team** | Your specialist roster from `Team/`, with avatars and bios |
| **Settings** | Show or hide Hub sections (open invoices, recently scanned, buckets, pinned notes, whiteboards, latest documents, latest journal) — applied instantly, saved on your machine only |

The cockpit reads `mypka.db` strictly **read-only**. Fleeting Notes is the only
write surface — it touches only `PKM/Fleeting Notes/` — and you can turn it off
(`WORKBENCH_WRITE_ENABLED=0`).

## Finance & bank connectors — read this first

> **⚠ Finance & bank connectors — unsupported example, use at your own risk**
>
> This cockpit can be connected to external task, calendar, and finance tools.
> Any finance or banking integration — for example reconciling transactions
> against **MoneyMoney** or another bank tool — is provided only as an
> **example of how the cockpit's author does it**, so that your own LLM
> assistant can study the pattern and build something for you. It is **not a
> product feature, not a recommendation, and not supported.**
>
> **You alone** set up and operate any connection between this cockpit and your
> bank, payment tools, or money-management software. **You alone** are
> responsible for your credentials and for the safety, accuracy, and integrity
> of your financial data.
>
> The software is provided **"as is", with no warranty and no liability**.
> myICOR accepts **no liability** for anything that goes wrong with your
> financial data, your bank connection, or your setup — including loss,
> corruption, or unauthorized access — whether or not it follows an example
> shown here. See the LICENSE (Sections 8–10) for the full terms.

> **⚠ Finanz- & Bank-Konnektoren — nicht unterstütztes Beispiel, Nutzung auf eigene Gefahr**
>
> Dieses Cockpit kann mit externen Aufgaben-, Kalender- und Finanz-Tools
> verbunden werden. Jede Finanz- oder Bank-Integration — zum Beispiel der
> Abgleich von Transaktionen mit **MoneyMoney** oder einem anderen Bank-Tool —
> wird ausschließlich als **Beispiel dafür bereitgestellt, wie der Autor des
> Cockpits es selbst macht**, damit dein eigener LLM-Assistent das Muster
> studieren und etwas für dich nachbauen kann. Es ist **keine Produktfunktion,
> keine Empfehlung und wird nicht unterstützt.**
>
> **Du allein** richtest jede Verbindung zwischen diesem Cockpit und deiner
> Bank, deinen Zahlungs-Tools oder deiner Finanzsoftware ein und betreibst sie.
> **Du allein** bist für deine Zugangsdaten und für die Sicherheit, Richtigkeit
> und Integrität deiner Finanzdaten verantwortlich.
>
> Die Software wird **„wie besehen" („as is") ohne jegliche Gewährleistung und
> ohne Haftung** bereitgestellt. myICOR übernimmt **keine Haftung** für Schäden
> an deinen Finanzdaten, deiner Bankverbindung oder deiner Einrichtung —
> einschließlich Verlust, Beschädigung oder unbefugtem Zugriff — unabhängig
> davon, ob ein hier gezeigtes Beispiel befolgt wurde oder nicht. Die
> vollständigen Bedingungen findest du in der LICENSE (Abschnitte 8–10).
>
> *Soweit zwingendes Recht (z. B. Haftung für Vorsatz und grobe Fahrlässigkeit
> oder für Schäden an Leben, Körper und Gesundheit) eine Haftungsbeschränkung
> nicht zulässt, gilt diese Beschränkung insoweit nicht.*

## Optional feature packs

`modules/` ships two ready-to-activate packs your LLM assistant can wire in
during install (or later): **Health** (dashboard over your health data) and
**Workouts** (GPX route maps). Both optional, local, off by default — just ask
your assistant to activate one.

## Make it yours: drop-in modules

The core is deliberately small. Want a recipes library? A films & series
shelf? A reading list? Ask your LLM assistant — e.g. *"add a recipes library
to my cockpit"*. The module seam is built in
(`web/src/lib/moduleRegistry.tsx`), and `examples/library-module/` contains a
complete worked example it can copy from. One registry entry = one new sidebar
section.

## Using it from your phone (optional)

By default the cockpit is reachable only from the computer it runs on. To use
it from your own phone/tablet on your own home network:

1. Set a PIN: `npm run set-pin` (from this folder). Only a hash is stored.
2. Launch with `COCKPIT_BIND_LAN=1`.

Without a PIN, LAN mode refuses to start — your second brain doesn't go on the
network ungated. And to be explicit: this is **per-user software**. Run it for
yourself, on your machine. It is not a hosting setup for serving other people.

## Uninstall

Delete `Expansions/mypka-cockpit/`. Your markdown is untouched. `mypka.db`
(the scaffold's SQLite layer) and `PKM/Fleeting Notes/` (your own notes and
whiteboards) stay — remove them yourself if you really want to.

## Documentation

| Doc | What it is |
|---|---|
| [`INSTALL.md`](./INSTALL.md) | The install contract — the 8-step procedure your assistant follows. **Start here.** |
| [`HOW-IT-WORKS.md`](./HOW-IT-WORKS.md) | Architecture: the read-only mirror model, the two-DB split, ports, CSP, the BYO-key chat bridge. |
| [`CUSTOMIZE.md`](./CUSTOMIZE.md) | Adapt the cockpit to any knowledge base: re-point the root, remap conventions, add/remove modules. |
| [`docs/journal-integration.md`](./docs/journal-integration.md) | The manual journal entry → integration flow: how a raw note becomes a graph-linked entry, the original-preservation guarantee, adapting the integration prompt. |
| [`sqlite-extension/DATA-CONTRACT.md`](./sqlite-extension/DATA-CONTRACT.md) | The exact tables/views the cockpit reads; required vs. optional; the upgrade mapping. |
| [`SECURITY.md`](./SECURITY.md) | Security policy: how to report a vulnerability, the loopback/PIN posture, the BYO-key rule. |
| [`DISCLAIMER.md`](./DISCLAIMER.md) | The backup / breaking-changes / AS-IS install disclaimer (surfaced at install Step 0). |

## License

myPKA Cockpit is **source-available** and **free for personal, non-commercial
use** under the **myICOR Cockpit Personal-Use License** (adapted from the
PolyForm Noncommercial License 1.0.0). See [`LICENSE`](./LICENSE) for the full
terms and [`NOTICE`](./NOTICE) for third-party attributions.

In plain language:

- **You may** download it, run it on your own machine, read and study the
  source, modify it (including with your own LLM), and share your changes —
  all free of charge, for personal/non-commercial use.
- **You may not** sell it, sublicense it for a fee, redistribute it
  commercially, or run it as a paid product or hosted service for other people.
  Those uses require a separate commercial license from myICOR.
- It comes with **no warranty and no liability** (AS-IS). In particular, the
  example finance/bank-connector pattern is unsupported and is your sole
  responsibility — see the finance callout above and `LICENSE` Sections 8–10.

Some optional components carry their own licenses (e.g. the optional workouts
pack uses `react-leaflet` under the Hippocratic License 2.1, which is not
compiled into the core app unless you activate that pack). See [`NOTICE`](./NOTICE).
