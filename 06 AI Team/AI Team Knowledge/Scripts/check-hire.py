#!/usr/bin/env python3
"""check-hire.py - refuse an incomplete hire.

Mack, 2026-09-14. Row 9 of the 2026-09-14 skills and hooks audit
(the 2026-09-14 scaffold skills and hooks audit report), to the validator
spec in Nolan's hire output contract, section 5. Same bytes in the private
vault and in the public ICOR for Life Scaffold: the folder is detected at
runtime by `vault_is_public()` (GL-025 present means private, whatever the
manifest says), so one file serves both shapes. new-agent.py asks the same
function.

WHY IT EXISTS
-------------
A hire used to be prose plus one pointer file, and nothing checked that the
hire was complete. A shim pointing at a path that does not exist fails
silently at dispatch time, months later, as "the agent did not answer".
SOP-001 step 7b and SOP-1007 step 7b now gate the announcement on this
script exiting 0.

THE 22 CHECKS
-------------
  1  folder      06 AI Team/Agents/<Name>/ exists, one Title-case word, no role suffix
  2  frontmatter required contract fields present, no forbidden ones, parses
  3  id          myicor_id valid and unique (relayed from mint-agent-ids.py --check)
  4  bio         <Name>.md exists, type agent-bio, links AGENT.md
  5  avatar      exists at this folder's convention, real PNG, square, and
                 not a placeholder (WARN, never OK, when it is one)
  6  journal     Journal/ exists and is not empty
  7  shim        .claude/agents/<slug>.md exists, name equals slug equals folder
  8  shim-desc   description present and opens with the role phrase from the contract
  9  shim-points shim body names the contract path, and that path exists
 10  shim-size   shim body under the line cap and carries no pasted contract
 11  shim-tools  tools come from the allowlist; private-data rule relayed
 12  index       agent-index row with [[<Name>]] and the slug, slug unique
 13  cheatsheet  (private) Larry's routing cheatsheet names the specialist
 14  skills      every skill with this slug's prefix passes skill-doctor.py
 15  skill-oblig the hire workup's `skills:` list matches what is on disk
 16  sop-scripts every [SCRIPT] step in this agent's SOPs names a script that exists
 17  red-tests   every guard this agent's SOPs or gates name has a red case
 18  gates       every owns_gates entry has a rule, a script and a Vex review
 19  wikilinks   links in the contract, the bio and the skills resolve
 20  dashes      no em dash and no en dash in the contract, bio, shim or skills
 21  brief       the Pax research brief the contract links exists, or a waiver does
 22  pack        (public) a pack-installed agent has a shim, or "activation incomplete"

A check can also print WARN. WARN is never green: it means the evidence this
check needs is not on disk yet (no hire workup, for instance), so the check
could not be answered either way. It does not fail the run, and it is counted
and printed separately so it cannot be read as a pass.

WHAT THIS DOES NOT PROVE (GL-081 shape, read before citing a green run)
----------------------------------------------------------------------
1. **It does not prove the specialist works.** It checks that the files a
   hire ships exist and agree with each other. Whether the contract is any
   good is a judgement, and no script has taste.
2. **It does not prove the host will dispatch the agent.** That is a property
   of the running host, not of the files. A green shim check means the file is
   shaped right, nothing more.
3. **A WARN is not a pass, and neither is a SKIP.** Both are printed with
   their reason and counted apart from the greens.

    check-hire.py <Name>              one agent
    check-hire.py --all               every dispatchable agent in this folder
    check-hire.py --self-test         plant every defect, watch every check go red
    check-hire.py --json              machine readable, works with any of the above

Exit 0 = no FAIL lines. Exit 1 = at least one FAIL, or a self-test that saw a
planted defect stay green.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

# `--self-test` copies helper scripts INTO a fixture vault and then runs them
# out of it, so a child that imports a sibling by path would have stock CPython
# write `__pycache__/*.pyc` into the fixture. Nothing here decodes a fixture
# tree today, but the same shape crashed run-red-tests.py in 1.24.0's CI, so the
# write is stopped at the source rather than worked around downstream.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# Spawned-child environment: never write bytecode into a tree we did not build
# for bytecode. Used by every spawner below that runs a script out of `root`.
CHILD_ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

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
SCRIPTS_REL = "06 AI Team/AI Team Knowledge/Scripts"
SKILLS_REL = "06 AI Team/AI Team Knowledge/Skills"
SOPS_REL = "06 AI Team/AI Team Knowledge/SOPs"
# The hire workup lives in the `wip` concept (GL-1013), resolved, never a
# room path: in mode B it is in the sibling content folder. Where no source
# serves wip, the workup is a task attachment (ruling k4v); find_workup reads
# both. Ada step 8, F2.
SHIM_REL = ".claude/agents"
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)

SHIM_BODY_LINE_CAP = 80
NAME_RE = re.compile(r"^[A-Z][a-zA-Z]+$")

PRIVATE_REQUIRED = ("myicor_id", "agent_version", "agent_version_date",
                    "agent_status", "agent_compatibility", "owner",
                    "routing_description")
PUBLIC_REQUIRED = ("type", "myicor_id", "name", "role", "routing_description")
FORBIDDEN_PREFIXES = ("last_updated",)

# The tool names a Claude Code shim may name. Anything else is a typo or an
# invention, and either way the host silently drops the whole line. An
# `mcp__<server>__*` pattern is always allowed; the private-data rule on those
# is check-agent-shim-mcp.py's job, not this list's.
TOOL_ALLOWLIST = {
    "Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "Glob", "Grep",
    "Bash", "BashOutput", "KillShell", "WebFetch", "WebSearch", "Task",
    "Agent", "TodoWrite", "SlashCommand", "ExitPlanMode", "Skill",
    "ToolSearch", "Monitor", "SendMessage", "TaskStop", "Artifact",
    "EnterWorktree", "ExitWorktree", "AskUserQuestion", "ListMcpResources",
    "ReadMcpResource", "All tools", "*",
}

RETIRED_HEADINGS = ("retired", "deliberate no-hire", "roster history",
                    "adding a new agent")


# ---------------------------------------------------------------------------
# small readers. Stdlib only: a member's python3 has no PyYAML.
# ---------------------------------------------------------------------------
def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError):
        return ""


def split_frontmatter(text):
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def parse_frontmatter(fm_text):
    """Top-level keys of a small YAML subset: scalars, folded continuation
    lines, block lists and inline `[a, b]` lists. Returns (dict, error) where
    error is a string when the block cannot be read at all."""
    out = {}
    key = None
    in_list = False
    if "\t" in fm_text:
        return out, "the frontmatter contains a tab, which YAML forbids for indentation"
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        if stripped.startswith("- ") and in_list and key:
            val = stripped[2:].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            out[key].append(val)
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            key = m.group(1)
            val = m.group(2).strip()
            if val == "":
                out[key] = []
                in_list = True
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                out[key] = [v.strip().strip("\"'") for v in inner.split(",") if v.strip()]
                in_list = False
            else:
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                out[key] = val
                in_list = False
        elif key is not None and raw.startswith((" ", "\t")):
            if isinstance(out.get(key), list):
                continue
            out[key] = (str(out.get(key, "")) + " " + raw.strip()).strip()
    return out, None


def png_size(path):
    """(width, height) from the PNG header, or None when it is not a PNG."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
    except (OSError, IOError):
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


# A PLACEHOLDER IS NOT AN AVATAR (pilot C finding F6). Both pilot models drew
# one to turn check 5 green: a teal square with a letter in it, and a flat
# 1254x1254 fill. Check 5 accepted both, because it only asked "is this a
# square PNG". A green reachable without the thing being true is the exact
# defect GL-1005 rule 4 names, and this one had two models find it in one
# afternoon. The three shapes below are what a placeholder looks like from
# outside: it says so in its name, it is too small to be a portrait, or it is
# one flat colour. None of them proves the image is GOOD; they prove it is not
# yet a picture of anybody, which is all a validator can honestly claim.
MIN_AVATAR_PX = 128


def png_is_solid(path):
    """True when every pixel is the same colour. None when it cannot be read.

    Reads the IDAT stream and refuses to guess: an interlaced PNG, a palette,
    or anything it cannot unfilter comes back None and the caller says nothing
    rather than something wrong."""
    try:
        data = open(path, "rb").read()
    except (OSError, IOError):
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 33:
        return None
    w, h, depth, colour = struct.unpack(">IIBB", data[16:26])
    interlace = data[28]
    if depth != 8 or interlace != 0 or colour not in (0, 2, 4, 6):
        return None
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colour]
    idat, i = b"", 8
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        if tag == b"IDAT":
            idat += data[i + 8:i + 8 + ln]
        i += 12 + ln
    try:
        raw = zlib.decompress(idat)
    except zlib.error:
        return None
    stride = w * channels
    if len(raw) < h * (stride + 1):
        return None
    first = None
    for y in range(h):
        row = raw[y * (stride + 1):(y + 1) * (stride + 1)]
        if row[0] not in (0, 2):        # None or Up: anything else needs a real decoder
            return None
        line = row[1:]
        if row[0] == 2:                 # Up filter: all-zero deltas repeat the row above
            if any(line):
                return False
            continue
        px = line[:channels]
        if line != px * w:
            return False
        if first is None:
            first = px
        elif px != first:
            return False
    return True


