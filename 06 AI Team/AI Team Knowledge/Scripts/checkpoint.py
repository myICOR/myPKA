#!/usr/bin/env python3
"""checkpoint.py: the deterministic half of a session checkpoint (WS-1005).

Answers, from the files alone, the questions a checkpoint asks:

  1. Which tasks moved this session?  Every task file changed since this
     session STARTED (`.mypka/state/session.json`), falling back
     to the last session log's own name where no session start hook ran,
     in all four states: Tasks/open/, Tasks/in-progress/,
     and the date-nested Tasks/done/YYYY/MM/ and Tasks/cancelled/YYYY/MM/.
     A task closed earlier in the same session lives in done/ by the time
     the checkpoint runs, and until 2026-09-07 it was invisible here (the
     report said `tasks touched : 0` for a session that shipped one;
     reported by Andrew Gillley from a 1.10.2 vault).
  2. Which work in WiP could leave?  Every piece of work in the wip concept (not
     _archive) whose newest file is older than --window days AND which no
     open or in-progress task mentions. Both facts are printed for every
     entry; the flag is only the intersection. The four buckets
     (the wip room's README.md, 2026-09-17) are never candidates themselves; the
     scan steps into them and reports the dated work inside, which inside
     a bucket is a folder OR a single .md file. Workstreams/<Name>/ is
     standing too, because a process has no finish line to leave against,
     so only its dated runs can be flagged; Projects/<name>/ is the unit
     that leaves, with its Project. A bucket's own README.md is never
     reported. Operations/ is reported first: it is the bucket nothing
     closes from the outside, so it is where work goes stale unnoticed.
  3. Is there a session log for today?
  4. How many date mentions still are not linked to their daily note?
     Asked of link-dates-to-daily-notes.py --check, not re-implemented here,
     so GL-1011's scope has one home.

It decides nothing (GL-1005): the operator reads the report and rules.
Exit 0 always, except the asserts, which exit 1 with a FAIL line.

THE COMPLETION RECEIPT, AND WHY --assert-logged CHANGED
-------------------------------------------------------
Until 2026-09-14 --assert-logged asked one question: is there a file in
Session Logs/ whose name starts with today's date. A log written at 09:00
therefore passed the checkpoint of a session that ran at 17:00 and wrote
nothing, and the gate read green for a session that never closed. The check
was bound to the DATE. Sessions are not days.

It is bound to the SESSION now. Closing a session writes a receipt:

  .mypka/state/receipts/<session-id>.json   (schema 1)
    workflow           which workflow this receipt closes (WS-1005)
    session_id         whose session it was
    started, finished  when
    inputs             path -> sha256 of what the work read
    outputs            path -> sha256 of what it wrote, the session log
                       among them
    validator_version  which version of THIS script wrote it
    unresolved         what is knowingly left open

--assert-logged then checks the receipt for THIS session: that it exists,
that it names this script's current validator version, that it names a
session log among its outputs, and that every output it names is still on
disk with the hash it recorded. Yesterday's receipt belongs to yesterday's
session id and cannot answer for this one.

The session id comes from `.mypka/state/session.json`, written by
the SessionStart hook (session-start.py). No environment variable carries a
session id to a script on any host we checked, so where there is no hook
there is no id, and the assert says exactly that instead of guessing.

--assert-logged-today keeps the old behaviour under its true name, for a
runtime with no session start hook. It is WEAKER, by design and by name: it
proves a file exists with today's date on it and nothing else.

WHAT A RECEIPT DOES NOT PROVE
- That the work was any good, or that the log says anything true. It proves
  which bytes were written, by which version, in which session.
- That nothing else changed. Only the paths named in the receipt are
  hashed; a file the checkpoint never listed is invisible to it.
- That the session id is the host's. Where the host sends none, one is
  minted, and the receipt is then bound to a local id rather than a real
  session. session.json records which of the two it was.

Usage:
  Scripts/checkpoint.py [<vault-root>] [--window 30] [--json]
                        [--assert-logged] [--assert-logged-today]
                        [--assert-dates-linked]
  Scripts/checkpoint.py --write-receipt --output "<session log path>" [...]
"""
import argparse, datetime, hashlib, importlib.util, json, os, re, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("root", nargs="?", default=None)
ap.add_argument("--window", type=int, default=30, help="days a WiP folder may sit untouched before it is a candidate to leave")
ap.add_argument("--json", action="store_true")
ap.add_argument("--assert-logged", action="store_true", help="exit 1 unless this session has a completion receipt naming a session log that is still on disk unchanged")
ap.add_argument("--assert-logged-today", action="store_true", help="the pre-2026-09-14 check, kept for runtimes with no session start hook: exit 1 unless SOME session log carries today's date. Weaker: a morning log passes an afternoon checkpoint")
ap.add_argument("--write-receipt", action="store_true", help="write this session's completion receipt")
ap.add_argument("--workflow", default="WS-1005", help="which workflow the receipt closes")
ap.add_argument("--session-id", default=None, help="override the session id from .mypka/state/session.json")
ap.add_argument("--input", action="append", default=[], help="a path the work read; repeatable")
ap.add_argument("--output", action="append", default=[], help="a path the work wrote; repeatable. The session log belongs here")
ap.add_argument("--unresolved", action="append", default=[], help="something knowingly left open; repeatable")
ap.add_argument("--assert-dates-linked", action="store_true", help="exit 1 unless every date mention in scope links to its daily note (GL-1011)")
ap.add_argument("--today", default=None, help="override today's date, YYYY-MM-DD (tests)")
a = ap.parse_args()

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


