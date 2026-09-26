#!/usr/bin/env python3
"""new-agent.py - the scripted half of a hire.

Mack, 2026-09-14. Step 4 of SOP-001 (private) and step 3 of SOP-1007
(public). Same bytes in both folders: the shape is detected at runtime by
`vault_is_public()` in `check-hire.py`, the one function both hire scripts
ask, so one file serves the private vault and the public ICOR for Life
Scaffold. (Until 2026-09-17 this script tested the manifest alone, which a
private vault also carries, and wrote the public skeleton there. Task
tsk-2026-09-17-006; red case 15l in run-red-tests.py.) With no
`check-hire.py` beside it, this script refuses rather than guess.

WHAT IT DOES (everything here has exactly one right answer)
-----------------------------------------------------------
  1. Creates `06 AI Team/Agents/<Name>/`.
  2. Writes the contract skeleton: the public folder copies `Agents/Agent 01/`
     and renames `Agent 01.md`; the private folder writes the GL-025 block.
  3. Mints `myicor_id` by calling `mint-agent-ids.py`, so one script owns ids.
  4. Writes the bio card `<Name>.md` with `type: agent-bio`.
  5. Creates `Journal/` with `_template.md` and a first entry (the hire
     itself), so an empty folder is never handed to version control. Both
     carry THIS hire's `agent_id`; neither is copied from a sibling.
  6. Adds the agent-index row.
  7. Prints the steps a person still has to do, in order.

WHAT IT DOES NOT DO
-------------------
The judgement. It writes skeletons with `<angle bracket>` blanks in them;
Nolan writes the words. It does not write a shim or a `SKILL.md`: those are
rendered from frontmatter by the generator (SOP-001 step 5). It does not run
the validator, and it never announces a hire.

THE HIRING MARKER
-----------------
Both folders run a PreToolUse write guard that refuses a write to
`06 AI Team/Agents/<Name>/AGENT.md`, because a contract is canonical and a
model writing one by accident is exactly the failure the guard exists for.
A hire is the one time that write is intended, so this script drops a marker
that says so:

    06 AI Team/Agents/<Name>/.hiring

`write-guard.py` stands down on THAT contract, and only that one, while the
marker is younger than 24 hours. A green `check-hire.py <Name>` deletes it.

The marker exists because the old instruction, `export ICOR_UNLOCK_WRITES=1`,
cannot be carried out on a single tool call: it is an environment variable, so
a model following it writes the contract from a shell, which is precisely
where the guard cannot see. Pilot C watched both CLIs do that. The env var
remains the second unlock, for an approved edit to something that already
exists. It is a seatbelt, not a lock, and it is here so nobody reaches for the
guard's delete key the first time it blocks real work.

Idempotent: run it twice and the second run changes nothing. It refuses
outright when the contract already exists, because overwriting a contract is
never what anyone meant.

    new-agent.py <Name> --slug <slug> --role "<one line>" [--dry-run]

Exit 0 = created, or already complete. Exit 1 = FAIL line on stderr.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# NO BYTECODE IN THE TREE WE ARE POINTED AT. This script importlib-loads a
# sibling out of Scripts/, and stock CPython then writes
# Scripts/__pycache__/<sibling>.cpython-3NN.pyc beside it, which is INSIDE the
# vault or the repo it was asked to read. A script that writes into the thing
# it measures is a script whose measurement nobody can trust, and the write is
# invisible under macOS's /usr/bin/python3, which redirects bytecode to its own
# cache (Conrad Froehling, 2026-09-16). PYTHONDONTWRITEBYTECODE is read at
# interpreter STARTUP, so only this assignment reaches a process already
# running.
sys.dont_write_bytecode = True

# noteio.py sits beside this script and is loaded by path, not by name, so
# the import needs nothing on sys.path, which is what lets this script run
# under the `-I -B -X utf8` the rendered hooks carry, with its own folder
# dropped from sys.path. A missing noteio.py is a half-upgraded Scripts/
# folder and says so in one line, because a traceback out of an import
# teaches the member nothing about what to do next.
_nio_path = Path(__file__).resolve().parent / "noteio.py"
if not _nio_path.is_file():
    raise SystemExit("FAIL noteio.py is missing from %s. Scripts/ is half "
                     "upgraded; restore noteio.py beside this script and run "
                     "this again." % _nio_path.parent)
_nio = importlib.util.spec_from_file_location("noteio", _nio_path)
noteio = importlib.util.module_from_spec(_nio)
_nio.loader.exec_module(noteio)

HERE = Path(__file__).resolve().parent
# resolve.py sits beside this script and is loaded by path, like noteio.py.
# It is the one code that finds the team root and turns a concept into a
# place (GL-1013 sections 6 and 9).
_rs_path = Path(__file__).resolve().parent / "resolve.py"
if not _rs_path.is_file():
    raise SystemExit("FAIL resolve.py is missing from %s. Scripts/ is half "
                     "upgraded; restore resolve.py beside this script and run "
                     "this again." % _rs_path.parent)
_rs = importlib.util.spec_from_file_location("mypka_resolve", _rs_path)
resolver = importlib.util.module_from_spec(_rs)
_rs.loader.exec_module(resolver)


def _team_root(explicit=None):
    """GL-1013 section 6: explicit, then CLAUDE_PROJECT_DIR when it holds the
    marker, then the walk up from this file."""
    try:
        return resolver.find_team_root(explicit=explicit, start=__file__).path
    except resolver.ResolveError as e:
        raise SystemExit("FAIL %s" % e)


# --root defaults to None: the resolver finds the team root (GL-1013 site table).
DEFAULT_ROOT = None

AGENTS_REL = "06 AI Team/Agents"
UNLOCK = "ICOR_UNLOCK_WRITES"
# Read by write-guard.py. One name, two scripts, and neither keeps a copy
# of the other's rule: the guard decides, this one only opens the door.
HIRING_MARKER = ".hiring"
NAME_RE = re.compile(r"^[A-Z][a-zA-Z]+$")
SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,23}$")

PRIVATE_CONTRACT = """---
agent_version: 1.0.0
agent_version_date: '{today}'
agent_status: active
agent_compatibility: tool-agnostic
owner: Nolan
bio: <One or two warm sentences for a human reader on the roster: what this member is like and what they are great at. Not a routing rule.>
routing_description: "{role}. Use proactively when <the cue patterns that route here>."
---

