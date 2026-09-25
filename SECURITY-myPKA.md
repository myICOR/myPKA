# myPKA security policy

myPKA is mostly markdown: contracts, procedures and guidelines that your AI reads. Markdown doesn't attack anybody. The parts that run are the parts this policy is about: the Python scripts, the hooks that hand two of those scripts to your AI host, and the release pipeline that builds the zip you download.

This file is called `SECURITY-myPKA.md` because, when myPKA sits inside your ICOR for Life folder, the folder's `SECURITY.md` belongs to ICOR for Life.

## The key rule: myPKA never ships or needs a secret

- **No release carries a key, token or password.** Nothing in this repository does either. The release workflow uses only the short-lived token GitHub gives each run, and only on the steps that talk to GitHub.
- **myPKA needs no account and no key to run.** The scripts open no network connection. They read and write files in your folder, nothing else.
- **Your model keys are yours.** The key or login for Claude, Codex, Gemini or any other AI belongs to you and to your AI host. myPKA never asks for it, never stores it and never sees it.
- **Keys for tools you connect stay local, in `.env`.** `.mcp.json` points to them by name, as `${VAR}`, never by value. `.env` is never tracked, never in a zip, and an update never touches it. `add-mcp-server.py` writes an empty line for the key and refuses a key typed on its command line.
- **The one server in the shipped `.mcp.json`** is the myICOR MCP endpoint, with no credential in the file. If you use it, any sign-in happens between your AI host and myICOR. No myPKA file holds it.
- **Never paste a key into the chat.** The team never asks you to.

Found a real secret in a myPKA release, in this repository or in its history? That's the most serious report we can get. Send it at once (below).

## Supported versions

