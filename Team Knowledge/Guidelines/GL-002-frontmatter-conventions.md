# GL-002 - Frontmatter Conventions

> **This Guideline is a general rule every agent reads on every relevant action.** Every entity note Penn captures, every entity Silas writes during an import, every frontmatter audit Silas runs — they all read this file. SOPs and Workstreams `[[wikilink]]` here rather than restating the schema.

This is the source of truth for the YAML frontmatter that sits at the top of every entity note in your myPKA. Every other file that needs to talk about field names `[[wikilinks]]` here.

Aligns with [[SOP-002-convert-mypka-to-sqlite]] (the SQLite migration contract). Field names in this Guideline match the column names that SOP-002 reads. Do not rename one without the other.

## Why this exists

Read this once, never again.

A note in your myPKA has two layers:

1. **Structured data** lives in YAML frontmatter at the top of the file. Names, dates, links, statuses, contact details. Anything that has a clear shape and the team will want to query.
2. **Narrative** lives in the body. How you met the person. Why the project matters. What you noticed. Anything that reads like prose.

The split is load-bearing for three reasons:

- The right-sidebar **Properties tab** in mypka-interface parses frontmatter and renders it as a typed key-value UI. No frontmatter, no Properties tab.
- The **SQLite migration** ([[SOP-002-convert-mypka-to-sqlite]]) reads frontmatter into typed columns. Inline body text like `**Email:** jane@example.com` migrates as zero structured data.
- New users (and new agents) need a predictable shape. If every note invents its own field names, search and automation collapse.

When in doubt, the rule is: structured fact goes in frontmatter, story goes in the body.

## Core rules

### 1. Frontmatter sits at the very top of the file

Open and close the block with three dashes on their own line:

```yaml
---
name: Jane Doe
role: Product Designer
---
```

Body content starts on the line after the closing `---`.

### 2. Field names are kebab-case-or-snake_case, never both

myPKA uses `snake_case` for frontmatter keys to match the SQLite column names in [[SOP-002-convert-mypka-to-sqlite]]. Do not mix conventions inside one file.

Good: `full_name`, `last_contact`, `target_date`.
Bad: `fullName`, `last-contact`, `Target Date`.

### 3. Typing rules

- **Strings** - quoted only when they contain special characters (colons, hashes, leading numbers). Plain text otherwise.
- **Dates** - always ISO `YYYY-MM-DD`. No timezones, no slashes, no month names. Cross-references [[GL-001-file-naming-conventions]] rule 2.
- **Datetimes** - ISO-8601 `YYYY-MM-DDTHH:MM:SSZ` when a wall-clock time matters. Otherwise prefer date.
- **Booleans** - `true` or `false`, lowercase.
- **Lists** - YAML array, one item per line, `-` prefix:
  ```yaml
  tags:
    - work
    - design
  ```
  Inline `[a, b, c]` is allowed for short lists but the multi-line form is preferred for readability.
- **Slugs and foreign keys** - kebab-case, matching the target file's stem exactly. See [[GL-001-file-naming-conventions]] rule 1.

### 4. Foreign-key fields store the slug, not the title

Locked decision: when one entity references another, the frontmatter field stores the **slug** of the target (the filename stem), and the UI resolves the slug to the target's `name` or `title` at render time.

```yaml
# In PKM/CRM/People/jane-doe.md
organization: acme-corp           # points to PKM/CRM/Organizations/acme-corp.md
```

Why slug not title: the slug is stable across renames inside frontmatter, the title is the field stored on the target file and may change. Storing the slug means a target rename (with file move) only needs to update one place.

The mypka-interface Properties tab renders the resolved title with the slug as a tooltip. The SQLite migration ([[SOP-002-convert-mypka-to-sqlite]]) resolves the slug to the FK integer at conversion time.

### 5. Required fields are minimal, optional fields are abundant

The team's bias: **require only what makes the note identifiable**. Every other field is optional and can be filled when the user has it.

Per entity, the required field is the one that names the thing:

| Entity | Required |
|---|---|
| Person | `full_name` |
| Organization | `name` |
| Project | `name` |
| Goal | `name`, `key_element` |
| Habit | `name` |
| Topic | `name` |
| Key Element | `name` |
| Document | `title` |