# {name} - {role}

You are {name}. <One sentence: the outcome this specialist exists to produce.>

## Identity

- **Name:** {name}
- **Role:** {role}
- **Reports to:** Larry (Orchestrator)
- **Operating principle:** <the one belief that decides the close calls>

## When Larry routes to {name}

| User input pattern | Why it routes here |
|---|---|
| <"the words Tom uses"> | <why this is {name}'s lane> |

## Method

<How this specialist works, in steps. Tag every step of a procedure that will
become an SOP `[SCRIPT]` or `[JUDGEMENT]` in the SOP, not here.>

## Deliverable structure

<What the output looks like, and where it lands.>

## Where {name} writes

<Paths and naming. Reference [[GL-001-file-naming-conventions]].>

## Scope boundaries

<What this specialist does not do, naming who owns the neighbouring work.>

## References

- [[GL-001-file-naming-conventions]]
- [[GL-002-frontmatter-conventions]]
- [[agent-index]]
"""

PUBLIC_CONTRACT = """---
type: agent
name: {name}
role: {role}
created: {today}
routing_description: "{role}. Launch for <what this agent is for, in one line>."
---

# {name} - {role}

## Mission
<One sentence: the outcome this agent exists to produce.>

## Owns
- <The work only this agent does.>

## Never
- <The work that belongs to somebody else, and who.>

## Works by
- <The SOPs, Workstreams and Guidelines it executes, as wikilinks.>
"""

BIO = """---
type: agent-bio
agent: {name}
role: {role}
created: {today}
---

# {name}

{avatar}

<One or two warm sentences: what this member is like and what they are great at.>

## What {name} does for you

- <A job you could hand over, in the words you would use.>

## When to call {name}

- <The moment it makes sense to ask.>

Contract: `06 AI Team/Agents/{name}/AGENT.md`
"""

JOURNAL_TEMPLATE = """---
agent_id: <self>
type: journal-entry
created: YYYY-MM-DDTHH:MM:SSZ
updated: YYYY-MM-DDTHH:MM:SSZ
topic: <topic-slug>
tags: []
linked_session_logs: []
related_journal_entries: []
status: durable
---

# {The insight in one sentence, which IS the title}

## Context
Two sentences at most. What happened that made me write this down.

## What I learned
The actual insight. Direct, no hedging. Caveats go under "When this does NOT apply".

## When this applies
Concrete trigger conditions.

## When this does NOT apply
Anti-applicability, so future me can skip past this entry when it does not fit.
"""

FIRST_ENTRY = """---
agent_id: {slug}
type: journal-entry
created: {today}T00:00:00Z
updated: {today}T00:00:00Z
topic: hired
tags: []
linked_session_logs: []
related_journal_entries: []
status: durable
---

# Hired as {role} on {today}

## Context
This folder's first entry, written by `new-agent.py` so the Journal is never
an empty folder. Version control drops an empty folder, and a specialist with
no journal reads as a specialist who has learned nothing.

## What I learned
Nothing yet. The next entry is the first real one.

## When this applies
Never. This entry exists to hold the folder open.

