#!/usr/bin/env python3
"""write-guard.py: refuse the two writes the Scaffold promises hardest.

A PreToolUse guard for the file-writing tools and, since the 2026-09-14
evening Vex ruling, for the shell tool. It reads the host's hook
payload as JSON on stdin and answers with an exit code:

  exit 0  nothing to say, the write proceeds
  exit 2  BLOCKED, with a plain-words reason on stderr

Two rules, and only two:

  1. PROTECTED PATHS. The user's raw daily notes under
     `00 Daily Scratchpad/`, and the entry contracts a session is built
     on: root `AGENTS.md`, root `CLAUDE.md` when the member created one
     (myPKA ships none), and every specialist contract
     `06 AI Team/Agents/<Name>/AGENT.md`, plus that contract's
     `.hiring` marker (only new-agent.py writes it, only check-hire.py
     clears it; a planted one would open the contract for a day) and the
     guard layer's own wiring. AGENTS.md hard rules 1
     and 3 say an agent expands AROUND the user's words and never inside
     them; nothing enforced that until today. Since the step 5 review
     (2026-09-24) these are judged under the myPKA root that resolve.py's
     marker logic finds, and under each content source's scratchpad, not
     only under CLAUDE_PROJECT_DIR (see WHICH ROOTS below).
  2. SECRET-SHAPED VALUES. A credential VALUE (never a variable name) in
     the content being written. AGENTS.md hard rule 10: secrets live only
     in `.env`. The value shapes are the ones the private vault's
     `outbound-write-guard.py` proved in service since 2026-08-06.

THE UNLOCK, AND WHY THERE IS ONE
--------------------------------
Hooks configured for a session also run inside dispatched specialists, so
a blanket deny on `AGENT.md` would stop Nolan halfway through a hire, with
no way through. Every deny here is therefore lifted by one environment
variable, set for the one command that needs it:

    ICOR_UNLOCK_WRITES=1

That is not a back door left open by accident, it is the documented door.
A guard with no unlock is a guard that gets deleted the first time it
blocks real work, and then it protects nothing. The unlock has its own red
test, so it is proven to work rather than assumed to.

The sanctioned edits to a scratchpad do not need the unlock at all: a
processed stamp goes through `stamp-processed.py`, which names the
scratchpad as a script ARGUMENT and not as a write shape, so the shell
reader lets it through (red-tested). On Bash the unlock is per call: an
`ICOR_UNLOCK_WRITES=1` prefix on the one command, logged to stderr.

WHAT THIS DOES NOT PROVE - read this before trusting it
-------------------------------------------------------
- **That a protected file cannot be changed.** This guard sees the
  file-writing tools, apply_patch, and the Bash write SHAPES the shell
  reader lists (redirects, tee, touch, rm, sed -i, mv/cp into). A Python
  script that writes, a path built from a variable it cannot resolve, an
  editor outside the session, and any host without hooks reach every one
  of these paths untouched. It raises the cost of an accident; it is not a
  permission system, and no document may call it one.
- **That no secret reaches disk.** It matches high-confidence value
  shapes. A key with no recognisable shape, a secret split across two
  writes, a secret written by a script, or one already in the file being
  edited all pass. A clean run means "these shapes were not in this
  payload", never "this write is safe".
- **That the unlock was deserved.** `ICOR_UNLOCK_WRITES=1` is a statement
  by whoever set it. The guard checks that it is set, not that it is true.
- **That it ran at all.** A host that does not implement hooks, or a
  missing python3, ends with the write allowed and nothing said. Absence
  of a block is not evidence of a check.

FAILS CLOSED ON ITS OWN ERRORS (Vex ruling, 2026-09-14)
------------------------------------------------------
An exception inside this file exits 2 with the error named on stderr, and
the write does not happen. It failed open until the 2026-09-14 security
gate, on the reasoning that a missed review is only an edit to a versioned
file. That covers rule 1 and not rule 2: a secret that reaches a note
reaches every sync and every backup, and a green that can be produced by
feeding the guard malformed input is a green reachable without the thing
being true (GL-1005 rule 4). Recovery when it wedges takes ten seconds and
is printed with the block: fix the guard, set ICOR_UNLOCK_WRITES=1 for the
one write, or remove its entry from .claude/settings.json.

The wall-clock budget is the one exception and stays open on purpose: a
run that outlasts BUDGET_S prints one line and exits 0, because the host's
own hook timeout cancels a slow hook and lets the call proceed anyway, and
a script cannot close a door the host holds open. The budget pattern is
the private vault's `decision-must-land.js` (SCAN_BUDGET_MS), tightened to
2 seconds because this runs on every single write.
"""
# THE FIRST STATEMENTS IN THIS FILE, AND THEY HAVE TO BE (Vex ruling, W7,
# 2026-09-16). A guard is launched from Scripts/, so Python puts Scripts/ at
# the FRONT of sys.path and a `Scripts/json.py` would then be what `import
# json` finds, inside the guard, before it has read a byte. The rendered hook
# passes `-I`, which drops that entry; this stanza is the belt to that brace,
# for a guard launched some other way (by hand, by a member's own wrapper, by
# a host whose hook config is older than this file). It has to run BEFORE the
# first stdlib import or it is defending a door already walked through.
#
# `dont_write_bytecode` is here for the same reason it is in every other
# script in this folder: a guard that drops __pycache__ into the tree it is
# guarding changes what it measures (Conrad Froehling, 2026-09-16).
import sys, os                                                   # noqa: E401
sys.dont_write_bytecode = True
# realpath on BOTH sides, because they are not spelled the same. Python 3.11
# and newer resolve sys.path[0] (`/private/tmp/x` on macOS) while __file__ is
# the path as typed (`/tmp/x`), and comparing the two with abspath alone
# silently never matched: the entry stayed, and this stanza defended nothing.
if sys.path:
    _first = os.path.realpath(sys.path[0] or os.getcwd())
    if _first == os.path.dirname(os.path.realpath(__file__)):
        del sys.path[0]

import calendar
import json
import re
import time

BUDGET_S = 2.0            # wall clock; exceeding it is neither pass nor block
MAX_SCAN_CHARS = 1_000_000  # a payload larger than this is scanned in part only
UNLOCK_ENV = "ICOR_UNLOCK_WRITES"
START = time.monotonic()


def over_budget():
    return time.monotonic() - START > BUDGET_S


