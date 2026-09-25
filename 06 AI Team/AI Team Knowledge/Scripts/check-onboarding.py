#!/usr/bin/env python3
"""Detect whether this scaffold has been onboarded, deterministically.

Usage:
  check-onboarding.py            -> report status, exit 0 onboarded / 2 fresh
  check-onboarding.py --complete -> write the onboarding marker (once)

Fresh-vault signals (all checkable): no onboarding marker, and no user
content beyond the shipped example notes (tagged `example`).
"""
import argparse, datetime, importlib.util, json, sys
from pathlib import Path

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
# The member's notes live in the content source: this folder in mode A,
# the sibling in mode B (GL-1013 section 8).
try:
    BIND = resolver.load(ROOT)
except resolver.ResolveError as e:
    raise SystemExit("FAIL %s" % e)
# The marker sits in the team's knowledge folder, the scripts concept's parent.
MARKER = resolver.team_path("scripts", bindings=BIND).parent / ".onboarded"
# The member's knowledge: the Inner World concepts, each resolved, so the
# count follows the concept wherever a source keeps it (Ada step 8, F4).
KNOWLEDGE_CONCEPTS = ("journal", "notes", "people", "companies", "key_elements",
                      "goals", "projects", "habits", "topics", "journey_notes")

ap = argparse.ArgumentParser()
ap.add_argument("--complete", action="store_true")
a = ap.parse_args()

if a.complete:
    if MARKER.exists():
        sys.exit("FAIL already onboarded; marker exists")
    MARKER.write_text(json.dumps({"onboarded": str(datetime.date.today())}) + "\n")
    print(f"OK marker written: {MARKER.name}")
    sys.exit(0)

def knowledge_homes():
    """The resolved folders of KNOWLEDGE_CONCEPTS, outermost only, so a home
    nested inside another is not counted twice. A concept no folder source
    serves has no home here."""
    homes = []
    for cid in KNOWLEDGE_CONCEPTS:
        try:
            homes.append(resolver.resolve_path(cid, bindings=BIND).resolve())
        except resolver.ResolveError:
            continue
    homes = sorted(set(homes), key=lambda h: len(h.parts))
    out = []
    for h in homes:
        if not any(h == o or o in h.parents for o in out):
            out.append(h)
    return out


def user_notes():
    n = 0
    for f in (x for home in knowledge_homes() if home.is_dir() for x in home.rglob("*.md")):
        if f.name == "README.md":
            continue
        if "tags: [example]" in f.read_text(encoding="utf-8", errors="ignore"):
            continue
        n += 1
    return n

signals = {
    "marker": MARKER.exists(),
    "inner_world_notes": user_notes(),
    "session_logs": sum(1 for _ in resolver.team_path("session_logs", bindings=BIND).rglob("*.md")),
}
print(json.dumps(signals))
if signals["marker"]:
    print("OK onboarded")
    sys.exit(0)
print("FRESH not onboarded: run the onboarding workstream (WS-1003)")
sys.exit(2)
