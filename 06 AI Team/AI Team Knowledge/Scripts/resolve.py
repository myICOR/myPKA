#!/usr/bin/env python3
"""resolve.py: turn a concept into a place, and find the myPKA root (GL-1013).

The team addresses CONCEPTS (`journal`, `wip/operations`), never room paths.
This module is the only code that turns a concept into a place and the only
code that finds the team root. Contract: GL-1013 sections 3 to 9.

    resolve.py <concept>[/<slot>] [--need a,b] [--write frontmatter|full]
               [--task ID] [--root PATH] [--json]
    resolve.py --check [--root PATH] [--json]
    resolve.py --tool NAME [--root PATH]      the path of a source's own script

Exit 0 bound (or --check compatible), 3 fallback, 4 degraded, 2 error. On an
error the FIRST stderr line is `E_CODE concept: detail`.

WHAT THIS MODULE NEVER DOES. It never writes, moves, creates a folder, opens
a network connection or starts a subprocess. It reads `.mypka/sources.yaml`,
the two manifests, the concept schema, `stat` of homes, and the `Tasks/` tree
for the wip fallback. Stdlib only. PyYAML is never imported: the reader below
is a strict subset of YAML (GL-1013 section 3, rule 5), because a guard that
imports a library a member does not have reports a failure when it never ran.

Scripts load this file by path, the same way they load noteio.py:

    _rs = importlib.util.spec_from_file_location("mypka_resolve", HERE / "resolve.py")
    resolver = importlib.util.module_from_spec(_rs); _rs.loader.exec_module(resolver)

Python floor: 3.9 (macOS /usr/bin/python3). No dataclasses, no `X | Y`
annotations, no match statement.
"""
# A script launched from Scripts/ has Scripts/ at the FRONT of sys.path, so a
# `Scripts/json.py` would shadow the stdlib before this file read a byte. Same
# stanza as session-start.py (Vex ruling W7, 2026-09-16).
import sys, os                                                   # noqa: E401
sys.dont_write_bytecode = True
if sys.path and __name__ == "__main__":
    _first = os.path.realpath(sys.path[0] or os.getcwd())
    if _first == os.path.dirname(os.path.realpath(__file__)):
        del sys.path[0]

import json
import re
from collections import namedtuple
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants. Room and folder names live HERE and in the schema, nowhere else
# in the team's scripts (plan T2). A later rename is one edit.
# ---------------------------------------------------------------------------
AGENTS_FILE = "AGENTS.md"
AGENTS_DIR = "06 AI Team/Agents"           # the team-root marker, with AGENTS.md
SCRIPTS_DIR = "06 AI Team/AI Team Knowledge/Scripts"
SOURCES_FILE = ".mypka/sources.yaml"
TEAM_MANIFEST = ".mypka/manifest.json"
SCHEMA_FILE = ".mypka/icor-concepts-1.json"
ICOR_MANIFEST = ".icor-for-life/manifest.json"
# The ICOR marker when `.icor-for-life/` did not sync to this device: the four
# rooms side by side (GL-1013 section 6).
ICOR_FOUR_ROOMS = ("00 Daily Scratchpad", "01 Inbox", "03 WiP", "04 Inner World")

KINDS = ("folder", "mcp", "rest")
IMPLEMENTED_KINDS = ("folder",)            # 1.0 ships the folder adapter only
CAPS_REMOTE = frozenset("read list search frontmatter links create update set_property move".split())
CAPS_FOLDER = CAPS_REMOTE | {"binary", "tools", "state"}
CAPS_MARKER_ONLY = frozenset({"tools", "state"})
KIND_MAX = {"folder": CAPS_FOLDER, "mcp": CAPS_REMOTE, "rest": CAPS_REMOTE}
WRITE_CAPS = frozenset({"create", "update", "set_property", "move"})
WRITE_NEEDS = {"frontmatter": frozenset({"set_property"}), "full": frozenset({"create", "update"})}
SCOPE_RANK = {"none": 0, "frontmatter": 1, "full": 2}
POLICIES = ("deny", "ask", "allow")

SOURCE_KEYS = {
    "folder": {"kind", "role", "root", "implements", "serves", "except", "homes", "capabilities", "write"},
    "mcp": {"kind", "role", "server", "auth_env", "implements", "serves", "except", "homes", "capabilities", "write"},
    "rest": {"kind", "role", "base_url", "auth_env", "implements", "serves", "except", "homes", "capabilities", "write"},
}
SOURCE_ID = re.compile(r"[a-z][a-z0-9_]{0,31}")
ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]{0,63}")
# An AWS access key id is all capitals and digits, so it passes ENV_NAME. It is
# a credential VALUE, never a variable name (Vex step 5, F10).
AWS_KEY_ID = re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}")
# A task id is a task SLUG, optionally with `.md`: never a path, never a glob
# (Vex step 5, F6 and F11). The lookup matches the file name exactly.
TASK_ID = re.compile(r"[a-z0-9][a-z0-9-]*")