# THE HIRING MARKER (pilot C finding F1). `new-agent.py` drops
# `06 AI Team/Agents/<Name>/.hiring` and `write-guard.py` stands down on that
# one contract while it is fresh. This script is the other end: a green run
# deletes it, and a marker still lying there after 24 hours is residue that
# reads like an open door and is not one.
HIRING_MARKER = ".hiring"
HIRING_MAX_AGE_H = 24


def hiring_age_hours(marker):
    """Hours since the hire started, or None when the file says nothing."""
    try:
        doc = json.loads(marker.read_text(encoding="utf-8"))
        stamp = str(doc.get("started") or "").replace("Z", "+00:00")
        started = datetime.fromisoformat(stamp)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
    except Exception:
        try:
            started = datetime.fromtimestamp(marker.stat().st_mtime, timezone.utc)
        except OSError:
            return None
    return (datetime.now(timezone.utc) - started).total_seconds() / 3600.0


def avatar_is_placeholder(path, size):
    """(True, why) when this file is a stand-in rather than a portrait."""
    name = path.name.lower()
    if "placeholder" in name or "_placeholder" in path.parent.name.lower():
        return True, "the file name says so"
    if (path.parent / (path.stem + ".placeholder")).is_file():
        return True, "a .placeholder sidecar sits beside it"
    if size and (size[0] < MIN_AVATAR_PX or size[1] < MIN_AVATAR_PX):
        return True, ("%dx%d is below the %dpx a roster portrait needs"
                      % (size[0], size[1], MIN_AVATAR_PX))
    if png_is_solid(path) is True:
        return True, "every pixel is the same colour"
    return False, ""


def write_png(path, w, h, solid=True):
    """Smallest legal PNG of the given size. Used by the self-test only.

    `solid=False` varies the pixels, because the clean fixture's avatar has to
    be something check 5 accepts as a picture rather than a stand-in."""
    if solid:
        raw = b"".join(b"\x00" + b"\xff\xff\xff" * w for _ in range(h))
    else:
        raw = b"".join(b"\x00" + bytes(bytearray(
            ((x * 7 + y * 13) % 256, (x * 3) % 256, (y * 5) % 256)[c]
            for x in range(w) for c in range(3))) for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)


# ---------------------------------------------------------------------------
# the vault, read once per run
# ---------------------------------------------------------------------------
def vault_is_public(root):
    """True for the public ICOR for Life Scaffold, False for the private vault.

    THE ONE ANSWER. new-agent.py imports this function rather than keeping a
    rule of its own (task tsk-2026-09-17-006: the two scripts used to disagree,
    and the hire script wrote the public skeleton into a private vault).

    The manifest alone cannot answer it: a private vault carries a copy of the
    installed Scaffold's `.icor-for-life/`, so `manifest.json` is present in
    both. GL-025 is the discriminator, because the private contract schema
    exists only where it governs.
    """
    root = Path(root)
    gl025 = (root / "06 AI Team/AI Team Knowledge/Guidelines"
             / "GL-025-agent-contract-schema.md").is_file()
    manifest = (root / ".icor-for-life" / "manifest.json").is_file()
    return (not gl025) and (manifest or (root / AGENTS_REL / "Agent 01").is_dir())


class Vault(object):
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.public = vault_is_public(self.root)
        self.agents_dir = self.root / AGENTS_REL
        self.scripts_dir = self.root / SCRIPTS_REL
        self.index_text = read(self.agents_dir / "agent-index.md")
        self.larry_text = read(self.agents_dir / "Larry" / "AGENT.md")
        self.hooks_rules = self._hooks_rules()
        self.red_tests_text = read(self.scripts_dir / "run-red-tests.py")
        self._note_index = None
        self._cross = None
        self._mint = None
        self._shim_mcp = None
        self._sops = None

    # --- lazily built indexes -------------------------------------------
    def cross_side(self):
        """Mode B: the content source's folders that team contracts and SOPs
        link into (its guidelines, its templates, its scripts), as
        (source_root, folder) pairs, found through the resolver, never as a
        room literal. Mode A, or no binding: none, because those folders are
        already inside self.root. Plan step 12, Ada N1: until then a mode B
        check-hire --all failed 6 lines on links and scripts that exist, one
        folder over."""
        if self._cross is None:
            self._cross = []
            try:
                b = resolver.load(self.root)
                src = resolver.tool_source(b)
            except resolver.ResolveError:
                b, src = None, None
            if src is not None and os.path.realpath(str(src.root)) != os.path.realpath(str(self.root)):
                dirs = []
                for concept in ("life_guidelines", "templates"):
                    try:
                        dirs.append(resolver.resolve_path(concept, bindings=b))
                    except resolver.ResolveError:
                        pass
                try:
                    dirs.append(resolver.resolve_tool("life-snapshot", bindings=b).parent)
                except resolver.ResolveError:
                    pass
                self._cross = [(Path(src.root), Path(d)) for d in dirs if Path(d).is_dir()]
        return self._cross

    def cross_scripts(self):
        """The content source's script folders (mode B), for check 16."""
        return [d for _root, d in self.cross_side() if d.name == Path(SCRIPTS_REL).name]

    def note_index(self):
        if self._note_index is None:
            stems, rels = set(), set()
            skip = {".git", ".obsidian", "node_modules", "__pycache__", ".venv"}
            for p in self.root.rglob("*"):
                if not p.is_file():
                    continue
                if any(part in skip for part in p.parts):
                    continue
                rel = p.relative_to(self.root).as_posix()
                stems.add(p.stem.lower())
                stems.add(p.name.lower())   # an embed names the file with its extension
                rels.add(rel.lower())
                if rel.lower().endswith(".md"):
                    rels.add(rel[:-3].lower())
            # Mode B: the hire workup and its brief live in the SIBLING content
            # folder, so a `[[<wip room>/...hire/research]]` link resolves
            # there. Only the wip homes are indexed, relative to their source
            # root, never the whole content folder (F2, Ada step 8).
            try:
                src_root = resolver.source_root("wip", bindings=resolver.load(self.root))
            except resolver.ResolveError:
                src_root = None
            if src_root is not None and os.path.realpath(str(src_root)) != os.path.realpath(str(self.root)):
                for home in workup_homes(self.root)[:1]:
                    for p in home.rglob("*"):
                        if not p.is_file() or any(part in skip for part in p.parts):
                            continue
                        rel = os.path.relpath(str(p), os.path.realpath(str(src_root))).replace(os.sep, "/")
                        stems.add(p.stem.lower())
                        stems.add(p.name.lower())
                        rels.add(rel.lower())
                        if rel.lower().endswith(".md"):
                            rels.add(rel[:-3].lower())
            for src_root, folder in self.cross_side():
                for p in folder.rglob("*"):
                    if not p.is_file() or any(part in skip for part in p.parts):
                        continue
                    rel = os.path.relpath(str(p), str(src_root)).replace(os.sep, "/")
                    stems.add(p.stem.lower())
                    stems.add(p.name.lower())
                    rels.add(rel.lower())
                    if rel.lower().endswith(".md"):
                        rels.add(rel[:-3].lower())
            self._note_index = (stems, rels)
        return self._note_index

    def mint_result(self):
        if self._mint is None:
            script = self.scripts_dir / "mint-agent-ids.py"
            if not script.is_file():
                self._mint = (None, "mint-agent-ids.py is not in Scripts/")
            else:
                r = subprocess.run([sys.executable, str(script), "--check",
                                    "--root", str(self.root)],
                                   capture_output=True, text=True, env=CHILD_ENV)
                self._mint = (r.returncode, (r.stdout or "") + (r.stderr or ""))
        return self._mint

    def shim_mcp_result(self):
        if self._shim_mcp is None:
            script = self.scripts_dir / "check-agent-shim-mcp.py"
            if not script.is_file():
                self._shim_mcp = (None, "check-agent-shim-mcp.py is not in Scripts/")
            else:
                r = subprocess.run([sys.executable, str(script), str(self.root / SHIM_REL)],
                                   capture_output=True, text=True, env=CHILD_ENV)
                self._shim_mcp = (r.returncode, (r.stdout or "") + (r.stderr or ""))
        return self._shim_mcp

    def sops(self):
        """[(path, owner_lower, text)] for every SOP and Workstream."""
        if self._sops is None:
            out = []
            for sub in ("SOPs", "Workstreams"):
                d = self.root / "06 AI Team/AI Team Knowledge" / sub
                if not d.is_dir():
                    continue
                for p in sorted(d.glob("*.md")):
                    if p.name.startswith("_"):
                        continue
                    text = read(p)
                    fm, body = split_frontmatter(text)
                    keys, _ = parse_frontmatter(fm)
                    owner = str(keys.get("owner", "")).strip().lower()
                    if not owner:
                        m = re.search(r"\*\*Default owner:\*\*\s*([A-Za-z]+)", body)
                        if m:
                            owner = m.group(1).lower()
                    out.append((p, owner, text))
            self._sops = out
        return self._sops

    def _hooks_rules(self):
        p = self.scripts_dir / "hooks-rules.json"
        if not p.is_file():
            return None
        try:
            return json.loads(read(p))
        except ValueError:
            return None

    # --- roster ----------------------------------------------------------
    def dispatchable(self):
        """Agent folders a host can dispatch: every folder under Agents/
        except Larry (the main-session identity, never a subagent), the
        hiring template, and anything the index lists as retired."""
        out = []
        if not self.agents_dir.is_dir():
            return out
        retired = self.retired_names()
        for p in sorted(self.agents_dir.iterdir()):
            if not p.is_dir() or p.name.startswith("_") or p.name.startswith("."):
                continue
            if p.name in ("Larry", "Agent 01"):
                continue
            if p.name in retired:
                continue
            out.append(p.name)
        return out

    def retired_names(self):
        """Only the FIRST cell of each row in the Retired table. The other
        cells name who absorbed the lane, and Felix reading as retired because
        Flow went to him is exactly the kind of quiet wrong answer a roster
        check must not produce."""
        names = set()
        m = re.search(r"\n## Retired\b(.*?)(?=\n## |\Z)", self.index_text, re.S)
        if not m:
            return names
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            first = line.strip("|").split("|")[0]
            hit = re.search(r"\[\[([^\]|]+)", first)
            if hit:
                names.add(hit.group(1).split("/")[-1].strip())
        return names

    def index_sections(self):
        """[(heading_lower, section_text)] for agent-index.md. The public
        Scaffold's index is one flat table with no `## ` headings at all, so
        a file with none is read as a single section rather than as zero."""
        out = []
        parts = re.split(r"\n## ", "\n" + self.index_text)
        for chunk in parts[1:]:
            head, _, rest = chunk.partition("\n")
            out.append((head.strip().lower(), rest))
        if not out and self.index_text.strip():
            out.append(("roster", self.index_text))
        return out

    def slug_of(self, name):
        """The slug the index gives this agent, else the folder lowercased."""
        for head, body in self.index_sections():
            if any(h in head for h in RETIRED_HEADINGS):
                continue
            for line in body.splitlines():
                if re.search(r"\[\[%s(?:\||\])" % re.escape(name), line):
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    if len(cells) >= 2 and re.match(r"^[a-z0-9-]+$", cells[1]):
                        return cells[1]
        return name.lower()


