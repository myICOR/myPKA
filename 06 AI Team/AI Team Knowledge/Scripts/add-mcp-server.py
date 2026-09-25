#!/usr/bin/env python3
"""Wire an external tool's OFFICIAL MCP server into the scaffold.

Usage (stdio server):
  add-mcp-server.py --name linear --command npx \
      --args "-y @linear/mcp-server" --env LINEAR_API_KEY
Usage (remote server):
  add-mcp-server.py --name notion --transport http \
      --url https://mcp.notion.com/mcp

Writes the entry to .mcp.json and a PLACEHOLDER line to .env. Guards
(code, not prose):
  - server name must be lowercase-hyphenated and not already configured
  - anything secret-shaped in --args/--url is REFUSED: secret values
    belong in .env, referenced from .mcp.json as ${VAR}
  - env var names must be UPPER_SNAKE; existing .env values are never
    overwritten; values are never printed
"""
import argparse, importlib.util, json, re, sys
from pathlib import Path

# NO BYTECODE IN THE TREE WE ARE POINTED AT. This script importlib-loads a
# sibling out of Scripts/, and stock CPython then writes
# Scripts/__pycache__/<sibling>.cpython-3NN.pyc beside it, which is INSIDE the
# vault or the repo it was asked to read. A script that writes into the thing
# it measures is a script whose measurement nobody can trust, and the write is
# invisible under macOS's /usr/bin/python3, which redirects bytecode to its own
# cache (Conrad Froehling, 2026-09-16). PYTHONDONTWRITEBYTECODE is read at
# interpreter STARTUP, so only this assignment reaches a process already
# running.
sys.dont_write_bytecode = True

# noteio.py sits beside this script and is loaded by path, not by name, so
# the import needs nothing on sys.path, which is what lets this script run
# under the `-I -B -X utf8` the rendered hooks carry, with its own folder
# dropped from sys.path. A missing noteio.py is a half-upgraded Scripts/
# folder and says so in one line, because a traceback out of an import
# teaches the member nothing about what to do next.
_nio_path = Path(__file__).resolve().parent / "noteio.py"
if not _nio_path.is_file():
    raise SystemExit("FAIL noteio.py is missing from %s. Scripts/ is half "
                     "upgraded; restore noteio.py beside this script and run "
                     "this again." % _nio_path.parent)
_nio = importlib.util.spec_from_file_location("noteio", _nio_path)
noteio = importlib.util.module_from_spec(_nio)
_nio.loader.exec_module(noteio)

# resolve.py sits beside this script and is loaded by path, like noteio.py.
# It is the one code that finds the team root and turns a concept into a
# place (GL-1013 sections 6 and 9).
_rs_path = Path(__file__).resolve().parent / "resolve.py"
if not _rs_path.is_file():
    raise SystemExit("FAIL resolve.py is missing from %s. Scripts/ is half "
                     "upgraded; restore resolve.py beside this script and run "
                     "this again." % _rs_path.parent)
_rs = importlib.util.spec_from_file_location("mypka_resolve", _rs_path)
resolver = importlib.util.module_from_spec(_rs)
_rs.loader.exec_module(resolver)


def _team_root(explicit=None):
    """GL-1013 section 6: explicit, then CLAUDE_PROJECT_DIR when it holds the
    marker, then the walk up from this file."""
    try:
        return resolver.find_team_root(explicit=explicit, start=__file__).path
    except resolver.ResolveError as e:
        raise SystemExit("FAIL %s" % e)


ROOT = _team_root()
MCP = ROOT / ".mcp.json"
ENV = ROOT / ".env"
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]|api[_-]?key\s*=|token\s*=|secret|Bearer\s+\S|[A-Fa-f0-9]{32,})")

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--command")
ap.add_argument("--args", default="")
ap.add_argument("--transport", choices=["http", "sse"])
ap.add_argument("--url")
ap.add_argument("--env", action="append", default=[])
a = ap.parse_args()

if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.name):
    sys.exit(f"FAIL server name must be lowercase-hyphenated: {a.name}")
if bool(a.command) == bool(a.url):
    sys.exit("FAIL provide exactly one of --command (stdio) or --url (remote)")
for blob in (a.args or "", a.url or ""):
    if SECRET_RE.search(blob):
        sys.exit("FAIL secret-shaped value in args/url; put secrets in .env and reference ${VAR}")
for v in a.env:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", v):
        sys.exit(f"FAIL env var must be UPPER_SNAKE: {v}")

cfg = json.loads(noteio.read_note(MCP)[0]) if MCP.exists() else {"mcpServers": {}}
cfg.setdefault("mcpServers", {})
if a.name in cfg["mcpServers"]:
    sys.exit(f"FAIL server already configured: {a.name}")

entry = {}
if a.command:
    entry["command"] = a.command
    if a.args:
        entry["args"] = a.args.split()
else:
    entry["type"] = a.transport or "http"
    entry["url"] = a.url
if a.env:
    entry["env"] = {v: "${" + v + "}" for v in a.env}
cfg["mcpServers"][a.name] = entry
noteio.write_note(MCP, json.dumps(cfg, indent=2) + "\n")

# .env is a file the member edits by hand, so it keeps its own line
# endings: a placeholder appended with a bare "\n" into a CRLF .env leaves
# one mixed line behind, and every line after it reads as changed in git
# (Ian Slattery, T15-A).
existing, eol = noteio.read_note(ENV) if ENV.exists() else ("", "\n")
added = []
for v in a.env:
    if re.search(rf"^{v}=", existing, re.M):
        continue
    existing = (existing.rstrip("\r\n") + eol + f"{v}=" + eol
                if existing.strip() else f"{v}=" + eol)
    added.append(v)
noteio.write_note(ENV, existing)
print(f"OK {a.name} wired into .mcp.json" + (f"; fill in .env: {', '.join(added)}" if added else ""))