# ---------------------------------------------------------------------------
# The embedded copy of icor-concepts/1. Used ONLY when the schema file did not
# reach this device (dot folders do not sync). The red suite compares it with
# the schema file on every run, so it cannot drift silently. `side` is the
# room's side in the schema: only `source` concepts are filtered by a source
# manifest's `exposes`.
# ---------------------------------------------------------------------------
_E = {
    # id: (default_path, slots, max_write_scope, needs, side)
    "scratchpad": ("00 Daily Scratchpad", {}, "frontmatter", (), "source"),
    "inbox": ("01 Inbox", {"outer_world": "Outer World", "outer_world_archive": "Outer World/archive",
                           "scanner": "Scanner Inbox"}, "full", ("move",), "source"),
    "planner": ("02 Planner", {"habits": "Habits", "routines": "Routines", "weeks": "Weeks"},
                "frontmatter", (), "source"),
    "wip": ("03 WiP", {"workstreams": "Workstreams", "ai_team": "AI Team", "projects": "Projects",
                       "operations": "Operations", "archive": "_archive"}, "full", (), "source"),
    "journal": ("04 Inner World/Journal", {}, "full", (), "source"),
    "notes": ("04 Inner World/Notes", {"highlights": "Highlights"}, "full", (), "source"),
    "people": ("04 Inner World/Contacts/People", {}, "full", (), "source"),
    "companies": ("04 Inner World/Contacts/Companies", {}, "full", (), "source"),
    "key_elements": ("04 Inner World/My Life/Key Elements", {}, "full", (), "source"),
    "goals": ("04 Inner World/My Life/Goals", {}, "full", (), "source"),
    "projects": ("04 Inner World/My Life/Projects", {}, "full", (), "source"),
    "habits": ("04 Inner World/My Life/Habits", {}, "full", (), "source"),
    "topics": ("04 Inner World/My Life/Topics", {}, "full", (), "source"),
    "journey_notes": ("04 Inner World/ICOR Journey Notes", {}, "full", (), "source"),
    "assets": ("05 Assets", {"images": "Images", "audio": "Audio", "documents": "Documents"},
               "full", ("binary",), "source"),
    "databases": ("07 Databases", {}, "full", ("binary",), "source"),
    "templates": ("06 AI Team/AI Team Knowledge/Templates", {}, "none", (), "shared"),
    "life_guidelines": ("06 AI Team/AI Team Knowledge/Guidelines", {}, "none", (), "shared"),
    "life_state": (".icor-for-life/scripts", {}, "none", ("state",), "machine"),
}
_T = {
    "agents": "06 AI Team/Agents",
    "sops": "06 AI Team/AI Team Knowledge/SOPs",
    "workstreams": "06 AI Team/AI Team Knowledge/Workstreams",
    "guidelines": "06 AI Team/AI Team Knowledge/Guidelines",
    "skills": "06 AI Team/AI Team Knowledge/Skills",
    "scripts": "06 AI Team/AI Team Knowledge/Scripts",
    "tool_profiles": "06 AI Team/AI Team Knowledge/Tool Profiles",
    "expansions": "06 AI Team/Expansions",
    "ai_sessions": "06 AI Team/AI Sessions",
    "session_logs": "06 AI Team/AI Team Knowledge/Session Logs",
    "tasks": "06 AI Team/AI Team Knowledge/Tasks",
    "task_deliverables": "06 AI Team/AI Team Knowledge/Tasks/<state>/<task-stem>/deliverables",
    "team_state": ".mypka/state",
    "expansion_receipts": ".mypka/expansions",
    "team_config": ".mypka",
}
# Team slots are folder names under the team home. Not in the schema file.
TEAM_SLOTS = {"tasks": {"open": "open", "in_progress": "in-progress", "done": "done", "cancelled": "cancelled"}}
TASK_STATES = ("open", "in-progress", "done", "cancelled")
_E_TOOLS = ("life-snapshot", "find-entity", "new-entity", "new-journal-entry", "planner-week",
            "check-quality", "link-dates-to-daily-notes", "stamp-processed", "new-base",
            "open-in-obsidian", "set-property", "check-bases", "validate-scaffold", "test-life-snapshot")

# ---------------------------------------------------------------------------
# Result types. namedtuple, so they are immutable and need nothing in
# sys.modules (dataclasses do on 3.9 when loaded by path).
# ---------------------------------------------------------------------------
Root = namedtuple("Root", "path found_by warnings")
Resolution = namedtuple("Resolution", "concept slot status mode source kind path locator capabilities "
                                      "write scope fallback needs_promotion missing warnings")
Concept = namedtuple("Concept", "id default_path slots scope needs side")
Schema = namedtuple("Schema", "content team tools origin")
Source = namedtuple("Source", "id kind role root server base_url auth_env implements serves except_ homes "
                              "declared_caps write caps marker manifest exposes")


class ResolveError(Exception):
    def __init__(self, code, concept, detail):
        self.code, self.concept, self.detail = code, concept, detail
        super().__init__("%s %s: %s" % (code, concept or "-", detail))


def _fail(code, concept, detail):
    raise ResolveError(code, concept, detail)


class Bindings(object):
    """The resolved table concept -> source + home + policy (GL-1013 section 1)."""
    __slots__ = ("root", "mode", "sources", "declared", "fallbacks", "schema", "warnings", "implied")

    def __init__(self, root, mode, sources, declared, fallbacks, schema, warnings, implied):
        self.root, self.mode, self.sources, self.declared = root, mode, sources, declared
        self.fallbacks, self.schema, self.warnings, self.implied = fallbacks, schema, warnings, implied


# ---------------------------------------------------------------------------
# The YAML subset reader (GL-1013 section 3, rule 5). Block mappings, plain or
# quoted scalars, flow lists of plain scalars, `#` comments. Everything else
# is E_SOURCES_PARSE naming the line: flow mappings, block sequences,
# anchors, aliases, tags, multi-document markers, tabs, duplicate keys.
# ---------------------------------------------------------------------------
_KEY = re.compile(r'^("(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'|[A-Za-z0-9_][A-Za-z0-9_.\-]*)\s*:(?:\s+(.*))?$')
_INT = re.compile(r"-?[0-9]+")


def _perr(n, why):
    _fail("E_SOURCES_PARSE", None, "line %d: %s" % (n, why))


def _strip_comment(line, n):
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            out.append(ch)
            if ch == q:
                q = None
            elif ch == "\\" and q == '"' and i + 1 < len(line):
                pass
            continue
        if ch in ('"', "'"):
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    if q:
        _perr(n, "unterminated quote")
    return "".join(out).rstrip()


def _unquote(tok, n):
    if tok.startswith('"'):
        if len(tok) < 2 or not tok.endswith('"'):
            _perr(n, "unterminated double quote")
        body = tok[1:-1]
        if re.search(r'(?<!\\)"', body.replace("\\\\", "")):
            _perr(n, "stray double quote")
        return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), body)
    if tok.startswith("'"):
        if len(tok) < 2 or not tok.endswith("'"):
            _perr(n, "unterminated single quote")
        return tok[1:-1].replace("''", "'")
    return tok