# ---------------------------------------------------------------------------
# the checks
# ---------------------------------------------------------------------------
class Result(object):
    def __init__(self):
        self.rows = []

    def add(self, num, status, label, message):
        self.rows.append({"n": num, "status": status, "check": label, "message": message})

    def ok(self, n, label, msg):
        self.add(n, "OK", label, msg)

    def fail(self, n, label, msg):
        self.add(n, "FAIL", label, msg)

    def warn(self, n, label, msg):
        self.add(n, "WARN", label, msg)

    def skip(self, n, label, msg):
        self.add(n, "SKIP", label, msg)

    @property
    def fails(self):
        return [r for r in self.rows if r["status"] == "FAIL"]


# Placeholder targets and code spans, mirroring find-unresolvable-wikilinks.py
# so the two tools agree about what a link even is. A `[[<slug>]]` in a
# template and a `[[entry-1]]` inside backticks are examples, not links, and a
# check that reds on an example teaches people to ignore it.
PLACEHOLDER_TOKENS = {"slug", "person-slug", "entity", "wikilink", "name",
                      "topic-slug", "project-slug", "goal-slug", "habit-slug",
                      "doc-slug", "target-slug", "old-slug", "new-slug",
                      "entity-slug", "wikilink-to-target", "..."}


def is_placeholder(target):
    if target in PLACEHOLDER_TOKENS:
        return True
    return ("<" in target or ">" in target or "{" in target or "}" in target
            or "%" in target)


def wikilinks(text):
    """Every link outside a fenced block and outside an inline code span."""
    out = []
    in_fence = False
    for raw in text.splitlines():
        s = raw.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = re.sub(r"`[^`]*`", " ", raw)
        for m in re.finditer(r"\[\[([^\]]+)\]\]", line):
            target = m.group(1).strip().lstrip("!").strip()
            if is_placeholder(target):
                continue
            out.append(target)
    return out


def link_resolves(vault, link):
    target = link.split("|")[0].split("#")[0].strip()
    if not target:
        return True
    stems, rels = vault.note_index()
    t = target.lower()
    if t in stems or t in rels or (t + ".md") in rels:
        return True
    return t.split("/")[-1] in stems