Everything else is optional. A note with three frontmatter fields is fine. A note with twenty is also fine. The shape stays consistent.

The one exception to "require only the name" is the **Goal**, which requires *both* `name` and `key_element`. A Goal that does not name the Key Element it serves is a target with no home domain - the **anchor rule** (see the Goals schema) makes `key_element` load-bearing, not optional.

### 6. Never invent ad-hoc fields

If you find yourself wanting a field that is not in this Guideline:

1. Check the entity schema below.
2. If the field is genuinely missing and you will use it more than once, edit this Guideline first. Add the field with its typing rule and any cross-references.
3. Then use it.

One-off `notes_jane_likes` style keys break the SQLite migration silently. Free-form notes go in the body.

## Entity schemas

These are the canonical fields per entity. Field names are case-sensitive and match the SQLite column names in [[SOP-002-convert-mypka-to-sqlite]].

### People - `PKM/CRM/People/<slug>.md`

```yaml
---
full_name: Jane Doe                        # required
first_name: Jane                           # optional, derived if absent
last_name: Doe                             # optional, derived if absent
relation: friend                           # colleague | friend | family | client | other
role: Product Designer
company: acme-corp                         # slug of an Organization
email: jane@example.com
phone: +1-415-555-0100                     # E.164 preferred
city: San Francisco
birth_date: 1990-03-14
linkedin_url: https://www.linkedin.com/in/janedoe
last_contact: 2026-05-09
tags:
  - work
  - design
---
```

Notes:
- `company` stores the slug of an Organization note. Per rule 4, the UI resolves it to the Organization's `name`.
- `relation` follows the SOP-002 convention: prefer one of `colleague`, `friend`, `family`, `client`, `other`. Free text accepted but limits queryability.
- Body section conventions: `## How we met`, `## Topics of common interest`, `## Notes`.

### Organizations - `PKM/CRM/Organizations/<slug>.md`

```yaml
---
name: Acme Corp                            # required
org_type: company                          # company | clinic | nonprofit | government | school | other
industry: software
website: https://www.acmecorp.example
email: hello@acmecorp.example
phone: +1-415-555-0199
city: San Francisco
tags:
  - vendor
---
```

Notes:
- `org_type` aligns with SOP-002's `organizations.type` column. The frontmatter key is `org_type` to avoid colliding with the YAML reserved-feeling word `type`.
- Body section conventions: `## What they do`, `## How we work together`, `## Notes`.

### The My Life model - buckets, the Goal layer, and the filter test

Before the per-entity schemas below, this is the doctrine that governs how the five My Life entities relate. The buckets are not interchangeable; each answers a different question about your life, and putting a thing in the wrong bucket is the most common way a myPKA goes stale.

**Four buckets:**

| Bucket | Question it answers | Time horizon | Example |
|---|---|---|---|
| **Key Element** | "What permanent domain of my life is this?" | Forever (until a life change) | Health, Work, Relationships, Money, Growth |
| **Project** | "What bounded outcome am I working toward, with an end?" | Weeks to months, then done | Ship the pricing page refresh |
| **Habit** | "What recurring behaviour do I repeat on a cadence?" | Ongoing, rhythm-based | Morning walk |
| **Topic** | "What subject do I keep thinking about and exploring?" | Open-ended exploration | Pricing strategy, French |

**Goals are an operating layer, not a fifth bucket.** A Goal is a measurable destination that sits *on top of* a Key Element and is *carried by* the work beneath it. A Goal does not live in its own conceptual silo - it always anchors to exactly one Key Element (the domain it belongs to) and is pursued through exactly one carrier (see the carrier doctrine below). "Lose 20 kg" is a Goal anchored to the `health` Key Element; it is not a domain, not a recurring behaviour, and not a subject of open exploration - it is a target.

**The filter test** - when you are unsure where a thing belongs, ask in order:

| If the thing is... | ...it is a |
|---|---|
| a permanent area of life that never "finishes" | **Key Element** |
| a measurable target with a finish line | **Goal** (anchored to a Key Element) |
| a bounded piece of work with a clear "done" | **Project** |
| a behaviour you repeat on a rhythm | **Habit** |
| a subject you keep returning to, still exploring | **Topic** |

