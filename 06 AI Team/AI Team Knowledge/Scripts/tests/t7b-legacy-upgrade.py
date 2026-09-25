#!/usr/bin/env python3
"""T7b (Marshall M1, step 13): a 1.34.1 folder is upgraded through myPKA,
then ICOR for Life, in mode A. Zero crashes, zero deletions, and a .update
only beside the one file the member edited.

Usage (from anywhere; lab only, repo-only, needs git and the lab history):
  t7b-legacy-upgrade.py LAB            green run, exit 0 on a pass
  t7b-legacy-upgrade.py LAB --red      the same run with the M1 fix removed
                                       (the 1.x list manifest not read);
                                       exit 0 only when that run goes RED

LAB is the folder holding the two lab repositories `mypka/` and
`icor-for-life/`.

The 1.34.1 folder. The lab was cut from the Scaffold at f7dd5f0 (1.34.1)
with no rewrites, so the two baseline commits hold 1.34.1's bytes: mypka
`d4836f0` and icor-for-life `a819c6f`, plus the 24 files the step 10
placement commits (`dbc30ae`, `27320fa`) added at their 1.34.1 paths (names
that only exist since the split, like README-myPKA.md, are left out). The
lab-generated `.mypka/` is removed, `.icor-for-life/VERSION` says 1.34.1, and
the manifest is written in the 1.34.1 SHAPE (schema 1, `files` a list of
{path, sha256, kind, example}, `agents`, `history`) from those bytes. The
original 1.34.1 manifest file lives only in the Scaffold repository, which
this lab never reads (Marshall section E).

The releases are the lab working trees as they stand: myPKA's manifest
`files`, then ICOR's, copied like a zip would carry them.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

BASE = {"mypka": ("d4836f0", "dbc30ae"), "icor-for-life": ("a819c6f", "27320fa")}
SCRIPTS = "06 AI Team/AI Team Knowledge/Scripts"
NOT_1341 = {".gitignore", ".github/workflows/release.yml", "README-myPKA.md", "LICENSE-myPKA.md",
            "SECURITY-myPKA.md", "THIRD-PARTY-NOTICES-myPKA.md", SCRIPTS + "/README-myPKA.md",
            SCRIPTS + "/noteio-icor.py"}
M1_ANCHOR = "    if isinstance(f, list):\n        out = {}"


def sh(*a, **kw):
    return subprocess.run(list(a), capture_output=True, check=True, **kw)


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_1341(lab, v):
    for repo, (base, placed) in BASE.items():
        tar = sh("git", "-C", str(lab / repo), "archive", base).stdout
        sh("tar", "-x", "-C", str(v), input=tar)
        added = [l.split("\t", 1)[1] for l in sh("git", "-C", str(lab / repo), "diff", "--name-status", base, placed,
                                                 text=True).stdout.splitlines() if l.startswith("A\t")]
        for rel in added:
            if rel in NOT_1341:
                continue
            data = sh("git", "-C", str(lab / repo), "show", "%s:%s" % (placed, rel)).stdout
            (v / rel).parent.mkdir(parents=True, exist_ok=True)
            (v / rel).write_bytes(data)
    shutil.rmtree(v / ".mypka")
    (v / ".icor-for-life/VERSION").write_text("1.34.1\n", encoding="utf-8")
    (v / ".icor-for-life/manifest.json").unlink()
    files, agents = [], []
    for p in sorted(x for x in v.rglob("*") if x.is_file()):
        rel = p.relative_to(v).as_posix()
        files.append({"path": rel, "sha256": h(p), "kind": "doc", "example": False})
        parts = rel.split("/")
        if len(parts) == 4 and parts[:2] == ["06 AI Team", "Agents"] and parts[3] == "AGENT.md":
            agents.append({"name": parts[2], "path": rel})
    (v / ".icor-for-life/manifest.json").write_text(json.dumps(
        {"schema": 1, "name": "ICOR for Life Scaffold", "version": "1.34.1", "files": files,
         "agents": agents, "history": []}, indent=1), encoding="utf-8")
    return len(files)


def stage(root, meta, dest):
    man = json.loads((root / meta / "manifest.json").read_text(encoding="utf-8"))
    for rel in man["files"]:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dest / rel)
    return man


def run(lab, red):
    work = Path(tempfile.mkdtemp(prefix="t7b-"))
    try:
        v = work / "vault"
        v.mkdir()
        n = build_1341(lab, v)
        (v / "04 Inner World/Notes/my own note.md").write_text("mine\n", encoding="utf-8")
        (v / "AGENTS.md").write_bytes((v / "AGENTS.md").read_bytes() + b"\nMy own line.\n")
        before = {p.relative_to(v).as_posix() for p in v.rglob("*") if p.is_file()}
        rm, ri = work / "rel-mypka", work / "rel-icor"
        man_m = stage(lab / "mypka", ".mypka", rm)
        man_i = stage(lab / "icor-for-life", ".icor-for-life", ri)
        up = lab / "mypka" / SCRIPTS / "mypka-update.py"
        if red:
            src = up.read_text(encoding="utf-8")
            if M1_ANCHOR not in src:
                return ["the M1 anchor is gone from mypka-update.py; the red run cannot be built"]
            up = work / "mypka-update.py"
            up.write_text(src.replace(M1_ANCHOR, "    if False:\n        out = {}", 1), encoding="utf-8")
            shutil.copy2(lab / "mypka" / SCRIPTS / "resolve.py", work / "resolve.py")
        out = []
        env = {k: val for k, val in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        for product, rel in (("mypka", rm), ("icor", ri)):
            r = subprocess.run([sys.executable, str(up), "--release", str(rel), "--target", str(v),
                                "--product", product, "--live"], capture_output=True, text=True, env=env)
            print("---- %s: exit %d" % (product, r.returncode))
            print("\n".join(l for l in r.stdout.splitlines() if not l.startswith(("SAME", "UPDATE", "ADD")))[-1500:])
            if r.stderr.strip():
                print(r.stderr.strip()[-1500:])
            if r.returncode != 0 or "Traceback" in r.stderr:
                out.append("%s update: exit %d" % (product, r.returncode))
        after = {p.relative_to(v).as_posix() for p in v.rglob("*") if p.is_file()}
        gone = sorted(before - after)
        if gone:
            out.append("%d file(s) deleted: %s" % (len(gone), gone[:3]))
        ups = sorted(p for p in after if p.endswith(".update"))
        if ups != ["AGENTS.md.update"]:
            out.append("expected exactly AGENTS.md.update, got %d .update file(s): %s" % (len(ups), ups[:5]))
        for man, root in ((man_m, rm), (man_i, ri)):
            for rel in man["files"]:
                if rel in ("AGENTS.md",) or rel in (man.get("seed") or []):
                    continue
                if not (v / rel).is_file() or h(v / rel) != h(root / rel):
                    out.append("%s is not the released bytes after the update" % rel)
                    break
        print("T7b: 1.34.1 folder of %d files, myPKA %s then ICOR %s, %d .update" % (
            n, man_m["version"], man_i["version"], len(ups)))
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    if len(argv) < 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    lab, red = Path(argv[1]).expanduser().resolve(), "--red" in argv[2:]
    out = run(lab, red)
    if red:
        if out:
            print("RED-WATCHED T7b under the 1.x list manifest not read: %s" % out[0])
            return 0
        print("FAIL T7b stayed green with the M1 fix removed; the test measures nothing")
        return 1
    for o in out:
        print("FAIL T7b: %s" % o)
    print("OK T7b" if not out else "FAILED T7b (%d)" % len(out))
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
