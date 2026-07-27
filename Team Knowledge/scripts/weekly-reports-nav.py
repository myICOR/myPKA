#!/usr/bin/env python3
"""
weekly-reports-nav.py - Inject the foldable archive drawer into every Week in Ink report.

Owner: Charta (rendering) / Silas (the manifest shape).
Schema source: GL-002 §"Weekly reports" (type: weekly-report).

WHAT IT DOES
    Walks PKM/Weekly Reports/YYYY/MM/<slug>/metadata.md, builds one manifest of
    every edition, and rewrites a single marked block inside each edition's
    rendered HTML:

        <!-- WEEKNAV:BEGIN -->  ... generated drawer (css + markup + js) ...  <!-- WEEKNAV:END -->

    The block is self-contained: styles, markup, the manifest as inline JSON, and
    the toggle/filter behaviour. No external requests, so the page keeps working
    from file:// (GL-058). Re-running is idempotent — the block is replaced, never
    appended. When the markers are absent the block is inserted right after <body>
    and the markers are planted for next time.

WHY MARKDOWN AND NOT mypka.db
    Markdown is canonical; mypka.db is derived and can be mid-regen or stale. The
    nav must never disagree with the notes on disk, so it reads the frontmatter
    directly. `weekly_reports` in the mirror is for querying, not for rendering.

SEARCH
    The manifest carries each edition's `search_expansion` (GL-002: topics,
    synonyms, entities, questions-it-answers). The in-page filter matches against
    title + slug + covers + that vocabulary, which behaves semantically without an
    embedding model — a file:// page cannot reach Ollama. True vector search over
    the same corpus is SOP-030 / rag-query.py, and the two are complementary.

USAGE
    python3 "Team Knowledge/scripts/weekly-reports-nav.py" [--check] [--vault PATH]

    --check   report what would change and exit non-zero if any file is stale;
              writes nothing. Use in a pre-publish gate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

BEGIN = "<!-- WEEKNAV:BEGIN -->"
END = "<!-- WEEKNAV:END -->"

MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------
def parse_frontmatter(path: Path) -> dict:
    """Minimal YAML frontmatter reader: scalars and '- ' lists, which is all the
    weekly-report schema uses. Deliberately dependency-free so the script runs on
    system python3 with no venv."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    fm: dict = {}
    key = None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) and raw.lstrip().startswith("- ") and key:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(_scalar(raw.lstrip()[2:]))
            continue
        m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        fm[key] = [] if val == "" else (_scalar(val) if val != "[]" else [])
    return fm


def _scalar(v: str):
    v = v.strip().strip('"').strip("'")
    if re.fullmatch(r'-?\d+', v):
        return int(v)
    return v


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------
def collect(root: Path) -> list[dict]:
    editions = []
    for meta in sorted(root.rglob("metadata.md")):
        if any(p.startswith("_") for p in meta.relative_to(root).parts):
            continue
        fm = parse_frontmatter(meta)
        date = str(fm.get("report_date", ""))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            print(f"  skip (no real report_date): {meta}", file=sys.stderr)
            continue
        html = fm.get("html_render")
        if not html or not (meta.parent / html).exists():
            print(f"  skip (html_render missing on disk): {meta}", file=sys.stderr)
            continue
        exp = fm.get("search_expansion") or []
        editions.append({
            "slug": fm.get("slug") or meta.parent.name,
            "edition": fm.get("edition"),
            "date": date,
            "year": int(date[:4]),
            "month": int(date[5:7]),
            "start": str(fm.get("week_start", "")),
            "end": str(fm.get("week_end", "")),
            "title": fm.get("title") or meta.parent.name,
            "status": fm.get("status", ""),
            "dur": fm.get("podcast_duration", ""),
            "file": str(meta.parent / html),
            "terms": " ".join(str(t) for t in exp).lower(),
        })
    editions.sort(key=lambda e: (e["date"], e["edition"] or 0), reverse=True)
    return editions


