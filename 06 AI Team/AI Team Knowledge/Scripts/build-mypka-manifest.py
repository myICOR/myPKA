#!/usr/bin/env python3
"""Build .mypka/manifest.json, the machine-readable description of THIS
version of myPKA, and check that the one on disk still describes the tree.

Usage:
  build-mypka-manifest.py            (re)write .mypka/manifest.json
  build-mypka-manifest.py --check    exit 1 if the manifest on disk is stale, the
                                     VERSION is malformed, CHANGELOG.md has no
                                     section for it, or a shipped path breaks a
                                     reserved rule
  options (both modes):
    --legacy-repo DIR    a clone of the ICOR for Life Scaffold repository with
                         its 1.x tags (env MYPKA_LEGACY_REPO). Recomputes
                         `legacy_previous` from it and proves the pin in
                         `legacy_source`. Without it the carried value is kept.
    --require-legacy     fail when the manifest carries no `legacy_source`
                         (the release workflow passes it: a public myPKA 6.x
                         without the 1.x history would spam existing members
                         with .update files, Marshall M2)

Repo-only (plan step 12). It runs in the myPKA repository and in CI, never in
a member's folder: the updater (mypka-update.py) only ever READS a manifest.

What each key is and where it comes from. Nothing here is copied from
anywhere else; every source has exactly one home.

  computed (rebuilt on every run, compared under --check)
    version    .mypka/VERSION, one line, MAJOR.MINOR.PATCH with an optional
               pre-release tag (1.0.0-lab). Hand-bumped.
    files      `git ls-files` (the index, like the zip) minus `repo_only`,
               path -> sha256 of the working-tree bytes. The manifest's own
               entry is the literal "self": a file cannot carry its own hash.
    repo_only  tracked paths that never reach a member: the RESIDUE_PATHS
               array of build-mypka-release.sh (read by regex, not copied).
               Every tracked path under Scripts/tests/ must be in it (T2
               exempts that folder whole, Vex step 16): one that is not
               fails the build and --check.
    generated  one entry per tracked Skills/<name>/SKILL.md: the host link
               scaffold-init.py apply writes at .agents/skills/<name>/SKILL.md.
               No hash, never tracked, never written by the updater.
    seed       shipped files that are the member's after the first install
               (.mcp.json: the one file the member is told to edit). The
               updater adds them when missing and never overwrites them.
    schema     2 since step 13: `files` is a path map (Flint step 14, 4.1).
    history    one entry per release since the split, newest first, from
               `git diff --name-status -M` between consecutive tags that carry
               a .mypka/manifest.json (so the v5 tags of myICOR/myPKA, a
               different product layout, never count): removed (path, sha256,
               note from the CHANGELOG.md line whose first backticked name
               is the path, may be empty, never with an empty name in it),
               renamed, added.
               Repo-only paths are left out. The Scaffold Check plugin reads
               it for leftovers (Flint step 14, 4.1).
    agents     every shipped contract 06 AI Team/Agents/<Name>/AGENT.md that
               is not the template, by identity (myicor_id, read with
               mint-agent-ids.py's own reader, never generated here). Moved
               from the ICOR builder in step 12: the agents are the team's.
    previous   path -> the sha256 of every OTHER byte-state that path had in
               an earlier tagged release (semver tags below VERSION). The
               updater overwrites a member's file only when its hash is one a
               release actually shipped; this is how it knows the older ones.
               Only paths this release ships. Tags may carry a leading `v`
               (v6.0.0: Marshall M3). The union with `legacy_previous`.
    legacy_previous  path -> every sha256 that path had at a 1.x tag of the
               ICOR for Life Scaffold (the team files' history before the
               split, Marshall M2), for paths this release ships. Recomputed
               with --legacy-repo, else carried.
  carried (declared by a person, kept across rebuilds, validated here)
    name, requires, source_commit,
    legacy_source   {repo, tag, commit}: the pinned second history source.
                    The tag must resolve to the commit in --legacy-repo.
  volatile (ignored by --check)
    built, commit

The icor-room-names block (Vex ruling b, step 16 A1). mypka-update.py keeps
the ICOR content rooms its TERRITORY needs as ONE generated constant,
ICOR_ROOM_NAMES, between the lines
  # BEGIN GENERATED: icor-room-names (build-mypka-manifest.py, do not hand-edit)
  # END GENERATED
This builder writes that block from the REPO SOURCE schema: the blob of
.mypka/icor-concepts-1.json in the git index, never an installed copy and
never a file that differs from what git tracks. Every room whose `side` is
"source", NFC-normalised and case-folded (the updater compares paths
folded), sorted, one per line. The block is written BEFORE the manifest is
computed, so the manifest hashes the updater's final bytes. `--check`
renders the block in memory and fails on any byte difference: a hand-edited
name, a room added to or dropped from the schema, a missing marker. The
updater never reads the schema for this list at runtime.

Reserved rules enforced on every build (plan step 10, ID ranges):
  - a shipped SOP-, WS- or GL- id lies in 1000-1999 (2000 and up is the
    member's range, so a release can never collide with a member's own file);
  - no shipped path ends in .local.md (AGENTS.local.md and AGENT.local.md are
    the member's overrides) or .update (the updater's own output).

Exit 0 = written, or --check passed. Exit 1 = FAIL lines on stderr.
"""
import datetime, hashlib, importlib.util, json, os, re, subprocess, sys, unicodedata
from pathlib import Path

