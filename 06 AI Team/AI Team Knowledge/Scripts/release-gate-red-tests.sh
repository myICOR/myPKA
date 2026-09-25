#!/bin/sh
# release-gate-red-tests.sh: no release while a guard has not been watched
# go red.
#
# Usage: release-gate-red-tests.sh <tree>
#   exit 0  every guard in <tree> refused what it must refuse
#   exit 1  BLOCKED, with the runner's own FAIL lines above
#
# WHY IT IS ITS OWN FILE
# run-red-tests.py was "run on demand" by nobody, and two of its gates sat
# red for three days for a missing-dependency reason while the suite kept
# being described as green (tsk-2026-09-11-005). A runner nobody runs is a
# document, not a gate. This is the one place that must run it: a release.
#
# It is a separate file rather than ten lines inside build-release-zip.sh so
# that it can be red-tested. build-release-zip.sh needs a git mirror, the gh
# CLI and the network; a red test cannot call it. This takes the tree as an
# argument and the runner from ICOR_RED_RUNNER, so run-red-tests.py can test
# the gate itself with a stub that refuses and a stub that passes.
#
# It runs against the STAGED tree, which is the bytes that will ship, not the
# dev checkout. A staged tree has no .git, so the suite's manifest guards
# report SKIP with their reason. A skip is not a green and is printed as
# itself.
#
# WHAT THIS DOES NOT PROVE
# - That the guards are registered in any host's hook config. It proves the
#   scripts refuse bad input when called; whether a host calls them is a
#   different fact, and .claude/settings.json is a different file.
# - That the suite covers every guard. Coverage is a judgement nobody has
#   automated yet; the suite proves only the cases it carries.
# - Anything about a member's machine. It ran here.
set -eu

TREE="${1:-}"
if [ -z "$TREE" ] || [ ! -d "$TREE" ]; then
  echo "BLOCKED red-tests: no tree to test (usage: release-gate-red-tests.sh <tree>)" >&2
  exit 1
fi

RUNNER="${ICOR_RED_RUNNER:-$TREE/06 AI Team/AI Team Knowledge/Scripts/run-red-tests.py}"
if [ ! -f "$RUNNER" ]; then
  echo "BLOCKED red-tests: the suite is not in the tree at $RUNNER, so nothing was proven" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "BLOCKED red-tests: python3 is not installed, so the suite could not run. A release is not allowed on an unproven tree." >&2
  exit 1
fi

if python3 "$RUNNER"; then
  exit 0
fi
echo "BLOCKED red-tests: a guard accepted input it must reject (see the FAIL lines above). Fix the guard, never the test." >&2
exit 1
