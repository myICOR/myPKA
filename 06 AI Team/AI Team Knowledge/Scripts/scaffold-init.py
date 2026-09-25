#!/usr/bin/env python3
"""scaffold-init.py: generate the harness layer from the vault's own frontmatter.

Mack, 2026-09-14. Row 2 of the 2026-09-14 skills-and-hooks audit
(the 2026-09-14 scaffold skills and hooks audit report, section 6.1), under
Tom decisions k3p (the skill is a pointer, the SOP is the body), w6r (the
generator writes every SKILL.md into the canonical home) and m9w2d (ship it in
the public Scaffold too, with a house cap that fails red).

    SOPs, Workstreams, Guidelines and agent contracts are the only bodies of
    knowledge. Everything a host reads above them is a thin adapter, and a
    person never writes one again.

WHAT IT BUILDS, AND FROM WHAT

    skills        SOP / Workstream frontmatter (skill_name, skill_summary,
                  skill_triggers, skill_prerun)
                  -> `06 AI Team/AI Team Knowledge/Skills/<name>/SKILL.md`
                     the canonical, portable file: THE one body, rendered once
                  -> `.agents/skills/<name>`           link to the canonical
                     folder, the universal path read by Codex, Gemini,
                     Cursor and Copilot (decision v8d, 2026-09-24)
                  -> `.claude/skills/<name>/SKILL.md`  thin adapter, only
                     because Claude Code does not read `.agents/skills/`
                     (R18, re-verified by Pax 7a on 2026-09-24). It differs
                     from the canonical file ONLY in its frontmatter and in
                     the injected `!` prerun line; the body is byte-identical
                     and skill-doctor.py fails red when it is not.

    shims         `06 AI Team/Agents/<Name>/AGENT.md` frontmatter
                  (routing_description, shim_reads, tools, model)
                  -> `.claude/agents/<slug>.md`   Markdown + YAML
                  -> `.codex/agents/<slug>.toml`  TOML, developer_instructions
                  -> `.gemini/agents/<slug>.md`   Markdown + YAML
                  Cursor reads `.claude/agents/`, so it gets no file.

    hooks         `06 AI Team/AI Team Knowledge/Scripts/hooks-rules.json`
                  -> `.claude/settings.json`   the `hooks` key only
                  -> `.codex/hooks.json`
                  Cursor loads Claude Code's hooks; Gemini CLI has none.

    pointers      -> `.gemini/settings.json` (`context.fileName` names
                     `AGENTS.md`), `.codex/config.toml`, written only when
                     absent. No `CLAUDE.md` and no `GEMINI.md` is written:
                     `AGENTS.md` is the only entry file (Tom, 2026-09-24).

THE FOUR VERBS

    plan     print every file it would create, update or remove. Writes nothing.
    apply    write them.
    check    exit 1 if a second apply would change anything, or if any
             generated file was hand-edited (the content hash in its header).
    doctor   per host: detected, installed, trusted, tested, unsupported.

WHAT A GREEN RUN DOES NOT PROVE (GL-081 shape, GL-1005 rule 4)

1. **It does not prove a host reads any of it.** Every path here comes from a
   vendor doc, and a doc is a claim about a version. `doctor` reports whether a
   host is even installed; nothing here watches a host load a file.
2. **It does not prove a hook fires.** `.claude/settings.json` and
   `.codex/hooks.json` are configuration. Whether the host invokes a guard on a
   matching tool call is a property of the host and of its trust state, which is
   not readable from disk on any of the three. `run-red-tests.py` proves the
   guard scripts refuse bad input when they are called, which is a different
   fact.
3. **A skill that generates is not a skill that gets selected.** Selection is
   the host's judgement over the description text. Nothing here measures it.
4. **The content hash proves the bytes, not the meaning.** A generated file that
   still hashes clean can be pointing at an SOP that has since been rewritten
   underneath it; the hash covers this file, not its source.

WHY THE HEADER CARRIES NO DATE
    A date in the header changes the file every day, so the second apply of the
    day would be a rewrite and `check` would fail for a reason that has nothing
    to do with the content. Source path plus content hash, and nothing else.

WHY THE SKILL NAME IS A FIELD AND NOT A DERIVATION
    A slug built from the title breaks every host link the first time the title
    is reworded, with no error anywhere. `skill_name` is required the moment
    `skill_triggers` is non-empty; a procedure with triggers and no name is
    refused rather than guessed at (GL-002 / GL-1002, 2026-09-14).
"""

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
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
# under `-I` with its own folder dropped from it. A missing noteio.py is a
# half-upgraded
# Scripts/ folder and says so in one line, because a traceback out of an
# import teaches the member nothing about what to do next.
_nio_path = Path(__file__).resolve().parent / "noteio.py"
if not _nio_path.is_file():
    raise SystemExit("FAIL noteio.py is missing from %s. Scripts/ is half "
                     "upgraded; restore noteio.py beside this script and run "
                     "this again." % _nio_path.parent)
_nio = importlib.util.spec_from_file_location("noteio", _nio_path)
noteio = importlib.util.module_from_spec(_nio)
_nio.loader.exec_module(noteio)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# HOUSE BUDGET, NOT A VENDOR LIMIT. The "about 35 skills, 2 percent of context"
# figure that circulated on 2026-09-13 is not in any current Codex or Claude
# doc; the 2026-09-14 audit checked and could not find it (report section 4.3).
# What IS documented: loaded Claude skills share a 25,000 token budget and
# descriptions are cut at 1,536 characters. This number is ours, chosen for
# startup cost and for how many names a person can scan, and it fails red so
# that growth is a decision somebody makes rather than a drift nobody sees.
MAX_SKILL_TOKENS = 4000

GEN_MARK = "GENERATED by scaffold-init.py"
NIL_UUID = "00000000-0000-0000-0000-000000000000"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Gemini CLI has no hook system of any kind (Pax portability brief, 2026-09-14,
# verified against geminicli.com's own docs). Cursor reads Claude Code's hooks
# and Claude Code's agents for compatibility, so it gets no file of its own.
HOSTS = ("claude-code", "codex", "gemini", "cursor")


# ---------------------------------------------------------------------------
# Vault root: walked, never asked of git
# ---------------------------------------------------------------------------

_RS_SI = []


def _resolver():
    """resolve.py, loaded once by path from beside this script."""
    if _RS_SI:
        return _RS_SI[0]
    rs = HERE_SI / "resolve.py"
    if not rs.is_file():
        raise SystemExit("FAIL resolve.py is missing from %s. Scripts/ is half "
                         "upgraded; restore resolve.py beside this script." % HERE_SI)
    spec = importlib.util.spec_from_file_location("mypka_resolve_si", rs)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _RS_SI.append(mod)
    return mod


def find_root(start=None):
    """Walk up until a folder holds AGENTS.md and `06 AI Team/Agents/`.

    Delegates to resolve.py's find_team_root (GL-1013 section 6, site (a)),
    the one code that knows the team-root marker. The walk only: env={} keeps
    this generator's old contract, where CLAUDE_PROJECT_DIR never picked the
    tree it renders.

    Never `git rev-parse`: this private vault left git on 2026-09-09 and a
    member's vault is a plain folder. A root found by git is a root that does
    not exist for most of the people this runs for.
    """
    here = Path(start or __file__).resolve()
    mod = _resolver()
    try:
        return mod.find_team_root(start=here, env={}).path
    except mod.ResolveError:
        raise SystemExit("FAIL no vault root above %s (looked for AGENTS.md next to "
                         "'06 AI Team/Agents/')" % here)


HERE_SI = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Frontmatter: a small reader, stdlib only
# ---------------------------------------------------------------------------
# PyYAML is not installed on every python3 this runs under. check-bases.py
# imported it until 2026-09-14 and two gates reported a FAILED GUARD when the
# guard had never run (tsk-2026-09-11-005). This reader handles the shapes the
# vault actually uses and nothing else: plain scalars, single and double quoted
# scalars that may run over several lines, block scalars, and lists of strings.

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")
_ITEM = re.compile(r"^\s+-\s+(.*)$")


def _scan_quoted(s, q):
    """s[0] is the opening quote. Return (value, True) or (None, False)."""
    out = []
    i = 1
    while i < len(s):
        c = s[i]
        if c == q:
            if q == "'" and i + 1 < len(s) and s[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), True
        if q == '"' and c == "\\" and i + 1 < len(s):
            out.append(s[i + 1])
            i += 2
            continue
        out.append(c)
        i += 1
    return None, False


def _scalar(raw):
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] in "'\"":
        v, ok = _scan_quoted(raw, raw[0])
        if ok:
            return v
    # unquoted: a # only starts a comment when it follows whitespace
    m = re.search(r"\s#", raw)
    if m:
        raw = raw[:m.start()]
    return raw.strip().strip('"').strip("'")


