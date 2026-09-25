#!/usr/bin/env python3
"""skill-doctor.py - check every SKILL.md against the skill contract.

Mack, 2026-09-14. Row 10 of the 2026-09-14 skills and hooks audit, wave 2
(the 2026-09-14 scaffold skills and hooks audit report, Nolan's hire
output contract section 4b). Same bytes in the private vault and in the
public ICOR for Life Scaffold: the folder is detected at runtime, so one
file serves both.

WHAT A SKILL IS
---------------
A door, not a body. The SOP or Workstream it points at is the procedure;
`SKILL.md` carries a name, a description with the trigger phrases, and one
line naming the file to read. Everything else is a second copy of a
procedure, and a second copy is a second thing to keep true
(`06 AI Team/AI Team Knowledge/Skills/README.md`).

WHAT THIS CHECKS (one OK or FAIL line each)
-------------------------------------------
  1  name    the frontmatter `name` equals the folder name, and matches the
             agentskills.io shape: lowercase letters, digits and hyphens,
             1 to 64 characters, no leading, trailing or doubled hyphen.
  2  desc    `description` is present, under 1024 characters, and carries at
             least one trigger phrase (a quoted phrase, or a "use when /
             before / after ..." clause). A description with no trigger is a
             skill a host never picks.
  3  body    the body is under 25 lines and names EXACTLY ONE SOP or
             Workstream path, and that path resolves on disk. Zero pointers
             is a door into nothing; two is a skill that is really two.
  4  header  a skill in the canonical Skills home carries the generated
             header naming its generator and source. A skill in a host
             adapter folder may be hand written and carries none.
  5  host    host-only frontmatter keys (allowed-tools, shell,
             user-invocable, model, argument-hint) appear only inside a host
             adapter folder (`.claude/`, `.codex/`, `.agents/`). In the
             canonical home they are portability debt. One exception,
             decision v8d and Pax 7a (2026-09-24): `disable-model-invocation`
             may sit in the canonical file, because Codex and Gemini ignore
             an unknown key without error and Cursor honours this one.
  6  dashes  no em dash and no en dash anywhere in the file (GL-043).
  7  clash   the skill name does not collide with a `.claude/commands/*.md`
             command that still exists. Two doors, one name, is a coin flip.
  9  same    a `.claude/skills/<name>` adapter whose twin sits in the
             canonical home carries the SAME body, byte for byte, once the
             frontmatter, the generated header line and the one injected
             `!` prerun line (with the blank line before it) are set aside
             (step 7b, decision v8d). The canonical body itself carries no
             `!` line: that syntax executes on Claude Code only. A hand
             edited adapter body is a fork of the one body, and a fork is
             a second thing to keep true. An adapter with no canonical twin
             is hand written and has nothing to be identical to.
  8  budget  (--all only) the descriptions of every skill together stay under
             MAX_SKILL_TOKENS. Every description is loaded into every
             session, so this is the one number that grows without anyone
             deciding to spend it.

WHAT THIS DOES NOT PROVE
------------------------
1. It does not prove the skill works. It reads files. Whether the host
   picks the skill on the phrases in its description is a property of the
   host, not of this check.
2. It does not prove the SOP behind the pointer is correct, only that the
   path resolves.
3. It does not read `.claude/settings.json`. A skill can be perfect here and
   never be offered by the host.

    skill-doctor.py "06 AI Team/AI Team Knowledge/Skills/<name>"
    skill-doctor.py --all [--json] [--root DIR]

Exit 0 = every checked skill passed. Exit 1 = at least one FAIL line.
"""
import argparse
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

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

CANONICAL_REL = "06 AI Team/AI Team Knowledge/Skills"
HOST_DIRS = (".claude", ".codex", ".agents", ".gemini", ".cursor")
HOST_ONLY_KEYS = ("allowed-tools", "shell", "user-invocable",
                  "disable-model-invocation", "model", "argument-hint")
# Keys a host adapter owns but the canonical file may ALSO carry (v8d, 7a).
CANONICAL_ALLOWED_KEYS = ("disable-model-invocation",)
CLAUDE_SKILLS_REL = ".claude/skills"
GENERATED_MARK = "<!-- GENERATED by"
INJECT_RE = re.compile(r"^!`[^`\n]+`$")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC_CHARS = 1024
MAX_BODY_LINES = 25
MAX_SKILL_TOKENS = 4000
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
# A pointer is a vault-relative path to a real SOP or Workstream file.
POINTER_RE = re.compile(r"[\w /()-]*?(?:SOPs|Workstreams)/(?:SOP|WS)-\d+[\w.-]*\.md")
TRIGGER_RE = re.compile(r"\buse\s+(?:when|before|after|for|if|whenever)\b|"
                        r"triggers?\s*:|\bthe user (?:says|asks|types)\b", re.I)
