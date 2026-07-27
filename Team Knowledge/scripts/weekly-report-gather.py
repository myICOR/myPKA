#!/usr/bin/env python3
"""
weekly-report-gather.py - Assemble the deterministic source bundle for one Week in Ink edition.

Owner: Penn (the gather) / Charta (what the render does with it).
Schema source: GL-002 §"Weekly reports".

WHAT IT DOES
    Given a FRIDAY anchor date, collects everything captured in the covered week
    (the preceding Saturday through that Friday, inclusive) and emits one JSON
    bundle:

        journal      PKM/Journal/YYYY/MM/  entries + their frontmatter signals
        images       PKM/Images/YYYY/MM/   captures, web-renderable flag
        deliverables Deliverables/<date>-*/ folders opened that week
        sessions     Team Knowledge/session-logs/YYYY/MM/  runs, by specialist
        aggregate    the week's mood / energy / virtue arc for the front page
        density      how much personal capture exists, so a thin week is filed
                     honestly as `sparse` instead of being padded

THE POINT
    Everything here is CAPTURED FACT. The renderer assembles; it does not invent.
    A week with no journal entries produces a business-only edition that says so,
    because a fabricated recap of someone's life is worse than a thin one.

USAGE
    python3 weekly-report-gather.py 2026-07-10            # one anchor, prints JSON
    python3 weekly-report-gather.py --range 2026-05-01 2026-07-24   # every Friday
    python3 weekly-report-gather.py 2026-07-10 --out bundle.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
WEB_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
DATE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})')


# --------------------------------------------------------------------------
def parse_fm(path: Path) -> tuple[dict, str]:
    """Frontmatter + body. Scalars and '- ' lists plus '|' block scalars, which is
    everything the Journal schema uses. Dependency-free on purpose."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, ""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block, body = text[3:end], text[end + 4:]
    fm: dict = {}
    key = None
    block_scalar = False
    for raw in block.splitlines():
        if block_scalar:
            if raw.startswith((" ", "\t")) or not raw.strip():
                fm[key] = (fm.get(key) or "") + raw.strip() + " "
                continue
            block_scalar = False
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) and raw.lstrip().startswith("- ") and key:
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(raw.lstrip()[2:].strip().strip('"').strip("'"))
            continue
        m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in ("|", ">", "|-", ">-"):
            fm[key] = ""
            block_scalar = True
            continue
        if val == "":
            fm[key] = []
        else:
            v = val.strip('"').strip("'")
            fm[key] = int(v) if re.fullmatch(r'-?\d+', v) else v
    return fm, body


def title_of(path: Path, body: str, slug: str) -> str:
    m = re.search(r'^#\s+(.+)$', body, re.M)
    if m:
        return m.group(1).strip()
    return slug[11:].replace("-", " ").strip().capitalize() if len(slug) > 11 else slug


def in_window(name: str, a: dt.date, b: dt.date):
    m = DATE_RE.match(name)
    if not m:
        return None
    try:
        d = dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None
    return d if a <= d <= b else None


