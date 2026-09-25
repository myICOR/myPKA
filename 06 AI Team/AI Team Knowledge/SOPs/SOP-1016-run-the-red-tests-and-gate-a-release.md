---
type: sop
id: SOP-1016
title: Run the red tests and gate a release
created: 2026-09-14
owner: mack
uses: ["[[GL-1005-code-vs-instructions]]"]
skill_name: red-tests
skill_summary: 'Feeds every guard in Scripts/ something it must reject and confirms it says no, then reports the count exactly as printed with the skips named; before a release the same suite runs against the staged tree and blocks the build while any guard has not gone red.'
skill_triggers:
  - 'run the red tests'
  - 'red-test the guards'
  - 'did every guard go red'
  - 'is the release gate green'
  - 'check the guards before the release'
skill_prerun: 'python3 "06 AI Team/AI Team Knowledge/Scripts/run-red-tests.py"'
---

# SOP-1016 Run the red tests and gate a release

A guard that has never been fed something it must reject is not known to
be a guard ([[GL-1005-code-vs-instructions|GL-1005]] rule 4: never ship a
gate you have not watched go red). This procedure is how the team watches.
Every step is a script; the model reads results and never states a count
it did not see print.

1. [SCRIPT] `Scripts/run-red-tests.py`. It feeds each guard in `Scripts/`
   an input it must refuse and an input it must allow, and prints one line
   per case. `OK n/n` is the only green. A `FAIL` names a guard that
   accepted what it must reject; fix the guard, never the test. A `SKIP`
   names a guard that could not run here and why; a skip is not a pass,
   and the count is reported with its skips every time.
2. [SCRIPT] After a guard is written or changed: its case in
   `Scripts/run-red-tests.py` (one input it must refuse, one clean control
   it must allow) is added first, then step 1 runs again and the new case
   is seen going red before the guard is registered in any host hook
   config ([[SOP-1007-hire-a-new-agent|SOP-1007]] step 6c for a guard a
   hire introduces).
3. [SCRIPT] Before a release: `Scripts/release-gate-red-tests.sh <staged
   tree>` runs the same suite against the bytes that will ship and exits 1
   with the runner's own `FAIL` lines while any guard has not gone red.
   `Scripts/build-release-zip.sh` calls it; no build while it is red.

What this does not prove: that a guard is registered in any host's hook
config, or that it runs on the runtime a member uses. It proves the script
refuses bad input when it is called, on this machine, on this run.
