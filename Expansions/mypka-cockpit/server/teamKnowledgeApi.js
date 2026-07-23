// teamKnowledgeApi.js — read-only list endpoints for the three Team-Knowledge
// doc families surfaced on the "My AI Team" fly-out: Workstreams, SOPs,
// Guidelines. Mirrors sessionLogsApi.js: SELECTs against the read-only mypka.db
// handle, rides the cockpit's standard `safe(handler)` envelope (so it inherits
// the SAME loopback/PIN/CSRF read-gate as every other /api/cockpit route), and
// degrades to a calm { available:false } envelope when the backing table is
// absent on a leaner mirror (a scaffold whose regen predates these tables).
//
//   GET /api/cockpit/team-knowledge/:family   (family ∈ workstreams|sops|guidelines)
//       { available, family, items } — items newest/id-ordered with the fields the
//       generic list view renders: slug, docId, title, status, owner, summary,
//       version, triggeredBy, domain, filePath.
//
// SCHEMA TOLERANCE (added v3.1.x): two different regen scripts populate these
// tables with DIFFERENT column shapes:
//   • Cockpit sample regen (scripts/regen-mypka-db.py shipped with the Expansion):
//       slug, doc_id, title, status, owner, summary, version, triggered_by, …
//   • A user's richer private regen (their own extended mirror script):
//       ws_id|sop_id|gl_id, slug, title, domain, status, owner, …, body — and
//       NO summary, NO version, NO triggered_by.
// This module no longer assumes a fixed column set. At module load it introspects
// each table with pragma_table_info, resolves which columns are actually present,
// builds the SELECT from only those columns, and synthesizes a summary from `body`
// when no summary column exists — so the SAME JSON item shape reaches the frontend
// regardless of which regen produced the file. The reader stays read-only and
// never interpolates request input into SQL identifiers.
import db from './db.js';

// The only three table names this module will ever touch. The :family route
// param is mapped through THIS map, so the table name in the SQL is a fixed
// literal from our own code — never a value derived from the request. (No SQL
// identifier interpolation of user input.)
const FAMILY_TABLE = {
  workstreams: 'workstreams',
  sops: 'sops',
  guidelines: 'guidelines',
};

// Candidate column names, in priority order, for each logical field. The first
// candidate that physically exists on the table wins. Every name here is from
// our own fixed code — never request input — so it is safe to embed in SQL.
const DOC_ID_CANDIDATES = ['doc_id', 'ws_id', 'sop_id', 'gl_id'];
const SUMMARY_CANDIDATES = ['summary']; // body is handled separately as a fallback
const TITLE_CANDIDATES = ['title'];
const STATUS_CANDIDATES = ['status'];
const OWNER_CANDIDATES = ['owner'];
const VERSION_CANDIDATES = ['version'];
const TRIGGERED_BY_CANDIDATES = ['triggered_by'];
const DOMAIN_CANDIDATES = ['domain'];
const FILE_PATH_CANDIDATES = ['file_path'];

// How many characters of `body` to keep when synthesizing a summary. Mirrors the
// length other list excerpts use; trimmed at a word boundary, single-lined.
const BODY_EXCERPT_LEN = 240;

function tableExists(name) {
  return !!db
    .prepare(`SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = ?`)
    .get(name);
}

// Set of physical column names on a table. The table name here is always a fixed
// literal from FAMILY_TABLE (never request input), so embedding it in the
// pragma_table_info() call is safe.
function columnSet(table) {
  const rows = db.prepare(`SELECT name FROM pragma_table_info(?)`).all(table);
  return new Set(rows.map((r) => r.name));
}

// First candidate that exists on the table, else null.
function pick(cols, candidates) {
  return candidates.find((c) => cols.has(c)) || null;
}

// Build a SELECT-list expression for a logical field, aliased so the row always
// carries the same property name regardless of which physical column backed it.
// Returns "NULL AS alias" when the field has no backing column on this table.
function col(name, alias) {
  return name ? `${name} AS ${alias}` : `NULL AS ${alias}`;
}