The Goal layer is what makes the other four buckets cohere: Key Elements give a Goal its home, Projects and Habits give it forward motion, and Topics feed it context. Get the buckets right and the whole My Life graph queries cleanly.

### Projects - `PKM/My Life/Projects/<slug>.md`

```yaml
---
name: Ship the Pricing Page Refresh        # required
status: active                             # planning | active | paused | done | archived
target_date: 2026-07-15
key_element: work                          # slug of a Key Element
linked_goals:
  - hit-50-mrr-by-q3
linked_topics:
  - pricing-strategy
linked_people:
  - jane-doe
tags:
  - marketing
---
```

Notes:
- `status` enum is the team default. Use one of the listed values for queryability; free text is parsed but not categorized.
- `key_element`, `linked_goals`, `linked_topics`, `linked_people` all store slugs per rule 4.
- `linked_goals` is the **Project side of the carrier doctrine**: a Project is one of the two sibling carriers that can move a Goal forward (the other is a Habit). A Goal listed here is one this Project is the engine for. See the Goals schema.
- `linked_topics` records the **Topics that seeded or feed this Project** - the "open question I decided to actually solve" move. When an Open Question in a Topic graduates into work, the Topic is listed here and the Topic itself *stays* a Topic (still exploring). This is distinct from a Topic graduating into a Key Element (see the Topics schema).
- Body section conventions: `## Why this matters`, `## Status update`, `## Open threads`, `## Next steps`.

### Goals - `PKM/My Life/Goals/<slug>.md`

```yaml
---
name: Hit $50K MRR by Q3                   # required
status: active                             # planning | active | paused | done | abandoned
target_date: 2026-09-30
key_element: work                          # required - slug of a KEY ELEMENT only (the anchor rule)
linked_projects:
  - ship-pricing-refresh                   # carrier: a Project (use this OR linked_habits, not both)
linked_habits:                             # carrier: a Habit (the sibling alternative)
linked_topics:                             # optional - Topics this Goal draws context from
tags:
  - revenue
---
```

Notes:
- **`key_element` is REQUIRED on every Goal, and it must be the slug of a Key Element - never a Project, never a Topic.** This is the **anchor rule**: a Goal always belongs to exactly one permanent domain of life. A target with no home domain is a target that drifts. (See rule 5 - the required-fields table lists `name` *and* `key_element` for Goals.)
- **The carrier doctrine.** A Goal is *carried* by exactly **one** of two siblings: a **Project** (via `linked_projects`) **or** a **Habit** (via `linked_habits`) - never both, and **never a Topic**. There is no third shape. A Project is the right carrier when the Goal is a bounded outcome ("ship X"); a Habit is the right carrier when the Goal is reached by repeated behaviour ("walk every morning"). A Topic only ever *feeds context* (`linked_topics`); it cannot carry a Goal because exploration has no finish line.
  - Canonical example: the Goal **"lose 20 kg"** anchors to the `health` Key Element (`key_element: health`) and is carried by **one** carrier - either a Project (`linked_projects: [cut-to-race-weight]`) if it is a bounded push, **or** a Habit (`linked_habits: [daily-calorie-deficit]`) if it is reached by a sustained routine. One carrier, never two.
- `linked_projects`, `linked_habits`, `linked_topics`, and `key_element` all store slugs per rule 4. The carrier relationship is mirrored from the other side: a Project lists this Goal in its `linked_goals`, a Habit lists it in its `linked_goals`.
- Body section conventions: `## Why this matters`, `## Definition of done`, `## Progress notes`.

### Habits - `PKM/My Life/Habits/<slug>.md`

```yaml
---
name: Morning Walk                         # required
cadence: daily                             # daily | weekdays | weekly | monthly | adhoc
status: active                             # active | paused | abandoned
started_on: 2026-04-01
key_element: health                        # slug of a Key Element
linked_goals:                              # carrier doctrine - Goals this Habit moves forward
  - lose-20-kg
tags:
  - health
---
```

