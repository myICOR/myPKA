#!/usr/bin/env python3
"""session-start.py: run the deterministic half of the session start ritual.

AGENTS.md "Session start ritual" asks the model to run three scripts before
it does anything else. Three calls a model may skip, forget or half-run, and
nothing noticed when it did. This runs them, and prints what they said, so
the model READS results instead of being asked to fetch them.

  0. check-onboarding.py   FRESH or lived-in
  3. check-quality.py --write, only when quality.json is missing or older
     than today, then the one-line health verdict
  5. expansion-pack.py list
  6. life-snapshot.py --write --brief, the six everyday life questions
     answered before anyone asks them (SOP-1017 is the reading procedure)

Steps 1, 2 and 4 of the ritual are judgement (read your contract, walk the
tasks, look at the inbox) and stay with the model, which is the whole of
GL-1005 in one paragraph.

It also writes `.mypka/state/session.json` (ruling j5d), the team layer's
record of which session this is (GL-1008). `checkpoint.py` reads it so a
completion receipt can be bound to THIS session rather than to today's date.

Stdout is added to the session as context. Exit is 0, with one exception: a
start ritual that blocks a session from starting is worse than one that did
not run, so nothing short of a version mismatch stops it.

THE COMPATIBILITY REPORT (plan step 9, GL-1013 sections 8 and 9). Before
anything else, the ritual compares what myPKA requires (`requires` in
.mypka/manifest.json, `icor-concepts >=1 <2`) with what the content source
implements (mode A: its .icor-for-life/manifest.json; mode B: the source
sources.yaml names, its manifest first, sources.yaml's own `implements`
second). One of four answers, always the first line after the session id:
  COMPATIBLE  every concept bound on icor-concepts/1.x.
  DEGRADED    a concept or a capability is missing; each one is named, and a
              missing `wip` names the k4v fallback (the deliverable attaches
              to its task). The session runs.
  WARN        a manifest is missing (Obsidian Sync does not carry dot
              folders). Run as icor-concepts/1, unverified. Never a refusal:
              a second device must not stop over a file sync never carried.
  REFUSED     the source implements a version outside `requires` (for
              example icor-concepts/2). Exit 2, the reason on stdout and on
              stderr, and NOTHING is written: no session.json, no
              quality.json, no snapshot, no child script run.
Any other binding error keeps the old behaviour: the content tools are
skipped, the line says why, exit 0.

WHAT THIS DOES NOT PROVE
- That the ritual HAPPENED in the model's head. It proves the scripts ran
  and their output was put in front of the model. Reading it is judgement.
- That the vault is healthy. It reports what check-quality measured; a
  metric nobody wrote is a metric nobody checks.
- That anything ran at all on a host without hooks. On any runtime that
  does not implement SessionStart, none of this happens and the prose
  ritual in AGENTS.md is the only thing left.
"""
# THE FIRST STATEMENTS IN THIS FILE, AND THEY HAVE TO BE (Vex ruling, W7,
# 2026-09-16). A guard is launched from Scripts/, so Python puts Scripts/ at
# the FRONT of sys.path and a `Scripts/json.py` would then be what `import
# json` finds, inside the guard, before it has read a byte. The rendered hook
# passes `-I`, which drops that entry; this stanza is the belt to that brace,
# for a guard launched some other way (by hand, by a member's own wrapper, by
# a host whose hook config is older than this file). It has to run BEFORE the
# first stdlib import or it is defending a door already walked through.
#
# `dont_write_bytecode` is here for the same reason it is in every other
# script in this folder: a guard that drops __pycache__ into the tree it is
# guarding changes what it measures (Conrad Froehling, 2026-09-16).
import sys, os                                                   # noqa: E401
sys.dont_write_bytecode = True
# realpath on BOTH sides, because they are not spelled the same. Python 3.11
# and newer resolve sys.path[0] (`/private/tmp/x` on macOS) while __file__ is
# the path as typed (`/tmp/x`), and comparing the two with abspath alone
# silently never matched: the entry stayed, and this stanza defended nothing.
if sys.path:
    _first = os.path.realpath(sys.path[0] or os.getcwd())
    if _first == os.path.dirname(os.path.realpath(__file__)):
        del sys.path[0]

