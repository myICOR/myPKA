# myPKA scripts

The deterministic half of the AI team's work. Anything a machine can tell
you got wrong lives here as code; anything only judgement can answer stays
as prose in the SOPs, Workstreams and Guidelines
([[GL-1005-code-vs-instructions|GL-1005]]).

This file is named `README-myPKA.md` because in mode A the `Scripts/` folder
is shared, and `README.md` there belongs to ICOR for Life (its life scripts).
Repo-only release tooling (the manifest builder, the release gates,
`release-gate-red-tests.sh`, `zip-staged-tree.sh`) never reaches your folder
and is not listed.

Every script prints `OK ...` and exits 0 when it is happy, and `FAIL ...`
with exit 1 when it is not. Every guard in here is red-tested by
`run-red-tests.py`: fed something it must reject, and watched to make sure
it actually says no.

## The scripts

| Script | What it does | Typical call |
| --- | --- | --- |
| `add-mcp-server.py` | Wires an external tool's official MCP server into the scaffold, with the key in `.env` and never in a tracked file | `add-mcp-server.py <name> --command npx --args ...` |
| `check-hire.py` | Refuses an incomplete hire: 22 checks over one agent, from the contract frontmatter and the id to the shim, the skills, the guards and the research brief. `--self-test` plants every defect and proves each check can go red | `check-hire.py <Name>`, `check-hire.py --all` |
| `check-onboarding.py` | Says whether this vault is FRESH or already lived in, so the first session knows which greeting to give | `check-onboarding.py` |
| `checkpoint.py` | The deterministic half of a session checkpoint: what shipped, what is still open, and whether THIS session wrote its completion receipt | `checkpoint.py --write-receipt --output "<log>"`, then `checkpoint.py --assert-logged` |
| `import-file.py` | Copies one external file into the scaffold with the placement rules enforced | `import-file.py <path>` |
| `import-inventory.py` | Scans an external knowledge source and reports what is in it, as JSON, before anything is imported | `import-inventory.py <folder>` |
| `mint-agent-ids.py` | Gives every agent contract its stable `myicor_id`, and checks that none is missing, malformed or shared | `mint-agent-ids.py --check` |
| `new-agent.py` | The scripted half of a hire: the agent folder, the contract and bio skeletons, the minted id, the first `Journal/` entry, and the index row. Refuses to overwrite a contract. Drops `06 AI Team/Agents/<Name>/.hiring`, the marker that lets the write guard accept writes to that one contract for the next 24 hours; a green `check-hire.py <Name>` deletes it. No `ICOR_UNLOCK_WRITES` on a hire | `new-agent.py <Name> --slug <slug> --role "<Role>"` |
| `new-progress-report.py` | Creates or re-stamps the `progress-report.md` inside a work folder of the `wip` concept (GL-1013) | `new-progress-report.py --wip <folder> --touch` |
| `new-session-log.py` | Creates a session log skeleton in `Session Logs/YYYY/MM/` | `new-session-log.py --agent larry --slug ...` |
| `new-task.py` | Creates a task, or moves one through open, in-progress, done and cancelled | `new-task.py new --slug ... --title ... --assignee penn` |
| `run-red-tests.py` | Feeds every guard in this folder something it must reject and confirms it says no | `run-red-tests.py` |
| `scaffold-init.py` | Generates the whole harness layer from the scaffold's own frontmatter: skills, agent shims for three hosts, hook configs and host pointer files. `plan` shows, `apply` writes, `check` refuses a drift or a hand-edit, `doctor` reports per host | `scaffold-init.py plan`, then `apply`, `check`, `doctor` |
| `scaffold-init.py doctor --json` | The same doctor report, also written to `.mypka/state/harness.json` (`schema: 1`, team state since 2026-09-24, GL-1013 section 2.2) for the Scaffold Check plugin, which renders it as the Harness block. Machine-layer data under GL-1008: per device, regenerated, never tracked. `--no-tests` skips the red-test run | `scaffold-init.py doctor --json` |
| `session-start.py` | The SessionStart hook entry, spawned directly with `-I -B -X utf8` and no shell in the chain. Runs `check-onboarding.py`, `check-quality.py --write` when quality.json is stale, and `expansion-pack.py list`, prints the results as session context, and records which session this is for `checkpoint.py` | `session-start.py` |
| `skill-doctor.py` | Checks every `SKILL.md`: the name, the description and its trigger, one pointer at a real SOP, the generated header, host-only frontmatter, dashes, command clashes, and the total description budget | `skill-doctor.py --all` |
| `write-guard.py` | The PreToolUse guard on the file-writing tools: refuses a write to a Daily Scratchpad, to the root entry contracts or to a specialist contract, and refuses any write carrying a secret-shaped value. Exit 2 blocks; a fresh `.hiring` marker next to a contract lets that one contract through during its hire, and `ICOR_UNLOCK_WRITES=1` lifts the guard for one call on an approved edit of an existing contract | (the hook runs it) |
| `check-icor-concepts.py` | Proves `.mypka/icor-concepts-1.json` covers the spec it was built from. Read-only | `check-icor-concepts.py` |
| `expansion-pack.py` | Lists, inspects, installs and removes reviewed AI Team expansion packs: it copies their files and runs none of them (GL-1012, WS-1006) | `expansion-pack.py list` |
| `test-expansion-pack.py` | The fixture suite behind `expansion-pack.py`: ownership, conflicts and path boundaries in temporary folders | `test-expansion-pack.py` |
| `mypka-update.py` | Applies a new myPKA or ICOR for Life release to your folder, in mode A or mode B, without losing an edit of yours and without deleting anything. Dry run first, then `--live` | `mypka-update.py --release <folder> --target <folder>` |
| `resolve.py` | Turns a concept (`journal`, `wip/operations`) into a place, and finds the myPKA root; the only code that does either (GL-1013) | `resolve.py --check` |
| `validate-team.py` | Validates what the team ships and keeps under the team root: the team half of the old `validate-scaffold.py` | `validate-team.py .` |
| `noteio.py` | Reads and writes a member's file without rewriting a byte the caller never meant to touch; ICOR for Life carries a pinned copy as `noteio-icor.py` | (the scripts import it) |
| `hooks-rules.json` | The one table of guard rules each host's hook config is rendered from | (read by `scaffold-init.py`) |

