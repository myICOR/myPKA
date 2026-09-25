---
type: guideline
id: GL-1015
title: Team frontmatter conventions
created: 2026-09-24
---

# GL-1015 Team frontmatter conventions

The team half of GL-1002, moved here verbatim at the split (step 10, 2026-09-24). These are the `side: team` types of `icor-concepts/1`: myPKA's own notes, always under the myPKA root. The common fields and the rule "no agent may invent a field" are in GL-1002 and apply here unchanged; a new team field goes into this file first.

## Per type (team)

| type | required fields | optional fields | template |
| --- | --- | --- | --- |
| task | status (open/in-progress/done/cancelled), assignee | related, due | none: `Scripts/new-task.py` |
| progress-report | status (live/closed), updated (ISO datetime) | plan | none: `Scripts/new-progress-report.py` |
| hire-proposal | owner, title | status (draft/decision-ready/approved), skills (list of skill slugs, or the literal `none, judgement role`; the field `check-hire.py` checks 15 and 18 read) | none: the `proposal.md` in `concept:wip/YYYY-MM-DD-<name>-hire/`, [[SOP-1007-hire-a-new-agent]] row 2 |
| session-log | date, agents | - | none: `Scripts/new-session-log.py` |
| sop / workstream / guideline | id, title | owner (the agent who runs this procedure by default, a lowercase agent slug; carried by every shipped sop and workstream, and by no guideline; ruling 2026-09-16), uses (the SOPs, Workstreams and Guidelines this one reads or invokes, a list of full quoted wikilinks and never bare text, per [[GL-1004-naming-rules]]; ruling 2026-09-16), skill_name (the skill's folder slug; REQUIRED once skill_triggers is non-empty), skill_summary (one sentence), skill_triggers (list of user phrases; non-empty makes the procedure skill-eligible), skill_prerun (one script invocation, injected before step 1); the four skill fields only meaningful on `sop` and `workstream`; wip_folder (text, the standing working folder `concept:wip/workstreams/<Name>/`, set only when it exists; only meaningful on `workstream`; ruling 2026-09-15) | none |
| journal-entry | agent_id (the agent's slug), created (ISO datetime), topic (a slug) | updated (ISO datetime), status (durable/superseded), linked_session_logs, related_journal_entries | none: `Scripts/new-agent.py` seeds `Agents/<Name>/Journal/_template.md` |
| agent-bio | agent, role | - | none |
| agent-soul | agent | - | none: `Agents/Larry/SOUL.md`, Larry only |
| agent | myicor_id (uuid v4, lowercase, immutable), name, role, routing_description (one line, required on every new hire) | shim_reads (list of paths), owns_gates (list of guard ids), brief_waived (why no research brief), tools (comma list of the tools the agent may use, each one from the allowlist `Scripts/check-hire.py` check 11 reads; absent means the host default) | none: `Agents/Agent 01/` |

## Progress reports (ruling 2026-08-29)

Work in `concept:wip` that runs past one session or one step carries one
`progress-report.md` in its folder ([[SOP-1006-start-work-and-archive-a-wip-folder|SOP-1006]]).

- `status` is `live` while the work runs and `closed` when the folder
  goes to `_archive/`.
- `updated` is stamped by `Scripts/new-progress-report.py --touch` on
  every append, never typed. A stale stamp is a lie about the work.
- `plan` wikilinks the plan note when the work has one; leave it off
  when it does not.

## Agents: the stable identity `myicor_id` (ruling 2026-09-07)

Every agent contract (`06 AI Team/Agents/<Name>/AGENT.md`, `type: agent`)
carries `myicor_id`, a UUID v4 in lowercase, written first after `type:`:

```yaml
type: agent
myicor_id: 5d1c6f2e-3a4b-4c7d-8e9f-0a1b2c3d4e5f   # minted once, never changed
name: Penn
role: Knowledge processor
created: 2026-08-27
```

- **Minted once, immutable.** The id is minted when the agent is hired
  (`Scripts/mint-agent-ids.py`, or `uuidgen | tr A-Z a-z`, per
  [[SOP-1007-hire-a-new-agent|SOP-1007]]) and never changed afterwards.
  Everything else about the agent may change under the user's hands, the
  name, the avatar, the whole contract; the id stays. It is the one fact by
  which an installer (ICOR for Life - Connect, for agents delivered from
  the myICOR library) can tell an agent that is already in the vault from
  one that is not, and it is the same UUID the library row for that agent
  carries as its primary key.
- **Never the name.** The id is never shown as the agent's name and never
  appears in a filename, a folder name or a wikilink. `name` and the folder
  stay the human handle.
- **One identity across vaults.** The ten agents this scaffold ships
  (Ada, Charta, Flint, Iris, Larry, Mack, Nolan, Pax, Penn, Silas) carry their
  ids in this repository, and every copy of one of those contracts, in a
  later scaffold release or in any vault that carries it, keeps the same
  id. A new hire in a vault gets a fresh id; an agent that arrives already
  carrying one keeps it ([[SOP-1011-import-or-align-an-external-agent|SOP-1011]]).
- **The template placeholder.** `Agents/Agent 01/AGENT.md` carries the
  literal nil UUID `00000000-0000-0000-0000-000000000000` with a comment
  that the hiring SOP replaces it. A real contract still on the nil value
  fails validation, so no hire can ship without an identity.
- **Plain, unquoted.** The hyphens make the value a string for every YAML
  parser; no quotes.
- **The guard.** `Scripts/mint-agent-ids.py --check` refuses a contract
  without the field, a malformed or shared value, or a template off the
  placeholder; `validate-team.py` runs it. `--export` prints the
  name-to-id map, the way the ten carry their identity into another vault.

## Skills: generated from the SOP, never hand-written (ruling 2026-09-14)

A skill is the door; the SOP is the room. Four fields on an SOP or a
Workstream are the whole input a generator needs to build that door, and
nobody writes a `SKILL.md` by hand, not even on a hire. All four are
optional until a procedure is skill-eligible; `skill_triggers` is what
makes it eligible, and `skill_name` is required from that moment on.

| field | type | required? | what it is | example |
| --- | --- | --- | --- | --- |
| `skill_name` | string, a slug | optional in general; **required whenever `skill_triggers` is non-empty** | The folder the generated skill lands in, `06 AI Team/AI Team Knowledge/Skills/<skill_name>/SKILL.md`, and the `name` inside it. Lowercase letters, digits and hyphens. It is what a user types and a host matches on, so it is a decision rather than a derivation: a slug built from the title would change the moment the title is reworded, and every host link would break with no error. The generator refuses a procedure that has triggers and no `skill_name` rather than guessing one. | `skill_name: import-skill` |
| `skill_summary` | string, one sentence | optional | What this procedure does, in the words a person would use asking for it. The generator renders it into the skill's `description`, the only text a host reads when deciding whether to pick the skill. No procedure detail: that is the SOP. | `skill_summary: "Convert an external skill into this scaffold's shape."` |
| `skill_triggers` | list of strings | optional; a **non-empty** list is what makes the procedure skill-eligible | The phrases the user actually says when they want this run, verbatim, not a description of them and not a restatement of the title. Empty or absent means no skill is generated, which is the right answer for a judgement procedure with no nameable trigger. | `skill_triggers:` then `  - "import this skill"` on the next line |
| `skill_prerun` | string | optional | Exactly ONE script invocation the generated skill injects and runs BEFORE the model reads step 1, so the deterministic half has already happened and the model reads its result instead of fetching it. Prints to stdout, decides nothing ([[GL-1005-code-vs-instructions|GL-1005]]). A procedure that needs two is a procedure whose first step is a script, and that belongs in the SOP. | `skill_prerun: 'python3 "06 AI Team/AI Team Knowledge/Scripts/checkpoint.py" --json'`; a content source's tool is reached through the resolver, `skill_prerun: 'python3 "06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool life-snapshot'` |

**Skill text is host-neutral (ruling 2026-09-24, split plan step 7c; no new field).** `skill_summary`, `skill_triggers`, `skill_prerun` and the SOP body a skill points at never name a host tool (`Bash`, `run_shell_command`, `Read`), a host variable (`${CLAUDE_PROJECT_DIR}`), a hook or a host's dispatch verb; they say "your shell tool", "open the file", "the folder that holds `AGENTS.md`" or a vault-relative path, and a prerun is one vault-relative command.

The rule in one sentence: a skill is generated from these fields into the
canonical home `06 AI Team/AI Team Knowledge/Skills/<slug>/SKILL.md` and
linked from there into `.claude/skills/` and `.agents/skills/`; the skill
is a pointer and the SOP is the body, so procedure text is never copied
into a `SKILL.md`. [[SOP-1012-convert-an-external-skill|SOP-1012]] already
says the same thing for an imported skill, and this is that rule applied
to the ones we author. The canonical home carries the README that states
it; the dot folders hold links, and links are per device.

`skills` on a hire's `proposal.md` (`type: hire-proposal`) is the other
half: it names which skills the hire ships, one slug per nameable
repeatable procedure, each
matching a folder under `06 AI Team/AI Team Knowledge/Skills/`. A
judgement role that ships none writes the literal `none, judgement role`
rather than omitting the key, because an absent key and a deliberate zero
are different facts and a validator has to tell them apart.

## Agents: routing, reads, and gates (ruling 2026-09-14)

Three more fields on an agent contract, so every host binding is rendered
from the contract instead of typed twice:

| field | type | required? | what it is | example |
| --- | --- | --- | --- | --- |
| `routing_description` | string, one line | **required on every new hire** | The routing text a host shim shows in its agent picker and reads when deciding whether to dispatch this agent. It is the source for `.claude/agents/<slug>.md` `description` and for every other host's equivalent, so a routing change is made here and the shims are regenerated, never typed into a shim. Larry is the one exception: he is the main-session identity and is never dispatched, so his contract carries none. | `routing_description: "Knowledge processor. Launch for scratchpad processing, Inbox captures, journal entries, My Life entities, and contacts."` |
| `shim_reads` | list of strings | optional | Vault-relative paths the generated shim tells the agent to read on invocation, beyond its own contract and the root pointer file, which every shim already names. Omit the key when the agent needs nothing always-on past its contract. | `shim_reads:` then `  - "06 AI Team/AI Team Knowledge/Guidelines/GL-1002-frontmatter-conventions.md"` on the next line |
| `owns_gates` | list of strings | optional | The guard ids this agent owns, so a red guard has a name attached to it. An id is the `id` of a rule in `Scripts/hooks-rules.json`, the host-neutral rule table the hook adapters are generated from; until that table exists the id is the guard script's filename stem, which is what the table will key on. Every entry must name a guard that exists, is registered in a host hook config, and has a red test someone has watched fail. Most agents own none; omit the key then. | `owns_gates:` then `  - "check-onboarding"` on the next line |
| `brief_waived` | string, one line | optional | Why this agent needed no research brief, when its domain was already settled. `Scripts/check-hire.py` check 21 accepts it in place of a waiver note in the hire workup folder, and reads the value rather than the key: the text has to say the brief was waived, so an empty or placeholder field waives nothing. Omit the key when a real brief exists and the contract links it. | `brief_waived: "Domain known, brief waived."` |

An `owns_gates` entry with no guard behind it is worse than an empty
list: the roster reads as covered and the gate never fires. Remove the
entry or build the guard.