import datetime
import importlib.util
import json
import re
import subprocess
import threading
import select
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
# resolve.py, loaded by path like every sibling (GL-1013). Nothing at module
# level may raise: a start ritual that blocks a session is worse than one
# that did not run, so a failure here is carried to main() as one line.
resolver, ROOT, BIND, BIND_ERR, BIND_EXC = None, None, None, None, None
try:
    _rs = importlib.util.spec_from_file_location("mypka_resolve", HERE / "resolve.py")
    resolver = importlib.util.module_from_spec(_rs)
    _rs.loader.exec_module(resolver)
    # CLAUDE_PROJECT_DIR first, but only when it holds the team marker; then
    # the walk up from this file (GL-1013 section 6, site 12).
    ROOT = resolver.find_team_root(start=__file__).path
    BIND = resolver.load(ROOT)
except Exception as _exc:                                        # noqa: BLE001
    BIND_ERR = str(_exc) or type(_exc).__name__
    BIND_EXC = _exc
# Team state, ruling j5d: .mypka/state/ under the team root.
MACHINE = resolver.team_path("team_state", root=ROOT) if ROOT is not None else None
# quality.json and snapshot.json are the content source's own machine layer.
LIFE, LIFE_STATE = None, None
if BIND is not None:
    try:
        LIFE_STATE = resolver.resolve_path("life_state", bindings=BIND)
        LIFE = resolver.tool_source(BIND).root
    except (resolver.ResolveError, AttributeError) as _exc:
        BIND_ERR = BIND_ERR or str(_exc)
BUDGET_S = 60  # the whole ritual; check-quality walks the vault


def tool(script):
    """(path, None) for a content source's own script, or (None, why)."""
    if BIND is None:
        return None, "no source binding (%s)" % BIND_ERR
    try:
        return resolver.resolve_tool(script, bindings=BIND), None
    except resolver.ResolveError as e:
        return None, "%s is not available (%s)" % (script, e)


def run(script, *args, budget=BUDGET_S):
    if isinstance(script, Path):
        path, script = script, script.name
    else:
        path = HERE / script
    if not path.is_file():
        return None, "%s is not in Scripts/" % script
    try:
        # THE SAME FLAGS THE HOOK GAVE US, HANDED DOWN. `-I` drops Scripts/
        # from the child's sys.path (F1, one layer per process), `-B` keeps
        # bytecode out of the member's tree, and `-X utf8` means a child
        # printing an emoji does not die in cp1252 on Windows. An inherited
        # environment variable could not do this job: PYTHONSAFEPATH is a
        # no-op below Python 3.11 and none of the three survives `-I` anyway.
        r = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
                            str(path), *args],
                           capture_output=True, text=True, timeout=budget)
    except subprocess.TimeoutExpired:
        return None, "%s did not finish in %ds; it was not run to the end" % (script, budget)
    except OSError as exc:
        return None, "%s could not be started (%s)" % (script, exc)
    return r, None


def _read_stdin_payload(budget=0.2):
    """The host's hook payload from stdin, or "" when none arrives in time.

    WAIT FOR A PAYLOAD, DO NOT WAIT FOREVER. A hook hands this script its
    payload and closes the pipe immediately. Anything else that inherits an
    open stdin (a script, a CI step, a test harness) never closes it, and a
    bare `stdin.read()` then blocks for as long as that caller lives: one
    red-test run sat here for ten minutes printing nothing, which reads exactly
    like a slow suite. A fifth of a second is far longer than a hook needs and
    short enough that nobody notices.

    TWO WAYS OF WAITING, BECAUSE select() IS NOT PORTABLE. On POSIX,
    select.select() answers "is there anything there yet" for a pipe. On
    Windows it answers only for sockets and raises for everything else, and the
    raise was swallowed into `ready = []`: the payload was never read, an id
    was minted, and the ritual announced "GUARDS: no host session id received"
    on a machine whose hooks were working perfectly (Conrad Froehling, Windows
    11, 2026-09-16). Where select cannot answer, a daemon thread does the
    blocking read and the budget falls on the join instead, so the behaviour is
    the same from the outside and a caller that never closes stdin still cannot
    hang this script. The thread is given a little longer because it has to be
    scheduled before it can read anything.
    """
    try:
        ready = select.select([sys.stdin], [], [], budget)[0]
    except (OSError, ValueError, AttributeError):
        return _read_stdin_in_a_thread(max(budget, 0.5))
    if not ready:
        return ""
    return _read_stdin_text()