## The guards, and what they do not prove

Three of the scripts above are not run by a person at all: a host's hook
runs them, before a write or at the start of a session. Which rules exist,
which script answers each one, and how each host's config is rendered from
that, all live in ONE file: `hooks-rules.json`, next to these scripts. The
Claude Code rendering is `.claude/settings.json`, hand-rendered for now and
explained in `.claude/settings.README.md`. Change the table, never the
rendered config.

Every guard here obeys the same four rules:

1. **It fails open.** An error inside it, or a run past its wall-clock
   budget, prints one line and lets the work through. An unknown must never
   render as clean, and a guard that stalls a turn gets switched off.
2. **It has an unlock, and the unlock is red-tested.**
   `ICOR_UNLOCK_WRITES=1`, set for one command. A guard with no way through
   is deleted the first time it blocks real work, and then it protects
   nothing.
3. **It says what it does not prove**, in its own docstring and in
   `hooks-rules.json`. A `PreToolUse` guard sees tool calls. A shell
   redirect, a script, or an editor outside the session reaches the same
   files untouched. **No hook here is an enforcement boundary and no
   document may call one that.**
4. **It is in `run-red-tests.py`** with a case it must refuse and a clean
   control it must let through. A guard that refuses everything proves as
   little as one that refuses nothing.

## The completion receipt

`checkpoint.py --write-receipt` writes
`.mypka/state/receipts/<session-id>.json` (`schema: 1`), in the
machine layer ([[GL-1008-the-machine-layer|GL-1008]]): the workflow it
closes, the session, when it started and finished, the inputs and outputs
with their sha256, which version of the script wrote it, and anything
knowingly left open. `--assert-logged` reads THAT, so a session log written
in the morning can no longer close an afternoon session that wrote nothing.
The session id comes from `.mypka/state/session.json`, written by
`session-start.py`. Where there is no session start hook there is no id, and
the assert says so rather than guessing; `--assert-logged-today` is the old
date-only check, kept under its true name and weaker by design.

## Optional AI Team packs

`expansion-pack.py list|inspect|install|remove` manages additive pack files.
See [[GL-1012-ai-team-expansions]] for the manifest and
[[WS-1006-install-an-ai-team-expansion]] for the LLM-guided procedure.
`test-expansion-pack.py` exercises ownership, conflict and path boundaries
in temporary vaults.