def parse_front(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    block = []
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        block.append(lines[i])
    else:
        return {}
    out = {}
    i, n = 0, len(block)
    while i < n:
        m = _KEY.match(block[i])
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest in (">", ">-", ">+", "|", "|-", "|+"):
            chunk, j = [], i + 1
            while j < n and (not block[j].strip() or block[j][:1] in (" ", "\t")):
                chunk.append(block[j].strip())
                j += 1
            out[key] = " ".join(c for c in chunk if c).strip()
            i = j
            continue
        if rest == "":
            items, j = [], i + 1
            while j < n:
                mi = _ITEM.match(block[j])
                if not mi:
                    break
                items.append(_scalar(mi.group(1)))
                j += 1
            out[key] = items if items else ""
            i = j if items else i + 1
            continue
        if rest[0] in "'\"":
            q, buf, j = rest[0], rest, i
            v, ok = _scan_quoted(buf, q)
            while not ok and j + 1 < n:
                j += 1
                buf = buf + "\n" + block[j]
                v, ok = _scan_quoted(buf, q)
            out[key] = v if ok else _scalar(rest)
            i = (j + 1) if ok else (i + 1)
            continue
        out[key] = _scalar(rest)
        i += 1
    return out


# ---------------------------------------------------------------------------
# The generated header
# ---------------------------------------------------------------------------

def _hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def md_header(source, body):
    return ("<!-- %s from `%s`. content-hash:%s. Do not hand-edit: change the "
            "source and re-run the generator. -->" % (GEN_MARK, source, _hash(body)))


def toml_header(source, body):
    # One line, on purpose: strip_header() below drops every line carrying the
    # marker, so a two-line header would leave its second line inside the hash
    # at check time and outside it at write time. The two would never agree and
    # every file would report as hand-edited.
    return ("# %s from `%s`. content-hash:%s. Do not hand-edit: change the "
            "source and re-run the generator." % (GEN_MARK, source, _hash(body)))


def header_line_of(text):
    for line in text.split("\n"):
        if GEN_MARK in line:
            return line
    return None


def strip_header(text):
    """The file minus its header line, which is what the hash covers."""
    keep = [ln for ln in text.split("\n") if GEN_MARK not in ln]
    return "\n".join(keep)


def hand_edited(path):
    """True when a generated file's body no longer matches the hash it carries.

    Returns None when the file carries no header at all, which means the
    generator does not own it and must not touch it.

    JSON is its own case: the header lives in a VALUE, not on a line of its own,
    so dropping the line that carries it would leave the file unparseable and
    the hash would be taken over something that never existed. The first draft
    of this function did exactly that and reported nine freshly written files as
    hand-edited, which is how the split came to be here.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if path.suffix == ".json":
        return codex_hooks_hand_edited(text)
    line = header_line_of(text)
    if line is None:
        return None
    m = re.search(r"content-hash:([0-9a-f]{12})", line)
    if not m:
        return True
    return _hash(strip_header(text)) != m.group(1)


# ---------------------------------------------------------------------------
# Reading the vault
# ---------------------------------------------------------------------------

def tk(root):
    return root / "06 AI Team" / "AI Team Knowledge"


def read_procedures(root):
    """Every SOP and Workstream that declares itself skill-eligible.

    Returns (skills, problems). A procedure with triggers and no `skill_name`
    is a problem, never a guess: the name is the thing a user types and a host
    matches on, and a derived one breaks silently the day the title changes.
    """
    skills, problems = [], []
    seen = {}
    for folder in ("SOPs", "Workstreams"):
        d = tk(root) / folder
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*.md")):
            if f.name.startswith("_"):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            fm = parse_front(text)
            trig = fm.get("skill_triggers") or []
            if not isinstance(trig, list) or not trig:
                continue
            rel = f.relative_to(root).as_posix()
            name = (fm.get("skill_name") or "").strip()
            if not name:
                problems.append("%s: skill_triggers is non-empty and skill_name "
                                "is missing (GL-002 / GL-1002, 2026-09-14)" % rel)
                continue
            if not SKILL_NAME_RE.match(name):
                problems.append("%s: skill_name %r is not a slug "
                                "(lowercase letters, digits, hyphens)" % (rel, name))
                continue
            if name in seen:
                problems.append("%s: skill_name %r is already taken by %s"
                                % (rel, name, seen[name]))
                continue
            summary = (fm.get("skill_summary") or "").strip()
            if not summary:
                problems.append("%s: skill_triggers is non-empty and "
                                "skill_summary is missing" % rel)
                continue
            prerun = (fm.get("skill_prerun") or "").strip()
            if prerun:
                bad = prerun_problem(prerun)
                if bad:
                    problems.append("%s: skill_prerun refused, %s. The prerun is "
                                    "rendered into `.claude/skills/<name>/SKILL.md` as a "
                                    "shell line the host RUNS, so it is an allowlist, not "
                                    "a string: `<python3|sh|bash|node> \"06 AI Team/AI Team "
                                    "Knowledge/Scripts/<file>\" [plain args]` and nothing "
                                    "else (Vex gate 2026-09-14)." % (rel, bad))
                    continue
            seen[name] = rel
            owner = str(fm.get("owner") or "").strip()
            owner = re.split(r"[\s(]", owner)[0] if owner else ""
            skills.append({
                "name": name,
                "summary": summary,
                "triggers": [t for t in trig if t],
                "prerun": (fm.get("skill_prerun") or "").strip(),
                "source": rel,
                "owner": owner[:1].upper() + owner[1:] if owner else "",
                "title": (fm.get("title") or "").strip(),
                "body": text,
            })
    return skills, problems


def read_contracts(root):
    """Every agent contract that earns a shim, and every contract refused.

    Three exclusions, each for its own reason: a folder with no AGENT.md is not
    a contract; a contract with no routing_description is the orchestrator, who
    is the session's own identity and is never dispatched (GL-025 exempts
    Larry); a contract still on the nil placeholder id is the hire template.

    Returns (contracts, problems). A contract whose `tools`, `model` or
    `shim_reads` would not survive the render is a PROBLEM and is dropped, so
    `apply` writes no shim for it at all (Vex gate 2026-09-14, V-04).
    """
    out, problems = [], []
    d = root / "06 AI Team" / "Agents"
    if not d.is_dir():
        return out, problems
    for folder in sorted(p for p in d.iterdir() if p.is_dir()):
        f = folder / "AGENT.md"
        if not f.is_file():
            continue
        fm = parse_front(f.read_text(encoding="utf-8"))
        rd = (fm.get("routing_description") or "").strip()
        if not rd:
            continue
        if (fm.get("myicor_id") or "").strip() == NIL_UUID:
            continue
        reads = fm.get("shim_reads") or []
        if not isinstance(reads, list):
            reads = []
        tools = fm.get("tools") or ""
        if isinstance(tools, list):
            tools = ", ".join(tools)
        c = {
            "name": folder.name,
            "slug": folder.name.lower().replace(" ", "-"),
            "rd": rd,
            "reads": [r for r in reads if r],
            "tools": str(tools).strip(),
            "model": str(fm.get("model") or "").strip(),
            "contract": f.relative_to(root).as_posix(),
        }
        bad = contract_problem(c)
        if bad:
            problems.append(bad)
            continue
        out.append(c)
    return out, problems


def read_rules(root):
    p = tk(root) / "Scripts" / "hooks-rules.json"
    if not p.is_file():
        return None, "no hooks-rules.json at %s" % p.relative_to(root).as_posix()
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except ValueError as e:
        return None, "hooks-rules.json does not parse: %s" % e


# ---------------------------------------------------------------------------
# Rendering: skills
# ---------------------------------------------------------------------------

# The extension must END the name (Vera step 15, F6): without the lookahead,
# `Scripts/hooks-rules.json` matched as `Scripts/hooks-rules.js` and the skill
# listed a script that does not exist. A trailing `.` or `)` still ends it.
SCRIPT_RE = re.compile(
    r"(?:06 AI Team/AI Team Knowledge/)?Scripts/[A-Za-z0-9_./-]+\.(?:py|sh|mjs|js)(?![A-Za-z0-9_])")


def script_calls(sop_text, limit=8):
    seen, out = set(), []
    for m in SCRIPT_RE.finditer(sop_text):
        s = m.group(0)
        if not s.startswith("06 AI Team/"):
            s = "06 AI Team/AI Team Knowledge/" + s
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


INTERPRETERS = {".py": "python3", ".sh": "sh", ".mjs": "node", ".js": "node"}


def normalise_prerun(cmd):
    """A prerun the SOP wrote as a bare path becomes a runnable command.

    GL-002 and GL-1002 both say the field is a full invocation with its
    arguments, and most are. One was not (`Scripts/checkpoint.py`), and a
    skill that injects a bare path injects a line the shell cannot run. This
    repairs the shape rather than letting the skill ship broken; a prerun that
    already names an interpreter is left exactly as written.
    """
    c = cmd.strip()
    if not c or c.split()[0] in ("python3", "python", "sh", "bash", "node"):
        return c
    m = re.match(r'^"?((?:06 AI Team/AI Team Knowledge/)?Scripts/[^"\s]+)"?(.*)$', c)
    if not m:
        return c
    path, rest = m.group(1), m.group(2)
    if not path.startswith("06 AI Team/"):
        path = "06 AI Team/AI Team Knowledge/" + path
    interp = INTERPRETERS.get(Path(path).suffix, "python3")
    return '%s "%s"%s' % (interp, path, rest)


# THE PRERUN ALLOWLIST (Vex security gate, 2026-09-14)
#
# `skill_prerun` is copied out of SOP / Workstream frontmatter into the Claude
# adapter as a `!`...`` line, and the host executes that line in the user's
# shell the moment the skill is invoked. Frontmatter on an SOP is writable by
# any agent through the ordinary Write tool (the write guard protects
# contracts and entry files, not procedures), and SOP-1012 imports procedures
# from outside the vault. So the field is an execution surface, and a string
# copied verbatim from it is remote code execution one Write away. Measured
# before this block existed: `bash -c 'id'`, a `; id` suffix, a `$(id)`
# argument and a `Scripts/../../..` path all rendered unchanged.
#
# What passes: one interpreter from INTERPRETERS' values, one double-quoted
# script path under `06 AI Team/AI Team Knowledge/Scripts/` with no `..`
# segment, then zero or more plain arguments (letters, digits, and _ = . , : @
# % + -). No quotes, no `$`, no backticks, no `;`, `|`, `&`, `<`, `>`, `(`, `)`,
# no newline. A prerun that needs any of those is a prerun whose first step
# belongs inside a script in Scripts/, where the red-test runner can see it.

_PRERUN_RE = re.compile(
    r'^(?:python3|python|sh|bash|node) '
    r'"(06 AI Team/AI Team Knowledge/Scripts/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+'
    r'\.(?:py|sh|mjs|js))"'
    r'((?: [A-Za-z0-9_=.,:@%+-]+)*)$')


def prerun_problem(cmd):
    """None when `cmd` (after normalise_prerun) is on the allowlist, else why not."""
    c = normalise_prerun(cmd)
    if "\n" in c or "\r" in c:
        return "it spans more than one line"
    m = _PRERUN_RE.match(c)
    if not m:
        return ("`%s` is not `<interpreter> \"06 AI Team/AI Team Knowledge/Scripts/"
                "<file>\" [plain args]`; shell metacharacters, quotes, `$`, and "
                "paths outside Scripts/ are refused" % c[:120])
    if ".." in m.group(1).split("/"):
        return "the script path `%s` climbs out of Scripts/ with `..`" % m.group(1)
    return None


# ---------------------------------------------------------------------------
# Contract frontmatter is rendered into host CONFIG, not into prose (V-04)
# ---------------------------------------------------------------------------
# `tools:` and `model:` are copied straight into the YAML frontmatter of
# `.claude/agents/<slug>.md`, and `shim_reads` items land inside a TOML `"""`
# basic string in the Codex shim. Claude Code subagent frontmatter honours
# `hooks`, `permissionMode` and `mcpServers`, so a `tools:` value that is really
# a multi-line YAML scalar can hand a subagent a shell hook. A `"""` or a
# backslash in a `shim_reads` entry ends or escapes the TOML string.
#
# So all three are validated at the source, before the render, and a bad value
# is a PROBLEM: `apply` writes nothing at all, `plan` and `doctor` print it.
#
# The tool names come from check-hire.py's TOOL_ALLOWLIST rather than a second
# copy here. Check 11 of that script already refuses a name no host knows, and
# two lists would disagree the day either one gains a tool.

_MODELS = ("opus", "sonnet", "haiku", "fable", "inherit")
_MCP_TOOL_RE = re.compile(r"^mcp__[\w.-]+__[\w.*-]+$")
_TOOL_ALLOWLIST_CACHE = []


def tool_allowlist():
    """check-hire.py's TOOL_ALLOWLIST, imported once from the script beside us.

    An empty set is returned when the import fails, and the caller turns that
    into a PROBLEM rather than into a silent pass: a validator that cannot read
    its own list must not report that everything is legal.
    """
    if _TOOL_ALLOWLIST_CACHE:
        return _TOOL_ALLOWLIST_CACHE[0]
    names = set()
    try:
        import importlib.util
        src = Path(__file__).resolve().parent / "check-hire.py"
        spec = importlib.util.spec_from_file_location("_check_hire_tools", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        names = set(getattr(mod, "TOOL_ALLOWLIST", ()) or ())
    except Exception:
        names = set()
    _TOOL_ALLOWLIST_CACHE.append(names)
    return names


def contract_problem(c):
    """None when the contract's host-config fields are safe to render, else why not."""
    rel = c["contract"]
    tools = c["tools"]
    if tools:
        if "\n" in tools or "\r" in tools:
            return ("%s: `tools` spans more than one line, so what reaches the shim "
                    "is not a tool list but arbitrary YAML; Claude Code subagent "
                    "frontmatter honours `hooks`, `permissionMode` and `mcpServers` "
                    "(Vex gate 2026-09-14, V-04)" % rel)
        allow = tool_allowlist()
        if not allow:
            return ("%s: `tools` is set but check-hire.py's TOOL_ALLOWLIST could not "
                    "be imported, so the names cannot be checked; refusing rather "
                    "than passing an unchecked value into host config" % rel)
        bad = [t.strip() for t in tools.split(",") if t.strip()
               and t.strip() not in allow and not _MCP_TOOL_RE.match(t.strip())]
        if bad:
            return ("%s: `tools` names %s, which is on no host's tool list and on no "
                    "`mcp__<server>__<tool>` shape; a name a host does not know is "
                    "dropped silently, and a value that is not a name at all is "
                    "frontmatter injection" % (rel, ", ".join(repr(x)[:40] for x in bad[:3])))
    model = c["model"]
    if model and model not in _MODELS:
        return ("%s: `model` is %r; the shim may only name one of %s"
                % (rel, model[:60], ", ".join(_MODELS)))
    for r in c["reads"]:
        if not isinstance(r, str):
            return "%s: a `shim_reads` entry is not a string" % rel
        if '"""' in r or "\\" in r or "\n" in r or "\r" in r:
            return ("%s: `shim_reads` entry %r carries a `\"\"\"`, a backslash or a "
                    "newline, each of which ends or escapes the TOML basic string it "
                    "is rendered into in the Codex shim" % (rel, r[:60]))
    return None


def description_for(sk):
    trig = ", ".join('"%s"' % t for t in sk["triggers"])
    return "%s. Use when the user says: %s." % (sk["summary"].rstrip(". "), trig)


# THE UNIVERSAL SKILL SHAPE (step 7b of the myPKA split plan, decision v8d)
#
# One body, rendered once, read by every host. The body is host-neutral
# (plan section 8.3): it never names a host tool, a host variable, a hook or a
# host's dispatch verb. It says "your shell tool", "the folder that holds
# `AGENTS.md`" and "hand this to the specialist". A prerun skill carries one
# neutral sentence telling the model to run the command itself unless its
# output is already below; on Claude Code the output IS below (the adapter
# injects exactly one `!` line after that sentence), on every other host the
# model runs it. That injected line, and the frontmatter, are the ONLY two
# things the Claude adapter may add. skill-doctor.py check 9 asserts it.
#
# `disable-model-invocation` sits in the canonical frontmatter too: Pax 7a
# (2026-09-24) measured that Codex and Gemini ignore unknown keys and Cursor
# honours this one. Codex does not honour it, so the body also carries the
# plain sentence "Run this only when the user asks for it by name."

