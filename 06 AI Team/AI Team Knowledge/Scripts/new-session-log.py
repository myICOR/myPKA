#!/usr/bin/env python3
"""Create a session log skeleton in Session Logs/YYYY/MM/.

Usage:
  new-session-log.py --agent larry --slug scaffold-build \
      [--datetime "2026-08-27 21:30"]

Deterministic parts owned here: location, filename, frontmatter skeleton.
The model writes the content into the created file afterwards.
"""
import argparse, datetime, importlib.util, re, sys
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
        return resolver.find_team_root(explicit=explicit, start=__file__).path
    except resolver.ResolveError as e:
        raise SystemExit("FAIL %s" % e)


ROOT = _team_root()
LOGS = resolver.team_path("session_logs", root=ROOT)

ap = argparse.ArgumentParser()
ap.add_argument("--agent", required=True)
ap.add_argument("--slug", required=True)
ap.add_argument("--datetime", dest="dt")
a = ap.parse_args()

if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+){0,7}", a.slug):
    sys.exit(f"FAIL slug must be lowercase-hyphenated: {a.slug}")
dt = datetime.datetime.strptime(a.dt, "%Y-%m-%d %H:%M") if a.dt else datetime.datetime.now()
dest = LOGS / f"{dt:%Y}" / f"{dt:%m}" / f"{dt:%Y-%m-%d-%H-%M}_{a.agent}_{a.slug}.md"
if dest.exists():
    sys.exit(f"FAIL log already exists: {dest.name}")
dest.parent.mkdir(parents=True, exist_ok=True)
noteio.write_note(dest, f"""---
type: session-log
date: {dt:%Y-%m-%d}
agents: [{a.agent}]
---

# Session: {a.slug.replace("-", " ")}

## What happened

## Decisions

## Open threads
""")
print(f"OK created {dest}")