# --- rule 1: the protected paths -------------------------------------------
# Vault-relative, POSIX separators. Checked by shape, never by a scan of the
# tree, so a path that does not exist yet is judged the same as one that does.
PROTECTED = (
    ("00 Daily Scratchpad/",
     "the user's raw daily notes are never edited by an agent "
     "(AGENTS.md hard rules 1 and 3). Extract from it, stamp it with "
     "stamp-processed.py, and leave the words alone"),
)
PROTECTED_EXACT = {
    "AGENTS.md": "the root operating contract is the user's to edit",
}
# CLAUDE.md is protected IF PRESENT (Tom, 2026-09-24). myPKA ships no
# CLAUDE.md, AGENTS.md is the one entry file. A member who creates one owns
# it, and from then on it is guarded like AGENTS.md; a missing one is never
# an error and creating it is not blocked.
PROTECTED_IF_PRESENT = {
    "CLAUDE.md": "the host entry file is the user's to edit",
}
# IGNORECASE, and every exact name below is compared case-folded: the default
# macOS volume is case-insensitive, so a Write to `agents.md` IS a write to
# AGENTS.md, and until the step 5 review it passed (Vex, 2026-09-24, F4).
AGENT_CONTRACT = re.compile(r"^06 AI Team/Agents/([^/]+)/AGENT\.md$", re.IGNORECASE)
AGENT_MARKER = re.compile(r"^06 AI Team/Agents/([^/]+)/\.hiring$", re.IGNORECASE)

# --- the hiring marker: the unlock the hire path can actually use ----------
# ICOR_UNLOCK_WRITES cannot be set on a single tool call. It is an environment
# variable, and a model that reads "re-run the command with it set" does the
# only thing that sentence permits: it writes the contract from a shell, where
# a hook registered on the file tools never looks. Both CLIs did exactly that
# in pilot C. A guard whose documented remedy is a bypass has taught the model
# the bypass.
#
# So the hire path gets a marker instead of a variable. `new-agent.py` drops
# `06 AI Team/Agents/<Name>/.hiring` when it scaffolds the folder, this guard
# allows writes to THAT agent's contract while the marker is younger than 24
# hours, and `check-hire.py` deletes it on a green run. The env var stays as
# the second unlock, for an approved edit to an existing contract or to an
# entry file, which are the cases where a person decides and a shell is fine.
#
# WHAT THIS DOES NOT PROVE: that the hire deserved the write. The marker is a
# statement by the script that started the hire, exactly as the env var is a
# statement by whoever exported it. It narrows the open door from every
# protected path for a whole session to one contract for one day.
HIRING_MARKER = ".hiring"
HIRING_MAX_AGE_S = 24 * 60 * 60