ONLY_BY_NAME = "Run this only when the user asks for it by name."


def prerun_sentence(sk):
    """The host-neutral prerun sentence the canonical body carries."""
    return ("Run `%s` with your shell tool, from the folder that holds "
            "`AGENTS.md`, before step 1, unless its output is already below. "
            "Read that output; do not run it twice." % normalise_prerun(sk["prerun"]))


def claude_prerun_line(sk):
    """The one line the Claude adapter injects after the prerun sentence."""
    # ${CLAUDE_PROJECT_DIR}, WITH the braces, because a skill runs from
    # wherever the session's shell happens to be and a vault-relative path
    # resolves against that.
    #
    # The braces are the whole fix (pilot B finding F2). Claude Code
    # SUBSTITUTES `${CLAUDE_PROJECT_DIR}` into a skill's markdown before
    # the shell ever sees it; it does not export it into the prerun's
    # environment. The unbraced `$CLAUDE_PROJECT_DIR` is therefore not
    # substituted, reaches the shell as an ordinary variable, expands to
    # EMPTY, and the command becomes `python3 "/06 AI Team/..."`. Claude
    # Code then aborts the whole invocation on the failed prerun, so
    # `/checkpoint` returned in 177 ms with 0 turns and the model never
    # read the skill at all. The variable resolves fine in hooks, which is
    # what made this look like a working pattern.
    cmd = normalise_prerun(sk["prerun"])
    cmd = cmd.replace('"06 AI Team/', '"${CLAUDE_PROJECT_DIR}/06 AI Team/')
    if "CLAUDE_PROJECT_DIR" not in cmd:
        cmd = re.sub(r"(^|\s)(06 AI Team/)", r"\1${CLAUDE_PROJECT_DIR}/\2", cmd)
    return "!`%s`" % cmd


def skill_body(sk, root, dispatchable=(), inject=None):
    """The one body. `inject` is the Claude adapter's `!` line, or None.

    Nothing else may differ between hosts: the canonical file and the Claude
    adapter call this with the same arguments except `inject`.
    """
    who = sk["owner"] or "the owning specialist"
    lines = []
    lines.append("")
    slug = (sk["owner"] or "").lower()
    if slug and slug in dispatchable:
        lines.append("You are %s. If you are the orchestrator, hand this to the "
                     "specialist `%s`; if you are already %s, act directly."
                     % (who, slug, who))
    else:
        # No shim for this owner: either the orchestrator, who is the session's
        # own identity and is never dispatched, or a name with no contract.
        lines.append("You are %s." % who)
    if sk["prerun"]:
        lines.append("")
        lines.append(ONLY_BY_NAME)
    lines.append("")
    lines.append("Read `%s` now and follow it exactly. That file is the "
                 "procedure; this file is the door." % sk["source"])
    if sk["prerun"]:
        lines.append("")
        lines.append(prerun_sentence(sk))
        if inject:
            lines.append("")
            lines.append(inject)
    calls = script_calls(sk["body"])
    if calls:
        lines.append("")
        lines.append("Script calls the procedure names, by path:")
        for c in calls:
            lines.append("- `%s`" % c)
    lines.append("")
    lines.append("Resources (open only when a step names them):")
    if sk["owner"] and (root / "06 AI Team" / "Agents" / sk["owner"] / "AGENT.md").is_file():
        lines.append("- `06 AI Team/Agents/%s/AGENT.md`" % sk["owner"])
    lines.append("- `%s`" % sk["source"])
    lines.append("")
    lines.append("Return the completion evidence the procedure's last step "
                 "names, and nothing it does not.")
    lines.append("")
    return lines


def render_canonical_skill(sk, root, dispatchable=()):
    """The universal file: name, description, the one body.

    Read by Codex, Gemini, Cursor and Copilot through `.agents/skills/<name>`.
    The only extra key is `disable-model-invocation` on a prerun skill, which
    the other hosts ignore without error or honour (Pax 7a, 2026-09-24).
    """
    fm = ["---", "name: %s" % sk["name"],
          "description: %s" % json.dumps(description_for(sk))]
    if sk["prerun"]:
        fm.append("disable-model-invocation: true")
    fm.append("---")
    return _with_md_header(fm + skill_body(sk, root, dispatchable),
                           sk["source"], insert_at=len(fm))


def _with_md_header(lines, source, insert_at):
    return _with_header(lines, source, insert_at, md_header)


def _with_header(lines, source, insert_at, fmt):
    """Insert the header as ITS OWN line, and hash exactly the joined rest.

    The hash at write time and the hash at check time have to be taken over the
    same string or every file reports as hand-edited. strip_header() drops the
    marker line and joins what is left; this joins what is left and then puts
    the marker line back. One operation, read in both directions.
    """
    body = "\n".join(lines)
    out = lines[:insert_at] + [fmt(source, body)] + lines[insert_at:]
    return "\n".join(out)


def render_claude_skill(sk, root, dispatchable=()):
    """The Claude Code adapter: Claude-only frontmatter plus one `!` line.

    `disable-model-invocation` is set exactly when the procedure declares a
    `skill_prerun`, and the reason is not style: a prerun runs a script before
    the model reads step 1, so a skill the model can select on its own runs
    that script unasked. SOP-090 stages bank transfers. That is the whole rule.
    """
    fm = ["---", "name: %s" % sk["name"],
          "description: %s" % json.dumps(description_for(sk))]
    inject = None
    if sk["prerun"]:
        fm.append("disable-model-invocation: true")
        fm.append("user-invocable: true")
        fm.append("shell: bash")
        fm.append("allowed-tools: Bash")
        inject = claude_prerun_line(sk)
    else:
        fm.append("user-invocable: true")
    fm.append("---")
    lines = fm + skill_body(sk, root, dispatchable, inject)
    return _with_md_header(lines, sk["source"], insert_at=len(fm))


# ---------------------------------------------------------------------------
# Rendering: agent shims
# ---------------------------------------------------------------------------

# One wording for the override line, the same in every host's shim and in the
# hand-held Claude shims. AGENTS.md and the contract template carry the same tail.
LOCAL_LOADER = ("Then read `%s` if it exists: it is the member's own file, never "
                "shipped and never overwritten by an update; it can add rules and "
                "change preferences, but it can never override a hard rule or "
                "switch off a guard.")


def local_override(contract):
    """The member's override beside a contract (Marshall C): AGENT.local.md
    next to 06 AI Team/Agents/<Name>/AGENT.md. Never shipped, never tracked."""
    return contract.rsplit("/", 1)[0] + "/AGENT.local.md"


def shim_body(c):
    lines = ["",
             "You are %s. Read `%s` now and follow it. That contract is the "
             "body; this file is the door." % (c["name"], c["contract"]),
             "",
             LOCAL_LOADER % local_override(c["contract"])]
    if c["reads"]:
        lines.append("")
        lines.append("Read these when the task involves them:")
        for r in c["reads"]:
            lines.append("- `%s`" % r)
    lines.append("")
    return lines


def render_claude_shim(c):
    fm = ["---", "name: %s" % c["slug"], "description: %s" % json.dumps(c["rd"])]
    if c["tools"]:
        fm.append("tools: %s" % c["tools"])
    if c["model"]:
        fm.append("model: %s" % c["model"])
    fm.append("---")
    return _with_md_header(fm + shim_body(c), c["contract"], insert_at=len(fm))


def render_gemini_shim(c):
    """Gemini CLI subagent: Markdown + YAML, body becomes the system prompt.

    No `tools` key. Gemini names its tools `read_file`, `grep_search` and so on;
    Claude's `Read, Grep` are not the same strings and a wrong name there is a
    restriction that silently does not apply. The contract's `tools` line is
    Claude vocabulary and stays in the Claude shim. Named here so the omission
    reads as a decision rather than an oversight.
    """
    fm = ["---", "name: %s" % c["slug"], "description: %s" % json.dumps(c["rd"]),
          "kind: local", "---"]
    return _with_md_header(fm + shim_body(c), c["contract"], insert_at=len(fm))


def render_codex_shim(c):
    """Codex CLI subagent: TOML. The prompt lives in `developer_instructions`.

    Verified 2026-09-14 against learn.chatgpt.com/docs/agent-configuration/
    subagents: name, description and developer_instructions are the required
    keys; `tools` is not among them (Codex scopes with sandbox_mode instead),
    so the contract's Claude tool list is not written here either.
    """
    body = "\n".join(x for x in shim_body(c) if x is not None).strip()
    lines = ['name = %s' % json.dumps(c["slug"]),
             'description = %s' % json.dumps(c["rd"]),
             'developer_instructions = """',
             body,
             '"""']
    return _with_header(lines + [""], c["contract"], 0, toml_header)


# ---------------------------------------------------------------------------
# Rendering: hook configs
# ---------------------------------------------------------------------------

def _matchers(rules, host):
    hm = (rules.get("host_matchers") or {}).get(host) or {}
    return hm


# The Codex bootstrap (Vex gate 2026-09-14, V-05 / condition C3).
#
# Codex documents `cwd` on the hook payload and names NO project-root variable,
# so the old `${CODEX_PROJECT_DIR:-$PWD}` expression resolved to the session's
# working directory. A session started in a subfolder (the WiP room, say)
# therefore pointed every hook at `<subfolder>/.claude/hooks/<guard>.py`,
# python could not open it, and python
# exits 2 -- which Codex reads as a DENY. That is a deny-all from any subfolder,
# not the fail-open the rule table claimed, and a guard that denies everything is
# the shape somebody switches off.
#
# So the command below finds the vault the same way `find_root()` does: walk up
# from the payload `cwd` to the folder holding AGENTS.md. Two properties matter
# and both are deliberate:
#
#   * it reads the payload from stdin and hands the SAME bytes to the guard, so
#     reading `cwd` does not consume the guard's input;
#   * when no AGENTS.md is found it prints one line and exits 0. A guard that
#     cannot locate the vault it protects has not reviewed anything, and saying
#     so out loud beats denying every tool call in the session. The fail-closed
#     ruling of V-03 is about a guard that RAN and could not parse its payload;
#     this is a guard that never started.
#
# Written with no single quote anywhere, because the whole program is carried
# inside one single-quoted shell argument.

_CODEX_BOOTSTRAP = """import json,os,subprocess,sys
b=sys.stdin.buffer.read()
try:
    d=(json.loads(b or b"{}") or {}).get("cwd") or ""
except Exception:
    d=""
d=os.path.abspath(d or os.environ.get("CODEX_PROJECT_DIR") or os.getcwd())
while d!=os.path.dirname(d) and not os.path.isfile(os.path.join(d,"AGENTS.md")):
    d=os.path.dirname(d)
g=os.path.join(d,sys.argv[2])
if not os.path.isfile(g):
    sys.stderr.write("codex hook: no AGENTS.md at or above the session cwd, so "+sys.argv[2]+" did not run and nothing was reviewed\\n")
    raise SystemExit(0)
raise SystemExit(subprocess.run([sys.argv[1],"-I","-B","-X","utf8",g],input=b).returncode)
"""


# HOW A GUARD IS LAUNCHED, AND WHY IT IS SPELLED OUT LIKE THIS
# ------------------------------------------------------------
# Conrad Froehling, Windows 11, 2026-09-16: the shell form this used to render
# (`PYTHONSAFEPATH=1 python3 "$CLAUDE_PROJECT_DIR/..."`) is three POSIX
# assumptions in one line. Claude Code runs a shell-form hook through Git Bash
# where it exists and PowerShell where it does not, and in PowerShell
# `VAR=1 cmd` is a syntax error and a bare `$CLAUDE_PROJECT_DIR` is `$null`.
# A member without Git Bash therefore had no guards at all and nothing said so.
#
# So both Claude hooks render in EXEC FORM: `command` plus `args`, which the
# host spawns directly with no shell between it and the interpreter, and which
# substitutes `${CLAUDE_PROJECT_DIR}` inside an argument. Vex's ruling on the
# shape, 2026-09-16, and each piece of it earns its place:
#
#   * `-I` isolated mode drops the script's own folder from sys.path, which is
#     the F1 defence the retired `PYTHONSAFEPATH=1` prefix was reaching for.
#     The variable is a no-op below Python 3.11; `-I` has meant this since 3.4.
#     Belt and braces: every guard drops that entry itself as its first
#     statement, so a guard launched some other way is defended too.
#   * `-B` writes no bytecode, so a guard never drops __pycache__ into the tree
#     it is guarding.
#   * `-X utf8` forces UTF-8 mode, so a payload carrying an emoji does not die
#     in cp1252 on a German Windows box.
#   * BRACED `${CLAUDE_PROJECT_DIR}`. Claude Code substitutes the braced form;
#     the bare form is a shell expansion and there is no shell here.
#
# THE INTERPRETER. Bare `python3` on macOS and Linux, where it is on PATH and
# means what it says. On Windows the ABSOLUTE `sys.executable` of whatever
# interpreter ran `apply`, because stock Windows Python installs `python.exe`
# and not `python3`, and because libuv resolves a bare name against the CURRENT
# DIRECTORY first: a synced vault carrying its own `python3` file would then be
# running the guard (Vex F-A, HIGH). The cost is real and is Tom's accepted
# trade: upgrade Python on Windows and `apply` has to run again.
HOOK_OS_NAME = os.name          # forced to "nt" by the red tests
HOOK_EXECUTABLE = sys.executable
GUARD_FLAGS = ("-I", "-B", "-X", "utf8")