def check_agent(vault, name):
    res = Result()
    root = vault.root
    d = vault.agents_dir / name
    slug = vault.slug_of(name)

    # 1. folder
    if not d.is_dir():
        res.fail(1, "folder", "06 AI Team/Agents/%s/ does not exist" % name)
        return res, slug
    if " - " in name or not NAME_RE.match(name):
        res.fail(1, "folder", "the folder is named `%s`; a contract folder is one Title-case "
                 "word with no role suffix" % name)
    else:
        res.ok(1, "folder", "06 AI Team/Agents/%s/" % name)

    contract_path = d / "AGENT.md"
    contract = read(contract_path)
    fm_text, body = split_frontmatter(contract)
    keys, fm_err = parse_frontmatter(fm_text)

    # 2. frontmatter
    required = PUBLIC_REQUIRED if vault.public else PRIVATE_REQUIRED
    if not contract:
        res.fail(2, "frontmatter", "%s/AGENT.md is missing or empty" % name)
    elif fm_err:
        res.fail(2, "frontmatter", "%s/AGENT.md frontmatter does not parse: %s" % (name, fm_err))
    else:
        missing = [k for k in required if not keys.get(k)]
        forbidden = [k for k in keys if k.startswith(FORBIDDEN_PREFIXES)]
        if missing:
            res.fail(2, "frontmatter", "%s/AGENT.md is missing required field(s): %s"
                     % (name, ", ".join(missing)))
        elif forbidden:
            res.fail(2, "frontmatter", "%s/AGENT.md carries %s, which belongs to Guideline files "
                     "and never to a contract" % (name, ", ".join(forbidden)))
        else:
            res.ok(2, "frontmatter", "%d required fields present" % len(required))

    # 3. id, relayed
    code, out = vault.mint_result()
    if code is None:
        res.warn(3, "id", out)
    elif code == 0:
        res.ok(3, "id", "mint-agent-ids.py --check passed for the whole roster")
    else:
        mine = [ln for ln in out.splitlines() if name.lower() in ln.lower()]
        if mine:
            res.fail(3, "id", "mint-agent-ids.py --check: %s" % mine[0].strip())
        else:
            first = out.strip().splitlines()[0] if out.strip() else "no output"
            res.warn(3, "id", "mint-agent-ids.py --check failed, but not on this agent: %s" % first)

    # 4. bio card
    bio_path = d / (name + ".md")
    # macOS is case insensitive, so `testy.md` still answers to `Testy.md` here
    # and the same file breaks on a case sensitive host. Compare the real
    # directory entries, not just existence.
    entries = [p.name for p in d.iterdir() if p.is_file()] if d.is_dir() else []
    exact = (name + ".md") in entries
    nearly = [e for e in entries if e.lower() == (name + ".md").lower()]
    if not bio_path.is_file():
        res.fail(4, "bio", "%s/%s.md is missing; that is the card a bare [[%s]] resolves to"
                 % (name, name, name))
    elif not exact and nearly:
        res.fail(4, "bio", "the bio card is named `%s`; it must be `%s.md` exactly, or the bare "
                 "[[%s]] link breaks on a case sensitive host" % (nearly[0], name, name))
    else:
        bio_text = read(bio_path)
        bfm, bbody = split_frontmatter(bio_text)
        bkeys, _ = parse_frontmatter(bfm)
        problems = []
        if str(bkeys.get("type", "")).strip() != "agent-bio":
            problems.append("type is not agent-bio")
        if str(bkeys.get("agent", "")).strip() != name:
            problems.append("agent is not %s" % name)
        if "AGENT.md" not in bio_text and "AGENT]]" not in bio_text:
            problems.append("the body does not link AGENT.md")
        if problems:
            res.fail(4, "bio", "%s.md: %s" % (name, "; ".join(problems)))
        else:
            res.ok(4, "bio", "%s.md" % name)

    # 5. avatar
    if vault.public:
        avatar = root / "06 AI Team/AI Team Knowledge/Avatars" / (name.lower() + ".png")
    else:
        avatar = d / "avatar.png"
    rel_av = avatar.relative_to(root).as_posix()
    if not avatar.is_file():
        res.fail(5, "avatar", "%s is missing; a hire without an avatar is incomplete" % rel_av)
    else:
        size = png_size(avatar)
        if size is None:
            res.fail(5, "avatar", "%s is not a PNG" % rel_av)
        elif size[0] != size[1]:
            res.fail(5, "avatar", "%s is %dx%d; the roster wants a square"
                     % (rel_av, size[0], size[1]))
        else:
            placeholder, why = avatar_is_placeholder(avatar, size)
            if placeholder:
                res.warn(5, "avatar", "%s is a placeholder (%s), not a portrait. "
                         "Pixel still owes the real one; a drawn stand-in turns "
                         "this check green without the thing being true"
                         % (rel_av, why))
            else:
                res.ok(5, "avatar", "%s, %dx%d" % (rel_av, size[0], size[1]))

    # 6. journal
    jdir = d / "Journal"
    if not jdir.is_dir() and (d / "journal").is_dir():
        jdir = d / "journal"
    if not jdir.is_dir():
        res.fail(6, "journal", "%s/Journal/ does not exist" % name)
    elif not any(p.is_file() for p in jdir.iterdir()):
        res.fail(6, "journal", "%s/Journal/ is empty. Version control drops an empty folder, so "
                 "the first entry is the hire itself" % name)
    else:
        res.ok(6, "journal", "%s/%s/ holds %d file(s)"
               % (name, jdir.name, len([p for p in jdir.iterdir() if p.is_file()])))

    # 7 to 11. the shim
    shim_path = root / SHIM_REL / (slug + ".md")
    # The Claude Code surface is the `.claude/` folder. There is no root
    # CLAUDE.md to look for: AGENTS.md is the only entry file (2026-09-24).
    has_host = (root / ".claude").is_dir()
    shim_text = read(shim_path)
    if not has_host:
        for n in (7, 8, 9, 10, 11):
            res.skip(n, "shim", "this folder has no Claude Code surface, so no shim is required")
    elif not shim_text:
        res.fail(7, "shim", ".claude/agents/%s.md is missing, so Larry cannot dispatch %s"
                 % (slug, name))
        for n in (8, 9, 10, 11):
            res.skip(n, "shim", "no shim to check")
    else:
        sfm, sbody = split_frontmatter(shim_text)
        skeys, _ = parse_frontmatter(sfm)
        declared = str(skeys.get("name", "")).strip()
        if declared != slug:
            res.fail(7, "shim", ".claude/agents/%s.md declares name `%s`; name, slug and folder "
                     "lowercased must be the same word" % (slug, declared))
        else:
            res.ok(7, "shim", ".claude/agents/%s.md" % slug)

        # 8. description opens with the role phrase
        desc = str(skeys.get("description", "")).strip()
        opener = str(keys.get("routing_description", "")).strip()
        source = "routing_description"
        if not opener and vault.public:
            opener, source = str(keys.get("role", "")).strip(), "role"

        def squash(s):
            return re.sub(r"[^a-z0-9]", "", s.lower())

        if not desc:
            res.fail(8, "shim-desc", ".claude/agents/%s.md has an empty description; that is the "
                     "text the host reads when deciding to dispatch" % slug)
        elif not opener:
            res.warn(8, "shim-desc", "the contract carries no %s to compare the shim against"
                     % source)
        else:
            a, b = squash(desc), squash(opener)
            n = min(30, len(a), len(b))
            if n and a[:n] == b[:n]:
                res.ok(8, "shim-desc", "opens with the contract's %s" % source)
            else:
                res.fail(8, "shim-desc", ".claude/agents/%s.md description does not open with the "
                         "contract's %s; the shim is rendered from the contract, so edit the "
                         "contract and regenerate" % (slug, source))

        # 9. the pointer
        want = "%s/%s/AGENT.md" % (AGENTS_REL, name)
        if want not in shim_text:
            res.fail(9, "shim-points", ".claude/agents/%s.md does not name `%s`; a shim that "
                     "points at the wrong path fails silently at dispatch time" % (slug, want))
        elif not contract_path.is_file():
            res.fail(9, "shim-points", "the shim names `%s` and that file does not exist" % want)
        else:
            res.ok(9, "shim-points", "names the contract, and it is on disk")

        # 10. size and no pasted contract
        blines = [ln for ln in sbody.splitlines() if ln.strip()]
        if "myicor_id:" in shim_text:
            res.fail(10, "shim-size", ".claude/agents/%s.md carries a `myicor_id:` line, so a "
                     "contract was pasted into the shim" % slug)
        elif len(blines) > SHIM_BODY_LINE_CAP:
            res.fail(10, "shim-size", ".claude/agents/%s.md body is %d lines; the cap is %d. The "
                     "shim is a pointer, the contract is the body"
                     % (slug, len(blines), SHIM_BODY_LINE_CAP))
        else:
            res.ok(10, "shim-size", "%d body lines, no pasted contract" % len(blines))

        # 11. tools
        tools_raw = skeys.get("tools", "")
        bad = []
        if isinstance(tools_raw, list):
            tools = [t.strip() for t in tools_raw if str(t).strip()]
        else:
            tools = [t.strip() for t in str(tools_raw).split(",") if t.strip()]
        for t in tools:
            if t in TOOL_ALLOWLIST:
                continue
            if re.match(r"^mcp__[\w.-]+__[\w.*-]+$", t):
                continue
            bad.append(t)
        mcode, mout = vault.shim_mcp_result()
        if bad:
            res.fail(11, "shim-tools", ".claude/agents/%s.md names tool(s) no host knows: %s"
                     % (slug, ", ".join(bad)))
        elif mcode is None:
            res.warn(11, "shim-tools", "tools are legal; %s" % mout)
        elif mcode != 0 and ("%s.md" % slug) in mout:
            first = (mout.strip().splitlines() or ["violation"])[0]
            res.fail(11, "shim-tools", "check-agent-shim-mcp.py: %s" % first)
        else:
            res.ok(11, "shim-tools", ("%d tool entr(ies), all legal" % len(tools)) if tools
                   else "no tools line, so the host default applies")

    # 12. agent-index row
    rows = []
    for head, sbody2 in vault.index_sections():
        if any(h in head for h in RETIRED_HEADINGS):
            continue
        for line in sbody2.splitlines():
            if re.search(r"\[\[%s(?:\||\])" % re.escape(name), line) and line.strip().startswith("|"):
                rows.append((head, line))
    if not rows:
        res.fail(12, "index", "agent-index.md has no live row for [[%s]]; Larry's routing skips "
                 "an unlisted specialist" % name)
    else:
        slug_cells = re.findall(r"^\|[^|]+\|\s*([a-z0-9-]+)\s*\|", vault.index_text, re.M)
        if not vault.public and slug_cells.count(slug) > 1:
            res.fail(12, "index", "the slug `%s` appears on %d rows; a slug is a dispatch key and "
                     "must be unique" % (slug, slug_cells.count(slug)))
        else:
            res.ok(12, "index", "row in section `%s`" % rows[0][0])

    # 13. Larry cheatsheet, private only
    if vault.public:
        res.skip(13, "cheatsheet", "the Scaffold routes from agent-index alone")
    else:
        m = re.search(r"\n## Routing cheatsheet\b(.*?)(?=\n## |\Z)", vault.larry_text, re.S)
        if not m:
            res.fail(13, "cheatsheet", "Larry/AGENT.md has no `## Routing cheatsheet` section")
        elif re.search(r"\b%s\b" % re.escape(name), m.group(1)):
            res.ok(13, "cheatsheet", "named in Larry's routing cheatsheet")
        else:
            res.fail(13, "cheatsheet", "Larry's routing cheatsheet does not name %s, so Larry "
                     "has no cue that routes there" % name)

    # 14 and 15. skills
    skill_dirs = []
    for base in (root / SKILLS_REL, root / ".claude" / "skills"):
        if base.is_dir():
            for p in sorted(base.iterdir()):
                if p.is_dir() and p.name.startswith(slug + "-"):
                    skill_dirs.append(p)
    doctor = vault.scripts_dir / "skill-doctor.py"
    if not skill_dirs:
        res.ok(14, "skills", "no skill carries the `%s-` prefix" % slug)
    elif not doctor.is_file():
        res.warn(14, "skills", "%d skill(s) found and skill-doctor.py is not in Scripts/"
                 % len(skill_dirs))
    else:
        bad = []
        for sd in skill_dirs:
            r = subprocess.run([sys.executable, str(doctor), str(sd), "--root", str(root)],
                               capture_output=True, text=True, env=CHILD_ENV)
            if r.returncode != 0:
                first = [ln for ln in (r.stderr or "").splitlines() if ln.startswith("FAIL")]
                bad.append(first[0] if first else "%s failed skill-doctor.py" % sd.name)
        if bad:
            res.fail(14, "skills", "; ".join(bad))
        else:
            res.ok(14, "skills", "%d skill(s) passed skill-doctor.py" % len(skill_dirs))

    workup_skills, workup_dir = find_workup(vault, name)
    on_disk = set(p.name for p in skill_dirs)
    if workup_skills is None:
        res.warn(15, "skill-oblig", "no hire workup with a `skills:` field in the wip concept "
                 "or a task attachment, so the skill obligation cannot be answered either way")
    elif isinstance(workup_skills, str):
        res.ok(15, "skill-oblig", "the workup records `%s`" % workup_skills)
    else:
        missing = [s for s in workup_skills if s not in on_disk]
        if missing:
            res.fail(15, "skill-oblig", "the hire workup lists skill(s) that are not on disk: %s"
                     % ", ".join(missing))
        else:
            res.ok(15, "skill-oblig", "every skill the workup lists exists")

    # 16 and 17. scripts behind [SCRIPT] steps, and their red cases
    my_sops = [(p, t) for (p, owner, t) in vault.sops() if owner == name.lower()]
    named_scripts = set()
    for p, text in my_sops:
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if "[SCRIPT]" not in ln:
                continue
            blob = "\n".join(lines[i:i + 4])
            for m in re.finditer(r"([A-Za-z0-9_.\-/]+\.(?:py|sh|mjs|js))(?![A-Za-z0-9])", blob):
                named_scripts.add(m.group(1).split("/")[-1])
    if not my_sops:
        res.ok(16, "sop-scripts", "%s owns no SOP, so there is no [SCRIPT] step to check" % name)
    elif not named_scripts:
        res.ok(16, "sop-scripts", "%d SOP(s) owned, no [SCRIPT] step names a script" % len(my_sops))
    else:
        missing = [s for s in sorted(named_scripts)
                   if not (vault.scripts_dir / s).is_file()
                   and not list(vault.scripts_dir.rglob(s))
                   and not (root / ".claude" / "hooks" / s).is_file()
                   and not any((d / s).is_file() for d in vault.cross_scripts())]
        if missing:
            res.fail(16, "sop-scripts", "SOP [SCRIPT] step(s) name script(s) that are not on "
                     "disk: %s" % ", ".join(missing))
        else:
            res.ok(16, "sop-scripts", "%d script(s) named by [SCRIPT] steps, all present"
                   % len(named_scripts))

    guard_ids = keys.get("owns_gates") or []
    if isinstance(guard_ids, str):
        guard_ids = [guard_ids] if guard_ids.strip() else []
    rules = (vault.hooks_rules or {}).get("rules", [])
    rule_by_id = dict((r.get("id"), r) for r in rules)
    known_guards = set(Path(r.get("guard", "")).name for r in rules)
    guard_scripts = set(s for s in named_scripts if s in known_guards)
    for gid in guard_ids:
        r = rule_by_id.get(gid)
        guard_scripts.add(Path(r.get("guard", "")).name if r else gid + ".py")
    if not guard_scripts:
        res.ok(17, "red-tests", "%s owns no guard, so there is no red case to require" % name)
    else:
        no_case = []
        for g in sorted(guard_scripts):
            if g and g.replace(".py", "") in vault.red_tests_text:
                continue
            hits = list(vault.scripts_dir.rglob(g)) + list((root / ".claude" / "hooks").rglob(g))
            if hits and "--self-test" in read(hits[0]):
                continue
            no_case.append(g)
        if no_case:
            res.fail(17, "red-tests", "guard(s) with no red case and no --self-test: %s. A guard "
                     "nobody watched go red is not known to be a guard" % ", ".join(no_case))
        else:
            res.ok(17, "red-tests", "%d guard(s), each with a red case or a --self-test"
                   % len(guard_scripts))

    # 18. gates
    if not guard_ids:
        res.ok(18, "gates", "no owns_gates on the contract, which is right for most specialists")
    elif vault.hooks_rules is None:
        res.warn(18, "gates", "owns_gates is set and Scripts/hooks-rules.json is missing or "
                 "unreadable, so the entries cannot be tied to a rule")
    else:
        problems = []
        for gid in guard_ids:
            r = rule_by_id.get(gid)
            if not r:
                problems.append("`%s` names no rule in hooks-rules.json" % gid)
                continue
            gp = root / r.get("guard", "")
            if not gp.is_file():
                problems.append("`%s` names a guard that is not on disk (%s)"
                                % (gid, r.get("guard")))
            if workup_dir is None:
                problems.append("`%s` has no Vex review file, because there is no hire workup "
                                "folder" % gid)
            else:
                reviews = [p for p in workup_dir.glob("*.md") if "vex" in p.name.lower()]
                if not reviews:
                    problems.append("`%s` has no Vex review file in %s"
                                    % (gid, workup_dir.relative_to(root).as_posix()))
        if problems:
            res.fail(18, "gates", "; ".join(problems))
        else:
            res.ok(18, "gates", "%d gate(s), each with a rule, a script and a review"
                   % len(guard_ids))

    # 19. wikilinks
    texts = [("AGENT.md", contract)]
    if bio_path.is_file():
        texts.append((bio_path.name, read(bio_path)))
    for sd in skill_dirs:
        texts.append((sd.name + "/SKILL.md", read(sd / "SKILL.md")))
    broken = []
    for label, t in texts:
        for link in wikilinks(t):
            if not link_resolves(vault, link):
                broken.append("%s -> [[%s]]" % (label, link))
    if broken:
        res.fail(19, "wikilinks", "%d link(s) resolve to nothing: %s"
                 % (len(broken), "; ".join(broken[:4]) + (" ..." if len(broken) > 4 else "")))
    else:
        res.ok(19, "wikilinks", "every wikilink resolves")

    # 20. dashes
    dash_files = [label for label, t in texts if EM_DASH in t or EN_DASH in t]
    if shim_text and (EM_DASH in shim_text or EN_DASH in shim_text):
        dash_files.append(".claude/agents/%s.md" % slug)
    if dash_files:
        res.fail(20, "dashes", "em or en dash in %s; GL-043 bans both" % ", ".join(dash_files))
    else:
        res.ok(20, "dashes", "no em or en dash")

    # 21. the Pax brief. A contract cites the brief by the wip concept's room
    # name, read from the schema, never restated here.
    wip_room = wip_room_name(root)
    brief_links = []
    for link in wikilinks(contract):
        t = link.split("|")[0].split("#")[0]
        if "hire" in t.lower() and ("research" in t.lower() or wip_room in t):
            brief_links.append(t)
    for m in re.finditer(r"`?(%s/[^`\s\)\]]+)`?" % re.escape(wip_room), contract):
        t = m.group(1)
        if "hire" in t.lower():
            brief_links.append(t)
    # A waiver may live in either of two places, and neither is preferred.
    # In the contract: `brief_waived: "Domain known, brief waived."` -- a fact
    # about this specialist, which travels with the specialist. In the workup
    # folder: any note saying the brief was waived -- which is where a real hire
    # records it, next to the research it replaces. Requiring only the second
    # made the public Scaffold ship eight scratch WiP folders whose only job was
    # to satisfy this check (Vex gate 2026-09-14).
    #
    # The VALUE is read, not just the key. An empty `brief_waived:`, or one
    # carrying a placeholder, is not a waiver; a field that counts by existing
    # is a field somebody adds to make a red go away.
    waiver = None
    waiver_where = ""
    wv = str(keys.get("brief_waived") or "").strip()
    if wv and ("brief waived" in wv.lower() or "domain known" in wv.lower()):
        waiver = contract_path
        waiver_where = "the contract's `brief_waived` field"
    if waiver is None and workup_dir is not None:
        for p in workup_dir.glob("*.md"):
            txt = read(p)
            if "brief waived" in txt.lower() or "domain known" in txt.lower():
                waiver = p
                waiver_where = "the workup note %s" % p.name
                break
    if brief_links:
        unresolved = [t for t in brief_links if not link_resolves(vault, t)]
        if unresolved:
            res.fail(21, "brief", "the contract links a research brief that is not on disk: %s"
                     % ", ".join(unresolved[:3]))
        else:
            res.ok(21, "brief", "links a research brief that exists")
    elif waiver is not None:
        res.ok(21, "brief", "no brief linked, and a waiver is recorded in %s" % waiver_where)
    else:
        res.fail(21, "brief", "the contract links no Pax research brief, carries no "
                 "`brief_waived:` waiver line, and has no waiver note in its workup "
                 "folder; a hire with no research is the generic specialist SOP-001 "
                 "prevents")

    # 22. pack mode, public only
    if not vault.public:
        res.skip(22, "pack", "pack mode is a Scaffold check; this folder is the private vault")
    else:
        # A receipt lives at `.icor-for-life/expansions/<pack-id>.json`, and
        # NOWHERE else. Outside the pack, because a receipt inside the pack
        # folder is a file the pack itself ships and can therefore forge, which
        # let `remove` delete files the pack never installed (Vex F5, batch b2,
        # 2026-09-15). This check read the in-pack path only, so it answered
        # "not installed by an Expansion pack" for every pack-installed agent
        # and quietly passed them all.
        #
        # There is no fallback to the old in-pack path, on Vex's ruling: no
        # pack has ever been published, so no legacy install exists anywhere,
        # and a second reader of a pack-shipped file is the very thing F5
        # forbids.
        receipts = []
        canonical = root / ".icor-for-life" / "expansions"
        if canonical.is_dir():
            receipts += sorted(canonical.glob("*.json"))
        installed_by_pack = False
        for receipt in receipts:
            try:
                r = json.loads(read(receipt))
            except ValueError:
                continue
            for f in r.get("files", []):
                if str(f.get("target", "")).startswith("%s/%s/" % (AGENTS_REL, name)):
                    installed_by_pack = True
        if not installed_by_pack:
            res.ok(22, "pack", "not installed by an Expansion pack")
        elif shim_text:
            res.ok(22, "pack", "pack installed, and the shim is in place")
        else:
            res.fail(22, "pack", "files installed; activation incomplete: %s was installed by an "
                     "Expansion pack and has no dispatch shim" % name)


    # 23. the hiring marker
    marker = d / HIRING_MARKER
    if not marker.is_file():
        res.ok(23, "hiring", "no open hiring marker")
    else:
        age = hiring_age_hours(marker)
        if age is None or age > HIRING_MAX_AGE_H:
            res.warn(23, "hiring", "%s/%s is %s old; write-guard.py stopped "
                     "honouring it at %d hours, so it reads like an open door and "
                     "is not one. Delete it."
                     % (d.relative_to(root).as_posix(), HIRING_MARKER,
                        "of unknown age" if age is None else "%.0f hours" % age,
                        HIRING_MAX_AGE_H))
        else:
            res.ok(23, "hiring", "%s open, %.1f h in; a green run clears it"
                   % (HIRING_MARKER, age))

    return res, slug