sys.dont_write_bytecode = True  # never drop a .pyc into the tree being hashed

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def die(msg):
    sys.exit("FAIL " + msg)


try:
    ROOT = _load("mypka_resolve_builder", HERE / "resolve.py").find_team_root(start=HERE, env={}).path
except Exception as exc:  # noqa: BLE001  the resolver raises its own error type
    die("cannot find the myPKA root above %s: %s" % (HERE, exc))

META = ROOT / ".mypka"
MANIFEST = META / "manifest.json"
MANIFEST_REL = ".mypka/manifest.json"
VERSION_FILE = META / "VERSION"
ROOT_VERSION_REL = "VERSION"
CHANGELOG = META / "CHANGELOG.md"
RELEASE_SCRIPT = HERE / "build-mypka-release.sh"
SCHEMA = 2
CARRIED = ("name", "requires", "source_commit", "legacy_source")
VOLATILE = ("built", "commit")
SKILLS = "06 AI Team/AI Team Knowledge/Skills/"
AGENTS_PREFIX = "06 AI Team/Agents/"
TESTS_PREFIX = "06 AI Team/AI Team Knowledge/Scripts/tests/"

SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?")
TAG_RE = re.compile(r"v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)")
ID_RE = re.compile(r"(?:^|/)(SOP|WS|GL)-(\d+)-[^/]*$")
SHIPPED_ID_RANGE = (1000, 1999)
MEMBER_SUFFIXES = (".local.md", ".update")
SEED = {".mcp.json"}


SCHEMA_REL = ".mypka/icor-concepts-1.json"
UPDATER = HERE / "mypka-update.py"
ROOM_BEGIN = "# BEGIN GENERATED: icor-room-names (build-mypka-manifest.py, do not hand-edit)"
ROOM_END = "# END GENERATED"


def fold(s):
    """The updater's own fold: NFC, then case-folded."""
    return unicodedata.normalize("NFC", s).casefold()