def covers_label(e: dict) -> str:
    """'4-10 July 2026', or a cross-month/cross-year form when the span straddles.
    Never derived from the ISO week, which describes the Friday anchor only."""
    s, t = e["start"], e["end"]
    if not (s and t):
        return e["date"]
    sy, sm, sd = int(s[:4]), int(s[5:7]), int(s[8:10])
    ty, tm, td = int(t[:4]), int(t[5:7]), int(t[8:10])
    if (sy, sm) == (ty, tm):
        return f"{sd}-{td} {MONTHS[tm]} {ty}"
    if sy == ty:
        return f"{sd} {MONTHS[sm]} to {td} {MONTHS[tm]} {ty}"
    return f"{sd} {MONTHS[sm]} {sy} to {td} {MONTHS[tm]} {ty}"


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build_block(editions: list[dict], current: dict) -> str:
    here = Path(current["file"]).parent
    years: dict[int, dict[int, list]] = {}
    for e in editions:
        years.setdefault(e["year"], {}).setdefault(e["month"], []).append(e)

    rows = []
    for y in sorted(years, reverse=True):
        y_has_current = any(e["slug"] == current["slug"]
                            for ms in years[y].values() for e in ms)
        n_y = sum(len(v) for v in years[y].values())
        months_html = []
        for mo in sorted(years[y], reverse=True):
            eds = years[y][mo]
            m_has_current = any(e["slug"] == current["slug"] for e in eds)
            items = []
            for e in eds:
                is_cur = e["slug"] == current["slug"]
                href = os.path.relpath(e["file"], here)
                # Everything the in-page filter matches against, lowercased once here
                # so the browser never has to normalise on every keystroke.
                hay = " ".join([e["title"], e["slug"], covers_label(e), e["terms"]]).lower()
                cls = "wn-ed is-current" if is_cur else "wn-ed"
                cur_attr = ' aria-current="page"' if is_cur else ""
                no = e["edition"] if e["edition"] is not None else "-"
                dur = f' · {esc(e["dur"])}' if e["dur"] else ""
                items.append(
                    f'<a class="{cls}" href="{esc(href)}" data-slug="{esc(e["slug"])}" '
                    f'data-hay="{esc(hay)}"{cur_attr}>'
                    f'<span class="wn-no">{esc(no)}</span>'
                    f'<span class="wn-body"><span class="wn-title">{esc(e["title"])}</span>'
                    f'<span class="wn-covers">{esc(covers_label(e))}{dur}</span></span></a>')
            months_html.append(
                f'<details class="wn-month" data-count="{len(eds)}"{" open" if m_has_current else ""}>'
                f'<summary><span class="wn-caret"></span><span class="wn-mname">{MONTHS[mo]}</span>'
                f'<span class="wn-count">{len(eds)}</span></summary>'
                f'<div class="wn-eds">{"".join(items)}</div></details>')
        rows.append(
            f'<details class="wn-year" data-count="{n_y}"{" open" if y_has_current else ""}>'
            f'<summary><span class="wn-caret"></span><span class="wn-yname">{y}</span>'
            f'<span class="wn-count">{n_y}</span></summary>'
            f'<div class="wn-months">{"".join(months_html)}</div></details>')

    tree = "".join(rows) or '<p class="wn-empty">No editions filed yet.</p>'
    mark = ('<svg viewBox="0 0 240 110" aria-hidden="true"><path d="M50 55 C50 18 92 18 120 55 '
            'C148 92 190 92 190 55 C190 18 148 18 120 55 C92 92 50 92 50 55 Z"/></svg>')

    return f"""{BEGIN}
<!-- Generated by Team Knowledge/scripts/weekly-reports-nav.py — do not hand-edit.
     Re-run the script after filing a new edition. -->
<style>
.wn-open{{position:fixed;top:18px;left:18px;z-index:120;width:44px;height:44px;display:flex;
  align-items:center;justify-content:center;gap:0;border:1px solid var(--hair);border-radius:50%;
  background:rgba(12,14,18,0.82);backdrop-filter:blur(8px);cursor:pointer;
  transition:opacity .18s,transform .18s,border-color .18s}}
.wn-open svg{{width:26px;height:12px;fill:none;stroke:var(--marker);stroke-width:9;
  stroke-linecap:round;stroke-linejoin:round}}
.wn-open:hover{{transform:scale(1.06);border-color:var(--marker-border)}}
body.wn-on .wn-open{{opacity:0;pointer-events:none;transform:scale(.9)}}
.wn-scrim{{position:fixed;inset:0;z-index:118;background:rgba(6,7,10,0.55);opacity:0;
  pointer-events:none;transition:opacity .22s}}
body.wn-on .wn-scrim{{opacity:1;pointer-events:auto}}
.wn{{position:fixed;top:0;left:0;bottom:0;z-index:119;width:318px;max-width:86vw;display:flex;
  flex-direction:column;background:var(--card);border-right:1px solid var(--hair);
  transform:translateX(-100%);transition:transform .26s cubic-bezier(.22,1,.36,1)}}
body.wn-on .wn{{transform:none}}
.wn-head{{padding:20px 18px 12px;border-bottom:1px solid var(--hair-sub);flex:0 0 auto}}
.wn-brand{{display:flex;align-items:center;justify-content:space-between;gap:10px}}
.wn-brand b{{font-family:'Bricolage Grotesque',sans-serif;font-weight:640;font-size:15px;
  letter-spacing:-.01em;color:var(--fg)}}
.wn-close{{width:28px;height:28px;border:1px solid var(--hair);border-radius:50%;background:none;
  color:var(--faint);cursor:pointer;font-size:15px;line-height:1;display:flex;align-items:center;
  justify-content:center}}
.wn-close:hover{{color:var(--fg);border-color:var(--marker-border)}}
.wn-sub{{margin-top:3px;font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;
  letter-spacing:.18em;text-transform:uppercase;color:var(--faint)}}
.wn-find{{margin-top:13px;position:relative}}
.wn-find input{{width:100%;padding:8px 26px 8px 10px;border:1px solid var(--hair);border-radius:7px;
  background:var(--deep);color:var(--fg);font:inherit;font-size:12.5px}}
.wn-find input:focus{{outline:none;border-color:var(--marker-border)}}
.wn-find input::placeholder{{color:var(--faint)}}
.wn-clear{{position:absolute;right:7px;top:50%;transform:translateY(-50%);border:0;background:none;
  color:var(--faint);cursor:pointer;font-size:14px;display:none}}
.wn-find.has-q .wn-clear{{display:block}}
.wn-hits{{margin-top:7px;font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--faint);min-height:11px}}
.wn-tree{{flex:1 1 auto;overflow-y:auto;padding:8px 10px 22px}}
.wn-tree::-webkit-scrollbar{{width:6px}}
.wn-tree::-webkit-scrollbar-thumb{{background:var(--hair-emp);border-radius:3px}}
.wn-year>summary,.wn-month>summary{{display:flex;align-items:center;gap:8px;cursor:pointer;
  list-style:none;padding:7px 8px;border-radius:6px;user-select:none}}
.wn-year>summary::-webkit-details-marker,.wn-month>summary::-webkit-details-marker{{display:none}}
.wn-year>summary:hover,.wn-month>summary:hover{{background:var(--raised)}}
.wn-caret{{width:0;height:0;border-left:4.5px solid var(--faint);border-top:3.5px solid transparent;
  border-bottom:3.5px solid transparent;transition:transform .16s;flex:0 0 auto}}
details[open]>summary .wn-caret{{transform:rotate(90deg)}}
.wn-yname{{font-family:'Bricolage Grotesque',sans-serif;font-weight:640;font-size:14px;color:var(--fg)}}
.wn-mname{{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--dim)}}
.wn-count{{margin-left:auto;font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:9px;
  color:var(--faint)}}
.wn-months{{padding-left:11px;border-left:1px solid var(--hair-sub);margin-left:12px}}
.wn-eds{{padding-left:11px;border-left:1px solid var(--hair-sub);margin-left:12px}}
.wn-ed{{display:flex;gap:9px;align-items:flex-start;padding:8px;border-radius:6px;
  text-decoration:none;color:inherit}}
.wn-ed:hover{{background:var(--raised)}}
.wn-ed.is-current{{background:var(--marker-soft);box-shadow:inset 2px 0 0 var(--marker)}}
.wn-no{{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:10px;color:var(--marker);
  flex:0 0 auto;padding-top:1px;min-width:16px}}
.wn-body{{display:flex;flex-direction:column;gap:2px;min-width:0}}
.wn-title{{font-size:12.5px;line-height:1.25;color:var(--dim)}}
.wn-ed.is-current .wn-title,.wn-ed:hover .wn-title{{color:var(--fg)}}
.wn-covers{{font-family:'Spline Sans Mono',ui-monospace,monospace;font-size:8.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--faint)}}
.wn-empty,.wn-none{{padding:14px 10px;font-size:12px;color:var(--faint)}}
.wn-none{{display:none}} .wn-tree.is-empty .wn-none{{display:block}}
[hidden]{{display:none !important}}
@media (prefers-reduced-motion:reduce){{.wn,.wn-scrim,.wn-open{{transition:none}}}}
@media print{{.wn,.wn-open,.wn-scrim{{display:none !important}}}}
</style>
<button class="wn-open" id="wnOpen" aria-label="Open the Week in Ink archive"
  aria-expanded="false" aria-controls="wnPanel">{mark}</button>
<div class="wn-scrim" id="wnScrim" hidden></div>
<nav class="wn" id="wnPanel" aria-label="Week in Ink archive" aria-hidden="true">
  <div class="wn-head">
    <div class="wn-brand"><b>The Week in Ink</b>
      <button class="wn-close" id="wnClose" aria-label="Close the archive">&#215;</button></div>
    <div class="wn-sub">Archive · {len(editions)} edition{"" if len(editions) == 1 else "s"}</div>
    <div class="wn-find" id="wnFind">
      <input type="search" id="wnQ" placeholder="Search the archive" autocomplete="off"
        aria-label="Search report content" aria-describedby="wnHits">
      <button class="wn-clear" id="wnClear" aria-label="Clear search">&#215;</button>
    </div>
    <div class="wn-hits" id="wnHits" role="status" aria-live="polite"></div>
  </div>
  <div class="wn-tree" id="wnTree">{tree}
    <p class="wn-none">Nothing matches that search.</p>
  </div>
</nav>
<script>
(function () {{
  var body = document.body, panel = document.getElementById('wnPanel');
  var openBtn = document.getElementById('wnOpen'), closeBtn = document.getElementById('wnClose');
  var scrim = document.getElementById('wnScrim'), tree = document.getElementById('wnTree');
  var q = document.getElementById('wnQ'), find = document.getElementById('wnFind');
  var clear = document.getElementById('wnClear'), hits = document.getElementById('wnHits');
  if (!panel) return;
  var eds = [].slice.call(tree.querySelectorAll('.wn-ed'));
  var groups = [].slice.call(tree.querySelectorAll('.wn-year, .wn-month'));

  function setOpen(on) {{
    body.classList.toggle('wn-on', on);
    panel.setAttribute('aria-hidden', on ? 'false' : 'true');
    openBtn.setAttribute('aria-expanded', on ? 'true' : 'false');
    scrim.hidden = !on;
    if (on) {{ setTimeout(function () {{ q.focus(); }}, 240); }} else {{ openBtn.focus(); }}
  }}
  openBtn.addEventListener('click', function () {{ setOpen(true); }});
  closeBtn.addEventListener('click', function () {{ setOpen(false); }});
  scrim.addEventListener('click', function () {{ setOpen(false); }});
  // This block is injected at the top of <body>, so this listener registers BEFORE
  // the deck's own keydown handler at the end of the document. That ordering is what
  // lets stopImmediatePropagation below actually suppress the deck: same event target
  // (document), so registration order decides. Do not move this block lower.
  var DECK_KEYS = ['ArrowRight', 'ArrowLeft', 'ArrowUp', 'ArrowDown',
                   'PageUp', 'PageDown', ' ', 'Home', 'End'];
  document.addEventListener('keydown', function (e) {{
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {{
      e.preventDefault(); setOpen(!body.classList.contains('wn-on')); return;
    }}
    if (!body.classList.contains('wn-on')) return;
    if (e.key === 'Escape') {{ setOpen(false); return; }}
    // While the drawer is open it owns navigation keys. Without this the deck turns
    // pages behind the scrim whenever focus sits on a fold control (<summary> is
    // focusable and is not covered by the deck's own input/button guard).
    if (DECK_KEYS.indexOf(e.key) !== -1 &&
        (panel.contains(e.target) || e.target === body || e.target === document)) {{
      e.stopImmediatePropagation();
    }}
  }});

  // Filter. Matches title + slug + covering dates + the edition's search_expansion
  // vocabulary, so a query behaves semantically without an embedding model.
  // Every term must appear somewhere in the haystack (AND), which keeps two-word
  // queries from returning the whole archive.
  var prior = null;
  function run() {{
    var raw = q.value.trim().toLowerCase();
    find.classList.toggle('has-q', raw.length > 0);
    var terms = raw.split(/\\s+/).filter(Boolean);
    if (!terms.length) {{
      eds.forEach(function (a) {{ a.hidden = false; }});
      groups.forEach(function (g) {{
        g.hidden = false;
        if (prior && prior.has(g)) {{ g.open = false; }}
      }});
      prior = null;
      tree.classList.remove('is-empty');
      hits.textContent = '';
      return;
    }}
    if (!prior) {{
      prior = new Set();
      groups.forEach(function (g) {{ if (!g.open) prior.add(g); }});
    }}
    var n = 0;
    eds.forEach(function (a) {{
      var hay = a.getAttribute('data-hay') || '';
      var ok = terms.every(function (t) {{ return hay.indexOf(t) !== -1; }});
      a.hidden = !ok;
      if (ok) n++;
    }});
    groups.forEach(function (g) {{
      var live = g.querySelectorAll('.wn-ed:not([hidden])').length;
      g.hidden = live === 0;
      if (live) g.open = true;
    }});
    tree.classList.toggle('is-empty', n === 0);
    hits.textContent = n + (n === 1 ? ' edition' : ' editions');
  }}
  q.addEventListener('input', run);
  clear.addEventListener('click', function () {{ q.value = ''; run(); q.focus(); }});
}})();
</script>
{END}"""


