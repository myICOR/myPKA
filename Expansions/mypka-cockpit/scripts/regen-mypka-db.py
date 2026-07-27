#!/usr/bin/env python3
"""regen-mypka-db.py — generate (or refresh) the SQLite mirror the myPKA Cockpit reads.

WHAT THIS DOES
  Scans the markdown myPKA this Expansion is installed in and rebuilds the
  cockpit's tables inside mypka.db at the myPKA root. The markdown stays the
  source of truth — the .db is a derived, regenerable layer. Run this again
  any time your notes change.

WHAT IT WILL NEVER DO
  * It never modifies, moves, or deletes any markdown file (the vault is
    opened read-only by construction: this script only ever reads .md files).
  * It never drops or alters a table it does not own. If your mypka.db already
    carries other tables (from a different mirror script, an analytics layer,
    an import), those are left byte-for-byte untouched. Only the tables listed
    in OWNED_TABLES below are dropped and rebuilt.

REQUIREMENTS
  Python 3.9+ and PyYAML (pip3 install --user pyyaml). Nothing else. No
  network access, no external services.

USAGE
  python3 "Expansions/mypka-cockpit/scripts/regen-mypka-db.py"
  (Run from anywhere — the script finds the myPKA root from its own location.)

SCHEMA
  The full table/column contract lives in ../docs/db-contract.md. Folders map
  to tables per the myPKA scaffold conventions (GL-001/GL-002):

    PKM/CRM/People/             -> people
    PKM/CRM/Organizations/      -> organizations
    PKM/My Life/Topics/         -> topics
    PKM/My Life/Projects/       -> projects
    PKM/My Life/Key Elements/   -> key_elements
    PKM/My Life/Goals/          -> goals
    PKM/My Life/Habits/         -> habits
    PKM/Documents/              -> documents
    PKM/Quotes/                 -> quotes (md-first, doc_type: quote)
    PKM/Outer World/YYYY/MM/    -> outer_world (md-first, doc_type: outer-world)
    PKM/My Life/Recipes/        -> recipes  (library; doc_type: recipe)
    PKM/My Life/Movies/         -> movies   (library; doc_type: movie)
    (any PKM/<Library>/         -> a mirror table, per the LIBRARIES config block)
    PKM/Journal/YYYY/MM/        -> journal (+ journal_media from ## Media)
    Deliverables/               -> deliverables
    Team Knowledge/Workstreams/ -> workstreams (header-bullet metadata, no YAML fm)
    Team Knowledge/SOPs/        -> sops        (header-bullet metadata, no YAML fm)
    Team Knowledge/Guidelines/  -> guidelines  (header-bullet metadata, no YAML fm)
    Team/<Name - Role>/         -> agents
    [[wikilinks]] in any body   -> links
    (titles + bodies, all above) -> notes_fts (FTS5 global search; see DATA-CONTRACT §13)

  PKM/Fleeting Notes/ is DELIBERATELY not indexed: fleeting notes are
  free-form capture/WIP docs outside the curated knowledge graph (the cockpit
  reads them straight from disk instead). Never add it here.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "PyYAML is required to parse note frontmatter.\n"
        "Install it with:  pip3 install --user pyyaml\n"
        "then re-run this script."
    )

# The script lives at <root>/Expansions/mypka-cockpit/scripts/regen-mypka-db.py
ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "mypka.db"

# Tables this script owns: dropped + rebuilt on every run. NOTHING ELSE in the
# .db file is touched.
OWNED_TABLES = [
    "people", "organizations", "topics", "projects", "goals",
    "key_elements", "habits", "documents", "deliverables",
    "journal", "journal_media", "agents", "agent_journal", "session_logs",
    "weekly_reports", "links", "meta",
    "transactions", "quotes", "outer_world",
    # Governance docs (item: cockpit Team-Knowledge browser). One table per family,
    # indexed from Team Knowledge/Workstreams|SOPs|Guidelines. Their metadata lives
    # in a `- **Label:** value` bullet block under the H1 (NOT YAML frontmatter), so
    # the regen parses that header block instead of fm. See the governance-docs pass
    # in main() and the header_block_fields() helper.
    "workstreams", "sops", "guidelines",
    # Library foundation (07-library-foundation.sql): the registry + the two
    # built-in libraries. A user-added library's table name (from LIBRARIES below)
    # is appended at runtime so the regen rebuilds it each run — see main().
    "library_registry", "recipes", "movies",
    # Global full-text search (item-8): the FTS5 virtual table over the searchable
    # corpus (titles + bodies of every entity/library/journal/deliverable). Standalone
    # (own-content) FTS5 — dropped + rebuilt each run like any owned table. See the
    # notes_fts CREATE in SCHEMA and the populate pass in main().
    "notes_fts",
]

# Views this script owns: dropped + rebuilt on every run alongside the tables, so
# they can never go stale against the data they read. Same rule as OWNED_TABLES —
# any OTHER view in the file (a different mirror, an analytics layer) is preserved.
OWNED_VIEWS = [
    "v_open_invoices", "v_reimbursement_pending", "v_invoice_payment_trail",
]

# Entity folders -> (table, title column). Missing folders are skipped quietly
# (the table is still created, just empty) so a leaner scaffold never errors.
ENTITY_FOLDERS = {
    "people":        (Path("PKM/CRM/People"), "full_name"),
    "organizations": (Path("PKM/CRM/Organizations"), "name"),
    "topics":        (Path("PKM/My Life/Topics"), "name"),
    "projects":      (Path("PKM/My Life/Projects"), "name"),
    "key_elements":  (Path("PKM/My Life/Key Elements"), "name"),
    "goals":         (Path("PKM/My Life/Goals"), "name"),
    "habits":        (Path("PKM/My Life/Habits"), "name"),
    "documents":     (Path("PKM/Documents"), "title"),
}

# ── LIBRARY FOUNDATION config (schema/07-library-foundation.sql) ─────────────
# A "library" is a curated collection (recipes, films, books, …). Each entry here
# is ONE library: a PKM folder of md notes (one note per item), a doc_type
# discriminator, a mirror table, and the typed AXIS columns the cockpit filters on.
# THIS BLOCK IS THE ADAPTATION SEAM: to wire a user's existing collection, add a
# dict here (and a matching CREATE TABLE in SCHEMA below + the table name in
# OWNED_TABLES). Recipes + movies are the two worked examples.
#
# Each library dict:
#   table        mirror table name (== library_slug; must be in OWNED_TABLES + SCHEMA)
#   folder       root-relative PKM source folder
#   doc_type     frontmatter discriminator; ONLY notes with this doc_type are mirrored
#   nav_label    sidebar label (written to library_registry for the data-driven nav)
#   nav_icon     a lucide icon name the client maps
#   sort_order   nav ordering
#   columns      ordered list of (column, kind, frontmatter_key) for the AXIS columns
#                (the invariant columns slug/title/status/tags/body/file_path/
#                 raw_frontmatter are handled generically and are NOT listed here).
#                kind ∈ {str, int, list_raw, list_slug, raw} — selects the fm_* parser:
#                  str       → fm_str        (scalar, wikilink-stripped)
#                  int       → fm_int        (integer or NULL)
#                  list_raw  → fm_list_json_raw (JSON array, verbatim strings)
#                  list_slug → fm_list_json     (JSON array, slugified — for FK lists)
#                  raw       → fm_raw_str     (verbatim text; '#'/'[[' survive, e.g. verdict)
#                The `title`, `status`, and `tags` invariant columns are populated
#                generically; list them in `columns` ONLY if a library renames them.
LIBRARIES = [
    {
        "table": "recipes",
        "folder": Path("PKM/My Life/Recipes"),
        "doc_type": "recipe",
        "nav_label": "Recipes",
        "nav_icon": "ChefHat",
        "sort_order": 10,
        "columns": [
            ("cuisine", "str", "cuisine"),
            ("dish_type", "str", "dish_type"),
            ("difficulty", "str", "difficulty"),
            ("total_time_min", "int", "total_time_min"),
            ("servings", "int", "servings"),
            ("ingredient_count", "int", "ingredient_count"),
            ("key_ingredients", "list_raw", "key_ingredients"),
            ("source_url", "str", "source_url"),
            ("source_channel", "str", "source_channel"),
        ],
    },
    {
        "table": "movies",
        "folder": Path("PKM/My Life/Movies"),
        "doc_type": "movie",
        "nav_label": "Films & Series",
        "nav_icon": "Clapperboard",
        "sort_order": 20,
        "columns": [
            ("media_type", "str", "media_type"),
            ("rating", "int", "rating"),
            ("release_year", "int", "release_year"),
            ("genre", "str", "genre"),
            ("director_creator", "str", "director_creator"),
            ("platform", "str", "platform"),
            ("date_watched", "str", "date_watched"),
            ("progress", "str", "progress"),
            ("total_seasons", "int", "total_seasons"),
            ("episodes_watched", "int", "episodes_watched"),
            ("verdict", "raw", "verdict"),
        ],
    },
]

SCHEMA = """
CREATE TABLE people (
  -- social_links: JSON array of {label,url} the cockpit renders as clickable
  -- chips. Built from GL-002 `links:` (array of {label,url}) PLUS the recognized
  -- flat convenience fields (website, twitter/x, linkedin, github, instagram,
  -- youtube, mastodon, bluesky). url is kept verbatim; label defaults from the
  -- platform/host when omitted. NULL when a note has none. See DATA-CONTRACT §15.
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, full_name TEXT, relation TEXT,
  social_links TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE organizations (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, org_type TEXT,
  social_links TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE topics (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, key_element TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE projects (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, status TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE goals (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, status TEXT,
  key_element TEXT, linked_projects TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE key_elements (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, description_short TEXT,
  status TEXT, body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE habits (
  -- started_on / status are read by the cockpit's habit list (listByType, the
  -- columnar detail columns) AND by the optional Health pack's planned-habits
  -- panel. They MUST exist as columns: listByType() prepares
  -- `SELECT ..., started_on, status FROM habits` directly (not via the
  -- degrade-on-missing optionalStmt), so a habits table WITHOUT these columns
  -- throws "no such column" and 500s the whole habits browse page. They are
  -- additive + harmless when empty (NULL on a habit note that omits them).
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, cadence TEXT,
  started_on TEXT, status TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE documents (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, title TEXT, doc_type TEXT,
  -- invoice fields (GL-002, doc_type: invoice only; NULL on every other doc_type)
  amount REAL, currency TEXT, invoice_number TEXT, due_date TEXT,
  payment_status TEXT, paid_on TEXT,
  reimbursable INTEGER, reimbursement_status TEXT, reimbursement_via TEXT,
  -- FK arrays (JSON TEXT of slugs). linked_organizations carries the invoice payee;
  -- linked_documents wires e.g. an invoice -> the contract it bills against.
  linked_organizations TEXT, linked_documents TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE deliverables (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, title TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE journal (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, title TEXT, entry_date TEXT,
  mood TEXT, mood_valence INTEGER, energy TEXT, category TEXT, entry_type TEXT,
  -- manual-entry preservation (see schema/06-journal-additions.sql):
  --   original_body       user's verbatim text, set by Penn at integration (else NULL)
  --   integration_status  'raw' | 'integrated' (NULL treated as 'raw')
  --   manually_added      1 = added via the cockpit manual-add flow, else 0/NULL
  original_body TEXT, integration_status TEXT, manually_added INTEGER,
  content TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE journal_media (
  id INTEGER PRIMARY KEY, journal_id INTEGER NOT NULL,
  file_path TEXT, media_type TEXT, mime_type TEXT, caption TEXT,
  sort_order INTEGER DEFAULT 0);
CREATE TABLE weekly_reports (
  -- One row per PKM/Weekly Reports/YYYY/MM/<slug>/metadata.md — an edition of the
  -- weekly recap (GL-002 §"Weekly reports", type: weekly-report).
  --
  -- DATE COLUMNS, READ THIS BEFORE QUERYING: report_date is the FRIDAY ANCHOR and
  -- the natural key. iso_week is the anchor's ISO week and does NOT describe the
  -- covered span — an edition anchored on a Friday opens the preceding Saturday,
  -- which can fall in the previous ISO week. Query coverage with week_start /
  -- week_end, never by parsing iso_week.
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, report_date TEXT,
  edition INTEGER, week_start TEXT, week_end TEXT, iso_week TEXT,
  title TEXT, status TEXT, html_path TEXT,
  podcast_path TEXT, podcast_duration TEXT,
  source_journal_entries TEXT, source_journal_count INTEGER,
  source_images TEXT, source_images_count INTEGER,
  pivotal_moments TEXT, search_expansion TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE INDEX idx_weekly_reports_date ON weekly_reports (report_date DESC);
CREATE INDEX idx_weekly_reports_span ON weekly_reports (week_start, week_end);
CREATE TABLE session_logs (
  -- One row per Team Knowledge/session-logs/YYYY/MM/<file>.md. The append-only
  -- record of every session the team ran, per AGENTS.md §session-log triggers.
  -- Filename convention: YYYY-MM-DD-HH-MM_<agent>_<topic-slug>.md; agent_id and
  -- timestamp come from the frontmatter (see session-logs/_template.md) and fall
  -- back to the filename when a log predates the schema.
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, agent_id TEXT, session_id TEXT,
  timestamp TEXT, type TEXT, title TEXT,
  linked_sops TEXT, linked_workstreams TEXT, linked_guidelines TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE agents (
  -- One row per Team/<Name - Role>/AGENTS.md. contract_body is the AGENTS.md
  -- markdown body (frontmatter stripped) so the cockpit's member-detail view can
  -- render the contract like a note body. contract_frontmatter is the YAML as a
  -- JSON object string (mirrors raw_frontmatter on entity tables — agent_version,
  -- supersedes, compatibility, etc.). The agent's [[wikilinks]] to SOPs/WS/GL/docs
  -- are extracted from contract_body into the `links` graph with
  -- source_table='agents' (see the agents pass in main()), so the member view can
  -- draw a connections canvas via the same idx_links_source path every note uses.
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT, folder TEXT,
  agent_status TEXT DEFAULT 'active', bio TEXT, avatar_path TEXT, owner TEXT,
  contract_body TEXT, contract_frontmatter TEXT, file_path TEXT);
CREATE TABLE agent_journal (
  -- One row per Team/<Name>/journal/*.md durable insight (the _template.md stub is
  -- skipped). agent_slug FKs agents.slug. The cockpit renders a newest-first feed
  -- per agent (created DESC, then title). title is the entry's H1 (the insight in
  -- one sentence, per the journal template); body is the markdown after the H1.
  id INTEGER PRIMARY KEY, agent_slug TEXT NOT NULL, slug TEXT NOT NULL,
  title TEXT, topic TEXT, created TEXT, updated TEXT, status TEXT,
  tags TEXT, body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE links (
  id INTEGER PRIMARY KEY,
  source_table TEXT NOT NULL, source_slug TEXT NOT NULL,
  target_raw TEXT, target_slug TEXT, target_table TEXT, link_type TEXT);
CREATE TABLE transactions (
  -- Example/import-external table: one bank transaction, the shape MoneyMoney (or any
  -- bank export) yields. This is the example of PERSISTING what a reconcile step would
  -- otherwise discard. Seeded from a markdown data file (see TRANSACTIONS_SEED) so it
  -- stays markdown-canonical & regenerable like everything else in this mirror.
  id INTEGER PRIMARY KEY,
  transaction_id TEXT NOT NULL,            -- bank's unique id for the transaction
  booking_date TEXT, value_date TEXT,      -- ISO YYYY-MM-DD
  amount REAL, currency TEXT,              -- amount is SIGNED (debit < 0, credit > 0)
  counterparty_name TEXT, purpose TEXT,
  end_to_end_reference TEXT,
  booked INTEGER DEFAULT 1,                -- 1 = booked, 0 = pending
  source_system TEXT,                      -- e.g. 'moneymoney'
  linked_invoice_slug TEXT,                -- FK to documents.slug (the invoice it settled)
  reconciliation_confidence TEXT,          -- e.g. 'confident' | 'ambiguous' | 'none'
  raw_data TEXT);                          -- JSON blob of the original bank record
CREATE TABLE quotes (
  -- md-first quote library (PKM/Quotes/, doc_type: quote). The quote text is the
  -- note body (or a `quote:` frontmatter fallback). author_slug is set when the
  -- `author` frontmatter was a [[wikilink]] to a CRM Person. See DATA-CONTRACT §8.
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL,
  quote_text TEXT, author TEXT, author_slug TEXT, source TEXT,
  quote_year INTEGER, tags TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
-- ── Outer World (schema/08-module-outer-world.sql) ─────────────────────────────
-- The mymind-style store of SAVED external content (doc_type: outer-world, folder
-- PKM/Outer World/YYYY/MM/). The old "news" entity is generalized into this: news
-- is now one source_type. Three layers in one table: the immutable SOURCE record
-- (source_*), the machine-fetched EMBED card (FLAT embed_*, Axon/Mack contract;
-- embed_image/embed_favicon are LOCAL relative paths localized at capture), and the
-- Inner-World ANNOTATION layer (tom_context + the linked_* bucket lanes + tags). The
-- linked_* are JSON-array TEXT of slugs projected as columns so the grid filters by
-- Topic/KE/Project/Person/Org without a links join. See DATA-CONTRACT §14.
CREATE TABLE outer_world (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, title TEXT, status TEXT,
  captured_on TEXT,
  source_url TEXT, source_type TEXT, source_author TEXT, source_published TEXT,
  embed_kind TEXT, embed_title TEXT, embed_description TEXT, embed_image TEXT,
  embed_site_name TEXT, embed_domain TEXT, embed_favicon TEXT, embed_author TEXT,
  embed_captured_at TEXT,
  tom_context TEXT, tags TEXT,
  linked_topics TEXT, linked_key_elements TEXT, linked_projects TEXT,
  linked_people TEXT, linked_organizations TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
-- ── Library foundation (schema/07-library-foundation.sql) ──────────────────────
-- The registry (data-driven Library nav) + the two built-in libraries. Each mirror
-- table carries the invariant library columns (slug/title/status/tags/body/
-- file_path/raw_frontmatter) plus its own axis columns. A user-added library needs
-- its own CREATE TABLE here, its name in OWNED_TABLES, and a dict in LIBRARIES.
CREATE TABLE library_registry (
  id INTEGER PRIMARY KEY, library_slug TEXT NOT NULL, nav_label TEXT,
  nav_icon TEXT, pkm_folder TEXT, doc_type TEXT,
  title_field TEXT DEFAULT 'title', sort_order INTEGER DEFAULT 0);
CREATE TABLE recipes (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, title TEXT,
  cuisine TEXT, dish_type TEXT, difficulty TEXT, status TEXT,
  total_time_min INTEGER, servings INTEGER, ingredient_count INTEGER,
  key_ingredients TEXT, source_url TEXT, source_channel TEXT,
  tags TEXT, body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE movies (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, title TEXT,
  media_type TEXT, status TEXT, rating INTEGER, release_year INTEGER,
  genre TEXT, director_creator TEXT, platform TEXT, date_watched TEXT,
  progress TEXT, total_seasons INTEGER, episodes_watched INTEGER, verdict TEXT,
  tags TEXT, body TEXT, file_path TEXT, raw_frontmatter TEXT);
-- ── Governance docs (Team Knowledge browser) ──────────────────────────────────
-- workstreams / sops / guidelines mirror the three Team Knowledge doc families. These
-- files carry NO YAML frontmatter: their metadata lives in a `- **Label:** value`
-- bullet block directly under the H1 (Status / Owner(s) / Default owner / Type /
-- Version / Triggered by / References). The regen parses THAT block (see
-- header_block_fields()) rather than fm. Identical column shape across the three so the
-- cockpit can render them through one generic doc view:
--   slug        filename stem (e.g. 'WS-001-daily-journaling') — the route key
--   doc_id      the formal id prefix ('WS-001'/'SOP-001'/'GL-001'); NULL for the
--               un-numbered task SOPs (sop-create-task, …)
--   title       the H1 (always present in these docs)
--   status      `- **Status:**` value if present, else NULL (NOT invented)
--   owner       `- **Owner:**` / `- **Owners:**` / `- **Default owner:**` value, else NULL
--   doc_type    'workstream' | 'sop' | 'guideline' (the family discriminator)
--   summary     first prose paragraph after the header bullet block (same technique as
--               agents.bio), else NULL
--   version     `- **Version:**` value if present, else NULL
--   triggered_by `- **Triggered by:**` / `- **Trigger:**` value if present, else NULL
--   tags        `- **Tags:**` list if present (none ship today), else NULL
-- body wikilinks (incl. the References bullets) become `links` edges; title+body feed
-- notes_fts. domain/category have no source label in these docs today → not a column.
CREATE TABLE workstreams (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, doc_id TEXT, title TEXT,
  status TEXT, owner TEXT, doc_type TEXT DEFAULT 'workstream', summary TEXT,
  version TEXT, triggered_by TEXT, tags TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE sops (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, doc_id TEXT, title TEXT,
  status TEXT, owner TEXT, doc_type TEXT DEFAULT 'sop', summary TEXT,
  version TEXT, triggered_by TEXT, tags TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE guidelines (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, doc_id TEXT, title TEXT,
  status TEXT, owner TEXT, doc_type TEXT DEFAULT 'guideline', summary TEXT,
  version TEXT, triggered_by TEXT, tags TEXT,
  body TEXT, file_path TEXT, raw_frontmatter TEXT);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

-- ── Global full-text search (FTS5, item-8) ─────────────────────────────────────
-- notes_fts is the single searchable corpus across EVERY entity + library + journal
-- + deliverable. Today the cockpit search only matches title/slug; this index makes
-- note BODIES searchable too. better-sqlite3 ships FTS5 compiled in (no new dep).
--
-- Design: a STANDALONE (own-content) FTS5 table — NOT external-content — because the
-- corpus spans many source tables, not one. `type` + `slug` + `entity_id` are stored
-- UNINDEXED so they ride on every hit row (the UI reads them straight off the match
-- to route to #/<type>/<slug>) without polluting the match. Only `title` + `body` are
-- tokenized. `porter unicode61` = the same tokenizer the private vault's *_fts uses
-- (case/diacritic-fold + English stemming). The regen DROPs + rebuilds it from the
-- exact same rows the owned tables get, so it can never drift; it is listed in
-- OWNED_TABLES so the drop/rebuild + read-only contract cover it like any owned table.
CREATE VIRTUAL TABLE notes_fts USING fts5(
  type UNINDEXED,        -- source table name: people|organizations|topics|projects|
                         --   goals|key_elements|habits|documents|deliverables|
                         --   journal|recipes|movies|<library> (routes #/<type>/<slug>)
  slug UNINDEXED,        -- note slug within that type (the route key)
  entity_id UNINDEXED,   -- the source row's integer id (rowid in its own table)
  title,                 -- indexed: the note's display title/name
  body,                  -- indexed: the note body / journal content
  tokenize='porter unicode61'
);
CREATE INDEX idx_links_source ON links (source_table, source_slug);
CREATE INDEX idx_links_target ON links (target_slug);
CREATE INDEX idx_journal_media_journal ON journal_media (journal_id);
CREATE INDEX idx_journal_entry_date ON journal (entry_date);
CREATE INDEX idx_agent_journal_agent ON agent_journal (agent_slug, created);
CREATE INDEX idx_session_logs_ts    ON session_logs (timestamp DESC);
CREATE INDEX idx_session_logs_agent ON session_logs (agent_id, timestamp DESC);
CREATE INDEX idx_transactions_invoice ON transactions (linked_invoice_slug);
CREATE INDEX idx_documents_payment_status ON documents (payment_status);
CREATE INDEX idx_outer_world_captured_on ON outer_world (captured_on);
CREATE INDEX idx_outer_world_source_type ON outer_world (source_type);
CREATE INDEX idx_workstreams_doc_id ON workstreams (doc_id);
CREATE INDEX idx_sops_doc_id ON sops (doc_id);
CREATE INDEX idx_guidelines_doc_id ON guidelines (doc_id);

-- ── Invoice views (Silas-owned; OWNED_VIEWS) ───────────────────────────────────
-- Open invoices with DERIVED due-state. Overdue / due-soon are computed here from
-- due_date vs. today on every regen — never stored on disk (they would go stale).
CREATE VIEW v_open_invoices AS
SELECT
  d.slug, d.title, d.invoice_number, d.linked_organizations,
  d.amount, d.currency, d.due_date,
  CAST(julianday(d.due_date) - julianday('now', 'localtime', 'start of day') AS INTEGER)
    AS days_until_due,
  CASE WHEN d.due_date IS NOT NULL
            AND d.due_date < date('now', 'localtime')
       THEN 1 ELSE 0 END AS is_overdue,
  CASE WHEN d.due_date IS NOT NULL
            AND d.due_date >= date('now', 'localtime')
            AND d.due_date <= date('now', 'localtime', '+7 days')
       THEN 1 ELSE 0 END AS is_due_soon,
  d.file_path
FROM documents d
WHERE d.doc_type = 'invoice' AND d.payment_status = 'open';

-- Reimbursable invoices still waiting to be claimed (claimed but not yet submitted).
CREATE VIEW v_reimbursement_pending AS
SELECT
  d.slug, d.title, d.invoice_number, d.linked_organizations,
  d.amount, d.currency, d.payment_status, d.paid_on,
  d.reimbursement_status, d.reimbursement_via, d.file_path
FROM documents d
WHERE d.doc_type = 'invoice'
  AND d.reimbursable = 1
  AND d.reimbursement_status = 'einzureichen';

-- Payment audit trail: each invoice LEFT JOINed to the bank transaction that settled
-- it (via transactions.linked_invoice_slug). Surfaces the matched payment for paid
-- invoices, and NULLs for invoices with no recorded transaction yet.
CREATE VIEW v_invoice_payment_trail AS
SELECT
  d.slug AS invoice_slug, d.title AS invoice_title, d.invoice_number,
  d.amount AS invoice_amount, d.currency AS invoice_currency,
  d.due_date, d.payment_status, d.paid_on,
  t.transaction_id, t.booking_date, t.value_date,
  t.amount AS transaction_amount, t.counterparty_name, t.purpose,
  t.end_to_end_reference, t.source_system, t.reconciliation_confidence,
  CASE WHEN t.transaction_id IS NOT NULL
            AND ABS(ABS(t.amount) - d.amount) < 0.005
       THEN 1 ELSE 0 END AS amount_matches
FROM documents d
LEFT JOIN transactions t ON t.linked_invoice_slug = d.slug
WHERE d.doc_type = 'invoice';
"""

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
# [[target]] / [[target|label]] / [[target#heading]] ; ![[...]] is an embed.
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]\[]+?)\]\]")
SKIP_NAMES = {"index.md", "readme.md"}

MIME_BY_EXT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav",
}

# Slug-collision priority (mirrors the cockpit's TYPE_PRIORITY).
TYPE_PRIORITY = [
    "people", "organizations", "projects", "goals", "topics",
    "key_elements", "habits", "documents", "deliverables", "journal",
    # governance docs: heavy link TARGETS (every References bullet, every agent
    # contract points at a WS-/SOP-/GL-). Slugs are id-prefixed so collisions with
    # entity notes are effectively impossible; placed below entities for safety.
    "workstreams", "sops", "guidelines",
    # agents are link SOURCES (their AGENTS.md links out to SOPs/WS/GL) and may
    # also be link TARGETS (a note linking [[silas]]); lowest priority so a slug
    # collision with a real entity note always resolves to the entity.
    "agents",
]

stats: dict[str, int] = {}
warnings: list[str] = []


def read_note(path: Path):
    """-> (frontmatter dict, body str). Malformed YAML degrades to {} + warning."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    fm, body = {}, text
    if m:
        body = text[m.end():]
        try:
            parsed = yaml.safe_load(m.group(1))
            if isinstance(parsed, dict):
                fm = parsed
        except yaml.YAMLError as e:
            warnings.append(f"frontmatter parse failed, treated as plain note: {path} ({e})")
    return fm, body


def jsonable(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    return v


def fm_json(fm: dict) -> str:
    return json.dumps(jsonable(fm), ensure_ascii=False)


def fm_str(fm: dict, key: str):
    v = fm.get(key)
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, str):
        return strip_wikilink(v.strip()) or None
    return str(v)


def fm_raw_str(fm: dict, key: str):
    """Frontmatter value as a plain string, NOT wikilink-stripped. Use for free
    text (e.g. original_body block scalars) where '#' / '[[' must survive."""
    v = fm.get(key)
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, str):
        return v if v.strip() else None
    return str(v)


def fm_int(fm: dict, key: str):
    v = fm.get(key)
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


def fm_float(fm: dict, key: str):
    v = fm.get(key)
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def fm_bool(fm: dict, key: str):
    """-> 1 / 0 / None. Stored as INTEGER (SQLite has no native bool)."""
    v = fm.get(key)
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "yes", "1"):
            return 1
        if s in ("false", "no", "0"):
            return 0
    return None


def fm_list_json(fm: dict, key: str):
    """A frontmatter list (e.g. linked_projects) -> JSON-array TEXT of slugs."""
    v = fm.get(key)
    if not isinstance(v, list):
        return None
    out = [slug_of(strip_wikilink(str(x))) for x in v if str(x).strip()]
    return json.dumps(out, ensure_ascii=False) if out else None


def fm_list_json_raw(fm: dict, key: str):
    """A frontmatter list -> JSON-array TEXT, values kept verbatim (NOT slugified).
    Use for tags / labels where the human string is what the UI shows; use
    fm_list_json for FK fields where the value must be a target slug."""
    v = fm.get(key)
    if not isinstance(v, list):
        return None
    out = [str(x).strip() for x in v if str(x).strip()]
    return json.dumps(out, ensure_ascii=False) if out else None


# Recognized flat social/website frontmatter keys -> default chip label.
# GL-002's `links:` array is the primary, extensible shape; these flat fields are
# the convenience aliases (and keep existing notes that already use `website`).
SOCIAL_FLAT_FIELDS = {
    "website": "Website", "homepage": "Website", "url": "Website",
    "twitter": "X", "x": "X", "linkedin": "LinkedIn", "github": "GitHub",
    "instagram": "Instagram", "youtube": "YouTube", "mastodon": "Mastodon",
    "bluesky": "Bluesky", "threads": "Threads", "facebook": "Facebook",
    "tiktok": "TikTok", "substack": "Substack",
}


def _normalize_url(v: str) -> str | None:
    """Best-effort clickable URL.
      - explicit scheme (http/https/mailto) → kept verbatim
      - a bare HOST ('example.org', 'sub.example.org/path') → prefixed https://
      - anything else (a bare @handle, a username with no host) → kept verbatim
        so the chip is honest (the cockpit can render non-URL handles as text).
    Never invents a host from a handle (that was the 'https://@ada@…' bug)."""
    s = str(v).strip()
    if not s:
        return None
    if s.startswith(("http://", "https://", "mailto:")):
        return s
    host = s.lstrip("/").split("/", 1)[0]
    looks_like_host = ("." in host and "@" not in host
                       and " " not in s and not host.startswith("."))
    return "https://" + s.lstrip("/") if looks_like_host else s


def fm_social_links(fm: dict):
    """-> JSON array TEXT of {label,url} clickable chips, or None.

    Sources, in order (dedup by url):
      1. `links:` — array of {label,url} (or {name/title, href/url}) OR a bare
         array of url strings. The primary GL-002 shape.
      2. The flat SOCIAL_FLAT_FIELDS (website/twitter/linkedin/…), each a scalar
         url/handle. Label defaults from the field name.
    Malformed entries are skipped (never crash the regen)."""
    out, seen = [], set()

    def add(label, raw):
        url = _normalize_url(raw) if raw is not None else None
        if not url or url in seen:
            return
        seen.add(url)
        out.append({"label": (str(label).strip() if label else None) or url, "url": url})

    links = fm.get("links")
    if isinstance(links, list):
        for item in links:
            if isinstance(item, dict):
                url = item.get("url") or item.get("href") or item.get("link")
                label = item.get("label") or item.get("name") or item.get("title")
                add(label, url)
            elif isinstance(item, str):
                add(None, item)
    for key, default_label in SOCIAL_FLAT_FIELDS.items():
        v = fm.get(key)
        if isinstance(v, str) and v.strip():
            add(default_label, v)
    return json.dumps(out, ensure_ascii=False) if out else None


def strip_wikilink(s: str) -> str:
    s = s.strip()
    if s.startswith("[[") and s.endswith("]]"):
        s = s[2:-2]
    return s.split("|")[0].split("#")[0].strip()


def slug_of(target: str) -> str:
    """Last path segment, lowercased, spaces -> hyphens (matches GL-001 slugs)."""
    last = target.replace("\\", "/").rstrip("/").split("/")[-1]
    if last.lower().endswith(".md"):
        last = last[:-3]
    return re.sub(r"\s+", "-", last.strip()).lower()


def title_from(fm: dict, body: str, fallback: str, *keys: str):
    for k in keys:
        v = fm_str(fm, k)
        if v:
            return v
    m = H1_RE.search(body)
    if m:
        return m.group(1).strip()
    return fallback


def md_files(folder: Path, recursive: bool = False):
    if not folder.is_dir():
        return []
    pattern = "**/*.md" if recursive else "*.md"
    return sorted(
        p for p in folder.glob(pattern)
        if p.name.lower() not in SKIP_NAMES and not p.name.startswith(".")
        and "_files" not in p.parts
    )


def extract_links(body: str):
    """-> [(target_raw, target_slug, link_type)] dedupe-preserving order."""
    seen, out = set(), []
    for m in WIKILINK_RE.finditer(body):
        raw = m.group(2).split("|")[0].strip()
        if not raw:
            continue
        link_type = "embed" if m.group(1) == "!" else "wikilink"
        key = (raw, link_type)
        if key in seen:
            continue
        seen.add(key)
        out.append((raw, slug_of(strip_wikilink(raw)), link_type))
    return out


# Governance docs carry their metadata as a `- **Label:** value` bullet block right
# under the H1 (these files have NO YAML frontmatter). Match a bullet whose first
# token is a bold label ending in a colon.
HEADER_BULLET_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?):\*\*\s*(.*)$")


def header_block_fields(body: str) -> dict:
    """Parse the leading `- **Label:** value` bullet block of a governance doc.

    Reads ONLY the first contiguous run of bold-label bullets after the H1 (so a
    `- **Path:**` bullet buried deep in the body is never mistaken for a header
    field). Returns {label_lower: value}. Wikilinks in values are kept verbatim
    (callers slug/strip as needed). A doc with no such block returns {}."""
    fields: dict[str, str] = {}
    in_block = False
    for line in body.splitlines():
        m = HEADER_BULLET_RE.match(line)
        if m:
            in_block = True
            fields[m.group(1).strip().lower()] = m.group(2).strip()
            continue
        if in_block:
            # A blank line inside the block is tolerated; first non-blank,
            # non-bullet line ends the header block.
            if line.strip() == "":
                continue
            break
    return fields


def header_summary(body: str) -> str | None:
    """First real prose paragraph after the H1 + header bullet block — the doc's
    one-line gist (mirrors the agents.bio extraction). Skips headings, bullets,
    tables, blockquotes. None if nothing prose-shaped is found."""
    for para in re.split(r"\n\s*\n", body):
        p = para.strip()
        if not p:
            continue
        first = p.splitlines()[0].lstrip()
        if first.startswith(("#", "-", "*", "|", ">")):
            continue
        return re.sub(r"\s+", " ", p)[:400]
    return None


# Governance-doc families -> (table, source folder, doc_type, id-prefix regex).
# The id-prefix regex pulls the formal doc id (WS-001 / SOP-001 / GL-001) off the
# filename stem; un-numbered task SOPs (sop-create-task, …) match nothing -> NULL.
GOVERNANCE_FAMILIES = [
    ("workstreams", Path("Team Knowledge/Workstreams"), "workstream",
     re.compile(r"^(WS-\d+)", re.IGNORECASE)),
    ("sops", Path("Team Knowledge/SOPs"), "sop",
     re.compile(r"^(SOP-\d+)", re.IGNORECASE)),
    ("guidelines", Path("Team Knowledge/Guidelines"), "guideline",
     re.compile(r"^(GL-\d+)", re.IGNORECASE)),
]


def main():
    if not (ROOT / "PKM").is_dir():
        sys.exit(f"This does not look like a myPKA root (no PKM/ folder): {ROOT}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # A user-added library (a dict in LIBRARIES whose table isn't a built-in) is
    # owned by the regen too — append its table name so it's dropped+rebuilt each
    # run alongside recipes/movies. (The built-ins are already in OWNED_TABLES.)
    for lib in LIBRARIES:
        if lib["table"] not in OWNED_TABLES:
            OWNED_TABLES.append(lib["table"])

    # Drop ONLY owned tables + owned views; everything else in the file is preserved.
    existing = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    foreign = sorted(existing - set(OWNED_TABLES) - set(OWNED_VIEWS))
    # Views first (they depend on the tables), then tables.
    for v in OWNED_VIEWS:
        cur.execute(f"DROP VIEW IF EXISTS {v}")
    for t in OWNED_TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
    cur.executescript(SCHEMA)

    link_rows = []          # collected; resolved + inserted at the end
    slug_to_table = {}      # slug -> table (first by TYPE_PRIORITY wins)

    def register(table: str, slug: str):
        if slug not in slug_to_table:
            slug_to_table[slug] = table
        else:
            cur_t = slug_to_table[slug]
            if TYPE_PRIORITY.index(table) < TYPE_PRIORITY.index(cur_t):
                slug_to_table[slug] = table

    # ---- entity folders ------------------------------------------------------
    for table, (rel, title_col) in ENTITY_FOLDERS.items():
        rows = 0
        for path in md_files(ROOT / rel):
            fm, body = read_note(path)
            slug = path.stem
            file_path = str(path.relative_to(ROOT))
            title = title_from(fm, body, slug, title_col, "title", "name")
            common = dict(slug=slug, body=body.strip(), file_path=file_path,
                          raw_frontmatter=fm_json(fm))
            if table == "people":
                cur.execute(
                    "INSERT INTO people (slug, full_name, relation, social_links, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :relation, :social_links, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "relation": fm_str(fm, "relation"),
                     "social_links": fm_social_links(fm)})
            elif table == "organizations":
                cur.execute(
                    "INSERT INTO organizations (slug, name, org_type, social_links, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :org_type, :social_links, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "org_type": fm_str(fm, "org_type"),
                     "social_links": fm_social_links(fm)})
            elif table == "topics":
                cur.execute(
                    "INSERT INTO topics (slug, name, key_element, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :ke, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "ke": fm_str(fm, "key_element")})
            elif table == "projects":
                cur.execute(
                    "INSERT INTO projects (slug, name, status, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :status, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "status": fm_str(fm, "status")})
            elif table == "goals":
                cur.execute(
                    "INSERT INTO goals (slug, name, status, key_element, linked_projects, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :status, :ke, :lp, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "status": fm_str(fm, "status"),
                     "ke": fm_str(fm, "key_element"),
                     "lp": fm_list_json(fm, "linked_projects")})
            elif table == "key_elements":
                cur.execute(
                    "INSERT INTO key_elements (slug, name, description_short, status, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :d, :status, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "d": fm_str(fm, "description_short"),
                     "status": fm_str(fm, "status")})
            elif table == "habits":
                cur.execute(
                    "INSERT INTO habits (slug, name, cadence, started_on, status, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :cadence, :started_on, :status, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "cadence": fm_str(fm, "cadence"),
                     "started_on": fm_str(fm, "started_on"),
                     "status": fm_str(fm, "status")})
            elif table == "documents":
                cur.execute(
                    "INSERT INTO documents (slug, title, doc_type, amount, currency,"
                    " invoice_number, due_date, payment_status, paid_on, reimbursable,"
                    " reimbursement_status, reimbursement_via, linked_organizations,"
                    " linked_documents, body, file_path, raw_frontmatter)"
                    " VALUES (:slug, :t, :doc_type, :amount, :currency, :invoice_number,"
                    " :due_date, :payment_status, :paid_on, :reimbursable,"
                    " :reimbursement_status, :reimbursement_via, :linked_organizations,"
                    " :linked_documents, :body, :file_path, :raw_frontmatter)",
                    {**common, "t": title, "doc_type": fm_str(fm, "doc_type"),
                     "amount": fm_float(fm, "amount"),
                     "currency": fm_str(fm, "currency"),
                     "invoice_number": fm_str(fm, "invoice_number"),
                     "due_date": fm_str(fm, "due_date"),
                     "payment_status": fm_str(fm, "payment_status"),
                     "paid_on": fm_str(fm, "paid_on"),
                     "reimbursable": fm_bool(fm, "reimbursable"),
                     "reimbursement_status": fm_str(fm, "reimbursement_status"),
                     "reimbursement_via": fm_str(fm, "reimbursement_via"),
                     "linked_organizations": fm_list_json(fm, "linked_organizations"),
                     "linked_documents": fm_list_json(fm, "linked_documents")})
            register(table, slug)
            for raw, tslug, ltype in extract_links(body):
                link_rows.append((table, slug, raw, tslug, ltype))
            rows += 1
        stats[table] = rows

    # ---- journal (recursive, dated) ------------------------------------------
    rows = 0
    for path in md_files(ROOT / "PKM/Journal", recursive=True):
        fm, body = read_note(path)
        slug = path.stem
        file_path = str(path.relative_to(ROOT))
        entry_date = fm_str(fm, "date") or fm_str(fm, "entry_date")
        if not entry_date:
            m = DATE_PREFIX_RE.match(path.stem)
            entry_date = m.group(1) if m else None
        title = title_from(fm, body, slug, "title")

        # Split out the ## Media section into journal_media rows; the content
        # column keeps everything before it.
        media_rows = []
        content = body
        media_match = re.search(r"^##\s+Media\s*$", body, re.MULTILINE)
        if media_match:
            content = body[: media_match.start()]
            media_block = body[media_match.end():]
            nxt = re.search(r"^##\s+", media_block, re.MULTILINE)
            if nxt:
                media_block = media_block[: nxt.start()]
            lines = media_block.splitlines()
            order = 0
            for i, line in enumerate(lines):
                em = re.match(r"^!\[\[([^\]]+)\]\]", line.strip())
                if not em:
                    continue
                mp = em.group(1).split("|")[0].strip()
                mp_rel = re.sub(r"^PKM/", "", mp.replace("\\", "/"))
                ext = Path(mp_rel).suffix.lower()
                caption = None
                if i + 1 < len(lines):
                    cm = re.match(r"^_(.+)_\s*$", lines[i + 1].strip())
                    if cm:
                        caption = cm.group(1).strip()
                media_type = "audio" if ext in (".mp3", ".m4a", ".wav") else (
                    "screenshot" if ("screenshot" in mp_rel.lower() or "social" in mp_rel.lower())
                    else "image")
                media_rows.append((mp_rel, media_type, MIME_BY_EXT.get(ext), caption, order))
                order += 1

        # Manual-entry preservation (see schema/06-journal-additions.sql):
        #   original_body      verbatim text Penn preserved at integration (else NULL)
        #   integration_status 'raw' | 'integrated'. If the note carries an
        #                      original_body but no explicit status, it was clearly
        #                      integrated → default to 'integrated'. Otherwise NULL
        #                      (the UI treats NULL as 'raw' = body is the original).
        original_body = fm_raw_str(fm, "original_body")
        integration_status = fm_str(fm, "integration_status")
        if integration_status is None and original_body is not None:
            integration_status = "integrated"
        manually_added = fm_bool(fm, "manually_added")
        cur.execute(
            "INSERT INTO journal (slug, title, entry_date, mood, mood_valence, energy,"
            " category, entry_type, original_body, integration_status, manually_added,"
            " content, file_path, raw_frontmatter)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (slug, title, entry_date, fm_str(fm, "mood"), fm_int(fm, "mood_valence"),
             fm_str(fm, "energy"), fm_str(fm, "category"), fm_str(fm, "entry_type"),
             original_body, integration_status, manually_added,
             content.strip(), file_path, fm_json(fm)))
        jid = cur.lastrowid
        for mp_rel, mtype, mime, caption, order in media_rows:
            cur.execute(
                "INSERT INTO journal_media (journal_id, file_path, media_type, mime_type, caption, sort_order)"
                " VALUES (?,?,?,?,?,?)", (jid, mp_rel, mtype, mime, caption, order))
        register("journal", slug)
        for raw, tslug, ltype in extract_links(body):
            link_rows.append(("journal", slug, raw, tslug, ltype))
        rows += 1
    stats["journal"] = rows

    # ---- deliverables ----------------------------------------------------------
    rows = 0
    for path in md_files(ROOT / "Deliverables", recursive=True):
        if "_archive" in path.parts or "_installed" in path.parts:
            continue
        fm, body = read_note(path)
        # A deliverable lives in a dated folder; key on folder/file for uniqueness.
        rel = path.relative_to(ROOT / "Deliverables")
        slug = slug_of(rel.parts[0]) if len(rel.parts) > 1 else path.stem
        title = title_from(fm, body, path.stem, "title")
        cur.execute(
            "INSERT INTO deliverables (slug, title, body, file_path, raw_frontmatter)"
            " VALUES (?,?,?,?,?)",
            (slug, title, body.strip(), str(path.relative_to(ROOT)), fm_json(fm)))
        register("deliverables", slug)
        for raw, tslug, ltype in extract_links(body):
            link_rows.append(("deliverables", slug, raw, tslug, ltype))
        rows += 1
    stats["deliverables"] = rows

    # ---- governance docs (Team Knowledge/Workstreams|SOPs|Guidelines) -----------
    # One loop mirrors all three families. These docs have NO YAML frontmatter; their
    # metadata is a `- **Label:** value` bullet block under the H1 (parsed by
    # header_block_fields). Recursive so a family's subfolder (e.g. Workstreams/myicor/)
    # is indexed too; INDEX.md is skipped generically (SKIP_NAMES). slug = filename stem;
    # doc_id = the formal WS-/SOP-/GL- prefix (NULL for un-numbered task SOPs). Title is
    # the H1. status/owner/version/triggered_by come ONLY from the header block (NULL when
    # absent — never invented). Body wikilinks (incl. the References bullets) become graph
    # edges; title+body feed notes_fts. raw_frontmatter is the parsed header block as JSON
    # (these docs have no fm, so this is the closest structured echo for the cockpit's
    # Properties panel).
    for table, rel, doc_type, id_re in GOVERNANCE_FAMILIES:
        rows = 0
        for path in md_files(ROOT / rel, recursive=True):
            fm, body = read_note(path)  # fm is {} for these (no YAML); body is full text
            slug = path.stem
            file_path = str(path.relative_to(ROOT))
            hdr = header_block_fields(body)
            id_m = id_re.match(slug)
            doc_id = id_m.group(1).upper() if id_m else None
            title = title_from(fm, body, slug, "title")
            owner = hdr.get("owner") or hdr.get("owners") or hdr.get("default owner")
            if owner:
                # These values can be multi-owner narrative with inline **bold** and
                # [[wikilinks]]; flatten both so the cockpit renders clean display text.
                owner = re.sub(r"\*\*(.+?)\*\*", r"\1", owner)
                owner = re.sub(r"\[\[([^\]\[]+?)\]\]",
                               lambda m: m.group(1).split("|")[0].split("#")[0],
                               owner).strip() or None
            status = hdr.get("status")
            version = hdr.get("version")
            triggered_by = hdr.get("triggered by") or hdr.get("trigger")
            # tags: header block almost never has them today, but honor a `Tags:` line.
            tags_raw = hdr.get("tags")
            tags = None
            if tags_raw:
                parts = [t.strip() for t in re.split(r"[,;]", tags_raw) if t.strip()]
                tags = json.dumps(parts, ensure_ascii=False) if parts else None
            cur.execute(
                f"INSERT INTO {table} (slug, doc_id, title, status, owner, doc_type,"
                f" summary, version, triggered_by, tags, body, file_path, raw_frontmatter)"
                f" VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (slug, doc_id, title, status, owner, doc_type,
                 header_summary(body), version, triggered_by, tags,
                 body.strip(), file_path,
                 json.dumps(jsonable(hdr), ensure_ascii=False)))
            # Resolver registration uses the LOWERCASED slug: governance filename stems
            # carry uppercase id prefixes (GL-001-…, WS-…, SOP-…) but extract_links()
            # lowercases every target via slug_of(), so an incoming [[GL-001-…]] reference
            # only resolves its target_table if the resolver key is lowercased too. The
            # stored `slug` column keeps the original-case stem (the cockpit route key).
            register(table, slug.lower())
            for raw, tslug, ltype in extract_links(body):
                link_rows.append((table, slug, raw, tslug, ltype))
            rows += 1
        stats[table] = rows

    # ---- quotes (PKM/Quotes/, md-first, doc_type: quote) ------------------------
    # One markdown file per quote. The quote TEXT is the note body (canonical), with
    # a `quote:` frontmatter field as a fallback for one-liners. `author` may be a
    # plain string OR a [[wikilink]] to a CRM Person — when it's a wikilink we resolve
    # author_slug so the Hub can deep-link the attribution. Only doc_type: quote notes
    # are mirrored (a stray non-quote note in the folder is skipped, not guessed).
    rows = 0
    for path in md_files(ROOT / "PKM/Quotes"):
        fm, body = read_note(path)
        if (fm_str(fm, "doc_type") or "").lower() != "quote":
            warnings.append(f"PKM/Quotes note without doc_type: quote, skipped: {path}")
            continue
        slug = path.stem
        file_path = str(path.relative_to(ROOT))
        # Quote text: prefer the body; fall back to a `quote:` frontmatter field.
        quote_text = body.strip() or fm_str(fm, "quote")
        # Author: if frontmatter held a [[wikilink]], keep the display label in
        # `author` and resolve the slug into author_slug; else author_slug stays NULL.
        author_raw = fm.get("author")
        author = author_slug = None
        if isinstance(author_raw, str) and author_raw.strip():
            stripped = strip_wikilink(author_raw)
            author = stripped or None
            if "[[" in author_raw:
                author_slug = slug_of(stripped)
        cur.execute(
            "INSERT INTO quotes (slug, quote_text, author, author_slug, source,"
            " quote_year, tags, body, file_path, raw_frontmatter)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (slug, quote_text, author, author_slug, fm_str(fm, "source"),
             fm_int(fm, "year"), fm_list_json_raw(fm, "tags"),
             body.strip(), file_path, fm_json(fm)))
        register("quotes", slug)
        for raw, tslug, ltype in extract_links(body):
            link_rows.append(("quotes", slug, raw, tslug, ltype))
        # An author wikilink in frontmatter is also a graph edge (author -> Person).
        if author_slug:
            link_rows.append(("quotes", slug, str(author_raw), author_slug, "wikilink"))
        rows += 1
    stats["quotes"] = rows

    # ---- outer_world (PKM/Outer World/YYYY/MM/, md-first, doc_type: outer-world) ----
    # The mymind-style store of SAVED external content. Recursive + dated (like the
    # journal): saves are time-series capture events. THREE layers per note:
    #   1. SOURCE (source_url/source_type/source_author/source_published) — immutable.
    #   2. EMBED card — the FLAT embed_* OpenGraph fields (Axon/Mack contract). Read
    #      1:1 from flat frontmatter keys (NOT a nested block). embed_image/_favicon
    #      are LOCAL relative paths (localized at capture; the regen stores them
    #      verbatim via fm_raw_str so a leading path/`#`/spaces survive byte-for-byte).
    #   3. ANNOTATION (tom_context + tags + the five linked_* bucket lanes) — the
    #      Inner-World layer. tom_context is read verbatim (may be a block scalar with
    #      line breaks). The linked_* are slug arrays projected into columns so the
    #      cockpit grid filters by Topic/KE/Project/Person/Org via json_each() with no
    #      links join. Body wikilinks ALSO become normal graph edges. Only notes whose
    #      doc_type is outer-world are mirrored (a stray note is skipped with a warning,
    #      never guessed). captured_on falls back to the YYYY-MM-DD filename prefix.
    rows = 0
    for path in md_files(ROOT / "PKM/Outer World", recursive=True):
        fm, body = read_note(path)
        if (fm_str(fm, "doc_type") or "").lower() != "outer-world":
            warnings.append(
                f"PKM/Outer World note without doc_type: outer-world, skipped: {path}")
            continue
        slug = path.stem
        file_path = str(path.relative_to(ROOT))
        title = title_from(fm, body, slug, "title")
        captured_on = fm_str(fm, "captured_on")
        if not captured_on:
            m = DATE_PREFIX_RE.match(path.stem)
            captured_on = m.group(1) if m else None
        cur.execute(
            "INSERT INTO outer_world (slug, title, status, captured_on,"
            " source_url, source_type, source_author, source_published,"
            " embed_kind, embed_title, embed_description, embed_image,"
            " embed_site_name, embed_domain, embed_favicon, embed_author,"
            " embed_captured_at, tom_context, tags,"
            " linked_topics, linked_key_elements, linked_projects,"
            " linked_people, linked_organizations,"
            " body, file_path, raw_frontmatter)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (slug, title, fm_str(fm, "status"), captured_on,
             fm_str(fm, "source_url"), fm_str(fm, "source_type"),
             fm_str(fm, "source_author"), fm_str(fm, "source_published"),
             fm_str(fm, "embed_kind"), fm_raw_str(fm, "embed_title"),
             fm_raw_str(fm, "embed_description"), fm_raw_str(fm, "embed_image"),
             fm_raw_str(fm, "embed_site_name"), fm_str(fm, "embed_domain"),
             fm_raw_str(fm, "embed_favicon"), fm_raw_str(fm, "embed_author"),
             fm_str(fm, "embed_captured_at"), fm_raw_str(fm, "tom_context"),
             fm_list_json_raw(fm, "tags"),
             fm_list_json(fm, "linked_topics"),
             fm_list_json(fm, "linked_key_elements"),
             fm_list_json(fm, "linked_projects"),
             fm_list_json(fm, "linked_people"),
             fm_list_json(fm, "linked_organizations"),
             body.strip(), file_path, fm_json(fm)))
        register("outer_world", slug)
        for raw, tslug, ltype in extract_links(body):
            link_rows.append(("outer_world", slug, raw, tslug, ltype))
        rows += 1
    stats["outer_world"] = rows

    # ---- libraries (the LIBRARY FOUNDATION; PKM/<Library>/, doc_type discriminator)
    # Generic, registry-driven ingestion: ONE loop mirrors EVERY library in
    # LIBRARIES. Each library is a folder of md notes (one note per item). The
    # invariant columns (slug/title/status/tags/body/file_path/raw_frontmatter) are
    # filled the same way for every library; the per-library AXIS columns come from
    # each library's `columns` spec via the matching fm_* parser. Body wikilinks
    # (a recipe → its cuisine Topic / the Person who taught it; a movie → its
    # director Person / genre Topic) become normal graph edges. Only notes whose
    # doc_type matches the library's discriminator are mirrored (a stray note is
    # skipped with a warning, never guessed into the wrong shape).
    PARSERS = {
        "str": fm_str, "int": fm_int, "raw": fm_raw_str,
        "list_raw": fm_list_json_raw, "list_slug": fm_list_json,
    }
    for lib in LIBRARIES:
        table = lib["table"]
        want_doc = (lib["doc_type"] or "").lower()
        rows = 0
        for path in md_files(ROOT / lib["folder"]):
            fm, body = read_note(path)
            if (fm_str(fm, "doc_type") or "").lower() != want_doc:
                warnings.append(
                    f"{lib['folder']} note without doc_type: {want_doc}, skipped: {path}")
                continue
            slug = path.stem
            file_path = str(path.relative_to(ROOT))
            title = title_from(fm, body, slug, "title", "name")
            # Invariant columns (same for every library).
            cols = ["slug", "title", "status", "tags", "body", "file_path", "raw_frontmatter"]
            vals = [slug, title, fm_str(fm, "status"), fm_list_json_raw(fm, "tags"),
                    body.strip(), file_path, fm_json(fm)]
            # Per-library axis columns.
            for col, kind, fkey in lib["columns"]:
                cols.append(col)
                vals.append(PARSERS[kind](fm, fkey))
            placeholders = ",".join("?" for _ in cols)
            cur.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                vals)
            register(table, slug)
            for raw, tslug, ltype in extract_links(body):
                link_rows.append((table, slug, raw, tslug, ltype))
            rows += 1
        stats[table] = rows
        # One registry row per library, so the cockpit's Library nav is data-driven.
        cur.execute(
            "INSERT INTO library_registry (library_slug, nav_label, nav_icon,"
            " pkm_folder, doc_type, title_field, sort_order) VALUES (?,?,?,?,?,?,?)",
            (table, lib["nav_label"], lib["nav_icon"], str(lib["folder"]),
             lib["doc_type"], "title", lib.get("sort_order", 0)))

    # ---- agents (Team/<Name - Role>/AGENTS.md) ---------------------------------
    rows = 0
    journal_rows = 0
    team_dir = ROOT / "Team"
    if team_dir.is_dir():
        for folder in sorted(p for p in team_dir.iterdir() if p.is_dir()):
            contract = folder / "AGENTS.md"
            if not contract.is_file():
                continue
            fm, body = read_note(contract)
            name = fm_str(fm, "name") or folder.name
            slug = slug_of(name.split(" - ")[0]) or slug_of(folder.name)
            status = fm_str(fm, "status") or fm_str(fm, "agent_status") or "active"
            # bio: explicit frontmatter, else the first prose paragraph of the contract.
            bio = fm_str(fm, "bio")
            if not bio:
                for para in re.split(r"\n\s*\n", body):
                    p = para.strip()
                    if p and not p.startswith("#") and not p.startswith("|") and not p.startswith("-"):
                        bio = re.sub(r"\s+", " ", p)[:400]
                        break
            avatar = None
            for cand in ("avatar.png", "avatar.jpg", "avatar.webp"):
                if (folder / cand).is_file():
                    avatar = str((folder / cand).relative_to(ROOT))
                    break
            file_path = str(contract.relative_to(ROOT))
            cur.execute(
                "INSERT INTO agents (slug, name, folder, agent_status, bio,"
                " avatar_path, owner, contract_body, contract_frontmatter, file_path)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (slug, name, folder.name, status, bio, avatar,
                 fm_str(fm, "owner"), body.strip(), fm_json(fm), file_path))
            register("agents", slug)
            # The contract's [[wikilinks]] (to SOPs/WS/GL/docs/other agents) become
            # edges in the `links` graph with source_table='agents', so the member
            # view's connections canvas reads them via idx_links_source like any note.
            for raw, tslug, ltype in extract_links(body):
                link_rows.append(("agents", slug, raw, tslug, ltype))
            rows += 1

            # ---- agent journal (Team/<Name>/journal/*.md) -----------------------
            # Durable per-agent insights, enumerable as a newest-first feed. The
            # _template.md stub is skipped (it is scaffolding, not an insight). The
            # H1 of each entry is the title (per the journal template convention).
            journal_dir = folder / "journal"
            if journal_dir.is_dir():
                for jpath in sorted(p for p in journal_dir.glob("*.md")
                                    if p.name != "_template.md"):
                    jfm, jbody = read_note(jpath)
                    jslug = jpath.stem
                    h1 = re.search(r"^#\s+(.+)$", jbody, re.MULTILINE)
                    jtitle = (h1.group(1).strip() if h1
                              else fm_str(jfm, "title") or jslug)
                    cur.execute(
                        "INSERT INTO agent_journal (agent_slug, slug, title, topic,"
                        " created, updated, status, tags, body, file_path, raw_frontmatter)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (slug, jslug, jtitle, fm_str(jfm, "topic"),
                         fm_str(jfm, "created"), fm_str(jfm, "updated"),
                         fm_str(jfm, "status"), fm_list_json_raw(jfm, "tags"),
                         jbody.strip(), str(jpath.relative_to(ROOT)), fm_json(jfm)))
                    journal_rows += 1
    stats["agents"] = rows
    stats["agent_journal"] = journal_rows

    # ---- session logs ----------------------------------------------------------
    # Team Knowledge/session-logs/YYYY/MM/YYYY-MM-DD-HH-MM_<agent>_<topic>.md
    # Powers the cockpit's Team Analytics view (specialist session load over time).
    # Graceful on an empty tree: a fresh myPKA has the folder + template only.
    rows = 0
    FNAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})_([a-z0-9-]+)_(.+)$")
    for path in md_files(ROOT / "Team Knowledge" / "session-logs", recursive=True):
        if path.name.startswith("_") or path.name.lower() == "readme.md":
            continue
        fm, body = read_note(path)
        slug = path.stem
        m = FNAME_RE.match(slug)
        # Frontmatter wins; the filename is the fallback so pre-schema logs still land.
        agent_id = fm_str(fm, "agent_id") or (m.group(6) if m else None)
        timestamp = fm_str(fm, "timestamp")
        if not timestamp and m:
            timestamp = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:00Z"
        title = title_from(fm, body, slug.replace("-", " "), "title")
        cur.execute(
            "INSERT INTO session_logs (slug, agent_id, session_id, timestamp, type, title,"
            " linked_sops, linked_workstreams, linked_guidelines, body, file_path, raw_frontmatter)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (slug, agent_id, fm_str(fm, "session_id"), timestamp, fm_str(fm, "type"), title,
             fm_list_json(fm, "linked_sops"), fm_list_json(fm, "linked_workstreams"),
             fm_list_json(fm, "linked_guidelines"),
             body.strip(), str(path.relative_to(ROOT)), fm_json(fm)))
        for raw, tslug, ltype in extract_links(body):
            link_rows.append(("session_logs", slug, raw, tslug, ltype))
        rows += 1
    stats["session_logs"] = rows

    # ---- weekly reports --------------------------------------------------------
    # PKM/Weekly Reports/YYYY/MM/<slug>/metadata.md, one folder per edition.
    # Skips any path component starting with "_" so the shipped _template/ and
    # _assets/ never land as phantom editions. A metadata.md whose report_date is
    # not a real YYYY-MM-DD (an untouched template copy) is skipped too.
    rows = 0
    wr_root = ROOT / "PKM" / "Weekly Reports"
    if wr_root.exists():
        for path in sorted(wr_root.rglob("metadata.md")):
            if any(part.startswith("_") for part in path.relative_to(wr_root).parts):
                continue
            fm, body = read_note(path)
            slug = fm_str(fm, "slug") or path.parent.name
            report_date = fm_str(fm, "report_date")
            if not (report_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(report_date))):
                continue
            html_render = fm_str(fm, "html_render")
            html_path = (str((path.parent / html_render).relative_to(ROOT))
                         if html_render else None)
            # podcast_path is folder-relative in the markdown (the audio lives in
            # PKM/Audio per the media rule), so resolve it against the edition folder.
            podcast = fm_str(fm, "podcast_path")
            podcast_path = None
            if podcast:
                try:
                    podcast_path = str((path.parent / podcast).resolve().relative_to(ROOT))
                except (OSError, ValueError):
                    podcast_path = podcast
            sj = fm.get("source_journal_entries") if isinstance(fm, dict) else None
            si = fm.get("source_images") if isinstance(fm, dict) else None
            cur.execute(
                "INSERT INTO weekly_reports (slug, report_date, edition, week_start, week_end,"
                " iso_week, title, status, html_path, podcast_path, podcast_duration,"
                " source_journal_entries, source_journal_count, source_images,"
                " source_images_count, pivotal_moments, search_expansion, body, file_path,"
                " raw_frontmatter) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (slug, report_date, fm_int(fm, "edition"), fm_str(fm, "week_start"),
                 fm_str(fm, "week_end"), fm_str(fm, "iso_week"), fm_str(fm, "title"),
                 fm_str(fm, "status"), html_path, podcast_path,
                 fm_str(fm, "podcast_duration"),
                 fm_list_json(fm, "source_journal_entries"),
                 len(sj) if isinstance(sj, list) else 0,
                 fm_list_json(fm, "source_images"),
                 len(si) if isinstance(si, list) else 0,
                 fm_list_json(fm, "pivotal_moments"),
                 fm_list_json(fm, "search_expansion"),
                 body.strip(), str(path.relative_to(ROOT)), fm_json(fm)))
            register("weekly_reports", slug)
            for raw, tslug, ltype in extract_links(body):
                link_rows.append(("weekly_reports", slug, raw, tslug, ltype))
            rows += 1
    stats["weekly_reports"] = rows

    # ---- transactions (example bank data; seeded from a JSON file) --------------
    # Markdown is canonical for NOTES; bank transactions are not notes, so the example
    # seeds them from a small JSON data file the regen reads. This is the worked
    # example of PERSISTING what a MoneyMoney-style reconcile step would discard. A
    # real install would point source_system at its own export instead. The seed is
    # OPTIONAL: a scaffold without it just gets an empty transactions table.
    rows = 0
    seed = ROOT / "PKM" / "Documents" / "_data" / "transactions.example.json"
    if seed.is_file():
        try:
            records = json.loads(seed.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            warnings.append(f"transactions seed is not valid JSON, skipped: {seed} ({e})")
            records = []
        for r in records if isinstance(records, list) else []:
            cur.execute(
                "INSERT INTO transactions (transaction_id, booking_date, value_date,"
                " amount, currency, counterparty_name, purpose, end_to_end_reference,"
                " booked, source_system, linked_invoice_slug, reconciliation_confidence,"
                " raw_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r.get("transaction_id"), r.get("booking_date"), r.get("value_date"),
                 r.get("amount"), r.get("currency"), r.get("counterparty_name"),
                 r.get("purpose"), r.get("end_to_end_reference"),
                 1 if r.get("booked", True) else 0, r.get("source_system"),
                 r.get("linked_invoice_slug"), r.get("reconciliation_confidence"),
                 json.dumps(r.get("raw_data", r), ensure_ascii=False)))
            rows += 1
    stats["transactions"] = rows

    # ---- notes_fts (global full-text search; item-8) ---------------------------
    # Populate the FTS5 index from the EXACT SAME rows the owned tables just got, so
    # it can never drift from them. One INSERT...SELECT per searchable source table,
    # mapping each table's title column (the §3 contract) onto the generic
    # (type, slug, entity_id, title, body) shape. `type` is the source table name —
    # the UI routes a hit to #/<type>/<slug>. The journal's title surface is `title`
    # and its body is the `content` column (not `body`); every other table uses
    # `body`. Library tables are discovered from LIBRARIES so a user-added library is
    # indexed automatically. Quotes are intentionally EXCLUDED: a quote's searchable
    # text is its quote_text and it has no note-route of its own in the cockpit nav
    # (it surfaces via the random-quote Hub, §8) — add it here only if a quote route
    # is introduced.
    #
    # (type, title_col, body_col) per searchable table. entity_id = the row's own id.
    FTS_SOURCES = [
        ("people",        "full_name",         "body"),
        ("organizations", "name",              "body"),
        ("topics",        "name",              "body"),
        ("projects",      "name",              "body"),
        ("goals",         "name",              "body"),
        ("key_elements",  "name",              "body"),
        ("habits",        "name",              "body"),
        ("documents",     "title",             "body"),
        ("deliverables",  "title",             "body"),
        ("journal",       "title",             "content"),
        ("outer_world",   "title",             "body"),
        ("workstreams",   "title",             "body"),
        ("sops",          "title",             "body"),
        ("guidelines",    "title",             "body"),
    ]
    # Every library mirror table carries the invariant (title, body) columns.
    for lib in LIBRARIES:
        FTS_SOURCES.append((lib["table"], "title", "body"))

    fts_rows = 0
    for src_table, title_col, body_col in FTS_SOURCES:
        cur.execute(
            f"INSERT INTO notes_fts (type, slug, entity_id, title, body) "
            f"SELECT '{src_table}', slug, id, {title_col}, {body_col} FROM {src_table}")
        fts_rows += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    # rowcount on INSERT...SELECT into a virtual table is unreliable across SQLite
    # builds; take the authoritative count from the table itself.
    fts_rows = cur.execute("SELECT COUNT(*) FROM notes_fts").fetchone()[0]
    stats["notes_fts"] = fts_rows

    # ---- links (resolved against the slug map) ---------------------------------
    for source_table, source_slug, raw, tslug, ltype in link_rows:
        cur.execute(
            "INSERT INTO links (source_table, source_slug, target_raw, target_slug, target_table, link_type)"
            " VALUES (?,?,?,?,?,?)",
            (source_table, source_slug, raw, tslug, slug_to_table.get(tslug), ltype))
    stats["links"] = len(link_rows)

    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)",
                ("generated_at", datetime.now().isoformat(timespec="seconds")))
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)",
                ("generator", "mypka-cockpit/scripts/regen-mypka-db.py"))

    con.commit()
    con.close()

    print(f"\n  mypka.db regenerated at {DB_PATH}")
    for t in ("people", "organizations", "topics", "projects", "goals",
              "key_elements", "habits", "documents", "journal",
              "deliverables", "quotes", "outer_world", "agents", "agent_journal",
              "workstreams", "sops", "guidelines",
              "transactions", "links"):
        print(f"    {t:<14} {stats.get(t, 0):>6} rows")
    for lib in LIBRARIES:
        t = lib["table"]
        print(f"    {t:<14} {stats.get(t, 0):>6} rows  (library)")
    print(f"    {'notes_fts':<14} {stats.get('notes_fts', 0):>6} rows  (full-text search)")
    if foreign:
        print(f"    preserved (not owned by this script): {', '.join(foreign)}")
    if warnings:
        print(f"\n  {len(warnings)} warning(s):")
        for w in warnings[:20]:
            print(f"    - {w}")
    print()


if __name__ == "__main__":
    main()
