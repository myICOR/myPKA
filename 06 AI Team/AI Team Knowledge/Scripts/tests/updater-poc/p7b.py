# P7b (Vex, step 13 approval): KNOWN OPEN until the step 18 attestations.
# The updater checks that a release is intact (every hash matches its own
# manifest); it cannot tell who built it. A release whose file was tampered
# and whose manifest was re-hashed to match is applied, live. The fix for
# 6.0.0 is GitHub build-provenance attestations on the release zips, checked
# with `gh attestation verify` (10-placement.md H2, plan step 18). Until then
# this script is expected to print "AGENTS.md now: TAMPERED".
from h import *
W = Path("w7"); shutil.rmtree(W, ignore_errors=True)
T = W/"t/mypka"; installed(T, "mypka", "1.0.0", {"AGENTS.md": "orig\n"})
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "TAMPERED\n"})
run(R, T, live=True); print("AGENTS.md now:", (T/"AGENTS.md").read_text())
