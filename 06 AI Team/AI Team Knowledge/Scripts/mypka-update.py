#!/usr/bin/env python3
"""mypka-update.py: apply a new myPKA (or ICOR for Life) release to a member's
folder, in mode A (co-located) or mode B (sibling), without ever losing a
member's edit and without ever deleting anything.

Usage:
  mypka-update.py --release <folder-or-zip>                 dry run (default)
  mypka-update.py --release <folder-or-zip> --live          apply
  options:
    --product mypka|icor   which product the release is (default mypka)
    --target DIR           the folder to update. Default: for mypka the myPKA
                           root this script sits in; for icor the content
                           source the resolver binds (mode A: the same folder;
                           mode B: the sibling named in .mypka/sources.yaml)
    --allow-downgrade      apply a release older than the installed one, or
                           over an installed manifest or version that cannot
                           be read, or a same-version release with other bytes

Dry run is the default (GL-1005): the plan is printed and NOTHING is written.
--live applies exactly that plan.

Check who built a download BEFORE you apply it (Vex P7): `--help` prints the
`gh attestation verify` command for both products (VERIFY_HELP below).

The rules, each one a red test in run-red-tests.py (group `step12/*`, UP1 to
UP27 and their lettered cases such as UP13c, T7 and T7b):
  1. Only paths the release manifest lists in `files` are ever written, plus
     `<path>.update` beside one of them. `repo_only` and `generated` are never
     written. Nothing is ever deleted: there is no delete call in this file.
  2. A shipped file is overwritten only when its current bytes are a version
     that some release SHIPPED: the hash in the installed manifest, or one of
     the release manifest's `previous` hashes for that path.
  3. A file whose bytes match no shipped version was edited by the member. It
     is left exactly as it is. When upstream changed that file, the new
     version is written next to it as `<file>.update` (the updater's own
     file, overwritten on the next run); when upstream did not change it,
     nothing is written and the row says `kept`.
  4. A missing shipped file is restored (a guard the member lost is worse than
     a file they did not want back); the report names it.
  4b. A `seed` file (.mcp.json, .obsidian/workspace.json) is the member's
     after the first install: added when missing, never overwritten. Once a
     seed, always a seed: the old manifest's `seed` counts too, and the
     installed record keeps every seed it ever listed (a release that drops
     one from its `seed` list still finds it there next time). The record
     is member-writable, so only SEED_OK paths count from it. When the
     shipped template itself changed, the new one is written as
     `<seed>.update` and the report says so; otherwise nothing is said.
  5. A file the old release shipped and the new one does not is LEFT IN
     PLACE, with a report line. A path the other product now ships (the ICOR
     2.0.0 update of a folder whose team files moved to myPKA) is ONE line,
     "moved to myPKA", not one per file.
  6. Overrides: `AGENTS.local.md` and any `AGENT.local.md` are the member's.
     A release that lists a `.local.md` or `.update` path, in any letter
     case, is refused whole. When an override sits beside a file being
     updated, the report says the override stays in force.
  7. Reserved ids: a release may ship SOP-, WS- and GL- ids 1000-1999 only
     (matched in any letter case); anything else refuses the whole release.
  8. Containment (Vex, step 13). Every path is compared NFC-normalised and
     case-folded, because macOS and Windows folders are case-insensitive. A
     path that is absolute, has `..`, names `.git` in any segment, ends a
     segment in a dot or a space, carries `:`, names the other product's meta
     folder, lies outside this product's TERRITORY, is on the NEVER_FROM list
     for this product, or (mode A) is a file the other product's installed
     manifest lists, generates or seeds, refuses the whole run before any
     byte is written. Two release paths that fold to one name refuse it too.
     In mode A an unreadable other manifest refuses the run.
  9. The release is verified first: every listed file present with the listed
     hash, and the release manifest lists ITSELF as "self". One mismatch
     refuses the whole run.
 10. Writes walk the target with no-follow directory handles: a folder that
     became a symlink after the plan stops the run (an OS error), it is never
     written through. The product's own manifest is written last, so an
     interrupted run is finished by running it again. That record is the
     release manifest plus the old record's seeds (rule 4b), nothing else.
 11. Versions. An installed manifest or version that cannot be read, a
     downgrade, and the same version with a different manifest are refused
     unless --allow-downgrade. A myPKA v5 folder is refused with a pointer to
     the migration note. A pre-2.0.0 ICOR manifest (the combined 1.x
     manifest, `files` as a list) is read: for a myPKA install its team paths
     are myPKA's installed baseline, not the other product's files.

Exit 0 = planned (dry run) or applied (--live). Exit 1 = refused (nothing
written) or stopped mid-run by the OS (the report says how many files were
written; the manifest was not). Exit 2 = usage.
"""
from __future__ import annotations  # the generated block's annotation stays a string on any 3.x

