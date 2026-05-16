#!/usr/bin/env bash
# build-scaffold-release.sh — build the myPKA scaffold release artifacts.  [AUTO-39]
# ---------------------------------------------------------------------------
# Produces, for a given scaffold version:
#   1. mypka-scaffold-v<version>.zip   — deterministic ZIP of the tracked tree
#   2. scaffold-manifest.json          — per-file sha256 map of every file the
#      scaffold version ships. This is the classifier `mypka update` relies on
#      for the Option-D scaffold-merge (AUTO-36 §5.6.1): it lets the updater
#      tell shipped-unmodified / shipped-modified / user-created files apart.
#
#   Usage:  scripts/build-scaffold-release.sh <version> [output-dir]
#   e.g.    scripts/build-scaffold-release.sh 1.10.3
#
# Run from the myPKA repo root. The ZIP contains the git-tracked tree, flat
# (no version-prefix dir) — consistent with existing myPKA release ZIPs.
# Deterministic: `git archive` emits a stable, sorted, fixed-mtime archive,
# so the same commit yields a byte-identical ZIP (stable sha256).
# ---------------------------------------------------------------------------
set -euo pipefail

VERSION="${1:?usage: build-scaffold-release.sh <version> [output-dir]}"
OUT_DIR="${2:-dist}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Guard: the VERSION file must match the requested version.
if [[ -f VERSION ]]; then
  FILE_VERSION="$(tr -d '[:space:]' < VERSION)"
  if [[ "$FILE_VERSION" != "$VERSION" ]]; then
    echo "error: VERSION file ($FILE_VERSION) != requested version ($VERSION)" >&2
    exit 1
  fi
fi

mkdir -p "$OUT_DIR"
OUT_ABS="$(cd "$OUT_DIR" && pwd)"
ZIP="$OUT_ABS/mypka-scaffold-v${VERSION}.zip"
MANIFEST="$OUT_ABS/scaffold-manifest.json"
rm -f "$ZIP" "$MANIFEST"

# --- 1. Deterministic ZIP — git archive of HEAD (tracked files only) --------
git archive --format=zip -o "$ZIP" HEAD
ZIP_SHA="$(shasum -a 256 "$ZIP" | cut -d' ' -f1)"
ZIP_SIZE="$(wc -c < "$ZIP" | tr -d ' ')"

# --- 2. scaffold-manifest.json — per-file sha256 of every tracked file ------
# Hash each git-tracked file exactly as it ships. Paths are repo-relative,
# forward-slash, sorted — the stable shape `mypka update` will diff against.
python3 - "$VERSION" "$MANIFEST" <<'PY'
import sys, json, hashlib, subprocess

version, manifest_path = sys.argv[1], sys.argv[2]
files = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
files = sorted(f.decode("utf-8") for f in files if f)

file_hashes = {}
for path in files:
    with open(path, "rb") as fh:
        file_hashes[path] = "sha256:" + hashlib.sha256(fh.read()).hexdigest()

manifest = {
    "scaffold_version": version,
    "file_count": len(file_hashes),
    "files": file_hashes,
}
with open(manifest_path, "w") as out:
    json.dump(manifest, out, indent=2, sort_keys=True)
    out.write("\n")
print(f"scaffold-manifest.json: {len(file_hashes)} files")
PY

MANIFEST_SHA="$(shasum -a 256 "$MANIFEST" | cut -d' ' -f1)"

echo "built:               $ZIP"
echo "scaffold version:    $VERSION"
echo "zip sha256:          $ZIP_SHA"
echo "zip size bytes:      $ZIP_SIZE"
echo "manifest:            $MANIFEST"
echo "manifest sha256:     $MANIFEST_SHA"

# Emit machine-readable outputs when running under GitHub Actions.
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "zip=$ZIP"
    echo "manifest=$MANIFEST"
    echo "zip_sha256=$ZIP_SHA"
    echo "zip_size=$ZIP_SIZE"
    echo "manifest_sha256=$MANIFEST_SHA"
  } >> "$GITHUB_OUTPUT"
fi
