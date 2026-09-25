#!/usr/bin/env python3
"""check-room-literals.py: T2 of the myPKA split (GL-1013 section 14). The
team names no ICOR for Life room and no ICOR tool by a path; it reaches both
through the resolver (a `concept:` ref, `resolve.py --tool <name>`).

Usage:
  check-room-literals.py [--root DIR]
    DIR  the top of a myPKA git work tree (default: the one this script is in)

Repo-only. It runs in the myPKA repository, in the release workflow and in
run-red-tests.py (group step16), never in a member's folder.

It runs `git grep --untracked` from DIR, so tracked and untracked files count
and gitignored ones do not. Two patterns, each with the exemptions GL-1013
section 14 states in prose; this file is the one runnable form of them.

Pattern 1, room literals: `0[0-57] (Daily Scratchpad|Inbox|Planner|WiP|Inner
World|Assets|Databases)` in any file. Exempt:
  - whole files: .mypka/icor-concepts-1.json (the schema), Scripts/resolve.py,
    Guidelines/GL-1013-*, Guidelines/GL-1014-*, Scripts/run-red-tests.py,
    Scripts/test-*.py, this file (it states the patterns), and everything
    under Scripts/tests/ (repo-only fixtures, never shipped);
  - a line in Scripts/write-guard.py or Scripts/hooks-rules.json that
    carries `00 Daily Scratchpad/` (the Vex-approved mode A legacy prefix);
  - a line carrying the marker `T2: fixture`;
  - in Scripts/mypka-update.py only: the lines from
    `# BEGIN GENERATED: icor-room-names (build-mypka-manifest.py, do not hand-edit)`
    through the next `# END GENERATED`, both markers included (Vex ruling b:
    written by build-mypka-manifest.py from the schema, checked by its
    --check). One such block, in that one file; nowhere else.

Pattern 2, ICOR tools by a team-side path: `Scripts/(<tool>)\\.py` for every
tool name in the schema's `tools.names`, or `.icor-for-life/scripts`, in any
file that is not a `.py`. Exempt: .git, anything under .mypka/, .gitignore,
Guidelines/GL-1013-*, and everything under Scripts/tests/.

Exit 0 = both patterns print nothing. Exit 1 = hits, one per line as
`pattern N: path:line: text`. Exit 2 = it could not run (no git, not a git
work tree, the schema unreadable); a check that could not run is never a 0.
"""
import json, re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True

SC = "06 AI Team/AI Team Knowledge/Scripts/"
GL = "06 AI Team/AI Team Knowledge/Guidelines/"
SCHEMA = ".mypka/icor-concepts-1.json"
UPDATER = SC + "mypka-update.py"
BEGIN = "# BEGIN GENERATED: icor-room-names (build-mypka-manifest.py, do not hand-edit)"
END = "# END GENERATED"
TESTS = SC + "tests/"

P1 = r"0[0-57] (Daily Scratchpad|Inbox|Planner|WiP|Inner World|Assets|Databases)"
P1_FILES = (SCHEMA, SC + "resolve.py", SC + "run-red-tests.py", SC + "check-room-literals.py")
P1_GLOBS = (re.compile(re.escape(GL) + r"GL-101[34]-[^/]*$"), re.compile(re.escape(SC) + r"test-[^/]*\.py$"))
P1_LEGACY_FILES = (SC + "write-guard.py", SC + "hooks-rules.json")
P1_LEGACY = "00 Daily Scratchpad/"
MARKER = "T2: fixture"


def die(msg):
    print("check-room-literals: " + msg, file=sys.stderr)
    sys.exit(2)


def grep(root, pattern):
    """(path, line_no, text) for every hit, tracked and untracked, gitignored
    files left out. -z keeps paths with spaces and colons whole."""
    try:
        r = subprocess.run(["git", "-C", str(root), "grep", "--untracked", "-I", "-z", "-n", "-E", "-e", pattern,
                            "--", "."], capture_output=True)
    except FileNotFoundError:
        die("git is not installed; T2 is a git grep")
    if r.returncode not in (0, 1):
        die("git grep failed in %s: %s" % (root, r.stderr.decode("utf-8", "replace").strip()[-300:]))
    out = []
    for rec in r.stdout.decode("utf-8", "replace").splitlines():
        parts = rec.split("\0", 2)
        if len(parts) == 3:
            out.append((parts[0], int(parts[1]), parts[2]))
    return out


def generated_lines(root):
    """Line numbers of the one icor-room-names block in the updater, markers
    included. Empty when the file or a marker is missing: then nothing is
    exempt and every literal there counts."""
    p = root / UPDATER
    if not p.is_file():
        return set()
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    begins = [i for i, l in enumerate(lines, 1) if l == BEGIN]
    if len(begins) != 1:
        return set()
    b = begins[0]
    ends = [i for i in range(b + 1, len(lines) + 1) if lines[i - 1] == END]
    return set(range(b, ends[0] + 1)) if ends else set()


def pattern1(root):
    gen = generated_lines(root)
    hits = []
    for path, n, text in grep(root, P1):
        if path in P1_FILES or path.startswith(TESTS) or any(g.fullmatch(path) for g in P1_GLOBS):
            continue
        if path in P1_LEGACY_FILES and P1_LEGACY in text:
            continue
        if MARKER in text:
            continue
        if path == UPDATER and n in gen:
            continue
        hits.append((path, n, text))
    return hits


def tool_names(root):
    try:
        names = json.loads((root / SCHEMA).read_text(encoding="utf-8"))["tools"]["names"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        die("cannot read tools.names from %s: %s" % (SCHEMA, exc))
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
        die("%s: tools.names is not a list of names" % SCHEMA)
    return sorted(names)


def pattern2(root):
    pat = r"Scripts/(%s)\.py|\.icor-for-life/scripts" % "|".join(re.escape(n) for n in tool_names(root))
    hits = []
    for path, n, text in grep(root, pat):
        if path.endswith(".py") or path == ".gitignore" or path.startswith(".mypka/") or path.startswith(TESTS):
            continue
        if path.startswith(GL + "GL-1013-"):
            continue
        hits.append((path, n, text))
    return hits


def main(argv):
    args = argv[1:]
    root = None
    if args[:1] == ["--root"] and len(args) == 2:
        root = Path(args[1]).resolve()
    elif args:
        print("usage: check-room-literals.py [--root DIR]", file=sys.stderr)
        return 2
    if root is None:
        root = Path(__file__).resolve().parents[3]
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    except FileNotFoundError:
        die("git is not installed; T2 is a git grep")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root:
        die("%s is not the top of a git work tree; run T2 in the myPKA repository" % root)
    h1, h2 = pattern1(root), pattern2(root)
    for label, hits in (("pattern 1", h1), ("pattern 2", h2)):
        for path, n, text in hits:
            print("%s: %s:%d: %s" % (label, path, n, text.strip()[:200]))
    print("T2 %s: pattern 1 = %d, pattern 2 = %d" % ("RED" if h1 or h2 else "GREEN", len(h1), len(h2)),
          file=sys.stderr)
    return 1 if h1 or h2 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