def wip_room_name(root):
    """The wip concept's room as a document writes it (`<room>/...`): its
    default path in the concept schema the team root carries."""
    return resolver.load_schema(Path(root)).content["wip"].default_path


def workup_homes(root):
    """The folders a hire workup can sit in, in order: the wip home and its
    ai_team bucket when a source serves wip (GL-1013), else nothing; the
    task-attachment fallback is read separately (k4v)."""
    try:
        b = resolver.load(Path(root))
        wip = resolver.resolve_path("wip", bindings=b)
    except resolver.ResolveError:
        return []
    homes = [wip]
    try:
        homes.append(resolver.resolve_path("wip", "ai_team", bindings=b))
    except resolver.ResolveError:
        pass
    return [h for h in homes if h.is_dir()]


def workup_attachments(root, pattern):
    """k4v: hire workups attached to a task, `Tasks/<state>/<stem>/deliverables/`.
    A deliverables folder counts when its task's stem matches `pattern`, and so
    does a folder inside one whose own name matches."""
    try:
        tasks = resolver.team_path("tasks", root=Path(root))
    except resolver.ResolveError:
        return []
    out = []
    for state in resolver.TASK_STATES:
        base = tasks / state
        if not base.is_dir():
            continue
        for d in base.rglob("deliverables"):
            if not d.is_dir() or d.is_symlink():
                continue
            if re.search(pattern, d.parent.name.lower()):
                out.append(d)
            out.extend(p for p in d.iterdir() if p.is_dir() and re.search(pattern, p.name.lower()))
    return out