| Version | Security fixes |
| --- | --- |
| 6.x | Yes. Fixes ship as a new 6.x release. |
| 5.x, including v5.5.2 | No. Move to 6.x: [MIGRATING-FROM-5.md](https://github.com/myICOR/myPKA/blob/main/MIGRATING-FROM-5.md). |
| The team inside ICOR for Life 1.34 or earlier | No. Move to 6.x: `README-myPKA.md`, "Coming from ICOR for Life 1.34 or earlier". |

A fix always ships as a new version. A published zip is never replaced or patched in place. To get a fix, download the new release, check it (below), then run the updater: dry run first, then again with `--live`, as `README-myPKA.md` describes. Only the newest 6.x release gets fixes, so stay on it.

## How to report a problem

**Never in a public issue.** Use GitHub's private vulnerability reporting on this repository:

https://github.com/myICOR/myPKA/security/advisories/new

Only you and the maintainers see the report until a fix ships. You need a GitHub account. Without one, write to `support@myicor.com` with `SECURITY` and `myPKA` in the subject.

How we handle personal data in reports: https://myicor.com/privacy#github

A useful report has:

- **The version**, from `.mypka/VERSION`. Please don't guess it from the download date.
- **Your operating system, your Python version** (`python3 --version`) **and your AI host with its version.**
- **Mode A or mode B**, and for mode B your `.mypka/sources.yaml` with any private path replaced.
- **The file and the line.** Name the script under `Scripts/` and the line number, not only the behaviour.
- **Steps to reproduce on a throwaway copy.** Copy the folder to a scratch place and break that one. Never test against notes you care about, and never send us your notes.
- **A harmless proof.** A payload that writes a file named after the finding proves as much as one that deletes a folder, and costs nobody anything.
- **No real credentials.** Never paste a token, a line from your `.env` or your own `.mcp.json`. Describe the credential instead ("the token my Linear MCP server uses"). If one of your keys was exposed, rotate it with its provider first, then report.

## What's in scope

**The updater** (`mypka-update.py`). Any way to make it write a file the release doesn't list, delete anything, or overwrite a file you edited. Any way to make it write through a symbolic link, or outside myPKA's own files (in mode A, into ICOR for Life's). Any way to make it accept a release whose files don't match its manifest, or apply an older version, a v5 folder or a changed release without refusing.

**The write guard** (`write-guard.py`). Any way to make it allow a write it says it refuses (a protected contract, your scratchpad, a secret-shaped value), or to skip it while the session still looks guarded. Its header lists what it doesn't catch, such as a script that writes files itself. Those are known. A new way around it, or a gap in what it says it catches, is in scope.

**The resolver** (`resolve.py` and `.mypka/sources.yaml`). Any way to make it bind the wrong folder, find the wrong myPKA root, send the team's writes outside the places you bound, or make it write, open a network connection or start a program. It is built to do none of the three.

**The hooks** (`.claude/settings.json`, `.codex/hooks.json`, and the `session-start.py` and `write-guard.py` they run). Any way a hook runs something other than the script it names, or the Codex hook's climb to `AGENTS.md` finds the wrong one. The hooks run on Claude Code and Codex. No hook ships for Gemini CLI or Cursor, so the guard doesn't run there. That is known.

**The other scripts** under `06 AI Team/AI Team Knowledge/Scripts/`, including `add-mcp-server.py`, `scaffold-init.py` and `expansion-pack.py`. Any script that writes outside the path it was given, or follows a symbolic link out of your folder. Any script that runs a string built from note content or a file name, or loads code from a folder your notes can reach. Any script that puts a secret into a tracked file, a note, a log line, an error message or your terminal.

**The release workflows** (`.github/workflows/release-mypka.yml`, `.github/workflows/contribution-check.yml`). Any way to get a release out without every gate passing, to build it from anything but its tag, to replace a published file, to inject a command through a pull request, or to reach the workflow's token.

**The attestations and the zip.** A zip that passes the check below without being built by `release-mypka.yml` from its tag on a GitHub-hosted runner. A zip that carries anything not in that tag, a repository-only file or any secret.

## What's out of scope

These aren't vulnerabilities in myPKA, and we close them as such:

- **Your AI host and its model.** Claude Code, Codex, Gemini CLI, Cursor and every other host are third-party software. Report their problems to their makers. myPKA is not a sandbox and can't stop a model you gave file access from using it. A model ignoring an instruction in `AGENTS.md` is a quality issue. A model getting past `write-guard.py` where it runs is in scope, above.
- **Your own keys and your own setup.** Your model keys, your `.env`, your `.mcp.json` after the first install, where you sync your folder and who uses your computer. Anything in myPKA that moves a key out of your folder, or into a file you didn't choose, is in scope.
- **MCP servers and tools you connect yourself.** Report those to their makers.
- **ICOR for Life, its plugins and Obsidian.** ICOR for Life has its own `SECURITY.md` in its own repository, and each plugin has its own.
- **The myICOR web app and its MCP endpoint.** That is a hosted service, not code in this repository. Still use the private form above, say it's about the hosted service, and we pass it to the right people.
- **Problems in Python, git, the GitHub CLI or your operating system.** Report those to their makers. How myPKA calls them is in scope.
- **Hardening with no shown impact.** "The scripts aren't signed", "`.env` isn't encrypted", scanner output with no working proof.
- **Social engineering, physical access, or attacks that need you to already be running the attacker's code.**

## Check that a download is genuine

Every release zip carries a build-provenance attestation: a signed record of which workflow built these exact bytes, from which tag. Check it with the GitHub CLI (`gh`) before you unpack or apply the zip. Put your version in place of `<version>`, as one line:

```
gh attestation verify mypka-<version>.zip --repo myICOR/myPKA --signer-workflow myICOR/myPKA/.github/workflows/release-mypka.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

Use the download only if it prints that verification succeeded. The unversioned `mypka.zip` is the same bytes and checks with the same command. `mypka-update.py --help` prints this command, and the one for ICOR for Life.

What the two checks prove:

- **`gh attestation verify`** proves who built the zip: our release workflow, from that tag, on a GitHub-hosted runner.
- **The updater** proves the zip is complete and unchanged: every file matches its manifest, or nothing is written.

Neither proves the code is free of bugs. That's what this policy is for.

## Our timelines

myPKA is maintained by a small team. We read every report, and we reply when we can. We can't promise a time to reply or a time to ship a fix, and nothing in this policy is a deadline we owe you.

Please keep your finding private until a fix ships, or until 90 days after your report, whichever comes first. If we need more time, we may ask you. Waiting longer is your choice.

When the fix ships, we publish a GitHub security advisory on this repository and name the fix in `.mypka/CHANGELOG.md`. We credit you by name and link in both, unless you'd rather stay anonymous. If a problem is being used against members before a fix exists, we may publish a warning and a safe workaround earlier, and we tell you first.

There's no bug bounty. We can't pay for reports.

## Good-faith research

If you research myPKA in good faith and follow this policy, Paperless Movement S.L., the company behind myPKA, authorizes that research in advance. For that research we won't file a criminal complaint against you (a denuncia or querella in Spain, a Strafantrag in Germany) and we won't bring a civil claim against you.

That holds when you:

- Test only what "What's in scope" lists, on a copy of myPKA on your own computer, or in your own fork or throwaway repository.
- Test the release workflows in your own fork. Don't open a pull request meant to run code in our repository.
- Stop at the first harmless proof. Don't use a finding to reach further, and don't keep any access you gained.
- Don't access, copy, keep, change or destroy data that isn't yours. If you see someone else's data by accident, stop, delete what you have and tell us in your report.
- Don't slow down or break anything for anyone else: no denial of service, no load testing, no spam, no social engineering, no physical access.
- Report only through one of the private channels above, or privately through INCIBE-CERT, Spain's national cybersecurity response team, and keep the finding private for the time set in "Our timelines".

Where it ends:

- **It doesn't cover the myICOR web app, its MCP endpoint or any other hosted service.** Don't test them. If you notice a problem there in normal use, please tell us through the form. Probing the service is not authorized.
- **It binds only Paperless Movement S.L.** We can't give up the rights of anyone else, such as GitHub, other users or the makers of tools you connect. We can't bind a prosecutor or a court in any country. In Spain, for example, a prosecutor can act without our complaint when many people are affected.
- If someone else takes action against you over research that followed this policy, we'll confirm in writing, on request, that we authorized it.
- If your report shows a vulnerability that is being actively exploited, EU law may require us to notify the EU cybersecurity authorities (ENISA and the national response team). We'll tell you when we do, and we won't share your name without your consent unless the law requires it.

Not sure something is allowed? Ask us through the form before you test.

Thank you. A report that arrives privately, from a scratch copy, with the line quoted and nothing real broken, is worth a great deal.
