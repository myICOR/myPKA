#!/usr/bin/env python3
"""Validate the myPKA team tree: the team half of the old validate-scaffold.py.

validate-scaffold.py (ICOR for Life) checks the CONTENT: rooms, naming,
theme, planner, notes, templates. It runs on the ICOR for Life root alone.
This script checks what the TEAM ships and keeps, under the team root (the
folder holding AGENTS.md and the agents concept). In mode A that is the one
shared folder; in mode B it is the myPKA folder, and nothing here reads the
content source. Split: 10-placement row 3, Ada step 8 finding F1.

Checks (all deterministic, GL-1005):
  1. The team concept folders exist: agents, sops, workstreams, guidelines,
     scripts, expansions, ai_sessions, session_logs, and the four task
     states. Paths come from the resolver (GL-1013), never restated here.
  2. Session logs and done/cancelled tasks sit in YYYY/MM/ (was
     validate-scaffold check 5).
  3. Every agent folder carries AGENT.md and its bio <Name>.md, and every
     contract carries a well-formed, unique myicor_id with the template on
     the nil placeholder, checked by mint-agent-ids.py --check so the rule
     has one home (was validate-scaffold check 9).
  4. The root entry contract: AGENTS.md is the canonical entry, AGENT.md and
     ADAPTER-PROMPT.md point at it, and a CLAUDE.md, when a member adds one,
     imports @AGENTS.md and stays thin (was validate-scaffold check 15).

Exit 0 = compliant. Exit 1 = violations listed on stderr.

Usage: validate-team.py [<team-root>] [--json]
  <team-root>  default: the resolver's walk up from this file. The
               environment is never consulted: a validator measures the tree
               it is named for or the one it sits in.
  --json       print {"root", "ok", "fails", "skipped", "sources"} on stdout
               instead of the OK line; FAIL lines still go to stderr.
"""
# A script launched from Scripts/ has Scripts/ at the FRONT of sys.path, so a
# `Scripts/json.py` would shadow the stdlib before this file read a byte (Vex
# ruling W7, 2026-09-16).
import sys, os                                                   # noqa: E401
sys.dont_write_bytecode = True
if sys.path and __name__ == "__main__":
    _first = os.path.realpath(sys.path[0] or os.getcwd())
    if _first == os.path.dirname(os.path.realpath(__file__)):
        del sys.path[0]

import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
_rs_path = HERE / "resolve.py"
if not _rs_path.is_file():
    raise SystemExit("FAIL resolve.py is missing from %s. Scripts/ is half "
                     "upgraded; restore resolve.py beside this script and run "
                     "this again." % HERE)
_rs = importlib.util.spec_from_file_location("mypka_resolve", _rs_path)
resolver = importlib.util.module_from_spec(_rs)
_rs.loader.exec_module(resolver)

JSON = "--json" in sys.argv[1:]
args = [a for a in sys.argv[1:] if a != "--json"]
try:
    _root = resolver.find_team_root(explicit=args[0] if args else None, start=__file__, env={})
except resolver.ResolveError as e:
    print("FAIL %s" % e, file=sys.stderr)
    sys.exit(1)
ROOT = _root.path
fails = []
skipped = []
sources = {}


def tp(concept, slot=None):
    return resolver.team_path(concept, slot, root=ROOT)


def rel(p):
    try:
        return Path(p).relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


# --- 1. the team folders ----------------------------------------------------
REQUIRED_CONCEPTS = ("expansions", "workstreams", "sops", "guidelines", "scripts",
                     "session_logs", "agents", "ai_sessions")
required = [tp(c) for c in REQUIRED_CONCEPTS]
required += [tp("tasks", s) for s in ("open", "in_progress", "done", "cancelled")]
for p in required:
    if not p.is_dir():
        fails.append("missing required folder: %s" % rel(p))

# --- 2. date nesting --------------------------------------------------------
for label, base in (("Session Logs", tp("session_logs")),
                    ("Tasks/done", tp("tasks", "done")),
                    ("Tasks/cancelled", tp("tasks", "cancelled"))):
    if base.is_dir():
        for f in base.rglob("*.md"):
            r = f.relative_to(base)
            if len(r.parts) != 3:
                fails.append("%s entry not in YYYY/MM/: %s" % (label, r))

# --- 3. agent folders and the stable identity -------------------------------
agents = tp("agents")
if agents.is_dir():
    for d in sorted(agents.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            if not (d / "AGENT.md").is_file():
                fails.append("agent folder missing AGENT.md: %s" % d.name)
            if not (d / ("%s.md" % d.name)).is_file():
                fails.append("agent folder missing user-facing bio %s.md: %s" % (d.name, d.name))
    mint = HERE / "mint-agent-ids.py"
    if not mint.is_file():
        fails.append("mint-agent-ids.py is missing from %s; the myicor_id check cannot run" % HERE)
    else:
        sources["3"] = rel(mint) if str(mint).startswith(str(ROOT)) else str(mint)
        r = subprocess.run([sys.executable, str(mint), "--check", "--root", str(ROOT)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            relayed = [ln[5:] for ln in (r.stderr or "").splitlines() if ln.startswith("FAIL ")]
            if not relayed:
                tail = ((r.stderr or r.stdout).strip().splitlines() or ["no output"])[-1]
                relayed = ["mint-agent-ids.py --check failed without a FAIL line: %s" % tail]
            fails.extend(relayed)

# --- 4. the root entry contract ---------------------------------------------
canonical = ROOT / "AGENTS.md"
if not canonical.is_file() or len(canonical.read_text(encoding="utf-8").strip()) < 200:
    fails.append("missing or empty canonical root AGENTS.md")
# AGENTS.md is the only entry file (Tom, 2026-09-24): no CLAUDE.md ships, and
# Claude Code 2.1.277+ reads AGENTS.md when there is none. A CLAUDE.md the
# member adds is optional, but it switches that fallback off, so if one exists
# it must still import @AGENTS.md and stay thin.
for name in ("CLAUDE.md", "AGENT.md", "ADAPTER-PROMPT.md"):
    entry = ROOT / name
    if name == "CLAUDE.md" and not entry.exists():
        continue
    if not entry.is_file():
        fails.append("missing root entry: %s" % name)
        continue
    content = entry.read_text(encoding="utf-8")
    if "AGENTS.md" not in content:
        fails.append("root entry does not point to AGENTS.md: %s" % name)
    if name == "CLAUDE.md" and not re.search(r"^@AGENTS\.md$", content, re.M):
        fails.append("CLAUDE.md must import @AGENTS.md directly")
    if name in ("CLAUDE.md", "AGENT.md") and len(content) > 1500:
        fails.append("root adapter duplicates rules instead of a thin pointer: %s" % name)

for msg in fails:
    print("FAIL %s" % msg, file=sys.stderr)
if JSON:
    print(json.dumps({"root": str(ROOT), "ok": not fails, "fails": fails,
                      "skipped": skipped, "sources": sources}, indent=2))
elif not fails:
    print("OK team at %s is compliant" % ROOT)
sys.exit(1 if fails else 0)