def find_workup(vault, name):
    """(skills, folder) from the hire workup. skills is a list of names, the
    literal string when it reads 'none, judgement role', or None when there is
    no workup carrying a `skills:` field. The workup is looked for in the
    resolved wip home (and its ai_team bucket) first; with none there, in the
    task attachments (k4v)."""
    pattern = r"%s[- ]?hire" % re.escape(name.lower())
    cands = [p for home in workup_homes(vault.root) for p in home.iterdir()
             if p.is_dir() and re.search(pattern, p.name.lower())]
    if not cands:
        cands = workup_attachments(vault.root, pattern)
    if not cands:
        return None, None
    folder = sorted(cands, key=lambda p: (p.name if p.name != "deliverables" else p.parent.name))[-1]
    pf = folder / "proposal.md"
    if pf.is_file():
        fm, _ = split_frontmatter(read(pf))
        keys, _err = parse_frontmatter(fm)
        val = keys.get("skills")
        if val is not None:
            if isinstance(val, list) and val:
                return [str(v).strip() for v in val if str(v).strip()], folder
            s = str(val).strip()
            if s and "none" in s.lower():
                return s, folder
            if s:
                return [x.strip() for x in s.split(",") if x.strip()], folder
    return None, folder


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------
def print_result(name, res, quiet=False):
    for r in res.rows:
        line = "%-4s %2d. %-12s %s" % (r["status"], r["n"], r["check"], r["message"])
        if r["status"] == "FAIL":
            print(("%s: " % name if quiet else "") + line, file=sys.stderr)
        elif not quiet:
            print(line)


def summarise(counts):
    return ("%d OK, %d FAIL, %d WARN, %d SKIP"
            % (counts["OK"], counts["FAIL"], counts["WARN"], counts["SKIP"]))


def tally(res, counts):
    for r in res.rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


# ---------------------------------------------------------------------------
# the self-test: plant every defect, watch every check go red
# ---------------------------------------------------------------------------
CLEAN_CONTRACT = """---
myicor_id: 11111111-2222-4333-8444-555555555555
agent_version: 1.0.0
agent_version_date: '2026-09-14'
agent_status: active
agent_compatibility: tool-agnostic
owner: Nolan
bio: Testy is the fixture specialist, and exists only so a validator can be watched going red.
routing_description: "Fixture Specialist. Use proactively when a self-test needs an agent that passes every check."
brief_waived: "Domain known, brief waived."
---

# Testy - Fixture Specialist

You are Testy. Research brief: [[@WIP@/2026-09-14-testy-hire/research]].
See [[GL-001-file-naming-conventions]].
"""

CLEAN_BIO = """---
type: agent-bio
agent: Testy
role: Fixture specialist
---

# Testy

Testy exists so a validator can be watched going red. Contract: `06 AI Team/Agents/Testy/AGENT.md`.
"""

CLEAN_SHIM = """---
name: testy
description: Fixture Specialist. Use proactively when a self-test needs an agent that passes every check.
tools: Read, Write, Edit, Glob, Grep
---

You are Testy. Read `06 AI Team/Agents/Testy/AGENT.md` on every invocation.
This shim is a pointer; the contract is canonical.
"""

CLEAN_INDEX = """---
type: guideline
id: agent-index
title: Agent roster and routing
---

# Agent index

## Core

| Agent | Slug | Role | Route here when |
| --- | --- | --- | --- |
| [[Larry]] | - | Orchestrator | always the entry point |
| [[Testy]] | testy | Fixture specialist | a self-test needs an agent |

## Retired

| Agent | Retired | Went to | Why |
| --- | --- | --- | --- |
"""

CLEAN_LARRY = """---
myicor_id: 99999999-2222-4333-8444-555555555555
agent_version: 1.0.0
agent_version_date: '2026-09-14'
agent_status: active
agent_compatibility: tool-agnostic
owner: Nolan
---

# Larry

## Routing cheatsheet

| User input pattern | Route to |
|---|---|
| "run the fixture" | Testy |

## What Larry does not do
"""

CLEAN_PROPOSAL = """---
type: hire-proposal
name: Testy
skills: none, judgement role
---

# Testy hire proposal

Domain known, brief waived.
"""


WORKUP = "2026-09-14-testy-hire"


def fixture_workup(v):
    """The fixture's hire workup: inside the wip concept the resolver binds
    for this fixture (implied mode A, the four ICOR rooms as the marker)."""
    return resolver.resolve_path("wip", bindings=resolver.load(Path(v))) / WORKUP


def build_fixture(dest, public=False, scripts_dir=None):
    """A minimal folder that passes every check, so a planted defect is the
    only reason a check can go red."""
    dest = Path(dest)
    # The ICOR marker without a manifest: the four rooms side by side, named
    # by the resolver, so wip binds to this folder (GL-1013 section 6).
    for room in resolver.ICOR_FOUR_ROOMS:
        (dest / room).mkdir(parents=True, exist_ok=True)
    (dest / AGENTS_REL / "Testy" / "Journal").mkdir(parents=True, exist_ok=True)
    (dest / AGENTS_REL / "Larry").mkdir(parents=True, exist_ok=True)
    (dest / SHIM_REL).mkdir(parents=True, exist_ok=True)
    (dest / SCRIPTS_REL).mkdir(parents=True, exist_ok=True)
    (dest / SKILLS_REL).mkdir(parents=True, exist_ok=True)
    (dest / SOPS_REL).mkdir(parents=True, exist_ok=True)
    (dest / "06 AI Team/AI Team Knowledge/Guidelines").mkdir(parents=True, exist_ok=True)
    (dest / AGENTS_REL).mkdir(parents=True, exist_ok=True)
    (dest / "AGENTS.md").write_text("# root\n")
    fixture_workup(dest).mkdir(parents=True, exist_ok=True)
    a = dest / AGENTS_REL / "Testy"
    # `@WIP@` is the wip concept's room name, filled in from the schema, so
    # the fixture's brief link is written the way a real contract writes it.
    (a / "AGENT.md").write_text(CLEAN_CONTRACT.replace("@WIP@", wip_room_name(dest)))
    (a / "Testy.md").write_text(CLEAN_BIO)
    (a / "Journal" / "_template.md").write_text("# Journal template\n")
    (dest / AGENTS_REL / "Larry" / "AGENT.md").write_text(CLEAN_LARRY)
    (dest / AGENTS_REL / "agent-index.md").write_text(CLEAN_INDEX)
    (dest / SHIM_REL / "testy.md").write_text(CLEAN_SHIM)
    (dest / "06 AI Team/AI Team Knowledge/Guidelines"
          / "GL-001-file-naming-conventions.md").write_text("# GL-001\n")
    if not public:
        (dest / "06 AI Team/AI Team Knowledge/Guidelines"
              / "GL-025-agent-contract-schema.md").write_text("# GL-025\n")
    wip = fixture_workup(dest)
    (wip / "proposal.md").write_text(CLEAN_PROPOSAL)
    (wip / "research.md").write_text("# Testy hire research\n")
    (dest / SCRIPTS_REL / "hooks-rules.json").write_text(json.dumps(
        {"schema": 1, "rules": [{"id": "fixture-guard",
                                 "guard": SCRIPTS_REL + "/fixture-guard.py",
                                 "event": "pre_tool_use", "match": "Bash",
                                 "severity": "block", "owner": "testy"}]}, indent=2))
    (dest / SCRIPTS_REL / "fixture-guard.py").write_text("# --self-test\n")
    (dest / SCRIPTS_REL / "run-red-tests.py").write_text("# fixture-guard red case\n")
    # The helpers a check SHELLS OUT TO, plus the siblings those helpers load
    # by path from their own folder. noteio.py is one of those siblings: a
    # fixture that copies mint-agent-ids.py without it gives that helper a
    # Scripts/ folder it refuses to run in, the check gets no answer, and the
    # planted defect looks like a check that cannot go red (2026-09-15).
    for helper in ("mint-agent-ids.py", "check-agent-shim-mcp.py",
                   "skill-doctor.py", "noteio.py", "resolve.py"):
        src = (Path(scripts_dir) if scripts_dir else HERE) / helper
        if src.is_file():
            shutil.copy2(str(src), str(dest / SCRIPTS_REL / helper))
    if public:
        (dest / ".icor-for-life").mkdir(parents=True, exist_ok=True)
        (dest / ".icor-for-life" / "manifest.json").write_text('{"schema": 1}')
        av = dest / "06 AI Team/AI Team Knowledge/Avatars"
        av.mkdir(parents=True, exist_ok=True)
        write_png(av / "testy.png", 256, 256, solid=False)
        (a / "AGENT.md").write_text(
            "---\ntype: agent\nmyicor_id: 11111111-2222-4333-8444-555555555555\n"
            "name: Testy\nrole: Fixture specialist\ncreated: 2026-09-14\n"
            'routing_description: "Fixture specialist. Use when a self-test needs an agent."\n'
            'brief_waived: "Domain known, brief waived."\n'
            "---\n\n# Testy - Fixture specialist\n\n"
            "Research brief: [[%s/2026-09-14-testy-hire/research]].\n" % wip_room_name(dest))
        (dest / SHIM_REL / "testy.md").write_text(
            "---\nname: testy\ndescription: Fixture specialist. Use when a self-test needs an "
            "agent.\n---\n\nYou are Testy. Read `06 AI Team/Agents/Testy/AGENT.md` every "
            "invocation.\n")
    else:
        write_png(a / "avatar.png", 256, 256, solid=False)
    return dest


