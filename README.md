# myPKA

**An AI team with clear roles, shared instructions and memory across sessions. It already knows ICOR. Open it in Claude Code, Codex, Gemini CLI or Cursor.**

> **Coming from myPKA v5?** 6.0.0 has a new shape. It doesn't update your v5 folder, and nothing forces you to move. Your v5 folder keeps working, and v5.5.2 stays downloadable from its release page. When you're ready, follow [MIGRATING-FROM-5.md](MIGRATING-FROM-5.md), step by step.

## What myPKA is

myPKA (My Personal Knowledge Assistance) is the architecture for an AI team that works with you. This repository is a ready-made team built on it: the agents, their contracts, the procedures they follow and the scripts that check their work.

- **ICOR** is the methodology: how you take things in, keep them under control, turn them into output and refine the loop.
- **ICOR for Life** is where you put ICOR into practice. It works fully without AI.
- **myPKA** is the AI team you add when you want help. It works on your ICOR for Life folder.

The team gives your AI better context, a clear job for every agent, procedures it can repeat and a record of what happened last session. It doesn't make the model smarter, and it doesn't make every answer right. You stay in charge, and you review the work.

## The team

You talk to **Larry**, the orchestrator. He hands each job to the right specialist and brings the result back. Ten specialists work with him, from **Penn**, who files your notes and your journal, to **Nolan**, who hires a new specialist when a job has no owner. The full team, with every job, is in [README-myPKA.md](README-myPKA.md#the-team).

## Works with your AI

`AGENTS.md` is the one entry file, for every host.

| Host | How it finds `AGENTS.md` |
| --- | --- |
| Claude Code (2.1.277 or later) | Reads it directly |
| Codex | Reads it directly |
| Gemini CLI | Through `.gemini/settings.json`, in a trusted folder |
| Cursor | Reads it directly |
| Anything else | Paste `ADAPTER-PROMPT.md` as your first message |

## Get started

1. **Download** [mypka.zip](https://github.com/myICOR/myPKA/releases/latest/download/mypka.zip) from the latest release.
2. **Check that it's genuine** with the GitHub CLI. Put your version in place of `<version>`, as one line:

   ```
   gh attestation verify mypka-<version>.zip --repo myICOR/myPKA --signer-workflow myICOR/myPKA/.github/workflows/release-mypka.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
   ```

   Continue only if it prints that verification succeeded. `mypka.zip` is the same bytes and checks with the same command.
3. **Choose where it lives:**
   - **Mode A, inside your ICOR for Life folder.** One folder holds both. The two products share no file names, so neither overwrites the other. No extra setup.
   - **Mode B, in its own folder next to your ICOR for Life folder.** You copy one file, `.mypka/sources.yaml`, that tells the team where your content is.
4. **Open the folder in your AI** and say hello to Larry.

The full steps, including mode B and moving from ICOR for Life 1.34, are in [README-myPKA.md](README-myPKA.md). That file also ships inside the download.

**Today** the team works on an ICOR for Life folder on your own disk. **Coming:** connecting myPKA to an ICOR for Life setup in Notion or Tana. No connector ships in 6.0.0.

## Updating

From the folder that holds `AGENTS.md`:

```
python3 "06 AI Team/AI Team Knowledge/Scripts/mypka-update.py" --release ~/Downloads/mypka-<version>.zip
```

That's a dry run: it prints the plan and writes nothing. Read it, then run the same command with `--live` to apply it. The updater never deletes a file, and it never overwrites a file you edited: our new version lands beside yours as `<file>.update`.

## You stay in control

- Every update is a dry run until you add `--live`.
- Your edits win. Your own rules live in `AGENTS.local.md`, which no update ever touches.
- The AI names a script, and you run it.
- Set `write: ask` and the team shows you each change and waits for your yes.
- Your keys stay in `.env`, never in the chat.

## License

Prose is licensed under CC BY-SA 4.0 ([LICENSE](LICENSE)). Code and configuration are MIT ([Scripts/LICENSE-myPKA](06%20AI%20Team/AI%20Team%20Knowledge/Scripts/LICENSE-myPKA)). [LICENSE-MAP.md](LICENSE-MAP.md) says in plain words which covers what. The names are not licensed: see [TRADEMARK.md](TRADEMARK.md). Licensor: Paperless Movement, S.L., Madrid, Spain.

## Contributing and security

Want to help? Read [CONTRIBUTING.md](CONTRIBUTING.md) first: every commit needs a sign-off. Found a security problem? Report it privately as [SECURITY-myPKA.md](SECURITY-myPKA.md) describes, never in a public issue.

Versions and what changed: [.mypka/CHANGELOG.md](.mypka/CHANGELOG.md). Older history: the `v5.x` tags.