def schema_room_names():
    """The folded `source` room names of the repo's tracked schema. Read from
    the git index, and refused when the working tree holds other bytes: the
    repo source is what git tracks, never whatever sits in .mypka/."""
    r = subprocess.run(["git", "show", ":" + SCHEMA_REL], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        die("%s is not in the git index of %s; the room names are read from the repo source only (%s)"
            % (SCHEMA_REL, ROOT, (r.stderr.decode("utf-8", "replace").strip().splitlines() or ["git show failed"])[-1]))
    blob = r.stdout
    wt = ROOT / SCHEMA_REL
    if not wt.is_file() or wt.read_bytes() != blob:
        die("%s in the working tree differs from the git index; stage it (git add) or restore it, "
            "then run again" % SCHEMA_REL)
    try:
        schema = json.loads(blob.decode("utf-8"))
    except ValueError as exc:
        die("%s is not valid JSON: %s" % (SCHEMA_REL, exc))
    rooms = schema.get("rooms") if isinstance(schema, dict) else None
    if not isinstance(rooms, list):
        die("%s has no `rooms` list" % SCHEMA_REL)
    names = set()
    for room in rooms:
        if not isinstance(room, dict) or room.get("side") != "source":
            continue
        path = room.get("path")
        if not isinstance(path, str) or not path.strip() or "/" in path or "\\" in path or '"' in path:
            die("%s: a source room has an unusable path %r" % (SCHEMA_REL, path))
        f = fold(path)
        if f in names:
            die("%s: two source rooms fold to one name, %r" % (SCHEMA_REL, f))
        names.add(f)
    if not names:
        die("%s names no room with side \"source\"; the ICOR territory would be empty" % SCHEMA_REL)
    return sorted(names)


def room_block(names):
    """The generated lines, markers included, newline-terminated."""
    body = ["ICOR_ROOM_NAMES: frozenset[str] = frozenset({"]
    body += ["    %s," % json.dumps(n, ensure_ascii=False) for n in names]
    body += ["})"]
    return "\n".join([ROOM_BEGIN] + body + [ROOM_END]) + "\n"


def splice_room_block(src, block):
    """src with its icor-room-names block replaced by block. Dies when the
    markers are missing, doubled, or out of order."""
    lines = src.splitlines(keepends=True)
    begins = [i for i, l in enumerate(lines) if l.rstrip("\r\n") == ROOM_BEGIN]
    if len(begins) != 1:
        die("%s must carry the line %r exactly once (found %d)" % (UPDATER.name, ROOM_BEGIN, len(begins)))
    b = begins[0]
    ends = [i for i in range(b + 1, len(lines)) if lines[i].rstrip("\r\n") == ROOM_END]
    if not ends:
        die("%s: no %r line after the icor-room-names BEGIN marker" % (UPDATER.name, ROOM_END))
    e = ends[0]
    return "".join(lines[:b]) + block + "".join(lines[e + 1:])


def semver_key(v):
    """Sort key with semver precedence: 1.0.0-lab < 1.0.0 < 1.0.1. None if
    the string is not a version."""
    m = SEMVER.fullmatch(v or "")
    if not m:
        return None
    pre = m.group(4)
    ids = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")) if pre else ()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if pre else 1, ids)


def tag_key(t):
    """semver_key of a tag, which may carry a leading `v` (M3)."""
    m = TAG_RE.fullmatch(t or "")
    return semver_key(m.group(1)) if m else None


def blob_hashes(repo, rev, keep):
    """{path: sha256} of every blob at rev whose path passes keep(path)."""
    r = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-z", "--full-tree", rev],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die("git ls-tree %s in %s: %s" % (rev, repo, (r.stderr.strip().splitlines() or ["failed"])[-1]))
    entries = []
    for rec in filter(None, r.stdout.split("\0")):
        meta, path = rec.split("\t", 1)
        _mode, typ, oid = meta.split()
        if typ == "blob" and keep(path):
            entries.append((path, oid))
    out = {}
    if not entries:
        return out
    batch = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], capture_output=True,
                           input="".join(oid + "\n" for _p, oid in entries).encode())
    buf, pos = batch.stdout, 0
    for path, _oid in entries:
        nl = buf.index(b"\n", pos)
        size = int(buf[pos:nl].split()[2])
        out[path] = hashlib.sha256(buf[nl + 1:nl + 1 + size]).hexdigest()
        pos = nl + 1 + size + 1
    return out


def git(*args, binary=False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=not binary)
    if r.returncode != 0:
        err = r.stderr if not binary else r.stderr.decode("utf-8", "replace")
        die("git %s: %s" % (" ".join(args), (err.strip().splitlines() or ["failed"])[-1]))
    return r.stdout


def changelog_sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+\[?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\]?", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


# A history note is shown to members as it is. One with an empty slot where a
# name belongs (it opens on punctuation, ": ," or "( )", a run of spaces, an
# empty pair of backticks) fails the build and --check, whoever made the hole.
NOTE_HOLE = re.compile(r"^[,;:.)]|[:(]\s*[,;:.)]|\S {2,}\S|``")


def note_hole(note):
    return bool(note) and NOTE_HOLE.search(note) is not None


def residue_paths():
    if not RELEASE_SCRIPT.is_file():
        die("%s is missing; repo_only is read from its RESIDUE_PATHS array" % RELEASE_SCRIPT.name)
    src = RELEASE_SCRIPT.read_text(encoding="utf-8")
    m = re.search(r"^declare -a RESIDUE_PATHS=\(\n(.*?)^\)", src, re.M | re.S)
    if not m:
        die("could not find the RESIDUE_PATHS array in build-mypka-release.sh")
    paths = re.findall(r'^\s*"([^"]+)"\s*$', m.group(1), re.M)
    if not paths:
        die("the RESIDUE_PATHS array in build-mypka-release.sh names no paths")
    return set(paths)


