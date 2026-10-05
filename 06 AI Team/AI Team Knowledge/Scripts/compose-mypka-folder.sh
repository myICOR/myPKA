#!/bin/sh
# compose-mypka-folder.sh: the myPKA 7 member zip, ONE folder.
#
# Repo-only (RESIDUE_PATHS in build-mypka-release.sh). Since 7.0.0 the member
# downloads one zip that holds both halves, as in v5: the content (the ICOR
# for Life release zip, pinned and attested by its own workflow) and the team
# (the zip build-mypka-release.sh builds from this tag, through every gate).
# This script only puts the two side by side; it changes no byte of either.
#
#   compose-mypka-folder.sh <team.zip> <content.zip> <output.zip> <epoch>
#
# Refuses (BLOCKED, exit 1) when:
#   - a path is in both zips (the halves must be disjoint: Gate 3 proves it on
#     the manifests, this proves it on the bytes that ship);
#   - the folder lacks what a member needs to start: AGENTS.md, README.md,
#     LICENSE, LICENSE.md, both VERSION files, Larry's contract, twelve
#     plugins under .obsidian/plugins/, the theme.
# The zip is written by zip-staged-tree.sh, so the same inputs and the same
# epoch give the same bytes.
set -eu
TEAM="${1:-}"; CONTENT="${2:-}"; OUT="${3:-}"; EPOCH="${4:-}"
block() { echo "BLOCKED compose: $*" >&2; exit 1; }
[ -f "$TEAM" ] && [ -f "$CONTENT" ] && [ -n "$OUT" ] && [ -n "$EPOCH" ] \
  || block "usage: compose-mypka-folder.sh <team.zip> <content.zip> <output.zip> <epoch>"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
LC_ALL=C; export LC_ALL
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mypka-compose.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
unzip -Z1 "$TEAM" | grep -v '/$' | sort > "$WORK/team.txt"
unzip -Z1 "$CONTENT" | grep -v '/$' | sort > "$WORK/content.txt"
both="$(comm -12 "$WORK/team.txt" "$WORK/content.txt")"
[ -z "$both" ] || block "in both halves (they must be disjoint): $(echo "$both" | head -5 | tr '\n' ' ')"
mkdir -p "$WORK/stage"
unzip -q "$CONTENT" -d "$WORK/stage"
unzip -q "$TEAM" -d "$WORK/stage"
have="$(cd "$WORK/stage" && find . -type f | wc -l | tr -d ' ')"
want="$(cat "$WORK/team.txt" "$WORK/content.txt" | wc -l | tr -d ' ')"
[ "$have" = "$want" ] || block "the folder holds $have files, the two zips list $want"
for f in AGENTS.md README.md LICENSE LICENSE.md README-myPKA.md .mypka/VERSION .icor-for-life/VERSION \
         .icor-for-life/manifest.json .mypka/manifest.json "06 AI Team/Agents/Larry/AGENT.md"; do
  [ -f "$WORK/stage/$f" ] || block "the folder has no $f"
done
plugins="$(find "$WORK/stage/.obsidian/plugins" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
[ "$plugins" -ge 12 ] || block "the folder has $plugins Obsidian plugins, not 12"
[ -d "$WORK/stage/.obsidian/themes" ] || block "the folder has no Obsidian theme"
sh "$SELF_DIR/zip-staged-tree.sh" "$WORK/stage" "$OUT" "$EPOCH" || block "the folder could not be archived reproducibly"
echo "OK $OUT: $have files ($(wc -l < "$WORK/content.txt" | tr -d ' ') content, $(wc -l < "$WORK/team.txt" | tr -d ' ') team), $plugins plugins, sha256 $(shasum -a 256 "$OUT" | cut -d' ' -f1)"