# Exec form (`args` on a hook) is read by Claude Code 2.1.139 and newer. Below
# that the key is ignored, the hook runs with no arguments at all, and every
# guard silently reviews nothing. POSIX falls back to the shell form carrying
# the same flags; Windows has no safe fallback and refuses to render the key.
CLAUDE_EXEC_FORM_FLOOR = (2, 1, 139)
_CLAUDE_VERSION = []            # one probe per process


def _hook_is_windows():
    return HOOK_OS_NAME == "nt"


def claude_code_version(_cache=_CLAUDE_VERSION):
    """(major, minor, patch) from `claude --version`, or None.

    None means "not answerable here", never "old": `claude` is a CLI a member
    may not have on PATH at all, and a generator that guessed a version from
    silence would be guessing about the only thing this decides.
    """
    if _cache:
        return _cache[0]
    exe = shutil.which("claude")
    v = None
    if exe:
        try:
            r = subprocess.run([exe, "--version"], capture_output=True,
                               text=True, timeout=15)
            m = re.search(r"(\d+)\.(\d+)\.(\d+)",
                          (r.stdout or "") + " " + (r.stderr or ""))
            if m:
                v = tuple(int(x) for x in m.groups())
        except (OSError, ValueError, subprocess.SubprocessError):
            v = None
    _cache.append(v)
    return v


def _guard_path_expr(rule, hm):
    """The guard's path as the host will read it. Braced, always."""
    var = hm.get("project_dir_var") or "CLAUDE_PROJECT_DIR"
    return "${%s}/%s" % (var, rule["guard"])


def _guard_hook(rule, host, hm, exec_form=True):
    """The one hook entry the host runs, minus its timeout.

    Claude Code sets $CLAUDE_PROJECT_DIR and documents it, so its command names
    the interpreter and hands it the path as an argument. A host whose table
    says `project_dir_finder: walk-up-to-AGENTS.md` gets the bootstrap above
    instead, in shell form, because it has no such variable and because its
    support for `args` is not verified: an unverified key is a hook that may
    run with no arguments, which is a guard reviewing nothing.
    """
    interp = rule.get("interpreter") or "python3"
    is_py = interp in ("python", "python3")
    flags = list(GUARD_FLAGS) if is_py else []
    if hm.get("project_dir_finder") == "walk-up-to-AGENTS.md":
        # The bootstrap is python3 itself and spawns the guard as a child, so
        # the flags go on both: on the bootstrap here, and on the child inside
        # _CODEX_BOOTSTRAP.
        return {"type": "command",
                "command": "python3 %s -c '%s' %s \"%s\""
                           % (" ".join(GUARD_FLAGS), _CODEX_BOOTSTRAP, interp,
                              rule["guard"])}
    path = _guard_path_expr(rule, hm)
    if not exec_form:
        return {"type": "command",
                "command": " ".join([interp] + flags + ['"%s"' % path])}
    command = HOOK_EXECUTABLE if (is_py and _hook_is_windows()) else interp
    return {"type": "command", "command": command, "args": flags + [path]}


def claude_hook_form():
    """-> (exec_form, refusal, note). Decided once, from the host's version.

    `refusal` is a whole message and not a flag, because the only useful thing
    to hand a member whose Claude Code is too old is the sentence that tells
    them what to type.
    """
    v = claude_code_version()
    floor = ".".join(str(n) for n in CLAUDE_EXEC_FORM_FLOOR)
    if v is None:
        return True, None, (
            "`claude` is not on PATH here, so its version could not be read. "
            "The hooks are rendered in exec form, which needs Claude Code %s "
            "or newer; below that the arguments are ignored and every guard "
            "runs with no payload path and reviews nothing." % floor)
    if v >= CLAUDE_EXEC_FORM_FLOOR:
        return True, None, None
    got = ".".join(str(n) for n in v)
    if _hook_is_windows():
        return False, (
            "REFUSED to render the `hooks` key: Claude Code %s is below %s, "
            "the first version that reads a hook's `args`. On Windows there is "
            "no safe fallback (a shell-form hook runs through Git Bash where "
            "it exists and PowerShell where it does not, and in PowerShell a "
            "bare $CLAUDE_PROJECT_DIR is $null), so nothing was written rather "
            "than wiring up guards that quietly review nothing. update Claude "
            "Code to %s or newer, then run this again. Every other key in "
            ".claude/settings.json is untouched." % (got, floor, floor)), None
    return False, None, (
        "Claude Code %s is below %s, the first version that reads a hook's "
        "`args`, so the hooks render in shell form with the same flags. "
        "Update Claude Code to %s or newer and run this again to get the exec "
        "form, which needs no shell at all." % (got, floor, floor))


def render_hooks_block(rules, host):
    """One host's `hooks` object, rendered from the neutral table.

    Rules that render to the same (event, matcher) collapse into one entry with
    one command each, in table order, which is what a person reading the config
    should see too: one script answering two rules is one hook.
    """
    hm = _matchers(rules, host)
    if not hm:
        return None, ["host_matchers has no entry for %r" % host]
    events = hm.get("events") or {}
    notes = []
    exec_form = True
    if host == "claude-code":
        exec_form, refusal, note = claude_hook_form()
        if note:
            notes.append(note)
        if refusal:
            # NOT an empty block and NOT a half-rendered one. Returning None
            # leaves `hooks` out of the build entirely, so settings_diff has
            # nothing to compare, apply_settings is never called, and every
            # other key in settings.json (permissions.deny among them) is
            # exactly where the member left it.
            return None, notes + [refusal]
    grouped = []  # [(event, matcher, [command...])]
    for rule in rules.get("rules", []):
        ev = events.get(rule["event"])
        if not ev:
            notes.append("%s: no %s equivalent for the neutral event %r, skipped"
                         % (rule["id"], host, rule["event"]))
            continue
        kinds = rule.get("tool_kinds") or []
        if kinds == ["session"]:
            matcher = hm.get("session")
        else:
            parts = [hm.get(k) for k in kinds if hm.get(k)]
            matcher = "|".join(parts) if parts else None
        # A rule may pin its own host matcher string (the private table does).
        if isinstance(rule.get("match"), str):
            matcher = rule["match"]
        hook = _guard_hook(rule, host, hm, exec_form=exec_form)
        key = (ev, matcher)
        for g in grouped:
            if (g[0], g[1]) == key:
                if hook not in g[2]:
                    g[2].append(hook)
                    g[3].append(rule.get("timeout_seconds"))
                break
        else:
            grouped.append([ev, matcher, [hook], [rule.get("timeout_seconds")]])
    block = {}
    for ev, matcher, hooks_, timeouts in grouped:
        entry = {}
        if matcher:
            entry["matcher"] = matcher
        hooks = []
        for h, to in zip(hooks_, timeouts):
            h = dict(h)
            if to:
                h["timeout"] = to
            hooks.append(h)
        entry["hooks"] = hooks
        block.setdefault(ev, []).append(entry)
    return block, notes


def render_codex_hooks(rules):
    block, notes = render_hooks_block(rules, "codex")
    if block is None:
        return None, notes
    doc = {"description": "", "hooks": block}
    body = json.dumps({"hooks": block}, indent=2, ensure_ascii=False)
    doc["description"] = ("%s from `06 AI Team/AI Team Knowledge/Scripts/"
                          "hooks-rules.json`. content-hash:%s. Do not hand-edit: "
                          "change the table and re-run the generator."
                          % (GEN_MARK, _hash(body)))
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n", notes


def codex_hooks_hand_edited(text):
    try:
        doc = json.loads(text)
    except ValueError:
        return True
    desc = doc.get("description") or ""
    if GEN_MARK not in desc:
        return None
    m = re.search(r"content-hash:([0-9a-f]{12})", desc)
    if not m:
        return True
    body = json.dumps({"hooks": doc.get("hooks", {})}, indent=2, ensure_ascii=False)
    return _hash(body) != m.group(1)


# ---------------------------------------------------------------------------
# The hand-written shims already on disk
# ---------------------------------------------------------------------------
# 51 in this vault, 8 in the public Scaffold, every one written by a person.
# Most of them carry instructions the contract does not: a mailbox rule, a
# cold-start briefing, a return format. Overwriting those would delete the only
# copy. The contract is the SSOT, so the extra lines have to MOVE there, and
# that is a person's judgement, not a generator's.
#
# The rule: a shim is safe to replace only when everything it says is already
# said by what the generator would produce. Two ways it can carry more:
#   - body lines the generated body does not have, or
#   - a frontmatter key the contract does not supply. `tools` is the one that
#     matters: 17 shims in this vault restrict tools and no contract does, and
#     regenerating one would silently WIDEN that agent's access.

def _norm(s):
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def classify_shim(path, generated_text, contract):
    """-> ('absent'|'generated'|'replaceable'|'keep', reason)"""
    if not path.exists():
        return "absent", ""
    text = path.read_text(encoding="utf-8")
    if header_line_of(text) is not None:
        return "generated", ""
    fm = parse_front(text)
    extra_keys = []
    if (fm.get("tools") or "") and not contract["tools"]:
        extra_keys.append("tools")
    if (fm.get("model") or "") and not contract["model"]:
        extra_keys.append("model")
    have = set(_norm(l) for l in text.split("\n---", 2)[-1].split("\n")
               if _norm(l) and not _norm(l).startswith("<!--"))
    want = set(_norm(l) for l in generated_text.split("\n---", 2)[-1].split("\n")
               if _norm(l) and not _norm(l).startswith("<!--"))
    extra_lines = sorted(have - want)
    if extra_keys or extra_lines:
        bits = []
        if extra_keys:
            bits.append("frontmatter the contract does not carry: " + ", ".join(extra_keys))
        if extra_lines:
            bits.append("%d body line(s) the contract does not carry" % len(extra_lines))
        return "keep", "; ".join(bits)
    return "replaceable", ""


# ---------------------------------------------------------------------------
# The build: one list of intended outputs
# ---------------------------------------------------------------------------

class Build(object):
    def __init__(self, root):
        self.root = root
        self.files = {}      # relpath -> text
        self.links = {}      # relpath -> target relpath (a folder)
        self.sources = {}    # relpath -> source relpath
        self.keep = []       # (relpath, reason) hand-written, left alone
        self.notes = []      # plain lines for plan and doctor
        self.problems = []   # red
        self.hooks_refused = None   # a whole sentence, or None

    def add(self, rel, text, source):
        self.files[rel] = text
        self.sources[rel] = source

    def add_link(self, rel, target, source):
        self.links[rel] = target
        self.sources[rel] = source