ROOT = _team_root(a.root)
# The binding: which source serves wip, and the source a content tool reads.
# A root with no binding (no sources.yaml, no ICOR marker) still has team
# memory to check; it simply has no WiP to scan and no dates to count.
try:
    BIND = resolver.load(ROOT)
except resolver.ResolveError:
    BIND = None
TASKS = resolver.team_path("tasks", root=ROOT)
LOGS = resolver.team_path("session_logs", root=ROOT)
WIP = None
if BIND is not None:
    try:
        WIP = resolver.resolve_path("wip", bindings=BIND)
    except resolver.ResolveError:
        WIP = None   # no source serves wip: deliverables sit with their tasks (k4v)
# Team state, ruling j5d: .mypka/state/, no longer .icor-for-life/scripts/.
MACHINE = resolver.team_path("team_state", root=ROOT)
RECEIPTS = MACHINE / "receipts"
# The buckets of the wip room's README.md. Never candidates themselves; the scan
# steps into them and reports the dated work inside. `Reports/` is not
# shipped and is listed anyway, because a member who opens one must not
# have it flagged as a stale folder on the first checkpoint after.
STANDING = ("Workstreams", "Projects", "AI Team", "Operations", "Reports")
# The two buckets that hold a NAMED folder per process or per Project
# rather than dated work directly. The other buckets hold the dated work
# itself, as a file or as a folder.
NAMED = ("Workstreams", "Projects")
# Report order, not filesystem order. `Operations/` is read first because
# it is the bucket nothing closes from the outside: a Project takes its
# folder with it and a Workstream run is finished by the next run, so
# Operations is where work goes stale unnoticed (Tom, 2026-09-17).
BUCKET_ORDER = ("Operations", "Reports", "Workstreams", "AI Team", "Projects")
today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
now = datetime.datetime.combine(today, datetime.time(23, 59))

def mtime(p: Path) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(p.stat().st_mtime)


def mtime_aware(p: Path) -> datetime.datetime:
    """The same instant, carrying the machine's own offset.

    `fromtimestamp()` with no argument returns LOCAL WALL TIME with no
    tzinfo on it, and `.astimezone()` on a naive value attaches the local
    zone rather than converting, which is exactly what is wanted here: the
    number is already local. Only the cutoff comparison needs this; `now`
    and every age in days below stay naive and stay comparable to mtime().
    """
    return datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone()

def newest_under(folder: Path):
    best = None
    for dp, _, fs in os.walk(folder):
        for f in fs:
            t = mtime(Path(dp) / f)
            if best is None or t > best:
                best = t
    return best