VERIFY_HELP = """\
Check who built a download BEFORE you apply it. This updater proves a release
is intact (every hash matches its manifest); it cannot prove who made it. The
GitHub CLI can: each release zip carries a build-provenance attestation, and
this command passes only for the exact bytes that the release workflow built
from that tag on a GitHub-hosted runner. Put the version you downloaded in
place of <version>, then apply only if it prints that verification succeeded:
  myPKA (one line):
    gh attestation verify mypka-<version>.zip --repo myICOR/myPKA --signer-workflow myICOR/myPKA/.github/workflows/release-mypka.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
  ICOR for Life (one line):
    gh attestation verify icor-for-life-obsidian-edition-<version>.zip --repo TomSolid/icor-for-life-scaffold --signer-workflow TomSolid/icor-for-life-scaffold/.github/workflows/release.yml --source-ref refs/tags/<version> --deny-self-hosted-runners
The unversioned download (mypka.zip, icor-for-life-obsidian-edition.zip) is
the same bytes and verifies with the same command. Note the tags: myPKA's
start with v, ICOR for Life's do not.
"""

import argparse, hashlib, importlib.util, json, os, re, shutil, stat, sys, tempfile, unicodedata, zipfile
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
META = {"mypka": ".mypka", "icor": ".icor-for-life"}
OTHER = {"mypka": "icor", "icor": "mypka"}
NAME = {"mypka": "myPKA", "icor": "ICOR for Life"}
SEMVER = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?")
ID_RE = re.compile(r"(?:^|/)(SOP|WS|GL)-(\d+)-[^/]*$", re.IGNORECASE)
SHIPPED_IDS = (1000, 1999)
MEMBER_SUFFIXES = (".local.md", ".update")
VOLATILE = ("built", "commit")
V5_NOTE = ("myPKA 6.0.0 does not install over a v5 folder. Coming from myPKA v5? Read "
           "https://github.com/myICOR/myPKA/blob/main/MIGRATING-FROM-5.md and move by hand")

# The ICOR for Life content rooms (side "source" in the icor-concepts/1
# schema), case-folded. Written by build-mypka-manifest.py from the REPO's
# schema at release time (Vex ruling b, step 16 A1); `--check` fails the
# release gate on any byte of drift. At runtime this installed constant is
# the only list: nothing here reads icor-concepts-1.json for it, and an
# incoming release can never widen it.
# BEGIN GENERATED: icor-room-names (build-mypka-manifest.py, do not hand-edit)
ICOR_ROOM_NAMES: frozenset[str] = frozenset({
    "00 daily scratchpad",
    "01 inbox",
    "02 planner",
    "03 wip",
    "04 inner world",
    "05 assets",
    "07 databases",
})
# END GENERATED

