#!/usr/bin/env python3
"""Scan an external knowledge source and report WHAT is there, as JSON.

Usage: import-inventory.py <source-path>

Deterministic only: counts, shapes, frontmatter keys. The MAPPING of
this material into the six rooms is judgement and stays with the model
(WS-1004). Detects known source shapes:
  - mypka   (INPUT/CONTROL/OUTPUT/REFINE folders)
  - obsidian-vault (.obsidian folder)
  - markdown-folder (plain .md tree)
"""
import json, sys
from collections import Counter
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("FAIL usage: import-inventory.py <source-path>")
src = Path(sys.argv[1]).expanduser()
if not src.is_dir():
    sys.exit(f"FAIL not a directory: {src}")

names = {p.name for p in src.iterdir() if p.is_dir()}
files_at_root = {p.name for p in src.iterdir() if p.is_file()}
if "SKILL.md" in files_at_root or any((src / d / "SKILL.md").is_file() for d in names):
    shape = "skill-package"
elif {"CONTROL", "REFINE"} <= names or {"INPUT", "OUTPUT", "CONTROL"} <= names:
    shape = "mypka"
elif ".obsidian" in names:
    shape = "obsidian-vault"
else:
    shape = "markdown-folder"

ext = Counter()
fm_keys = Counter()
agents = []
skills = []
top = Counter()
for p in src.rglob("*"):
    if any(part.startswith(".") and part != ".obsidian" for part in p.relative_to(src).parts):
        continue
    if p.is_file():
        ext[p.suffix.lower() or "(none)"] += 1
        rel = p.relative_to(src)
        top[rel.parts[0]] += 1
        if p.name in ("AGENT.md", "AGENTS.md") or (p.suffix == ".md" and p.parent.name == "agents"):
            agents.append(str(rel))
        if p.name == "SKILL.md" or (p.suffix in (".py", ".sh", ".js") and "script" in str(rel).lower()):
            skills.append(str(rel))
        if p.suffix == ".md" and ext[".md"] <= 400:
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
                if t.startswith("---\n"):
                    for line in t[4:t.find("\n---\n", 4)].splitlines():
                        if ":" in line and not line.startswith((" ", "#", "-")):
                            fm_keys[line.split(":", 1)[0].strip()] += 1
            except Exception:
                pass

print(json.dumps({
    "source": str(src),
    "shape": shape,
    "files_by_extension": dict(ext.most_common(15)),
    "files_by_top_folder": dict(top.most_common(20)),
    "frontmatter_keys": dict(fm_keys.most_common(25)),
    "agent_definitions_found": agents[:40],
    "skill_definitions_and_scripts_found": skills[:40],
}, indent=2))