# --------------------------------------------------------------------------
def gather(anchor: dt.date) -> dict:
    start = anchor - dt.timedelta(days=6)

    # ---- journal -----------------------------------------------------------
    journal = []
    jroot = VAULT / "PKM/Journal"
    for f in sorted(jroot.rglob("*.md")):
        d = in_window(f.name, start, anchor)
        if not d:
            continue
        fm, body = parse_fm(f)
        slug = f.stem
        journal.append({
            "slug": slug,
            "date": str(d),
            "weekday": d.strftime("%A"),
            "title": title_of(f, body, slug),
            "category": fm.get("category"),
            "entry_type": fm.get("entry_type"),
            "mood": fm.get("mood"),
            "mood_valence": fm.get("mood_valence"),
            "energy": fm.get("energy"),
            "key_element": fm.get("key_element"),
            "linked_topics": fm.get("linked_topics") or [],
            "linked_goals": fm.get("linked_goals") or [],
            "stoic": (fm.get("stoic_perspective") or "").strip() or None,
            "virtues": {k: fm.get(k) for k in
                        ("virtue_wisdom", "virtue_courage", "virtue_justice", "virtue_temperance")
                        if fm.get(k) is not None},
            "moods": {k: fm.get(k) for k in
                      ("mood_frustration", "mood_motivation", "mood_positivity",
                       "mood_anxiety", "mood_clarity") if fm.get(k) is not None},
            "is_pivotal": "pivotal-moment" in slug,
            "is_zenon": "zenon-perspe" in slug or "zenon-perspektive" in slug,
            "file": str(f.relative_to(VAULT)),
            "excerpt": " ".join(re.sub(r'^#.*$', '', body, flags=re.M).split())[:400],
        })

    # ---- images ------------------------------------------------------------
    images = []
    for f in sorted((VAULT / "PKM/Images").rglob("*")):
        if not f.is_file():
            continue
        d = in_window(f.name, start, anchor)
        if not d:
            continue
        images.append({
            "file": str(f.relative_to(VAULT)),
            "name": f.name,
            "date": str(d),
            "label": f.stem[11:].replace("-", " "),
            "web_ready": f.suffix.lower() in WEB_IMAGE,
            "bytes": f.stat().st_size,
        })

    # ---- deliverables opened this week -------------------------------------
    deliverables = []
    for f in sorted((VAULT / "Deliverables").iterdir()):
        if not f.is_dir() or f.name.startswith("_"):
            continue
        d = in_window(f.name, start, anchor)
        if d:
            deliverables.append({"slug": f.name, "date": str(d),
                                 "label": f.name[11:].replace("-", " ")})
    arch = VAULT / "Deliverables/_archive"
    if arch.exists():
        for f in sorted(arch.iterdir()):
            if not f.is_dir():
                continue
            d = in_window(f.name, start, anchor)
            if d:
                deliverables.append({"slug": f.name, "date": str(d), "archived": True,
                                     "label": f.name[11:].replace("-", " ")})

    # ---- session logs ------------------------------------------------------
    sessions, by_agent = [], {}
    for f in sorted((VAULT / "Team Knowledge/session-logs").rglob("*.md")):
        d = in_window(f.name, start, anchor)
        if not d:
            continue
        m = re.match(r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}_([a-z0-9-]+)_(.+)\.md$', f.name)
        agent = m.group(1) if m else "unspecified"
        topic = (m.group(2).replace("-", " ") if m else f.stem)
        sessions.append({"date": str(d), "agent": agent, "topic": topic})
        by_agent[agent] = by_agent.get(agent, 0) + 1

    # ---- agents: session load with avatars ---------------------------------
    # Team folders are "<Name> - <Role>"; session-log slugs are the lowercased
    # first token ("charta", "penn"). Resolve once, here, so the renderer never
    # has to guess and a missing avatar degrades to initials instead of a 404.
    avatars = {}
    troot = VAULT / "Team"
    if troot.exists():
        for d in troot.iterdir():
            if not d.is_dir():
                continue
            key = d.name.split(" - ")[0].strip().lower()
            a = d / "avatar.png"
            if a.exists():
                avatars[key] = str(a.relative_to(VAULT))
    agents = []
    for slug, n in sorted(by_agent.items(), key=lambda kv: (-kv[1], kv[0])):
        agents.append({
            "slug": slug,
            "name": slug.capitalize(),
            "sessions": n,
            "share": round(n / len(sessions) * 100) if sessions else 0,
            "avatar": avatars.get(slug),
        })

    # ---- aggregate ---------------------------------------------------------
    def avg(vals):
        vals = [v for v in vals if isinstance(v, int)]
        return round(sum(vals) / len(vals)) if vals else None

    agg = {
        "mood_valence": avg([e["mood_valence"] for e in journal]),
        "virtues": {k: avg([e["virtues"].get(k) for e in journal])
                    for k in ("virtue_wisdom", "virtue_courage",
                              "virtue_justice", "virtue_temperance")},
        "moods": {k: avg([e["moods"].get(k) for e in journal])
                  for k in ("mood_frustration", "mood_motivation", "mood_positivity",
                            "mood_anxiety", "mood_clarity")},
        "categories": {},
        "key_elements": {},
    }
    for e in journal:
        if e["category"]:
            agg["categories"][e["category"]] = agg["categories"].get(e["category"], 0) + 1
        if e["key_element"]:
            agg["key_elements"][e["key_element"]] = agg["key_elements"].get(e["key_element"], 0) + 1

    # ---- density -----------------------------------------------------------
    substantive = [e for e in journal if not e["is_zenon"]]
    if len(substantive) >= 6 and images:
        density = "full"
    elif substantive or images:
        density = "light"
    else:
        density = "sparse"     # no personal capture at all: work-only edition

    return {
        "anchor": str(anchor),
        "week_start": str(start),
        "week_end": str(anchor),
        "iso_week": f"{anchor.isocalendar()[0]}-W{anchor.isocalendar()[1]:02d}",
        "density": density,
        "counts": {"journal": len(journal), "journal_substantive": len(substantive),
                   "images": len(images), "images_web_ready": sum(1 for i in images if i["web_ready"]),
                   "deliverables": len(deliverables), "sessions": len(sessions)},
        "journal": journal,
        "pivotal": [e for e in journal if e["is_pivotal"]],
        "images": images,
        "deliverables": deliverables,
        "sessions": sessions,
        "sessions_by_agent": dict(sorted(by_agent.items(), key=lambda kv: -kv[1])),
        "agents": agents,
        "aggregate": agg,
    }


