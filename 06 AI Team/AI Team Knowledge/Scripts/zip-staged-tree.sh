#!/bin/sh
# zip-staged-tree.sh: turn a staged tree into a zip that is a pure function of
# that tree's CONTENT, on any machine, in any locale, at any clock.
#
# Usage: zip-staged-tree.sh <tree> <output.zip> <epoch>
#   exit 0  the zip was written
#   exit 1  BLOCKED, with the reason on stderr; no zip is written
#
# WHY IT IS ITS OWN FILE
# Same reason as release-gate-red-tests.sh: build-release-zip.sh needs a git
# mirror, the gh CLI and the network, so a red test cannot call it, and a rule
# nothing can test is a rule nobody has watched work. This takes a tree and an
# output path, so run-red-tests.py can build a fixture twice under different
# locales and clocks and assert one sha256, and can plant the one thing that
# must block and watch it block.
#
# THE THREE THINGS THAT MAKE TWO ZIPS OF ONE TREE DIFFER
#   1. Entry ORDER. A directory walk is filesystem order, and `sort` is
#      locale order. Both are pinned: one sorted list, LC_ALL=C.
#   2. Entry TIMES. The zip format keeps local time, so the clock is pinned to
#      UTC and every entry is stamped with the staged commit's timestamp.
#      `-X` drops the per-file extra attributes on top of that.
#   3. Entry CONTENT that is not in the commit. This is the one that cost a
#      release. On 2026-09-15 the member zip was byte-unstable on the CI
#      runner and byte-stable on the maintainer's Mac: the red-test gate
#      imports three Scripts modules out of the STAGED tree with importlib,
#      CPython writes their `__pycache__/*.pyc` next to them inside that tree,
#      and a .pyc embeds the absolute path of its source, which is a mktemp
#      directory with six random characters in its name. Three entries of the
#      zip therefore changed on every build. On the Mac nothing was visible at
#      all, because Apple's /usr/bin/python3 redirects the bytecode cache to
#      ~/Library/Caches/com.apple.python and the files never reached the tree.
#      build-release-zip.sh now runs that gate against a COPY of the staged
#      tree, so nothing a gate does can reach the shipping bytes. This is the
#      second lock: compiled bytecode in the tree BLOCKS the zip. It is never
#      filtered out quietly, because a filter hides the thing that put it
#      there, and the next writer will not be bytecode.
set -eu

TREE="${1:-}"
OUT="${2:-}"
EPOCH="${3:-}"

if [ -z "$TREE" ] || [ ! -d "$TREE" ] || [ -z "$OUT" ] || [ -z "$EPOCH" ]; then
  echo "BLOCKED zip: usage: zip-staged-tree.sh <tree> <output.zip> <epoch>" >&2
  exit 1
fi
case "$EPOCH" in
  ''|*[!0-9]*) echo "BLOCKED zip: '$EPOCH' is not a unix timestamp" >&2; exit 1 ;;
esac

LC_ALL=C
TZ=UTC
export LC_ALL TZ

# The zip is written from inside the tree, so a relative output path would
# land in the tree it is archiving. Resolve it first, against the caller's
# working directory.
case "$OUT" in
  /*) ;;
  *)  OUT="$(pwd)/$OUT" ;;
esac
outdir="$(dirname "$OUT")"
if [ ! -d "$outdir" ]; then
  echo "BLOCKED zip: the output directory $outdir does not exist" >&2
  exit 1
fi

# Compiled bytecode is never part of a commit and never part of a download.
# Its presence means something ran inside the tree that is about to ship.
found="$(find "$TREE" \( -type d -name "__pycache__" -o -type f -name "*.pyc" -o -type f -name "*.pyo" \) | LC_ALL=C sort)"
if [ -n "$found" ]; then
  echo "BLOCKED zip: the tree carries compiled bytecode, so something ran inside the bytes that are about to ship:" >&2
  echo "$found" | sed "s|^$TREE/|                 |" >&2
  echo "                 A .pyc embeds the absolute path of its source, so it changes every build and the zip stops being a function of the commit. Run whatever wrote it against a copy of the tree, not the tree." >&2
  exit 1
fi

# Every entry carries the staged commit's time. Symlinks are stamped without
# following them: the target may sit outside the tree.
python3 - "$TREE" "$EPOCH" <<'PYSTAMP'
import os, sys
root, t = sys.argv[1], int(sys.argv[2])
for d, dirs, files in os.walk(root):
    for n in dirs + files:
        os.utime(os.path.join(d, n), (t, t), follow_symlinks=False)
os.utime(root, (t, t))
PYSTAMP

# `zip` UPDATES an archive that already exists: entries the tree no longer has
# would survive into it. On 2026-09-04 a second build on one day merged into
# the morning's zip and shipped a folder that had been removed. The archive is
# removed first, so the zip is always a fresh copy of the tree it was given.
rm -f "$OUT"
( cd "$TREE" && find . -type f ! -name ".DS_Store" | sed 's|^\./||' | LC_ALL=C sort \
  | TZ=UTC zip -qX "$OUT" -@ )
[ -f "$OUT" ] || { echo "BLOCKED zip: no archive was written to $OUT" >&2; exit 1; }