// One resolved reader per existing family table, prepared at module load (the
// same load-time-prepare idiom the rest of the server uses). A family whose table
// is absent maps to null and the reader returns { available:false } for it.
//
// Ordering: by the formal doc number when present (WS-001 < WS-002 < …) with the
// un-numbered docs after the numbered run, then by title. The doc-id column is
// whichever of doc_id/ws_id/sop_id/gl_id exists; values look like 'WS-12', so a
// plain string sort would put 'WS-12' before 'WS-2' — we sort on the numeric tail.
const READERS = Object.fromEntries(
  Object.entries(FAMILY_TABLE).map(([family, table]) => {
    if (!tableExists(table)) return [family, null];

    const cols = columnSet(table);
    const docIdCol = pick(cols, DOC_ID_CANDIDATES);
    const summaryCol = pick(cols, SUMMARY_CANDIDATES);
    const hasBody = cols.has('body');
    const versionCol = pick(cols, VERSION_CANDIDATES);
    const triggeredByCol = pick(cols, TRIGGERED_BY_CANDIDATES);
    const domainCol = pick(cols, DOMAIN_CANDIDATES);
    const slugCol = cols.has('slug') ? 'slug' : null;

    // Select-list: every logical field aliased to a stable property name. We pull
    // `body` raw (aliased) only when there's no summary column, so the reader can
    // synthesize an excerpt in JS without re-querying.
    const selectParts = [
      col(slugCol, 'slug'),
      col(docIdCol, 'doc_id'),
      col(pick(cols, TITLE_CANDIDATES), 'title'),
      col(pick(cols, STATUS_CANDIDATES), 'status'),
      col(pick(cols, OWNER_CANDIDATES), 'owner'),
      col(summaryCol, 'summary'),
      col(versionCol, 'version'),
      col(triggeredByCol, 'triggered_by'),
      col(domainCol, 'domain'),
      col(pick(cols, FILE_PATH_CANDIDATES), 'file_path'),
    ];
    if (!summaryCol && hasBody) {
      selectParts.push('body AS body');
    }

    // ORDER BY uses the resolved doc-id column. If the table somehow has no doc-id
    // column at all, fall back to ordering by title only.
    const orderBy = docIdCol
      ? `
        ORDER BY
          CASE WHEN ${docIdCol} IS NULL THEN 1 ELSE 0 END,
          CAST(
            COALESCE(
              NULLIF(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(${docIdCol}, '')),
                'WS-', ''), 'SOP-', ''), 'GL-', ''), ''),
              '999999'
            ) AS INTEGER
          ),
          title COLLATE NOCASE`
      : `ORDER BY title COLLATE NOCASE`;

    const stmt = db.prepare(
      `SELECT ${selectParts.join(', ')} FROM ${table} ${orderBy}`
    );

    return [
      family,
      {
        stmt,
        // Whether the table physically carries each optional field — lets the
        // envelope advertise field availability to the client if it ever wants
        // to hide a chip column wholesale (separate from per-row emptiness).
        has: {
          docId: !!docIdCol,
          summary: !!summaryCol || hasBody,
          version: !!versionCol,
          triggeredBy: !!triggeredByCol,
          domain: !!domainCol,
        },
      },
    ];
  }),
);

// Collapse a markdown body to a short single-line excerpt. Strips the leading
// frontmatter/heading noise a body might start with, flattens whitespace, and
// trims at a word boundary near BODY_EXCERPT_LEN.
function excerptFromBody(body) {
  if (!body) return null;
  const flat = String(body)
    .replace(/^---[\s\S]*?---\s*/, '') // any stray leading frontmatter block
    .replace(/^#{1,6}\s.*$/m, '')       // a leading markdown heading line
    .replace(/[#*_`>]/g, ' ')           // light markdown punctuation
    .replace(/\s+/g, ' ')
    .trim();
  if (!flat) return null;
  if (flat.length <= BODY_EXCERPT_LEN) return flat;
  const cut = flat.slice(0, BODY_EXCERPT_LEN);
  const lastSpace = cut.lastIndexOf(' ');
  return `${(lastSpace > 80 ? cut.slice(0, lastSpace) : cut).trim()}…`;
}

function shape(row) {
  // summary: prefer the real column, else a trimmed excerpt of body, else null.
  const summary = row.summary || excerptFromBody(row.body) || null;
  return {
    slug: row.slug,
    docId: row.doc_id || null,
    title: row.title || row.slug,
    status: row.status || null,
    owner: row.owner || null,
    summary,
    version: row.version || null,
    triggeredBy: row.triggered_by || null,
    domain: row.domain || null,
    filePath: row.file_path || null,
  };
}

function readFamily(family) {
  const reader = READERS[family];
  if (!reader) return { available: false, family, items: [] };
  const items = reader.stmt.all().map(shape);
  return { available: true, family, fields: reader.has, items };
}

export function registerTeamKnowledgeRoutes(app, { safe }) {
  app.get('/api/cockpit/team-knowledge/:family', safe((req) => {
    const family = String(req.params.family || '').toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(FAMILY_TABLE, family)) {
      // Unknown family — same calm absent envelope rather than a 500/404, so the
      // client renders the empty state instead of an error.
      return { available: false, family, items: [] };
    }
    return readFamily(family);
  }));
}

export { readFamily };
