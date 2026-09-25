#!/usr/bin/env python3
"""Give every agent contract its stable identity: `myicor_id` in AGENT.md.

Origin: the ICOR for Life Scaffold repository, at
06 AI Team/AI Team Knowledge/Scripts/mint-agent-ids.py. A vault that carries
this script (My Life Folder does) carries that file unchanged: edit the
Scaffold's copy first, then copy it over. One source.

What the field is (GL-1002, "Agents: the stable identity"): a UUID v4,
lowercase, minted once when the agent is hired and never changed again.
The name, the avatar and the contract text may all change under the
member's hands; the id is the one fact by which an installer can tell an
agent that is already in the vault from one that is not. It is the same
UUID a myICOR library row for that agent carries as its primary key.

Usage:
  mint-agent-ids.py [--root DIR]           insert myicor_id where it is
                                            missing (a fresh UUID v4, or the
                                            one --map names), print a table
  mint-agent-ids.py --check [--root DIR]   write nothing; exit 1 if a
                                            contract lacks the field, carries
                                            a malformed one, shares one with
                                            another, or a template is not on
                                            the placeholder
  mint-agent-ids.py --export [--root DIR]  write nothing; print {name: id}
                                            JSON for every real agent (the
                                            way the shipped agents carry the
                                            same identity into another vault)
  --map FILE                               {name: id} JSON; an agent named
                                            there receives that id instead of
                                            a fresh one

Rules, all deterministic (GL-1005):
  - Walks 06 AI Team/Agents/<Name>/AGENT.md; <Name> is the agent's name.
  - Inserts the field right after `type:` when the frontmatter has that
    key, else as the first field. Never reorders or rewrites any other
    line, never touches the body.
  - Refuses to change an existing value. A --map id that differs from the
    value on disk is a conflict: reported, nothing written.
  - Templates (`Agent NN`, `_template*`) carry the literal nil UUID
    00000000-0000-0000-0000-000000000000 with a comment; a real contract
    on the nil value is malformed.
  - Any error means no file is written at all.

Exit 0 = done (or --check passed). Exit 1 = FAIL lines on stderr.
"""
import argparse
import importlib.util
import json
import re
import sys
import uuid
from collections import defaultdict
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

HERE = Path(__file__).resolve().parent
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


# --root defaults to None: the resolver finds the team root (GL-1013 site table).
DEFAULT_ROOT = None
AGENTS_REL = Path("06 AI Team/Agents")
FIELD = "myicor_id"
NIL = "00000000-0000-0000-0000-000000000000"
PLACEHOLDER_LINE = (
    f"{FIELD}: {NIL}  "
    "# placeholder: the hiring SOP mints the real id at hire time"
)
UUID4_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
FIELD_RE = re.compile(r"^" + FIELD + r":(.*)$")


def is_template(name):
    return bool(re.fullmatch(r"Agent \d+", name)) or name.lower().startswith("_template")


def frontmatter(text):
    r"""(lines, fence, opening): the frontmatter lines with their own line
    endings stripped off, the offset where the closing `---` itself starts,
    and the opening fence exactly as the file writes it. None when absent.

    Both fences are read in either line ending. A contract synced from
    Windows is CRLF, and "---\n" alone does not find its fences at all, so
    the whole file read as "no frontmatter" and the id could not be minted.
    The caller rebuilds with the file's own eol, so nothing else in the
    block is rewritten (Ian Slattery, T15-A).
    """
    opening = next((f for f in ("---\n", "---\r\n") if text.startswith(f)), None)
    if opening is None:
        return None
    close = noteio.FM_CLOSE.search(text, len(opening) - 1)
    if close is not None:
        raw, fence = text[len(opening):close.start()], close.start() + 1
    else:
        tail = next((t for t in ("\r\n---", "\n---") if text.endswith(t)), None)
        if tail is None:
            return None
        raw, fence = text[len(opening):len(text) - len(tail)], len(text) - 3
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in raw.split("\n")]
    return lines, fence, opening


def read_value(lines):
    """(index, value) of the field line, value stripped of quotes and a
    trailing comment; (None, None) when the field is absent."""
    for i, line in enumerate(lines):
        m = FIELD_RE.match(line)
        if m:
            raw = m.group(1).strip()
            # maxsplit= by name: the positional third argument to
            # re.split is deprecated since 3.13 and prints a
            # DeprecationWarning straight into the member's terminal
            # (Andrew Gillley, T13-5).
            raw = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
            if raw.startswith("#"):
                raw = ""
            return i, raw.strip("'\"")
    return None, None


def insert_index(lines):
    for i, line in enumerate(lines):
        if line.startswith("type:"):
            return i + 1
    return 0