Notes:
- `cadence` is the rhythm; `status` is whether you are currently doing it.
- `linked_goals` is the **Habit side of the carrier doctrine**: a Habit is one of the two sibling carriers that can move a Goal forward (the other is a Project). When a Goal is reached through sustained repetition - the canonical example "lose 20 kg" pursued via a daily routine - the Goal lists this Habit in its `linked_habits`, and the Habit lists the Goal here. Stores slugs per rule 4. A Habit may be the carrier for more than one Goal, but each Goal is carried by only one carrier.
- Streak tracking is a body-level concern (or an extension), not a frontmatter field. Frontmatter holds the definition, not the daily log.
- Body section conventions: `## Why this habit`, `## What it looks like`, `## Reflection`.

### Topics - `PKM/My Life/Topics/<slug>.md`

```yaml
---
name: Pricing Strategy                     # required
key_element: work                          # slug of a Key Element
parent_topic: business-strategy            # optional, slug of a parent Topic
lifecycle: exploring                       # exploring | promoted | dormant (default exploring)
promoted_to:                               # Key-Element slug, set ONLY when lifecycle: promoted
tags:
  - strategy
---
```

Notes:
- A Topic is a recurring subject of thought - lighter than a Project, broader than a single Document.
- Topics can nest via `parent_topic` to a single parent. Multi-parent is not supported - keep the tree clean.
- **`lifecycle`** tracks where a Topic sits in its arc: `exploring` (the default - an active subject of thought), `promoted` (it has graduated into a permanent Key Element - see below), or `dormant` (you have stopped returning to it but want to keep the note).
- **Topic → Key Element graduation (the `promoted_to` field).** A Topic that keeps growing in importance can become a permanent domain of life - a Key Element. When that happens, set `lifecycle: promoted` and `promoted_to: <key-element-slug>` pointing at the new Key Element note (whose `promoted_from` points back here - see the Key Elements schema). This is the Topic *itself* becoming a permanent area of life.
  - Canonical example: **"French."** It starts as a Topic - a subject you keep returning to, still exploring. The day it becomes a sustained, measurable pursuit with its own permanent place in your life, it graduates: the Topic gets `lifecycle: promoted`, `promoted_to: language-learning` (or a dedicated `french` Key Element), and a Goal like "reach B2 French by year-end" can then anchor to that Key Element with a carrier beneath it.
- **Do not confuse graduation with the Open-Question → Project move.** Promotion is the Topic becoming a *Key Element*. The Open-Question → Project move is different: there, you decide to *solve* one open question from the Topic, you spin up a Project, the Project records the Topic in its `linked_topics`, and the **Topic stays `exploring`** - it is feeding a Project, not retiring into a domain. One Topic can feed many Projects over its life and still never be promoted.
- Body section conventions: `## What I think about here`, `## Open questions`, `## Graduation`, `## Sources`.

### Key Elements - `PKM/My Life/Key Elements/<slug>.md`

```yaml
---
name: Work                                 # required
description_short: My professional life and the businesses I run
status: active                             # active | dormant | archived
promoted_from:                             # optional - Topic slug this Key Element graduated from
tags:
  - life
---
```

Notes:
- Key Elements are the top-level domains of life (Work, Health, Relationships, Money, Growth, etc.). There are typically 5 to 9 per user.
- Other entities point to a Key Element via the `key_element` field on Projects, Goals, Habits, and Topics.
- **`status`** now includes `archived` alongside `active` and `dormant`. `archived` is the reverse of promotion - a domain that has *left* your life (a career you closed, a chapter that ended). `dormant` is a domain that is quiet but still yours; `archived` is one you have let go.
- **`promoted_from`** is the reverse pointer of a Topic's `promoted_to`. When a Topic graduates into this Key Element (see the Topics schema - the "French" example), set `promoted_from: <topic-slug>` so the lineage is queryable from both ends. Left blank for Key Elements that were domains from day one.
- Body section conventions: `## What this covers`, `## What good looks like`, `## What I am ignoring`.

### Documents - `PKM/Documents/<slug>.md`

```yaml
---
title: Apartment Lease 2026                # required
doc_type: contract                         # contract | id | invoice | warranty | medical | tax | other
physical_location: top drawer of the desk
digital_location: Dropbox/Legal/2026-lease.pdf
issued_on: 2026-01-15
expiry_date: 2027-01-14
renewal_trigger: 2026-11-15                # date to act, not the document's own deadline
linked_people:
  - jane-doe                               # tenant, landlord, etc.
linked_organizations:
  - acme-property-management
tags:
  - housing
---
```