def root_version_problems(tracked_set, residue):
    """v5q (Tom, 2026-09-24): a repo-only root VERSION, byte-equal to
    .mypka/VERSION. A v5 folder's update check reads VERSION at the root of
    the repository's main, so this twin is what tells it a new major exists.
    It never ships: a 6.x folder's version is .mypka/VERSION, and the
    updater reads a root VERSION beside Team/ as a v5 folder (M6)."""
    rv = ROOT / ROOT_VERSION_REL
    if ROOT_VERSION_REL not in tracked_set or not rv.is_file():
        return ["the root VERSION is not tracked; it is repo-only and byte-equal to .mypka/VERSION, so a v5 "
                "folder's update check sees this release (v5q)"]
    out = []
    if ROOT_VERSION_REL not in residue:
        out.append("the root VERSION is not in RESIDUE_PATHS of build-mypka-release.sh; it is repo-only and "
                   "never ships (v5q)")
    have, want = rv.read_bytes(), VERSION_FILE.read_bytes()
    if have != want:
        out.append("the root VERSION %r is not byte-equal to .mypka/VERSION %r; write the same bytes to both (v5q)"
                   % (have.decode("utf-8", "replace"), want.decode("utf-8", "replace")))
    return out


def reserved_problems(paths):
    """Every shipped path that breaks the ID-range or member-suffix rule."""
    out = []
    for p in sorted(paths):
        if p.endswith(MEMBER_SUFFIXES):
            out.append("%s: a shipped path may not end in %s (reserved for the member and the updater)"
                       % (p, " or ".join(MEMBER_SUFFIXES)))
        m = ID_RE.search(p)
        if m:
            n = int(m.group(2))
            if not SHIPPED_ID_RANGE[0] <= n <= SHIPPED_ID_RANGE[1]:
                out.append("%s: shipped %s ids live in %d-%d; %d is outside it (2000 and up is the member's range)"
                           % (p, m.group(1), SHIPPED_ID_RANGE[0], SHIPPED_ID_RANGE[1], n))
    return out