QUOTED_RE = re.compile(r"[\"“][^\"“”]{3,}[\"”]|'[^']{3,}'")


def est_tokens(text):
    """Deterministic stand-in for a tokenizer: four characters per token,
    rounded up. It is never exact and it never has to be; the budget is
    about growth, and this number grows with the text the same way."""
    return int(math.ceil(len(text) / 4.0))


def split_frontmatter(text):
    """Return (frontmatter_text, body_text). No frontmatter gives ('', text)."""
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def parse_keys(fm_text):
    """Top-level `key: value` pairs from a small YAML subset. Values are kept
    as written, minus one layer of matching quotes. Continuation lines fold
    into the value above them, which is how a long description wraps."""
    out = {}
    key = None
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key is not None and raw.startswith((" ", "\t")):
            out[key] = (out[key] + " " + raw.strip()).strip()
    for k, v in list(out.items()):
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            out[k] = v[1:-1]
    return out


def is_host_skill(path, root):
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return rel.parts[0] in HOST_DIRS


def commands_in(root):
    d = root / ".claude" / "commands"
    if not d.is_dir():
        return set()
    return {p.stem for p in d.glob("*.md")}


def find_skills(root):
    """Every SKILL.md under the canonical home and under each host folder.
    `_template.md` is the body shape the generator fills, not a skill."""
    found = []
    canonical = root / CANONICAL_REL
    if canonical.is_dir():
        for p in sorted(canonical.rglob("SKILL.md")):
            found.append(p.parent)
    for host in HOST_DIRS:
        d = root / host / "skills"
        if d.is_dir():
            for p in sorted(d.rglob("SKILL.md")):
                found.append(p.parent)
    return found