# Where each product may write at all (Vex step 13, R4). Compared folded.
TERRITORY = {
    "mypka": {"prefixes": (".mypka/", "06 AI Team/", ".claude/", ".codex/", ".gemini/", ".agents/"),
              # The four j5v license files keep the names GitHub reads (Lex step
              # 11b); ICOR for Life ships none of them (check-disjoint holds it).
              "exact": ("AGENTS.md", "AGENT.md", "ADAPTER-PROMPT.md", ".mcp.json",
                        "LICENSE", "LICENSE-MAP.md", "TRADEMARK.md", "CONTRIBUTING.md"),
              "root_re": re.compile(r"^[^/]+-mypka(\.md)?$")},
    "icor": {"prefixes": (".icor-for-life/", ".obsidian/", "06 AI Team/AI Team Knowledge/")
                         + tuple(sorted(room + "/" for room in ICOR_ROOM_NAMES)),
             "exact": ("LICENSE.md", "README.md", "SECURITY.md", "THIRD-PARTY-NOTICES.md"),
             "root_re": None},
}
# The team control surface: never written by an ICOR release, whatever its
# territory says (instructions, hooks, host config, contracts, skills).
NEVER_FROM = {
    "icor": {"prefixes": (".mypka/", ".claude/", ".codex/", ".gemini/", ".agents/", ".cursor/", ".github/",
                          "06 AI Team/Agents/", "06 AI Team/AI Team Knowledge/Skills/",
                          "06 AI Team/AI Team Knowledge/Tasks/", "06 AI Team/AI Team Knowledge/Session Logs/",
                          "06 AI Team/AI Sessions/", "06 AI Team/Expansions/"),
             "exact": ("AGENTS.md", "AGENT.md", "CLAUDE.md", "GEMINI.md", ".mcp.json", "ADAPTER-PROMPT.md")},
    "mypka": {"prefixes": (".icor-for-life/", ".obsidian/"), "exact": ()},
}


def fold(s):
    """One name per file on a case-insensitive, normalisation-insensitive disk."""
    return unicodedata.normalize("NFC", s).casefold()


# The only paths a seed can ever be (rule 4b). A record lives in the member's
# folder and the member can edit it, so a seed the old record lists counts
# only if it is one of these: an injected seed on a shipped file (a hook, a
# guard) would otherwise freeze that file and block every later security fix.
SEED_OK = {fold(p) for p in (".mcp.json", ".obsidian/workspace.json")}


def semver_key(v):
    m = SEMVER.fullmatch(v or "")
    if not m:
        return None
    pre = m.group(4)
    ids = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")) if pre else ()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if pre else 1, ids)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Refused(Exception):
    pass


MISSING = object()


def read_json(p):
    """The parsed JSON, or None when the file is absent. A file that exists
    but cannot be read or parsed raises (OSError, ValueError): the caller
    decides, and an unreadable manifest is never read as an empty one (R5)."""
    p = Path(p)
    if not p.exists() and not p.is_symlink():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def files_map(man):
    """`files` as a path -> sha256 map, whatever the shape: the 2.x map, or the
    1.x combined manifest's list of {path, sha256, kind, example} (M1)."""
    f = (man or {}).get("files")
    if isinstance(f, dict):
        return dict(f)
    if isinstance(f, list):
        out = {}
        for e in f:
            if isinstance(e, dict) and isinstance(e.get("path"), str):
                out[e["path"]] = e.get("sha256") or ""
        return out
    return {}


def is_legacy(man):
    """The combined pre-split manifest (ICOR 1.x): `files` is a list, or the
    version is below 2.0.0."""
    if not isinstance(man, dict):
        return False
    if isinstance(man.get("files"), list):
        return True
    k = semver_key(str(man.get("version", "")))
    return bool(k and k < (2, 0, 0, 0, ()))


def default_target(product):
    spec = importlib.util.spec_from_file_location("mypka_resolve_update", HERE / "resolve.py")
    res = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(res)
    root = res.find_team_root(start=HERE)
    if product == "mypka":
        return root.path
    src = res.tool_source(res.load(root))
    if src is None:
        raise Refused("no local ICOR for Life source is bound; pass --target")
    return Path(src.root)