def _read_stdin_text():
    """Bytes, then UTF-8 with replacement. NOT the locale codec.

    Same defect as write-guard.py's (Vex F-B, 2026-09-16): a hook payload
    carrying an emoji raises UnicodeDecodeError under cp1252, and here that
    meant the session id was lost and the ritual announced that the guards
    were off on a machine whose hooks were working.
    """
    try:
        buf = getattr(sys.stdin, "buffer", None)
        if buf is None:
            return sys.stdin.read() or ""
        return buf.read().decode("utf-8", "replace") or ""
    except (OSError, ValueError):
        return ""


def _read_stdin_in_a_thread(budget):
    box = []

    def _read():
        box.append(_read_stdin_text())

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(budget)
    # A daemon thread still reading when the budget runs out is abandoned, and
    # the interpreter does not wait for it on the way out. That is the whole
    # point: stdin held open by somebody else must not hold a session shut.
    return box[0] if box else ""


def record_session():
    """Write which session this is, for checkpoint.py to bind a receipt to.

    The id comes from the host's hook payload when there is one. No
    environment variable carries it (checked against Claude Code's hook
    documentation, 2026-09-14), so a runtime that sends no payload gets a
    minted id instead: still one id per session, just not the host's.
    """
    sid = os.environ.get("ICOR_SESSION_ID") or ""
    source = "ICOR_SESSION_ID"
    if not sid and not sys.stdin.isatty():
        text = _read_stdin_payload()
        if text:
            try:
                payload = json.loads(text or "{}")
                sid = str(payload.get("session_id") or "")
                source = "host hook payload"
            except ValueError:
                sid = ""
    if not sid:
        sid = "local-" + uuid.uuid4().hex[:12]
        source = "minted here (the host sent no session id)"
    if MACHINE is None:
        return sid
    MACHINE.mkdir(parents=True, exist_ok=True)
    (MACHINE / "session.json").write_text(json.dumps({
        "schema": 1,
        "session_id": sid,
        "started": datetime.datetime.now(datetime.timezone.utc)
                    .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "id_source": source,
    }, indent=2) + "\n", encoding="utf-8")
    return sid


def _no_host_session_id(sid):
    """True when this ritual had to mint its own id.

    Reads the artefact rather than a variable in scope, because the artefact is
    what a resuming session, a red test and a member can all look at, and a
    second definition of "was there a hook" is a second thing to keep true."""
    try:
        doc = json.loads((MACHINE / "session.json").read_text(encoding="utf-8"))
    except (ValueError, OSError, TypeError):
        return str(sid or "").startswith("local-")
    return str(doc.get("id_source") or "").startswith("minted here")


def quality_is_stale():
    if LIFE_STATE is None:
        return True
    q = LIFE_STATE / "quality.json"
    if not q.is_file():
        return True
    try:
        data = json.loads(q.read_text(encoding="utf-8"))
        return not str(data.get("generated", "")).startswith(
            datetime.date.today().isoformat())
    except (ValueError, OSError):
        return True


