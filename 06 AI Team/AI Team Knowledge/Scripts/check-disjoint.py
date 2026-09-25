#!/usr/bin/env python3
"""check-disjoint.py: no path is shipped by both myPKA and ICOR for Life.

Usage:
  check-disjoint.py <mypka manifest.json> <icor manifest.json>

Why. In mode A both products are unpacked into ONE folder (ruling q7x), so a
path shipped by both is two releases fighting over one file: whichever
updater runs last wins, and the other product's hash check then calls the
member's untouched file "edited". The rule (plan step 10): the installed sets
are disjoint. Repo-only paths never reach a member, so they may overlap
(`.gitignore` does, on purpose).

What counts as installed: a manifest's `files` plus its `generated` paths
(rendered into the member's folder per device). What is refused, exit 1:
  1. the same path in both installed sets;
  2. two paths that differ only in letter case (macOS and Windows folders
     are case-insensitive, so they are one file there);
  3. a path one side ships as a FILE that the other uses as a FOLDER
     (`a` vs `a/b`): the second unpack fails or nests;
  4. one SOP-, WS- or GL- number shipped by both sides (GL-1016 on each side
     under two names is not a path clash, and it is still two guidelines
     with one id);
  5. a gap in the numbers (Marshall B: the next id for a new shipped file is
     the next free id of that type ACROSS BOTH manifests). Per type, every
     number from the lowest used to the highest is shipped by one side, or
     was removed in a `history` entry, or is declared in a `retired_ids`
     list (a number shipped once, or reserved by code outside these repos,
     that never comes back). A new file that
     skips a number, or takes one the other side is about to take from its
     own count, leaves a gap and is refused. The OK line names the next free
     id of each type.
Every finding is printed; nothing is written. Exit 2 = a manifest could not
be read (never a silent pass).

Repo-only CI tooling (plan step 12): a required step in both release
workflows. ICOR's workflow runs it from a myPKA checkout at the pinned tag.
"""
import json, re, sys, unicodedata

ID_RE = re.compile(r"(?:^|/)(SOP|WS|GL)-(\d+)-[^/]*$", re.IGNORECASE)
RETIRED_RE = re.compile(r"(SOP|WS|GL)-(\d+)", re.IGNORECASE)


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError) as exc:
        print("ERROR cannot read %s: %s" % (path, exc), file=sys.stderr)
        sys.exit(2)
    files = m.get("files")
    if isinstance(files, list):   # the 1.x shape (Marshall M1): read it, never crash on it
        m["files"] = files = {e.get("path"): e.get("sha256") for e in files if isinstance(e, dict) and e.get("path")}
    if not isinstance(files, dict):
        print("ERROR %s has no `files` map; refusing to call it disjoint" % path, file=sys.stderr)
        sys.exit(2)
    return m


def installed(m):
    return set(m.get("files") or {}) | set(m.get("generated") or {})


def retired(m):
    """{(kind, number)} a manifest declares as used-and-gone: `retired_ids`
    entries and every id a `history` entry removed or renamed away."""
    out = set()
    for r in m.get("retired_ids") or []:
        mm = RETIRED_RE.fullmatch(str(r))
        if mm:
            out.add((mm.group(1).upper(), int(mm.group(2))))
    for h in m.get("history") or []:
        gone = [x.get("path", "") for x in h.get("removed") or []] + [x.get("from", "") for x in h.get("renamed") or []]
        for p in gone:
            mm = ID_RE.search(p)
            if mm:
                out.add((mm.group(1).upper(), int(mm.group(2))))
    return out


def next_free(a, b):
    """({kind: next free number}, [gap findings]) across both manifests."""
    used, gone = {}, retired(a) | retired(b)
    for m in (a, b):
        for p in installed(m):
            mm = ID_RE.search(p)
            if mm:
                used.setdefault(mm.group(1).upper(), set()).add(int(mm.group(2)))
    nxt, gaps = {}, []
    for kind in sorted(used):
        nums = used[kind] | {n for k, n in gone if k == kind}
        nxt[kind] = max(nums) + 1
        # From the lowest SHIPPED number, as the rule above says: a retired
        # number below it (the 1.x GL-001 series, gone since the renumbering
        # to GL-1001, read from the 1.x tags' history) is no gap to fill.
        holes = [n for n in range(min(used[kind]), max(nums) + 1) if n not in nums]
        if holes:
            gaps.append("%s ids are not counted across both manifests: %s free below the highest shipped "
                        "%s-%d (fill the lowest free number next, or declare a number shipped once, or reserved "
                        "by code outside these repos, in `retired_ids`)" % (kind, ", ".join("%s-%d" % (kind, n) for n in holes), kind, max(used[kind])))
    return nxt, gaps


def findings(a_name, a, b_name, b):
    out = []
    A, B = installed(a), installed(b)
    for p in sorted(A & B):
        out.append("both ship %s" % p)
    fold = {}
    for side, paths in ((a_name, A), (b_name, B)):
        for p in paths:
            fold.setdefault(unicodedata.normalize("NFC", p).casefold(), set()).add((side, p))
    for key, hits in sorted(fold.items()):
        names = {p for _s, p in hits}
        if len(names) > 1:
            out.append("case-only clash (one file on a case-insensitive disk): %s"
                       % ", ".join("%s:%s" % h for h in sorted(hits)))
    for side, paths, other_side, other in ((a_name, A, b_name, B), (b_name, B, a_name, A)):
        dirs = set()
        for p in other:
            parts = p.split("/")
            dirs.update("/".join(parts[:i]) for i in range(1, len(parts)))
        for p in sorted(paths & dirs):
            out.append("%s ships the file %s, which %s uses as a folder" % (side, p, other_side))
    ids = {}
    for side, paths in ((a_name, A), (b_name, B)):
        for p in paths:
            mm = ID_RE.search(p)
            if mm:
                ids.setdefault((mm.group(1).upper(), int(mm.group(2))), set()).add((side, p))
    for (kind, num), hits in sorted(ids.items()):
        if len({s for s, _p in hits}) > 1:
            out.append("%s-%d is shipped by both sides: %s" % (kind, num, ", ".join("%s:%s" % h for h in sorted(hits))))
    out += next_free(a, b)[1]
    return out


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    a, b = load(argv[1]), load(argv[2])
    a_name, b_name = a.get("name") or "first", b.get("name") or "second"
    out = findings(a_name, a, b_name, b)
    ro = sorted(set(a.get("repo_only") or {}) & set(b.get("repo_only") or {}))
    if out:
        for f in out:
            print("FAIL " + f, file=sys.stderr)
        print("FAIL %d finding(s): the two manifests are not disjoint" % len(out), file=sys.stderr)
        return 1
    nxt = next_free(a, b)[0]
    print("OK disjoint: %s %d installed, %s %d installed, 0 shared; repo-only overlap allowed: %s; next free: %s"
          % (a_name, len(installed(a)), b_name, len(installed(b)), ", ".join(ro) or "none",
             ", ".join("%s-%d" % kv for kv in sorted(nxt.items())) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