def build(root):
    b = Build(root)
    skills, problems = read_procedures(root)
    b.problems.extend(problems)
    contracts, cproblems = read_contracts(root)
    b.problems.extend(cproblems)
    dispatchable = set(c["slug"] for c in contracts)
    rules, rule_err = read_rules(root)

    # --- token budget, counted before anything is written -------------------
    # What a host loads at startup is the name and the description of every
    # skill, and nothing else. Four characters to the token is the usual rough
    # count; it is an estimate and is named as one.
    startup = sum(len(sk["name"]) + len(description_for(sk)) for sk in skills)
    b.tokens = (startup + 3) // 4
    b.skill_count = len(skills)
    if b.tokens > MAX_SKILL_TOKENS:
        b.problems.append(
            "skill startup budget: %d estimated tokens across %d skills, over "
            "MAX_SKILL_TOKENS=%d. This is a HOUSE budget, not a vendor limit: "
            "raise the constant on purpose or drop a skill, but do not let it "
            "drift." % (b.tokens, len(skills), MAX_SKILL_TOKENS))

    # --- skills -------------------------------------------------------------
    for sk in skills:
        if sk["prerun"]:
            first = sk["prerun"].split('"')
            cand = first[1] if len(first) > 1 else ""
            if cand and not (root / cand).exists():
                b.notes.append("skill %s: skill_prerun names %s, which is not on "
                               "disk; the prerun is still written, and it will "
                               "fail loudly rather than silently" % (sk["name"], cand))
        b.add("06 AI Team/AI Team Knowledge/Skills/%s/SKILL.md" % sk["name"],
              render_canonical_skill(sk, root, dispatchable), sk["source"])
        b.add(".claude/skills/%s/SKILL.md" % sk["name"],
              render_claude_skill(sk, root, dispatchable), sk["source"])
        b.add_link(".agents/skills/%s" % sk["name"],
                   "06 AI Team/AI Team Knowledge/Skills/%s" % sk["name"], sk["source"])

    # --- agent shims --------------------------------------------------------
    for c in contracts:
        claude_rel = ".claude/agents/%s.md" % c["slug"]
        text = render_claude_shim(c)
        state, reason = classify_shim(root / claude_rel, text, c)
        if state == "keep":
            b.keep.append((claude_rel, reason))
        else:
            b.add(claude_rel, text, c["contract"])
        b.add(".codex/agents/%s.toml" % c["slug"], render_codex_shim(c), c["contract"])
        b.add(".gemini/agents/%s.md" % c["slug"], render_gemini_shim(c), c["contract"])

    # --- hook configs -------------------------------------------------------
    # A settings.json that does not parse is a red, never an empty document.
    # apply_settings() rewrites the file from a parsed copy, and a parse that
    # silently fell back to {} would write back the `hooks` key alone: every
    # `permissions.deny` row (the never-send-email denies among them) would be
    # gone with nothing said. Measured 2026-09-14 with one trailing comma.
    # (Vex security gate.)
    sp = settings_path(root)
    if sp.exists():
        try:
            json.loads(sp.read_text(encoding="utf-8"))
        except (ValueError, OSError, UnicodeDecodeError) as e:
            b.problems.append(".claude/settings.json does not parse (%s). Refused: "
                              "rewriting it would drop every key that is not `hooks`, "
                              "permissions.deny included. Repair the file by hand, "
                              "then re-run." % e)
    if rule_err:
        b.notes.append("hooks: " + rule_err)
    else:
        b.rules = rules
        block, notes = render_hooks_block(rules, "claude-code")
        b.notes.extend("hooks/claude-code: " + n for n in notes)
        if block is not None:
            b.claude_hooks = block
        else:
            for n in notes:
                if n.startswith("REFUSED"):
                    b.hooks_refused = n
        txt, notes = render_codex_hooks(rules)
        b.notes.extend("hooks/codex: " + n for n in notes)
        if txt is not None:
            b.add(".codex/hooks.json", txt,
                  "06 AI Team/AI Team Knowledge/Scripts/hooks-rules.json")
        b.add(".claude/settings.README.md", render_settings_readme(root, rules),
              "06 AI Team/AI Team Knowledge/Scripts/hooks-rules.json")

    # --- host pointer files: written where absent, kept up to date where we
    # wrote them, never touched where a person wrote them ---------------------
    def pointer(rel, render):
        p = root / rel
        if p.exists() and header_line_of(p.read_text(encoding="utf-8")) is None:
            b.notes.append("pointer: %s was written by hand and was not touched" % rel)
            return
        b.add(rel, render(), "AGENTS.md")

    gemini_entry(root, b)
    pointer(".codex/config.toml", lambda: render_codex_config(root))
    # CLAUDE.md is NEVER written here, present or absent. It is a root entry
    # contract, it is on the write guard's protected list, and a generator that
    # can replace the file describing the rules is a generator that can remove
    # them.
    return b


GEMINI_SETTINGS = {"context": {"fileName": ["AGENTS.md"]}}


def gemini_entry(root, b):
    """Point Gemini CLI at AGENTS.md: `.gemini/settings.json`, written only when absent.

    AGENTS.md is the only entry file (Tom, 2026-09-24), so there is no
    GEMINI.md. Gemini CLI's `context.fileName` names the file it loads as
    project context, a string or a list. Read in the installed Gemini CLI
    0.58.0 source on 2026-09-24: workspace settings and GEMINI.md are gated
    by the SAME folder-trust check (untrusted means neither is applied, and
    trust is on only when `security.folderTrust.enabled` is set), so this
    file finds Larry exactly where a GEMINI.md would have.

    JSON carries no generated header, so a settings.json that exists is the
    user's: it is never rewritten, only checked, and a missing AGENTS.md entry
    is a note naming the one key to add.
    """
    rel = ".gemini/settings.json"
    p = root / rel
    old = root / "GEMINI.md"
    if old.is_file() and header_line_of(old.read_text(encoding="utf-8")) is not None:
        b.notes.append("pointer: GEMINI.md is no longer generated (Gemini reads "
                       "AGENTS.md through %s). It carries the generated header; "
                       "delete it." % rel)
    if not p.exists():
        b.add(rel, json.dumps(GEMINI_SETTINGS, indent=2) + "\n", "AGENTS.md")
        return
    try:
        names = (json.loads(p.read_text(encoding="utf-8")).get("context") or {}).get("fileName")
    except (ValueError, AttributeError):
        b.notes.append("pointer: %s does not parse, so Gemini CLI may not find "
                       "AGENTS.md. Not touched." % rel)
        return
    names = [names] if isinstance(names, str) else (names or [])
    if "AGENTS.md" not in names:
        b.notes.append("pointer: %s exists and its context.fileName does not name "
                       "AGENTS.md, so Gemini CLI will not load the contract. Add "
                       "\"AGENTS.md\" to context.fileName by hand; the file is "
                       "yours and was not touched." % rel)


def render_codex_config(root):
    """.codex/config.toml, written only when absent.

    UNVERIFIED, and said so in `doctor`: OpenAI's own configuration page
    (learn.chatgpt.com/docs/agent-configuration/agents-md, fetched 2026-09-14)
    documents `project_doc_max_bytes` and its 32 KiB default, and shows it being
    set in `~/.codex/config.toml`. It does NOT say whether a project-local
    `.codex/config.toml` is read for that key. The hooks page does document
    `<repo>/.codex/config.toml` as a config location, which is why this file is
    written at all. If the key turns out to be global-only, the fix is one line
    in the user's own `~/.codex/config.toml` and this file is harmless.
    """
    size = 0
    p = root / "AGENTS.md"
    if p.is_file():
        size = p.stat().st_size
    body = [
        "",
        "# Codex reads AGENTS.md from the project root. This vault's entry file",
        "# is %d bytes; Codex's documented default budget for project" % size,
        "# instructions is 32 KiB, and an entry over that is an entry that gets",
        "# truncated with nothing said about it.",
        "#",
        "# UNVERIFIED: whether Codex honours this key from a PROJECT-local",
        "# config.toml, or only from ~/.codex/config.toml. `scaffold-init.py",
        "# doctor` reports it as unverified every run until somebody watches it",
        "# work. Until then, setting the same line in ~/.codex/config.toml is",
        "# the path that is documented.",
        "project_doc_max_bytes = 65536",
        "",
        "# YOUR GUARDS ARE OFF UNTIL YOU TRUST THEM, AND `codex exec` CANNOT ASK.",
        "#",
        "# This vault ships hooks in .codex/hooks.json: one of them refuses a",
        "# write to your raw daily notes, to AGENTS.md, to a specialist contract,",
        "# and to any content carrying a secret-shaped value. Codex runs NO",
        "# project hook until you have reviewed and trusted it, the trust prompt",
        "# lives in the interactive TUI (`/hooks`), and `codex exec` never shows",
        "# it. A scripted Codex run in a fresh vault therefore has no guards at",
        "# all and says nothing about it.",
        "#",
        "# Open Codex interactively in this folder ONCE, run `/hooks`, and trust",
        "# them. Nothing in this vault can do it for you: trust is recorded in",
        "# ~/.codex/config.toml under [hooks.state], and the key contains this",
        "# vault's ABSOLUTE PATH, so moving or renaming the folder drops the",
        "# trust silently and the guards go quiet with no message. Trust them",
        "# again after a move. `--dangerously-bypass-hook-trust` runs them for",
        "# one invocation without recording anything, and is for automation that",
        "# has already vetted the hook source.",
        "#",
        "# One more thing a script cannot do for you: Codex's workspace-write",
        "# sandbox refuses writes into .codex/ and .agents/, so",
        "# `scaffold-init.py apply` has to be run by YOU, from your own terminal,",
        "# not by the model inside a Codex session.",
        "",
    ]
    return _with_header(body, "AGENTS.md", 0, toml_header)


def render_settings_readme(root, rules):
    """The sidecar that carries the generator's ownership of settings.json.

    settings.json itself gets no header: the generator owns exactly one key in
    it (`hooks`) and a top-level key of its own would be a key the host never
    asked for. So the ownership statement, the rendering table and the hash of
    the rendered block live here, next to it.
    """
    block, _ = render_hooks_block(rules, "claude-code")
    # A refused block (Claude Code below the exec-form floor on Windows) is
    # recorded as such rather than hashed as an empty document: the sidecar
    # must never read as "these are the hooks" when there are none.
    blob = json.dumps(block, indent=2, ensure_ascii=False)
    rows = []
    for rule in rules.get("rules", []):
        rows.append("| `%s` | %s | %s |" % (
            rule["id"], rule.get("event", ""),
            "yes, exit 2" if (rule.get("blocks") or rule.get("severity") in ("block", "deny"))
            else "no, it only adds context"))
    body = [
        "",
        "# `.claude/settings.json` is generated. Do not edit it.",
        "",
        "Its `hooks` key is rendered by `scaffold-init.py` from one table:",
        "`06 AI Team/AI Team Knowledge/Scripts/hooks-rules.json`. That table is",
        "the SSOT. Change the table and re-run the generator; a matcher typed",
        "straight into `settings.json` is the host lock-in the table exists to",
        "prevent, and it is invisible to every other host.",
        "",
        "The generator owns the `hooks` key and nothing else in that file.",
        "`permissions` and every other key you put there are read, kept and",
        "written back untouched.",
        "",
        ("Rendered hooks block content-hash: `%s`" % _hash(blob)) if block is not None
        else ("No hooks block is rendered on this machine. Claude Code here is "
              "below the version that reads a hook's `args`, and on Windows "
              "there is no safe shell fallback. `scaffold-init.py doctor` "
              "prints the sentence with the version in it."),
        "",
        "## What is rendered, and whether it blocks",
        "",
        "| Rule in the table | Neutral event | Blocks? |",
        "| --- | --- | --- |",
    ] + rows + [
        "",
        "Two rules answered by the same script at the same event render to one",
        "hook entry, because one script running once is what actually happens.",
        "",
        "## What this configuration does not prove",
        "",
        "- **It is not an enforcement boundary.** Some tool paths bypass hooks,",
        "  and nothing outside a tool call is visible to a hook at all. A shell",
        "  redirect or an editor outside the session reaches every protected",
        "  path untouched.",
        "- **It is per device.** `.claude/` does not travel through Obsidian",
        "  Sync. A second machine has the scripts and none of this wiring until",
        "  the generator is run there too.",
        "- **It is one host.** Codex reads `.codex/hooks.json`, Cursor loads",
        "  Claude Code's hooks for compatibility, and Gemini CLI has no hook",
        "  system at all.",
        "- **Registered is not proven.** A guard listed here still has to have",
        "  been watched go red. `run-red-tests.py` carries that second fact.",
        "",
    ]
    return _with_md_header(body, "06 AI Team/AI Team Knowledge/Scripts/hooks-rules.json",
                           insert_at=1)


# ---------------------------------------------------------------------------
# Comparing the build with what is on disk
# ---------------------------------------------------------------------------

def settings_path(root):
    return root / ".claude" / "settings.json"