def build(legacy_repo=None, require_legacy=False):
    fails = []
    if not VERSION_FILE.is_file():
        die(".mypka/VERSION is missing; write one line, e.g. 1.0.0")
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if semver_key(version) is None:
        die("VERSION must be MAJOR.MINOR.PATCH with an optional -pre-release tag, got %r" % version)

    on_disk = {}
    if MANIFEST.is_file():
        try:
            on_disk = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except ValueError as exc:
            die("manifest.json is not valid JSON: %s" % exc)
    if not on_disk.get("requires"):
        die("the manifest on disk declares no `requires` (e.g. \"icor-concepts >=1 <2\"); "
            "it is carried, never computed, so a person writes it once")

    residue = residue_paths()
    tracked = [p for p in git("ls-files", "-z").split("\0") if p]
    tracked_set = set(tracked)
    files, repo_only = {}, {}
    for p in sorted(tracked):
        fp = ROOT / p
        if p == MANIFEST_REL:
            files[p] = "self"
            continue
        if not fp.is_file():
            die("tracked but missing on disk: %s" % p)
        h = hashlib.sha256(fp.read_bytes()).hexdigest()
        (repo_only if p in residue else files)[p] = h
    for p in sorted(residue - tracked_set):
        fails.append("RESIDUE_PATHS names %s, which is not tracked (a stale entry hides nothing and "
                     "misleads the next reader)" % p)
    # Vex step 16 MEDIUM: T2 exempts everything under Scripts/tests/ as a
    # folder, while RESIDUE_PATHS lists exact files. A tracked file there that
    # RESIDUE_PATHS does not name would ship unchecked, so it fails the build.
    for p in sorted(tracked_set - residue):
        if p.startswith(TESTS_PREFIX):
            fails.append("%s is tracked under %s but not listed in RESIDUE_PATHS of build-mypka-release.sh; "
                         "T2 exempts that folder because nothing in it ships, so list it there (repo-only) "
                         "or move it out" % (p, TESTS_PREFIX))
    fails += root_version_problems(tracked_set, residue)
    if MANIFEST_REL not in files:
        fails.append("%s is not tracked; the manifest ships with the release it describes" % MANIFEST_REL)

    generated = {}
    for p in sorted(tracked_set):
        if p.startswith(SKILLS) and p.endswith("/SKILL.md"):
            name = p[len(SKILLS):].split("/")[0]
            if name.startswith("_") or p.count("/") != SKILLS.count("/") + 1:
                continue
            generated[".agents/skills/%s/SKILL.md" % name] = {
                "from": p, "by": "scaffold-init.py apply",
                "kind": "link, or a copy where the platform has no symlinks"}
    for g in generated:
        if g in tracked_set:
            fails.append("%s is generated per device and must not be tracked" % g)

    mint = _load("mint_agent_ids_builder", HERE / "mint-agent-ids.py")
    agents, ids_seen = [], {}
    for p in sorted(files):
        if not (p.startswith(AGENTS_PREFIX) and p.endswith("/AGENT.md")):
            continue
        parts = p[len(AGENTS_PREFIX):].split("/")
        if len(parts) != 2 or mint.is_template(parts[0]):
            continue
        name = parts[0]
        fm = mint.frontmatter((ROOT / p).read_text(encoding="utf-8"))
        if fm is None:
            die("agent %s: %s has no frontmatter, so it carries no myicor_id" % (name, p))
        idx, val = mint.read_value(fm[0])
        if idx is None or val == mint.NIL or not mint.UUID4_RE.fullmatch(val or ""):
            die("agent %s: myicor_id %r is missing, the nil placeholder, or not a lowercase UUID v4" % (name, val))
        if val in ids_seen:
            die("agent %s: myicor_id %s is already carried by %s" % (name, val, ids_seen[val]))
        ids_seen[val] = name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        shim = ".claude/agents/%s.md" % slug
        agents.append({"name": name, "myicor_id": val, "path": p, "shim": shim if shim in files else None})
    if not agents:
        die("no shipped agent contract under %s; a team with no agents is not one" % AGENTS_PREFIX)

    # previous: every older byte-state a shipped path had at an earlier release
    tags = sorted((t for t in git("tag").split() if tag_key(t) and tag_key(t) < semver_key(version)),
                  key=tag_key)
    previous = {}
    for tag in tags:
        for path, h in blob_hashes(ROOT, tag, lambda p: p in files and p != MANIFEST_REL).items():
            if files.get(path) != h:
                previous.setdefault(path, set()).add(h)

    # legacy_previous (Marshall M2): the team files' 1.x history lives in the
    # ICOR for Life Scaffold repository's tags, which this repository never
    # has. A pinned second source, moved paths only.
    pin = on_disk.get("legacy_source")
    legacy = None
    if legacy_repo is not None:
        if not isinstance(pin, dict) or not all(isinstance(pin.get(k), str) and pin.get(k) for k in ("repo", "tag", "commit")):
            die("--legacy-repo given but the manifest on disk carries no legacy_source {repo, tag, commit}; "
                "a person declares the pin first")
        if not re.fullmatch(r"[0-9a-f]{40}", pin["commit"]):
            die("legacy_source.commit must be a full 40-character sha, got %r" % pin["commit"])
        r = subprocess.run(["git", "-C", str(legacy_repo), "rev-parse", "-q", "--verify", pin["tag"] + "^{commit}"],
                           capture_output=True, text=True)
        if r.returncode != 0 or r.stdout.strip() != pin["commit"]:
            die("legacy_source: tag %s in %s is %s, the pin says %s (a moved tag is not the history this "
                "manifest was built from)" % (pin["tag"], legacy_repo, r.stdout.strip() or "missing", pin["commit"]))
        ltags = subprocess.run(["git", "-C", str(legacy_repo), "tag"], capture_output=True, text=True).stdout.split()
        top = tag_key(pin["tag"])
        legacy = {}
        for tag in sorted((t for t in ltags if tag_key(t) and tag_key(t) <= top), key=tag_key):
            for path, h in blob_hashes(legacy_repo, tag, lambda p: p in files and p != MANIFEST_REL).items():
                if files.get(path) != h:
                    legacy.setdefault(path, set()).add(h)
        legacy = {p: sorted(v) for p, v in sorted(legacy.items())}
    elif pin is not None or on_disk.get("legacy_previous"):
        legacy = on_disk.get("legacy_previous") or {}
        if not isinstance(legacy, dict) or not all(isinstance(v, list) for v in legacy.values()):
            die("legacy_previous on disk is not a map of path to a list of sha256")
        for p in sorted(legacy):
            if p not in files:
                fails.append("legacy_previous names %s, which this release does not ship; rebuild with "
                             "--legacy-repo" % p)
        legacy = {p: sorted(set(v) - {files.get(p)}) for p, v in sorted(legacy.items()) if p in files}
        legacy = {p: v for p, v in legacy.items() if v}
    if require_legacy and not isinstance(pin, dict):
        fails.append("no legacy_source: a myPKA release without the 1.x history of the team files writes a "
                     ".update beside every changed team file of an existing member (M2)")
    for p, v in (legacy or {}).items():
        previous.setdefault(p, set()).update(v)
    previous = {p: sorted(v) for p, v in sorted(previous.items())}

    # history (Flint step 14, 4.1): releases since the split only, i.e. tags
    # that carry .mypka/manifest.json; HEAD counts as VERSION when untagged.
    def has_manifest(t):
        return subprocess.run(["git", "cat-file", "-e", "%s:%s" % (t, MANIFEST_REL)], cwd=ROOT,
                              capture_output=True).returncode == 0
    split_tags = [t for t in sorted((t for t in git("tag").split() if tag_key(t)), key=tag_key) if has_manifest(t)]
    head_tags = [t for t in git("tag", "--points-at", "HEAD").split() if tag_key(t)]
    points = [(TAG_RE.fullmatch(t).group(1), t) for t in split_tags if t not in head_tags]
    if head_tags:
        points.append((TAG_RE.fullmatch(head_tags[0]).group(1), head_tags[0]))
    else:
        points.append((version, "HEAD"))
    notes = changelog_sections(CHANGELOG.read_text(encoding="utf-8")) if CHANGELOG.is_file() else {}

    def note_for(ver, path):
        # The line whose SUBJECT (first backticked name) is this exact path; a
        # line naming it in passing explains another file. An opening path is
        # dropped (the report shows it beside the note); a later one stays, so
        # no note reads "Removed: , the ..." (ICOR 2.0.0, Felix).
        tick = "`%s`" % path
        for line in notes.get(ver, "").splitlines():
            names = re.findall(r"`([^`]+)`", line)
            if not names or names[0] != path:
                continue
            text = line.strip().lstrip("-* ").strip()
            return text[len(tick):].strip(" :-") if text.startswith(tick) else text
        return ""
    history, prev = [], None
    for label, rev in points:
        if prev is None:
            prev = rev
            continue
        diff = ["diff", "--cached", "--name-status", "-M", prev] if rev == "HEAD" else \
            ["diff", "--name-status", "-M", prev, rev]
        removed, renamed, added = [], [], []
        old_hashes = None
        for line in git(*diff).splitlines():
            parts = line.split("\t")
            code = parts[0][0]
            if any(x in residue for x in parts[1:]):
                continue
            if code in ("D", "R") and old_hashes is None:
                old_hashes = blob_hashes(ROOT, prev, lambda p: True)
            if code == "D":
                note = note_for(label, parts[1])
                if note_hole(note):
                    fails.append("%s removes `%s` and its note has an empty name where a name belongs: %r; "
                                 "write the changelog line as \"- Removed: `%s`, what it was.\""
                                 % (label, parts[1], note, parts[1]))
                removed.append({"path": parts[1], "sha256": old_hashes.get(parts[1], ""), "note": note})
            elif code == "R":
                renamed.append({"from": parts[1], "to": parts[2], "from_sha256": old_hashes.get(parts[1], "")})
            elif code == "A":
                added.append(parts[1])
        history.append({"version": label, "date": git("log", "-1", "--format=%cs", "HEAD" if rev == "HEAD" else rev).strip(),
                        "removed": removed, "renamed": renamed, "added": added})
        prev = rev
    history.reverse()

    fails += reserved_problems(list(files) + list(generated))

    manifest = {
        "schema": SCHEMA,
        "name": on_disk.get("name") or "myPKA",
        "version": version,
        "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": git("rev-parse", "--short", "HEAD").strip(),
        "lab": "lab" in version.split("-", 1)[-1] if "-" in version else False,
        "requires": on_disk["requires"],
        "files": files,
        "repo_only": repo_only,
        "generated": generated,
        "seed": sorted(p for p in SEED if p in files),
        "agents": agents,
        "history": history,
        "previous": previous,
    }
    if legacy is not None:
        manifest["legacy_previous"] = legacy
    for k in ("source_commit", "legacy_source"):
        if on_disk.get(k):
            manifest[k] = on_disk[k]
    return version, on_disk, manifest, fails


