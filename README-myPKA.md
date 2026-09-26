# myPKA: your AI team

myPKA (My Personal Knowledge Assistance) is the architecture for an AI team that works with you: clear roles, shared instructions, repeatable procedures and memory across sessions. This folder is a ready-made team built on it. The team already knows ICOR, and it works on the notes, projects and tasks in your ICOR for Life folder.

How the three names fit together:

- **ICOR** is the methodology: how you take things in, keep them under control, turn them into output and refine the loop.
- **ICOR for Life** is where you put ICOR into practice. It works fully without AI.
- **myPKA** is the AI team you add when you want help. It's this folder.

What the team gives your AI is better context, a clear job for every agent, procedures it can repeat and a record of what happened last session. It doesn't make the model smarter, and it doesn't make every answer right. You stay in charge, and you review the work.

This file is called `README-myPKA.md` because, when myPKA sits inside your ICOR for Life folder, the folder's `README.md` belongs to ICOR for Life.

## The team

You talk to Larry. He works out what you need, hands it to the right specialist and brings the result back to you.

| Agent | What they do |
| --- | --- |
| **Larry** | Orchestrator. Your one point of contact. Routes the work and never does a specialist's job himself. |
| **Penn** | Files your scratchpad notes, Inbox captures and journal entries into the right place. Repairs what you filed by hand, after you say yes. |
| **Nolan** | Hires a new specialist when a job has no owner. |
| **Pax** | Research and fact checks before anything is acted on. |
| **Mack** | Connects tools: MCP servers, APIs, webhooks, logins. |
| **Silas** | Structure: frontmatter, health checks, the shape of an import. |
| **Iris** | Your design system. |
| **Charta** | Infographics, tables, diagrams and one-pagers. |
| **Flint** | The Obsidian platform: plugin and theme questions. |
| **Ada** | Plans bigger jobs before anyone starts, and audits the team's own setup. |
| **Mason** | Turns a plugin bug or wish into a fix and a pull request. |

The full routing table is `06 AI Team/Agents/agent-index.md`. When you need a role nobody covers, Nolan hires one.

## Open it in your AI

`AGENTS.md` is the one entry file. Every host reads the same file, so the team behaves the same wherever you run it.

| Host | How it finds `AGENTS.md` |
| --- | --- |
| Claude Code (2.1.277 or later) | Reads it directly. No `CLAUDE.md` ships. |
| Codex | Reads it directly. |
| Gemini CLI | Through `.gemini/settings.json`, in a trusted folder. |
| Cursor | Reads it directly. |
| Any other host, or an older Claude Code | Paste `ADAPTER-PROMPT.md` as your first message. |

Start your AI session in the folder that holds `AGENTS.md`. If your AI tells you the setup for your host is missing, it prints this command and waits for you:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/scaffold-init.py" plan
```

`plan` shows what would be written and changes nothing. Run it with `apply` instead of `plan` to write it.

The scripts need Python 3 and nothing else. On Windows, type `py -3` where this page says `python3`.

## Two ways to set it up

**Mode A: inside your ICOR for Life folder.** One folder holds both. This is the usual choice if you already use ICOR for Life. It needs no extra setup. The two products share no file names, so neither one overwrites the other.

**Mode B: next to your ICOR for Life folder.** myPKA gets its own folder, beside your content:

```
your-parent-folder/
  mypka/            start your AI session here
  icor-for-life/    your ICOR for Life folder
```

Mode B needs one file that tells the team where your content is. From inside the `mypka` folder:

```
cp .mypka/sources.mode-b.yaml.example .mypka/sources.yaml
python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --check
```

If your ICOR for Life folder has another name or sits somewhere else, change `root:` in `.mypka/sources.yaml` first. The check should report `binding: compatible, mode B`. In mode B, always start your AI session in the `mypka` folder, never in the ICOR for Life folder.

**Moving from mode A to mode B later, with expansion packs installed.** In mode A the install receipts are in your ICOR for Life folder, at `.icor-for-life/expansions/`. In mode B the tools look for them in the `mypka` folder, at `.mypka/expansions/`. When you move the team out, move every file from that folder into `mypka/.mypka/expansions/` too. They stay behind otherwise, and without them `expansion-pack.py` lists your packs as not installed and refuses to remove them.

`.mypka/sources.yaml` belongs to one device, because it holds a path on that machine. A second computer needs its own copy.

## What works today, and what's coming

Today the team works on an ICOR for Life folder on your own disk, in mode A or mode B.

Coming: connecting myPKA to an ICOR for Life setup in Notion or Tana. `sources.yaml` already has a place for it, but no connector ships in this version.

## Install

1. Download `mypka.zip` from the latest release: https://github.com/myICOR/myPKA/releases/latest/download/mypka.zip
2. Check that it's genuine (next section). Only continue if the check passes.
3. Unpack it:
   - Mode A, into your ICOR for Life folder: `unzip mypka.zip -d "/path/to/your ICOR for Life folder"`
   - Mode B, into a new folder next to it: `unzip mypka.zip -d "/path/to/your-parent-folder/mypka"`, then the mode B step above.
4. Open the folder in your AI.

The zip holds hidden files and folders whose names start with a dot (`.mypka`, `.claude`, `.codex`, `.gemini`, `.mcp.json`). If you move the files by hand in a file manager that hides them (the Mac Finder does, by default), they get left behind. The `unzip` command keeps them.

Already running an ICOR for Life folder from version 1.34 or earlier, with the team inside it? Don't unpack over it. Use the steps in "Coming from ICOR for Life 1.34 or earlier" below.

## Check that a download is genuine

Every myPKA release zip carries a build-provenance attestation: a signed record that says which workflow built these exact bytes, from which tag. Before you unpack or apply a download, check it with the GitHub CLI (`gh`). Put the version you downloaded in place of `<version>`, as one line:

```
gh attestation verify mypka-<version>.zip --repo myICOR/myPKA --signer-workflow myICOR/myPKA/.github/workflows/release-mypka.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

