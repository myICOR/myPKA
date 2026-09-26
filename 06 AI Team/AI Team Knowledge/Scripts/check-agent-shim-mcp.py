#!/usr/bin/env python3
"""check-agent-shim-mcp.py: no web research tools on a private-data agent's shim.

An agent that reads the member's most private notes (Penn reads and writes the
journal) must not also hold a tool that sends text to the open web. Then a
prompt injection hidden in something Penn files has no channel out. This is
the rule check-hire.py check 11 relays; until 6.0.2 the script was missing from
myPKA, so check 11 only ever warned (Vera C5 M1).

    check-agent-shim-mcp.py [<folder>]     <folder> is the team root or the
                                           .claude/agents folder itself;
                                           default: this script's team root
    check-agent-shim-mcp.py --self-test

A private-data shim must carry an explicit `tools:` line. No line, `*` or
`All tools` means every tool the host has, web search included, so each is a
FAIL (Vex C2 X3, X4): the rule is only a rule when the list is closed.
Naming a web tool on the line is the other violation. `Bash` is allowed
(Vex ruling, C2 X3/X4) but prints one NOTE: a shell can still reach the web
through curl or python3, which only a host-level network block closes.

Deterministic: a shim either names a banned tool or it does not. Exit 0 =
clean, exit 1 = violations, one FAIL line each on stderr. Stdlib only.
"""
import re
import sys
import tempfile
from pathlib import Path

SHIM_REL = ".claude/agents"
# The agents whose inputs are the member's private notes. Their shim slugs.
PRIVATE_DATA = ("penn",)
# Tools that send text to the open web: the host's own, and the research MCP
# servers myPKA documents. Matched on the tools line only.
# Entries that mean "every tool the host has".
OPEN_ENDED = ("*", "All tools")
BANNED_TOOLS = ("WebSearch", "WebFetch")
BANNED_MCP = ("mcp__brave-search", "mcp__perplexity", "mcp__exa", "mcp__tavily", "mcp__firecrawl")
TOOLS_RE = re.compile(r"(?m)^tools:\s*(.*)$")


def tools_of(text):
    """The tool entries on the frontmatter tools line, or None if there is none."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    head = text[3:end] if end != -1 else ""
    m = TOOLS_RE.search(head)
    if not m:
        return None
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def scan(shim_dir):
    fails, notes = [], []
    for slug in PRIVATE_DATA:
        p = shim_dir / (slug + ".md")
        if not p.is_file():
            continue  # an agent that is not hired is not a violation
        tools = tools_of(p.read_text(encoding="utf-8", errors="replace"))
        if tools is None:
            fails.append("%s: private-data shim has no tools line, so it inherits every host tool, "
                         "web search included; name the tools it needs" % p.name)
            continue
        for t in tools:
            if t in OPEN_ENDED:
                fails.append("%s: private-data shim names `%s`, every host tool, web search included; "
                             "name the tools it needs" % (p.name, t))
        for t in tools:
            if t == "Bash":
                notes.append("%s: private-data shim holds Bash; a shell can still reach the web "
                              "(curl, python3). Accepted; only a host-level network block closes it" % p.name)
            if t in BANNED_TOOLS or any(t == b or t.startswith(b + "__") for b in BANNED_MCP):
                fails.append("%s: private-data shim names %s, a tool that reaches the open web"
                             % (p.name, t))
    return fails, notes


def shim_dir_of(arg):
    p = Path(arg).expanduser().resolve()
    return p / SHIM_REL if (p / SHIM_REL).is_dir() else p


def self_test():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "penn.md").write_text("---\nname: penn\ntools: Read, Write\n---\n", encoding="utf-8")
        if scan(d)[0]:
            return "FAIL self-test: a clean private-data shim was reported"
        for bad in ("WebSearch", "mcp__perplexity__perplexity_ask", "mcp__brave-search"):
            (d / "penn.md").write_text("---\nname: penn\ntools: Read, %s\n---\n" % bad, encoding="utf-8")
            if not scan(d)[0]:
                return "FAIL self-test: %s on penn.md was not detected" % bad
        (d / "penn.md").write_text("---\nname: penn\ntools: Read, Write, Edit, Glob, Grep, Bash\n---\n",
                                   encoding="utf-8")
        f, n = scan(d)
        if f or not any("Bash" in x for x in n):
            return "FAIL self-test: a closed line with Bash must pass with one Bash NOTE"
        (d / "penn.md").write_text("---\nname: penn\ntools: Read\n---\nSee WebSearch in the body.\n",
                                   encoding="utf-8")
        if scan(d)[0]:
            return "FAIL self-test: a tool named in the body, not on the tools line, was reported"
        for bad, what in (("---\nname: penn\n---\n", "no tools line"),
                          ("---\nname: penn\ntools: *\n---\n", "tools: *"),
                          ("---\nname: penn\ntools: All tools\n---\n", "tools: All tools")):
            (d / "penn.md").write_text(bad, encoding="utf-8")
            if not scan(d)[0]:
                return "FAIL self-test: %s on penn.md was not detected" % what
    return None


def main(argv):
    if "--self-test" in argv:
        err = self_test()
        if err:
            print(err, file=sys.stderr)
            return 1
        print("OK self-test: 3 planted web tools and 3 open tool lists went red, 3 clean controls stayed green")
        return 0
    arg = argv[0] if argv else str(Path(__file__).resolve().parents[3])
    fails, notes = scan(shim_dir_of(arg))
    for n in notes:
        print("NOTE " + n)
    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print("OK no web research tool on the %d private-data shim(s)" % len(PRIVATE_DATA))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