def check_skill(skill_dir, root, commands):
    """Return (list of (status, check, message), description_text)."""
    res = []
    skill_dir = Path(skill_dir)
    name_on_disk = skill_dir.name
    f = skill_dir / "SKILL.md"
    if not f.is_file():
        res.append(("FAIL", "file", "%s has no SKILL.md in it" % name_on_disk))
        return res, ""
    text = f.read_text(encoding="utf-8", errors="replace")
    fm_text, body = split_frontmatter(text)
    keys = parse_keys(fm_text)

    # 1. name
    declared = keys.get("name", "")
    if not fm_text.strip():
        res.append(("FAIL", "name", "%s has no frontmatter, so it declares no name" % name_on_disk))
    elif not declared:
        res.append(("FAIL", "name", "%s has no `name` in its frontmatter" % name_on_disk))
    elif declared != name_on_disk:
        res.append(("FAIL", "name", "%s declares name `%s`; the name must equal the folder"
                    % (name_on_disk, declared)))
    elif len(declared) > MAX_NAME:
        res.append(("FAIL", "name", "%s is %d characters; the limit is %d"
                    % (declared, len(declared), MAX_NAME)))
    elif not NAME_RE.match(declared):
        res.append(("FAIL", "name", "%s is not a legal skill name: lowercase letters, digits "
                    "and single hyphens only, no leading or trailing hyphen" % declared))
    else:
        res.append(("OK", "name", "%s" % declared))

    # 2. description
    desc = keys.get("description", "")
    if not desc:
        res.append(("FAIL", "desc", "%s has no `description`, so no host can decide to pick it"
                    % name_on_disk))
    elif len(desc) > MAX_DESC_CHARS:
        res.append(("FAIL", "desc", "%s description is %d characters; the limit is %d"
                    % (name_on_disk, len(desc), MAX_DESC_CHARS)))
    elif not (TRIGGER_RE.search(desc) or QUOTED_RE.search(desc)):
        res.append(("FAIL", "desc", "%s description carries no trigger phrase; say when to use "
                    "it, in the words the user says" % name_on_disk))
    else:
        res.append(("OK", "desc", "%d characters, trigger phrase present" % len(desc)))

    # 3. body: line cap, exactly one pointer, and it resolves
    body_lines = [ln for ln in body.splitlines() if ln.strip()
                  and not ln.strip().startswith("<!--")]
    pointers = []
    for m in POINTER_RE.finditer(body):
        hit = m.group(0).strip().lstrip("`'\" ")
        if hit not in pointers:
            pointers.append(hit)
    if len(body_lines) > MAX_BODY_LINES:
        res.append(("FAIL", "body", "%s body is %d lines; the cap is %d. A skill is a door, the "
                    "SOP is the body" % (name_on_disk, len(body_lines), MAX_BODY_LINES)))
    elif not pointers:
        res.append(("FAIL", "body", "%s names no SOP or Workstream path, so it is a door into "
                    "nothing" % name_on_disk))
    elif len(pointers) > 1:
        res.append(("FAIL", "body", "%s names %d procedures (%s); one skill is one door"
                    % (name_on_disk, len(pointers), ", ".join(pointers))))
    else:
        target = root / pointers[0]
        if not target.is_file():
            res.append(("FAIL", "body", "%s points at `%s`, which is not on disk"
                        % (name_on_disk, pointers[0])))
        else:
            res.append(("OK", "body", "%d lines, one pointer: %s" % (len(body_lines), pointers[0])))

    # 4. generated header, canonical home only
    host_skill = is_host_skill(skill_dir, root)
    has_header = "GENERATED by" in text
    if host_skill:
        res.append(("OK", "header", "host adapter skill; a hand written one needs no header"))
    elif has_header:
        res.append(("OK", "header", "generated header present"))
    else:
        res.append(("FAIL", "header", "%s sits in the canonical Skills home with no generated "
                    "header, so it was written by hand; change the source procedure and re-run "
                    "the generator" % name_on_disk))

    # 5. host-only frontmatter outside a host folder
    offenders = [k for k in HOST_ONLY_KEYS if k in keys
                 and k not in CANONICAL_ALLOWED_KEYS]
    if offenders and not host_skill:
        res.append(("FAIL", "host", "%s carries host-only frontmatter (%s) in the canonical home; "
                    "those keys belong in a host adapter folder"
                    % (name_on_disk, ", ".join(offenders))))
    else:
        res.append(("OK", "host", "no host-only frontmatter out of place"))

    # 6. dashes
    bad = []
    if EM_DASH in text:
        bad.append("em dash")
    if EN_DASH in text:
        bad.append("en dash")
    if bad:
        res.append(("FAIL", "dashes", "%s carries %s; GL-043 bans both in drafted prose"
                    % (name_on_disk, " and ".join(bad))))
    else:
        res.append(("OK", "dashes", "no em or en dash"))

    # 7. command clash
    if name_on_disk in commands:
        res.append(("FAIL", "clash", "%s collides with the command `.claude/commands/%s.md`; "
                    "retire one of the two doors" % (name_on_disk, name_on_disk)))
    else:
        res.append(("OK", "clash", "no clash with a remaining command"))

    # 9. the adapter body is the canonical body
    res.append(same_body(skill_dir, root, text))

    return res, desc


def shared_body(text, adapter):
    """The body a host adapter and the canonical file must share.

    Frontmatter and the generated header line are set aside on both sides
    (the header carries a content hash, which differs by construction). On
    the adapter side, each `!` line is set aside with the one blank line
    directly above it: that pair is the injected prerun, and nothing else is.
    Returns (body, list of problems found while stripping).
    """
    _, body = split_frontmatter(text)
    lines = [ln for ln in body.split("\n") if not ln.startswith(GENERATED_MARK)]
    problems = []
    out = []
    injected = 0
    for ln in lines:
        if INJECT_RE.match(ln):
            if not adapter:
                problems.append("the canonical body carries a `!` line (%s), which "
                                "executes on Claude Code only; the canonical body is "
                                "read by every host" % ln[:80])
                out.append(ln)
                continue
            injected += 1
            if out and out[-1] == "":
                out.pop()
            continue
        out.append(ln)
    if injected > 1:
        problems.append("the adapter injects %d `!` lines; one prerun is one line"
                        % injected)
    return "\n".join(out), problems


