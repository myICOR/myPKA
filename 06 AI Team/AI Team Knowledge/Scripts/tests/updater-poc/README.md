# updater-poc: Vex's step 13 proofs against mypka-update.py

Repo-only (listed in RESIDUE_PATHS of build-mypka-release.sh). Copied from the
step 13 review's scratchpad on 2026-09-24, because the scratchpad is
session-only.

| File | What it proves |
|---|---|
| `h.py` | shared helpers: fixture folders, releases, installed manifests |
| `p1.py` | P1: mode A, a myPKA release overwrites ICOR's files through a case-only variant |
| `p2.py` | P2 (`.GIT/`), P3 (cross-product planting), P8 (`AGENTS.LOCAL.md`), P6 (unlisted manifest over a symlinked `.mypka`) |
| `p4.py` | P4: a folder swapped for a symlink between plan and write |
| `p5.py` | P5 (unreadable installed version), P7 (no authenticity, dry run, on its own target) |
| `p7b.py` | P7 live: a tampered release with a re-hashed manifest is applied. KNOWN OPEN until the step 18 build-provenance attestations (`gh attestation verify`); expected output today is `AGENTS.md now: TAMPERED` |
| `fix.py` | Vex's proposed no-follow writer (R2), now in the updater |
| `verify.py` | swaps `fix.py` into the step 12 updater (it predates the fix: on the fixed updater the signature differs) |
| `verify-fixed.py` | the same three scenarios against the fixed updater, no swap |

Run each from this folder with `python3 <file>`. They write their fixture
folders (`w1` to `w8`, `v0` to `v6`) here; those are ignored by git. The red
cases UP17 to UP22 in `run-red-tests.py` carry the same proofs into the suite.