Notes:
- `title` is the field, not `name` - aligns with SOP-002's `documents.title` column.
- `physical_location` and `digital_location` are independent. A document can have both, either, or neither.
- `renewal_trigger` is the date you want to be reminded to act. The actual `expiry_date` may be later.
- Body section conventions: `## Summary`, `## Key terms`, `## Notes`.

### Weekly reports (`type: weekly-report`) - `PKM/Weekly Reports/YYYY/MM/<slug>/metadata.md`

One edition of **The Week in Ink**, the Friday weekly recap. The folder is the unit: `metadata.md` carries this schema plus a markdown mirror of the week, and sits next to the rendered deck. An edition is **assembled from captured sources**, never authored from memory, so the frontmatter is largely a provenance record. See [[PKM/Weekly Reports/INDEX]] for the production scripts.

```yaml
---
type: weekly-report                                 # required, always literally 'weekly-report'
report_date: 2026-07-10                             # required - ISO YYYY-MM-DD, the FRIDAY anchor, natural key
slug: 2026-07-10-week-in-ink-28                     # required - matches the folder name
edition: 28                                         # integer, monotonic edition number
week_start: 2026-07-04                              # first day covered (inclusive)
week_end: 2026-07-10                                # last day covered (inclusive; equals report_date)
iso_week: 2026-W28                                  # ISO week of the ANCHOR - see the warning below
title: "It Has Two Souls"                           # the edition headline
status: published                                   # draft | published | archived
html_render: the-week-in-ink-2026-07-10.html        # bare filename of the deck inside the folder
podcast_path: ""                                    # folder-relative path to episode audio, or "" for none
podcast_duration: ""                                # mm:ss, or ""
source_journal_entries: []                          # Journal slugs the edition was gathered from
source_images: []                                   # PKM/Images filenames behind any renditions/
pivotal_moments: []                                 # Journal slugs of the week's turning points
search_expansion: []                                # offline-search vocabulary (see notes)
specialists: []                                     # contributing specialist slugs
tags:
  - weekly-report
  - week-in-ink
---
```

**Required fields:** `type` (always literally `weekly-report`), `report_date`, `slug`.

**Notes:**

- **`iso_week` describes the anchor, NOT the covered span.** An edition is anchored on a Friday but opens the preceding Saturday, which can fall in the previous ISO week: edition 28 is labelled `2026-W28` yet covers 2026-07-04, a Saturday in ISO week 27. Always render and query the explicit `week_start` to `week_end` range. The week number alone is ambiguous to a reader and wrong to parse.
- `report_date` is the Friday anchor and the natural key (one edition per week). `week_end` equals it by contract.
- `edition` is monotonic and is not derivable from the date if the series predates the automation, so it is stored.
- `html_render` is a **bare filename** inside the edition folder. `podcast_path` is **folder-relative**, because original media lives in its canonical PKM home rather than in the edition folder (see the media rule below).
- **Media placement (SSOT).** Original media produced for an edition lives in `PKM/Audio/YYYY/MM/` or `PKM/Videos/YYYY/MM/`, and recurring brand assets under `Team Knowledge/Brand Assets/`. The edition references them by relative path. The single exception is a `renditions/` folder inside the edition, holding downscaled or format-converted derivatives of `PKM/Images` originals, because browsers cannot render `.heic` and full-resolution originals are far heavier than needed. Renditions are regenerable derivatives, not a competing source of truth, and each must be traceable through `source_images`.
- `source_journal_entries`, `source_images` and `pivotal_moments` are the provenance chain. They make an edition reproducible and let the mirror answer "which week covered this entry".
- `search_expansion` is the offline-search vocabulary (topics, synonyms, entities, questions the edition answers) written so a plain keyword match behaves semantically. It backs the in-page filter in the archive drawer, which cannot reach an embedding model from a `file://` page.
- **Body convention:** the markdown body is a real prose mirror of the week, day by day, not a description of the deck. It is the searchable artefact; a body full of section scaffolding makes the edition unfindable.
- **Indexing:** the regen walks `PKM/Weekly Reports/**/metadata.md` into the `weekly_reports` table, skipping any path component beginning with `_` (so `_template/` and `_assets/` never land as phantom editions) and any `report_date` that is not a real `YYYY-MM-DD`. Markdown is canonical; the table is derived.