def open_release(path, tmp):
    """A release folder, or a zip unpacked safely into tmp."""
    p = Path(path).expanduser()
    if p.is_dir():
        return p.resolve()
    if not zipfile.is_zipfile(p):
        raise Refused("release %s is neither a folder nor a zip" % p)
    out = Path(tmp) / "release"
    with zipfile.ZipFile(p) as z:
        seen = {}
        for info in z.infolist():
            name = info.filename
            pp = PurePosixPath(name)
            if name.startswith("/") or ".." in pp.parts or "\\" in name:
                raise Refused("zip entry %r escapes the release folder" % name)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise Refused("zip entry %r is a symlink; a release carries files only" % name)
            if fold(name) in seen and seen[fold(name)] != name:
                raise Refused("zip entries %r and %r are one file on a case-insensitive disk"
                              % (seen[fold(name)], name))
            seen[fold(name)] = name
        z.extractall(out)
    return out.resolve()


def _under(f, prefixes):
    return any(f.startswith(fold(p)) for p in prefixes)


def check_path(rel, product):
    """Why a manifest path can never be written by this product, or None."""
    if not rel or "\0" in rel or "\\" in rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return "not a relative POSIX path"
    segs = rel.split("/")
    if any(x in ("", ".", "..") for x in segs):
        return "has an empty, '.' or '..' segment"
    if ":" in rel or any(x not in (".", "..") and x != x.rstrip(". ") for x in segs):
        return "carries ':' or a segment ending in a dot or a space (another name for a file on Windows)"
    f = fold(rel)
    if any(fold(x) == ".git" for x in segs):
        return "is inside .git"
    if f.endswith(MEMBER_SUFFIXES):
        return "ends in .local.md or .update, which are the member's and the updater's"
    m = ID_RE.search(rel)
    if m and not SHIPPED_IDS[0] <= int(m.group(2)) <= SHIPPED_IDS[1]:
        return "ships %s-%s, outside the shipped id range %d-%d" % (m.group(1).upper(), m.group(2), *SHIPPED_IDS)
    if fold(segs[0]) == fold(META[OTHER[product]]):
        return "names %s, the other product's folder" % META[OTHER[product]]
    return territory_problem(rel, product)


def territory_problem(rel, product):
    f = fold(rel)
    nf = NEVER_FROM[product]
    if f in {fold(x) for x in nf["exact"]} or _under(f, nf["prefixes"]):
        return "is the other product's control surface; %s never writes it" % NAME[product]
    t = TERRITORY[product]
    if f in {fold(x) for x in t["exact"]} or _under(f, t["prefixes"]):
        return None
    if t["root_re"] is not None and "/" not in f and t["root_re"].match(f):
        return None
    return "lies outside %s's territory" % NAME[product]