def settings_diff(root, b):
    """-> (action, current_doc). action in create / update / same."""
    p = settings_path(root)
    if not hasattr(b, "claude_hooks"):
        return None, None
    if not p.exists():
        return "create", {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return "update", {}
    return ("same" if doc.get("hooks") == b.claude_hooks else "update"), doc


def generated_on_disk(root):
    """Every file under the harness folders that carries our header."""
    out = []
    for base in (".claude", ".codex", ".gemini", ".agents",
                 "06 AI Team/AI Team Knowledge/Skills"):
        d = root / base
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.is_symlink():
                continue
            if f.suffix not in (".md", ".toml", ".json"):
                continue
            # `.agents/skills/<name>` belongs to the second loop below, whole.
            # Where the OS refuses symlinks it is a COPY of the skill folder,
            # so every SKILL.md inside it carries the generated header and this
            # loop reported each one as a generated file nobody produces:
            # `check` then asked to remove the contents of the link it had just
            # written (Conrad Froehling, 2026-09-16).
            if f.relative_to(root).as_posix().startswith(".agents/skills/"):
                continue
            # `_template.md` and any other underscore file is documentation for
            # the shape, not an instance of it. It quotes the generated header
            # verbatim to SHOW what one looks like, which is exactly why it must
            # be skipped here: it is the one file whose header is an example.
            if f.name.startswith("_"):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f.name == "hooks.json":
                if GEN_MARK in text:
                    out.append(f.relative_to(root).as_posix())
                continue
            if header_line_of(text) is not None:
                out.append(f.relative_to(root).as_posix())
    for base in (".agents/skills",):
        d = root / base
        if d.is_dir():
            for f in sorted(d.iterdir()):
                # A symlink OR a directory: `link()` writes whichever the OS
                # allows, and an entry the generator no longer produces has to
                # be swept either way.
                if f.is_symlink() or f.is_dir():
                    out.append(f.relative_to(root).as_posix())
    return sorted(set(out))


def generated_counts(b, same):
    """`same` split into (generated files, host links).

    One definition in one place. `check` prints these and `doctor --json`
    writes them, and two numbers in the product that mean the same thing and
    disagree is a defect a member has no way to resolve: it just reads as the
    plugin being wrong. A symlink carries no header and no content hash, so it
    is never counted among the files whose hash matched, which is what the old
    single tally claimed about all of them.
    """
    files = len([r for r in same if r in b.files])
    return files, len(same) - files


def copy_is_stale(copy_dir, target_dir):
    """True when a copied host link no longer matches the folder it stands for.

    Bytes, and the set of relative paths on both sides, because a copy that has
    the right files with the wrong contents and a copy that is missing a file
    are the same defect from the member's side: the host reads something the
    generator did not produce. A copy that holds a symlink of its own is stale
    on principle rather than followed.
    """
    def snapshot(d):
        out = {}
        for p in sorted(d.rglob("*")):
            if p.is_symlink():
                return None
            if p.is_file():
                out[p.relative_to(d).as_posix()] = p.read_bytes()
        return out

    try:
        if not target_dir.is_dir():
            return True
        here, there = snapshot(copy_dir), snapshot(target_dir)
    except OSError:
        return True
    return here is None or there is None or here != there


def diff(root, b):
    create, update, same, remove, edited = [], [], [], [], []
    orphans = []
    for rel, text in sorted(b.files.items()):
        p = root / rel
        if not p.exists():
            create.append(rel)
            continue
        # Read from bytes, not through text mode. Text mode folds CRLF
        # back to LF on the way in, so a generated file that landed as CRLF
        # (write_text on Windows did that until 2026-09-15) compared equal
        # and was never corrected. Bytes make the difference visible, and the
        # write below lands LF on every platform (Ian Slattery, T15-A).
        cur = noteio.read_note(p)[0]
        if cur == text:
            same.append(rel)
        else:
            if header_line_of(cur) is not None and hand_edited(p):
                edited.append(rel)
            update.append(rel)
    for rel, target in sorted(b.links.items()):
        p = root / rel
        if p.is_symlink():
            try:
                resolved = (p.parent / os.readlink(p)).resolve()
            except OSError:
                resolved = None
            if resolved == (root / target).resolve():
                same.append(rel)
            else:
                update.append(rel)
        elif p.is_dir():
            # A COPY IS A HOST LINK TOO, AND IT CAN BE CURRENT.
            # Where the OS refuses symlinks, `link()` copies the skill folder
            # instead. This used to read every non-symlink at a link path as
            # "update", so on Windows `check` was red for ever and `apply`
            # rewrote the same copies on every run: a generator whose check can
            # never go green proves nothing at all (Conrad Froehling,
            # 2026-09-16). A copy whose bytes still match its target is
            # current; one whose bytes have moved on is an update, which is
            # exactly what a stale copy needs.
            if copy_is_stale(root / rel, root / target):
                update.append(rel)
            else:
                same.append(rel)
        elif p.exists():
            update.append(rel)
        else:
            create.append(rel)
    intended = set(b.files) | set(b.links)
    for rel in generated_on_disk(root):
        if rel in intended:
            continue
        src = None
        p = root / rel
        if p.is_symlink():
            remove.append((rel, "the skill it links to is no longer generated"))
            continue
        if p.is_dir():
            # A copied host link, on an OS that refuses symlinks. Same verdict
            # as the symlink above; reading it as a note would raise.
            remove.append((rel, "the skill it was copied from is no longer "
                                "generated"))
            continue
        line = header_line_of(noteio.read_note(p)[0]) or ""
        m = re.search(r"from `([^`]+)`", line)
        src = m.group(1) if m else None
        if src and (root / src).exists():
            # The rule is remove-only-when-the-source-is-gone. A file the
            # generator no longer produces while its source still exists is a
            # rename or a dropped trigger, and deleting on that guess is how a
            # generator eats work nobody asked it to touch. Reported, not
            # removed, every run until a person rules on it.
            orphans.append(rel)
        else:
            remove.append((rel, "its source `%s` is gone" % (src or "unknown")))
    b.orphans = orphans
    return create, update, same, remove, edited


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    # Bytes, so a generated file is byte-identical on macOS, Linux and
    # Windows. write_text() would turn every "\n" into "\r\n" on Windows and
    # the manifest hashes would differ per platform.
    noteio.write_note(p, text)


def apply_order(rels, b):
    """The sequence `apply` writes in, and the sequence `plan` prints.

    FILES BEFORE LINKS, each alphabetical, and one function so the two commands
    cannot drift apart again.

    `apply` used to walk `sorted(set(create + update))`. "." sorts before "0",
    so `.agents/skills/<name>` (a link) was always processed before
    `06 AI Team/AI Team Knowledge/Skills/<name>/SKILL.md` (the file it points
    at). On macOS and Linux the dangling symlink is filled in a moment later
    and nothing ever shows. On Windows, for an unprivileged shell with
    Developer Mode off, os.symlink raises WinError 1314, `link()` falls through
    to shutil.copytree, and copytree has nothing to copy: FileNotFoundError,
    traceback, harness half built. An Administrator terminal hid the whole
    thing, because there the symlink succeeds (Conrad Froehling, Windows 11,
    2026-09-16).

    `plan` listed the same set in its own order again, so the two commands
    disagreed about what happens when and the order that mattered was the one
    nobody printed.
    """
    rels = sorted(set(rels))
    return ([r for r in rels if r not in b.links]
            + [r for r in rels if r in b.links])


def link(root, rel, target):
    """Symlink where the OS allows it, copy where it does not.

    Recorded either way, because the two behave differently under a sync tool
    and under a host that resolves paths itself, and a member on Windows or on
    a synced folder gets the copy without being told otherwise.
    """
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink() or p.exists():
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
    rel_target = os.path.relpath((root / target), p.parent)
    try:
        os.symlink(rel_target, p, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError, AttributeError):
        shutil.copytree(root / target, p)
        return "copy"


def apply_settings(root, b):
    """Own the `hooks` key. Keep every other key exactly as it was."""
    p = settings_path(root)
    doc = {}
    if p.exists():
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            # Belt and braces: build() already refuses this in `problems`.
            # Never fall back to {}; that is the deny-list wipe (Vex, 2026-09-14).
            raise SystemExit("FAIL .claude/settings.json does not parse (%s); not "
                             "rewritten, because that would drop every key that is "
                             "not `hooks`." % e)
    doc["hooks"] = b.claude_hooks
    p.parent.mkdir(parents=True, exist_ok=True)
    noteio.write_note(p, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


# A SANDBOX THAT REFUSES THE WRITE MUST SAY SO IN WORDS, NOT IN A TRACEBACK
# (pilot C finding F4). Codex's `workspace-write` sandbox refuses writes into
# `.codex/` and `.agents/` even though they sit inside the workspace: Nolan's
# probe got "operation not permitted". So `apply` cannot finish from inside a
# Codex session and the new agent silently gets no Codex shim. There is no
# documented environment variable that says "you are in a Codex sandbox", so
# this does not guess: it attempts the write and reads EPERM, which is the
# only evidence that exists. The answer is not to retry, it is to hand the
# member the command to run in their own terminal.
def sandbox_note(root, rel, exc):
    return ("PERMISSION DENIED writing %s (%s). A host sandbox is refusing this "
            "path: Codex's workspace-write sandbox refuses .codex/ and .agents/ "
            "even inside the workspace. Nothing here can talk it round. Run this "
            "from your OWN terminal, outside the session:\n"
            "    python3 \"%s/06 AI Team/AI Team Knowledge/Scripts/scaffold-init.py\" apply"
            % (rel, exc, root))


def do_apply(root, b, out):
    create, update, same, remove, edited = diff(root, b)
    modes = {}
    denied = []
    for rel in apply_order(create + update, b):
        try:
            if rel in b.files:
                write(root, rel, b.files[rel])
            elif rel in b.links:
                modes[rel] = link(root, rel, b.links[rel])
        except PermissionError as exc:
            denied.append(rel)
            out(sandbox_note(root, rel, exc))
            continue
        except FileNotFoundError as exc:
            # ENOENT. With files written before links this should no longer
            # happen, and if it does the member gets a sentence naming the
            # path rather than a traceback with a half-built harness under it
            # (Conrad Froehling, 2026-09-16).
            denied.append(rel)
            out("MISSING SOURCE writing %s (%s). Nothing here can create it. "
                "Re-run `plan` and read what it says about that path; if the "
                "target of a host link is missing, the skill it points at was "
                "not generated." % (rel, exc))
            continue
        except OSError as exc:
            if getattr(exc, "errno", None) in (1, 13):   # EPERM, EACCES
                denied.append(rel)
                out(sandbox_note(root, rel, exc))
                continue
            raise
    for rel, why in remove:
        p = root / rel
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        # an emptied skill folder is swept with it
        if p.parent.is_dir() and not any(p.parent.iterdir()):
            p.parent.rmdir()
    act, _ = settings_diff(root, b)
    if act in ("create", "update"):
        apply_settings(root, b)
    if b.hooks_refused:
        # `plan` and `doctor` print every note; `apply` prints a summary. The
        # one note a member MUST see from `apply` is the one saying their
        # guards were not wired, so it is printed here by name.
        out(b.hooks_refused)
    out("apply: %d created, %d updated, %d already current, %d removed%s"
        % (len(create) - len([r for r in denied if r in create]),
           len(update) - len([r for r in denied if r in update]),
           len(same), len(remove),
           ", %d REFUSED by a host sandbox" % len(denied) if denied else ""))
    if denied:
        # AND IT EXITS NON-ZERO (Silas's Codex re-run 2026-09-14/15, R3).
        # Until now this said INCOMPLETE in prose and returned 0, so a model
        # that read the exit code rather than the paragraph reported a clean
        # activation with no shims, no skills and no guards behind it. Silas's
        # run caught it only by reading the prose and then running `check`. A
        # script that says INCOMPLETE and exits 0 is a green that is not green,
        # which is the exact shape this folder's own doctrine forbids.
        out("apply: the harness is INCOMPLETE. %d path(s) were refused: %s. Until "
            "they are written from your own terminal, the hosts that read them "
            "have no shims, no skills and no guards."
            % (len(denied), ", ".join(denied[:6])))
    if act in ("create", "update"):
        out("apply: .claude/settings.json hooks key %sd (every other key kept)" % act)
    if modes:
        kinds = sorted(set(modes.values()))
        out("apply: .agents/skills entries written as %s" % ", ".join(kinds))
        if "copy" in kinds:
            # SAY WHY, not just what. On Windows this is the normal outcome for
            # an unprivileged shell with Developer Mode off, and a member who
            # reads "copy" without the reason files a bug (Conrad Froehling,
            # 2026-09-16). The copy is made AFTER its target is written, so it
            # is a real copy of a real skill and not an empty folder.
            out("apply: this OS would not let us make a symlink, so those "
                "entries are copies of the skill folder. They work the same "
                "way; they go stale when the skill changes, which is what "
                "`check` is for, and a re-run refreshes them.")
    return create, update, same, remove, denied


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Does Codex trust THIS folder's hooks?
# ---------------------------------------------------------------------------
#
# Codex records the answer in its own config and never in the vault, keyed by
# the absolute path of the hooks file plus the position of the hook inside it:
#
#   [hooks.state."<abs vault>/.codex/hooks.json:<event>:<i>:<j>"]
#   trusted_hash = "..."
#
# So the answer is per machine AND per path, and moving or renaming the folder
# silently drops it. It is worth reading because the failure it hides is the
# worst shape a guard can have: `codex exec` never asks and runs no untrusted
# hook, without printing anything, so a member with untrusted hooks has every
# guard off and a terminal that looks exactly like one where they are on.
#
# An unreadable or absent config is "unknown" and never "no". Telling somebody
# their guards are off when the truth is that a file could not be opened sends
# them to fix something that may not be broken, and a guess wearing the clothes
# of a measurement is the one thing this whole report exists not to do.

CODEX_TRUST_TEXT = {
    "yes": ('yes, for this exact path. ~/.codex/config.toml records a '
            'trusted_hash under [hooks.state] for "%s/.codex/hooks.json". '
            'Moving or renaming this folder drops it, because the key carries '
            'the absolute path.'),
    "no": ('NOT TRUSTED, guards off in codex exec until trusted. '
           '~/.codex/config.toml carries no [hooks.state] entry for '
           '"%s/.codex/hooks.json", so no hook here has been reviewed on this '
           'machine. Codex asks only in an interactive session (/hooks); codex '
           'exec never asks and runs none of them, silently. Open Codex in this '
           'folder once and trust them.'),
    "unknown": ('not readable: ~/.codex/config.toml could not be read, so this '
                'says nothing rather than guessing.'),
}

CODEX_SANDBOX_TEXT = (
    "Codex's workspace-write sandbox refuses writes into .codex/ and .agents/, "
    "so scaffold-init.py apply must be run by the member from their own "
    "terminal, not by a model inside a Codex session. apply names every path it "
    "was refused and says the harness is incomplete.")

# A table header, and the one key inside it that proves a review happened.
_TOML_TABLE = re.compile(r'^\s*\[\s*hooks\.state\s*\.\s*"(.*)"\s*\]\s*$')
_TOML_ANY_TABLE = re.compile(r"^\s*\[")
_TOML_HASH = re.compile(r"^\s*trusted_hash\s*=")


def codex_config_path():
    """`${CODEX_HOME:-~}/.codex/config.toml`, as Codex resolves it."""
    home = os.environ.get("CODEX_HOME") or os.path.expanduser("~")
    return Path(home) / ".codex" / "config.toml"


def codex_trust(root, config_path=None):
    """'yes', 'no' or 'unknown' for this folder's hooks on this machine.

    Read as text rather than through a TOML parser on purpose: tomllib landed
    in 3.11 and this script runs on whatever python3 a member has. check-bases
    learned the same lesson the hard way when its PyYAML import turned two red
    tests green by never running them.
    """
    path = Path(config_path) if config_path else codex_config_path()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unknown"
    prefix = "%s/.codex/hooks.json:" % Path(root).resolve()
    key, has_hash = None, False

    def _proved():
        return key is not None and key.startswith(prefix) and has_hash

    for line in text.split("\n"):
        m = _TOML_TABLE.match(line)
        if m:
            if _proved():
                return "yes"
            key, has_hash = m.group(1), False
            continue
        if _TOML_ANY_TABLE.match(line):
            if _proved():
                return "yes"
            key, has_hash = None, False
            continue
        if key is not None and _TOML_HASH.match(line):
            has_hash = True
    return "yes" if _proved() else "no"


BINARIES = {"claude-code": "claude", "codex": "codex",
            "gemini": "gemini", "cursor": "cursor-agent"}
FOLDERS = {"claude-code": ".claude", "codex": ".codex",
           "gemini": ".gemini", "cursor": ".cursor"}

# `doctor --json` writes this for the Scaffold Check plugin. Machine-layer
# data under GL-1008: per device, regenerated, never tracked and never a
# source. `schema` is the first thing a reader checks.
#
# TEAM STATE, not life state (GL-1013 section 2.2, ruling j5d extended
# 2026-09-24): this generator is a team script and the file describes the
# team's hosts, hooks and guards, so it lives under team_path("team_state"),
# `.mypka/state/`, beside session.json and receipts/. It was
# `.icor-for-life/scripts/harness.json` until then; readers follow the move.
HARNESS_SCHEMA = 1
HARNESS_NAME = "harness.json"
HARNESS_PATH = ".mypka/state/" + HARNESS_NAME        # for messages; the write resolves it


def harness_file(root):
    """Where `doctor --json` writes harness.json for this team root."""
    return _resolver().team_path("team_state", root=root) / HARNESS_NAME


def _red_tests(root, run_tests):
    """The red-test suite's verdict, once: ({status, summary, skips}, lines).

    `status` is one of ok, red, absent, error, skipped. `lines` is what the
    terminal prints under `tested`, first line then continuations.
    """
    runner = tk(root) / "Scripts" / "run-red-tests.py"
    if not runner.is_file():
        msg = ("no run-red-tests.py in this folder, so no guard here has been "
               "watched go red")
        return {"status": "absent", "summary": msg, "skips": []}, [msg]
    if not run_tests:
        msg = "not run (--no-tests)"
        return {"status": "skipped", "summary": msg, "skips": []}, [msg]
    # --fast, because doctor is a health check somebody is WAITING for and the
    # full suite grew past a minute. The flag skips the groups that clone the
    # repo, read the build script and build fixture vaults; every guard case
    # still runs and a failure still exits 1. The release gate and CI call the
    # same file with no arguments and get the whole thing, so nothing that
    # ships was proved by a fast run. The suite names the skipped groups on its
    # own summary line and that line is what lands under `tested:` here.
    try:
        r = subprocess.run([sys.executable, str(runner), "--fast"],
                           capture_output=True, text=True, timeout=900)
    except (subprocess.TimeoutExpired, OSError) as e:
        msg = "could not run the suite here (%s)" % e
        return {"status": "error", "summary": msg, "skips": []}, [msg]
    # A failing run prints its findings on stderr and exits before the
    # summary line ever reaches stdout, so reading stdout alone reports
    # "no output" for the one case that matters most.
    tail = [l for l in (r.stdout or "").strip().split("\n") if l.strip()]
    err = [l for l in (r.stderr or "").strip().split("\n") if l.strip()]
    if r.returncode == 0:
        # the summary line, not the last line: both runners print a
        # standing reminder about SKIPs after their tally, and quoting
        # that as the result reports a warning as a count.
        ok = [l for l in tail if l.startswith("OK ")]
        summary = ok[-1] if ok else (tail[-1] if tail else "no output")
        skips = [l for l in tail if l.startswith("SKIP ")
                 or l.startswith("FAST-SKIP ") or l.startswith("FAST RUN")]
        return ({"status": "ok", "summary": summary, "skips": skips},
                [summary] + [l[:160] for l in skips])
    # A RED AND A CRASH ARE NOT THE SAME NEWS, AND THEY USED TO READ THE SAME.
    # A suite that goes red names the case on a `FAIL <guard>/<case>` line. A
    # suite that could not run at all here prints a traceback and no FAIL line:
    # no POSIX shell to spawn a .sh fixture with, an interpreter that is not
    # there, an import that failed. Calling that "RED, the suite found
    # something" blames a guard for the platform, which is what every Windows
    # member saw (Conrad Froehling, 2026-09-16). The two need different words
    # because they need different actions: a red is a defect in this folder, a
    # crash is a machine that cannot run the proof.
    findings = [l for l in err + tail if l.startswith("FAIL ")]
    if not findings:
        summary = ("could not run the suite here, exit %d. It reported no FAIL "
                   "line at all, so this is the suite crashing on this machine "
                   "and NOT a guard going red." % r.returncode)
        return ({"status": "error", "summary": summary, "skips": []},
                [summary] + (err or tail)[:6])
    summary = ("RED, exit %d. The suite found something; this is not a green."
               % r.returncode)
    return ({"status": "red", "summary": summary, "skips": []},
            [summary] + (err or tail)[:6])


# THE DEAD-INTERPRETER LINE, WHICH USED TO BE A SHELL SCRIPT
# ----------------------------------------------------------
# `session-start.sh` existed for one job that was not shell work: saying, in a
# plain line, that python3 is not installed, so a member whose session start
# ritual never ran found out from a sentence instead of from a runtime error.
# With both hooks rendered in exec form there is no shell in the chain at all,
# so that job moves HERE, where it is better done anyway: doctor spawns the
# interpreter the rendered hooks actually name and reports what happened.
#
# WHAT THIS DOES NOT PROVE. That the host can spawn it. This process and the
# host may resolve a bare `python3` differently, and the host may run under a
# different user or PATH. A pass means this machine can start that interpreter
# from here; a fail means nobody can, which is the half worth knowing.
def hook_interpreters(block):
    """Every distinct interpreter the rendered hooks name, in order."""
    seen = []
    for entries in (block or {}).values():
        for entry in entries:
            for h in entry.get("hooks") or []:
                cmd = h.get("command") or ""
                if "args" not in h:
                    # shell form: the interpreter is the first word, and a
                    # quoted path is never the first word of one of ours.
                    cmd = (cmd.split(" ") or [""])[0]
                if cmd and cmd not in seen:
                    seen.append(cmd)
    return seen


def interpreter_report(block):
    """-> [(command, ok, sentence)] for each interpreter the hooks name."""
    out = []
    for cmd in hook_interpreters(block):
        try:
            r = subprocess.run([cmd, "-c", "import sys; print(sys.version.split()[0])"],
                               capture_output=True, text=True, timeout=20)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            out.append((cmd, False,
                        "%s is what every hook in .claude/settings.json runs, "
                        "and it did not start here (%s). Until that path is a "
                        "working Python 3 the guards are registered and dead: "
                        "nothing is checked on this machine. Install Python 3, "
                        "or run `scaffold-init.py apply` again once it is "
                        "there, so the hooks are re-rendered against the "
                        "interpreter that exists." % (cmd, exc)))
            continue
        if r.returncode != 0:
            out.append((cmd, False,
                        "%s is what every hook in .claude/settings.json runs, "
                        "and it started but exited %d (%s). The guards are "
                        "registered and dead until that is fixed."
                        % (cmd, r.returncode,
                           (r.stderr or "").strip()[:160] or "no message")))
            continue
        out.append((cmd, True, "%s answered, Python %s"
                    % (cmd, (r.stdout or "").strip() or "unknown")))
    return out


def doctor_report(root, b, run_tests=True):
    """Everything doctor knows, worked out once.

    The terminal report and `harness.json` are both rendered from this. Two
    copies of the per-host logic would drift, and the plugin reading the file
    would then show a different answer from the terminal, which is the worst
    kind of wrong: two sources that are each believable on their own.

    Every host dict carries the published keys plus `display`, the extra
    labelled lines the terminal prints and the file does not.
    """
    try:
        version = (root / ".icor-for-life" / "VERSION").read_text(
            encoding="utf-8").strip() or None
    except OSError:
        version = None
    # Flint step 14, 4.1: in mode B the line above is null (the content
    # version lives in the sibling), and in mode A it is the CONTENT version.
    # The team's own version is .mypka/VERSION. Additive: schema unchanged.
    try:
        mypka_version = (root / ".mypka" / "VERSION").read_text(
            encoding="utf-8").strip() or None
    except OSError:
        mypka_version = None

    # `diff` is what fills in b.orphans, so doctor has to run it before it can
    # report a count. Nothing here is written; plan and check call it the same
    # way.
    diff(root, b)

    tests, tests_lines = _red_tests(root, run_tests)
    interp_problems = []
    hosts = []
    for host in HOSTS:
        detected = []
        if (root / FOLDERS[host]).is_dir():
            detected.append("%s/ present" % FOLDERS[host])
        if shutil.which(BINARIES[host]):
            detected.append("`%s` on PATH" % BINARIES[host])
        # `trusted` is "unknown" on every host today, and the note says why.
        # No host writes its trust answer anywhere this script can read, so a
        # "yes" here would be a guess wearing the clothes of a measurement.
        h = {"id": host, "detected": detected, "trusted": "unknown",
             "unsupported": [], "display": []}
        if host == "claude-code":
            n_sk = len([r for r in b.files if r.startswith(".claude/skills/")])
            n_sh = len([r for r in b.files if r.startswith(".claude/agents/")])
            act, _ = settings_diff(root, b)
            state = {"same": "current", "create": "not written yet",
                     "update": "would change on the next apply"}.get(act, "no rule table")
            h["installed"] = ("%d skills, %d generated shims plus %d held by hand, "
                              "hooks in .claude/settings.json (%s)"
                              % (n_sk, n_sh, len(b.keep), state))
            h["trusted_note"] = ("Claude Code asks once per project and stores the "
                                 "answer outside the vault, so this line can only "
                                 "ever say it does not know.")
            h["tested"] = tests["status"]
            h["display"].append(("trusted", "not readable from disk. " + h["trusted_note"]))
            h["display"].append(("unsupported",
                                 "nothing. This is the host every mechanism exists on."))
            if b.hooks_refused:
                h["display"].append(("interpreter", b.hooks_refused))
                interp_problems.append(b.hooks_refused)
            for cmd, ok, line in interpreter_report(getattr(b, "claude_hooks", None)):
                h["display"].append(("interpreter", line))
                if not ok:
                    interp_problems.append(line)
        elif host == "codex":
            n_sh = len([r for r in b.files if r.startswith(".codex/agents/")])
            h["installed"] = ("%d shims (TOML), %d skills via .agents/skills/, "
                              "hooks in .codex/hooks.json" % (n_sh, len(b.links)))
            trust = codex_trust(root)
            body = CODEX_TRUST_TEXT[trust]
            h["trusted"] = trust
            h["trusted_note"] = (body % Path(root).resolve()) if "%s" in body else body
            # The sandbox note travels WITH the flag rather than being retyped
            # in the plugin: two copies of one sentence is two things to keep
            # true, and the one that drifts is always the copy nobody edits.
            h["sandbox"] = True
            h["sandbox_note"] = CODEX_SANDBOX_TEXT
            h["tested"] = tests["status"]
            h["display"].append(("trusted", h["trusted_note"]))
            h["display"].append(("sandbox", CODEX_SANDBOX_TEXT))
            h["display"].append(("unverified",
                                 ".codex/config.toml sets project_doc_max_bytes. "
                                 "OpenAI documents the key and its 32 KiB default, and "
                                 "documents <repo>/.codex/config.toml as a config "
                                 "location, but does not say the key is honoured "
                                 "project-locally. Set the same line in "
                                 "~/.codex/config.toml if a Codex session truncates "
                                 "the entry."))
            for n in b.notes:
                if n.startswith("hooks/codex:"):
                    h["display"].append(("skipped", n.split(":", 1)[1].strip()))
        elif host == "gemini":
            n_sh = len([r for r in b.files if r.startswith(".gemini/agents/")])
            h["installed"] = ("%d shims (Markdown), %d skills via .agents/skills/, "
                              ".gemini/settings.json entry" % (n_sh, len(b.links)))
            h["unsupported"] = ["hooks"]
            h["trusted_note"] = ("Gemini asks the user to approve a skill before its "
                                 "body loads, and workspace-scope skills need /trust.")
            # There is no hook system here at all, so the red-test suite proves
            # nothing about this host and must not borrow the others' green.
            h["tested"] = "unsupported"
            h["display"].append(("unsupported",
                                 "hooks. Gemini CLI has no lifecycle hook system of "
                                 "any kind, so every guard in the rule table is "
                                 "unenforced there. Nothing is written to .gemini for "
                                 "hooks and nothing should be."))
            h["display"].append(("note", h["trusted_note"]))
        else:
            h["installed"] = ("nothing, on purpose. Cursor reads .claude/skills/, "
                              ".claude/agents/ and Claude Code's hooks for "
                              "compatibility, so a fourth copy would be a fourth "
                              "thing to keep true.")
            h["trusted_note"] = ("Cursor reads Claude Code's files, so its trust "
                                 "answer is Claude Code's and is kept outside the vault.")
            h["tested"] = "unsupported"
            h["display"].append(("unsupported", "nothing of its own."))
        hosts.append(h)

    return {
        "generated": datetime.datetime.now(datetime.timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scaffold_version": version,
        "mypka_version": mypka_version,
        "skills": {"count": b.skill_count, "tokens": b.tokens,
                   "budget": MAX_SKILL_TOKENS},
        # `generated` is how many files this generator produces, not how many
        # are currently correct on disk. That question is `check`, and answering
        # it twice in two places is how the two come to disagree.
        "files": {"generated": len(b.files), "hand_kept": len(b.keep),
                  "orphans": len(b.orphans)},
        "tests": tests,
        # A dead interpreter is a problem of doctor's own finding, not one of
        # build's: it must reach harness.json and the exit code, and it must
        # NOT make `apply` refuse to write the skills and shims, which is the
        # one thing still worth having when the guards cannot run.
        "problems": list(b.problems) + interp_problems,
        "notes": list(b.notes),
        "hosts": hosts,
        "display": {"tests": tests_lines},
    }


def harness_doc(report):
    """The published `harness.json`, listed key by key.

    Explicit rather than a filtered copy of the report: this file is a contract
    the Scaffold Check plugin reads, and it must not gain a key because someone
    added one to the report for the terminal.
    """
    return {
        "schema": HARNESS_SCHEMA,
        "generated": report["generated"],
        "scaffold_version": report["scaffold_version"],
        "mypka_version": report["mypka_version"],
        "skills": report["skills"],
        "files": report["files"],
        "tests": report["tests"],
        "problems": report["problems"],
        "notes": report["notes"],
        "hosts": [_harness_host(h) for h in report["hosts"]],
    }


def _harness_host(h):
    """One host row of `harness.json`. `sandbox` and `sandbox_note` appear only
    where a sandbox exists, so "when present" in the plugin is a real test and
    not a check against a key that is always there and usually false."""
    row = {"id": h["id"], "detected": h["detected"], "installed": h["installed"],
           "trusted": h["trusted"], "trusted_note": h["trusted_note"],
           "tested": h["tested"], "unsupported": h["unsupported"]}
    if h.get("sandbox"):
        row["sandbox"] = True
        row["sandbox_note"] = h.get("sandbox_note", "")
    return row


def do_doctor(root, b, out, run_tests=True, write_json=False):
    report = doctor_report(root, b, run_tests=run_tests)
    out("=" * 47)
    out("doctor: %s" % root)
    out("=" * 47)
    for h in report["hosts"]:
        out("")
        out("%s" % h["id"])
        out("  detected    : %s" % (", ".join(h["detected"])
                                    or "no, neither its folder nor its binary is here"))
        out("  installed   : %s" % h["installed"])
        for label, text in h["display"]:
            out("  %-12s: %s" % (label, text))
    out("")
    out("skills      : %d, about %d startup tokens estimated, budget %d"
        % (report["skills"]["count"], report["skills"]["tokens"],
           report["skills"]["budget"]))
    out("hand-kept   : %d shim(s) left alone because they carry instructions the "
        "contract does not" % report["files"]["hand_kept"])
    for i, line in enumerate(report["display"]["tests"]):
        out(("tested      : " if i == 0 else "              ") + line)
    for n in report["notes"]:
        if not n.startswith("hooks/codex:"):
            out("note        : " + n)
    for p in report["problems"]:
        out("PROBLEM     : " + p)
    if write_json:
        path = harness_file(root)
        # GL-1008: never assume the machine layer is there. A vault that
        # arrived on a second device through Obsidian Sync has no dot folders
        # at all, and a write into a missing parent is the usual way this
        # fails on the machine nobody tested on.
        path.parent.mkdir(parents=True, exist_ok=True)
        noteio.write_note(path, json.dumps(harness_doc(report), indent=2,
                                           ensure_ascii=False) + "\n")
        out("")
        out("wrote       : %s" % HARNESS_PATH)
    return 1 if report["problems"] else 0


# ---------------------------------------------------------------------------
# plan, check, main
# ---------------------------------------------------------------------------

def do_plan(root, b, out):
    create, update, same, remove, edited = diff(root, b)
    act, _ = settings_diff(root, b)
    out("=" * 47)
    out("plan: %s" % root)
    out("      nothing below has been written")
    out("=" * 47)
    # One order, `apply_order`, so this list IS the sequence apply will walk.
    # Printed as one run rather than as a CREATE block and an UPDATE block:
    # grouping the verbs is prettier and it hid the only thing about the order
    # that matters, which is that every file is written before any link.
    news = set(create)
    for rel in apply_order(create + update, b):
        if rel in news:
            out("CREATE  %s   <- %s" % (rel, b.sources.get(rel, "?")))
        else:
            mark = "  (HAND-EDITED since it was generated)" if rel in edited else ""
            out("UPDATE  %s   <- %s%s" % (rel, b.sources.get(rel, "?"), mark))
    for rel, why in remove:
        out("REMOVE  %s   (%s)" % (rel, why))
    if act in ("create", "update"):
        out("%s  .claude/settings.json   <- hooks-rules.json (the `hooks` key only; "
            "every other key kept)" % act.upper())
    for rel, reason in b.keep:
        out("KEEP    %s   hand-written, %s" % (rel, reason))
    for rel in b.orphans:
        out("ORPHAN  %s   generated, no longer produced, source still on disk. "
            "Not removed: the rule is remove-when-the-source-is-gone." % rel)
    out("-" * 47)
    out("%d create, %d update, %d already current, %d remove, %d kept by hand, "
        "%d orphan" % (len(create), len(update), len(same), len(remove),
                       len(b.keep), len(b.orphans)))
    out("skills %d (about %d startup tokens, budget %d), shims %d agents x 3 hosts, "
        "hook configs %d" % (b.skill_count, b.tokens, MAX_SKILL_TOKENS,
                             len([r for r in b.files if r.startswith(".claude/agents/")])
                             + len(b.keep),
                             (1 if hasattr(b, "claude_hooks") else 0)
                             + (1 if ".codex/hooks.json" in b.files else 0)))
    for n in b.notes:
        out("note: " + n)
    for p in b.problems:
        out("PROBLEM: " + p)
    return 1 if b.problems else 0


def do_check(root, b, out):
    create, update, same, remove, edited = diff(root, b)
    act, _ = settings_diff(root, b)
    fails = []
    for rel in create:
        fails.append("missing: %s" % rel)
    for rel in update:
        if rel in edited:
            fails.append("hand-edited: %s carries a generated header and its body "
                         "no longer matches the hash in it" % rel)
        else:
            fails.append("stale: %s would change on the next apply" % rel)
    for rel, why in remove:
        fails.append("stale: %s should be gone (%s)" % (rel, why))
    if act in ("create", "update"):
        fails.append("stale: .claude/settings.json hooks key would change on the "
                     "next apply")
    # a generated file that was hand-edited but whose text happens to round-trip
    for rel in same:
        p = root / rel
        if p.is_file() and hand_edited(p):
            fails.append("hand-edited: %s" % rel)
    for p in b.problems:
        fails.append(p)
    if fails:
        for f in fails:
            out("FAIL " + f)
        out("FAIL check: %d finding(s). Run `scaffold-init.py apply`, or repair "
            "the source and re-run." % len(fails))
        return 1
    n_files, n_links = generated_counts(b, same)
    out("OK check: a second apply would change nothing, %d generated file(s) still "
        "match the hash in their header, %d host link(s) in place, %d shim(s) held "
        "by hand, %d orphan(s)"
        % (n_files, n_links, len(b.keep), len(b.orphans)))
    out("What this does not prove: that any host reads any of it, that a hook "
        "fires, or that a skill gets selected. It proves these bytes are the "
        "bytes the sources produce.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate the harness layer (skills, agent shims, hook "
                    "configs, host pointers) from this vault's own frontmatter.")
    ap.add_argument("verb", choices=("plan", "apply", "check", "doctor"))
    ap.add_argument("--root", default=None,
                    help="vault root; by default the first folder above this "
                         "script holding AGENTS.md next to '06 AI Team/'")
    ap.add_argument("--no-tests", action="store_true",
                    help="doctor: do not run run-red-tests.py")
    ap.add_argument("--json", action="store_true",
                    help="doctor: also write %s, which the Scaffold Check "
                         "plugin reads. The text report is still printed."
                         % HARNESS_PATH)
    a = ap.parse_args(argv)
    root = find_root(a.root) if a.root else find_root()
    lines = []

    def out(s):
        lines.append(s)
        print(s)

    b = build(root)
    if a.verb == "plan":
        rc = do_plan(root, b, out)
    elif a.verb == "apply":
        if b.problems:
            for p in b.problems:
                out("FAIL " + p)
            out("FAIL apply refused: fix the source and re-run. Nothing written.")
            return 1
        rc = 1 if do_apply(root, b, out)[4] else 0
    elif a.verb == "check":
        rc = do_check(root, b, out)
    else:
        rc = do_doctor(root, b, out, run_tests=not a.no_tests, write_json=a.json)
    return rc


if __name__ == "__main__":
    sys.exit(main())
