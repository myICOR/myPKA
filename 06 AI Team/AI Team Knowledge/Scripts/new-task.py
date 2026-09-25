#!/usr/bin/env python3
"""Create or move a task through Tasks/{open,in-progress,done,cancelled}.

Usage:
  new-task.py [--root TEAM_ROOT] new --slug seed-example-notes \
      --title "Seed example notes" --assignee penn [--due 2026-09-20] \
      [--related "[[WS-1005]]"]
  new-task.py [--root TEAM_ROOT] move <task-name> --to in-progress|done|cancelled
  new-task.py [--root TEAM_ROOT] promote <task-name>

<task-name> is the task's slug, with or without `.md`: never a path, never
a pattern (Vex step 5, F6 and F11). It must match exactly one task file under
Tasks/<state>/, and a file inside a `deliverables/` folder is never a task.
Until 2026-09-24 any existing file was accepted, and `move AGENTS.md --to
done` moved the root contract out of the team root.

Deterministic parts owned here: location, filename, status field kept in
sync with the folder, done/cancelled filed under YYYY/MM/.

PROMOTION (GL-1013 section 2.3, ruling k4v). Where no source serves `wip`, a
deliverable attaches to its task. A task with no deliverable stays one file;
on its first attachment `promote` turns it into a folder
`Tasks/<state>/<stem>/<stem>.md` plus `deliverables/`. resolve.py reports
`needs_promotion` and never moves anything; this script does the move. A
promoted task travels as a folder through every later `move`.
"""
import argparse, datetime, importlib.util, re, shutil, sys
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
        r = resolver.find_team_root(explicit=explicit, start=__file__)
    except resolver.ResolveError as e:
        raise SystemExit("FAIL %s" % e)
    for w in r.warnings:
        print(w, file=sys.stderr)
    return r.path


STATES = ("open", "in-progress", "done", "cancelled")

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=None,
                help="team root (default: the resolver's root discovery, GL-1013 section 6)")
sub = ap.add_subparsers(dest="cmd", required=True)
n = sub.add_parser("new")
n.add_argument("--slug", required=True)
n.add_argument("--title", required=True)
n.add_argument("--assignee", required=True)
# GL-1002 lists `due` as a valid optional task field and this script could not
# write it, so both pilot CLIs generated the file and then hand-edited the one
# they had just generated (on Codex through a shell heredoc, which is invisible
# to the write guard). A generated file that has to be hand-finished on the
# next step is a hole in the tool, not a step in the procedure.
n.add_argument("--due", default=None,
               help="ISO date, YYYY-MM-DD. Optional (GL-1002)")
n.add_argument("--related", action="append", default=[],
               help='a wikilink this task belongs to, e.g. "[[WS-1005]]". Repeatable')
m = sub.add_parser("move")
m.add_argument("task")
# Every state, `open` included. `move --to open` is how a task comes back
# out of in-progress when the work is parked, and the argument parser used to
# reject it with no way round it (Brian Carroll, T16-13).
m.add_argument("--to", required=True, choices=STATES)
pr = sub.add_parser("promote")
pr.add_argument("task")
a = ap.parse_args()

ROOT = _team_root(a.root)
TASKS = resolver.team_path("tasks", root=ROOT)


def find_task(name):
    """The one task file named `name`: a task slug, with or without `.md`.
    The lookup is resolve.py's locate_task, the same one the wip fallback
    uses, so "the task" has one definition."""
    try:
        _stem, hits = resolver.locate_task(TASKS, name)
    except resolver.ResolveError as e:
        sys.exit("FAIL %s" % e.detail)
    if len(hits) != 1:
        sys.exit(f"FAIL found {len(hits)} tasks named {name} under Tasks/<state>/")
    return hits[0][1]


def is_promoted(task_file):
    return task_file.parent.name == task_file.stem and task_file.parent.name not in STATES

today = datetime.date.today()
if a.cmd == "new":
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+){0,7}", a.slug):
        sys.exit(f"FAIL slug must be lowercase-hyphenated: {a.slug}")
    if a.due is not None:
        try:
            datetime.date.fromisoformat(a.due)
        except ValueError:
            sys.exit(f"FAIL --due must be an ISO date, YYYY-MM-DD: {a.due}")
    for w in a.related:
        if not (w.startswith("[[") and w.endswith("]]")):
            sys.exit(f"FAIL --related must be a wikilink: {w}")
    dest = TASKS / "open" / f"{today}-{a.slug}.md"
    if dest.exists():
        sys.exit(f"FAIL task already exists: {dest.name}")
    related = ("related: []" if not a.related
               else "related:\n" + "\n".join(f'  - "{w}"' for w in a.related))
    due = f"due: {a.due}\n" if a.due else ""
    noteio.write_note(dest, f"""---
type: task
status: open
assignee: {a.assignee}
created: {today}
{due}{related}
---

# {a.title}
""")
    print(f"OK created {dest}")
elif a.cmd == "promote":
    cand = find_task(a.task)
    if is_promoted(cand):
        (cand.parent / "deliverables").mkdir(exist_ok=True)
        print(f"OK {cand.stem} is already a folder")
        sys.exit(0)
    folder = cand.parent / cand.stem
    if folder.exists():
        sys.exit(f"FAIL {folder.name}/ already exists beside the task file")
    (folder / "deliverables").mkdir(parents=True)
    cand.rename(folder / cand.name)
    print(f"OK promoted {cand.stem} -> {cand.stem}/{cand.name} + deliverables/")
else:
    cand = find_task(a.task)
    if a.to in ("done", "cancelled"):
        dest_dir = TASKS / a.to / f"{today:%Y}" / f"{today:%m}"
    else:
        dest_dir = TASKS / a.to
    dest_dir.mkdir(parents=True, exist_ok=True)
    text, _eol = noteio.read_note(cand)
    if f"status: {a.to}" not in text:
        # [^\r\n]* rather than .* : `.` matches a carriage return, so on a
        # CRLF task file the old pattern swallowed the \r and turned that one
        # line into a lone LF inside an otherwise CRLF file.
        text = re.sub(r"^status:[^\r\n]*", f"status: {a.to}", text, count=1, flags=re.M)
    if is_promoted(cand):
        # A promoted task moves as its folder, deliverables and all.
        dest = dest_dir / cand.stem
        if dest.resolve() == cand.parent.resolve():
            sys.exit(f"FAIL {cand.stem} is already in {a.to}")
        if dest.exists():
            sys.exit(f"FAIL destination already holds {cand.stem}/")
        noteio.write_note(cand, text)
        shutil.move(str(cand.parent), str(dest))
        print(f"OK moved {cand.stem}/ -> {a.to}")
        sys.exit(0)
    dest = dest_dir / cand.name
    if dest.resolve() == cand.resolve():
        sys.exit(f"FAIL {cand.name} is already in {a.to}")
    if dest.exists():
        sys.exit(f"FAIL destination already holds {cand.name}")
    noteio.write_note(dest, text)
    cand.unlink()
    print(f"OK moved {cand.name} -> {a.to}")