def load_map(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        sys.exit(f"FAIL --map {path}: not readable JSON ({e})")
    if not isinstance(data, dict):
        sys.exit(f"FAIL --map {path}: must be a JSON object of name to id")
    bad = [k for k, v in data.items() if not isinstance(v, str) or not UUID4_RE.fullmatch(v)]
    if bad:
        sys.exit(f"FAIL --map {path}: not a lowercase UUID v4 for {', '.join(sorted(bad))}")
    dupes = [v for v in set(data.values()) if list(data.values()).count(v) > 1]
    if dupes:
        sys.exit(f"FAIL --map {path}: one id given to more than one agent ({', '.join(sorted(dupes))})")
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=DEFAULT_ROOT, help="vault root (default: this script's vault)")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--export", action="store_true", help="print {name: id} JSON, write nothing")
    ap.add_argument("--map", help="{name: id} JSON of ids to reuse for named agents")
    a = ap.parse_args()

    root = _team_root(a.root)
    agents = root / AGENTS_REL
    mapping = load_map(a.map) if a.map else {}
    readonly = a.check or a.export

    rows = []      # (name, id, action)
    errors = []    # FAIL messages
    writes = []    # (path, new_text)
    seen = defaultdict(list)

    if not agents.is_dir():
        errors.append(f"{AGENTS_REL} is not a folder under {root}")

    for d in sorted(agents.iterdir()) if agents.is_dir() else []:
        if not d.is_dir() or d.name.startswith("."):
            continue
        f = d / "AGENT.md"
        if not f.is_file():
            continue  # validate-team reports a folder without AGENT.md
        name = d.name
        tmpl = is_template(name)
        text, eol = noteio.read_note(f)
        fm = frontmatter(text)
        if fm is None:
            errors.append(f"{name}: AGENT.md has no frontmatter, so it cannot carry {FIELD}")
            rows.append((name, "-", "no-frontmatter"))
            continue
        lines, fence, opening = fm
        idx, val = read_value(lines)

        if idx is not None:
            if tmpl:
                if val == NIL:
                    rows.append((name, val, "template"))
                else:
                    errors.append(f"{name}: a template must carry the nil placeholder {NIL}, not '{val}'")
                    rows.append((name, val, "template-not-placeholder"))
            elif val == NIL:
                errors.append(f"{name}: still on the template placeholder; the hiring SOP mints a real {FIELD}")
                rows.append((name, val, "placeholder-on-real-agent"))
            elif not UUID4_RE.fullmatch(val):
                errors.append(f"{name}: {FIELD} '{val}' is not a lowercase UUID v4")
                rows.append((name, val, "malformed"))
            elif name in mapping and mapping[name] != val:
                errors.append(f"{name}: {FIELD} on disk is {val}, --map says {mapping[name]}; an id is never changed")
                rows.append((name, val, "conflict"))
            else:
                rows.append((name, val, "kept"))
                seen[val].append(name)
            continue

        # the field is missing
        if readonly:
            errors.append(f"{name}: AGENT.md lacks {FIELD} (GL-1002, Agents: the stable identity)")
            rows.append((name, "-", "missing"))
            continue
        if tmpl:
            new_line, new_id, action = PLACEHOLDER_LINE, NIL, "placeholder"
        elif name in mapping:
            new_id, action = mapping[name], "mapped"
            new_line = f"{FIELD}: {new_id}"
        else:
            new_id, action = str(uuid.uuid4()), "minted"
            new_line = f"{FIELD}: {new_id}"
        lines.insert(insert_index(lines), new_line)
        writes.append((f, opening + "".join(ln + eol for ln in lines)
                       + text[fence:]))
        rows.append((name, new_id, action))
        if not tmpl:
            seen[new_id].append(name)

    for the_id, names in sorted(seen.items()):
        if len(names) > 1:
            errors.append(f"{FIELD} {the_id} is carried by more than one agent: {', '.join(names)}")

    if a.export:
        if errors:
            for e in errors:
                print("FAIL " + e, file=sys.stderr)
            sys.exit(1)
        out = {name: the_id for name, the_id, action in rows if action == "kept"}
        print(json.dumps(out, indent=2, sort_keys=True))
        return

    w_name = max([len("agent")] + [len(r[0]) for r in rows])
    w_id = max([len("myicor_id")] + [len(r[1]) for r in rows])
    print(f"{'agent':<{w_name}}  {'myicor_id':<{w_id}}  action")
    for name, the_id, action in rows:
        print(f"{name:<{w_name}}  {the_id:<{w_id}}  {action}")

    if errors:
        for e in errors:
            print("FAIL " + e, file=sys.stderr)
        sys.exit(1)

    if not readonly:
        for f, new_text in writes:
            noteio.write_note(f, new_text)
    counts = defaultdict(int)
    for _, _, action in rows:
        counts[action] += 1
    summary = ", ".join(f"{n} {k}" for k, n in sorted(counts.items()))
    print(f"OK {len(rows)} agent contracts under {agents}: {summary}")


if __name__ == "__main__":
    main()
