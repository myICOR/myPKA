#!/usr/bin/env python3
"""check-version-bump.py: a shipped file never changes without a VERSION bump
and a CHANGELOG section for the new version.

Usage:
  check-version-bump.py --product mypka [--root DIR] --base REF|auto
  check-version-bump.py --product icor   --root DIR  --base REF|auto

  --product  mypka reads .mypka/, icor reads .icor-for-life/
  --root     the repository to check (default for mypka: the repository this
             script sits in; icor needs it, since ICOR's workflow runs this
             from a myPKA checkout)
  --base     the release to compare with. `auto` is the newest N.N.N tag
             (a leading `v` allowed: myPKA tags are v6.0.0, Marshall M3)
             reachable from HEAD that does not point AT HEAD (so on a tag push
             it is the tag before). No such tag: exit 2, name one.

Why. The updater decides what to overwrite by hash. Two different byte-states
under one version number break that: a member's file matches neither the
version they "have" nor the one they are offered, and the updater has to call
an untouched file edited. Marshall's rule, made a gate: shipped bytes changed
=> VERSION is greater (semver precedence, 1.0.0-lab < 1.0.0) AND
<meta>/CHANGELOG.md has a `## <VERSION>` section with content.

"Shipped" = tracked at the working tree's index, minus the manifest's
`repo_only`, minus the three files that ARE the version (VERSION,
CHANGELOG.md, manifest.json), compared with the same set at --base. Added,
removed and modified paths all count.

Exit 0 = nothing shipped changed, or it changed with a bump and a section.
Exit 1 = FAIL lines. Exit 2 = could not decide (never a silent pass).
Repo-only CI tooling (plan step 12).
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

SEMVER = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?")
META = {"mypka": ".mypka", "icor": ".icor-for-life"}


def semver_key(v):
    m = SEMVER.fullmatch(v or "")
    if not m:
        return None
    pre = m.group(4)
    ids = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")) if pre else ()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if pre else 1, ids)


def undecided(msg):
    print("ERROR " + msg, file=sys.stderr)
    sys.exit(2)


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--product", choices=sorted(META), required=True)
    ap.add_argument("--root")
    ap.add_argument("--base", required=True)
    a = ap.parse_args(argv[1:])

    if a.root:
        root = Path(a.root).resolve()
    elif a.product == "mypka":
        r = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            undecided("not inside a git repository; pass --root")
        root = Path(r.stdout.strip())
    else:
        undecided("--product icor needs --root (the ICOR for Life checkout)")

    def git(*args, binary=False, ok=False):
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=not binary)
        if r.returncode != 0:
            if ok:
                return None
            err = r.stderr if not binary else r.stderr.decode("utf-8", "replace")
            undecided("git %s: %s" % (" ".join(args), (err.strip().splitlines() or ["failed"])[-1]))
        return r.stdout

    meta = META[a.product]
    version_rel, changelog_rel, manifest_rel = meta + "/VERSION", meta + "/CHANGELOG.md", meta + "/manifest.json"
    own = {version_rel, changelog_rel, manifest_rel}

    base = a.base
    if base == "auto":
        head = git("rev-parse", "HEAD").strip()
        cands = []
        for t in (git("tag", "--merged", "HEAD") or "").split():
            if semver_key(t) and git("rev-parse", t + "^{commit}").strip() != head:
                cands.append(t)
        if not cands:
            undecided("--base auto found no N.N.N or vN.N.N tag behind HEAD; pass --base <ref> (the last release)")
        base = max(cands, key=semver_key)
    if git("rev-parse", "--verify", "-q", base + "^{commit}", ok=True) is None:
        undecided("base %r is not a commit in %s" % (base, root))

    try:
        manifest = json.loads((root / manifest_rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        undecided("cannot read %s: %s" % (manifest_rel, exc))
    repo_only = set(manifest.get("repo_only") or {})
    base_manifest = git("show", "%s:%s" % (base, manifest_rel), ok=True)
    if base_manifest:
        try:
            repo_only |= set(json.loads(base_manifest).get("repo_only") or {})
        except ValueError:
            pass
    skip = own | repo_only

    now = {}
    for p in filter(None, git("ls-files", "-z").split("\0")):
        if p in skip:
            continue
        fp = root / p
        now[p] = hashlib.sha256(fp.read_bytes()).hexdigest() if fp.is_file() else None

    entries = []
    for rec in filter(None, git("ls-tree", "-r", "-z", "--full-tree", base).split("\0")):
        info, path = rec.split("\t", 1)
        _mode, typ, oid = info.split()
        if typ == "blob" and path not in skip:
            entries.append((path, oid))
    then = {}
    if entries:
        out = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"], capture_output=True,
                             input="".join(o + "\n" for _p, o in entries).encode()).stdout
        pos = 0
        for path, _oid in entries:
            nl = out.index(b"\n", pos)
            size = int(out[pos:nl].split()[2])
            then[path] = hashlib.sha256(out[nl + 1:nl + 1 + size]).hexdigest()
            pos = nl + 1 + size + 1

    changed = sorted(p for p in set(now) | set(then) if now.get(p) != then.get(p))
    v_now = (root / version_rel).read_text(encoding="utf-8").strip() if (root / version_rel).is_file() else ""
    v_then = (git("show", "%s:%s" % (base, version_rel), ok=True) or "").strip()

    if not changed:
        print("OK %s: no shipped file changed since %s (VERSION %s)" % (a.product, base, v_now or "?"))
        return 0

    fails = []
    kn, kt = semver_key(v_now), semver_key(v_then)
    if kn is None:
        fails.append("%s is %r, not a version" % (version_rel, v_now))
    elif kt is not None and not kn > kt:
        fails.append("%d shipped file(s) changed since %s but %s is still %s (at %s it was %s); bump it"
                     % (len(changed), base, version_rel, v_now, base, v_then))
    text = (root / changelog_rel).read_text(encoding="utf-8") if (root / changelog_rel).is_file() else ""
    body, inside = [], False
    for line in text.splitlines():
        m = re.match(r"^##\s+\[?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\]?", line)
        if m:
            if inside:
                break
            inside = m.group(1) == v_now
            continue
        if inside:
            body.append(line)
    if not "\n".join(body).strip():
        fails.append("%s has no '## %s' section with content for the %d changed file(s)"
                     % (changelog_rel, v_now, len(changed)))
    if fails:
        for f in fails:
            print("FAIL " + f, file=sys.stderr)
        for p in changed[:10]:
            print("  changed: %s" % p, file=sys.stderr)
        if len(changed) > 10:
            print("  ... and %d more" % (len(changed) - 10), file=sys.stderr)
        return 1
    print("OK %s: %d shipped file(s) changed since %s, VERSION %s -> %s, changelog section present"
          % (a.product, len(changed), base, v_then or "(none)", v_now))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