# --------------------------------------------------------------------------
def inject(path: Path, block: str) -> bool:
    html = path.read_text(encoding="utf-8")
    if BEGIN in html and END in html:
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: block,
                     html, flags=re.S)
    else:
        m = re.search(r'<body[^>]*>', html)
        if not m:
            print(f"  !! no <body> in {path}", file=sys.stderr)
            return False
        new = html[:m.end()] + "\n" + block + "\n" + html[m.end():]
    if new == html:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--check", action="store_true",
                    help="report staleness, write nothing, exit 1 if stale")
    a = ap.parse_args()

    root = Path(a.vault) / "PKM" / "Weekly Reports"
    if not root.exists():
        print(f"no weekly reports tree at {root}")
        return 0
    eds = collect(root)
    if not eds:
        print("no editions found")
        return 0
    print(f"{len(eds)} edition(s) in the manifest")

    stale = 0
    for e in eds:
        block = build_block(eds, e)
        p = Path(e["file"])
        if a.check:
            cur = p.read_text(encoding="utf-8")
            if BEGIN not in cur or block not in cur:
                print(f"  STALE  {e['slug']}")
                stale += 1
        elif inject(p, block):
            print(f"  wrote  {e['slug']}")
        else:
            print(f"  ok     {e['slug']}")
    if a.check and stale:
        print(f"{stale} report(s) stale — run without --check")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