def inside(root, rel):
    """The destination path, or a reason it is not safely inside root. No
    existing component between root and the file may be a symlink."""
    cur = root
    for part in PurePosixPath(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            return None, "crosses the symlink %s" % cur.relative_to(root)
    try:
        cur.resolve().relative_to(root)
    except ValueError:
        return None, "resolves outside the target"
    return cur, None


def strip_volatile(m):
    return {k: v for k, v in (m or {}).items() if k not in VOLATILE}


def carried_seeds(old, new):
    """Seeds the old record lists and the release does not (rule 4b): the
    record written for this release keeps them, so a seed stays a seed for
    every later release, not just the next one. Compared folded. Only paths
    in SEED_OK carry: the record is member-writable."""
    have = {fold(p) for p in (new.get("seed") or [])}
    out = []
    for p in old.get("seed") or []:
        if isinstance(p, str) and fold(p) in SEED_OK and fold(p) not in have:
            have.add(fold(p))
            out.append(p)
    return out


def record_of(new, carried):
    """The installed record: the release manifest, its seed list merged with
    the carried seeds."""
    rec = dict(new)
    rec["seed"] = sorted(list(new.get("seed") or []) + list(carried))
    return rec


def plan(args):
    product = args.product
    meta = META[product]
    man_rel = meta + "/manifest.json"
    target = (Path(args.target).expanduser() if args.target else default_target(product))
    if not target.is_dir():
        raise Refused("target %s is not a folder" % target)
    target = target.resolve()
    tmp = tempfile.mkdtemp(prefix="mypka-update-")
    args._tmp = tmp
    release = open_release(args.release, tmp)
    try:
        new = read_json(release / man_rel)
    except (OSError, ValueError):
        new = None
    if not isinstance(new, dict) or not isinstance(new.get("files"), dict):
        raise Refused("the release has no readable %s (target %s)" % (man_rel, target))
    files = new["files"]

    # R1: the release manifest lists itself, by that exact name, as "self".
    selfs = [p for p in files if fold(p) == fold(man_rel)]
    if selfs != [man_rel] or files[man_rel] != "self":
        raise Refused("the release manifest does not list itself as %s = \"self\"; a manifest that "
                      "is written but not listed is written unchecked" % man_rel)
    folded = {}
    for p in files:
        folded.setdefault(fold(p), []).append(p)
    clash = sorted(v for v in folded.values() if len(v) > 1)
    if clash:
        raise Refused("the release lists paths that are one file on a case-insensitive disk: %s"
                      % "; ".join(", ".join(c) for c in clash))

    # M6: a myPKA v5 folder is not a first install.
    if product == "mypka" and not (target / man_rel).exists() and (
            (target / ".scaffold-version").is_file() or
            ((target / "VERSION").is_file() and (target / "Team").is_dir())):
        raise Refused("%s looks like a myPKA v5 folder (root VERSION, .scaffold-version or Team/). %s."
                      % (target, V5_NOTE))

    # R5: the installed manifest. Absent is a first install; present and
    # unreadable is refused (unless --allow-downgrade).
    try:
        old = read_json(target / man_rel)
    except (OSError, ValueError) as exc:
        if not args.allow_downgrade:
            raise Refused("the installed %s cannot be read (%s); pass --allow-downgrade to install over it"
                          % (man_rel, type(exc).__name__))
        old = None
    if old is not None and not isinstance(old, dict):
        if not args.allow_downgrade:
            raise Refused("the installed %s is not a manifest; pass --allow-downgrade to install over it" % man_rel)
        old = None
    old = old or {}
    old_files = files_map(old)

    # R4: the other product, in mode A. Its meta folder present (any case)
    # means its manifest must be readable.
    other_product = OTHER[product]
    other_meta = META[other_product]
    other_dir = None
    for entry in os.listdir(target):
        if fold(entry) == fold(other_meta):
            other_dir = target / entry
    other = {}
    if other_dir is not None:
        try:
            other = read_json(other_dir / "manifest.json")
        except (OSError, ValueError):
            other = MISSING
        if other is None or other is MISSING or not isinstance(other, dict) or (
                not isinstance(other.get("files"), (dict, list))):
            raise Refused("mode A: %s/manifest.json cannot be read, so this run cannot tell which files "
                          "are %s's; restore it (or reinstall %s) first"
                          % (other_meta, NAME[other_product], NAME[other_product]))
    other_files = files_map(other)
    legacy_other = product == "mypka" and is_legacy(other)
    if legacy_other:
        # M1: the combined 1.x manifest. Its team paths are myPKA's
        # installed baseline; only the rest stays the other product's.
        for p, h in other_files.items():
            if p in files and p not in old_files:
                old_files[p] = h
        deny_src = [p for p in other_files if p not in files]
    else:
        deny_src = list(other_files) + list(other.get("generated") or {}) + list(other.get("seed") or [])
    deny = {fold(p) for p in deny_src}

    if product == "icor" and is_legacy(old) and other_dir is None and any(
            p.startswith("06 AI Team/Agents/") for p in old_files):
        raise Refused("this folder has the combined 1.x layout and no .mypka/: install myPKA first, then "
                      "ICOR for Life (the team files move to myPKA; updating ICOR first would leave them "
                      "owned by nobody)")

    carried = carried_seeds(old, new)
    args._carried = carried
    # A record this updater wrote carries old seeds on top of its release, so
    # "the same version" compares everything but `seed`, and then asks only
    # that every seed of the release is already a seed in the record.
    old_cmp = {k: v for k, v in strip_volatile(old).items() if k != "seed"}
    new_cmp = {k: v for k, v in strip_volatile(new).items() if k != "seed"}
    if not {fold(p) for p in (new.get("seed") or [])} <= {fold(p) for p in (old.get("seed") or [])
                                                          if isinstance(p, str)}:
        new_cmp["seed"] = new.get("seed")
    v_new, v_old = str(new.get("version", "")), str(old.get("version", ""))
    if semver_key(v_new) is None:
        raise Refused("the release manifest's version %r is not a version" % v_new)
    if old and semver_key(v_old) is None and not args.allow_downgrade:
        raise Refused("the installed version %r cannot be read, so a downgrade cannot be ruled out; "
                      "pass --allow-downgrade to install anyway" % v_old)
    if semver_key(v_old) and not args.allow_downgrade:
        if semver_key(v_new) < semver_key(v_old):
            raise Refused("installed %s is newer than the release %s; pass --allow-downgrade to go back"
                          % (v_old, v_new))
        if semver_key(v_new) == semver_key(v_old) and old_cmp != new_cmp:
            raise Refused("installed %s and the release %s are the same version with different contents; "
                          "one version name never has two byte-states" % (v_old, v_new))

    problems = []
    rows = []
    member_ids = {}
    for dirpath, dirnames, names in os.walk(target):
        dirnames[:] = [d for d in dirnames if fold(d) not in (".git", "node_modules")]
        for n in names:
            # F3: <file>.update is the updater's own file (rule 3) and
            # <file>.local.md the member's override of a shipped file; neither
            # is a second note with the same id, so neither is an id clash.
            if fold(n).endswith(MEMBER_SUFFIXES):
                continue
            m = ID_RE.search(n)
            if m:
                rel = os.path.relpath(os.path.join(dirpath, n), target).replace(os.sep, "/")
                member_ids.setdefault((m.group(1).upper(), int(m.group(2))), []).append(rel)

    prev_new = new.get("previous") or {}
    prev_old = old.get("previous") or {}
    seeds = {fold(p) for p in (new.get("seed") or [])} | {fold(p) for p in (old.get("seed") or [])
                                                           if isinstance(p, str) and fold(p) in SEED_OK}
    for rel in sorted(files):
        why = check_path(rel, product)
        if why is None and fold(rel) in deny:
            why = "is shipped by %s too (mode A: one folder, two products)" % (
                other.get("name") or NAME[other_product])
        if why:
            problems.append("%s %s" % (rel, why))
            continue
        src = release / rel
        want = files[rel]
        if not src.is_file() or src.is_symlink():
            problems.append("%s is listed but missing from the release" % rel)
            continue
        if rel != man_rel and sha(src) != want:
            problems.append("%s in the release does not match its manifest hash" % rel)
            continue
        dest, why = inside(target, rel)
        if why:
            problems.append("%s %s" % (rel, why))
            continue
        upd, why = inside(target, rel + ".update")
        if why:
            problems.append("%s.update %s" % (rel, why))
            continue
        note = ""
        for override in ("AGENTS.local.md", "AGENT.local.md"):
            sib = dest.parent / override
            if fold(dest.name) == fold(override.replace(".local", "")) and sib.is_file():
                note = "your %s stays in force" % sib.relative_to(target)
        m = ID_RE.search(rel)
        if m:
            others = [p for p in member_ids.get((m.group(1).upper(), int(m.group(2))), []) if fold(p) != fold(rel)]
            if others:
                kinds = ["%s (%s)" % (p, "a copy an earlier release shipped" if p in old_files else "your own file")
                         for p in others]
                rows.append(("id-clash", rel, "you also have %s with this id; both kept" % ", ".join(kinds)))
        if rel == man_rel:
            if dest.is_dir():
                problems.append("%s is a folder in the target" % rel)
                continue
            rows.append(("record", rel, "written last: %s -> %s%s" % (
                v_old or "(none)", v_new,
                ("; still seeds, from the old record: %s" % ", ".join(carried)) if carried else "")))
            continue
        if dest.is_dir():
            problems.append("%s is a folder in the target, the release ships a file there" % rel)
            continue
        installed = old_files.get(rel)
        if installed == "self":
            installed = None
        if not dest.exists():
            was = rel in old_files
            rows.append(("add", rel, ("restored: shipped before, missing now" if was else "new in %s" % v_new)))
            continue
        have = sha(dest)
        if have == want:
            rows.append(("same", rel, note))
            continue
        if fold(rel) in seeds:
            # No installed hash (a first install over an existing file, or a
            # 1.x folder whose manifest never listed it): nothing says the
            # template changed, so nothing is said.
            if installed is not None and installed != want:
                rows.append(("seed-new", rel, "yours, kept; the shipped template changed, the new one is at "
                             "%s.update" % rel))
            else:
                rows.append(("seed", rel, "yours after the first install; never updated"))
            continue
        known = set(prev_new.get(rel) or []) | set(prev_old.get(rel) or [])
        if installed:
            known.add(installed)
        if have in known:
            rows.append(("update", rel, note))
        elif installed and installed == want:
            rows.append(("kept", rel, "edited by you, left as is; unchanged upstream, so no .update%s"
                         % (("; " + note) if note else "")))
        else:
            rows.append(("kept+upd", rel, "edited by you, left as is; the new version is at %s.update (the "
                         "updater's file, overwritten on the next run)%s" % (rel, ("; " + note) if note else "")))
    moved = []
    other_fold = {fold(p) for p in other_files}
    for rel in sorted(set(old_files) - set(files)):
        if fold(rel) == fold(man_rel):
            continue
        if not legacy_other and fold(rel) in other_fold:
            moved.append(rel)
            continue
        dest = target / rel
        if dest.is_file() and not dest.is_symlink():
            pristine = sha(dest) == (old_files[rel] or "")
            rows.append(("retired", rel, "no longer shipped; left in place%s"
                         % (" (unchanged since shipped, safe to remove by hand)" if pristine else "")))
    if moved:
        rows.append(("moved", "%d file(s)" % len(moved), "moved to %s: now listed in %s/manifest.json and "
                     "updated by its own release; left in place" % (NAME[other_product], other_meta)))
    if problems:
        raise Refused("the release cannot be applied safely:\n  " + "\n  ".join(problems))
    mode = "A (co-located)" if other_dir is not None else "B (sibling)"
    return release, target, rows, v_old, v_new, mode, man_rel


def _dir_fd_nofollow(root, parent):
    """An fd for root/parent, opened one segment at a time with O_NOFOLLOW, so
    a segment that is (or became) a symlink stops the walk with an OSError.
    Missing folders are created on the way (Vex step 13, R2)."""
    fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in PurePosixPath(parent).parts:
            try:
                nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(part, 0o755, dir_fd=fd)
                nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nfd
        return fd
    except BaseException:
        os.close(fd)
        raise


_NOFOLLOW_OK = (hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
                and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd
                # os.replace takes the same dir_fd arguments as os.rename (one
                # C function) but is not listed in supports_dir_fd itself.
                and os.rename in os.supports_dir_fd)


def write_atomic(src, root, rel):
    """Copy src to root/rel through no-follow directory handles, then rename
    into place inside that directory handle. POSIX (Linux and macOS).
    Windows has no dir_fd: there every component is re-checked with lstat
    right before the write, which narrows the window but cannot close it."""
    p = PurePosixPath(rel)
    mode = stat.S_IMODE(os.stat(src).st_mode) & 0o755
    if not _NOFOLLOW_OK:
        cur = Path(root)
        for part in p.parent.parts:
            cur = cur / part
            if cur.is_symlink():
                raise OSError(40, "a folder became a symlink during the run", str(cur))
            cur.mkdir(exist_ok=True)
        dest = cur / p.name
        if dest.is_symlink():
            raise OSError(40, "the file became a symlink during the run", str(dest))
        fd, tmp = tempfile.mkstemp(prefix=".mypka-update-", dir=str(cur))
        try:
            with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
                shutil.copyfileobj(inp, out)
            os.chmod(tmp, mode)
            os.replace(tmp, dest)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return
    dfd = _dir_fd_nofollow(root, p.parent)
    tmp = ".mypka-update-%s.tmp" % os.urandom(6).hex()
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
            shutil.copyfileobj(inp, out)
            os.fchmod(out.fileno(), mode)
        os.replace(tmp, p.name, src_dir_fd=dfd, dst_dir_fd=dfd)
    except BaseException:
        try:
            os.unlink(tmp, dir_fd=dfd)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(dfd)


def main(argv):
    ap = argparse.ArgumentParser(description="Apply a myPKA or ICOR for Life release. Dry run unless --live.",
                                 epilog=VERIFY_HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--release", required=True)
    ap.add_argument("--product", choices=sorted(META), default="mypka")
    ap.add_argument("--target")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--allow-downgrade", action="store_true")
    args = ap.parse_args(argv[1:])
    args._tmp = None
    args._carried = []
    written = []
    try:
        release, target, rows, v_old, v_new, mode, man_rel = plan(args)
        print("%s update %s -> %s, product %s, mode %s, target %s"
              % ("LIVE" if args.live else "DRY RUN", v_old or "(none)", v_new, args.product, mode, target))
        for action, rel, note in rows:
            print("%-8s %s%s" % (action.upper(), rel, ("  (%s)" % note) if note else ""))
        counts = {}
        for action, _r, _n in rows:
            counts[action] = counts.get(action, 0) + 1
        summary = ", ".join("%d %s" % (counts[k], k) for k in sorted(counts))
        if not args.live:
            print("DRY RUN: nothing written (%s). Run again with --live to apply." % summary)
            return 0
        for action, rel, _n in rows:
            if action in ("add", "update"):
                write_atomic(release / rel, target, rel)
                written.append(rel)
            elif action in ("kept+upd", "seed-new"):
                write_atomic(release / rel, target, rel + ".update")
                written.append(rel + ".update")
        rec_src = release / man_rel
        if args._carried:
            rec_src = Path(args._tmp) / "record.json"
            rec_src.write_text(json.dumps(record_of(read_json(release / man_rel), args._carried), indent=2,
                                          ensure_ascii=False) + "\n", encoding="utf-8")
        write_atomic(rec_src, target, man_rel)
        print("APPLIED %s: %s" % (v_new, summary))
        return 0
    except Refused as exc:
        print("REFUSED %s" % exc, file=sys.stderr)
        print("REFUSED nothing was written", file=sys.stderr)
        return 1
    except OSError as exc:
        print("REFUSED the operating system stopped a write: %s (%s)"
              % (exc.strerror or exc, exc.filename or "a folder on the way"), file=sys.stderr)
        print("REFUSED %d file(s) were written before it; the installed manifest was NOT updated, so "
              "the next run re-checks every file: %s" % (len(written), ", ".join(written[:5]) or "none"),
              file=sys.stderr)
        return 1
    finally:
        if args._tmp:
            shutil.rmtree(args._tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
