#!/usr/bin/env python3
"""Create (or re-stamp) the progress report inside a WiP work folder.

The folder is the `wip` concept, resolved (GL-1013): `concept:wip/<bucket>/...`
in the content source that serves wip. Where no source serves wip, the report
attaches to its task instead (ruling k4v): give --task and it lands in
`Tasks/<state>/<task-stem>/deliverables/progress-report.md`, the task being
promoted into its folder first by `new-task.py promote`.

Usage:
  new-progress-report.py --wip 2026-08-29-access-levels \
      --title "Four-level access rollout" \
      --phase "0 Foundations" --phase "1 Free tier opens" \
      [--plan "[[plan-access-levels]]"]
  new-progress-report.py --wip 2026-08-29-access-levels --touch
  new-progress-report.py --task 2026-09-24-demo --phase "One"   (no wip source)

Deterministic parts owned here: location, filename, frontmatter, the
mermaid skeleton, the scoreboard rows, the legend, the updated stamp.
The model writes the phase names, what each delivers, the decisions,
and the log entries.
"""
import argparse, datetime, importlib.util, os, re, subprocess, sys
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


def _safe_dest(dest, limit):
    """The report file itself stays inside its home (Vex step 5 residual 1).

    --wip and the task stem are checked before this, but the LEAF was not: a
    `progress-report.md` symlink planted in the work folder carried the write
    to wherever it pointed (Vex wrote `outside/pwn.md` in mode B). So the
    leaf may not be a symlink at all, and its real path must stay inside
    `limit`: the wip home when a source serves wip, the Tasks/ tree on the
    k4v fallback."""
    if dest.is_symlink():
        sys.exit("FAIL %s is a symlink; the progress report is written only as "
                 "a plain file inside its home, never through a link" % dest)
    if not resolver._within(dest, limit):
        sys.exit("FAIL %s resolves outside %s; refused" % (dest, limit))


def _write_report(dest, text, create):
    """Write without following a leaf symlink, even one planted between the
    check above and this call: O_NOFOLLOW refuses a link, and a create adds
    O_EXCL, which refuses any existing name, a dangling link included."""
    flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    flags |= (os.O_CREAT | os.O_EXCL) if create else os.O_TRUNC
    try:
        fd = os.open(str(dest), flags, 0o644)
    except OSError as e:
        sys.exit("FAIL could not write %s without following a link (%s)" % (dest, e.strerror or e))
    with os.fdopen(fd, "wb") as fh:
        fh.write(text.encode("utf-8"))


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


ap = argparse.ArgumentParser()
ap.add_argument("--wip",
                help="path inside the wip concept, bucket included, "
                     "e.g. Operations/2026-09-18-broken-sync")
ap.add_argument("--title")
ap.add_argument("--phase", action="append", default=[])
ap.add_argument("--plan")
ap.add_argument("--touch", action="store_true", help="only re-stamp updated")
ap.add_argument("--task", help="the task this work belongs to; used when no source serves wip (k4v)")
ap.add_argument("--root", help="team root (defaults to the resolver's root discovery)")
a = ap.parse_args()

root = _team_root(a.root)
# --task is a task SLUG, never a path or a pattern (Vex step 5, F11): checked
# here, before anything runs, by the same rule the resolver's lookup uses.
if a.task is not None:
    try:
        a.task = resolver.task_stem(a.task)
    except resolver.ResolveError as e:
        sys.exit("FAIL %s" % e.detail)
# --wip names a folder INSIDE the wip home: relative, no `..`, and its real
# path stays there (Vex step 5, F7). Until 2026-09-24 an absolute path or
# `../..` wrote the report outside both roots.
if a.wip is not None:
    _w = a.wip.replace("\\", "/")
    if not _w or Path(_w).is_absolute() or _w.startswith("~") or any(
            part in ("..", ".") for part in _w.split("/")):
        sys.exit("FAIL --wip must be a path inside the wip concept (bucket/work folder), "
                 "never absolute and never with . or ..: %s" % a.wip)
