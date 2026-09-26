#!/usr/bin/env bash
# build-mypka-release.sh: build the myPKA member zip from one commit, through
# every gate, locally or in CI. Repo-only (plan step 12); the name was
# reserved in step 10.
#
# Usage: build-mypka-release.sh <output-dir>
#   MYPKA_REF            the commit or tag to build (default HEAD). A tag must
#                        equal .mypka/VERSION at that commit, with or without
#                        a leading v (myPKA tags are v6.0.0, Marshall M3).
#   MYPKA_GATE_CONTENT   a content source tree (an ICOR for Life checkout at
#                        the pinned version). REQUIRED: the red-test suite is
#                        the combined suite until it is split per repo, so it
#                        runs on a mode A merge: this tree first, the staged
#                        myPKA tree over it.
#   ICOR_RED_RUNNER      passed through to release-gate-red-tests.sh (the red
#                        tests use it to stub the suite).
#   exit 0  the zip was written: <output-dir>/myPKA-<version>.zip
#   exit 1  BLOCKED, reasons on stderr, nothing written
#
# Order: stage the commit (git archive, so only tracked bytes), strip the
# repo-only files, prove the staged tree is exactly the manifest's `files`,
# run the red-test gate on a COPY merged with the content source, prove the
# gate wrote nothing into the stage, zip with zip-staged-tree.sh stamped with
# the commit's time. Same order and the same reasons as ICOR's
# build-release-zip.sh, minus the plugins and the network.
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
S="06 AI Team/AI Team Knowledge/Scripts"
OUT_DIR="${1:-}"
REF="${MYPKA_REF:-HEAD}"
CONTENT="${MYPKA_GATE_CONTENT:-}"

block() { echo "BLOCKED $*" >&2; exit 1; }

[ -n "$OUT_DIR" ] || block "usage: build-mypka-release.sh <output-dir>"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"
REPO="$(git -C "$SELF_DIR" rev-parse --show-toplevel 2>/dev/null)" || block "not inside the myPKA repository"
git -C "$REPO" rev-parse --verify -q "$REF^{commit}" >/dev/null || block "ref '$REF' is not a commit here"

# The files that live in the repo and never reach a member. The manifest
# builder reads this array as the one source of `repo_only`; keep one quoted
# path per line.
declare -a RESIDUE_PATHS=(
  ".gitignore"
  "README.md"
  "MIGRATING-FROM-5.md"
  "VERSION"
  ".github/workflows/release-mypka.yml"
  ".github/SECURITY.md"
  "06 AI Team/AI Team Knowledge/Scripts/build-mypka-release.sh"
  "06 AI Team/AI Team Knowledge/Scripts/build-mypka-manifest.py"
  "06 AI Team/AI Team Knowledge/Scripts/check-disjoint.py"
  "06 AI Team/AI Team Knowledge/Scripts/check-release-blockers.py"
  "06 AI Team/AI Team Knowledge/Scripts/check-room-literals.py"
  "06 AI Team/AI Team Knowledge/Scripts/check-version-bump.py"
  "06 AI Team/AI Team Knowledge/Scripts/release-gate-red-tests.sh"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/README.md"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/fix.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/h.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/p1.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/p2.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/p4.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/p5.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/p7b.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/verify.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/updater-poc/verify-fixed.py"
  "06 AI Team/AI Team Knowledge/Scripts/tests/t7b-legacy-upgrade.py"
)

VERSION="$(git -C "$REPO" show "$REF:.mypka/VERSION" 2>/dev/null | tr -d '[:space:]')" \
  || block ".mypka/VERSION is missing at $REF"
if git -C "$REPO" rev-parse -q --verify "refs/tags/$REF" >/dev/null && [ "${REF#v}" != "$VERSION" ]; then
  block "tag $REF does not equal .mypka/VERSION $VERSION"
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/mypka-release.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
STAGE="$WORK/stage"
mkdir -p "$STAGE"
git -C "$REPO" archive --format=tar "$REF" | tar -x -C "$STAGE"
for rp in "${RESIDUE_PATHS[@]}"; do rm -f "$STAGE/$rp"; done
find "$STAGE" -type d -empty -delete

echo "==> manifest gate (the staged tree is exactly the manifest's files)"
python3 - "$STAGE" <<'PY' || block "the staged tree and .mypka/manifest.json disagree (see above)"
import hashlib, json, os, sys
stage = sys.argv[1]
m = json.load(open(os.path.join(stage, ".mypka/manifest.json"), encoding="utf-8"))
want = m.get("files") or {}
have = set()
for d, _dirs, names in os.walk(stage):
    for n in names:
        have.add(os.path.relpath(os.path.join(d, n), stage).replace(os.sep, "/"))
bad = 0
for p in sorted(have - set(want)):
    print("  in the zip, not in the manifest: %s" % p, file=sys.stderr); bad += 1
for p in sorted(set(want) - have):
    print("  in the manifest, not in the zip: %s" % p, file=sys.stderr); bad += 1
for p in sorted(set(want) & have):
    if want[p] == "self":
        continue
    if hashlib.sha256(open(os.path.join(stage, p), "rb").read()).hexdigest() != want[p]:
        print("  hash differs from the manifest: %s" % p, file=sys.stderr); bad += 1
if bad:
    sys.exit(1)
print("    %d files, all hashes match" % len(want))
PY

snapshot() {  # $1 label -> a sorted sha256 listing of the stage
  (cd "$STAGE" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) > "$WORK/staged-$1.txt"
}
snapshot 01-after-staging

echo "==> red-test gate (on a mode A merge copy, never on the stage)"
[ -n "$CONTENT" ] && [ -d "$CONTENT" ] \
  || block "MYPKA_GATE_CONTENT names no content tree; the suite needs a content source to run, and an unproven tree does not ship"
PROBE="$WORK/probe"
mkdir -p "$PROBE"
( cd "$CONTENT" && tar -c --exclude=.git . ) | tar -x -C "$PROBE"
cp -a "$STAGE"/. "$PROBE"/
if ! PYTHONDONTWRITEBYTECODE=1 sh "$REPO/$S/release-gate-red-tests.sh" "$PROBE"; then
  block "red-tests: a guard in the staged tree did not refuse what it must refuse"
fi
rm -rf "$PROBE"
snapshot 02-after-red-tests
cmp -s "$WORK/staged-01-after-staging.txt" "$WORK/staged-02-after-red-tests.txt" \
  || block "the gates changed the staged tree; a zip must be a function of the commit"

NAME="myPKA-$VERSION.zip"
EPOCH="$(git -C "$REPO" log -1 --format=%ct "$REF")"
echo "==> zipping -> $OUT_DIR/$NAME"
sh "$REPO/$S/zip-staged-tree.sh" "$STAGE" "$OUT_DIR/$NAME" "$EPOCH" \
  || block "the staged tree could not be archived reproducibly"
echo "OK $OUT_DIR/$NAME sha256 $(shasum -a 256 "$OUT_DIR/$NAME" | cut -d' ' -f1)"
