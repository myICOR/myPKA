#!/usr/bin/env python3
"""
weekly-report-render.py - Turn a week bundle into a filed Week in Ink edition.

Owner: Charta. Schema source: GL-002 §"Weekly reports".
Input:  a bundle from weekly-report-gather.py
Output: PKM/Weekly Reports/YYYY/MM/<slug>/
          metadata.md   frontmatter + a REAL prose mirror of the week
          the-week-in-ink-<anchor>.html   the deck

TWO RULES THIS FILE EXISTS TO ENFORCE

1. ASSEMBLE, NEVER INVENT. Every sentence rendered is traceable to a captured
   fact: a Journal entry title or excerpt, a Zenon stoic perspective, an image
   filename, a Deliverable folder, a session-log topic. Where a week has no
   personal capture the edition SAYS SO and renders a work-only record. A
   fabricated recap of someone's own life is worse than a thin one.

2. THE MARKDOWN BODY IS THE SEARCHABLE ARTEFACT. weekly_reports.body is what the
   RAG corpus embeds (SOP-030). If the body is scaffolding ("## The seven pages",
   "## Build history") then semantic search returns section headers instead of
   content — which is exactly what happened to edition 28. So the mirror below
   carries the week's actual narrative, day by day, not a description of the deck.

USAGE
    python3 weekly-report-render.py /tmp/wk-bundles/2026-06-05.json [--force]
    python3 weekly-report-render.py --all /tmp/wk-bundles [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
ROOT = VAULT / "PKM/Weekly Reports"
MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

# Journal categories that read as personal rather than work. Used only to SPLIT
# the week onto the right page, never to hide anything.
PERSONAL = {"reflection", "gratitude", "mental", "physical", "family", "personal"}


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def covers(b: dict) -> str:
    s, t = b["week_start"], b["week_end"]
    sy, sm, sd = int(s[:4]), int(s[5:7]), int(s[8:10])
    ty, tm, td = int(t[:4]), int(t[5:7]), int(t[8:10])
    if (sy, sm) == (ty, tm):
        return f"{sd}-{td} {MONTHS[tm]} {ty}"
    if sy == ty:
        return f"{sd} {MONTHS[sm]} to {td} {MONTHS[tm]} {ty}"
    return f"{sd} {MONTHS[sm]} {sy} to {td} {MONTHS[tm]} {ty}"


def first_sentence(text: str, cap: int = 240) -> str:
    t = " ".join((text or "").split())
    if not t:
        return ""
    m = re.search(r'(.+?[.!?])(\s|$)', t)
    out = m.group(1) if m else t
    return out[:cap].rstrip() + ("…" if len(out) > cap else "")


def edition_no(anchor: str) -> int:
    """Edition 28 is the anchor point (2026-07-10). Editions are one per week, so
    the number is derivable by week offset from that fixed pair. Stored in
    frontmatter rather than recomputed by consumers."""
    import datetime as dt
    base_d, base_n = dt.date(2026, 7, 10), 28
    d = dt.date.fromisoformat(anchor)
    return base_n + round((d - base_d).days / 7)


def split_week(b: dict):
    subst = [e for e in b["journal"] if not e["is_zenon"]]
    zenon = {e["date"]: e for e in b["journal"] if e["is_zenon"]}
    personal = [e for e in subst if (e.get("category") or "") in PERSONAL
                or (e.get("key_element") or "") in ("family", "health")]
    work = [e for e in subst if e not in personal]
    pivotal = b["pivotal"] or sorted(
        subst, key=lambda e: (e.get("mood_valence") is None, -abs((e.get("mood_valence") or 3) - 3))
    )[:3]
    return subst, zenon, personal, work, pivotal


# ==========================================================================
# markdown mirror  (this is what gets embedded)
# ==========================================================================
def build_markdown(b: dict, slug: str, html_name: str) -> str:
    subst, zenon, personal, work, pivotal = split_week(b)
    c, agg = b["counts"], b["aggregate"]
    ed = edition_no(b["anchor"])
    dens = b["density"]

    fm = [
        "---", "type: weekly-report", f"report_date: {b['anchor']}", f"slug: {slug}",
        f"edition: {ed}", f"week_start: {b['week_start']}", f"week_end: {b['week_end']}",
        f"iso_week: {b['iso_week']}",
        # json.dumps, not an f-string with bare quotes: journal titles contain
        # double quotes (e.g. retiring "tom solid") and a naive quoted scalar
        # produces YAML that parses as a truncated block collection, which silently
        # drops edition/source_* on import.
        "title: " + json.dumps(covers(b) if not subst else subst[0]["title"][:70],
                               ensure_ascii=False),
        f"status: published", f"html_render: {html_name}",
        'podcast_path: ""', 'podcast_duration: ""',
    ]
    fm.append("source_journal_entries:" if b["journal"] else "source_journal_entries: []")
    for e in b["journal"]:
        fm.append(f"  - {e['slug']}")
    fm.append("source_images:" if b["images"] else "source_images: []")
    for i in b["images"]:
        fm.append(f"  - {i['name']}")
    fm.append("pivotal_moments:" if b["pivotal"] else "pivotal_moments: []")
    for e in b["pivotal"]:
        fm.append(f"  - {e['slug']}")

    # search_expansion: real vocabulary harvested from the week, so the offline
    # filter behaves semantically. Titles + key elements + topics + image labels.
    terms = []
    for e in subst:
        terms.append(e["title"].lower())
    terms += [str(k).replace("-", " ") for k in agg["key_elements"]]
    for e in subst:
        terms += [str(t).replace("-", " ") for t in e["linked_topics"]]
    terms += [i["label"] for i in b["images"][:12]]
    terms += [d["label"] for d in b["deliverables"][:12]]
    seen, uniq = set(), []
    for t in terms:
        t = " ".join(str(t).split())[:90]
        if t and t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    fm.append("search_expansion:")
    for t in uniq[:28]:
        fm.append("  - " + json.dumps(t, ensure_ascii=False))
    fm += ["specialists:", "  - penn", "  - charta",
           "tags:", "  - weekly-report", "  - week-in-ink"]
    if dens != "full":
        fm.append(f"  - {dens}-week")
    fm.append("---")

    # ---------------- body: the actual week ----------------
    L = [f"\n# The Week in Ink, edition {ed}", ""]
    L.append(f"**Covers {covers(b)}** ({b['week_start']} to {b['week_end']}). "
             f"Labelled {b['iso_week']} after its Friday anchor; the span opens the "
             f"preceding Saturday, so the week number and the covered days deliberately "
             f"do not line up.")
    L.append("")
    L.append(f"Assembled from {c['journal']} journal entr"
             f"{'y' if c['journal'] == 1 else 'ies'}, {c['images']} image capture"
             f"{'' if c['images'] == 1 else 's'}, {c['deliverables']} deliverable folder"
             f"{'' if c['deliverables'] == 1 else 's'} and {c['sessions']} session log"
             f"{'' if c['sessions'] == 1 else 's'}.")
    L.append("")

    if dens == "sparse":
        L.append("## What kind of edition this is")
        L.append("")
        L.append("**No journal entries and no image captures exist for this week.** "
                 "The Week in Ink is built from exactly those two sources, so this "
                 "edition cannot carry pivotal moments or a life-and-family page. "
                 "What follows is a work-only record assembled from session logs and "
                 "deliverables. It is filed rather than skipped so the archive has no "
                 "silent gaps, and it is marked sparse rather than padded with invented "
                 "narrative.")
        L.append("")

    # --- the days
    if subst:
        L.append("## The week, day by day")
        L.append("")
        for d in sorted({e["date"] for e in subst}):
            day = [e for e in subst if e["date"] == d]
            L.append(f"### {day[0]['weekday']} {d}")
            L.append("")
            for e in day:
                bits = []
                if e.get("mood"):
                    bits.append(str(e["mood"]))
                if e.get("energy"):
                    bits.append(f"energy {e['energy']}")
                meta = f" ({', '.join(bits)})" if bits else ""
                L.append(f"- **{e['title']}**{meta}. {first_sentence(e['excerpt'])}")
                L.append(f"  [[{e['slug']}]]")
            z = zenon.get(d)
            if z and z.get("stoic"):
                L.append(f"  > {first_sentence(z['stoic'], 300)}")
            L.append("")

    # --- pivotal
    if pivotal:
        head = ("## Pivotal moments" if b["pivotal"]
                else "## The entries that carried the most weight")
        L.append(head)
        L.append("")
        if not b["pivotal"]:
            L.append("*No entry was tagged `pivotal-moment-` this week, so these are the "
                     "entries whose recorded mood moved furthest from neutral.*")
            L.append("")
        for e in pivotal:
            L.append(f"- **{e['title']}** ({e['date']}). {first_sentence(e['excerpt'], 300)} "
                     f"[[{e['slug']}]]")
        L.append("")

    # --- business and content
    L.append("## The business and content week")
    L.append("")
    if b["deliverables"]:
        L.append(f"{len(b['deliverables'])} deliverable folder"
                 f"{'' if len(b['deliverables']) == 1 else 's'} opened:")
        L.append("")
        for d in b["deliverables"][:16]:
            L.append(f"- {d['label']} (`{d['slug']}`)")
        if len(b["deliverables"]) > 16:
            L.append(f"- …and {len(b['deliverables']) - 16} more")
        L.append("")
    if b["sessions_by_agent"]:
        who = ", ".join(f"{a} ({n})" for a, n in list(b["sessions_by_agent"].items())[:8])
        L.append(f"Session load by specialist: {who}.")
        L.append("")
        L.append("Threads worked:")
        L.append("")
        seen_t = set()
        for s in b["sessions"]:
            t = s["topic"]
            if t in seen_t:
                continue
            seen_t.add(t)
            L.append(f"- {t} ({s['agent']}, {s['date']})")
            if len(seen_t) >= 14:
                break
        L.append("")
    if work:
        L.append("Work entries captured in the journal:")
        L.append("")
        for e in work:
            L.append(f"- **{e['title']}** ({e['date']}) [[{e['slug']}]]")
        L.append("")

    # --- life and family
    if personal:
        L.append("## Life and family")
        L.append("")
        for e in personal:
            L.append(f"- **{e['title']}** ({e['weekday']} {e['date']}). "
                     f"{first_sentence(e['excerpt'])} [[{e['slug']}]]")
        L.append("")
    if b["images"]:
        L.append("Captured this week:")
        L.append("")
        for i in b["images"][:14]:
            L.append(f"- {i['label']} (`{i['name']}`)")
        L.append("")

    # --- the arc
    if any(v is not None for v in agg["virtues"].values()) or agg["mood_valence"] is not None:
        L.append("## The arc")
        L.append("")
        if agg["mood_valence"] is not None:
            L.append(f"Mean recorded mood valence: {agg['mood_valence']} of 5.")
        vs = {k: v for k, v in agg["virtues"].items() if v is not None}
        if vs:
            L.append("Virtue averages: " + ", ".join(
                f"{k.replace('virtue_', '')} {v}" for k, v in vs.items()) + " (0-100).")
        ms = {k: v for k, v in agg["moods"].items() if v is not None}
        if ms:
            L.append("Mood texture: " + ", ".join(
                f"{k.replace('mood_', '')} {v}" for k, v in ms.items()) + " (0-100).")
        if agg["key_elements"]:
            L.append("Key elements touched: " + ", ".join(
                f"{k} ({n})" for k, n in sorted(agg["key_elements"].items(),
                                                key=lambda kv: -kv[1])) + ".")
        L.append("")

    L.append("## Provenance")
    L.append("")
    L.append(f"Gathered by `weekly-report-gather.py` and rendered by "
             f"`weekly-report-render.py` from captured sources only. Density: **{dens}**. "
             f"No podcast episode exists for this edition.")
    L.append("")
    return "\n".join(fm) + "\n".join(L) + "\n"


# ==========================================================================
# the deck
# ==========================================================================
SLIDE_CSS = """
/* generated-edition additions on top of _assets/deck.css (gx- prefix: no collisions) */
.slide{padding:52px 56px 44px}
.gx-h{display:flex;justify-content:space-between;align-items:center;gap:20px;
border-bottom:1px solid var(--hair);padding-bottom:10px;margin-bottom:20px}
.gx-grid{display:grid;gap:20px;height:518px}
.gx-2{grid-template-columns:1fr 1fr}.gx-3{grid-template-columns:1fr 1fr 1fr}
.gx-card{background:var(--card);border:1px solid var(--hair-sub);border-radius:10px;
padding:16px 18px;display:flex;flex-direction:column;min-height:0}
.gx-ct{font-family:'Bricolage Grotesque',sans-serif;font-weight:640;font-size:15px}
.gx-cs{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--faint);margin-top:3px}
.gx-scroll{margin-top:11px;overflow-y:auto;min-height:0;flex:1}
.gx-scroll::-webkit-scrollbar{width:6px}
.gx-scroll::-webkit-scrollbar-thumb{background:var(--hair-emp);border-radius:3px}
.gx-scroll ul{list-style:none;margin:0;padding:0}
.gx-scroll li{padding:7px 0;border-bottom:1px solid var(--hair-sub);font-size:12.5px;
color:var(--dim);display:flex;justify-content:space-between;gap:12px;align-items:baseline}
.gx-scroll li:last-child{border-bottom:0}
.gx-qt{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--faint);white-space:nowrap;flex:0 0 auto}
.gx-note{font-size:13px;color:var(--faint);background:var(--card);border:1px dashed var(--hair);
border-radius:10px;padding:14px 16px;margin:0 0 16px}
.gx-day{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:9px;letter-spacing:.16em;
text-transform:uppercase;color:var(--marker);margin:14px 0 2px}
.gx-bar{display:flex;align-items:center;gap:10px;padding:5px 0}
.gx-bl{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--faint);width:78px;flex:0 0 auto}
.gx-bt{flex:1;height:6px;background:var(--raised);border-radius:3px;overflow:hidden}
.gx-bt i{display:block;height:100%;background:var(--marker);border-radius:3px}
.gx-bv{font-size:10px;color:var(--dim);width:26px;text-align:right;flex:0 0 auto}
.gx-gal{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}
.gx-gal figure{margin:0;cursor:zoom-in}
.gx-gal img{width:100%;height:82px;object-fit:cover;border-radius:7px;border:1px solid var(--hair-sub)}
.gx-gal figcaption{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:7.5px;
letter-spacing:.06em;text-transform:uppercase;color:var(--faint);margin-top:4px;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gx-w{grid-template-columns:1.5fr 1fr}
.ag-row{display:flex;align-items:center;gap:11px;padding:7px 0}
.ag-nm{width:76px;flex:0 0 auto;font-family:'Spline Sans Mono',ui-monospace,monospace;
font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ag-track{position:relative;flex:1;height:24px;background:var(--raised);
border-radius:12px;min-width:0}
.ag-fill{position:absolute;left:0;top:0;bottom:0;border-radius:12px;
background:linear-gradient(90deg,rgba(255,90,45,.30),var(--marker))}
.ag-face{position:absolute;top:50%;transform:translate(-50%,-50%);width:28px;height:28px;
border-radius:50%;object-fit:cover;border:2px solid var(--bg);box-shadow:0 0 0 1.5px var(--marker);
background:var(--card)}
.ag-ini{position:absolute;top:50%;transform:translate(-50%,-50%);width:28px;height:28px;
border-radius:50%;border:2px solid var(--bg);box-shadow:0 0 0 1.5px var(--hair-emp);
background:var(--raised);color:var(--dim);display:flex;align-items:center;justify-content:center;
font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:10px}
.ag-n{width:36px;flex:0 0 auto;text-align:right;font-family:'Spline Sans Mono',ui-monospace,monospace;
font-size:11px;color:var(--fg)}
.ag-hero{display:flex;flex-direction:column;align-items:center;text-align:center;gap:7px;
padding:4px 0 14px;border-bottom:1px solid var(--hair-sub)}
.ag-hero-img{width:86px;height:86px;border-radius:50%;object-fit:cover;
border:3px solid var(--marker);box-shadow:0 0 26px rgba(255,90,45,.28)}
.ag-hero-nm{font-family:'Bricolage Grotesque',sans-serif;font-weight:640;font-size:19px}
.ag-hero-sub{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;
letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.ag-kpi{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--hair-sub)}
.ag-kpi b{font-family:'Bricolage Grotesque',sans-serif;font-weight:640;font-size:20px}
.ag-kpi span{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;
letter-spacing:.12em;text-transform:uppercase;color:var(--faint);align-self:flex-end}
.ag-share{display:flex;height:11px;border-radius:6px;overflow:hidden;margin-top:13px;gap:2px}
.ag-share i{display:block;height:100%;background:var(--marker)}
.ag-legend{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}
.ag-legend span{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8px;
letter-spacing:.08em;text-transform:uppercase;color:var(--faint)}
.gx-lead{font-family:'Bricolage Grotesque',sans-serif;font-weight:640;
font-size:34px;line-height:1.08;letter-spacing:-.02em;margin:22px 0 20px}
"""


def slide(sid, kicker, num, inner, ed, cov):
    return (f'<section class="slide" id="{sid}" aria-label="{esc(kicker)}">'
            f'<div class="gx-h"><span class="sect-k kicker"><span class="knum">{num}</span> &middot; '
            f'{esc(kicker)}</span><span class="nm">The Week in Ink &middot; Ed {ed} &middot; {esc(cov)}</span>'
            f'</div>{inner}</section>')


def gx_card(title, sub, inner):
    return (f'<div class="gx-card"><div class="gx-ct">{esc(title)}</div>'
            f'<div class="gx-cs">{esc(sub)}</div><div class="gx-scroll">{inner}</div></div>')


def li(main, qt=""):
    q = f'<span class="gx-qt">{esc(qt)}</span>' if qt else ""
    return f'<li><span>{main}</span>{q}</li>'



def build_agent_slide(b, ed, cov, up):
    """Slide: the team at work. A horizontal bar chart where each specialist's
    avatar rides the tip of their own bar. Specialists with no avatar.png fall
    back to initials rather than a broken image (Marcus has none)."""
    agents = b.get("agents") or []
    total = b["counts"]["sessions"]
    if not agents:
        return slide("pTeam", "The team at work", "04",
                     '<p class="gx-note">No session logs were recorded this week, so there '
                     'is no specialist activity to chart.</p>', ed, cov)

    top = agents[0]
    mx = max(a["sessions"] for a in agents) or 1

    def face(a, cls_img, cls_ini, style=""):
        if a["avatar"]:
            src = up + urllib.parse.quote(a["avatar"])
            return (f'<img class="{cls_img}" style="{style}" loading="lazy" '
                    f'src="{src}" alt="{esc(a["name"])}">')
        ini = (a["slug"][:2] or "??").upper()
        return f'<span class="{cls_ini}" style="{style}" aria-label="{esc(a["name"])}">{esc(ini)}</span>'

    rows = []
    for a in agents:
        pct = a["sessions"] / mx * 100
        # keep the avatar inside the track at both extremes
        pos = f"max(15px, min(calc(100% - 15px), {pct:.1f}%))"
        rows.append(
            f'<div class="ag-row"><span class="ag-nm" title="{esc(a["name"])}">{esc(a["slug"])}</span>'
            f'<span class="ag-track"><i class="ag-fill" style="width:{pct:.1f}%"></i>'
            + face(a, "ag-face", "ag-ini", f"left:{pos}")
            + f'</span><span class="ag-n">{a["sessions"]}</span></div>')

    seg, leg = [], []
    for n, a in enumerate(agents[:6]):
        op = 1 - (n * 0.13)
        seg.append(f'<i style="flex:{a["share"] or 1};opacity:{op:.2f}"></i>')
        leg.append(f'<span>{esc(a["slug"])} {a["share"]}%</span>')
    rest = sum(a["share"] for a in agents[6:])
    if rest > 0:
        seg.append(f'<i style="flex:{rest};opacity:.18"></i>')
        leg.append(f'<span>others {rest}%</span>')

    hero = (f'<div class="ag-hero">'
            + face(top, "ag-hero-img", "ag-hero-img")
            + f'<span class="ag-hero-nm">{esc(top["name"])}</span>'
            f'<span class="ag-hero-sub">busiest specialist &middot; {top["sessions"]} runs '
            f'&middot; {top["share"]}%</span></div>'
            f'<div class="ag-kpi"><b>{total}</b><span>sessions</span></div>'
            f'<div class="ag-kpi"><b>{len(agents)}</b><span>specialists engaged</span></div>'
            f'<div class="ag-kpi"><b>{round(total / len(agents))}</b><span>mean runs each</span></div>'
            f'<div class="ag-share">{"".join(seg)}</div>'
            f'<div class="ag-legend">{"".join(leg)}</div>')

    return slide("pTeam", "The team at work", "04",
                 '<div class="gx-grid gx-w">'
                 + gx_card("Session load by specialist",
                           # literal U+00B7, NOT "&middot;": gx_card escapes its
                           # subtitle, so an entity would render as raw text.
                           f'{len(agents)} specialists \u00b7 {total} runs',
                           "".join(rows))
                 + f'<div class="gx-card"><div class="gx-ct">Who carried the week</div>'
                   f'<div class="gx-cs">share of all runs</div>'
                   f'<div class="gx-scroll">{hero}</div></div>'
                 + '</div>', ed, cov)


def build_html(b: dict, slug: str) -> str:
    subst, zenon, personal, work, pivotal = split_week(b)
    c, agg = b["counts"], b["aggregate"]
    ed, cov = edition_no(b["anchor"]), covers(b)
    up = "../" * 5          # vault root (image `file` values are vault-relative)
    # The deck engine lives in a FRAMEWORK path, not under PKM/. manifest.json marks
    # PKM/** as user state the updater must never write, so an engine file shipped
    # there could never receive a fix. Team Knowledge/scripts/** is framework-owned
    # and upgradable, so deck.css / deck.js / fonts live there and editions reference
    # them across the vault root.
    up_wr = "../" * 5 + "Team%20Knowledge/scripts/weekly-report-assets/"
    imgs = [i for i in b["images"] if i["web_ready"]]
    sparse = b["density"] == "sparse"

    lead = (subst[0]["title"] if subst else
            (b["deliverables"][0]["label"].title() if b["deliverables"]
             else "A quiet week on the record"))
    stats = "".join(
        f'<div class="ms"><span class="v">{v}</span><span class="l">{esc(l)}</span></div>'
        for l, v in [("journal entries", c["journal"]), ("images", c["images"]),
                     ("deliverables", c["deliverables"]), ("sessions", c["sessions"])])
    mark = ('<svg class="cover-line" viewBox="0 0 560 84" role="img" aria-label="The ink line, unwound">'
            '<path pathLength="1" d="M 88 42 C 88 25, 66.4 25, 52 42 C 37.6 59, 16 59, 16 42 '
            'C 16 25, 37.6 25, 52 42 C 66.4 59, 88 59, 88 42 C 140 41, 180 42, 220 43 '
            'C 320 45.5, 420 40.5, 548 42"/></svg>')
    p1 = (f'<section class="slide cover is-active" id="p1" aria-label="Front page">{mark}'
          f'<div class="folio"><span>Edition No. {ed}</span>'
          f'<span>Tom&#39;s week, read back to you</span><span>myPKA team</span></div>'
          f'<div class="nameplate"><div class="name">THE WEEK <span class="ink-accent">IN INK</span></div>'
          f'<span class="dateline">{esc(cov)} &middot; {esc(b["iso_week"])} &middot; density {esc(b["density"])}</span></div>'
          f'<h1 class="gx-lead">{esc(lead)}</h1>'
          + (f'<p class="gx-note">No journal entries or image captures exist for this week. '
             f'This is a work-only record, filed so the archive has no silent gaps.</p>' if sparse else "")
          + f'<div class="mini-stats">{stats}</div></section>')

    if pivotal:
        cards = "".join(
            f'<div class="pcard"><div class="head"><span class="num">{n+1:02d}</span>'
            f'<span class="dt">{esc(e["weekday"])} {esc(e["date"])}</span></div>'
            f'<h3>{esc(e["title"])}</h3>'
            f'<div class="body">{esc(first_sentence(e["excerpt"], 300))}</div>'
            + (f'<div class="stoic">{esc(first_sentence(zenon[e["date"]]["stoic"], 240))}</div>'
               if zenon.get(e["date"]) and zenon[e["date"]].get("stoic") else "")
            + '</div>' for n, e in enumerate(pivotal[:3]))
        note = ("" if b["pivotal"] else
                '<p class="gx-note">Nothing was tagged a pivotal moment this week. These are '
                'the entries whose recorded mood moved furthest from neutral.</p>')
        inner = note + f'<div class="pivot-cols">{cards}</div>'
    else:
        inner = ('<p class="gx-note">No journal entries were captured this week, so there is '
                 'nothing to mark as a turning point. The work record is two pages on.</p>')
    p2 = slide("p2", "Pivotal moments" if b["pivotal"] else "Where the week turned", "01",
               inner, ed, cov)

    if subst:
        days = []
        for d in sorted({e["date"] for e in subst}):
            day = [e for e in subst if e["date"] == d]
            days.append(f'<div class="gx-day">{esc(day[0]["weekday"])} {esc(d)}</div><ul>'
                        + "".join(li(f'<b>{esc(e["title"])}</b>',
                                     e.get("mood") or e.get("energy") or "") for e in day)
                        + '</ul>')
        inner = ('<div class="gx-grid">'
                 + gx_card("The week, day by day", f'{len(subst)} entries', "".join(days))
                 + '</div>')
    else:
        inner = '<p class="gx-note">No journal entries were captured this week.</p>'
    p3 = slide("p3", "The week, day by day", "02", inner, ed, cov)

    dl = "".join(li(esc(d["label"]), d["date"][5:]) for d in b["deliverables"][:60])
    ses = "".join(li(f'<b>{esc(a)}</b>', str(n)) for a, n in b["sessions_by_agent"].items())
    threads, seen_t = [], set()
    for s in b["sessions"]:
        if s["topic"] in seen_t:
            continue
        seen_t.add(s["topic"])
        threads.append(li(esc(s["topic"]), s["agent"]))
        if len(threads) >= 60:
            break
    p4 = slide("p4", "The business and content week", "03",
               '<div class="gx-grid gx-3">'
               + gx_card("Deliverables", f'{c["deliverables"]} opened',
                         f'<ul>{dl}</ul>' if dl else '<p class="gx-note">none</p>')
               + gx_card("Session load", f'{c["sessions"]} runs',
                         f'<ul>{ses}</ul>' if ses else '<p class="gx-note">none</p>')
               + gx_card("Threads worked", f'{len(seen_t)} distinct',
                         f'<ul>{"".join(threads)}</ul>' if threads else '<p class="gx-note">none</p>')
               + '</div>', ed, cov)

    if personal or imgs:
        pl = "".join(li(f'<b>{esc(e["title"])}</b>', e["weekday"][:3] + " " + e["date"][5:])
                     for e in personal)
        gal = "".join(
            f'<figure class="lbx" data-cap="{esc(i["label"])}">'
            f'<img loading="lazy" src="{esc(up + i["file"])}" alt="{esc(i["label"])}">'
            f'<figcaption>{esc(i["label"])}</figcaption></figure>' for i in imgs[:12])
        inner = ('<div class="gx-grid gx-2">'
                 + gx_card("Entries", f'{len(personal)} personal',
                           f'<ul>{pl}</ul>' if pl else '<p class="gx-note">no personal entries</p>')
                 + gx_card("Captured", f'{len(imgs)} images',
                           f'<div class="gx-gal">{gal}</div>' if gal
                           else '<p class="gx-note">no web-renderable images</p>')
                 + '</div>')
    else:
        inner = ('<p class="gx-note">Nothing personal was captured this week: no journal '
                 'entries in the personal categories and no images. This page is empty on '
                 'purpose rather than filled with inference.</p>')
    pT = build_agent_slide(b, ed, cov, up)
    p5 = slide("p5", "Life and family", "05", inner, ed, cov)

    def bar(lbl, val, mx=100):
        w = 0 if val is None else max(2, round(val / mx * 100))
        return (f'<div class="gx-bar"><span class="gx-bl">{esc(lbl)}</span>'
                f'<span class="gx-bt"><i style="width:{w}%"></i></span>'
                f'<span class="gx-bv">{"-" if val is None else val}</span></div>')
    vb = "".join(bar(k.replace("virtue_", ""), v) for k, v in agg["virtues"].items()
                 if v is not None)
    mb = "".join(bar(k.replace("mood_", ""), v) for k, v in agg["moods"].items()
                 if v is not None)
    ke = "".join(li(esc(k), str(n)) for k, n in
                 sorted(agg["key_elements"].items(), key=lambda kv: -kv[1]))
    p6 = slide("p6", "The arc", "06",
               '<div class="gx-grid gx-3">'
               + gx_card("Virtue", "0-100 average", vb or '<p class="gx-note">not scored</p>')
               + gx_card("Mood texture", "0-100 average", mb or '<p class="gx-note">not scored</p>')
               + gx_card("Key elements", "touched this week",
                         f'<ul>{ke}</ul>' if ke else '<p class="gx-note">none recorded</p>')
               + '</div>', ed, cov)

    js_ = "".join(li(f'<b>{esc(e["title"])}</b>', e["date"][5:]) for e in b["journal"])
    ims = "".join(li(esc(i["label"]), i["date"][5:]) for i in b["images"])
    p7 = slide("p7", "Sources", "07",
               '<div class="gx-grid gx-2">'
               + gx_card("Journal", f'{c["journal"]} entries',
                         f'<ul>{js_}</ul>' if js_ else '<p class="gx-note">none</p>')
               + gx_card("Images", f'{c["images"]} captures',
                         f'<ul>{ims}</ul>' if ims else '<p class="gx-note">none</p>')
               + '</div>', ed, cov)

    chrome = (
        '<button class="edge left" id="edgeLeft" aria-label="Previous page" tabindex="-1"></button>'
        '<button class="edge right" id="edgeRight" aria-label="Next page" tabindex="-1"></button>'
        '<nav class="nav" aria-label="Page navigation">'
        '<button class="arrow" id="prev" aria-label="Previous page">&#8249;</button>'
        '<div class="dots" id="dots" role="tablist"></div>'
        '<span class="indicator"><span class="nm">The Week in Ink</span> &nbsp;&middot;&nbsp; '
        '<span class="cur" id="curNum">01</span> / <span id="totNum">08</span></span>'
        '<button class="arrow" id="next" aria-label="Next page">&#8250;</button></nav>'
        '<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true" '
        'aria-label="Image viewer">'
        '<button class="lb-close" id="lbClose" aria-label="Close image viewer">&#215;</button>'
        '<figure class="lb-frame"><img id="lbImg" alt="">'
        '<figcaption id="lbCap" class="mono"></figcaption></figure></div>')

    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>The Week in Ink &middot; Ed {ed} &middot; {esc(cov)}</title>'
            f'<link rel="stylesheet" href="{esc(up_wr)}inkline-fonts.css">'
            f'<link rel="stylesheet" href="{esc(up_wr)}deck.css">'
            f'<style>{SLIDE_CSS}</style></head><body>'
            f'<div class="deck-viewport"><div class="stage" id="stage">'
            f'{p1}{p2}{p3}{p4}{pT}{p5}{p6}{p7}'
            f'</div></div>{chrome}'
            f'<script src="{esc(up_wr)}deck.js"></script></body></html>')



# Frontmatter keys a human may have curated by hand, which a re-render must never
# clobber. Learned the hard way: a --force pass over edition 28 replaced its real
# title, blanked its podcast pointer, and swapped its curated 11-image source list
# for all 20 files that merely fell inside the date window.
CURATED_KEYS = ("title", "podcast_path", "podcast_duration", "source_images",
                "pivotal_moments", "specialists", "status")
CURATED_BEGIN = "<!-- CURATED:BEGIN -->"
CURATED_END = "<!-- CURATED:END -->"


def read_existing(meta: Path):
    """Return (curated frontmatter values, curated body block) from a prior file."""
    if not meta.exists():
        return {}, ""
    text = meta.read_text(encoding="utf-8")
    keep, body = {}, ""
    if CURATED_BEGIN in text and CURATED_END in text:
        body = text.split(CURATED_BEGIN, 1)[1].split(CURATED_END, 1)[0].strip()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        block = text[3:end] if end != -1 else ""
        cur = None
        for raw in block.splitlines():
            m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', raw)
            if m:
                cur = m.group(1)
                val = m.group(2).strip()
                if cur in CURATED_KEYS and val not in ("", '""', "[]"):
                    keep[cur] = val
                elif cur in CURATED_KEYS and val == "":
                    keep[cur] = []
                continue
            if cur in CURATED_KEYS and raw.lstrip().startswith("- ") and isinstance(keep.get(cur), list):
                keep[cur].append(raw.lstrip()[2:].strip())
    return {k: v for k, v in keep.items() if v not in ([], "")}, body


def apply_curated(md: str, keep: dict, curated_body: str) -> str:
    """Overlay preserved values onto a freshly generated metadata.md."""
    if not keep and not curated_body:
        return md
    head, rest = md.split("\n---\n", 1) if "\n---\n" in md else (md, "")
    lines = head.splitlines()
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r'^([A-Za-z0-9_]+):', ln)
        key = m.group(1) if m else None
        if key in keep:
            v = keep[key]
            if isinstance(v, list):
                out.append(f"{key}:")
                out += [f"  - {x}" for x in v]
            else:
                out.append(f"{key}: {v}")
            i += 1
            while i < len(lines) and lines[i].startswith(("  - ", "  ")) and not re.match(r'^[A-Za-z0-9_]+:', lines[i]):
                i += 1
            continue
        out.append(ln)
        i += 1
    md = "\n".join(out) + "\n---\n" + rest
    if curated_body:
        md = md.rstrip() + f"\n\n{CURATED_BEGIN}\n{curated_body}\n{CURATED_END}\n"
    return md



TEAM_BEGIN = "<!-- TEAMSLIDE:BEGIN -->"
TEAM_END = "<!-- TEAMSLIDE:END -->"


def inject_team_slide(html_path: Path, b: dict) -> bool:
    """Give a HAND-BUILT deck the generated team slide without touching anything else.

    Edition 28's deck is authored and must never be regenerated, but its week has the
    richest specialist data in the archive and the slide is pure derived analytics, so
    it does not conflict with hand-authored narrative. The block is marker-wrapped and
    idempotent. Its own engine reads slides.length dynamically, so the page counter and
    dots pick the extra slide up with no change to its JavaScript.

    The injected CSS deliberately DROPS the `.slide{padding}` rule from SLIDE_CSS: that
    would override the hand-built deck's own slide padding and reflow every page.
    """
    if not html_path.exists():
        return False
    h = html_path.read_text(encoding="utf-8")
    ed, cov = edition_no(b["anchor"]), covers(b)
    css = "\n".join(l for l in SLIDE_CSS.splitlines()
                     if not l.startswith(".slide{padding"))
    block = (f"{TEAM_BEGIN}\n<style>{css}</style>\n"
             + build_agent_slide(b, ed, cov, "../" * 5)
             + f"\n{TEAM_END}")
    if TEAM_BEGIN in h and TEAM_END in h:
        new = re.sub(re.escape(TEAM_BEGIN) + r".*?" + re.escape(TEAM_END),
                     lambda _: block, h, flags=re.S)
    else:
        anchor_tag = '</div><!-- /stage -->'
        if anchor_tag not in h:
            return False
        new = h.replace(anchor_tag, block + "\n" + anchor_tag, 1)
    if new == h:
        return False
    html_path.write_text(new, encoding="utf-8")
    return True


def render(bundle_path: Path, force: bool) -> str | None:
    b = json.loads(bundle_path.read_text(encoding="utf-8"))
    anchor = b["anchor"]
    y, m = anchor[:4], anchor[5:7]
    ed = edition_no(anchor)
    slug = f"{anchor}-week-in-ink-{ed}"
    out = ROOT / y / m / slug
    if out.exists() and not force:
        return f"exists, skipped: {slug}"
    out.mkdir(parents=True, exist_ok=True)
    html_name = f"the-week-in-ink-{anchor}.html"
    keep, curated_body = read_existing(out / "metadata.md")
    md = apply_curated(build_markdown(b, slug, html_name), keep, curated_body)
    (out / "metadata.md").write_text(md, encoding="utf-8")
    # A hand-authored deck is never regenerable: edition 28 carries a produced
    # episode, an audio-synced player, chapters and a transcript that no assembler
    # can reproduce. A --force pass once destroyed it and it had to be recovered
    # from git. The sentinel makes that unrepeatable.
    if (out / ".hand-built").exists():
        did = inject_team_slide(out / html_name, b)
        return (f"metadata refreshed, hand-built deck preserved"
                f"{', team slide synced' if did else ''}: {slug}")
    (out / html_name).write_text(build_html(b, slug), encoding="utf-8")
    return f"wrote {slug}  ({b['density']}, {b['counts']['journal']}j/{b['counts']['images']}i)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", nargs="?")
    ap.add_argument("--all", metavar="DIR")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    paths = sorted(Path(a.all).glob("*.json")) if a.all else [Path(a.bundle)]
    if not paths:
        print("no bundles found", file=sys.stderr)
        return 1
    for p in paths:
        print(" ", render(p, a.force))
    return 0


if __name__ == "__main__":
    sys.exit(main())