# --- 1. the last session log, and today's ---------------------------------
# A session log is named for the moment it covers (GL-1004:
# YYYY-MM-DD-HH-MM_agent_slug.md), and that is the timestamp this scan needs.
# Filesystem mtime is a different fact: a sync tool, a restore from Time
# Machine, a checkout, or the member simply reopening the log to read it all
# move mtime forward. Comparing against mtime therefore put the cutoff in the
# future and the report said `tasks touched : 0` on a session that had
# shipped six of them (Brian Carroll, T16-12). The name is read first and
# mtime is the fallback, for a log a member renamed or wrote by hand.
LOG_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{2})_")


def log_time(p: Path) -> datetime.datetime:
    m = LOG_NAME.match(p.name)
    if m:
        try:
            return datetime.datetime.fromisoformat(
                "%sT%s:%s" % (m.group(1), m.group(2), m.group(3)))
        except ValueError:
            pass
    return mtime(p)


logs = sorted(LOGS.glob("*/*/*.md")) if LOGS.exists() else []
last_log = max(logs, key=log_time) if logs else None
last_log_time = log_time(last_log) if last_log else datetime.datetime.min
todays = [p for p in logs if p.name.startswith(today.isoformat())]

# --- 1b. the cutoff: when THIS session started ----------------------------
# The log's own name is the right cutoff for a report written after the log,
# and the wrong one for the report a checkpoint writes BEFORE it (WS-1005
# runs the report first, then writes the log). Read in that order the log
# name is still the PREVIOUS session's, so work shipped earlier today was
# listed twice: once in the report that preceded the log and again in the
# next session's. Worse in the other direction: once the log exists, a task
# closed earlier in the same session but before the log's own minute sits
# BEHIND the cutoff and disappears from the session that shipped it.
#
# A session knows when it started. session-start.py writes it to
# .mypka/state/session.json as `started`, UTC, with a trailing Z,
# and the receipt half of this script already reads that file. The log name
# stays as the fallback, for a runtime with no session start hook.
#
# Two traps, both of which this handles rather than documents:
#   - `fromisoformat` did not accept a trailing `Z` until Python 3.11, and
#     3.9 is what ships on this machine. The Z is converted, not parsed.
#   - `started` is UTC-aware and mtime() is naive local. Comparing the two
#     raises TypeError on some paths and silently compares wall clocks on
#     none of them, so the comparison is made in aware time on both sides
#     (mtime_aware) and every OTHER use of mtime() is left alone.
# Reported by Brian Carroll (B2-2).
def _parse_started(raw):
    s = str(raw or "").strip()
    if not s:
        return None
    if s[-1] in "Zz":
        s = s[:-1] + "+00:00"
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo is not None else d.replace(tzinfo=datetime.timezone.utc)


def session_started():
    sf = MACHINE / "session.json"
    if not sf.is_file():
        return None
    try:
        return _parse_started(json.loads(sf.read_text(encoding="utf-8")).get("started"))
    except (ValueError, OSError):
        return None