def _scalar(tok, n):
    tok = tok.strip()
    if not tok:
        _perr(n, "empty value")
    if tok[0] in "{":
        _perr(n, "flow mappings are not part of the subset; write the mapping in block form")
    if tok[0] in "&*!|>%@`":
        _perr(n, "anchors, aliases, tags and block scalars are not part of the subset")
    if tok[0] in "\"'":
        return _unquote(tok, n)
    if ": " in tok or tok.endswith(":"):
        _perr(n, "a plain scalar may not contain ': '")
    if _INT.fullmatch(tok):
        return int(tok)
    return tok


def _value(tok, n):
    tok = tok.strip()
    if tok.startswith("["):
        if not tok.endswith("]"):
            _perr(n, "unterminated flow list")
        inner = tok[1:-1].strip()
        if not inner:
            return []
        if any(c in inner for c in "[]{}"):
            _perr(n, "nested flow collections are not part of the subset")
        return [_scalar(x, n) for x in inner.split(",")]
    return _scalar(tok, n)


def parse_subset(text):
    """Parse the YAML subset into nested dicts. Raises E_SOURCES_PARSE."""
    root = {}
    stack = [[None, root]]
    pending = None
    for n, raw in enumerate(text.splitlines(), 1):
        lead = raw[:len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in lead:
            _perr(n, "a tab in the indentation")
        line = _strip_comment(raw, n)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if body in ("---", "...") or body.startswith("%"):
            _perr(n, "multi-document markers and directives are not part of the subset")
        if body.startswith("-"):
            _perr(n, "block sequences are not part of the subset; write a flow list [a, b]")
        m = _KEY.match(body)
        if not m:
            _perr(n, "expected `key: value` or `key:`")
        key = _unquote(m.group(1), n)
        val = m.group(2)
        if pending is not None:
            p_indent, p_dict, p_key = pending
            pending = None
            if indent > p_indent:
                child = {}
                p_dict[p_key] = child
                stack.append([indent, child])
            else:
                _perr(n - 1 if n > 1 else n, "key %r has no value" % p_key)
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        frame = stack[-1]
        if frame[0] is None:
            frame[0] = indent
        if indent != frame[0]:
            _perr(n, "indentation does not match any open mapping")
        d = frame[1]
        if key in d:
            _perr(n, "duplicate key %r" % key)
        if val is None or not val.strip():
            d[key] = None
            pending = (indent, d, key)
        else:
            d[key] = _value(val, n)
    if pending is not None:
        _perr(len(text.splitlines()), "key %r has no value" % pending[2])
    return root


# ---------------------------------------------------------------------------
# The schema: the file when it is on this device, else the embedded copy.
# ---------------------------------------------------------------------------
def embedded_schema():
    content = {k: Concept(k, v[0], dict(v[1]), v[2], tuple(v[3]), v[4]) for k, v in _E.items()}
    return Schema(content, dict(_T), tuple(_E_TOOLS), "embedded")


def load_schema(team_root):
    p = Path(team_root) / SCHEMA_FILE
    if not p.is_file():
        return embedded_schema()
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        sides = {r.get("path"): r.get("side") for r in doc.get("rooms", [])}
        content = {}
        for cid, c in doc["concepts"].items():
            side = "machine" if c.get("room") is None else sides.get(c.get("room"), "source")
            content[cid] = Concept(cid, c["default_path"], dict(c.get("slots") or {}),
                                   c.get("max_write_scope", "full"), tuple(c.get("needs") or ()), side)
        team = {k: v for k, v in doc.get("team_concepts", {}).items() if not k.startswith("$")}
        tools = tuple((doc.get("tools") or {}).get("names") or ())
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        _fail("E_SCHEMA_MISMATCH", None, "%s is unreadable (%s)" % (SCHEMA_FILE, exc))
    return Schema(content, team, tools, "file")


# ---------------------------------------------------------------------------
# Finding the team root (GL-1013 section 6).
# ---------------------------------------------------------------------------
def is_team_root(p):
    p = Path(p)
    return (p / AGENTS_FILE).is_file() and (p / AGENTS_DIR).is_dir()


def _walk(start):
    s = Path(start).resolve()
    for p in [s] + list(s.parents):
        if is_team_root(p):
            return p
    return None


def _explicit_root(explicit):
    """An explicit root is taken as given (section 6, step 1), but one without
    the team-root marker says so: an ICOR folder named by --root otherwise
    loads as implied mode A with write: allow and nobody is told (Vex step 5,
    F12)."""
    p = Path(explicit).expanduser()
    if not p.is_dir():
        _fail("E_NO_ROOT", None, "explicit root %s is not a folder" % p)
    return Root(p.resolve(), "explicit", () if is_team_root(p) else ("W_ROOT_EXPLICIT_UNMARKED",))


def find_team_root(explicit=None, *, start=None, env=None, cwd=None):
    """First hit wins: explicit, CLAUDE_PROJECT_DIR (only with the marker),
    a walk up from `start` (default: this file), a walk up from the hook
    payload's `cwd`. None of these: E_NO_ROOT."""
    if explicit:
        return _explicit_root(explicit)
    warnings = []
    env = os.environ if env is None else env
    hint = env.get("CLAUDE_PROJECT_DIR")
    if hint:
        if is_team_root(Path(hint).expanduser()):
            return Root(Path(hint).expanduser().resolve(), "env:CLAUDE_PROJECT_DIR", ())
        warnings.append("W_ROOT_ENV_IGNORED")
    hit = _walk(start if start is not None else __file__)
    if hit is not None:
        return Root(hit, "walk:file", tuple(warnings))
    if cwd:
        hit = _walk(cwd)
        if hit is not None:
            return Root(hit, "walk:cwd", tuple(warnings))
    _fail("E_NO_ROOT", None, "no folder holding %s and %s/ above %s" % (AGENTS_FILE, AGENTS_DIR, start or __file__))


# ---------------------------------------------------------------------------
# Loading the binding.
# ---------------------------------------------------------------------------
_CACHE = {}


def _read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def icor_marker(folder):
    """(has_marker, manifest_or_None). The manifest wins; the four rooms side
    by side are the marker when `.icor-for-life/` did not sync."""
    folder = Path(folder)
    man = folder / ICOR_MANIFEST
    if man.is_file():
        return True, _read_json(man) or {}
    return all((folder / r).is_dir() for r in ICOR_FOUR_ROOMS), None


def _ids(value, concept_ids, team_ids, where):
    if not isinstance(value, list):
        _fail("E_SOURCES_PARSE", None, "%s must be a flow list" % where)
    out = []
    for cid in value:
        cid = str(cid)
        if cid in team_ids:
            _fail("E_TEAM_CONCEPT_REBOUND", cid, "a team concept is fixed under the team root; remove it from %s" % where)
        if cid not in concept_ids:
            _fail("E_UNKNOWN_CONCEPT", cid, "not a concept of icor-concepts/1 (%s)" % where)
        out.append(cid)
    return out


def _parse_requires(req):
    m = re.fullmatch(r"\s*([a-z][a-z0-9\-]*)\s+>=\s*(\d+)\s+<\s*(\d+)\s*", str(req or ""))
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def _parse_implements(imp):
    m = re.fullmatch(r"\s*([a-z][a-z0-9\-]*)/(\d+)\s*", str(imp or ""))
    return (m.group(1), int(m.group(2))) if m else None


def _source_from_yaml(sid, spec, team_root, schema):
    if not SOURCE_ID.fullmatch(sid):
        _fail("E_SOURCES_PARSE", None, "source id %r must match [a-z][a-z0-9_]{0,31}" % sid)
    if not isinstance(spec, dict):
        _fail("E_SOURCES_PARSE", None, "source %s must be a mapping" % sid)
    kind = spec.get("kind")
    if kind not in KINDS:
        _fail("E_SOURCES_PARSE", None, "source %s: kind must be one of %s" % (sid, ", ".join(KINDS)))
    extra = set(spec) - SOURCE_KEYS[kind]
    if extra:
        _fail("E_SOURCES_PARSE", None, "source %s: unknown key(s) for kind %s: %s" % (sid, kind, ", ".join(sorted(extra))))
    role = spec.get("role", "source")
    if role not in ("source", "enricher"):
        _fail("E_SOURCES_PARSE", None, "source %s: role must be source or enricher" % sid)
    need_key = {"folder": "root", "mcp": "server", "rest": "base_url"}[kind]
    if not isinstance(spec.get(need_key), str) or not spec.get(need_key):
        _fail("E_SOURCES_PARSE", None, "source %s: kind %s needs %s" % (sid, kind, need_key))
    auth_env = spec.get("auth_env")
    if auth_env is not None and not (isinstance(auth_env, str) and ENV_NAME.fullmatch(auth_env)):
        _fail("E_SOURCES_PARSE", None, "source %s: auth_env must be an env-var NAME, never a value" % sid)
    if auth_env is not None and AWS_KEY_ID.fullmatch(auth_env):
        _fail("E_SOURCES_PARSE", None, "source %s: auth_env has the shape of an AWS access key id; "
              "write the env-var NAME that holds it, never the value" % sid)
    concept_ids, team_ids = set(schema.content), set(schema.team)
    serves = spec.get("serves")
    if serves is None and role == "source":
        _fail("E_SOURCES_PARSE", None, "source %s: serves is required" % sid)
    if serves == "all":
        serves_set = set(concept_ids)
    elif serves is None:
        serves_set = set()
    else:
        serves_set = set(_ids(serves, concept_ids, team_ids, "source %s serves" % sid))
    exc = spec.get("except")
    if exc is not None:
        if serves != "all":
            _fail("E_SOURCES_PARSE", None, "source %s: except is only legal with serves: all" % sid)
        serves_set -= set(_ids(exc, concept_ids, team_ids, "source %s except" % sid))
    if role == "enricher":
        serves_set = set()
    homes = spec.get("homes") or {}
    if not isinstance(homes, dict):
        _fail("E_SOURCES_PARSE", None, "source %s: homes must be a block mapping" % sid)
    _ids(list(homes), concept_ids, team_ids, "source %s homes" % sid)
    for k, v in homes.items():
        if not isinstance(v, str) or not v:
            _fail("E_SOURCES_PARSE", k, "source %s: a home must be a non-empty string" % sid)
    declared = spec.get("capabilities")
    if declared is not None:
        if not isinstance(declared, list):
            _fail("E_SOURCES_PARSE", None, "source %s: capabilities must be a flow list" % sid)
        declared = frozenset(str(c) for c in declared)
        over = declared - KIND_MAX[kind]
        if over:
            _fail("E_CAPABILITY_OVERCLAIM", None, "source %s (kind %s) declares %s, above the kind's maximum"
                  % (sid, kind, ", ".join(sorted(over))))
    write = spec.get("write", "ask")
    if write not in POLICIES:
        _fail("E_SOURCES_PARSE", None, "source %s: write must be deny, ask or allow" % sid)
    if write == "allow" and kind != "folder":
        _fail("E_POLICY", None, "source %s: write: allow is legal on kind folder only" % sid)
    root = None
    if kind == "folder":
        r = Path(os.path.expanduser(spec["root"]))
        root = Path(os.path.normpath(str(r if r.is_absolute() else Path(team_root) / r)))
    implements = spec.get("implements")
    return Source(sid, kind, role, root, spec.get("server"), spec.get("base_url"), auth_env, implements,
                  frozenset(serves_set), None, dict(homes), declared, write, None, False, None, None)


def _within(child, parent):
    c, p = os.path.realpath(str(child)), os.path.realpath(str(parent))
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def load(root=None):
    """Build the binding for a team root (default: find_team_root())."""
    if root is None:
        root = find_team_root()
    elif not isinstance(root, Root):
        root = _explicit_root(root)
    key = str(root.path)
    if key in _CACHE:
        return _CACHE[key]
    b = _load(root)
    _CACHE[key] = b
    return b


def clear_cache():
    _CACHE.clear()


def _load(root):
    team = root.path
    warnings = list(root.warnings)
    schema = load_schema(team)
    if schema.origin == "embedded":
        warnings.append("W_VERSION_UNVERIFIED")
    sy = team / SOURCES_FILE
    fallbacks = {"wip": "task_attachment", "missing_capability": "degrade"}
    if sy.is_file():
        implied = False
        try:
            text = sy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            _fail("E_SOURCES_PARSE", None, "%s is unreadable (%s)" % (SOURCES_FILE, exc))
        doc = parse_subset(text)
        extra = set(doc) - {"schema", "sources", "fallbacks"}
        if extra:
            _fail("E_SOURCES_PARSE", None, "unknown top-level key(s): %s" % ", ".join(sorted(extra)))
        if "schema" not in doc:
            _fail("E_SOURCES_PARSE", None, "schema is required")
        if doc["schema"] != 1:
            _fail("E_SCHEMA_MISMATCH", None, "sources.yaml schema %r; this resolver reads schema 1" % (doc["schema"],))
        srcs = doc.get("sources")
        if not isinstance(srcs, dict) or not srcs:
            _fail("E_SOURCES_PARSE", None, "sources must hold one or more sources")
        fb = doc.get("fallbacks")
        if fb is not None:
            if not isinstance(fb, dict):
                _fail("E_BAD_FALLBACK", None, "fallbacks must be a block mapping")
            for k, v in fb.items():
                if k == "wip" and v == "task_attachment":
                    continue
                if k == "missing_capability" and v in ("degrade", "refuse"):
                    fallbacks[k] = v
                    continue
                _fail("E_BAD_FALLBACK", k if k in schema.content else None,
                      "%s: %s is not a legal fallback (wip: task_attachment; missing_capability: degrade|refuse)" % (k, v))
        sources = {sid: _source_from_yaml(sid, spec, team, schema) for sid, spec in srcs.items()}
    else:
        implied = True
        has, _man = icor_marker(team)
        if not has:
            _fail("E_NO_SOURCES", None, "no %s and no ICOR for Life marker in %s" % (SOURCES_FILE, team))
        sources = {"life": Source("life", "folder", "source", team, None, None, None, None,
                                  frozenset(schema.content), None, {}, None, "allow", None, False, None, None)}

    # Folder roots: existence, nesting, mode.
    folder = [s for s in sources.values() if s.kind == "folder"]
    for s in folder:
        if not s.root.is_dir():
            _fail("E_SOURCE_MISSING", None, "source %s: root %s does not exist" % (s.id, s.root))
    mode = "B"
    treal = os.path.realpath(str(team))
    for s in folder:
        sreal = os.path.realpath(str(s.root))
        if sreal == treal:
            mode = "A"
        elif _within(s.root, team) or _within(team, s.root):
            _fail("E_NESTED", None, "source %s: root %s and the team root %s nest" % (s.id, s.root, team))
    for i, s in enumerate(folder):
        for t in folder[i + 1:]:
            if _within(s.root, t.root) or _within(t.root, s.root):
                _fail("E_NESTED", None, "sources %s and %s have overlapping roots" % (s.id, t.id))

    # Version check (GL-1013 section 8).
    tman = _read_json(team / TEAM_MANIFEST) or {}
    req = _parse_requires(tman.get("requires"))
    if not tman.get("requires"):
        warnings.append("W_VERSION_UNVERIFIED")

    done = {}
    for s in sources.values():
        marker, man = (icor_marker(s.root) if s.kind == "folder" else (False, None))
        exposes = None
        if s.kind == "folder" and marker and man is None:
            warnings.append("W_NO_ICOR_MANIFEST")
        imp = None
        if man is not None and man.get("implements"):
            imp = man.get("implements")
        elif s.implements:
            imp = s.implements
            warnings.append("W_VERSION_UNVERIFIED")
        elif s.serves:
            warnings.append("W_VERSION_UNVERIFIED")
        if imp is not None and req is not None:
            pi = _parse_implements(imp)
            if pi is None or pi[0] != req[0] or not (req[1] <= pi[1] < req[2]):
                _fail("E_SCHEMA_MISMATCH", None, "source %s implements %s; myPKA requires %s"
                      % (s.id, imp, tman.get("requires")))
        serves = set(s.serves)
        if man is not None and isinstance(man.get("exposes"), list):
            exposes = frozenset(str(x) for x in man["exposes"])
            unknown = exposes - set(schema.content)
            if unknown:
                warnings.append("W_EXPOSES_UNKNOWN")
            serves = {c for c in serves if schema.content[c].side != "source" or c in exposes}
        caps = KIND_MAX[s.kind]
        if s.kind == "folder" and not marker:
            caps = caps - CAPS_MARKER_ONLY
        if s.declared_caps is not None:
            caps = caps & s.declared_caps
        if man is not None and isinstance(man.get("capabilities"), list):
            caps = caps & frozenset(str(x) for x in man["capabilities"])
        done[s.id] = s._replace(serves=frozenset(serves), caps=frozenset(caps), marker=marker,
                                manifest=man, exposes=exposes)
    sources = done

    # One write home per concept (rule 1).
    declared = {}
    for cid in sorted(schema.content):
        hits = sorted(s.id for s in sources.values() if cid in s.serves)
        if len(hits) > 1:
            _fail("E_DOUBLE_HOME", cid, "served by %s; exactly one source may serve it" % " and ".join(hits))
        if hits:
            declared[cid] = hits[0]
    for s in sources.values():
        if s.kind not in IMPLEMENTED_KINDS and s.serves:
            warnings.append("W_KIND_NOT_IMPLEMENTED")
    return Bindings(root, mode, sources, declared, fallbacks, schema, tuple(sorted(set(warnings))), implied)


# ---------------------------------------------------------------------------
# Resolving.
# ---------------------------------------------------------------------------
def _join(base, rel):
    return Path(os.path.normpath(str(Path(base) / rel)))


def team_path(concept, slot=None, *, bindings=None, root=None):
    """A team concept's folder under the team root. Never configurable."""
    if bindings is not None:
        team, schema = bindings.root.path, bindings.schema
    else:
        team = (root.path if isinstance(root, Root) else Path(root).resolve()) if root is not None \
            else find_team_root().path
        schema = load_schema(team)
    if concept not in schema.team:
        _fail("E_UNKNOWN_CONCEPT", concept, "not a team concept")
    if concept == "task_deliverables":
        _fail("E_NO_TASK", concept, "task_deliverables needs a task: resolve('task_deliverables', task_id=...)")
    home = _join(team, schema.team[concept])
    if slot is None:
        return home
    slots = TEAM_SLOTS.get(concept, {})
    if slot not in slots:
        _fail("E_UNKNOWN_CONCEPT", concept, "unknown slot %r" % slot)
    return _join(home, slots[slot])


def task_stem(task_id, concept=None):
    """The stem of a task id: a slug, optionally with `.md`. Anything else (a
    path, a glob, a capital, a dot) is E_NO_TASK before any lookup runs."""
    t = str(task_id or "")
    stem = t[:-3] if t.endswith(".md") else t
    if not TASK_ID.fullmatch(stem):
        _fail("E_NO_TASK", concept, "task id %r is not a task slug ([a-z0-9][a-z0-9-]*, optionally .md); "
              "give the task's name, never a path or a pattern" % t)
    return stem


def locate_task(tasks, task_id, concept=None):
    """Every (state, file) holding the task `task_id` under `tasks/<state>/`.

    The name is matched exactly (the id is a validated slug, so the walk has no
    pattern to expand). A file inside a `deliverables/` folder is never a task,
    and a hit whose real path leaves `tasks/<state>/` (a symlink) is dropped.
    new-task.py uses this lookup too, so there is one definition of "the task".
    """
    stem = task_stem(task_id, concept)
    fname = stem + ".md"
    hits = []
    for state in TASK_STATES:
        base = Path(tasks) / state
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(str(base)):
            dirnames[:] = sorted(d for d in dirnames if d != "deliverables")
            if fname not in filenames:
                continue
            p = Path(dirpath) / fname
            if p.is_symlink() or not p.is_file() or not _within(p, base):
                continue
            hits.append((state, p))
    return stem, sorted(hits, key=lambda h: str(h[1]))


def _task_deliverables(b, concept, task_id):
    """The k4v folder `Tasks/<state>/<task-stem>/deliverables` of one task, and
    whether the task still needs promotion (it is one file). Never moves."""
    tasks = team_path("tasks", bindings=b)
    stem, hits = locate_task(tasks, task_id, concept)
    if not hits:
        _fail("E_NO_TASK", concept, "task %s not found under Tasks/" % stem)
    if len(hits) > 1:
        _fail("E_TASK_AMBIGUOUS", concept, "task %s found %d times" % (stem, len(hits)))
    state, p = hits[0]
    if state == "cancelled":
        _fail("E_TASK_CLOSED", concept, "task %s is cancelled; a closed task takes no deliverable" % stem)
    promoted = p.parent.name == stem and p.parent != tasks / state
    base = p.parent if promoted else p.parent / stem
    return base / "deliverables", not promoted


def _task_fallback(b, concept, task_id, warnings):
    if not task_id:
        _fail("E_NO_TASK", concept, "no source serves %s and no task_id was given for the task-attachment fallback" % concept)
    path, promote = _task_deliverables(b, concept, task_id)
    return Resolution(concept, None, "fallback", b.mode, None, "team", path, None,
                      frozenset(CAPS_FOLDER), "allow", "full", "task_attachment", promote,
                      frozenset(), tuple(sorted(set(warnings))))


def resolve(concept, slot=None, *, need=(), for_write=None, task_id=None, bindings=None):
    b = bindings if bindings is not None else load()
    schema = b.schema
    warnings = list(b.warnings)
    if concept == "task_deliverables" and concept in schema.team:
        # A team concept, but one folder per task (ruling k4v, Vera F4). Same
        # lookup as the wip fallback; bound, because nothing fell back.
        if slot is not None:
            _fail("E_UNKNOWN_CONCEPT", concept, "unknown slot %r" % slot)
        if not task_id:
            _fail("E_NO_TASK", concept, "task_deliverables needs a task id (--task ID)")
        p, promote = _task_deliverables(b, concept, task_id)
        return Resolution(concept, None, "bound", b.mode, "team", "team", p, None, frozenset(CAPS_FOLDER),
                          "allow", "full", None, promote, frozenset(), tuple(sorted(set(warnings))))
    if concept in schema.team:
        p = team_path(concept, slot, bindings=b)
        return Resolution(concept, slot, "bound", b.mode, "team", "team", p, None, frozenset(CAPS_FOLDER),
                          "allow", "full", None, False, frozenset(), tuple(sorted(set(warnings))))
    if concept not in schema.content:
        _fail("E_UNKNOWN_CONCEPT", concept, "not a concept of icor-concepts/1 or a team concept")
    c = schema.content[concept]
    if slot is not None and slot not in c.slots:
        _fail("E_UNKNOWN_CONCEPT", concept, "unknown slot %r" % slot)
    if for_write not in (None, "frontmatter", "full"):
        _fail("E_POLICY", concept, "for_write must be frontmatter or full")
    sid = b.declared.get(concept)
    src = b.sources.get(sid) if sid else None
    if src is not None and src.kind not in IMPLEMENTED_KINDS:
        warnings.append("W_KIND_NOT_IMPLEMENTED")
        src = None
    if src is None:
        if b.fallbacks.get(concept) == "task_attachment":
            return _task_fallback(b, concept, task_id, warnings)
        _fail("E_UNBOUND", concept, "no source serves it and it has no fallback")
    caps = src.caps
    need = frozenset(need or ())
    wneed = (need & WRITE_CAPS) | (WRITE_NEEDS[for_write] if for_write else frozenset())
    if wneed - caps:
        _fail("E_CAPABILITY", concept, "source %s lacks write capability %s; writes never degrade"
              % (src.id, ", ".join(sorted(wneed - caps))))
    missing = need - caps
    status = "bound"
    if missing:
        if b.fallbacks.get("missing_capability") == "refuse":
            _fail("E_CAPABILITY", concept, "source %s lacks %s" % (src.id, ", ".join(sorted(missing))))
        status = "degraded"
    if for_write:
        if src.write == "deny":
            _fail("E_POLICY", concept, "source %s is write: deny" % src.id)
        if SCOPE_RANK[for_write] > SCOPE_RANK[c.scope]:
            _fail("E_POLICY", concept, "a %s write is above the concept's max write scope %s" % (for_write, c.scope))
    home = src.homes.get(concept, c.default_path)
    path = _join(src.root, home)
    if slot is not None:
        path = _join(path, c.slots[slot])
    if not _within(path, src.root):
        _fail("E_ESCAPE", concept, "home %s leaves the root of source %s" % (path, src.id))
    return Resolution(concept, slot, status, b.mode, src.id, src.kind, path, None, caps, src.write, c.scope,
                      None, False, missing, tuple(sorted(set(warnings))))


def resolve_path(concept, slot=None, **kw):
    b = kw.get("bindings")
    if b is None:
        b = kw["bindings"] = load()
    sid = b.declared.get(concept)
    if sid and b.sources[sid].kind != "folder" and not kw.get("task_id"):
        _fail("E_NOT_A_FOLDER", concept, "bound to %s source %s; it has no folder path"
              % (b.sources[sid].kind, sid))
    r = resolve(concept, slot, **kw)
    if r.path is None:
        _fail("E_NOT_A_FOLDER", concept, "no folder path")
    return r.path


def resolve_ref(ref, **kw):
    """`concept:<id>[/<slot>][/<rest>]` to a path. Anything else is returned
    as a Path unchanged, so a script can take a vault path or a ref."""
    ref = str(ref)
    if not ref.startswith("concept:"):
        return Path(ref)
    b = kw.get("bindings")
    if b is None:
        b = kw["bindings"] = load()
    parts = [p for p in ref[len("concept:"):].split("/") if p]
    if not parts:
        _fail("E_UNKNOWN_CONCEPT", None, "empty concept ref")
    cid, rest = parts[0], parts[1:]
    if any(p in ("..", ".") for p in rest):
        _fail("E_ESCAPE", cid, "a concept ref may not step with . or ..")
    slot = None
    if cid == "task_deliverables" and cid in b.schema.team:
        base = resolve(cid, task_id=kw.get("task_id"), bindings=b).path
    elif cid in b.schema.team:
        if rest and rest[0] in TEAM_SLOTS.get(cid, {}):
            slot = rest.pop(0)
        base = team_path(cid, slot, bindings=b)
    else:
        if cid in b.schema.content and rest and rest[0] in b.schema.content[cid].slots:
            slot = rest.pop(0)
        base = resolve_path(cid, slot, **kw)
    out = base.joinpath(*rest) if rest else base
    # The home was checked by resolve(); the REST of the ref was not. A symlink
    # inside the home (`Notes/escape -> /elsewhere`) still leaves the source
    # (Vex step 5, F9). The limit is the source root for a bound folder
    # concept, the deliverables folder on the task fallback, the team root for
    # a team concept.
    if cid == "task_deliverables" and cid in b.schema.team:
        limit = base
    elif cid in b.schema.team:
        limit = b.root.path
    else:
        sid = b.declared.get(cid)
        src = b.sources.get(sid) if sid else None
        limit = src.root if (src is not None and src.kind == "folder") else base
    if not _within(out, limit):
        _fail("E_ESCAPE", cid, "%s leaves %s" % (ref, limit))
    return out


def tool_source(b):
    cands = [s for s in b.sources.values()
             if s.kind in IMPLEMENTED_KINDS and s.serves and s.marker]
    if not cands:
        return None
    cands.sort(key=lambda s: (0 if "templates" in s.serves else 1, s.id))
    return cands[0]


def resolve_tool(name, *, bindings=None):
    """The path of a source's own script (`life-snapshot`), on the source that
    carries the ICOR marker and the `tools` capability."""
    b = bindings if bindings is not None else load()
    name = str(name)
    if name.endswith(".py"):
        name = name[:-3]
    src = tool_source(b)
    man = (src.manifest or {}) if src else {}
    tmap = man.get("tools") if isinstance(man.get("tools"), dict) else {}
    if name not in b.schema.tools and name not in tmap:
        _fail("E_UNKNOWN_CONCEPT", name, "not a tool of icor-concepts/1")
    if src is None:
        _fail("E_CAPABILITY", name, "no local folder source with the ICOR marker; tools are not available")
    if "tools" not in src.caps:
        _fail("E_CAPABILITY", name, "source %s does not grant the tools capability" % src.id)
    rel = tmap.get(name) or "%s/%s.py" % (SCRIPTS_DIR, name)
    p = _join(src.root, rel)
    if not _within(p, src.root):
        _fail("E_ESCAPE", name, "tool path leaves the root of source %s" % src.id)
    if not p.is_file():
        _fail("E_CAPABILITY", name, "source %s does not carry %s" % (src.id, rel))
    return p


def source_root(concept="journal", *, bindings=None):
    """The folder root of the source serving `concept`, for callers that hand
    a whole vault path to a source's own tool (life-snapshot, check-quality)."""
    b = bindings if bindings is not None else load()
    sid = b.declared.get(concept)
    src = b.sources.get(sid) if sid else None
    if src is None or src.kind != "folder":
        _fail("E_NOT_A_FOLDER", concept, "no folder source serves it")
    return src.root


# ---------------------------------------------------------------------------
# check(): the binding table, deterministic (R29).
# ---------------------------------------------------------------------------
def check(bindings=None, root=None):
    try:
        b = bindings if bindings is not None else load(root)
    except ResolveError as e:
        return {"schema": 1, "status": "refused", "mode": None, "team_root": None, "sources": [],
                "concepts": [], "warnings": [], "error": {"code": e.code, "concept": e.concept, "detail": e.detail}}
    rows, worst = [], 0
    for cid in sorted(b.schema.content):
        c = b.schema.content[cid]
        row = {"concept": cid, "status": None, "source": None, "kind": None, "path": None,
               "write": None, "scope": c.scope, "missing": [], "fallback": None}
        try:
            r = resolve(cid, need=c.needs, bindings=b)
            row.update(status=r.status, source=r.source, kind=r.kind, path=str(r.path) if r.path else None,
                       write=r.write, missing=sorted(r.missing))
            if r.status == "degraded":
                worst = max(worst, 1)
        except ResolveError as e:
            if e.code == "E_NO_TASK" and b.fallbacks.get(cid) == "task_attachment":
                row.update(status="fallback", kind="team", fallback="task_attachment", write="allow")
                worst = max(worst, 1)
            elif e.code in ("E_UNBOUND", "E_CAPABILITY"):
                row.update(status="unbound" if e.code == "E_UNBOUND" else "degraded")
                worst = max(worst, 1)
            else:
                row.update(status="error", fallback=None)
                row["error"] = {"code": e.code, "detail": e.detail}
                worst = 2
        rows.append(row)
    srcs = []
    for sid in sorted(b.sources):
        s = b.sources[sid]
        srcs.append({"id": sid, "kind": s.kind, "role": s.role, "root": str(s.root) if s.root else None,
                     "write": s.write, "capabilities": sorted(s.caps), "marker": bool(s.marker),
                     "implements": (s.manifest or {}).get("implements") or s.implements})
    return {"schema": 1, "status": ("compatible", "degraded", "refused")[worst], "mode": b.mode,
            "implied": b.implied, "team_root": str(b.root.path), "found_by": b.root.found_by,
            "sources": srcs, "concepts": rows, "warnings": sorted(set(b.warnings)), "error": None}


def format_check(rep):
    if rep["status"] == "refused" and rep.get("error") and not rep["concepts"]:
        e = rep["error"]
        return "binding: refused, %s %s: %s" % (e["code"], e["concept"] or "-", e["detail"])
    out = ["binding: %s, mode %s%s, team root %s" % (rep["status"], rep["mode"],
                                                     " (implied)" if rep.get("implied") else "", rep["team_root"])]
    for s in rep["sources"]:
        out.append("  source %s: %s %s, write %s" % (s["id"], s["kind"], s["root"] or "", s["write"]))
    for r in rep["concepts"]:
        where = r["path"] or ("task deliverables" if r["fallback"] else "-")
        extra = (" missing %s" % ",".join(r["missing"])) if r["missing"] else ""
        if r.get("error"):
            extra = " %s" % r["error"]["code"]
        out.append("  %-16s %-8s %s%s" % (r["concept"], r["status"], where, extra))
    if rep["warnings"]:
        out.append("  warnings: %s" % ", ".join(rep["warnings"]))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------
EXIT = {"bound": 0, "fallback": 3, "degraded": 4}


def _res_json(r):
    return {"schema": 1, "concept": r.concept, "slot": r.slot, "status": r.status, "mode": r.mode,
            "source": r.source, "kind": r.kind, "path": str(r.path) if r.path else None,
            "locator": r.locator, "capabilities": sorted(r.capabilities), "write": r.write,
            "scope": r.scope, "fallback": r.fallback, "needs_promotion": r.needs_promotion,
            "missing": sorted(r.missing), "warnings": list(r.warnings)}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="resolve.py", description="Resolve a concept (GL-1013).")
    ap.add_argument("ref", nargs="?", help="concept[/slot]")
    ap.add_argument("--need", default="")
    ap.add_argument("--write", choices=("frontmatter", "full"))
    ap.add_argument("--task")
    ap.add_argument("--root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tool", help="print the path of a content source's own script (life-snapshot, ...)")
    a = ap.parse_args(argv)
    try:
        root = find_team_root(explicit=a.root)
        if a.check:
            rep = check(root=root)
            if rep["status"] == "refused" and rep.get("error"):
                e = rep["error"]
                print("%s %s: %s" % (e["code"], e["concept"] or "-", e["detail"]), file=sys.stderr)
            elif rep["status"] == "refused":
                bad = [r for r in rep["concepts"] if r.get("error")][0]
                print("%s %s: %s" % (bad["error"]["code"], bad["concept"], bad["error"]["detail"]), file=sys.stderr)
            print(json.dumps(rep, indent=2, sort_keys=True) if a.json else format_check(rep))
            return {"compatible": 0, "degraded": 4, "refused": 2}[rep["status"]]
        if a.tool:
            # Prints the path only. This module never starts a subprocess: the
            # caller runs the script it was handed.
            print(resolve_tool(a.tool, bindings=load(root)))
            return 0
        if not a.ref:
            ap.error("give a concept, --tool NAME, or --check")
        cid, _, slot = a.ref.partition("/")
        need = [x for x in a.need.split(",") if x]
        b = load(root)
        r = resolve(cid, slot or None, need=need, for_write=a.write, task_id=a.task, bindings=b)
    except ResolveError as e:
        print("%s %s: %s" % (e.code, e.concept or "-", e.detail), file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(_res_json(r), indent=2, sort_keys=True))
    else:
        print(r.path if r.path is not None else r.locator)
        for w in r.warnings:
            print(w, file=sys.stderr)
    return EXIT[r.status]


if __name__ == "__main__":
    sys.exit(main())