def same_body(skill_dir, root, text):
    """Check 9. One (status, check, message) triple."""
    try:
        rel = Path(skill_dir).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = ""
    name = Path(skill_dir).name
    canonical = root / CANONICAL_REL / name / "SKILL.md"
    if rel.startswith(CANONICAL_REL + "/"):
        _, probs = shared_body(text, adapter=False)
        if probs:
            return ("FAIL", "same", "%s: %s" % (name, "; ".join(probs)))
        return ("OK", "same", "canonical body carries no host-only execution line")
    if not rel.startswith(CLAUDE_SKILLS_REL + "/"):
        return ("OK", "same", "not a Claude adapter; nothing to compare")
    if not canonical.is_file():
        return ("OK", "same", "no canonical twin, so a hand written adapter with "
                "nothing to be identical to")
    ctext = canonical.read_text(encoding="utf-8", errors="replace")
    cbody, cprobs = shared_body(ctext, adapter=False)
    abody, aprobs = shared_body(text, adapter=True)
    probs = cprobs + aprobs
    if probs:
        return ("FAIL", "same", "%s: %s" % (name, "; ".join(probs)))
    if abody != cbody:
        a, c = abody.split("\n"), cbody.split("\n")
        i = 0
        while i < min(len(a), len(c)) and a[i] == c[i]:
            i += 1
        al = a[i] if i < len(a) else "<end>"
        cl = c[i] if i < len(c) else "<end>"
        col = 0
        while col < min(len(al), len(cl)) and al[col] == cl[col]:
            col += 1
        lo = max(0, col - 20)
        return ("FAIL", "same", "%s: the Claude adapter body differs from the canonical "
                "body at body line %d, column %d (adapter %r, canonical %r). The adapter "
                "may add frontmatter and one injected `!` line, nothing else; change the "
                "source procedure and re-run scaffold-init.py apply"
                % (name, i + 1, col + 1, al[lo:lo + 50], cl[lo:lo + 50]))
    return ("OK", "same", "adapter body is byte-identical to `%s/%s/SKILL.md`"
            % (CANONICAL_REL, name))


def main():
    ap = argparse.ArgumentParser(description="Check SKILL.md files against the skill contract.")
    ap.add_argument("skill", nargs="?", help="path to one skill folder (the one holding SKILL.md)")
    ap.add_argument("--all", action="store_true", help="check every skill in this folder")
    ap.add_argument("--json", action="store_true", help="machine readable report on stdout")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="vault root (default: this script's vault)")
    args = ap.parse_args()

    root = _team_root(args.root)
    if not args.all and not args.skill:
        print("FAIL skill-doctor: name a skill folder, or pass --all", file=sys.stderr)
        return 1

    commands = commands_in(root)
    targets = find_skills(root) if args.all else [Path(args.skill)]
    if args.all and not targets:
        line = "OK skill-doctor: no skills on disk yet, so nothing to check"
        print(json.dumps({"root": str(root), "skills": [], "fails": 0, "note": line})
              if args.json else line)
        return 0

    report = []
    fails = 0
    total_desc_tokens = 0
    for t in targets:
        if not t.is_dir():
            print("FAIL skill-doctor: %s is not a folder" % t, file=sys.stderr)
            fails += 1
            continue
        res, desc = check_skill(t, root, commands)
        total_desc_tokens += est_tokens(desc)
        entry = {"skill": t.name, "path": str(t), "checks": []}
        for status, check, msg in res:
            entry["checks"].append({"status": status, "check": check, "message": msg})
            if status == "FAIL":
                fails += 1
                if not args.json:
                    print("FAIL %s/%s: %s" % (t.name, check, msg), file=sys.stderr)
            elif not args.json:
                print("OK   %s/%s: %s" % (t.name, check, msg))
        report.append(entry)

    budget = {"checked": None}
    if args.all:
        budget = {"checked": True, "tokens": total_desc_tokens, "max": MAX_SKILL_TOKENS}
        if total_desc_tokens > MAX_SKILL_TOKENS:
            fails += 1
            msg = ("the descriptions of %d skills come to about %d tokens, over the %d budget. "
                   "Every description is loaded into every session: shorten them or retire a skill"
                   % (len(report), total_desc_tokens, MAX_SKILL_TOKENS))
            if args.json:
                budget["message"] = msg
            else:
                print("FAIL budget: %s" % msg, file=sys.stderr)
        elif not args.json:
            print("OK   budget: about %d of %d description tokens used by %d skills"
                  % (total_desc_tokens, MAX_SKILL_TOKENS, len(report)))

    if args.json:
        print(json.dumps({"root": str(root), "skills": report, "budget": budget,
                          "fails": fails}, indent=2))
    elif fails:
        print("\n%d check(s) failed across %d skill(s)" % (fails, len(report)), file=sys.stderr)
    else:
        print("\nOK %d skill(s) passed every check" % len(report))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
