# myPKA

**Your life and work in one folder of plain markdown, organised by ICOR, with an AI team that works in it with you. Open it in Claude Code, Codex, Gemini CLI or Cursor, or in Obsidian, or just a text editor.**

> **myPKA 7: one folder again.** From August to October 2026 the folder (ICOR for Life) and the AI team (myPKA 6) were two downloads. Since 7.0.0 they are one, under the name it started with: rooms, templates, life scripts, the Obsidian setup with twelve pre-installed plugins, and the whole team, including Vex, Felix, Vera and Pixel, who were separate agent packs. Coming from myPKA 6 or ICOR for Life 2? See "Updating" below. From v5: [MIGRATING-FROM-5.md](MIGRATING-FROM-5.md).

Learn it in the free myPKA course: https://app.myicor.com/courses/mypka-system

## What myPKA is

myPKA (My Personal Knowledge Assistance) is the architecture for an AI team that works with you, and the folder it works in.

- **ICOR** is the methodology: how you take things in, keep them under control, turn them into output and refine the loop.
- **myPKA** is where you put it into practice: one folder of plain files, with Larry and his specialists. It works fully without AI too.

The team gives your AI better context, a clear job for every agent, procedures it can repeat and a record of what happened last session. It doesn't make the model smarter, and it doesn't make every answer right. You stay in charge, and you review the work.

## The team

You talk to **Larry**, the orchestrator. He hands each job to the right specialist and brings the result back: **Penn** files your notes and journal, **Nolan** hires a specialist when a job has no owner, **Pax** researches, **Mack** connects tools, **Silas** keeps the structure, **Iris** and **Charta** do design and visuals, **Flint** knows Obsidian, **Ada** plans and audits, **Mason** fixes plugins, **Vex** reviews security, **Felix** builds web UI, **Vera** gates quality and **Pixel** makes images. The full team: [README-myPKA.md](README-myPKA.md#the-team).

## Any AI. Obsidian optional

`AGENTS.md` is the one entry file, for every host.

| Host | How it finds `AGENTS.md` |
| --- | --- |
| Claude Code (2.1.277 or later) | Reads it directly |
| Codex | Reads it directly |
| Gemini CLI | Through `.gemini/settings.json`, in a trusted folder |
| Cursor | Reads it directly |
| Anything else | Paste `ADAPTER-PROMPT.md` as your first message |

Open the folder in Obsidian and trust the author, and the twelve ICOR for Life plugins (Planner, Focus, Connect, AI Chat, Interface, Scaffold Check, SQLite Viewer, Terminal, Outliner, PDF Annotation, Canvases, Scratchpad) and the INKLINE theme switch on. You never need Obsidian: the plugins only add an interface on top of the same files.

## Get started

1. **Download** [mypka.zip](https://github.com/myICOR/myPKA/releases/latest/download/mypka.zip) from the latest release.
2. **Check that it's genuine** with the GitHub CLI. Put your version in place of `<version>`, as one line:

   ```
   gh attestation verify mypka-<version>.zip --repo myICOR/myPKA --signer-workflow myICOR/myPKA/.github/workflows/release-mypka.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
   ```

   Continue only if it prints that verification succeeded. `mypka.zip` is the same bytes and checks with the same command.
3. **Unzip it** into a folder of your own.
4. **Open the folder in your AI** and say hello to Larry, or open it in Obsidian.

## Updating

From the folder that holds `AGENTS.md`, the team first, then the content:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/mypka-<version>.zip
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/mypka-<version>.zip --product icor
```

Each is a dry run: it prints the plan and writes nothing. Read it, then run the same command with `--live`. The updater never deletes a file, and it never overwrites a file you edited: our new version lands beside yours as `<file>.update`. Installed Vex, Felix, Vera or Pixel as a pack? Remove the pack first, as [README-myPKA.md](README-myPKA.md#updating) says.

## An experiment from Tom's Tool Lab

myPKA is something Tom (Thomas Roedl) builds and uses himself, shared as a starting point, not a product. It may change from one release to the next; there is no support schedule, no promise of fixes and no release cycle. You are responsible for what you install and run, for its security, and for how you use it in your own systems.

## License

MIT, for the whole folder from 7.0.0 ([LICENSE](LICENSE)). [LICENSE-MAP.md](LICENSE-MAP.md) says in plain words what that covers and which few parts keep their own terms (the INKLINE theme, bundled libraries). The names are not licensed: see [TRADEMARK.md](TRADEMARK.md). Licensor: Thomas Roedl (Tom) and Paperless Movement, S.L., Madrid, Spain.

## Feedback and security

This repository does not take pull requests. Bugs, questions and ideas go under the myPKA videos on myICOR ([CONTRIBUTING.md](CONTRIBUTING.md)). Found a security problem? Report it privately as [SECURITY-myPKA.md](SECURITY-myPKA.md) describes, never in a public issue.

Versions and what changed: [.mypka/CHANGELOG.md](.mypka/CHANGELOG.md). The content's own changelog ships in the folder at `.icor-for-life/CHANGELOG.md`. Older history: the `v5.x` and `v6.x` tags.