## Specialist-contract frontmatter

The schemas above govern PKM **entity notes**. Specialist **contracts** carry their own small set of frontmatter keys (`agent_version`, `agent_status`, `owner`, etc.). This section documents one optional contract-level field that is part of the v4 tool-agnostic core: `model`.

### `model` - optional

| Property | Value |
|---|---|
| Field name | `model` |
| Required? | **Optional.** Omit to inherit the session/harness default. |
| Applies to | Specialist contracts (`Team/<Name> - <Role>/AGENTS.md` frontmatter) and their host shims (`.claude/agents/<slug>.md`). |
| Type | Portable tier alias - one of `reasoning`, `balanced`, `fast`. An explicit `provider/model-id` string is also accepted (escape hatch, discouraged - see below). |

**Default is omit-to-inherit.** When `model` is absent, the specialist runs on whatever model the session or harness has selected. Most specialists should leave it unset. Set it only when a specialist's work has a clear, stable tier need.

**The value is a portable tier alias, not a concrete model name.** The contract stays provider-neutral; the harness adapter resolves the alias to a real model.

| Alias | Meaning | Use for |
|---|---|---|
| `reasoning` | Deepest reasoning, highest capability | Architect-grade work: schema design, security audits, multi-step planning. |
| `balanced` | The default specialist tier | Most specialist work. Good capability at sensible cost. |
| `fast` | Cheapest, highest-throughput | High-volume, low-judgment work: bulk formatting, simple extraction, triage fan-out. |

**The adapter owns alias-to-model resolution, not the contract.** A harness adapter maps each alias to a concrete model for that provider. For example, a Claude Code adapter maps `reasoning` to an Opus-class model, `balanced` to Sonnet, and `fast` to Haiku, and writes the resolved value into the host shim. The portable contract never names the concrete model; only the generated shim does. This keeps one contract runnable across any provider.

**OpenRouter is the supported BYO-key router.** A member who routes through OpenRouter supplies their own OpenRouter key and points the harness at OpenRouter's Anthropic-compatible endpoint via the `ANTHROPIC_BASE_URL` environment variable. The alias-to-slug mapping for OpenRouter (e.g. which OpenRouter model slug `balanced` resolves to) lives in the adapter and the member's harness config, never in the contract. BYO key, member's own account - this is the supported path.

**Escape hatch: explicit `provider/model-id` is permitted but flagged.** You may pin a concrete model with an explicit `provider/model-id` string (e.g. `anthropic/claude-opus-4`). The agnosticism-audit in `validation-script.sh` flags any such value as a **coupling warning**, because it pins a provider into the portable core and breaks the run-anywhere contract. Prefer the alias form. Reach for the explicit string only when a specialist genuinely depends on one specific model's behavior, and accept the warning as the documented record of that coupling.

> **ToS INVARIANT (Lex).** If `model` resolves to an Anthropic model **and our own code makes the call** (not a first-party Anthropic client such as the Claude apps or Claude Code itself), that call MUST authenticate with an Anthropic API key, AWS Bedrock, or Google Vertex - **never** a subscription OAuth token. Never reuse `~/.claude/.credentials.json` or any subscription-session credential for programmatic calls. Routing the same call via OpenRouter is fine because it uses the member's own OpenRouter key (BYO). This invariant is non-negotiable and is enforced (co-owned with Vex) by the agnosticism-audit, which hard-fails on any reference to `~/.claude/.credentials.json` or OAuth-token reuse in the portable core.

## How to extend this Guideline

Your myPKA grows. New fields will surface. Two acceptable extension paths:

1. **Add a new optional field to an existing entity.** Edit the entity's schema above. Add the field with its typing rule. Commit. The SQLite migration in [[SOP-002-convert-mypka-to-sqlite]] will pick up new optional columns gracefully (they default to `NULL` for older notes).

2. **Add a new entity type.** Higher cost. Requires a new folder under `PKM/`, a new schema in this Guideline, a new section in [[SOP-002-convert-mypka-to-sqlite]], and a new template in [[Templates/INDEX]]. Do not do this casually.

Two rules that apply to both paths:

