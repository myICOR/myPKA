# myPKA: your AI team

myPKA (My Personal Knowledge Assistance) is the architecture for an AI team that works with you: clear roles, shared instructions, repeatable procedures and memory across sessions. Since myPKA 7.0.0 it ships again as **one folder**: your rooms, templates and life scripts (the content that was called ICOR for Life from August to October 2026), the Obsidian setup, and the team, in one download. The folder's `README.md` is the place to start; this file is the team's own guide.

How the names fit together:

- **ICOR** is the methodology: how you take things in, keep them under control, turn them into output and refine the loop.
- **myPKA** is the folder where you put it into practice, with an AI team that works in it with you. It works fully without AI too, and fully without Obsidian.
- **ICOR for Life** is the name the content half carried while it was a separate download (2.x). Its files still keep their technical home, `.icor-for-life/` (version, changelog, manifest), because the updater and the Scaffold Check plugin read them there.

What the team gives your AI is better context, a clear job for every agent, procedures it can repeat and a record of what happened last session. It doesn't make the model smarter, and it doesn't make every answer right. You stay in charge, and you review the work.

Learn it in the myPKA course: https://app.myicor.com/courses/mypka-system

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
| **Vex** | Security reviewer. Reviews anything you did not write before it runs, and audits your app's security. Proves, never applies the fix. |
| **Felix** | Frontend developer. Builds, fixes and audits web UI in your own code projects; code stays outside the folder. |
| **Vera** | Quality gate for visual and UI work: your design system, WCAG 2.2 AA, the reader's needs. APPROVED, CONDITIONAL or BLOCKED. |
| **Pixel** | Image maker: thumbnails, social images, covers, illustrations, avatars in your own look, or a ready image brief. |

Vex, Felix, Vera and Pixel were separate agent packs until 7.0.0. They are team members now.

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

## One folder, or two

**One folder (the default since 7.0.0).** Unzip the download and everything is in place: the rooms, the team, the Obsidian setup. The team's files and the content's files share no file names, so neither half overwrites the other when you update.

**Two folders (mode B), if you already run it that way.** The team can live in its own folder, beside your content:

```
your-parent-folder/
  mypka/            start your AI session here
  icor-for-life/    your content folder
```

Mode B needs one file that tells the team where your content is. From inside the `mypka` folder:

```
cp .mypka/sources.mode-b.yaml.example .mypka/sources.yaml
python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --check
```

If your content folder has another name or sits somewhere else, change `root:` in `.mypka/sources.yaml` first. The check should report `binding: compatible, mode B`. In mode B, always start your AI session in the `mypka` folder.

**Moving from one folder to two, with expansion packs installed.** In one folder the install receipts are at `.icor-for-life/expansions/`. In mode B the tools look for them at `.mypka/expansions/`. Move every file from the first into the second, or `expansion-pack.py` lists your packs as not installed and refuses to remove them.

`.mypka/sources.yaml` belongs to one device, because it holds a path on that machine. A second computer needs its own copy.

## Expansions

`06 AI Team/Expansion Library/` holds optional packs that ship with myPKA but are not switched on (Voice & File Converter, Handwritten Collaboration Loop). Its `README.md` says how to install one and what to watch for. Packs you add yourself go into `06 AI Team/Expansions/`; your AI inspects them and asks before it installs anything (WS-1006).

## What works today, and what's coming

Today the team works on the folder on your own disk, in one folder or in mode B.

Coming: connecting myPKA to an ICOR setup in Notion or Tana. `sources.yaml` already has a place for it, but no connector ships in this version.

## Install

1. Download `mypka.zip` from the latest release: https://github.com/myICOR/myPKA/releases/latest/download/mypka.zip (or from Tom's Tool Lab on myICOR).
2. Check that it's genuine (next section). Only continue if the check passes.
3. Unpack it into a new folder: `unzip mypka.zip -d "/path/to/myPKA"`.
4. Open the folder in your AI, or in Obsidian as a vault.

The zip holds hidden files and folders whose names start with a dot (`.mypka`, `.icor-for-life`, `.obsidian`, `.claude`, `.codex`, `.gemini`, `.mcp.json`). If you move the files by hand in a file manager that hides them (the Mac Finder does, by default), they get left behind. The `unzip` command keeps them.

Already running a folder? Don't unpack over it. Update it (below).

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

**One download, two commands.** The zip holds both halves. Update the team first, then the content, each a dry run first and then `--live`:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/mypka-<version>.zip
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/mypka-<version>.zip --product icor
```

The updater finds your content by itself, in one folder and in mode B.

**Vex, Felix, Vera or Pixel installed as a pack before 7.0.0?** Remove the pack first, as its README says (`expansion-pack.py remove <name> --approved`, after taking out its roster and SOP rows). It deletes only files you never edited; your journal and `AGENT.local.md` stay. Then update: the team version comes in. Do not install the App Developer Pack or the Designer Pack any more: every agent they added is in the team.

### Coming from ICOR for Life 1.34 or earlier

Until 1.34, the AI team shipped inside ICOR for Life. Your folder already holds it, but not the new updater yet, so you run the one inside the download:

1. Unpack `mypka-<version>.zip` into a temporary folder. Not into your ICOR for Life folder.
2. Run the updater from that temporary folder, pointed at your folder. Dry run first, then again with `--live`:

   ```
   python3 "<temporary folder>/06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release mypka-<version>.zip --target "/path/to/your ICOR for Life folder"
   ```

3. Then update the content from your own folder, with the `--product icor` command above.

Your notes aren't touched. Team files you edited are kept, with `.update` beside them where we changed them too. An old `CLAUDE.md` or `GEMINI.md` stays where it is, because the updater never deletes. If it only points to `AGENTS.md`, it does no harm. If you wrote your own rules into it, move them to `AGENTS.local.md`.

## You stay in control

- **Dry run first, every time.** Nothing is written until you add `--live`.
- **Nothing is deleted by an update.** Your edits win, and our changes wait beside them as `.update` files.
- **Your own rules have their own file.** `AGENTS.local.md`, next to `AGENTS.md`, is yours: never shipped, never overwritten. The same goes for `AGENT.local.md` next to any agent's `AGENT.md`. It can add rules and change preferences. It can't switch off a hard rule or a guard.
- **You run the scripts.** The AI names the command, and you start it. The one exception is the hire scripts Nolan runs during a hire, and he tells you afterwards.
- **Ask before every write, if you want.** `write: ask` in `.mypka/sources.yaml` makes the team show you each change and wait for your yes. The mode B example already uses it. In mode A, copy `.mypka/sources.yaml.example` to `.mypka/sources.yaml` to switch it on.
- **Your keys stay in `.env`.** The team never asks you to paste a key into the chat and never writes one into a note.

## License

- Everything in this folder is MIT from 7.0.0: `LICENSE` (and `06 AI Team/AI Team Knowledge/Scripts/LICENSE-myPKA` for the scripts, as before).
- `LICENSE-MAP.md` says in plain words what that covers, and the few parts with their own terms (the INKLINE theme, libraries some plugins bundle).
- The names and logos are not licensed: see `TRADEMARK.md`.
- Earlier copies keep the license they came with.

## An experiment, not a product

myPKA comes from Tom's Tool Lab: a starting point and inspiration. It may change from one release to the next; there is no support schedule, no promise of fixes and no release cycle. You are responsible for what you install and run, for its security, and for how you use it in your own systems.

## Security

Found a security problem? Report it privately, never in a public issue. How: `SECURITY-myPKA.md`.

## Version

Your version is in `.mypka/VERSION`. What changed in each version, and every file that moved: `.mypka/CHANGELOG.md`.
