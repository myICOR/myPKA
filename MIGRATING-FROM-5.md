# Moving from myPKA v5 to 6.0.0

This page is for you if you run a myPKA v5 folder (it has `VERSION`, `.scaffold-version`, `PKM/` and `Team/` at the top), or if you forked this repository while it was on v5.

## The short version

6.0.0 is not an update of your v5 folder. It has a new shape, so there's no automatic path, and the updater refuses a v5 folder on purpose: it stops and writes nothing.

You don't have to move. Your v5 folder keeps working as it is, and v5.5.2 stays downloadable from its release page. When you do move, you set up a fresh folder and let the team import your v5 content into it. Your v5 folder is never changed along the way.

## What changed

In v5, one folder held everything: your knowledge and the AI team. From 6.0.0 on, they're two products:

- **ICOR for Life 2.0.0** holds your content: journal, contacts, projects, notes, inbox, work in progress.
- **myPKA 6.0.0** is the AI team: agents, contracts, SOPs, Workstreams, Guidelines, scripts.

You can keep them in one folder (mode A, the closest to v5) or side by side (mode B). The details are in [README-myPKA.md](README-myPKA.md).

Where your v5 things end up, roughly. The import shows you the exact mapping and waits for your yes before it writes anything.

| In v5 | In 6.0.0 | Product |
| --- | --- | --- |
| `PKM/` (journal, CRM, My Life, documents) | the Inner World room | ICOR for Life |
| `PKM/Images/` | the Assets room | ICOR for Life |
| `Team Inbox/` | the Inbox | ICOR for Life |
| `Deliverables/` | the WiP room | ICOR for Life |
| `Team/<Name> - <Role>/AGENTS.md` | `06 AI Team/Agents/<Name>/AGENT.md` | myPKA |
| `Team Knowledge/` (SOPs, Workstreams, Guidelines, tasks, session logs) | `06 AI Team/AI Team Knowledge/` | myPKA |
| `Expansions/` | `06 AI Team/Expansions/` | myPKA |
| `CLAUDE.md` and `AGENTS.md` | `AGENTS.md` only, plus `AGENTS.local.md` for your own rules | myPKA |
| `VERSION`, `.scaffold-version`, `manifest.json` | `.mypka/VERSION`, `.mypka/manifest.json` | myPKA |
| `scripts/update-scaffold.py`, `--apply` | `mypka-update.py`, `--live` | myPKA |

More that changed:

- **No `CLAUDE.md`.** Every host reads `AGENTS.md` now. The host table in [README-myPKA.md](README-myPKA.md) shows how each one finds it.
- **The team grew from 6 agents to 11.** All six v5 agents are still there, and five new ones joined. The team table in [README-myPKA.md](README-myPKA.md) lists every agent and their job.
- **Numbers.** Every numbered file we ship (SOP, WS, GL) uses 1000 to 1999. Numbers below 1000, and from 2000 up, are yours, so your own v5 files never collide with ours.
- **Not in 6.0.0:** the myPKA Cockpit and the SQLite conversion (v5's SOP-002). If you use them, they stay in your v5 folder, unchanged.
- **Your v5 folder won't tell you about 6.0.0.** Its update check reads a version file at the top of this repository, and 6.0.0 keeps its version in `.mypka/VERSION`. And v5's `update-scaffold.py` can't apply 6.0.0: it stops, because the 6.0.0 manifest has a different shape.

## Step by step

1. **Make a copy of your v5 folder.** Nothing below changes it, but a copy costs you nothing.
2. **Download both products:**
   - myPKA 6.0.0: `mypka-6.0.0.zip` from https://github.com/myICOR/myPKA/releases
   - ICOR for Life 2.0.0: `icor-for-life-obsidian-edition-2.0.0.zip` from https://github.com/TomSolid/icor-for-life-scaffold/releases
3. **Check that both are genuine** with the GitHub CLI (`gh`). Each command is one line. Continue only if both print that verification succeeded:

   ```
   gh attestation verify mypka-6.0.0.zip --repo myICOR/myPKA --signer-workflow myICOR/myPKA/.github/workflows/release-mypka.yml --source-ref refs/tags/v6.0.0 --deny-self-hosted-runners
   gh attestation verify icor-for-life-obsidian-edition-2.0.0.zip --repo TomSolid/icor-for-life-scaffold --signer-workflow TomSolid/icor-for-life-scaffold/.github/workflows/release.yml --source-ref refs/tags/2.0.0 --deny-self-hosted-runners
   ```

   Note the tags: myPKA's start with `v`, ICOR for Life's don't.
4. **Unpack ICOR for Life into a new, empty folder.** Not into your v5 folder.
5. **Unpack myPKA into that same folder** (mode A):

   ```
   unzip mypka-6.0.0.zip -d "/path/to/your new folder"
   ```

   The zip holds hidden files whose names start with a dot. Moving files by hand in the Mac Finder leaves them behind, and `unzip` keeps them. For mode B instead, follow [README-myPKA.md](README-myPKA.md).
6. **Move your keys yourself.** Copy the lines you need from your v5 `.env` into a `.env` in the new folder. Never paste a key into the chat.
7. **Move your own rules.** If you wrote your own rules into v5's `CLAUDE.md` or `AGENTS.md`, put them into `AGENTS.local.md`, next to the new `AGENTS.md`. That file is yours: no update ever overwrites it. It can't switch off a hard rule or a guard.
8. **Open the new folder in your AI and import.** In the first session, Larry offers to import existing knowledge and AI teams. Say yes and give him the path to your v5 folder. Later on, you can ask for it any time: "import my myPKA v5 folder from `<path>`". Then:
   - The team takes stock of your v5 folder and drafts a mapping: what goes where, with counts. **Nothing is written until you approve it.**
   - Penn converts your notes into the new structure, links included.
   - Agents you hired in v5 don't land as they are. Nolan decides for each one: hire it again as a proper agent, merge it into an existing agent, or keep its knowledge as SOPs and Guidelines.
   - Silas checks the result, and you compare three converted notes with their originals together.
   - Your v5 folder is never changed or deleted. The import is a copy plus a conversion.

   One honest note: the import doesn't recognise the v5 layout by name yet. It reads your v5 folder as a plain markdown folder. So read the mapping carefully before you say yes, especially for `Team/` and `Team Knowledge/`.
9. **Keep your v5 folder until you're happy.** Retire it when you choose to.

## If you forked this repository

- The v5 history and every `v5.x` tag stay. `main` moves to 6.0.0 in one commit on top of v5. Nothing is force-pushed.
- To stay on v5, build on the tag `v5.5.2`, not on `main`.
- Merging our `main` into a v5 branch doesn't update v5. It brings in the whole 6.0.0 tree, with conflicts wherever you changed a file.
- The download name changed: v5 shipped `mypka-scaffold-latest.zip`, 6.0.0 ships `mypka.zip` and `mypka-<version>.zip`.
- Your copy keeps the license it came with. Copies from v5.3.0 on are CC BY-SA 4.0; copies before v5.3.0 are CC BY-NC-SA 4.0. Creative Commons licenses can't be revoked. 6.0.0 continues the CC BY-SA 4.0 line for prose and adds MIT for code and configuration: see [LICENSE-MAP.md](LICENSE-MAP.md).
- "Built on myPKA" is fine. Naming your version "myPKA" is not: see [TRADEMARK.md](TRADEMARK.md).

## What stays yours

- Your v5 folder, all of it, for as long as you want it.
- Everything the import copies over from your v5 folder, as the mapping you approved says.
- The agents you hired, and their journals, once Nolan has placed them.
- Your keys in `.env`, your `.mcp.json`, and your rules in `AGENTS.local.md`.
- Every file you edit later. An update never overwrites your edits. It puts our new version beside yours as `<file>.update`.