_started = session_started()
cutoff = _started if _started is not None else (
    last_log_time.astimezone() if last_log else
    datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
cutoff_source = "session.json started" if _started is not None else (
    "last session log name" if last_log else "no cutoff (nothing to compare against)")

# --- 2. tasks touched since the last log ----------------------------------
# open/ and in-progress/ are flat; done/ and cancelled/ nest by YYYY/MM/
# (hard rule 6), so those two are walked recursively. Only open and
# in-progress tasks can still reference a WiP folder, so only their text
# feeds the WiP check below.
STATES = ("open", "in-progress", "done", "cancelled")
touched = []
task_texts = []
touched_by_state = {s: 0 for s in STATES}
for state in STATES:
    d = TASKS / state
    if not d.exists():
        continue
    live = state in ("open", "in-progress")
    for f in sorted(d.glob("*.md") if live else d.rglob("*.md")):
        if live:
            task_texts.append(f.read_text(errors="ignore"))
        if mtime_aware(f) > cutoff:
            touched.append({"state": state, "file": f.name,
                            "path": f.relative_to(TASKS).as_posix()})
            touched_by_state[state] += 1
all_task_text = "\n".join(task_texts)

# --- 3. WiP folders: age and task references -------------------------------
wip = []


def wip_row(entry: Path, label: str, standing: bool):
    # newest_under() walks a folder; a single dated FILE is its own newest.
    newest = (mtime(entry) if entry.is_file()
              else (newest_under(entry) or mtime(entry)))
    age = (now - newest).days
    # A task may name the bucket path, the file or folder name, or the
    # name without its extension. All three are the same piece of work.
    referenced = (label in all_task_text or entry.name in all_task_text
                  or (entry.is_file() and entry.stem in all_task_text))
    return {
        "folder": label,
        "days_untouched": max(0, age),
        "referenced_by_open_task": referenced,
        "standing": standing,
        "candidate_to_leave": (not standing) and age > a.window and not referenced,
    }


def wip_child(parent: Path):
    """The entries inside a bucket that are work, in name order.

    A bucket carries one README.md that explains it. That file is not
    work and must never be reported, or every checkpoint would offer to
    archive the documentation of the room it is reporting on.
    """
    for child in sorted(parent.iterdir()):
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if child.is_file() and child.name.lower() == "readme.md":
            continue
        if child.is_dir() or child.suffix.lower() == ".md":
            yield child


if WIP is not None and WIP.exists():
    roots = [e for e in WIP.iterdir()
             if not e.name.startswith("_") and not e.name.startswith(".")]
    # Buckets first, in the order of BUCKET_ORDER; then anything else at
    # the root, which in a vault older than 1.30.0 is undated-bucket work
    # from before the buckets existed and is reported exactly as before.
    def root_key(e: Path):
        if e.is_dir() and e.name in STANDING:
            return (0, BUCKET_ORDER.index(e.name) if e.name in BUCKET_ORDER
                    else len(BUCKET_ORDER), e.name)
        return (1, 0, e.name)

    for entry in sorted(roots, key=root_key):
        if entry.is_dir() and entry.name in STANDING:
            wip.append(wip_row(entry, entry.name, standing=True))
            for child in wip_child(entry):
                label = f"{entry.name}/{child.name}"
                # Workstreams/<Name>/ is itself standing (a process); its
                # dated runs sit one level further down. Projects/<name>/
                # is the unit that leaves, with its Project. Every other
                # bucket holds the dated work itself.
                if entry.name == "Workstreams" and child.is_dir():
                    wip.append(wip_row(child, label, standing=True))
                    for run in wip_child(child):
                        wip.append(wip_row(run, f"{label}/{run.name}", standing=False))
                else:
                    wip.append(wip_row(child, label, standing=False))
            continue
        if not entry.is_dir():
            continue
        wip.append(wip_row(entry, entry.name, standing=False))

# --- 4. date mentions not yet linked to their daily note (GL-1011) --------
# Asked of the script that owns the rule. A count it could not read is
# reported as None, never as 0: a check that reads a source must say when
# it read none.
dates_unlinked = None
# The linker is the content source's own tool, and it reads the content
# source's root (GL-1013 resolve_tool).
linker, LIFE = None, None
if BIND is not None:
    try:
        linker = resolver.resolve_tool("link-dates-to-daily-notes", bindings=BIND)
        LIFE = resolver.tool_source(BIND).root
    except resolver.ResolveError:
        linker = None
if linker is not None and linker.is_file():
    r = subprocess.run([sys.executable, str(linker), str(LIFE), "--check", "--json"],
                       capture_output=True, text=True)
    try:
        # The first JSON object on stdout, not the whole stream. Belt and
        # braces with the linker's own fix: a caller that demands a pure
        # stdout is a caller that reports None the day anything adds a line.
        dates_unlinked = json.JSONDecoder().raw_decode(
            r.stdout[r.stdout.find("{"):])[0]["mentions"]
    except (ValueError, KeyError):
        dates_unlinked = None

report = {
    "today": today.isoformat(),
    "last_session_log": str(last_log.relative_to(ROOT)) if last_log else None,
    "session_log_today": bool(todays),
    # The key keeps its 1.14.0 name so an existing reader does not break,
    # but the cutoff is the session's start when there is one; `cutoff` and
    # `cutoff_source` say which of the two answered.
    "tasks_touched_since_last_log": touched,
    "tasks_touched_by_state": touched_by_state,
    "cutoff": cutoff.isoformat() if last_log or _started else None,
    "cutoff_source": cutoff_source,
    "wip": wip,
    "window_days": a.window,
    "date_mentions_unlinked": dates_unlinked,
}

if a.json:
    print(json.dumps(report, indent=2))
else:
    print(f"checkpoint {today.isoformat()}  (window {a.window} days)")
    print(f"  last session log : {report['last_session_log'] or 'none yet'}")
    print(f"  log for today    : {'yes' if report['session_log_today'] else 'NO'}")
    print(f"  date links       : {'unknown (link-dates-to-daily-notes.py did not answer)' if dates_unlinked is None else str(dates_unlinked) + ' mention(s) unlinked'}")
    print(f"  cutoff           : {report['cutoff'] or 'none'} ({cutoff_source})")
    print(f"  tasks touched    : {len(touched)}"
          + (" (" + ", ".join(f"{s} {n}" for s, n in touched_by_state.items() if n) + ")" if touched else ""))
    for t in touched:
        print(f"    - [{t['state']}] {t['path']}")
    cands = [w for w in wip if w["candidate_to_leave"]]
    print(f"  wip folders      : {len(wip)}, candidates to leave: {len(cands)}")
    for w in wip:
        flag = "LEAVE?" if w["candidate_to_leave"] else ("stand " if w.get("standing") else "keep  ")
        ref = "task" if w["referenced_by_open_task"] else "none"
        print(f"    {flag}  {w['days_untouched']:>4}d  ref:{ref:<4}  {w['folder']}")

# --- 5. the completion receipt (schema 1) ---------------------------------
# Bumped by hand whenever the receipt's meaning changes. A receipt written by
# a different version is refused rather than half-trusted: the fields would
# still parse, and that is exactly what makes a silent version drift
# dangerous.
RECEIPT_SCHEMA = 1
VALIDATOR_VERSION = "checkpoint.py/2026-09-16"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def session_id():
    """This session's id, and where it came from. Never invented here: a
    receipt bound to an id this script made up would bind to nothing."""
    if a.session_id:
        return a.session_id, "--session-id"
    env = os.environ.get("ICOR_SESSION_ID")
    if env:
        return env, "ICOR_SESSION_ID"
    sf = MACHINE / "session.json"
    if sf.is_file():
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            if data.get("schema") == 1 and data.get("session_id"):
                return str(data["session_id"]), "session.json"
        except (ValueError, OSError):
            pass
    return None, None


def hashes(paths):
    out = {}
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / raw
        rel = p.relative_to(ROOT).as_posix() if str(p).startswith(str(ROOT)) else str(p)
        out[rel] = sha256_of(p) if p.is_file() else None
    return out


def receipt_path(sid):
    return RECEIPTS / (re.sub(r"[^A-Za-z0-9._-]", "_", sid) + ".json")


if a.write_receipt:
    sid, how = session_id()
    if not sid:
        print("FAIL: no session id, so a receipt would be bound to nothing. "
              "The SessionStart hook writes .mypka/state/session.json; "
              "on a runtime without hooks, pass --session-id or set ICOR_SESSION_ID.",
              file=sys.stderr)
        sys.exit(1)
    missing = [p for p, h in hashes(a.output).items() if h is None]
    if missing:
        print("FAIL: the receipt names output(s) that are not on disk: "
              + ", ".join(missing), file=sys.stderr)
        sys.exit(1)
    # A receipt records a hash and later asserts the file still matches it, so
    # an output the machine layer rewrites every session is a receipt that is
    # guaranteed to rot. Codex's first pilot session listed session.json and
    # quality.json, and from session 2 onward that receipt could never verify
    # again (pilot B finding F8). This is one line instead of a lesson.
    MACHINE_REL = MACHINE.relative_to(ROOT).as_posix() + "/"
    # Two machine layers since the split (j5d): the team's own state, and the
    # content source's (quality.json, snapshot.json). Both rewrite themselves.
    prefixes = [MACHINE_REL]
    if BIND is not None:
        try:
            _ls = resolver.resolve_path("life_state", bindings=BIND)
            _ls_s = str(_ls)
            prefixes.append((_ls.relative_to(ROOT).as_posix() if _ls_s.startswith(str(ROOT) + os.sep)
                             else _ls_s) + "/")
        except resolver.ResolveError:
            pass
    self_writing = [p for p in hashes(a.output)
                    if any(p.startswith(x) for x in prefixes)]
    if self_writing:
        print("FAIL: the receipt names output(s) the machine layer rewrites on "
              "its own: " + ", ".join(self_writing) + ". Those files change every "
              "session, so a receipt naming them can never verify again. Name "
              "the work: the session log, a note, a deliverable.", file=sys.stderr)
        sys.exit(1)
    started = None
    sf = MACHINE / "session.json"
    if sf.is_file():
        try:
            started = json.loads(sf.read_text(encoding="utf-8")).get("started")
        except (ValueError, OSError):
            started = None
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "workflow": a.workflow,
        "session_id": sid,
        "session_id_source": how,
        "started": started or now_utc.isoformat().replace("+00:00", "Z"),
        "finished": now_utc.isoformat().replace("+00:00", "Z"),
        "inputs": hashes(a.input),
        "outputs": hashes(a.output),
        "validator_version": VALIDATOR_VERSION,
        "unresolved": list(a.unresolved),
    }
    receipt_path(sid).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"OK receipt written: {receipt_path(sid).relative_to(ROOT)} "
          f"({len(receipt['outputs'])} output(s), {len(receipt['unresolved'])} unresolved)")

