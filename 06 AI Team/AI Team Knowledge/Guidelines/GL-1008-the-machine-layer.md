---
type: guideline
id: GL-1008
title: The machine layer - what lives in .icor-for-life
created: 2026-09-09
uses: ["[[GL-1005-code-vs-instructions]]", "[[GL-1006-bases-and-live-views]]"]
---

# GL-1008 The machine layer: what lives in `.icor-for-life`

`.icor-for-life/` is the one hidden folder every ICOR for Life plugin and
every vault script uses for data that another plugin or script reads.
Obsidian does not show, index or search a folder whose name starts with a
dot, so nothing in it is ever a note. This guideline rules what goes in,
what stays out, and how a plugin reaches it.

## The layout

| Path | Written by | Read by |
| --- | --- | --- |
| `VERSION`, `manifest.json`, `CHANGELOG.md`, `README.md` | the scaffold's own release (see `.icor-for-life/README.md`) | Scaffold Check; people read the README and the changelog |
| `<plugin-id>/` | that one plugin, the id exactly as in its `manifest.json`, for example `icor-for-life-scaffold-check/` | that plugin, and any other plugin through a documented file |
| `scripts/` | the vault's Python scripts, for plugins | plugins |

The first file under `scripts/` is `quality.json`: a quality script the
team is building writes it, Scaffold Check reads it and shows it. Its
shape is versioned with a top-level `schema` integer; the fields are not
fixed yet and are documented with the script when it lands.

Two examples of what a `<plugin-id>/` subfolder holds:

- `<plugin-id>/runs/<id>/<ISO stamp>.json`, `schema: 1`: one record per AI
  run the plugin made (model, duration, the raw structured output, the
  verification verdicts, token usage). Run history, which this guideline
  names as machine-layer state rather than a setting. Deleting it loses no
  knowledge: what the run produced is in the note.
- `<plugin-id>/models/`: downloaded weights or other large artifacts,
  fetched on the member's click and re-fetchable at any time.

Neither is ever a note, and neither is ever the only copy of anything. A
file the member brought in is the opposite case and stays in the Assets (`concept:assets`):
it is a source, nothing regenerates it, and the membership test below
refuses it.

## The membership test (one sentence)

> A file belongs in `.icor-for-life/` only if something regenerates it.

So, never:

- **A source.** Anything a person typed, or the only copy of anything.
  Delete the whole folder except the four scaffold files and nothing is
  lost that one run of the writer does not bring back.
- **A user setting.** Settings stay in `.obsidian/plugins/<id>/data.json`,
  where Obsidian keeps them. State that changes on every run (the last
  result, a run history) is not a setting and belongs here, not there.
- **Anything a person reads.** People read notes. A human report is a
  note in a room (Scaffold Check writes its report under
  `06 AI Team/AI Team Knowledge/Scaffold Check/`), and a dashboard renders
  from the JSON. This is [[GL-1006-bases-and-live-views|GL-1006]] again:
  the file is data, the note or the view is what a person sees.

## Access, for plugin authors

- Obsidian's `Vault` API sees only the files visible in the app; a hidden
  folder is reached through the adapter only. Use `this.app.vault.adapter`
  (`exists`, `read`, `write`, `mkdir`, `list`) with `normalizePath` on
  every path. No `fs`, no `path`: the adapter is the same call on desktop
  and on mobile.
- Never assume the folder exists. A vault built by hand, or one that
  arrived on a second device through Obsidian Sync, may not have it.
  Every write starts with `exists` and `mkdir` of your own subfolder.
- Write only inside your own `<plugin-id>/` subfolder. `scripts/` belongs
  to the scripts.
- Read another plugin's subfolder, or `scripts/`, only through a file that
  is documented and carries a top-level `schema` integer. Check `schema`
  before trusting a field. A missing file means "not run yet", never an
  error.
- No vault event fires for a file in a hidden folder. Read the file when
  you need it (on run, when a view opens); do not wait to be told.

## Sync and git

Obsidian Sync excludes files and folders beginning with a dot, and
`.obsidian` is the only exception. So the layer is per device: every file
in it must be rebuildable by the thing that writes it, on any device,
from nothing. Other sync tools (iCloud Drive, git, Dropbox) do carry it,
so a plugin must also cope with a file written on another machine.

In git the whole folder is ignored, except `VERSION`, `manifest.json`,
`CHANGELOG.md` and `README.md`, which describe the scaffold version and
ship with it. Nothing a plugin or a script writes is ever tracked or
shipped.

## Mobile

Same rules. The adapter on mobile (`CapacitorAdapter`) implements the
same interface as on desktop, so `exists`, `read`, `write`, `mkdir` and
`list` work unchanged. What differs is presence: on a phone that got the
vault through Obsidian Sync the folder is not there until a plugin
creates it, which is why every write starts with `exists` and `mkdir`.