Use the download only if it prints that verification succeeded. The unversioned `mypka.zip` is the same bytes and checks with the same command. `mypka-update.py --help` prints the command for both products.

## Updating

Download the new release, check it (above), then run the updater from the folder that holds `AGENTS.md`:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/mypka-<version>.zip
```

That's a dry run. It prints the plan and writes nothing. Read the plan. When you're happy with it, run the same command again with `--live` at the end.

What the updater does, and doesn't do:

- It writes only the files the release lists. It never deletes anything.
- A file you edited stays exactly as you left it. If we changed that file too, our new version lands next to yours as `<file>.update`, so you can compare and decide.
- `.mcp.json` is yours after the first install. An update never overwrites it.
- It refuses a download whose files don't match its own manifest, an older version than the one you have, and a myPKA v5 folder (see `MIGRATING-FROM-5.md` in the myPKA repository on GitHub).

**ICOR for Life updates run through the same updater.** Update myPKA first, then ICOR for Life:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/icor-for-life-obsidian-edition-<version>.zip --product icor
```

Again a dry run first, then `--live`. The updater finds your ICOR for Life folder by itself, in both modes.

### Coming from ICOR for Life 1.34 or earlier

Until 1.34, the AI team shipped inside ICOR for Life. Your folder already holds it, but not the new updater yet, so you run the one inside the download:

1. Unpack `mypka-6.0.0.zip` into a temporary folder. Not into your ICOR for Life folder.
2. Run the updater from that temporary folder, pointed at your folder. Dry run first, then again with `--live`:

   ```
   python3 "<temporary folder>/06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release mypka-6.0.0.zip --target "/path/to/your ICOR for Life folder"
   ```

3. Then update ICOR for Life to 2.0.0 from your own folder, with the `--product icor` command above.

Your notes aren't touched. Team files you edited are kept, with `.update` beside them where we changed them too. An old `CLAUDE.md` or `GEMINI.md` stays where it is, because the updater never deletes. If it only points to `AGENTS.md`, it does no harm. If you wrote your own rules into it, move them to `AGENTS.local.md`.

## You stay in control

- **Dry run first, every time.** Nothing is written until you add `--live`.
- **Nothing is deleted by an update.** Your edits win, and our changes wait beside them as `.update` files.
- **Your own rules have their own file.** `AGENTS.local.md`, next to `AGENTS.md`, is yours: never shipped, never overwritten. The same goes for `AGENT.local.md` next to any agent's `AGENT.md`. It can add rules and change preferences. It can't switch off a hard rule or a guard.
- **You run the scripts.** The AI names the command, and you start it. The one exception is the hire scripts Nolan runs during a hire, and he tells you afterwards.
- **Ask before every write, if you want.** `write: ask` in `.mypka/sources.yaml` makes the team show you each change and wait for your yes. The mode B example already uses it. In mode A, copy `.mypka/sources.yaml.example` to `.mypka/sources.yaml` to switch it on.
- **Your keys stay in `.env`.** The team never asks you to paste a key into the chat and never writes one into a note.

## License

- Prose (`AGENTS.md`, agent contracts, SOPs, Workstreams, Guidelines, this file): CC BY-SA 4.0, in `LICENSE`.
- Code and configuration: MIT, in `06 AI Team/AI Team Knowledge/Scripts/LICENSE-myPKA`.
- `LICENSE-MAP.md` says in plain words which license covers what.
- The names and logos are covered by neither license: see `TRADEMARK.md`.

In mode A each file keeps its own license: ICOR for Life's files follow ICOR for Life's `LICENSE.md`.

## Security

Found a security problem? Report it privately, never in a public issue. How: `SECURITY-myPKA.md`.

## Version

Your version is in `.mypka/VERSION`. What changed in each version, and every file that moved: `.mypka/CHANGELOG.md`.