def _plant_1(v):
    (v / AGENTS_REL / "Testy").rename(v / AGENTS_REL / "Testy - Fixture Specialist")


def _plant_2(v):
    p = v / AGENTS_REL / "Testy" / "AGENT.md"
    p.write_text(p.read_text().replace("agent_version: 1.0.0\n", "last_updated: '2026-09-14'\n"))


def _plant_3(v):
    p = v / AGENTS_REL / "Testy" / "AGENT.md"
    p.write_text(re.sub(r"myicor_id: .*\n", "", p.read_text()))


def _plant_4(v):
    (v / AGENTS_REL / "Testy" / "Testy.md").rename(v / AGENTS_REL / "Testy" / "testy.md")


def _plant_5(v):
    write_png(v / AGENTS_REL / "Testy" / "avatar.png", 1, 2)


def _plant_5_public(v):
    write_png(v / "06 AI Team/AI Team Knowledge/Avatars/testy.png", 1, 2)


def _plant_6(v):
    for p in (v / AGENTS_REL / "Testy" / "Journal").iterdir():
        p.unlink()


def _plant_7(v):
    p = v / SHIM_REL / "testy.md"
    p.write_text(p.read_text().replace("name: testy", "name: testy2"))


def _plant_8(v):
    p = v / SHIM_REL / "testy.md"
    p.write_text(re.sub(r"description: .*\n", "description:\n", p.read_text()))


def _plant_9(v):
    p = v / SHIM_REL / "testy.md"
    p.write_text(p.read_text().replace("Testy/AGENT.md", "Testy/AGENTS.md"))


def _plant_10(v):
    p = v / SHIM_REL / "testy.md"
    p.write_text(p.read_text() + "\n" + (v / AGENTS_REL / "Testy" / "AGENT.md").read_text())


def _plant_11(v):
    p = v / SHIM_REL / "testy.md"
    p.write_text(p.read_text().replace("tools: Read, Write, Edit, Glob, Grep", "tools: Read, Bsh"))


def _plant_12(v):
    p = v / AGENTS_REL / "agent-index.md"
    p.write_text(re.sub(r"\|\s*\[\[Testy\]\].*\n", "", p.read_text()))


def _plant_13(v):
    p = v / AGENTS_REL / "Larry" / "AGENT.md"
    p.write_text(p.read_text().replace('| "run the fixture" | Testy |', ""))


def _plant_14(v):
    d = v / SKILLS_REL / "testy-do-thing"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: testy-do-thing\ndescription: Do the thing. Use when the user says do the "
        "thing.\n---\n<!-- GENERATED by scaffold-init.py -->\n\nRead "
        "`06 AI Team/AI Team Knowledge/SOPs/SOP-999-nothing.md` now and follow it exactly.\n")


def _plant_15(v):
    p = fixture_workup(v) / "proposal.md"
    p.write_text(p.read_text().replace("skills: none, judgement role", "skills: testy-do-thing"))


def _plant_15_mode_b(v):
    """F2 (Ada step 8): the workup in the SIBLING content folder, mode B.
    Before the fix find_workup looked under the team root only, found nothing
    and check 15 degraded to a WARN; it must go red on the missing skill."""
    _plant_15(v)
    _to_mode_b(v)


def _to_mode_b(v):
    """Turn a built fixture into mode B: the content (four rooms, the workup)
    moves to a sibling folder and .mypka/sources.yaml points at it."""
    v = Path(v).resolve()
    life = v.parent / (v.name + "-life")
    for room in resolver.ICOR_FOUR_ROOMS:
        (life / room).mkdir(parents=True, exist_ok=True)
    wip_here = fixture_workup(v).parent
    shutil.move(str(fixture_workup(v)), str(life / wip_here.relative_to(v) / WORKUP))
    for room in resolver.ICOR_FOUR_ROOMS:
        shutil.rmtree(str(v / room), ignore_errors=True)
    (v / ".mypka").mkdir(parents=True, exist_ok=True)
    (v / resolver.SOURCES_FILE).write_text(
        "schema: 1\nsources:\n  life:\n    kind: folder\n    root: \"../%s\"\n"
        "    serves: all\n    write: allow\n" % life.name)
    resolver.clear_cache()


def _plant_15_task(v):
    """k4v: no wip room in reach, the workup attached to its task under
    Tasks/<state>/<stem>/deliverables/. Check 15 must still read it."""
    _plant_15(v)
    src = fixture_workup(v)
    task_dir = resolver.team_path("tasks", "open", root=v) / WORKUP
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / (WORKUP + ".md")).write_text("---\ntype: task\n---\n\n# Testy hire\n")
    shutil.move(str(src), str(task_dir / "deliverables"))
    shutil.rmtree(str(src.parent), ignore_errors=True)
    resolver.clear_cache()


def _plant_16(v):
    (v / SOPS_REL / "SOP-900-fixture.md").write_text(
        "---\nsop_id: SOP-900\ntitle: Fixture\nowner: Testy\n---\n\n"
        "# SOP-900\n\n### 1. [SCRIPT] run it\n\n`python3 \"06 AI Team/AI Team Knowledge/"
        "Scripts/trim.py\"`\n")


def _plant_17(v):
    (v / SOPS_REL / "SOP-901-fixture.md").write_text(
        "---\nsop_id: SOP-901\ntitle: Fixture guard\nowner: Testy\n---\n\n"
        "# SOP-901\n\n### 1. [SCRIPT] run the guard\n\n`python3 \"06 AI Team/AI Team Knowledge/"
        "Scripts/fixture-guard.py\"`\n")
    (v / SCRIPTS_REL / "run-red-tests.py").write_text("# no cases here\n")
    (v / SCRIPTS_REL / "fixture-guard.py").write_text("# no self test here\n")


def _plant_18(v):
    p = v / AGENTS_REL / "Testy" / "AGENT.md"
    p.write_text(p.read_text().replace("owner: Nolan\n",
                                       "owner: Nolan\nowns_gates:\n  - \"ghost-guard\"\n"))


def _plant_18_public(v):
    p = v / AGENTS_REL / "Testy" / "AGENT.md"
    p.write_text(p.read_text().replace("created: 2026-09-14\n",
                                       "created: 2026-09-14\nowns_gates:\n  - \"ghost-guard\"\n"))


def _plant_19(v):
    p = v / AGENTS_REL / "Testy" / "AGENT.md"
    p.write_text(p.read_text() + "\nSee [[GL-999-nothing]].\n")


def _plant_20(v):
    p = v / SHIM_REL / "testy.md"
    p.write_text(p.read_text() + "\nA line with an " + EM_DASH + " in it.\n")


def _strip_both_waivers(v):
    """Delete the linked brief and BOTH waiver homes.

    A plant that clears only one home goes green on the other and stops testing
    anything, which is the failure this whole check was written to avoid.
    """
    (fixture_workup(v) / "research.md").unlink()
    p = fixture_workup(v) / "proposal.md"
    p.write_text(p.read_text().replace("Domain known, brief waived.", "Nothing here."))
    c = v / AGENTS_REL / "Testy" / "AGENT.md"
    return c


def _plant_21(v):
    """Waiver in NEITHER place: the red case Vex asked for."""
    c = _strip_both_waivers(v)
    c.write_text("\n".join(l for l in c.read_text().splitlines()
                            if not l.startswith("brief_waived:")) + "\n")


def _plant_21b(v):
    """The field is present but says nothing. Presence is not a waiver."""
    c = _strip_both_waivers(v)
    c.write_text(c.read_text().replace(
        'brief_waived: "Domain known, brief waived."', 'brief_waived: "TBD"'))


def _plant_22(v):
    """A pack receipt in the one place a receipt lives,
    `.icor-for-life/expansions/<pack-id>.json`, with the shim missing. Until
    2026-09-15 check 22 read the in-pack path instead and passed this."""
    d = v / ".icor-for-life" / "expansions"
    d.mkdir(parents=True, exist_ok=True)
    (d / "fixture-pack.json").write_text(json.dumps(
        {"schema": 1, "id": "fixture-pack",
         "files": [{"target": AGENTS_REL + "/Testy/AGENT.md", "sha256": "x"}]}))
    (v / SHIM_REL / "testy.md").unlink()


