#!/usr/bin/env python3
"""Copy ONE external file into the scaffold, with the rules enforced.

Usage:
  import-file.py <source-file> --dest "concept:topics/Some Topic.md" \
      [--manifest <manifest.md>]
  (--dest also takes a path relative to the content source's root)

Guards (code, not prose):
  - destination must be INSIDE one of the importable rooms (never the
    root, never .obsidian, never outside the scaffold). The rooms are the
    ones the content concepts resolve to (GL-1013), plus the team's own
    room; never a tuple of room names.
  - refuses to overwrite an existing file
  - binary files may only land in a binary concept's room (assets)
  - .md files may not land there
  - appends a line to the import manifest when given
"""
import argparse, datetime, importlib.util, os, shutil, sys
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
# Content rooms live in the content source (mode A: this folder; mode B: the
# sibling). The team's room stays under the team root.
try:
    BIND = resolver.load(ROOT)
    LIFE = resolver.source_root("notes", bindings=BIND)
except resolver.ResolveError as e:
    raise SystemExit("FAIL %s" % e)
# The team's room: the first folder of the agents concept (GL-1013).
TEAM_ROOM = resolver.team_path("agents", bindings=BIND).relative_to(BIND.root.path).parts[0]
# Concepts an import never lands in. `databases` stays out on purpose:
# nothing there has a markdown source, so nothing is imported into it. The
# planner stays IN: it writes notes a member imports alongside everything
# else, and leaving it out refused every Planner destination (Brian Carroll,
# T16-2 / Andrew Gillley, T13-6).
NOT_IMPORTED = ("databases",)


def _content_rooms():
    """{room: [concept, ...]} for every source-side content concept this
    binding serves from a folder under LIFE: the room is the first folder of
    the concept's resolved home. A concept on no folder source has no room."""
    rooms = {}
    life = Path(LIFE).resolve()
    for cid in sorted(BIND.schema.content):
        c = BIND.schema.content[cid]
        if c.side != "source" or cid in NOT_IMPORTED:
            continue
        try:
            home = resolver.resolve_path(cid, bindings=BIND).resolve()
            parts = home.relative_to(life).parts
        except (resolver.ResolveError, ValueError):
            continue
        if parts:
            rooms.setdefault(parts[0], []).append(cid)
    return rooms


CONTENT_ROOMS = _content_rooms()
# Binary files land only in the room of a concept that needs `binary`.
BINARY_ROOMS = {room for room, cids in CONTENT_ROOMS.items()
                if any("binary" in BIND.schema.content[c].needs for c in cids)}
ROOMS = tuple(sorted(CONTENT_ROOMS)) + (TEAM_ROOM,)

ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--dest", required=True)
ap.add_argument("--manifest")
ap.add_argument("--mtime-from", help="original source file whose modification time the landed file must carry (for converted notes; straight copies already keep it via copy2)")
a = ap.parse_args()

src = Path(a.source).expanduser()
if not src.is_file():
    sys.exit(f"FAIL no such source file: {src}")
# --dest takes a room path or a concept ref (GL-1013 section 2.4):
#   a path relative to the content source root, or "concept:notes/x.md".
if a.dest.startswith("concept:"):
    try:
        dest = resolver.resolve_ref(a.dest, bindings=BIND).resolve()
    except resolver.ResolveError as e:
        sys.exit("FAIL %s" % e)
    base = ROOT if str(dest).startswith(str(ROOT.resolve()) + "/" + TEAM_ROOM) else LIFE
else:
    base = ROOT if Path(a.dest).parts[:1] == (TEAM_ROOM,) else LIFE
    dest = (base / a.dest).resolve()
try:
    rel = dest.relative_to(base.resolve())
except ValueError:
    sys.exit(f"FAIL destination escapes the scaffold: {dest}")
if not rel.parts or rel.parts[0] not in ROOMS:
    sys.exit("FAIL destination must be inside one of the importable rooms "
             f"({', '.join(ROOMS)}): {rel}")
if dest.exists():
    sys.exit(f"FAIL destination exists, refusing to overwrite: {rel}")
is_md = src.suffix.lower() in (".md", ".markdown", ".txt")
_bin = ", ".join(sorted(BINARY_ROOMS)) or "none bound"
if not is_md and (base is ROOT or rel.parts[0] not in BINARY_ROOMS):
    sys.exit(f"FAIL binary files may only be imported into the assets concept ({_bin}): {rel}")
if is_md and base is not ROOT and rel.parts[0] in BINARY_ROOMS:
    sys.exit(f"FAIL notes may not be imported into the assets concept ({_bin}): {rel}")

dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dest)
if a.mtime_from:
    ref = Path(a.mtime_from).expanduser()
    if not ref.exists():
        sys.exit(f"FAIL --mtime-from does not exist: {ref}")
    st = ref.stat()
    os.utime(dest, (st.st_atime, st.st_mtime))
if a.manifest:
    m = Path(a.manifest)
    with m.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.date.today()} `{src}` -> `{rel}`\n")
print(f"OK imported -> {rel}")
