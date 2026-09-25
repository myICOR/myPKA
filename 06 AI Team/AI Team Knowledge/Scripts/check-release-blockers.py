#!/usr/bin/env python3
"""check-release-blockers.py: no myPKA release while a legal text is still a
draft, a decision is still open in a shipped file, or a license file is not
the exact text it must be (Lex step 11b, Tom j5v, 2026-09-24).

Usage:
  check-release-blockers.py [--root DIR]
    DIR  the top of a myPKA git work tree (default: the one this script is in)

Repo-only. It runs in the myPKA repository, in the release workflow (Gate 1c)
and in run-red-tests.py (group step18, cases LG*), never in a member's folder.

It reads every tracked file (`git ls-files`, from the work tree). Blockers:

  B1  a line that starts with `DRAFT pending Themis` (a legal text not yet
      co-signed; Themis co-signed the step 11b texts on 2026-09-24, so none
      is expected, and a new draft must carry one).
  B2  an open bracket placeholder in the co-signed texts: a decision code
      bracket, an opening square bracket, three lowercase letters or digits,
      a colon and a space (w8t, u6j, q3m and s4c were filled on Tom's
      rulings of 2026-09-25), or the privacy contact email and privacy
      policy URL brackets in CONTRIBUTING.md (condition C7, filled the same
      day), or a condition
      bracket (an opening square bracket, C, a number, a colon and a space;
      the form Vex and Lex use for a pending contact). Each is a fact only
      Tom gives; Marshall replaces the bracket and changes nothing else.
  B3  `LICENSE-myPKA.md` exists (the pre-j5v placeholder; it grants nothing).
  B4  the words "affiliated holding entity" anywhere (one named owner, w8t).
  B5  `LICENSE` is not the CC BY-SA 4.0 legal code byte for byte (the
      sha256 Lex recorded), or `Scripts/LICENSE-myPKA` is not the bare MIT
      text with the holder line "Paperless Movement, S.L. and the myPKA
      authors".
  B6  `README-myPKA.md` still says it is a placeholder.
  B7  `SECURITY-myPKA.md` is missing or still the pre-split placeholder
      (Vex wrote the member security policy at step 18; GitHub shows it
      through the repo-only pointer `.github/SECURITY.md`).

Exempt from B1, B2 and B4: this file and run-red-tests.py (they state the
patterns).

Exit 0 = no blocker. Exit 1 = blockers, one per line as `Bn path:line: text`.
Exit 2 = it could not run (no git, not a work tree); a check that could not
run is never a 0.
"""
import hashlib, re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True

SC = "06 AI Team/AI Team Knowledge/Scripts/"
SELF = SC + "check-release-blockers.py"
EXEMPT = (SELF, SC + "run-red-tests.py")
DRAFT = re.compile(r"^DRAFT pending Themis")
PENDING = re.compile(r"\[[a-z0-9]{3}: |\[C[0-9]+: |\[privacy (contact email|policy URL)\]")
HOLDING = re.compile(r"affiliated\s+holding\s+entity", re.I)
STALE = "LICENSE-myPKA.md"
README = "README-myPKA.md"
README_PLACEHOLDER = re.compile(r"PLACEHOLDER|\*\*Status: placeholder\.\*\*")
SECURITY = "SECURITY-myPKA.md"
SECURITY_PLACEHOLDER = re.compile(r"PLACEHOLDER|\*\*Status: placeholder\.\*\*|Vex splits the scope section")
EXACT = {
    # CC BY-SA 4.0 legalcode.txt, 20138 bytes, 428 lines (Lex fetch, 2026-09-24)
    "LICENSE": "28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5",
    # bare MIT, Copyright (c) 2026 Paperless Movement, S.L. and the myPKA authors
    # (Lex step 11b, part 2 section 2; holder line per Lex 11f, 2026-09-25)
    SC + "LICENSE-myPKA": "170333a76ed584f3892d02c7b83cb68d8602cb29d09fdbbbe380cee7f6eecf5b",
}


def die(msg):
    print("CANNOT RUN " + msg, file=sys.stderr)
    sys.exit(2)


def main(argv):
    root = Path(__file__).resolve().parents[3]
    if argv[:1] == ["--root"] and len(argv) == 2:
        root = Path(argv[1]).resolve()
    elif argv:
        die("usage: check-release-blockers.py [--root DIR]")
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True)
    except FileNotFoundError:
        die("git is not installed")
    if r.returncode != 0:
        die("%s is not a git work tree: %s" % (root, r.stderr.decode(errors="replace").strip()))
    tracked = [p for p in r.stdout.decode("utf-8").split("\0") if p]
    hits = []
    for rel in tracked:
        f = root / rel
        if not f.is_file():
            continue
        if rel == STALE:
            hits.append("B3 %s: the pre-j5v licence placeholder is still tracked; delete it" % rel)
        if rel in EXEMPT:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if DRAFT.search(line):
                hits.append("B1 %s:%d: %s" % (rel, n, line.strip()[:160]))
            if PENDING.search(line):
                hits.append("B2 %s:%d: %s" % (rel, n, line.strip()[:160]))
            if HOLDING.search(line):
                hits.append("B4 %s:%d: %s" % (rel, n, line.strip()[:160]))
    for rel, want in EXACT.items():
        f = root / rel
        if rel not in tracked or not f.is_file():
            hits.append("B5 %s: missing (a license file must be tracked and ship)" % rel)
            continue
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        if got != want:
            hits.append("B5 %s: sha256 %s, want %s (never edit a license text; re-fetch it)" % (rel, got, want))
    rf = root / README
    if README in tracked and rf.is_file() and README_PLACEHOLDER.search(rf.read_text(encoding="utf-8")):
        hits.append("B6 %s: still the placeholder; the member-facing text is not written" % README)
    sf = root / SECURITY
    if SECURITY not in tracked or not sf.is_file():
        hits.append("B7 %s: missing (the member security policy must be tracked and ship)" % SECURITY)
    elif SECURITY_PLACEHOLDER.search(sf.read_text(encoding="utf-8")):
        hits.append("B7 %s: still the placeholder; the member security policy is not written" % SECURITY)
    for h in hits:
        print(h)
    if hits:
        print("BLOCKED: %d release blocker(s); the release waits until each is cleared" % len(hits))
        return 1
    print("OK no release blocker (%d tracked files read)" % len(tracked))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