def last_receipt_line():
    """One line naming the newest completion receipt and what it left open.

    A receipt carries the machine-readable answer to "what did the last
    session do": its outputs with hashes, and its `unresolved` list. Nothing
    pointed a resuming session at it, so both pilot CLIs reconstructed the
    answer from the session log's prose instead and the receipt stayed a
    validator artifact (pilot B finding F6). This is the pointer.

    It never fails a start: an unreadable receipts folder returns the plain
    sentence that there is none, because a start ritual that blocks a session
    is worse than one that did not run."""
    try:
        recs = sorted((MACHINE / "receipts").glob("*.json"),
                      key=lambda q: q.stat().st_mtime, reverse=True)
    except (OSError, TypeError):
        recs = []
    if not recs:
        return ("last receipt: none yet. WS-1005 writes one at the end of a "
                "session; until then there is nothing machine-readable to resume from.")
    try:
        doc = json.loads(recs[0].read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return "last receipt: %s is unreadable (%s)" % (recs[0].name, exc)
    unresolved = doc.get("unresolved") or []
    return ("last receipt: %s, session %s, %d unresolved item(s)%s"
            % (recs[0].relative_to(ROOT).as_posix(),
               doc.get("session_id") or "unknown", len(unresolved),
               ("; " + "; ".join(str(u) for u in unresolved[:3])) if unresolved else ""))


def life_snapshot_missing():
    """The line to say when there is no snapshot, in SOP-1017's concept form.
    life-snapshot is the content source's tool, so its path comes from the
    resolver (GL-1013 section 2.4), never from a team-root Scripts/ path that
    does not exist in mode B. When resolve_tool finds it, the path is added."""
    path, _err = tool("life-snapshot")
    where = ""
    if path is not None:
        try:
            shown = Path(path).relative_to(ROOT).as_posix()
        except ValueError:
            shown = str(path)
        where = " On this device the path is %s." % shown
    return ('No life snapshot on this device yet. Run: python3 '
            '"06 AI Team/AI Team Knowledge/Scripts/resolve.py" --tool life-snapshot, '
            'then python3 "<the path it printed>" --write (on Windows: py -3 '
            '"06 AI Team\\AI Team Knowledge\\Scripts\\resolve.py" --tool life-snapshot, '
            'then py -3 "<the path it printed>" --write).%s Until then I would have '
            "to read the folders, which is slower and less reliable; say the word "
            "and I will." % where)


LIFE_SNAPSHOT_RULE = (
    "Do NOT answer the six life questions from memory and do NOT say there are "
    "no goals: a missing report means the script did not run, never that the "
    "life is empty."
)

# THE SIZE CAP (Vex gate 2026-09-15, finding F1 MEDIUM, mirrored from the
# private vault's wrapper). Nothing here is a leak; it is a flood. A tampered
# or malformed snapshot, or one absurd note title, makes the brief render
# megabytes, and this ritual prints whatever it renders straight into the
# session context at EVERY start, so it repeats until somebody notices.
# Measured on the private vault before the cap: 5,000,809 bytes of stdout.
#
# Only the character cap is mirrored. This ritual never opens snapshot.json:
# it reads the child's stdout, so the private wrapper's 2 MB file refusal has
# no surface here. A real brief is under 4000 characters.
MAX_BRIEF_CHARS = 16000


def bounded_brief(text):
    """Cut an oversized brief and SAY it was cut, never silently."""
    if len(text) <= MAX_BRIEF_CHARS:
        return text
    return (text[:MAX_BRIEF_CHARS]
            + "\n(brief cut at %d characters; a real one is under 4000. "
              "Something is oversized; check snapshot.json and the note titles "
              "before trusting the lines above.)" % MAX_BRIEF_CHARS)


def life_snapshot_lines():
    """The six everyday questions, answered before anyone asks them.

    `life-snapshot.py --write --brief` walks three entity rooms, the Journal
    months touching the last 30 days, the Planner and the scratchpads, writes
    `.icor-for-life/scripts/snapshot.json` and renders about sixteen lines.
    Measured at 0.06s on this scaffold and 0.5s on a lived-in vault, so it runs
    on every start rather than on a staleness check: a brief that is sometimes
    yesterday's is a brief whose date nobody reads.

    It never fails a start. A missing or unrunnable snapshot prints the line
    the reader must say instead of listing goals from memory, which is the
    whole point: an absent report means the script did not run, never that the
    member has no goals. SOP-1017 is the reading procedure.
    """
    path, err = tool("life-snapshot")
    r = None
    if path is not None:
        r, err = run(path, str(LIFE), "--write", "--brief")
    if err:
        return ["  life snapshot: NOT TAKEN, %s" % err,
                "    " + life_snapshot_missing(),
                "    " + LIFE_SNAPSHOT_RULE]
    if r.returncode != 0:
        return ["  life snapshot: NOT TAKEN, life-snapshot.py exited %d (%s)"
                % (r.returncode, (r.stderr or r.stdout or "no output").strip()[:200]),
                "    " + life_snapshot_missing(),
                "    " + LIFE_SNAPSHOT_RULE]
    body = bounded_brief((r.stdout or "").strip()).splitlines()
    if not body:
        return ["  life snapshot: life-snapshot.py exited 0 and printed nothing",
                "    " + life_snapshot_missing(),
                "    " + LIFE_SNAPSHOT_RULE]
    return ["  life snapshot:"] + ["    " + b for b in body]


REFUSE_EXIT = 2
K4V_LINE = ("no source serves it; k4v fallback: a deliverable attaches to its "
            "task at Tasks/<state>/<task-stem>/deliverables/ (pass the task id)")


def _json_or_none(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def refusal():
    """The one reason this ritual stops: the source's schema version is
    outside what this myPKA requires (E_SCHEMA_MISMATCH from the resolver).
    None otherwise. Decided before anything is written."""
    if BIND_EXC is not None and getattr(BIND_EXC, "code", None) == "E_SCHEMA_MISMATCH":
        return getattr(BIND_EXC, "detail", None) or str(BIND_EXC)
    return None


def refusal_advice(why):
    """What to do about a refusal, by its cause (Vera step 15, F5). The
    resolver raises E_SCHEMA_MISMATCH for three different files, and only one
    of them is fixed by changing a release."""
    sources = resolver.SOURCES_FILE
    if why.startswith(sources.rsplit("/", 1)[-1] + " schema"):
        return ("The fix is in %s, not in a release: it declares a schema this "
                "resolver does not read. Set `schema: 1` in that file, or copy "
                "%s.example over it (a hand edit: the team's write guard protects "
                "the binding)." % (sources, sources))
    if why.startswith(resolver.SCHEMA_FILE):
        return ("The fix is %s, which ships with myPKA: restore it from the "
                "myPKA release zip you installed; do not edit it by hand."
                % resolver.SCHEMA_FILE)
    return ("Do not read or write the content with this team until the versions "
            "match: install a myPKA release that reads that version, or go back to "
            "an ICOR for Life release that implements icor-concepts/1.")


def compatibility_lines():
    """The compatibility report (plan step 9): COMPATIBLE, DEGRADED with the
    missing concepts named, or NOT CHECKED; plus a WARN line per missing
    manifest. Never raises: a report that crashes the ritual is worse than
    none."""
    if BIND is None:
        return ["  compatibility: NOT CHECKED, the binding did not load (%s)" % BIND_ERR]
    try:
        rep = resolver.check(BIND)
    except Exception as exc:                                     # noqa: BLE001
        return ["  compatibility: NOT CHECKED, resolve.check failed (%s)" % exc]
    tman_p = ROOT / resolver.TEAM_MANIFEST
    tman = _json_or_none(tman_p)
    requires = (tman or {}).get("requires")
    decl, warns = [], []
    if not requires:
        warns.append("  WARN %s is %s (Obsidian Sync does not carry dot folders), so "
                      "what this myPKA requires is unknown; running as icor-concepts/1, "
                      "unverified. Not a refusal." % (resolver.TEAM_MANIFEST,
                                                       "missing" if tman is None else "without requires"))
    for sid in sorted(BIND.sources):
        src = BIND.sources[sid]
        if not src.serves:
            continue
        man = src.manifest or {}
        if man.get("implements"):
            decl.append("source %s implements %s (from %s)"
                        % (sid, man["implements"], src.root / resolver.ICOR_MANIFEST))
        elif src.implements:
            decl.append("source %s implements %s (from sources.yaml, unverified)" % (sid, src.implements))
        else:
            decl.append("source %s declares no version" % sid)
        if src.kind == "folder" and src.marker and src.manifest is None:
            warns.append("  WARN %s is missing on this device (Obsidian Sync does not carry "
                         "dot folders); source %s runs as icor-concepts/1, unverified. "
                         "Not a refusal." % (src.root / resolver.ICOR_MANIFEST, sid))
    head = "myPKA requires %s; %s" % (requires or "icor-concepts/1 (assumed)",
                                     "; ".join(decl) or "no source declares a version")
    short = []
    for row in rep.get("concepts", []):
        st, cid = row.get("status"), row.get("concept")
        if st == "bound":
            continue
        if st == "fallback" and cid == "wip":
            short.append((cid, K4V_LINE))
        elif st == "fallback":
            short.append((cid, "no source serves it; falls back to %s" % row.get("fallback")))
        elif st == "degraded" and row.get("missing"):
            short.append((cid, "lacks %s" % ", ".join(row["missing"])))
        elif st == "degraded":
            short.append((cid, "a capability it needs is missing"))
        elif st == "unbound":
            short.append((cid, "no source serves it and it has no fallback"))
        else:
            err = row.get("error") or {}
            short.append((cid, "%s %s" % (err.get("code", "error"), err.get("detail", ""))))
    if short:
        out = ["  compatibility: DEGRADED, missing %s. %s" % (", ".join(c for c, _ in short), head)]
        out += ["    %s: %s" % (c, why) for c, why in short]
    else:
        out = ["  compatibility: COMPATIBLE%s, %s" % (" (unverified, see WARN)" if warns else "", head)]
    out += warns
    rw = [w for w in rep.get("warnings", []) if w != "W_ROOT_EXPLICIT_UNMARKED"]
    if rw:
        out.append("    resolver warnings: %s" % ", ".join(rw))
    return out


PACKS_SHOWN = 40
# What may reach the model from a pack folder, Vex C2 X1. The folder arrives
# in an untrusted zip and this output is injected at every session start,
# before any review: a folder named like an instruction was printed as one.
# A legal pack id is the installer's own rule; a zip or a receipt file name
# is plain characters; everything else is replaced, never quoted.
_ID_OK = re.compile(r"[a-z][a-z0-9-]{0,79}")
_NAME_OK = re.compile(r"[A-Za-z0-9._-]{1,80}")
_HIDDEN = "(a folder with an illegal pack name, not shown: run expansion-pack.py list)"


def _shown(v, ok=_ID_OK):
    v = str(v)
    return v if ok.fullmatch(v) else _HIDDEN


def pack_lines(r):
    """One line per pack under 06 AI Team/Expansions/, read from the JSON
    `expansion-pack.py list` prints.

    Until 6.0.2 this printed the first eight lines of that JSON as text. One
    pack takes four lines, so a folder holding the four single-agent packs
    showed the first pack whole, half of the second and nothing of the other
    two: a pack a member dropped in was never announced (C2, 2026-09-26).
    """
    text = (r.stdout or "").strip()
    try:
        rows = json.loads(text) if r.returncode == 0 else None
    except ValueError:
        rows = None
    if not isinstance(rows, list):
        why = (r.stderr.strip() or text or "no output").splitlines()
        return ["  expansion packs: NOT LISTED, expansion-pack.py list exit %d: %s"
                % (r.returncode, why[0][:200] if why else "no output")]
    if not rows:
        return ["  expansion packs: none in 06 AI Team/Expansions/"]
    new = sum(1 for x in rows if isinstance(x, dict) and x.get("status") != "installed-files")
    out = ["  expansion packs: %d found, %d not installed%s"
           % (len(rows), new, " (a new pack starts WS-1006: inspect and explain, never run it)"
              if new else "")]
    for x in rows[:PACKS_SHOWN]:
        x = x if isinstance(x, dict) else {"id": "", "status": "unreadable-row"}
        extra = ""
        if x.get("ignored_in_pack_receipts"):
            extra = ", ignored in-pack receipt(s): %s" % ", ".join(
                _shown(n, _NAME_OK) for n in x["ignored_in_pack_receipts"])
        ok = _NAME_OK if x.get("status") == "needs-safe-extraction" else _ID_OK
        out.append("    %s: %s%s" % (_shown(x.get("id"), ok), _shown(x.get("status"), _NAME_OK), extra))
    if len(rows) > PACKS_SHOWN:
        out.append("    and %d more: run expansion-pack.py list" % (len(rows) - PACKS_SHOWN))
    return out


def main():
    lines = ["Session start ritual (run by the SessionStart hook, not by the model):"]

    # REFUSE FIRST, WRITE NOTHING (plan step 9). This runs before
    # record_session() and before any child, so a refused start leaves the
    # tree exactly as it found it.
    why = refusal()
    if why:
        msg = ("  compatibility: REFUSED (exit %d), E_SCHEMA_MISMATCH: %s.\n"
               "    Nothing was written: no session.json, no quality.json, no life "
               "snapshot, no child script run.\n"
               "    %s Check with: "
               "python3 \"06 AI Team/AI Team Knowledge/Scripts/resolve.py\" --check"
               % (REFUSE_EXIT, why, refusal_advice(why)))
        print("\n".join(lines) + "\n" + msg)
        print(msg.strip(), file=sys.stderr)
        return REFUSE_EXIT

    sid = record_session()
    lines.append("  session id: %s" % sid)
    lines.extend(compatibility_lines())
    if BIND_ERR:
        lines.append("  binding: NOT LOADED, %s. Content tools are skipped; "
                     "run resolve.py --check." % BIND_ERR)
    # NOTHING INSIDE THE SESSION SAID THE GUARDS WERE OFF (Silas's Codex
    # re-run 2026-09-14/15, R2). The trust state is readable from `doctor` and
    # from the block at the top of .codex/config.toml, and across four
    # hooks-OFF Codex runs no model opened either, so neither line entered any
    # transcript and a scripted run reported a clean pass with no guard behind
    # it. This script already knew: it had to mint its own id precisely
    # BECAUSE no hook payload arrived. That fact was sitting in session.json
    # and nothing told anyone to read it as a trust signal. Now it is a line.
    if _no_host_session_id(sid):
        lines.append("  GUARDS: no host session id received, so this ritual was "
                     "run by hand and not by a hook. On Codex that means the "
                     "project hooks are UNTRUSTED and every guard is OFF for "
                     "this session (codex exec never asks). Report this line, "
                     "and run `scaffold-init.py doctor` for the trust state.")

    r, err = run("check-onboarding.py")
    if err:
        lines.append("  onboarding: NOT CHECKED, %s" % err)
    else:
        lines.append("  onboarding: %s" % (r.stdout.strip() or r.stderr.strip() or "no output"))

    if quality_is_stale():
        path, err = tool("check-quality")
        r = None
        if path is not None:
            r, err = run(path, str(LIFE), "--write")
        note = "refreshed"
    else:
        r, err = None, None
        note = "already current for today"
    q = (LIFE_STATE / "quality.json") if LIFE_STATE is not None else None
    if err:
        lines.append("  vault health: NOT MEASURED, %s" % err)
    elif q is not None and q.is_file():
        try:
            data = json.loads(q.read_text(encoding="utf-8"))
            bad = [m["id"] for m in data.get("metrics", [])
                   if m.get("severity") in ("attention", "broken")]
            lines.append("  vault health: %s (%s)%s" % (
                data.get("health", "unknown"), note,
                ("; " + ", ".join(bad)) if bad else ""))
        except (ValueError, OSError) as exc:
            lines.append("  vault health: quality.json unreadable (%s)" % exc)
    else:
        lines.append("  vault health: quality.json was not written")

    r, err = run("expansion-pack.py", "list")
    if err:
        lines.append("  expansion packs: NOT LISTED, %s" % err)
    else:
        lines.extend(pack_lines(r))

    lines.extend(life_snapshot_lines())

    lines.append("  " + last_receipt_line())
    lines.append("  still yours: read your contract, walk Tasks/open and "
                 "Tasks/in-progress, look at the inbox and today's scratchpad "
                 "(concepts inbox and scratchpad).")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never stop a session from starting
        print("Session start ritual did not run (%s: %s). Run check-onboarding.py, "
              "check-quality.py --write and expansion-pack.py list by hand."
              % (type(exc).__name__, exc))
        sys.exit(0)