def hiring_open(root, rel):
    """True while this agent's own .hiring marker exists and is fresh."""
    m = AGENT_CONTRACT.match(rel)
    if not m or not root:
        return False
    marker = os.path.join(root, os.path.dirname(rel), HIRING_MARKER)
    try:
        started = os.path.getmtime(marker)      # the fallback, read first
    except OSError:
        return False
    try:
        # The stamp the hire wrote, in UTC. calendar.timegm, never mktime:
        # mktime reads a struct_time as LOCAL time, so the same marker would
        # be worth a different number of hours depending on the machine.
        stamp = str((json.load(open(marker, encoding="utf-8")) or {})
                    .get("started") or "")
        started = calendar.timegm(time.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        pass                                    # keep the mtime
    return (time.time() - started) <= HIRING_MAX_AGE_S

# --- the guard layer's own wiring (Vex gate 2026-09-14, V-06) --------------
# Everything above is a document. These are the files that decide whether a
# write is reviewed at all, and until today each was an ordinary file here: one
# Write of {"env": {"ICOR_UNLOCK_WRITES": "1"}} into settings.local.json stands
# the layer down for every later session, and one Edit to a guard does the
# same. It remains a friction gate -- a shell reaches all of it with `sed -i`,
# and the unlock is one export away for a person. What it closes is the
# accident the guard exists for: meeting a block and "fixing" the block.
HOOKS_RULES_REL = "06 AI Team/AI Team Knowledge/Scripts/hooks-rules.json"
WIRING_EXACT = {
    ".claude/settings.json":
        "the hook wiring decides whether any write is reviewed; a block is not "
        "fixed by editing the thing that blocked it",
    ".claude/settings.local.json":
        "one `env` key here sets ICOR_UNLOCK_WRITES for every later session, "
        "which stands the whole guard layer down silently",
    HOOKS_RULES_REL:
        "the rule table is what the hook configs are generated from, so an edit "
        "here removes a guard from every host at once",
    # This guard finds the myPKA root through resolve.py (step 5), so an edit
    # to the resolver's marker logic changes what this guard protects.
    "06 AI Team/AI Team Knowledge/Scripts/resolve.py":
        "this guard finds the team root through the resolver, so an edit here "
        "changes which contract files are protected",
    # The binding decides which source the team may write and how: one Edit
    # from `write: ask` to `write: allow` stands down every review of every
    # write into the member's content (Vex step 5, F8, approved by Tom
    # 2026-09-24, f8s). The first sources.yaml on a device is written by the
    # one-call unlock GL-1013 section 3 documents.
    ".mypka/sources.yaml":
        "the source binding decides where the team writes and whether it asks "
        "first; flipping write: ask to allow is not fixed in passing",
    # The two examples are what the onboarding unlock COPIES to sources.yaml
    # (GL-1013 section 3). Unguarded, `write: allow` edited into an example
    # passes in silence and then rides the logged, legitimate unlock into the
    # binding (Vex step 5, residual 2). Guarding the two files is simpler than
    # a hash check in a copy that is one `cp`, and needs no new runtime.
    ".mypka/sources.mode-b.yaml.example":
        "onboarding copies this example to .mypka/sources.yaml with the "
        "one-call unlock, so an edit here is an edit to the next binding",
    ".mypka/sources.yaml.example":
        "onboarding copies this example to .mypka/sources.yaml with the "
        "one-call unlock, so an edit here is an edit to the next binding",
}
HOOK_DIR = ".claude/hooks/"
_REGISTERED = []


def registered_guards(rel_hint=""):
    """Guard paths from hooks-rules.json, read once, empty when unreadable.

    Empty is not a claim that no guard exists. `.claude/hooks/` is protected by
    shape either way, so this only adds guards that live elsewhere.
    """
    if _REGISTERED:
        return _REGISTERED[0]
    out = set()
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        doc = json.load(open(os.path.join(here, "hooks-rules.json"), encoding="utf-8"))
        for rule in doc.get("rules", []):
            g = (rule or {}).get("guard")
            if isinstance(g, str) and g:
                out.add(g)
    except Exception:
        out = set()
    _REGISTERED.append(out)
    return out


def _folded(table):
    return {k.casefold(): v for k, v in table.items()}


def protected_reason(rel, root=None):
    """Why `rel` (relative to `root`, POSIX) is protected, else None.

    Case-folded throughout (F4). `root` is needed only for the one rule that
    depends on the disk: CLAUDE.md is protected when it is present there."""
    f = rel.casefold()
    exact = _folded(PROTECTED_EXACT)
    if f in exact:
        return exact[f]
    if_present = _folded(PROTECTED_IF_PRESENT)
    if f in if_present and root and os.path.lexists(os.path.join(root, rel)):
        return if_present[f]
    wiring = _folded(WIRING_EXACT)
    if f in wiring:
        return wiring[f]
    if AGENT_CONTRACT.match(rel):
        return ("a specialist contract is written by the hiring procedure "
                "(SOP-1007), not edited in passing")
    if AGENT_MARKER.match(rel):
        return ("the hiring marker is written by new-agent.py and cleared by "
                "check-hire.py; planted by any other tool it would open that "
                "contract for a day")
    if f.startswith(HOOK_DIR.casefold()) and f != HOOK_DIR.casefold():
        return ("a hook script is the guard layer itself; edit it deliberately "
                "with the unlock set, never in passing")
    if f in {g.casefold() for g in registered_guards()}:
        return ("hooks-rules.json registers this file as a guard, so editing it "
                "changes what every host enforces")
    for prefix, why in PROTECTED:
        if f.startswith(prefix.casefold()):
            return why
    return None


# --- WHICH ROOTS (Vex step 5 verdict, GL-1013 section 6 and site (b)) ------
# Until 2026-09-24 every rule above was judged against ONE root:
# CLAUDE_PROJECT_DIR, else the payload cwd. In mode B (myPKA beside its
# content source) a session whose CLAUDE_PROJECT_DIR names the ICOR sibling
# saw P/mypka/AGENTS.md as "outside the root", returned None, and let the
# Write through (R28, watched red in both modes). And with the session in the
# team root, the scratchpad lives in the SIBLING, so it was never protected.
#
# So the guard now judges each target against every root it can name:
#   legacy      CLAUDE_PROJECT_DIR or the payload cwd, every rule (mode A is
#               unchanged by construction: all three roots are one folder)
#   team        each myPKA root that resolve.py's find_team_root marker logic
#               finds: CLAUDE_PROJECT_DIR only when it holds the marker, the
#               walk up from THIS file, the walk up from the payload cwd.
#               Every rule.
#   scratchpad  the scratchpad concept's resolved folder in each binding, so a
#               source's raw daily notes stay protected wherever they live.
#   source      each folder source root in each binding: no path rule, but a
#               shell write into it is in the secret-value rule's scope.
# A root counts under its spelled path AND its real path, so a symlinked alias
# of the team folder is the team folder (F5).
#
# WHAT THIS DOES NOT PROVE: that a team root nobody can walk to is protected.
# A session started in an unrelated folder, with this guard reached by an
# absolute hook path, still finds the team root by the walk from this file.
# A copy of the team somewhere else, never named by env, cwd or this file, is
# not a root this call knows about.
_RESOLVER = []


def _resolver():
    """resolve.py, loaded by path from beside this file (the way every team
    script loads it), or None when it is not there. An exception while
    loading it is this guard's own error and fails closed in __main__."""
    if _RESOLVER:
        return _RESOLVER[0]
    mod = None
    here = os.path.dirname(os.path.realpath(__file__))
    p = os.path.join(here, "resolve.py")
    if os.path.isfile(p):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mypka_resolve_guard", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    _RESOLVER.append(mod)
    return mod


def guarded_roots(payload, notices):
    """[(root, kind)] with kind legacy | team | scratchpad, de-duplicated."""
    out, seen = [], set()

    def add(root, kind):
        if not root:
            return
        key = (os.path.realpath(str(root)), kind)
        if key not in seen:
            seen.add(key)
            out.append((str(root), kind))

    add(payload_root(payload), "legacy")
    rs = _resolver()
    if rs is None:
        notices.append("write-guard: resolve.py is not beside this guard, so the "
                       "team's contract files are protected only under "
                       "CLAUDE_PROJECT_DIR or the session cwd, not under the myPKA "
                       "root. Restore resolve.py.\n")
        return out
    cwd = str(payload.get("cwd") or "")
    tries = [{"start": __file__}, {"start": __file__, "env": {}}]
    if cwd:
        tries.append({"start": cwd, "env": {}})
    teams = []
    for kw in tries:
        try:
            teams.append(rs.find_team_root(**kw))
        except rs.ResolveError:
            pass
    done = set()
    for r in teams:
        real = os.path.realpath(str(r.path))
        if real in done:
            continue
        done.add(real)
        add(r.path, "team")
        try:
            b = rs.load(r)
            sp = rs.resolve("scratchpad", bindings=b)
        except rs.ResolveError as e:
            # A broken sources.yaml must not wedge every write, and must not
            # pass in silence either: the team root is still guarded above.
            if e.code not in ("E_UNBOUND",):
                notices.append("write-guard: the binding under %s did not load "
                               "(%s); the team root is guarded, a content "
                               "source's scratchpad is not on this call.\n"
                               % (r.path, e.code))
            continue
        if sp.path is not None:
            add(sp.path, "scratchpad")
        # Each folder source root: no path rule of its own (its scratchpad is
        # above), but a shell write INTO it is a write into the member's vault,
        # so the secret-value rule reads it (rule 2 on the shell kind).
        for s in b.sources.values():
            if s.kind == "folder" and s.root is not None:
                add(s.root, "source")
    return out


def rels_under(ap, root):
    """`ap` relative to `root` (POSIX), once as spelled and once real. Empty
    when `ap` is outside `root` both ways."""
    out = []
    for a, b in ((os.path.abspath(ap), os.path.abspath(root)),
                 (os.path.realpath(ap), os.path.realpath(root))):
        try:
            rel = os.path.relpath(a, b)
        except ValueError:          # another drive on Windows
            continue
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            continue
        rel = rel.replace(os.sep, "/")
        if rel not in out:
            out.append(rel)
    # Vex step 13, F7: macOS and Windows folders are case-insensitive, so
    # P/MYPKA/AGENTS.md IS P/mypka/AGENTS.md there, and relpath (which
    # compares spelled names) called it outside the root. In mode B the team
    # root is reached by a path the session did not spell, so compare the
    # folded paths as well, and hand back the target's own trailing segments.
    if not out and sys.platform in ("darwin", "win32"):
        for a, b in ((os.path.abspath(ap), os.path.abspath(root)),
                     (os.path.realpath(ap), os.path.realpath(root))):
            fa, fb = _fold_path(a), _fold_path(b)
            try:
                rel = os.path.relpath(fa, fb)
            except ValueError:
                continue
            if rel == os.pardir or rel.startswith(os.pardir + os.sep) or rel == os.curdir:
                continue
            n = len(rel.split(os.sep))
            rel = "/".join(a.replace(os.sep, "/").split("/")[-n:])
            if rel not in out:
                out.append(rel)
    return out


def _fold_path(p):
    import unicodedata
    return unicodedata.normalize("NFC", p).casefold()


# --- rule 2: the secret value shapes ---------------------------------------
# Every pattern matches a VALUE, never a name. Naming a secret is normal
# practice and must not fire. Ported from the private vault's
# outbound-write-guard.py, which has carried them since 2026-08-06.
SECRET_PATTERNS = [
    ("a JSON web token", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    ("a Supabase secret key", r"\bsb_secret_[A-Za-z0-9_-]{16,}"),
    ("a Resend API key", r"\bre_[A-Za-z0-9]{4,32}_[A-Za-z0-9]{16,}"),
    # `(?!ant-)` so an Anthropic key is not reported as an OpenAI one: the
    # shapes overlap, and a block naming the wrong vendor sends whoever
    # reads it to rotate the wrong credential (pilot A finding F9).
    ("an OpenAI API key", r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{24,}"),
    ("an Anthropic API key", r"\bsk-ant-[A-Za-z0-9_-]{24,}"),
    ("a GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    ("a Slack token", r"\bxox[baprs]-[A-Za-z0-9-]{12,}"),
    ("a Stripe key", r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{20,}"),
    ("a Telegram bot token", r"\b\d{8,10}:[A-Za-z0-9_-]{33,}"),
    ("a Google refresh token", r"\b1//[A-Za-z0-9_-]{25,}"),
    ("a Postgres connection string carrying a password",
     r"\bpostgres(?:ql)?://[^\s:/@]+:[^\s@'\"]{6,}@"),
    ("a private key block",
     r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    # The long tail no list of vendors can enumerate.
    ("a key assigned to a NAME_KEY style variable",
     r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_"
     r"(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD|DSN|CREDENTIALS|APIKEY)"
     r"\s*[=:]\s*[\"']?([A-Za-z0-9_\-./+]{16,})"),
]

# A value carrying one of these is a worked example, not a credential. Without
# this list the guideline that documents a key shape could not be written.
PLACEHOLDERS = (
    "example", "placeholder", "redacted", "masked", "changeme", "change_me",
    "dummy", "your", "yourkey", "xxxx", "abcdef", "<", ">", "${", "$(",
    "insert_here", "todo", "notreal", "sample", "test_key",
)


def looks_placeholder(value):
    low = value.lower()
    return low.startswith("$") or any(t in low for t in PLACEHOLDERS)


def secret_reason(text):
    for label, pat in SECRET_PATTERNS:
        if over_budget():
            return None
        m = re.search(pat, text)
        if m and not looks_placeholder(m.group(1) if m.groups() else m.group(0)):
            return label
    return None


# --- payload reading --------------------------------------------------------
# WHERE A WRITE TARGET HIDES (pilot A finding F1, pilots B and C, 2026-09-14)
# ---------------------------------------------------------------------------
# This block is shared verbatim between the private vault's
# `.claude/hooks/write-guard.py` and the public Scaffold's
# `06 AI Team/AI Team Knowledge/Scripts/write-guard.py`. The two guards keep
# their own PROTECTED sets, because they guard different vaults, but they must
# not disagree about where a host puts the path it is about to write.
#
# Until 2026-09-14 both read `file_path` and `notebook_path` and nothing else,
# which is the Claude Code shape and only that. Codex's only file-writing tool
# is `apply_patch`, whose payload carries no path key: the paths are HEADERS
# INSIDE the patch body on `tool_input.command`. And every pilot watched the
# model write a protected contract from the shell (`cat > AGENT.md`), where a
# hook registered on the file tools never looks.
#
# So there are three readers here, chosen by the tool that made the call:
#   1. a path key         (Write, Edit, MultiEdit, NotebookEdit)
#   2. patch headers      (apply_patch: `*** Update File:`, `*** Add File:`,
#                          `*** Delete File:`, `*** Move to:`)
#   3. the shell reader   (Bash): the paths a command would WRITE, and only
#                          those. `grep x AGENTS.md` names a protected file
#                          and writes nothing; a guard that cannot tell those
#                          apart is a ban on naming the file at all.
#
# THE SHELL READER, and what it does and does not see (Vex ruling 2026-09-14
# evening, the Vex security gate of the 2026-09-14 skills and hooks audit,
# addendum). It is registered on the shell kind in hooks-rules.json since
# that ruling. Measured before the ruling on 11,619 real Bash calls from this
# vault's own transcripts: 0.04 s per call, 0 crashes, and 8 blocks of which
# 4 were real shell edits to CLAUDE.md, AGENTS.md and settings.json and 4 were
# false blocks from two defects this rewrite removes (a `cd` it ignored, and
# a `;` glued to a word that never split a segment).
#
#   SEES    `> path`, `>> path`, `&> path`, `>| path` (a redirect to a file;
#           `2>&1`, `>&2` and `/dev/null` are not files)
#           `tee path`, `touch path`, `truncate path`, `rm path`
#           `sed -i ... path`, `perl -i ... path`, `ruby -i ... path`
#           `mv|cp|install|rsync|ln ... path` (the LAST argument)
#           `cd path` and `pushd path` inside the same command, so a write
#           after `cd /somewhere/else && ...` is judged where it lands
#           `~`, `$HOME`, `$PWD` and `$CLAUDE_PROJECT_DIR` in a path
#   SKIPS   a path it cannot resolve: any other `$VAR`, a backtick, or a
#           relative path after a `cd` it could not read. Unknown is
#           unknown, never "still the vault" (the no-git-guard V-07 lesson):
#           an unresolvable path is allowed, not denied.
#           heredoc BODIES. `cat > x <<'EOF' ... EOF` is judged on its first
#           line; the body is data, and a markdown blockquote in it that
#           begins `> AGENTS.md` is prose, not a redirect.
#   AN INTERPRETER HANDED ITS PROGRAM INLINE is UNRESOLVABLE, not
#           non-writing: `python3 -`, `python3 -c`, `node -e`, `perl -e`,
#           `sh -c`, and any of them fed a heredoc. The call is ALLOWED, one
#           line on stderr says the rule was not applied to the program body,
#           and any protected path spelled out LITERALLY in that body is
#           still refused, because the path is right there in the bytes the
#           host sent. Silas's Codex re-run 2026-09-14/15, R1 HIGH: told to
#           delete a line from a protected note, two independent Codex runs
#           wrote `python3 - <<'PY' ... p.write_bytes(rest) ... PY` on the
#           first try and the guard returned 0 in silence. Measured on 11,623
#           real Bash calls from this vault: 2,511 now carry the notice (22%,
#           because editing through a python heredoc is the house style) and
#           31 are refused where 4 were before. Two narrowings were measured
#           into that number and both are stated at their code: the literal
#           sweep is armed only when the program text carries a write-shaped
#           construct, and a literal must carry a path separator. What is
#           left is a program that names a protected path with its folders
#           and then writes something. Narrowed again 2026-09-15 morning
#           (Vex): the sweep reads the PROGRAM text (the `-c` argument or
#           the heredoc body) from the cwd in force at that segment, and a
#           `>` is a write only when it redirects into a path. Same corpus:
#           the 31 refusals (18 true, 13 false) became 21 (18 true, 3 false),
#           the 13 false ones (a `cd` elsewhere, a read-only program beside
#           a shell redirect, a protected path in a `cat` heredoc's prose)
#           gone; closing the bare-name hole (see _BARE_PROTECTED) took them
#           to 42 (37 true, 5 false, every false one a writing program whose
#           prose names a protected file with its folders, and the block
#           names the prefix that clears it). A shell program (`bash -c`,
#           `sh <<'SH'`) is read by this reader exactly.
#   REFUSES TO GUESS. A command shlex cannot tokenise (an unbalanced quote)
#           is ALLOWED with one line on stderr saying the rule was not
#           applied. A guard that denies what it did not understand is a
#           guard that gets deleted, and this vault's own history has that
#           exact deletion in it.
#   NOT APPLIED on the shell kind: the secret-value rule. A secret typed into
#           a Bash command is already in the transcript when this guard
#           sees it, the network edge belongs to outbound-write-guard.py,
#           and the one sanctioned home for a secret (`.env`) is written from
#           a shell. Blocking that write would be a false block on the path
#           the rule exists to send people to.
#   THE PER-CALL UNLOCK. `ICOR_UNLOCK_WRITES=1 cat > AGENTS.md` unlocks THAT
#           command: an assignment prefix in the command text is the one
#           unlock a model can apply to a single call, it is visible in the
#           transcript, and this guard logs the stand-down to stderr. It is
#           a statement of intent by whoever typed it, exactly as the env
#           var is; the guard checks that it is there, not that it is true.
#           It covers the SEGMENT it prefixes and nothing else, which is
#           what the shell does with it (Vex step 5, residual 3). Until
#           2026-09-24 one prefix anywhere stood the guard down for the whole
#           command, so `ICOR_UNLOCK_WRITES=1 cp a b; echo x > AGENTS.md`
#           passed. Now the second segment is judged like any other. A
#           `bash -c` program under the prefix inherits it (the variable
#           reaches the child); `export ICOR_UNLOCK_WRITES=1` covers the
#           segments AFTER it in the same shell, never the ones before it,
#           and never out of a `( ... )` subshell.
#
# WHAT THE SHELL READER DOES NOT PROVE: that a protected file cannot be
# changed from a shell. A program that BUILDS its path (`open('AGENTS' + '.md')`,
# a name from a variable or a loop) is invisible to the literal sweep, a script
# on disk is never read at all, `dd of=`,
# `cp -r` of a whole folder, a path built from a variable set earlier in the
# same command, an editor, and any host without hooks all reach the bytes
# untouched. It raises the cost of the ACCIDENT the pilots watched; it is not
# a permission system, and no document may call it one.
import shlex

# Claude Code and Codex both report the shell tool as `Bash` (hooks-rules.json
# host_matchers, verified against both vendors' hook pages 2026-09-14).
SHELL_TOOLS = ("bash", "shell")

PATCH_FILE_HEADER = re.compile(
    r"(?m)^\*\*\*[ \t]+(?:Add|Update|Delete)[ \t]+File:[ \t]*(\S[^\n]*?)[ \t]*$")
PATCH_MOVE_HEADER = re.compile(
    r"(?m)^\*\*\*[ \t]+Move[ \t]+to:[ \t]*(\S[^\n]*?)[ \t]*$")

_SEPARATORS = {";", ";;", "&&", "||", "|", "|&", "&", "(", ")"}
_REDIRECTS = {">", ">>", ">|", "&>", "&>>", ">&"}
_LEADING_WORDS = {"do", "then", "else", "elif", "if", "while", "until", "time",
                  "sudo", "env", "nice", "nohup", "exec", "command", "builtin",
                  "{", "}", "!"}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# AN INTERPRETER HANDED ITS PROGRAM INLINE IS UNRESOLVABLE, NOT HARMLESS
# (Silas's Codex re-run 2026-09-14/15, R1 HIGH). Told to delete a line from a
# protected note, two independent Codex runs reached for the same shape with
# no prompting:
#
#     python3 - <<'PY'
#     p = Path('00 Daily Scratchpad/2026/09/2026-09-14.md'); p.write_bytes(rest)
#     PY
#
# The reader parsed that confidently as a command that writes nothing, exited
# 0, and printed NOTHING, so the note lost its frontmatter fence with the
# guard running. The limit itself is honest and declared; the silence was the
# defect. A confident wrong answer where an unsure one would have spoken is
# the worse failure mode, and it is the one a model walks into by default.
#
# So: allow (fail open, per the ruling), but say the rule was not applied, and
# if the program text names a protected path LITERALLY, refuse it, because the
# path is right there in the bytes the host sent.
_INTERPRETERS = {"python", "python2", "python3", "perl", "ruby", "node", "deno",
                 "php", "sh", "bash", "zsh", "osascript", "awk"}
_INLINE_FLAGS = {"-c", "-e", "-E", "--eval", "--exec"}
_HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# A heredoc line that hands its body to an interpreter: that body is the
# interpreter's PROGRAM, and the literal sweep reads the program, nothing else.
_HEREDOC_INTERP_RE = re.compile(
    r"(?:^|[\s;&|(])(?:python[23]?|perl|ruby|node|deno|php|sh|bash|zsh|osascript|awk)"
    r"\b[^;&|<]*<<")
# A shell handed a shell program is not unresolvable: this reader reads it.
_SHELLS = {"sh", "bash", "zsh"}
_NOT_A_FILE = ("/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty")
ALL_ARGS_CMDS = ("tee", "touch", "truncate", "rm")
INPLACE_CMDS = ("sed", "perl", "ruby")
DEST_LAST_CMDS = ("mv", "cp", "install", "rsync", "ln")
_UNLOCK_TOKEN = UNLOCK_ENV + "=1"


def _shell_lines(command, bodies=None):
    """One logical line per entry: continuations joined, heredoc bodies dropped.

    When `bodies` is a list, the body of every heredoc whose line hands it to
    an interpreter is appended to it, in command order: that body is the
    program, and the literal sweep reads the program and nothing else."""
    raw = command.replace("\r\n", "\n").split("\n")
    lines, i = [], 0
    while i < len(raw):
        line = raw[i]
        while line.endswith("\\") and i + 1 < len(raw):
            i += 1
            line = line[:-1] + raw[i]
        lines.append(line)
        i += 1
        m = _HEREDOC_RE.search(line)
        if m:
            term = m.group(2)
            start = i
            while i < len(raw) and raw[i].strip() != term:
                i += 1
            if bodies is not None and _HEREDOC_INTERP_RE.search(line):
                bodies.append("\n".join(raw[start:i]))
            i += 1
    return lines


def _tokens(text):
    """shlex with punctuation_chars, so `;`, `&&`, `|`, `>` and `(` are their
    own tokens whether or not a space surrounds them. Raises ValueError on an
    unbalanced quote, which the caller turns into an allow-with-notice."""
    s = shlex.shlex(text, posix=True, punctuation_chars=True)
    s.whitespace_split = True
    return list(s)


def command_paths(command, cwd):
    """(paths this command would WRITE outside an unlock, any_unlock, unresolvable).

    A path written by a segment the unlock covers (its own
    `ICOR_UNLOCK_WRITES=1` prefix, or an earlier `export` in the same shell)
    is left out of the first list: that segment is stood down and no other
    is. `any_unlock` is True when some segment was, so the caller can log it.
    Each unresolvable entry carries a fifth item, True when its segment was
    unlocked, so the literal sweep skips that program and no other.

    `unresolvable` is a list of (interpreter, how, cwd, program) for every
    segment that hands a program to an interpreter inline or on stdin: the cwd
    in force at that segment (None when a `cd` before it could not be read)
    and the program text when it is in the command (the `-c` argument or the
    heredoc body), else None. The reader cannot say what such a program
    writes, and saying nothing is the one answer it must not give. A shell
    handed a shell program is read by this same reader instead.

    Raises ValueError when the shell text cannot be tokenised."""
    root_env = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    home = os.path.expanduser("~")
    state = {"cwd": cwd or None, "unlocked": False, "unresolvable": [],
             "bodies": [], "exported": False}
    stack = []
    out = []

    def expand(p):
        p = re.sub(r"\$\{?CLAUDE_PROJECT_DIR\}?",
                   lambda m: root_env or m.group(0), p)
        p = re.sub(r"\$\{?PWD\}?",
                   lambda m: state["cwd"] or m.group(0), p)
        p = re.sub(r"\$\{?HOME\}?", lambda m: home, p)
        if p.startswith("~"):
            p = os.path.expanduser(p)
        if "$" in p or "`" in p:
            return None
        return p

    def resolve(p):
        if not p or p in _NOT_A_FILE:
            return None
        p = expand(p)
        if p is None:
            return None
        if not os.path.isabs(p):
            if not state["cwd"]:
                return None
            p = os.path.join(state["cwd"], p)
        return os.path.abspath(p)

    def flush(seg):
        if not seg:
            return
        k, seg_unlocked = 0, state["exported"]
        while k < len(seg) and (seg[k] in _LEADING_WORDS or _ASSIGN_RE.match(seg[k])):
            if seg[k] == _UNLOCK_TOKEN:
                seg_unlocked = True
            k += 1
        if seg_unlocked:
            state["unlocked"] = True
        # The unlock covers THIS segment only (residual 3): its paths go to a
        # list nobody judges, every other segment's paths are judged.
        dest = [] if seg_unlocked else out
        taken = set()
        for i, t in enumerate(seg):
            if t in _REDIRECTS and i + 1 < len(seg):
                nxt = seg[i + 1]
                taken.add(i + 1)
                if nxt.isdigit() or nxt == "-" or nxt.startswith("&"):
                    continue
                r = resolve(nxt)
                if r:
                    dest.append(r)
        body = [t for j, t in enumerate(seg) if j >= k and j not in taken
                and t not in _REDIRECTS]
        if not body:
            return
        head = os.path.basename(body[0])
        args = [t for t in body[1:] if t and not t.startswith("-")]
        if head in _INTERPRETERS:
            how, program = None, None
            for idx in range(1, len(body)):
                t = body[idx]
                if t in _INLINE_FLAGS:
                    how = "its `%s` argument" % t
                    program = body[idx + 1] if idx + 1 < len(body) else None
                    break
                if t == "-":
                    how = "standard input (`-`)"
                    break
                if t.startswith("<<"):
                    how = "a heredoc on standard input"
                    break
            if how is None and "<<" in body[1:]:
                how = "a heredoc on standard input"
            if how is not None:
                if program is None and "<<" in body[1:] and state["bodies"]:
                    program = state["bodies"].pop(0)
                sub = None
                if head in _SHELLS and program is not None:
                    # `bash -c '...'` and `sh <<'SH'`: a shell program, which
                    # this reader reads exactly, from the cwd in force here.
                    try:
                        sub = command_paths(program, state["cwd"])
                    except ValueError:
                        sub = None
                if sub is not None:
                    # Under the prefix the child shell inherits the variable,
                    # so everything it writes is covered; otherwise its own
                    # segments carry their own unlocks.
                    dest.extend(sub[0])
                    state["unlocked"] = state["unlocked"] or sub[1]
                    state["unresolvable"].extend(
                        u[:4] + (u[4] or seg_unlocked,) for u in sub[2])
                else:
                    state["unresolvable"].append((head, how, state["cwd"], program,
                                                  seg_unlocked))
        if head in ("cd", "pushd"):
            target = args[0] if args else "~"
            state["cwd"] = resolve(target) if target != "-" else None
            return
        if head == "export" and _UNLOCK_TOKEN in body[1:]:
            state["unlocked"] = True
            state["exported"] = True        # the segments after this one
            return
        wanted = []
        if head in ALL_ARGS_CMDS:
            wanted = args
        elif head in INPLACE_CMDS and any(
                t == "-i" or t.startswith("-i") for t in body[1:]):
            wanted = args
        elif head in DEST_LAST_CMDS and args:
            wanted = args[-1:]
        for w in wanted:
            r = resolve(w)
            if r:
                dest.append(r)

    toks = _tokens(" ; ".join(_shell_lines(command, state["bodies"])))
    seg = []
    for t in toks:
        if t in _SEPARATORS:
            flush(seg)
            seg = []
            if t == "(":
                stack.append((state["cwd"], state["exported"]))
            elif t == ")" and stack:
                state["cwd"], state["exported"] = stack.pop()
        else:
            seg.append(t)
    flush(seg)
    return out, state["unlocked"], state["unresolvable"]


# Quotes must MATCH. The first draft accepted `['"] ... ['"]`, so
# `node -e "require('fs').writeFileSync('AGENTS.md','x')"` yielded `require(`
# and the protected path in the middle of it was never seen. A path in a
# program is quoted, and it is quoted the same way at both ends.
# Three patterns run INDEPENDENTLY over the same text, never as one
# alternation. As one alternation the double-quoted branch of
# `node -e "require('fs').writeFileSync('AGENTS.md','x')"` swallows the whole
# argument in a single match and the single-quoted path inside it is never
# offered to the next iteration. A program quotes its paths, and a program is
# usually already inside somebody else's quotes, so nesting is the normal case.
_LITERAL_PATH_RES = (
    re.compile(r"'([^'\n]{2,300})'"),                       # 'single quoted'
    re.compile(r'"([^"\n]{2,300})"'),                       # "double quoted"
    re.compile(r"([A-Za-z0-9_.~@+-]*/[A-Za-z0-9_.~@/+-]*)"),  # bare, with a slash
)
# A protected file's bare name, quoted, in a writing program, is that file in
# the program's cwd: `p = "AGENTS.md"` from the vault root is the vault's
# AGENTS.md, exactly as `sed -i '' ... AGENTS.md` is. Not when it is joined
# onto something else (`R / "AGENTS.md"`, `join(tmp, "AGENTS.md")`, a word
# stuck to the quote): that is a fixture builder naming a file under a folder
# the reader cannot see, and guessing "here" for it is the guess this reader
# is not allowed to make.
_BARE_PROTECTED = {"AGENTS.md", "CLAUDE.md", "AGENT.md", ".hiring",
                   "settings.json", "settings.local.json"}
_JOINERS = "/,_"


def _joined(text, start):
    """True when the quote at `start` follows `/`, `,`, `_` or a word char."""
    j = start - 1
    while j >= 0 and text[j] in " \t":
        j -= 1
    return j >= 0 and (text[j] in _JOINERS or text[j].isalnum())


# A READ IS NOT A WRITE, even when the reader has given up on the program.
# Blanket-denying every inline program that NAMES a protected path refused
# `python3 -c "json.load(open('hooks-rules.json'))"` within a minute of
# shipping, and a guard that refuses ordinary inspection is a guard somebody
# deletes, which costs more than the case it caught. So the literal sweep is
# armed only when the program carries a write-shaped construct SOMEWHERE in
# its text. This is a heuristic in the ALLOW direction only: a program that
# writes through a shape not listed here is missed, which is the same
# under-blocking the rest of this reader already declares, and never the
# other way round.
# Plain alternation, assembled from a tuple. A single verbose-mode pattern was
# tried first and was wrong twice in five minutes: once because `\b` in a
# non-raw string is a backspace, and once because `(?x)` turned an ordinary
# `#` into a comment. A regex nobody can read is a regex nobody can check.
_WRITE_VERBS = (
    r"open\s*\([^)]*['\"][rbt+]*[wax]",     # open(p, 'w'), open(p, 'a'), 'xb'
    r"write_(?:text|bytes)",
    r"\.write(?:lines)?\s*\(",
    r"writeFileSync", r"appendFileSync", r"createWriteStream",
    r"unlink(?:Sync)?", r"renameSync", r"mkdirSync",
    r"os\.(?:remove|rename|replace|rmdir|makedirs|truncate)",
    r"shutil\.(?:copy\w*|move|rmtree)",
    r"\w+\.rename\s*\(",
    r"json\.dump\s*\(", r"yaml\.dump\s*\(", r"truncate\s*\(",
    r"File\.(?:write|open|delete|rename)", r"IO\.write",
    r"print\s*\([^)]*\bfile\s*=",
    r"chmod", r"\btee\b", r"\bsed\s+-i\b",
    # a redirect INTO a path. A bare `>` matched every `2>/dev/null` and every
    # `if a > b` in a program, and armed the sweep on read-only inspection
    # (Vex, 2026-09-15 morning: 13 of the 31 corpus refusals were that shape).
    r"(?<![-=<>!])>>?\s*['\"]?(?!/dev/)[/~.$]",
    r"open\s*\([^)]*['\"]\s*>>?",                # perl: open(F, '>file')
    r"\bmv\b", r"\bcp\b", r"\brm\b",
)
_WRITE_VERB_RE = re.compile("|".join(_WRITE_VERBS))


def _program_writes(command):
    """True when the inline program text carries any write-shaped construct."""
    return bool(_WRITE_VERB_RE.search(command))


def _literal_paths(command, cwd):
    """Every path-looking literal in the raw command text, absolute.

    Used ONLY when an interpreter was handed its program inline: the reader has
    given up on parsing that program, so the one thing it can still honestly do
    is notice a protected path spelled out in it. Heredoc bodies are INCLUDED
    here, unlike everywhere else in this reader, because here the body is the
    program rather than data."""
    out = []
    for m in [m for rx in _LITERAL_PATH_RES for m in rx.finditer(command)]:
        cand = (m.group(1) or "").strip()
        if not cand or cand.startswith("-"):
            continue
        # A path-shaped literal carries a separator, OR it is a protected
        # file's bare name standing on its own (see _BARE_PROTECTED). Any
        # other bare `AGENTS.md` was accepted for about ten minutes on
        # 2026-09-14 and refused two legitimate commands in that time, both
        # a fixture builder writing its own `AGENTS.md` under a temp folder
        # held in a variable: a bare filename joined onto something says
        # nothing about WHERE, and guessing "here" is the one guess this
        # reader is not allowed to make.
        #
        # The hole `python3 -c "open('AGENTS.md','w')"` from the vault root
        # left was closed 2026-09-15 morning (Vex): on the same 11,623 real
        # Bash calls the standalone bare name adds 22 refusals, 19 of them a
        # program editing this vault's AGENTS.md or CLAUDE.md from its root
        # (the house shape for those edits), 3 a program writing prose that
        # names the file. The joined shape (`R / "CLAUDE.md"`) stays skipped.
        if "/" not in cand and not (cand in _BARE_PROTECTED
                                    and not _joined(command, m.start())):
            continue
        if "$" in cand or "`" in cand or cand in _NOT_A_FILE:
            continue
        if cand.startswith("~"):
            cand = os.path.expanduser(cand)
        if not os.path.isabs(cand):
            if not cwd:
                continue
            cand = os.path.join(cwd, cand)
        out.append(os.path.abspath(cand))
    return out


def read_targets(tool_name, tool_input, cwd):
    """(paths, shell_unlocked, notice) for one hook payload.

    `paths` are strings: absolute for the shell reader, and as the host wrote
    them (a path key or a patch header, relative to `cwd`) otherwise.
    `notice` is one stderr line when the shell reader could not parse the
    command, and the caller ALLOWS that call after printing it."""
    found, unlocked, notice = [], False, None
    if not isinstance(tool_input, dict):
        return found, unlocked, notice
    for key in ("file_path", "notebook_path", "path"):
        v = tool_input.get(key)
        if isinstance(v, str) and v:
            found.append(v)
    is_shell = str(tool_name or "").lower() in SHELL_TOOLS
    for key in ("command", "patch", "input", "body"):
        v = tool_input.get(key)
        if not isinstance(v, str) or not v:
            continue
        headers = PATCH_FILE_HEADER.findall(v) + PATCH_MOVE_HEADER.findall(v)
        if headers:
            found.extend(headers)
        elif is_shell and key == "command":
            try:
                paths, unlocked, unresolvable = command_paths(v, cwd)
                found.extend(paths)
                if unresolvable:
                    who, how = unresolvable[0][:2]
                    notice = ("write-guard: this command hands a program to `%s` "
                              "through %s. The shell reader cannot tell what that "
                              "program writes, so the protected-path rule was NOT "
                              "applied to the program body. A protected path named "
                              "literally in the program IS still refused; anything "
                              "else in it is not checked.\n" % (who, how))
                    # The literals, because the path is right there in the bytes
                    # the host sent: every path-shaped literal in the PROGRAM
                    # text, judged from the cwd in force at that segment, when
                    # that program carries a write-shaped construct. Sweeping
                    # the whole command from the session cwd (2026-09-14) put a
                    # relative literal after `cd /elsewhere` in this vault,
                    # armed on a `>` or an `open(...,'w')` in another segment,
                    # and read the prose of a `cat` heredoc as a program: 13
                    # of 31 corpus refusals (Vex, 2026-09-15 morning). When the
                    # program text is not in the command (`cat p.py | python3 -`)
                    # the whole command is swept, as before. It still refuses a
                    # writing program that only MENTIONS a protected path with
                    # its folders, which is the safe direction for a friction
                    # gate whose message names the way through.
                    for _who, _how, seg_cwd, program, seg_unl in unresolvable:
                        if seg_unl:
                            continue    # that segment carries the unlock
                        text = program if program is not None else v
                        if _program_writes(text):
                            found.extend(_literal_paths(text, seg_cwd))
            except ValueError as exc:
                notice = ("write-guard: could not parse this shell command (%s); "
                          "the protected-path rule was NOT applied to it and the "
                          "call is allowed\n" % exc)
    return found, unlocked, notice


def strings(node, out, depth=0):
    """Every string in the tool input, whatever shape the host wraps it in.
    Read by walking rather than by naming fields, so a host that renames
    `content` or nests an edit list differently still gets scanned."""
    if depth > 12 or len(out) > 5000:
        return out
    if isinstance(node, dict):
        for v in node.values():
            strings(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            strings(v, out, depth + 1)
    elif isinstance(node, str):
        out.append(node)
    return out


# A relative path in a patch header or a shell command is relative to the
# SESSION's working directory, which the payload carries (main() joins it
# there). Resolving it against this process's own cwd answered a different
# question whenever the hook was not started in the session folder. The old
# one-root `relative()` lived here until the step 5 review; `rels_under`
# replaced it, against every guarded root.
def payload_root(payload):
    return os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ""


def _env_file(rel):
    base = os.path.basename(rel or "")
    return base == ".env" or base.startswith(".env.")


def read_stdin_text():
    """The hook payload, decoded as UTF-8 whatever the console codepage is.

    `sys.stdin.read()` decodes in the LOCALE codec. On a German Windows box
    that is cp1252, and a payload carrying an emoji (a session log, a reply
    draft, any note with a check mark in it) raised UnicodeDecodeError before
    this guard had looked at anything. This guard fails CLOSED on its own
    errors, so that exception was a refused write with a decoding traceback
    attached, on a payload that was never against a rule (Vex F-B, HIGH,
    2026-09-16). Read the bytes and decode them ourselves, replacing what will
    not decode: a byte we cannot read is not a reason to refuse a write, and
    the rules below match on shapes that survive replacement.
    """
    buf = getattr(sys.stdin, "buffer", None)
    if buf is None:            # a test harness handing us a text stream
        return sys.stdin.read()
    return buf.read().decode("utf-8", "replace")


def main():
    raw = read_stdin_text()
    if not raw.strip():
        return 0
    payload = json.loads(raw)
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    is_shell = tool_name.lower() in SHELL_TOOLS
    cwd = str(payload.get("cwd") or "")

    unlocked = os.environ.get(UNLOCK_ENV) == "1"

    paths, shell_unlocked, notice = read_targets(tool_name, tool_input, cwd)
    if notice:
        # The shell reader refused to guess. Say so, and then GO ON: the
        # interpreter case (Silas's Codex re-run, R1) carries both a notice and
        # the literal paths found in the program text, and returning here threw
        # those away, so the guard announced that it had not applied the rule
        # and then did not apply it to the one thing it could still see. Where
        # the reader produced no paths at all (an unbalanced quote) the loop
        # below finds nothing and the call is allowed exactly as before.
        print(notice, end="", file=sys.stderr)
    if shell_unlocked and not unlocked:
        # The paths of the unlocked segment(s) are already out of `paths`;
        # every other segment is judged below (Vex step 5, residual 3).
        print("write-guard: %s=1 on this command, guard stood down for the "
              "segment(s) it prefixes only; the rest of the command is still "
              "checked." % UNLOCK_ENV, file=sys.stderr)

    path = paths[0] if paths else ""
    notices = []
    roots = guarded_roots(payload, notices) if paths else []
    for line in notices:
        print(line, end="", file=sys.stderr)
    # Every (relative path, root, kind) a target has under a guarded root.
    hits = []
    for c in paths:
        ap = c
        if not os.path.isabs(ap) and payload.get("cwd"):
            ap = os.path.join(str(payload.get("cwd")), ap)
        for root, kind in roots:
            for crel in rels_under(ap, root):
                hits.append((crel, root, kind))
    rel = hits[0][0] if hits else None
    if not unlocked:
        for crel, root, kind in hits:
            if kind == "source":
                continue            # scan scope only; see guarded_roots
            if kind == "scratchpad":
                why = PROTECTED[0][1]
                crel = "%s/%s" % (os.path.basename(root.rstrip("/")), crel)
            else:
                why = protected_reason(crel, root)
            if why and kind != "scratchpad" and hiring_open(root, crel):
                why = None          # an open hire, on this agent's own contract
            if why:
                print("BLOCKED write to %s: %s.\n"
                      "Two ways through, in order. If this is a HIRE, the marker "
                      "is the door: `new-agent.py` writes 06 AI Team/Agents/"
                      "<Name>/.hiring and this guard stands down for that one "
                      "contract for 24 hours, and check-hire.py clears it on a "
                      "green run. If this is an approved edit to something that "
                      "already exists: on the file tools re-run the session with "
                      "%s=1; on Bash prefix that ONE command with %s=1 and the "
                      "guard logs the stand-down. A shell is not a way around this "
                      "line any more: the same rule reads Bash."
                      % (crel, why, UNLOCK_ENV, UNLOCK_ENV), file=sys.stderr)
                return 2

    # Rule 2 on the shell kind applies when the command writes INTO the vault
    # and not into `.env`: that is the sanctioned home for a secret, and the
    # transcript already holds whatever was typed. A command with no vault
    # write is not this rule's business.
    scan = True
    if is_shell:
        scan = any(not _env_file(h[0]) for h in hits)
    if not unlocked and scan:
        text = "\n".join(strings(tool_input, []))[:MAX_SCAN_CHARS]
        label = secret_reason(text)
        if label:
            print("BLOCKED write to %s: the content carries %s. Secrets live only "
                  "in .env (AGENTS.md hard rule 10); write the variable NAME here "
                  "and the value there. If this is a worked example, make it "
                  "obviously fake (EXAMPLE, your-key-here) or set %s=1 for this "
                  "one call." % (rel or path or "this file", label, UNLOCK_ENV),
                  file=sys.stderr)
            return 2

    if over_budget():
        print("write-guard: budget of %.0fs exceeded; the write was NOT checked"
              % BUDGET_S, file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail CLOSED, loudly. See the docstring.
        print("BLOCKED by write-guard: it failed closed on its own error (%s: %s); "
              "this write was NOT checked. Fix the guard, or set %s=1 for this one "
              "write, or remove the write-guard.py entry from .claude/settings.json."
              % (type(exc).__name__, exc, UNLOCK_ENV), file=sys.stderr)
        sys.exit(2)