PLANTS = [
    (1, "folder", "folder renamed to `Testy - Fixture Specialist`", _plant_1, "both"),
    (2, "frontmatter", "agent_version removed, last_updated added", _plant_2, "private"),
    (3, "id", "myicor_id removed", _plant_3, "both"),
    (4, "bio", "bio card renamed to lowercase `testy.md`", _plant_4, "both"),
    (5, "avatar", "a 1x2 PNG written in place", _plant_5, "private"),
    (5, "avatar", "a 1x2 PNG written in place", _plant_5_public, "public"),
    (6, "journal", "Journal/ emptied", _plant_6, "private"),
    (7, "shim", "shim declares `name: testy2`", _plant_7, "both"),
    (8, "shim-desc", "shim description blanked", _plant_8, "both"),
    (9, "shim-points", "shim body points at AGENTS.md, the 2026-09-03 defect", _plant_9, "both"),
    (10, "shim-size", "the contract appended to the shim", _plant_10, "both"),
    (11, "shim-tools", "`tools: Read, Bsh`, a typo the host drops silently", _plant_11, "private"),
    (12, "index", "the agent-index row deleted", _plant_12, "both"),
    (13, "cheatsheet", "Larry's cheatsheet row deleted", _plant_13, "private"),
    (14, "skills", "a SKILL.md citing SOP-999, which does not exist", _plant_14, "both"),
    (15, "skill-oblig", "the workup lists a skill that is not on disk", _plant_15, "both"),
    (15, "skill-oblig", "the same, the workup in the sibling content folder (mode B)",
     _plant_15_mode_b, "both"),
    (15, "skill-oblig", "the same, no wip room, the workup attached to its task (k4v)",
     _plant_15_task, "both"),
    (16, "sop-scripts", "a [SCRIPT] step naming trim.py, which does not exist", _plant_16, "both"),
    (17, "red-tests", "a guard with neither a red case nor a --self-test", _plant_17, "both"),
    (18, "gates", "owns_gates names a guard with no rule behind it", _plant_18, "private"),
    (18, "gates", "owns_gates names a guard with no rule behind it", _plant_18_public, "public"),
    (19, "wikilinks", "[[GL-999-nothing]] inserted", _plant_19, "both"),
    (20, "dashes", "one em dash inserted in the shim", _plant_20, "both"),
    (21, "brief", "the brief deleted and a waiver in NEITHER place", _plant_21, "both"),
    (21, "brief", "the brief deleted and `brief_waived: \"TBD\"`, which waives nothing",
     _plant_21b, "both"),
    (22, "pack", "a .icor-for-life/expansions receipt with an agent folder and no shim", _plant_22, "public"),
]


def self_test(scripts_dir=None, verbose=True):
    """Build a clean fixture, assert it passes, then plant each defect in its
    own copy and assert exactly that check goes red. A check whose fixture
    cannot be made to go red is a check that is not known to be a check."""
    problems = []
    watched = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for mode in ("private", "public"):
            clean = tmp / ("clean-" + mode)
            build_fixture(clean, public=(mode == "public"), scripts_dir=scripts_dir)
            res, _ = check_agent(Vault(clean), "Testy")
            if res.fails:
                problems.append("the clean %s control did not pass: %s"
                                % (mode, "; ".join("%d/%s %s" % (f["n"], f["check"], f["message"])
                                                   for f in res.fails)))
            elif verbose:
                print("OK   clean control (%s) passed every check" % mode)
            # The same fixture in mode B: the workup and its brief in the
            # sibling content folder. Before F2 check 15 degraded to a WARN
            # and a public contract's brief link did not resolve.
            clean_b = tmp / ("clean-" + mode + "-mode-b")
            build_fixture(clean_b, public=(mode == "public"), scripts_dir=scripts_dir)
            _to_mode_b(clean_b)
            res, _ = check_agent(Vault(clean_b), "Testy")
            bad = res.fails + [w for w in res.rows if w["status"] == "WARN" and w["n"] == 15]
            if bad:
                problems.append("the clean %s mode B control did not pass: %s"
                                % (mode, "; ".join("%d/%s %s" % (f["n"], f["check"], f["message"])
                                                   for f in bad)))
            elif verbose:
                print("OK   clean control (%s, mode B) passed every check" % mode)

            for i, (num, label, defect, plant, scope) in enumerate(PLANTS):
                if scope not in ("both", mode):
                    continue
                v = tmp / ("%s-%02d-%s-%d" % (mode, num, label, i))
                build_fixture(v, public=(mode == "public"), scripts_dir=scripts_dir)
                plant(v)
                res, _ = check_agent(Vault(v), "Testy")
                watched += 1
                if not [f for f in res.fails if f["n"] == num]:
                    problems.append("check %d (%s) stayed green with %s [%s]"
                                    % (num, label, defect, mode))
                elif verbose:
                    print("RED  %2d. %-12s %s [%s]" % (num, label, defect, mode))
    if problems:
        for p in problems:
            print("FAIL self-test: %s" % p, file=sys.stderr)
        print("\nself-test failed: %d planted defect(s) did not turn their check red. A check "
              "that cannot go red is not a check." % len(problems), file=sys.stderr)
        return 1
    print("\nOK self-test: %d planted defects, %d checks went red, and both clean controls "
          "stayed green" % (watched, watched))
    return 0


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Refuse an incomplete hire.")
    ap.add_argument("name", nargs="?", help="the specialist's name, Title case")
    ap.add_argument("--all", action="store_true", help="check every dispatchable agent")
    ap.add_argument("--self-test", action="store_true", dest="selftest",
                    help="plant every defect in a temp copy and watch every check go red")
    ap.add_argument("--json", action="store_true", help="machine readable report")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="vault root")
    args = ap.parse_args()

    if args.selftest:
        return self_test(scripts_dir=HERE, verbose=not args.json)

    root = _team_root(args.root)
    if not (root / AGENTS_REL).is_dir():
        print("FAIL check-hire: %s has no `%s` folder, so it is not a vault root"
              % (root, AGENTS_REL), file=sys.stderr)
        return 1
    vault = Vault(root)
    folder = "the public Scaffold" if vault.public else "the private vault"

    if not args.all and not args.name:
        print("FAIL check-hire: name a specialist, or pass --all", file=sys.stderr)
        return 1

    names = vault.dispatchable() if args.all else [args.name]
    counts = {"OK": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
    report = []
    per_check = {}
    for name in names:
        res, slug = check_agent(vault, name)
        tally(res, counts)
        for r in res.rows:
            if r["status"] == "FAIL":
                per_check.setdefault("%02d %s" % (r["n"], r["check"]), []).append(name)
        report.append({"agent": name, "slug": slug, "checks": res.rows, "fails": len(res.fails)})
        # A green run closes the hire, so it closes the door the hire opened.
        # Left alone, the marker would keep this one contract writable by every
        # later session, which is the standing open door the marker exists to
        # avoid being.
        if not res.fails:
            mk = vault.agents_dir / name / HIRING_MARKER
            if mk.is_file():
                try:
                    mk.unlink()
                    if not args.json:
                        print("     cleared %s (the hire is green; the write guard "
                              "is closed on this contract again)"
                              % mk.relative_to(root).as_posix())
                except OSError as e:
                    print("WARN check-hire: could not delete %s (%s); delete it by "
                          "hand or the contract stays writable" % (mk, e),
                          file=sys.stderr)
        if not args.json:
            print_result(name, res, quiet=args.all)

    # orphan skills: a door into a room nobody lives in
    orphans = []
    if args.all:
        slugs = set(vault.slug_of(n) for n in vault.dispatchable())
        known = set()
        for p in list(vault.agents_dir.glob("*")) + list(vault.agents_dir.glob("_retired/*")):
            if p.is_dir():
                known.add(p.name.lower())
        known |= set(n.lower() for n in vault.retired_names())
        for base in (root / SKILLS_REL, root / ".claude" / "skills"):
            if not base.is_dir():
                continue
            for p in sorted(base.iterdir()):
                if not p.is_dir() or not (p / "SKILL.md").is_file() or "-" not in p.name:
                    continue
                prefix = p.name.split("-")[0]
                if prefix in slugs:
                    continue
                if prefix in known:
                    orphans.append(p.name)
    if orphans:
        counts["FAIL"] += 1
        msg = ("skill folder(s) whose prefix matches no dispatchable slug: %s. A door into a "
               "retired room is a dispatch that fails silently" % ", ".join(sorted(set(orphans))))
        per_check.setdefault("14 orphan-skills", []).append("(folder level)")
        if not args.json:
            print("FAIL  -- orphan-skills %s" % msg, file=sys.stderr)

    if args.json:
        print(json.dumps({"root": str(root), "folder": folder, "agents": report,
                          "counts": counts, "fails_by_check": per_check}, indent=2))
    else:
        print("\n" + "=" * 47)
        print("check-hire in %s: %d agent(s), %s" % (folder, len(names), summarise(counts)))
        if per_check:
            print("FAIL lines by check:")
            for key in sorted(per_check):
                who = per_check[key]
                print("  %-18s %3d  %s" % (key, len(who),
                                           ", ".join(who[:8]) + (" ..." if len(who) > 8 else "")))
        print("A WARN is not a pass and a SKIP is not a pass. Read them before citing this run.")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