# --------------------------------------------------------------------------
def fridays(a: dt.date, b: dt.date):
    d = a + dt.timedelta((4 - a.weekday()) % 7)      # first Friday on/after a
    while d <= b:
        yield d
        d += dt.timedelta(days=7)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("anchor", nargs="?", help="Friday anchor, YYYY-MM-DD")
    ap.add_argument("--range", nargs=2, metavar=("FROM", "TO"))
    ap.add_argument("--out", help="write JSON here (single anchor only)")
    ap.add_argument("--outdir", help="write one <anchor>.json per week into this dir")
    ap.add_argument("--summary", action="store_true", help="one line per week, no JSON")
    a = ap.parse_args()

    if a.range:
        anchors = list(fridays(dt.date.fromisoformat(a.range[0]),
                               dt.date.fromisoformat(a.range[1])))
    elif a.anchor:
        anchors = [dt.date.fromisoformat(a.anchor)]
    else:
        ap.error("give an anchor or --range")

    out = []
    for anc in anchors:
        if anc.weekday() != 4:
            print(f"warn: {anc} is a {anc.strftime('%A')}, not a Friday", file=sys.stderr)
        b = gather(anc)
        out.append(b)
        if a.outdir:
            d = Path(a.outdir); d.mkdir(parents=True, exist_ok=True)
            (d / f"{anc}.json").write_text(json.dumps(b, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
        if a.summary:
            c = b["counts"]
            piv = len(b["pivotal"])
            print(f"{b['anchor']}  {b['week_start']}..{b['week_end']}  "
                  f"{b['density']:6}  j={c['journal']:>2}({c['journal_substantive']:>2} subst) "
                  f"img={c['images']:>2} dlv={c['deliverables']:>2} ses={c['sessions']:>3} "
                  f"pivotal={piv}")

    if a.out and len(out) == 1:
        Path(a.out).write_text(json.dumps(out[0], indent=2, ensure_ascii=False), encoding="utf-8")
    elif not a.summary and not a.outdir:
        print(json.dumps(out[0] if len(out) == 1 else out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