def strip_volatile(m):
    return {k: v for k, v in m.items() if k not in VOLATILE}


def main(argv):
    args = argv[1:]
    legacy_repo = os.environ.get("MYPKA_LEGACY_REPO") or None
    if "--legacy-repo" in args:
        i = args.index("--legacy-repo")
        if i + 1 >= len(args):
            sys.exit("usage: --legacy-repo needs the path of an ICOR for Life Scaffold clone")
        legacy_repo = args[i + 1]
        del args[i:i + 2]
    unknown = [a for a in args if a not in ("--check", "--require-legacy")]
    if unknown:
        sys.exit("usage: build-mypka-manifest.py [--check] [--legacy-repo DIR] [--require-legacy]  (unknown: %s)"
                 % " ".join(unknown))
    check = "--check" in args

    # The icor-room-names block first: the manifest hashes the updater's bytes.
    updater_src = UPDATER.read_text(encoding="utf-8")
    want_src = splice_room_block(updater_src, room_block(schema_room_names()))
    room_fail = None
    if want_src != updater_src:
        if check:
            room_fail = ("%s: the generated icor-room-names block differs from the rooms of %s (a hand edit, "
                         "or the schema changed); run build-mypka-manifest.py" % (UPDATER.name, SCHEMA_REL))
        else:
            UPDATER.write_text(want_src, encoding="utf-8")
            print("OK wrote the icor-room-names block in %s" % UPDATER.name)

    version, on_disk, manifest, fails = build(Path(legacy_repo).expanduser().resolve() if legacy_repo else None,
                                              "--require-legacy" in args)

    sections = changelog_sections(CHANGELOG.read_text(encoding="utf-8")) if CHANGELOG.is_file() else {}
    if not CHANGELOG.is_file():
        fails.append(".mypka/CHANGELOG.md is missing; every version gets a section")
    elif not sections.get(version):
        fails.append(".mypka/CHANGELOG.md has no '## %s' section with content" % version)

    if room_fail:
        fails.insert(0, room_fail)
    if check:
        if not on_disk:
            fails.append("manifest.json does not exist; run build-mypka-manifest.py")
        elif strip_volatile(on_disk) != strip_volatile(manifest):
            diff = sorted(k for k in set(on_disk) | set(manifest)
                          if k not in VOLATILE and on_disk.get(k) != manifest.get(k))
            detail = ""
            if "files" in diff:
                a, b = on_disk.get("files") or {}, manifest["files"]
                moved = sorted(p for p in set(a) | set(b) if a.get(p) != b.get(p))
                detail = " (%d path(s), first: %s)" % (len(moved), ", ".join(moved[:3]))
            fails.append("manifest.json is stale in: %s%s; run build-mypka-manifest.py" % (", ".join(diff), detail))
        if fails:
            for f in fails:
                print("FAIL " + f, file=sys.stderr)
            return 1
        print("OK manifest %s is current: %d files, %d repo-only, %d generated, %d agents, %d paths with older states"
              % (version, len(manifest["files"]), len(manifest["repo_only"]), len(manifest["generated"]),
                 len(manifest["agents"]), len(manifest["previous"])))
        return 0

    hard = [f for f in fails if "CHANGELOG" not in f]
    if hard:
        for f in hard:
            print("FAIL " + f, file=sys.stderr)
        print("FAIL nothing written", file=sys.stderr)
        return 1
    META.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OK wrote %s: version %s, %d files, %d repo-only, %d generated, %d agents"
          % (MANIFEST_REL, version, len(manifest["files"]), len(manifest["repo_only"]),
             len(manifest["generated"]), len(manifest["agents"])))
    for f in fails:
        print("WARN " + f + "; --check will fail until it is written", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