## When this does NOT apply
Everywhere else.
"""


def fail(msg):
    print("FAIL new-agent: " + msg, file=sys.stderr)
    return 1


def load_vault_is_public():
    """`vault_is_public` from check-hire.py beside this file, or None.

    Imported, never copied: two scripts holding two copies of one rule is the
    exact drift task tsk-2026-09-17-006 fixed.
    """
    ch = HERE / "check-hire.py"
    if not ch.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("check_hire_shape", str(ch))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "vault_is_public", None)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Create the scripted half of a hire.")
    ap.add_argument("name", help="the specialist's name, one Title-case word")
    ap.add_argument("--slug", required=True, help="dispatch key, lowercase, unique")
    ap.add_argument("--role", required=True, help="the role in one short line")
    ap.add_argument("--section", default=None,
                    help="agent-index section to add the row to (default: the first table)")
    ap.add_argument("--dry-run", action="store_true", dest="dry",
                    help="print what would be written, write nothing")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="vault root")
    args = ap.parse_args()

    root = _team_root(args.root)
    name, slug, role = args.name.strip(), args.slug.strip(), args.role.strip()
    today = date.today().isoformat()
    vault_is_public = load_vault_is_public()
    if vault_is_public is None:
        return fail("check-hire.py is not beside this script, or has no vault_is_public(). "
                    "That function is the one answer to which vault this is, and this "
                    "script does not guess. Restore check-hire.py in Scripts/ and re-run.")
    public = vault_is_public(root)
    agents = root / AGENTS_REL
    d = agents / name
    contract = d / "AGENT.md"

    if not agents.is_dir():
        return fail("%s has no `%s` folder, so it is not a vault root" % (root, AGENTS_REL))
    if not NAME_RE.match(name):
        return fail("`%s` is not a contract name. One Title-case word, letters only, no role "
                    "suffix: the folder is the name." % name)
    if not SLUG_RE.match(slug):
        return fail("`%s` is not a slug. Lowercase, starts with a letter, letters digits and "
                    "hyphens, 2 to 24 characters." % slug)
    if contract.is_file():
        return fail("%s/%s/AGENT.md already exists. A contract is never overwritten: edit it, or "
                    "retire the specialist first." % (AGENTS_REL, name))
    index = agents / "agent-index.md"
    if index.is_file():
        text, _eol = noteio.read_note(index)
        cells = re.findall(r"^\|[^|]+\|\s*([a-z0-9-]+)\s*\|", text, re.M)
        if slug in cells:
            return fail("the slug `%s` is already in agent-index.md. A slug is a dispatch key and "
                        "two agents cannot share one." % slug)

    # The hire opens the door, and the door is a file rather than an
    # environment variable. ICOR_UNLOCK_WRITES cannot be set on one tool call,
    # so telling the operator to export it routed both CLIs in pilot C into
    # `cat > AGENT.md` in a shell, which the write guard never sees. The
    # marker below is what write-guard.py honours: this agent's contract only,
    # for 24 hours, cleared by a green check-hire.py run.

    plan = []
    writes = []
    marker = d / HIRING_MARKER
    session_id = None
    try:
        session_id = json.loads(
            (root / ".icor-for-life" / "scripts" / "session.json")
            .read_text(encoding="utf-8")).get("session_id")
    except Exception:
        session_id = None
    plan.append("shape  %s (check-hire.py vault_is_public)"
                % ("public Scaffold" if public else "private vault, GL-025 skeleton"))
    plan.append("write  " + str(marker.relative_to(root)) + "  (the hiring marker: it "
                "opens this one contract to the write guard for 24 hours)")

    def plan_write(path, text):
        plan.append("write  " + str(Path(path).relative_to(root)))
        writes.append((Path(path), text))

    # 1 and 2. the folder and the contract
    if public and (agents / "Agent 01").is_dir():
        plan.append("render %s/%s/AGENT.md from the Agent 01 template" % (AGENTS_REL, name))
        template_contract = noteio.read_note(agents / "Agent 01" / "AGENT.md")[0]
        body = re.sub(r"^name: .*$", "name: " + name, template_contract, flags=re.M)
        body = re.sub(r"^role: .*$", "role: " + role, body, flags=re.M)
        body = re.sub(r"^created: .*$", "created: " + today, body, flags=re.M)
        body = re.sub(r"^myicor_id: .*\n", "", body, flags=re.M)
        body = body.replace("<Name>", name).replace("<Role in three words>", role)
        plan_write(contract, body)
    else:
        tpl = PUBLIC_CONTRACT if public else PRIVATE_CONTRACT
        plan_write(contract, tpl.format(name=name, role=role, today=today))

    # 4. the bio card
    if public:
        avatar_embed = "![[06 AI Team/AI Team Knowledge/Avatars/%s.png|240]]" % name.lower()
    else:
        avatar_embed = "![[06 AI Team/Agents/%s/avatar.png|240]]" % name
    plan.append("embed  " + avatar_embed + "  (in the bio card)")
    plan_write(d / (name + ".md"), BIO.format(name=name, role=role, today=today,
                                              avatar=avatar_embed))

    # 5. the journal
    #
    # The template is rendered from JOURNAL_TEMPLATE with this hire's own
    # slug in it. Until 2026-09-16 it was COPIED from the first sibling that
    # had one, `sorted(agents.glob(...))`, so every hire in the public
    # Scaffold was seeded with `agent_id: charta` and every journal entry
    # written from it claimed to be Charta's (Brian Carroll, B2-7). A
    # template carrying another agent's id is worse than no template: it
    # passes YAML, it passes the eye, and it mislabels the entry.
    #
    # `.replace`, never `.format`: the template body carries literal braces
    # (`# {The insight in one sentence, which IS the title}`) and `.format`
    # would raise KeyError on them.
    plan_write(d / "Journal" / "_template.md",
               JOURNAL_TEMPLATE.replace("<self>", slug))
    plan_write(d / "Journal" / ("%s-%s-hired.md" % (today, slug)),
               FIRST_ENTRY.format(slug=slug, role=role, today=today))

    # 6. the agent-index row
    row = None
    index_eol = "\n"
    if index.is_file():
        # agent-index.md is a file the member reads and edits. The row is
        # inserted in the file's OWN line ending so the rest of the table is
        # not rewritten under it (Ian Slattery, T15-A).
        text, index_eol = noteio.read_note(index)
        header_re = re.compile(r"^\|[^\n]*\|\s*\n\|[\s:|-]+\|\s*$", re.M)
        target = None
        if args.section:
            m = re.search(r"\n## %s\b" % re.escape(args.section), text)
            if not m:
                return fail("agent-index.md has no section named `%s`" % args.section)
            search_from = m.end()
        else:
            search_from = 0
        hm = header_re.search(text, search_from)
        if hm:
            cols = len([c for c in text[hm.start():hm.end()].splitlines()[0].strip()
                        .strip("|").split("|")])
            if cols >= 4:
                row = "| [[%s]] | %s | %s | <the user inputs that route here> |" % (name, slug, role)
            else:
                row = "| [[%s]] | %s | <the user inputs that route here> |" % (name, role)
            target = hm.end()
            plan.append("insert the agent-index row into the table at line %d"
                        % (text[:target].count("\n") + 1))
        if row and target is not None:
            new_text = text[:target] + index_eol + row + text[target:]
            writes.append((index, new_text))

    if args.dry:
        print("dry run, nothing written:")
        for line in plan:
            print("  " + line)
        print("\nOK new-agent: %d file(s) would be written or changed" % len(writes))
        return 0

    marker.parent.mkdir(parents=True, exist_ok=True)
    noteio.write_note(marker, json.dumps({
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": name,
        "session_id": session_id,
        "why": ("write-guard.py stands down on this one AGENT.md while this file "
                "is here and younger than 24 hours; check-hire.py deletes it on a "
                "green run"),
    }, indent=2) + "\n")
    print("wrote  " + str(marker.relative_to(root))
          + "  (hiring marker, 24h, this contract only)")

    for path, text in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        noteio.write_note(path, text)
        print("wrote  " + str(path.relative_to(root)))

    # 3. the id, minted by the one script that owns ids
    mint = HERE / "mint-agent-ids.py"
    if mint.is_file():
        r = subprocess.run([sys.executable, str(mint), "--root", str(root)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL new-agent: mint-agent-ids.py could not mint the id: %s"
                  % (r.stderr or r.stdout).strip(), file=sys.stderr)
            return 1
        print("minted myicor_id through mint-agent-ids.py")
    else:
        print("WARN new-agent: mint-agent-ids.py is not in Scripts/. Mint by hand: "
              "`uuidgen | tr A-Z a-z`, then write it as the first frontmatter field.")

    print("\nOK new-agent: %s is scaffolded. What is left is judgement, in this order:" % name)
    print("  1. Fill %s/%s/AGENT.md: identity, cues, method, boundaries, and the words of "
          "`bio` and `routing_description`." % (AGENTS_REL, name))
    print("  2. Fill %s/%s/%s.md, the user-facing card." % (AGENTS_REL, name, name))
    # Public text only (C1 G4): until 6.0.2 these two lines named documents
    # and a cheatsheet that exist in one private vault and in no member's.
    print("  3. Make the avatar (SOP-1007 row 5): an image-generating specialist if the "
          "team has one, else a placeholder, saved where that row says.")
    print("  4. Announce the generator run so the shim and any skill are rendered from the "
          "frontmatter. Never type a shim by hand.")
    print("  5. Finish the agent-index row (SOP-1007 row 12).")
    print("  6. Run `check-hire.py %s`. It must exit 0 before the hire is announced, "
          "and a green run deletes the hiring marker." % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
