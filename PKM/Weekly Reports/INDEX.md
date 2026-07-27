# Weekly Reports - Archive

The permanent home for **The Week in Ink**, your Friday weekly recap. `Deliverables/` is a working surface that gets swept at close; weekly reports are the durable record of what a week actually contained, so every edition is filed here where it is never lost. Date-nested time-series shape (`YYYY/MM/<slug>/`), same as [[PKM/Journal]] and [[PKM/Images]]. Each edition folder holds `metadata.md` (the markdown SSOT + frontmatter per [[GL-002-frontmatter-conventions]]) plus the rendered deck. The `_template/` folder carries the reusable frontmatter schema; the deck stylesheet, engine and fonts live in `Team Knowledge/scripts/weekly-report-assets/` (a framework path, so they receive updates).

## What an edition is

An edition answers "what actually happened this week and what did it mean". It is **assembled, never invented**: every line traces to something already captured, a [[PKM/Journal]] entry, a [[PKM/Images]] capture, a `Deliverables/` folder or a session log. That gather is the whole point of the format. The recap is not written from memory, it is built from what you already wrote down.

If a week has no journal entries and no images, the edition says so and renders a work-only record rather than padding seven pages with inference. A thin honest edition beats a fabricated recap of your own life.

## How to produce one

Three scripts in `Team Knowledge/scripts/`, run in order:

```
python3 "Team Knowledge/scripts/weekly-report-gather.py" <friday> --outdir /tmp/wk
python3 "Team Knowledge/scripts/weekly-report-render.py" /tmp/wk/<friday>.json
python3 "Team Knowledge/scripts/weekly-reports-nav.py"
```

`gather` collects the covered week into a JSON bundle and reports its density. `render` turns the bundle into `metadata.md` plus an eight-slide deck. `nav` injects the foldable archive drawer into every edition, so any edition is a complete entry point to the whole archive. Re-run `nav` after filing a new edition; `--check` reports staleness without writing, which suits a pre-publish gate.

`gather --range <from> <to>` walks every Friday in a span, which is how you backfill.

## Reading an edition

Open the rendered HTML. Arrow keys, the on-screen arrows, the page dots or the edge zones turn pages; `Escape` closes the image lightbox. The mark at top left opens the archive drawer, which groups every edition by year then month and filters as you type. The filter searches each edition's title, covering dates and its `search_expansion` vocabulary, so a content word finds the right week even when it is not in the title.

## Week numbering

Editions are numbered by the ISO week of their **Friday anchor**, but the covered span opens the preceding Saturday and can therefore begin in the previous ISO week. Always read the explicit `week_start` to `week_end` range, which every rendered deck shows in its running head. The week number alone is ambiguous. The same rule applies in the mirror: query coverage with `week_start` / `week_end`, never by parsing `iso_week`.

## Media rule (SSOT)

Original media produced for an edition lives in its canonical PKM home and is referenced by relative path, never copied into the edition folder: episode audio in `PKM/Audio/YYYY/MM/`, video in `PKM/Videos/YYYY/MM/`, recurring brand audio under `Team Knowledge/Brand Assets/`. The single exception is a `renditions/` folder inside the edition, which holds downscaled and format-converted derivatives of `PKM/Images` originals, because browsers cannot render `.heic` and full-resolution originals are several times the needed weight. Renditions are regenerable derivatives, not a second source of truth, and every one is traced in the edition's `source_images`.

## Hand-authored editions

Dropping a file named `.hand-built` into an edition folder makes the renderer refresh that edition's `metadata.md` but never overwrite its HTML, even with `--force`. Use it for any edition you have authored or extended by hand.

## Running index

Add a row per edition as you file it.

| Edition | Anchor | Covers | Title | Density |
|---|---|---|---|---|
| - | - | - | *no editions filed yet* | - |

## In the mirror

The regen walks `PKM/Weekly Reports/**/metadata.md` into the `weekly_reports` table (one row per edition). Markdown is canonical; the table is derived and rebuilt on every run.