if a.assert_logged:
    sid, how = session_id()
    if not sid:
        print("FAIL: no session id to check a receipt against. The SessionStart "
              "hook writes .mypka/state/session.json; on a runtime "
              "without hooks use --assert-logged-today (weaker: it only proves "
              "some log carries today's date) or pass --session-id.",
              file=sys.stderr)
        sys.exit(1)
    rp = receipt_path(sid)
    if not rp.is_file():
        print(f"FAIL: session {sid} has no completion receipt at "
              f"{rp.relative_to(ROOT)}; finish WS-1005 and run "
              f"checkpoint.py --write-receipt --output '<the session log>'",
              file=sys.stderr)
        sys.exit(1)
    try:
        rec = json.loads(rp.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"FAIL: the receipt for session {sid} is unreadable ({exc})", file=sys.stderr)
        sys.exit(1)
    problems = []
    if rec.get("schema") != RECEIPT_SCHEMA:
        problems.append(f"it is schema {rec.get('schema')!r}, this script writes {RECEIPT_SCHEMA}")
    if rec.get("validator_version") != VALIDATOR_VERSION:
        problems.append(f"it was written by {rec.get('validator_version')!r}, "
                        f"this script is {VALIDATOR_VERSION!r}")
    if rec.get("workflow") != a.workflow:
        problems.append(f"it closes {rec.get('workflow')!r}, not {a.workflow!r}")
    outputs = rec.get("outputs") or {}
    logs_prefix = LOGS.relative_to(ROOT).as_posix() + "/"
    if not any(p.startswith(logs_prefix) for p in outputs):
        problems.append("it names no session log among its outputs")
    for rel, recorded in sorted(outputs.items()):
        f = ROOT / rel
        if not f.is_file():
            problems.append(f"the output {rel} it names is gone")
        elif recorded and sha256_of(f) != recorded:
            problems.append(f"the output {rel} changed after the receipt was written")
    if problems:
        print(f"FAIL: the completion receipt for session {sid} does not close this "
              f"checkpoint: " + "; ".join(problems), file=sys.stderr)
        sys.exit(1)
    if rec.get("unresolved"):
        print(f"NOTE: the receipt records {len(rec['unresolved'])} unresolved item(s): "
              + "; ".join(str(u) for u in rec["unresolved"]))
    print(f"OK receipt {rp.relative_to(ROOT)} closes {rec.get('workflow')} for session {sid}")

if a.assert_logged_today and not todays:
    print(f"FAIL: no session log for {today.isoformat()} under {LOGS.relative_to(ROOT)}; run new-session-log.py before ending the session", file=sys.stderr)
    sys.exit(1)
if a.assert_dates_linked and dates_unlinked != 0:
    print(f"FAIL: {'could not read' if dates_unlinked is None else dates_unlinked} date mention(s) not linked to their daily note (GL-1011); run link-dates-to-daily-notes.py --fix", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