- **Pick one, document, never invent ad-hoc.** If two notes use different field names for the same thing, search and migration both rot.
- **Never rename a field without the SOP.** A rename here without a matching update in [[SOP-002-convert-mypka-to-sqlite]] silently breaks the SQLite migration. Coordinate the change.

## Cross-references

- [[GL-001-file-naming-conventions]] - slug rules, ISO date format, filename patterns.
- [[SOP-002-convert-mypka-to-sqlite]] - the SQLite migration contract. This Guideline's field names match SOP-002's column names.
- [[Templates/INDEX]] - copy-and-edit starter templates for every entity type defined here.

## Updates to this Guideline

If the rules change, update this file. Do not duplicate the change into SOPs, Workstreams, or templates. They `[[wikilink]]` here and inherit the change automatically.

### Version history

- **v2.5** - Added the **Weekly reports** entity schema (`type: weekly-report`, `PKM/Weekly Reports/YYYY/MM/<slug>/metadata.md`) for The Week in Ink, the Friday weekly recap. One folder per edition; `metadata.md` carries the provenance frontmatter plus a prose mirror of the week, next to the rendered deck. Documents the anchor-versus-span trap (`iso_week` describes the Friday anchor, not the covered days, so coverage is queried via `week_start`/`week_end`), the media SSOT rule (originals stay in `PKM/Audio` / `PKM/Videos` / Brand Assets and are referenced; only regenerable image `renditions/` sit inside the edition), and the body convention (a real day-by-day mirror, because the body is the searchable artefact). Mirrored by the new `weekly_reports` table in the cockpit regen. Additive and backward-compatible - no existing note changes.
- **v2.4** - Added the **`model`** optional contract-level field (new section "Specialist-contract frontmatter"). `model` applies to specialist contracts (`Team/<Name> - <Role>/AGENTS.md`) and their `.claude/agents/<slug>.md` shims, not to PKM entity notes. Value is a portable tier alias (`reasoning` | `balanced` | `fast`); omit to inherit the session/harness default. The harness adapter resolves the alias to a concrete model (e.g. Claude Code maps `reasoning`/`balanced`/`fast` to Opus/Sonnet/Haiku in the shim); the contract stays provider-neutral. An explicit `provider/model-id` string is permitted but flagged by the agnosticism-audit as a coupling warning. OpenRouter documented as the supported BYO-key router (Anthropic-compatible endpoint via `ANTHROPIC_BASE_URL`), with alias-to-slug resolution living in the adapter. Added Lex's ToS INVARIANT: an Anthropic-resolved `model` called by our own code must use an API key / Bedrock / Vertex, never a subscription OAuth token, and never `~/.claude/.credentials.json` (co-enforced with Vex by the agnosticism-audit). Additive and backward-compatible - contracts without `model` stay valid and inherit the default.
- **v2.3** - My Life model encoded as a first-class schema concept. Added the intro section "The My Life model - buckets, the Goal layer, and the filter test" (four buckets: Key Element = permanent, Project = bounded, Habit = cadenced, Topic = exploration; Goals as an operating layer, not a fifth bucket; a filter-test table for correct placement). **Goal** `key_element` is now REQUIRED and constrained to Key-Element slugs only (the anchor rule; rule-5 required-fields table updated to `name, key_element`); added the **carrier doctrine** (a Goal is carried by exactly one of two siblings - a Project via `linked_projects` OR a Habit via `linked_habits`, never both, never a Topic, no third shape) and `linked_topics` (context only). **Topic** gains `lifecycle` (exploring | promoted | dormant) + `promoted_to` (Key-Element slug) to encode Topic → Key Element graduation as first-class, and the prose now distinguishes graduation from the Open-Question → Project move. **Key Element** gains `promoted_from` (reverse of Topic `promoted_to`) and an `archived` status (the reverse transition - a domain leaving the life). **Habit** gains `linked_goals` (the Habit side of the carrier doctrine). **Project** schema formalized `linked_topics` and documented `linked_goals` as the Project side of the carrier doctrine. All changes additive and backward-compatible - notes without the new fields stay valid; the SQLite migration picks up new optional columns as NULL. Authored under §"Never invent ad-hoc fields" and §"How to extend" path 1. The four My Life templates (goal, topic, key-element, habit) were updated in the same change.