try:
    r = resolver.resolve("wip", task_id=a.task, bindings=resolver.load(root))
except resolver.ResolveError as e:
    sys.exit("FAIL %s" % e)
if r.status == "fallback":
    # k4v: no wip room in reach; the report is a task artifact.
    if r.needs_promotion and not a.touch:
        # The same team root this run resolved, named explicitly (Vex step 5,
        # F6), and the task by its stem only.
        p = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "new-task.py"),
                            "--root", str(root), "promote", Path(a.task).stem],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit("FAIL could not promote task %s: %s" % (a.task, (p.stderr or p.stdout).strip()))
        r = resolver.resolve("wip", task_id=a.task, bindings=resolver.load(root))
    folder, shown = r.path, "task %s deliverables" % a.task
    limit = resolver.team_path("tasks", root=root)
else:
    if not a.wip:
        sys.exit("FAIL give --wip <bucket>/<work folder>")
    folder, shown = r.path / a.wip, "concept:wip/%s (%s)" % (a.wip, r.path / a.wip)
    if not resolver._within(folder, r.path):
        sys.exit("FAIL --wip %s leaves the wip home %s" % (a.wip, r.path))
    limit = r.path
dest = folder / "progress-report.md"
now = datetime.datetime.now()

if not folder.is_dir():
    sys.exit(f"FAIL no such WiP folder: {shown}")
_safe_dest(dest, limit)

if a.touch:
    if not dest.exists():
        sys.exit(f"FAIL no progress report to stamp: {shown}")
    text, _eol = noteio.read_note(dest)
    # [^\r\n]* rather than .* : `.` matches a carriage return, so on a CRLF
    # report the old pattern ate the \r and left one lone LF line behind.
    new, n = re.subn(r"(?m)^updated:[^\r\n]*", f"updated: {now:%Y-%m-%d %H:%M}", text, count=1)
    if not n:
        sys.exit("FAIL progress report has no updated field")
    _write_report(dest, new, create=False)
    print(f"OK stamped {dest}")
    sys.exit(0)

if dest.exists():
    sys.exit(f"FAIL progress report already exists: {shown}/progress-report.md")
if not a.phase:
    sys.exit("FAIL give at least one --phase")
if len(a.phase) > 9:
    sys.exit(f"FAIL {len(a.phase)} phases: a diagram past 9 nodes stops being readable, split the work")

# Mermaid: state lives in the label, never in a color (06 AI Team/README.md,
# authoring rule 3). The one RUNNING phase carries the single :::mark accent.
lines, ids = [], [f"p{i}" for i in range(len(a.phase))]
for i, (nid, name) in enumerate(zip(ids, a.phase)):
    state = "RUNNING" if i == 0 else "QUEUED"
    mark = ":::mark" if i == 0 else ""
    node = f'{nid}["{name} - {state}"]{mark}'
    lines.append(f"    {node}" if i == 0 else f"    {ids[i-1]} --> {node}")
diagram = "\n".join(lines)
rows = "\n".join(
    f"| {name} | | {'RUNNING' if i == 0 else 'QUEUED'} |" for i, name in enumerate(a.phase)
)
title = a.title or (a.wip or a.task or "work").replace("-", " ")
plan = f'plan: "{a.plan}"\n' if a.plan else ""

_write_report(dest, f"""---
type: progress-report
status: live
created: {now:%Y-%m-%d}
updated: {now:%Y-%m-%d %H:%M}
{plan}---

# {title}: progress

Glance, do not read. Legend: DONE / RUNNING / QUEUED / BLOCKED.

```mermaid
flowchart TD
{diagram}
```

## Scoreboard

| Phase | What it delivers | Status |
| --- | --- | --- |
{rows}

## Decisions

-

## Log

### {now:%Y-%m-%d %H:%M}
- Work started.
""", create=True)
print(f"OK created {dest}")
