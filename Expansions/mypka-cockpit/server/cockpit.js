// cockpit.js — the universal note layer over mypka.db (read-only).
//
// Implements Silas's data-layer contract:
//   Contract A — universal resolver: v_notes UNION across the 10 entity tables,
//     slug-based lookup with type-priority for collisions, raw_frontmatter as JSON.
//   Contract B — graph: outbound links + deduped backlinks, graceful degradation
//     for unresolved / non-entity targets, journal images via journal_media.
//
// Markdown is canonical; this never writes. Every statement is a SELECT.
import db from './db.js';
// Fleeting notes (Workbench docs) are INTENTIONALLY excluded from mypka.db
// (workbench.js — free-form, no-frontmatter, graph-excluded). Search + resolve
// still need to SEE them so [[wikilinks]] to fleeting notes work; both reads
// below are filesystem-only and read-only — the never-writes contract holds.
import { listWorkbenchDocs, readWorkbenchDoc } from './workbench.js';

// ---------------------------------------------------------------------------
// The 10 entity tables and their per-table column mapping (Silas's mapping).
// `title` is the human label column; it differs per table (people->full_name,
// journal->title, documents/deliverables->title, everything else->name).
// `body`  is the note body (journal->content, everything else->body).
// `subtitle` is a short scannable second line surfaced in lists (best-effort).
// ---------------------------------------------------------------------------
const ENTITY = {
  key_elements: { title: 'name', body: 'body', sub: 'description_short' },
  topics: { title: 'name', body: 'body', sub: 'key_element' },
  habits: { title: 'name', body: 'body', sub: 'cadence' },
  people: { title: 'full_name', body: 'body', sub: 'relation' },
  organizations: { title: 'name', body: 'body', sub: 'org_type' },
  projects: { title: 'name', body: 'body', sub: 'status' },
  goals: { title: 'name', body: 'body', sub: 'status' },
  documents: { title: 'title', body: 'body', sub: 'doc_type' },
  deliverables: { title: 'title', body: 'body', sub: null },
  journal: { title: 'title', body: 'content', sub: 'category' },
};

// Type-priority for slug collisions (Silas): a person beats a same-slug document.
// Lower index = higher priority. Drives which match is "primary".
const TYPE_PRIORITY = [
  'people', 'organizations', 'projects', 'goals', 'topics',
  'key_elements', 'habits', 'documents', 'deliverables', 'journal',
];

// Display labels for each entity type (used in nav + "also:" hints).
export const TYPE_LABELS = {
  key_elements: 'Key element',
  topics: 'Topic',
  habits: 'Habit',
  people: 'Person',
  organizations: 'Organization',
  projects: 'Project',
  goals: 'Goal',
  documents: 'Document',
  deliverables: 'Deliverable',
  journal: 'Journal',
};

const ENTITY_TABLES = Object.keys(ENTITY);
const ENTITY_SET = new Set(ENTITY_TABLES);

// ---------------------------------------------------------------------------
// Live-schema probe (same idiom as graph.js). The base regen does not always
// emit every optional column — e.g. `habits` historically ships with only
// `cadence` (no `started_on` / `status`), while the columnar list (item-7)
// wants all three. We probe each entity table's real column set once at module
// load and only ever SELECT columns that actually exist; absent columns are
// projected as NULL so a thin schema degrades to blank cells instead of a 500.
// Markdown stays canonical; this is purely defensive against regen variance.
// ---------------------------------------------------------------------------
const TABLE_COLS = new Map();
for (const t of ENTITY_TABLES) {
  try {
    const cols = db.prepare(`PRAGMA table_info(${t})`).all().map((c) => c.name);
    TABLE_COLS.set(t, new Set(cols));
  } catch {
    TABLE_COLS.set(t, new Set());
  }
}

/** Does entity table `t` actually carry column `col`? */
function hasCol(t, col) {
  return TABLE_COLS.get(t)?.has(col) ?? false;
}

/** A subtitle SQL expr that degrades to NULL when the source column is absent. */
function subExpr(t, m) {
  return m.sub && hasCol(t, m.sub) ? m.sub : 'NULL';
}

function priorityRank(type) {
  const i = TYPE_PRIORITY.indexOf(type);
  return i === -1 ? 999 : i;
}

// ---------------------------------------------------------------------------
// v_notes as a UNION ALL. We run it inline (NOT as a CREATE VIEW) because the
// regen drops views and the DB is opened read-only — a UNION expression is the
// safe, regen-proof form of the contract.
// Columns: type, id, slug, title, subtitle, file_path
// ---------------------------------------------------------------------------
const V_NOTES = ENTITY_TABLES
  .map((t) => {
    const m = ENTITY[t];
    const sub = subExpr(t, m);
    return `SELECT '${t}' AS type, id, slug, ${m.title} AS title, ${sub} AS subtitle, file_path FROM ${t}`;
  })
  .join('\n  UNION ALL\n  ');

// Nav counts: SELECT type, COUNT(*) FROM v_notes GROUP BY type.
const navCountsStmt = db.prepare(`
  SELECT type, COUNT(*) AS count FROM (
  ${V_NOTES}
  ) GROUP BY type
`);

export function getNavCounts() {
  const rows = navCountsStmt.all();
  const byType = Object.fromEntries(rows.map((r) => [r.type, r.count]));
  // Stable, intentional nav order (Health/Dashboard handled by the client).
  const order = [
    'journal', 'people', 'topics', 'projects', 'key_elements',
    'habits', 'goals', 'organizations', 'documents', 'deliverables',
  ];
  return order
    .filter((t) => byType[t] != null)
    .map((t) => ({ type: t, label: TYPE_LABELS[t], count: byType[t] }));
}

// ---------------------------------------------------------------------------
// List a single entity type (for the type-browse pages). Newest-first for
// journal (by entry_date); alpha by title for the rest. Paginated.
// ---------------------------------------------------------------------------
// Per-type EXTRA columns surfaced in the columnar list (item-7). Each entry is
// [outAlias, sqlExpr] where sqlExpr references the source table's own columns
// (a fixed allow-list — never user input — so interpolation is safe). The client
// renders these as right-aligned detail columns beside the title. Only columns
// the list table already carries are used; nothing is re-fetched per-row.
const LIST_COLUMNS = {
  people: [['relation', 'relation']],
  organizations: [['org_type', 'org_type']],
  topics: [['key_element', 'key_element']],
  projects: [['status', 'status']],
  goals: [['status', 'status'], ['key_element', 'key_element']],
  key_elements: [['status', 'status'], ['description', 'description_short']],
  habits: [['cadence', 'cadence'], ['started_on', 'started_on'], ['status', 'status']],
  documents: [['doc_type', 'doc_type']],
  deliverables: [],
  journal: [['category', 'category']],
};

export function listByType(type, { limit = 200, offset = 0 } = {}) {
  if (!ENTITY_SET.has(type)) return { type, items: [], total: 0, columns: [] };
  const m = ENTITY[type];
  const sub = subExpr(type, m);
  const order =
    type === 'journal'
      ? 'entry_date DESC, id DESC'
      : `${m.title} COLLATE NOCASE ASC`;
  const dateCol = type === 'journal' ? 'entry_date' : 'NULL';
  // Journal rows carry mood/energy the dated view renders as chips.
  const extra = type === 'journal' ? ', mood, energy' : ', NULL AS mood, NULL AS energy';
  // Per-type detail columns (item-7). Aliases are surfaced under `cols` on each
  // row; the column descriptor list rides on the response so the client can
  // render headers + adapt order without hardcoding the per-type shape.
  // DEFENSIVE: a thin regen may omit an optional detail column (e.g. `habits`
  // historically lacked `started_on` / `status`). For any column the table does
  // not actually carry we project `NULL` instead of the (nonexistent) column —
  // the descriptor still rides along so the header renders, the cell just blanks.
  // This keeps the endpoint forward+backward compatible: it never 500s on a
  // missing optional column, and lights up automatically once the regen emits it.
  const cols = LIST_COLUMNS[type] || [];
  const colSelect = cols
    .map(([alias, expr]) => `, ${hasCol(type, expr) ? expr : 'NULL'} AS col_${alias}`)
    .join('');
  // DATA-CONTRACT §15 — people + organizations carry `social_links` (TEXT, a JSON
  // array of {label,url}). It is NOT a sortable detail column; it rides as a
  // separate per-row field the client renders as a clickable chip cluster.
  // GUARDED by the same live-schema probe used above: a pre-§15 regen has no
  // `social_links` column, so we project nothing and the chips simply never
  // render (graceful degradation; never a 500). Lights up automatically once a
  // §15-aware regen emits the column.
  const hasSocial = (type === 'people' || type === 'organizations') && hasCol(type, 'social_links');
  const socialSelect = hasSocial ? ', social_links' : '';
  const rows = db
    .prepare(
      `SELECT slug, ${m.title} AS title, ${sub} AS subtitle, ${dateCol} AS date${extra}${colSelect}${socialSelect}
       FROM ${type} ORDER BY ${order} LIMIT ? OFFSET ?`
    )
    .all(limit, offset);
  // Fold the col_* fields into a tidy `cols` object per row (drops the prefix).
  const items = rows.map((r) => {
    const out = { slug: r.slug, title: r.title, subtitle: r.subtitle, date: r.date };
    if (type === 'journal') { out.mood = r.mood; out.energy = r.energy; }
    if (cols.length) {
      out.cols = {};
      for (const [alias] of cols) out.cols[alias] = r[`col_${alias}`] ?? null;
    }
    // socialLinks: pass the raw JSON string through verbatim (client parses +
    // validates per §15 render contract). Absent / NULL → field omitted.
    if (hasSocial && r.social_links) out.socialLinks = r.social_links;
    return out;
  });
  const total = db.prepare(`SELECT COUNT(*) AS c FROM ${type}`).get().c;
  return {
    type,
    label: TYPE_LABELS[type],
    items,
    total,
    // Column descriptors (alias only; the client owns the human header + width).
    columns: cols.map(([alias]) => alias),
  };
}

// ---------------------------------------------------------------------------
// Resolve a slug -> all matching notes across the 10 tables (Contract A).
// Slugs are NOT globally unique (7 collisions), so we return every match,
// ordered by type-priority. The first is "primary"; the rest are "auch:" hints.
// ---------------------------------------------------------------------------
const resolveStmt = db.prepare(`
  SELECT type, slug, title FROM (
  ${V_NOTES}
  ) WHERE slug = ?
`);

export function resolveSlug(slug) {
  const matches = resolveStmt.all(slug);
  matches.sort((a, b) => priorityRank(a.type) - priorityRank(b.type));
  return matches; // [] | [primary] | [primary, ...secondary]
}

// ---------------------------------------------------------------------------
// Fetch ONE note in full: body (untruncated), metadata (raw_frontmatter as a
// JSON object), plus the graph (outbound links + deduped backlinks).
// ---------------------------------------------------------------------------
function fetchRow(type, slug) {
  const m = ENTITY[type];
  // journal exposes extra display fields the viewer header uses.
  const extra =
    type === 'journal'
      ? ', entry_date, mood, mood_valence, energy, category, entry_type, '
        + 'original_body, integration_status, manually_added'
      : '';
  return db
    .prepare(
      `SELECT id, slug, ${m.title} AS title, ${m.body} AS body, file_path, raw_frontmatter${extra}
       FROM ${type} WHERE slug = ? LIMIT 1`
    )
    .get(slug);
}

function parseFrontmatter(raw) {
  if (!raw) return {};
  try {
    const obj = JSON.parse(raw);
    return obj && typeof obj === 'object' ? obj : {};
  } catch {
    return {};
  }
}

// Outbound links FROM this note. Clickable only when the target resolves to one
// of the 10 entity tables; everything else (target_table NULL, or a non-entity
// table like session_logs/news/navigation) degrades to a plain label.
const outboundStmt = db.prepare(`
  SELECT DISTINCT target_raw, target_slug, target_table, link_type
  FROM links
  WHERE source_table = ? AND source_slug = ?
  ORDER BY link_type, target_raw
`);

function shapeOutbound(rows) {
  return rows.map((r) => {
    const clickable = !!(r.target_table && ENTITY_SET.has(r.target_table) && r.target_slug);
    // DATA-CONTRACT §12 — resolve the target's human TITLE by (target_table,
    // target_slug) so the in-body renderer can show "Weekly Review" instead of
    // the raw slug. Reuses entityTitle() (the same per-table title-column lookup
    // backlinkTitle() uses). NULL when the target is an orphan (target_table NULL),
    // a non-entity table, or the resolved note has an empty title column → the
    // renderer then falls back to the slug. No schema change; the data is present.
    const title = clickable ? entityTitle(r.target_table, r.target_slug) : null;
    return {
      raw: r.target_raw,
      slug: r.target_slug,
      targetType: r.target_table,
      title, // resolved display title, or null (renderer falls back to slug)
      linkType: r.link_type, // 'wikilink' | 'embed'
      clickable,
    };
  });
}

// Backlinks: every distinct source that points AT this slug. DEDUPE on
// (source_table, source_slug) — the raw links table has near-duplicates
// (e.g. a target referenced twice in one note). Clickable only when the source
// is one of the 10 entity tables (a session_log/agent backlink is shown as a
// non-clickable provenance label).
const backlinkStmt = db.prepare(`
  SELECT DISTINCT source_table, source_slug
  FROM links
  WHERE target_slug = ?
  ORDER BY source_table, source_slug
`);

// Resolve a slug in a given entity table -> its human title column (DATA-CONTRACT
// §12: people.full_name, topics.name, journal.title, …). NULL for a non-entity
// table, a missing row, or an empty title cell — callers fall back to the slug.
// The table name comes ONLY from the ENTITY map (a fixed allow-list), so the
// interpolated column/table identifiers can never be attacker-controlled.
function entityTitle(table, slug) {
  if (!ENTITY_SET.has(table) || !slug) return null;
  const m = ENTITY[table];
  const row = db.prepare(`SELECT ${m.title} AS title FROM ${table} WHERE slug = ? LIMIT 1`).get(slug);
  const t = row && typeof row.title === 'string' ? row.title.trim() : '';
  return t || null;
}

// Resolve a backlink source -> its human title (only for entity tables).
function backlinkTitle(table, slug) {
  return entityTitle(table, slug);
}

function shapeBacklinks(targetSlug, selfType, selfSlug) {
  const rows = backlinkStmt.all(targetSlug);
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    // Don't list the note as a backlink to itself.
    if (r.source_table === selfType && r.source_slug === selfSlug) continue;
    const key = `${r.source_table}/${r.source_slug}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const clickable = ENTITY_SET.has(r.source_table);
    out.push({
      sourceType: r.source_table,
      slug: r.source_slug,
      title: clickable ? backlinkTitle(r.source_table, r.source_slug) || r.source_slug : r.source_slug,
      label: TYPE_LABELS[r.source_table] || r.source_table,
      clickable,
    });
  }
  return out;
}

// Journal images via the journal_media junction. The mirror stores file_path
// (relative to PKM/) but NOT the BLOB, so the client loads the bytes from a
// dedicated image route. We surface only image-like media (image/screenshot);
// audio is noted separately so the viewer can show a calm "Audio" chip.
const mediaStmt = db.prepare(`
  SELECT file_path, media_type, mime_type, caption, sort_order
  FROM journal_media
  WHERE journal_id = ?
  ORDER BY sort_order, id
`);

// Normalize a PKM-relative path the cockpit file/media routes can serve. Both
// guarded routes resolve their `path` arg against PKM/ (they PREPEND "PKM/"), so a
// value that ALREADY carries a leading "PKM/" (as journal frontmatter `source`
// does — e.g. "PKM/Audio/2025/08/foo.mp3") would resolve to PKM/PKM/Audio/… and
// 404. journal_media.file_path, by contrast, is stored WITHOUT the prefix
// ("Images/2025/08/foo.png"). We strip a single leading "PKM/" so EITHER
// convention yields the route-correct, prefix-free relative path. Also normalizes
// backslashes; leaves traversal/absolute paths for the route's own jail to reject.
function toPkmRelative(p) {
  if (typeof p !== 'string' || !p.trim()) return null;
  return p.trim().replace(/\\/g, '/').replace(/^PKM\//, '');
}

function shapeMedia(journalId, metadata) {
  const rows = mediaStmt.all(journalId);
  const images = [];
  let audioCount = 0;
  for (const r of rows) {
    if (r.media_type === 'audio') {
      audioCount += 1;
      continue;
    }
    images.push({
      // file_path is relative to PKM/ in the mirror; the client requests it
      // through /api/cockpit/media?path=... which serves from disk read-only.
      path: r.file_path,
      mediaType: r.media_type,
      caption: r.caption || null,
    });
  }
  // Voice entries carry the rendered Seneca audio under frontmatter `source`
  // (a PKM/-prefixed .mp3, e.g. "PKM/Audio/2025/08/…-stoic-mentor-….mp3"). We
  // surface a ready-to-play descriptor so Felix's <audio> needs ZERO knowledge of
  // the prefix quirk: `path` is the route-correct prefix-free relative path, and
  // `url` is the exact same-origin /api/cockpit/file URL the <audio src> uses (the
  // /file route now serves audio/* inline with the PKM jail + PIN gate intact).
  let audio = null;
  const rawSource = metadata && typeof metadata.source === 'string' ? metadata.source : null;
  if (rawSource && /\.(mp3|m4a|aac|wav|ogg|oga)$/i.test(rawSource)) {
    const rel = toPkmRelative(rawSource);
    if (rel) {
      audio = { path: rel, url: `/api/cockpit/file?path=${encodeURIComponent(rel)}` };
    }
  }
  return { images, audioCount, audio };
}

// v3 #4 — derive an in-app file PREVIEW from a note's frontmatter. Document notes
// carry the real file under `digital_location` (relative to PKM/, e.g.
// Documents/_files/foo.pdf). We surface a {path, kind, mime, previewable} the
// client renders inline via a native <iframe>/<embed> (PDF/image) — no renderer
// dep. Non-previewable types (docx/xlsx) still surface the path but flag
// previewable:false so the UI offers a calm "not previewable" note instead.
const PREVIEW_MIME = {
  pdf: 'application/pdf',
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg',
  gif: 'image/gif', webp: 'image/webp', svg: 'image/svg+xml', txt: 'text/plain',
};
// Frontmatter keys that may hold a file path, in priority order.
const FILE_FIELDS = ['digital_location', 'file', 'source_file', 'attachment', 'scan'];

function derivePreview(metadata) {
  for (const key of FILE_FIELDS) {
    const v = metadata[key];
    const candidate = Array.isArray(v) ? v.find((x) => typeof x === 'string') : v;
    if (typeof candidate !== 'string' || !candidate.trim()) continue;
    const rel = candidate.trim();
    // Only PKM-relative paths are servable through the guarded /file route.
    if (rel.startsWith('/') || rel.includes('..') || /^[a-z]+:\/\//i.test(rel)) {
      return { path: rel, kind: 'external', mime: null, previewable: false, field: key };
    }
    const ext = (rel.split('.').pop() || '').toLowerCase();
    const mime = PREVIEW_MIME[ext] || null;
    const kind = ext === 'pdf' ? 'pdf' : mime && mime.startsWith('image/') ? 'image' : ext === 'txt' ? 'text' : 'other';
    return { path: rel, kind, mime, previewable: !!mime, field: key, ext };
  }
  return null;
}

export function getNote(type, slug) {
  if (!ENTITY_SET.has(type)) return null;
  const row = fetchRow(type, slug);
  if (!row) return null;

  const metadata = parseFrontmatter(row.raw_frontmatter);
  const note = {
    type,
    slug: row.slug,
    title: row.title || slug,
    typeLabel: TYPE_LABELS[type],
    body: row.body || '',
    filePath: row.file_path || null,
    metadata,
    preview: derivePreview(metadata),
    outbound: shapeOutbound(outboundStmt.all(type, slug)),
    backlinks: shapeBacklinks(slug, type, slug),
  };

  if (type === 'journal') {
    // integration_status: 'integrated' | 'raw'. NULL is treated as 'raw' per
    // DATA-CONTRACT §10. The unfold-original affordance shows only when the entry
    // is 'integrated' AND original_body is present (the preserved verbatim text).
    const integrationStatus = row.integration_status === 'integrated' ? 'integrated' : 'raw';
    note.journal = {
      entryDate: row.entry_date || null,
      mood: row.mood || null,
      moodValence: row.mood_valence ?? null,
      energy: row.energy || null,
      category: row.category || null,
      entryType: row.entry_type || null,
      integrationStatus,
      // original_body is only meaningful once integrated; null otherwise (the
      // body IS the original for a raw entry — nothing to unfold).
      originalBody: integrationStatus === 'integrated' && typeof row.original_body === 'string' && row.original_body.trim()
        ? row.original_body
        : null,
      manuallyAdded: row.manually_added === 1 || row.manually_added === true,
    };
    note.media = shapeMedia(row.id, metadata);
  }

  return note;
}

// ---------------------------------------------------------------------------
// Title/slug search across all entity tables — powers the editor's [[ wikilink
// autocomplete. Prefix matches rank above substring matches; cheap LIKE over
// the same inline v_notes UNION the resolver uses. Read-only.
// ---------------------------------------------------------------------------
const searchStmt = db.prepare(`
  SELECT type, slug, title FROM (
  ${V_NOTES}
  ) WHERE title LIKE ? OR slug LIKE ?
  LIMIT 60
`);

// Fleeting notes rank BEFORE journal (the lowest entity priority) but after
// every other entity type — a half-step keeps the integer ranks untouched.
const FLEETING_RANK = TYPE_PRIORITY.indexOf('journal') - 0.5;
const searchRank = (type) => (type === 'fleeting' ? FLEETING_RANK : priorityRank(type));

export function searchNotes(q, limit = 12) {
  const needle = String(q || '').trim();
  if (!needle) return { items: [] };
  const rows = searchStmt.all(`%${needle}%`, `%${needle}%`);
  const low = needle.toLowerCase();
  // Merge fleeting-note matches (filesystem, not in mypka.db by design).
  // listWorkbenchDocs() returns null on a missing dir — calm-degrade to none.
  for (const d of listWorkbenchDocs() || []) {
    const title = (d.title || d.slug).toLowerCase();
    if (title.includes(low) || d.slug.toLowerCase().includes(low)) {
      rows.push({ type: 'fleeting', slug: d.slug, title: d.title || d.slug });
    }
  }
  rows.sort((a, b) => {
    const ap = (a.title || a.slug || '').toLowerCase().startsWith(low) ? 0 : 1;
    const bp = (b.title || b.slug || '').toLowerCase().startsWith(low) ? 0 : 1;
    if (ap !== bp) return ap - bp;
    return searchRank(a.type) - searchRank(b.type);
  });
  return {
    items: rows.slice(0, Math.min(25, limit)).map((r) => ({
      type: r.type,
      slug: r.slug,
      title: r.title || r.slug,
      label: r.type === 'fleeting' ? 'Fleeting note' : TYPE_LABELS[r.type],
    })),
  };
}

// ---------------------------------------------------------------------------
// GLOBAL full-text search (DATA-CONTRACT §13) — the ⌘K command palette.
//
// This is SEPARATE from searchNotes() above. searchNotes() is the cheap
// title/slug LIKE that powers the editor's [[ autocomplete and MUST stay as it
// is. globalSearch() runs the FTS5 BM25 query over the `notes_fts` index, which
// finally searches note BODIES, not just titles.
//
// `notes_fts` is built during regen (Silas's lane) and is NOT in the cockpit's
// REQUIRED_TABLES (db.js), so on a freshly-cloned scaffold — or before the first
// regen that ships the index — the table simply isn't there. We therefore:
//   1) detect the table at first call (cached), and
//   2) prepare the statement lazily (NOT at module load like searchStmt), so a
//      missing table never breaks the cockpit's boot-time prepare() pass.
// When the index is absent the route returns { available:false, items:[] } and
// the UI shows a calm "rebuild the index" hint instead of a 500.
//
// SECURITY: the user's text is bound as a PARAMETER (`?`), never concatenated —
// FTS5 MATCH has its own query grammar and is an injection surface otherwise.
let _ftsAvailable = null;     // null = unknown; true/false once probed
let _globalSearchStmt = null; // prepared on first successful probe

function ftsReady() {
  if (_ftsAvailable !== null) return _ftsAvailable;
  try {
    const row = db
      .prepare(`SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'`)
      .get();
    _ftsAvailable = !!row;
    if (_ftsAvailable) {
      // Exact query shape from DATA-CONTRACT §13.2. snippet col 4 = body;
      // bm25 weights title=5.0, body=1.0 (a title hit outranks a body hit ~5:1);
      // ORDER BY rank ASC (bm25 returns NEGATIVE scores; most-negative = best).
      _globalSearchStmt = db.prepare(`
        SELECT
          type,
          slug,
          entity_id,
          title,
          snippet(notes_fts, 4, '<mark>', '</mark>', '…', 12) AS snippet,
          bm25(notes_fts, 5.0, 1.0) AS rank
        FROM notes_fts
        WHERE notes_fts MATCH ?
        ORDER BY rank
        LIMIT ?
      `);
    }
  } catch {
    _ftsAvailable = false;
  }
  return _ftsAvailable;
}

// Turn a user's free-text query into a safe FTS5 MATCH expression. We keep this
// FORGIVING (as-you-type): split on whitespace, strip FTS5 syntax characters
// from each token so a stray quote/paren/minus can't change the query's meaning
// or error, AND-join the tokens, and append `*` to the LAST token for a prefix
// match (user types `mobil` → matches `mobility`). Returns '' when nothing
// usable remains (caller short-circuits to an empty result).
function buildFtsMatch(raw) {
  const tokens = String(raw || '')
    .toLowerCase()
    // Drop FTS5 operators/quoting/column-filter/separator punctuation so a stray
    // quote, paren, colon, or semicolon can't change the query's meaning OR throw
    // a "syntax error near" (which would silently return no hits). Keep letters,
    // digits, hyphens-inside-words, and unicode word chars (umlauts etc. — the
    // index is unicode61).
    .replace(/["()*:^;,.!?/\\[\]{}<>=&|~]/g, ' ')
    .split(/\s+/)
    .map((t) => t.replace(/^[-+]+/, '').trim()) // strip leading -/+ (NOT/boost)
    .filter(Boolean);
  if (tokens.length === 0) return '';
  // Prefix-match only the LAST token (the one still being typed); earlier tokens
  // are treated as complete words so results settle as the query grows.
  return tokens
    .map((t, i) => (i === tokens.length - 1 ? `${t}*` : t))
    .join(' AND ');
}

export function globalSearch(q, limit = 30) {
  const needle = String(q || '').trim();
  if (!needle) return { available: ftsReady(), items: [] };
  if (!ftsReady()) return { available: false, items: [] };
  const match = buildFtsMatch(needle);
  if (!match) return { available: true, items: [] };
  const cap = Math.max(1, Math.min(50, Number(limit) || 30));
  let rows;
  try {
    rows = _globalSearchStmt.all(match, cap);
  } catch {
    // A malformed MATCH (should be impossible after sanitising) degrades to no
    // hits rather than a 500 — search-as-you-type must never throw.
    return { available: true, items: [] };
  }
  return {
    available: true,
    items: rows.map((r) => ({
      type: r.type,
      slug: r.slug,
      entityId: r.entity_id,
      title: r.title || r.slug,
      snippet: r.snippet || '',
      // Display label reuses TYPE_LABELS; an unknown source table (a user-added
      // library indexed by the regen) falls back to a title-cased table name.
      label: TYPE_LABELS[r.type] || titleCaseType(r.type),
    })),
  };
}

function titleCaseType(t) {
  return String(t || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Resolve + fetch in one call: the universal entry point for any [[wikilink]]
// click. Returns the primary note plus any "also matches" (secondary) hints.
export function resolveNote(slug, preferredType) {
  const matches = resolveSlug(slug);
  if (matches.length === 0) {
    // Fleeting fallback: workbench docs live outside mypka.db, so the entity
    // resolver can never see them. Check the filesystem before giving up.
    // readWorkbenchDoc returns { ok:'bad'|'missing' } on failure (success has
    // no `ok` field) and runs the same slug whitelist/jail as the notes route.
    const doc = readWorkbenchDoc(String(slug || ''));
    if (!doc.ok) {
      return {
        found: true,
        slug,
        note: {
          type: 'fleeting',
          slug: doc.slug,
          title: doc.title,
          typeLabel: 'Fleeting note',
          body: doc.markdown,
          filePath: `PKM/Fleeting Notes/${doc.slug}.md`,
          metadata: {},
          outbound: [],
          backlinks: [],
        },
        secondary: [],
      };
    }
    return { found: false, slug, matches: [] };
  }
  // If the caller knows the type (came from a typed list), honor it.
  let primary = matches[0];
  if (preferredType) {
    const exact = matches.find((m) => m.type === preferredType);
    if (exact) primary = exact;
  }
  const note = getNote(primary.type, primary.slug);
  const secondary = matches
    .filter((m) => !(m.type === primary.type))
    .map((m) => ({ type: m.type, slug: m.slug, title: m.title, label: TYPE_LABELS[m.type] }));
  return { found: true, slug, note, secondary };
}

// ---------------------------------------------------------------------------
// Team roster (read-only). The `agents` table is Silas's team SSOT mirror; every
// active member carries a card-ready bio + a real avatar on disk (avatar_path is
// repo-relative, or NULL -> the client renders initials). Pure SELECT, alpha by
// the full "Name - Role" string; the client splits name/role on " - ".
// ---------------------------------------------------------------------------
const agentsStmt = db.prepare(`
  SELECT slug, name, folder, agent_status, bio, avatar_path, owner
  FROM agents
  WHERE agent_status = 'active'
  ORDER BY name
`);

export function listAgents() {
  return { agents: agentsStmt.all() };
}

// ---------------------------------------------------------------------------
// Team analytics — specialist session load over a selectable time range.
//
// Source: session_logs (one row per run; agent_id + timestamp). This is the same
// data the Week in Ink "team at work" slide renders, but unbounded by the weekly
// window so a range can span any period. Avatars come from agents.avatar_path and
// are served through the jailed /api/cockpit/avatar route; a specialist with no
// avatar on disk returns null and the client falls back to initials.
//
// Read-only. Dates are compared on substr(timestamp,1,10) because session_logs
// stores an ISO datetime and the range is day-granular.
// ---------------------------------------------------------------------------
const analyticsRangeStmt = db.prepare(`
  SELECT COALESCE(NULLIF(TRIM(s.agent_id), ''), 'unspecified') AS agent_slug,
         COUNT(*) AS sessions,
         MIN(substr(s.timestamp,1,10)) AS first_day,
         MAX(substr(s.timestamp,1,10)) AS last_day,
         MAX(a.avatar_path) AS avatar_path,
         MAX(a.name) AS name
    FROM session_logs s
    LEFT JOIN agents a
      ON a.slug = COALESCE(NULLIF(TRIM(s.agent_id), ''), '~no-agent~')
   WHERE s.timestamp IS NOT NULL AND s.timestamp <> ''
     AND substr(s.timestamp,1,10) >= @from
     AND substr(s.timestamp,1,10) <= @to
   GROUP BY agent_slug
   ORDER BY sessions DESC, agent_slug
`);

const analyticsSeriesStmt = db.prepare(`
  SELECT substr(s.timestamp,1,10) AS day,
         COALESCE(NULLIF(TRIM(s.agent_id), ''), 'unspecified') AS slug,
         COUNT(*) AS sessions
    FROM session_logs s
   WHERE s.timestamp IS NOT NULL AND s.timestamp <> ''
     AND substr(s.timestamp,1,10) >= @from
     AND substr(s.timestamp,1,10) <= @to
   GROUP BY day, slug
   ORDER BY day
`);

const analyticsBoundsStmt = db.prepare(`
  SELECT MIN(substr(timestamp,1,10)) AS first_day,
         MAX(substr(timestamp,1,10)) AS last_day,
         COUNT(*) AS total
    FROM session_logs
   WHERE timestamp IS NOT NULL AND timestamp <> ''
`);

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

export function teamAnalytics({ from, to } = {}) {
  const bounds = analyticsBoundsStmt.get() || {};
  const lo = ISO_DAY.test(String(from || '')) ? from : (bounds.first_day || '1970-01-01');
  const hi = ISO_DAY.test(String(to || '')) ? to : (bounds.last_day || '2999-12-31');
  const rows = analyticsRangeStmt.all({ from: lo, to: hi });
  const total = rows.reduce((n, r) => n + r.sessions, 0);
  // agents.name is the full "Name - Role" folder string; the client wants them
  // apart (RosterView splits the same way).
  const agents = rows.map((r) => ({
    slug: r.agent_slug,
    name: (r.name ? String(r.name).split(' - ')[0]
                  : r.agent_slug.charAt(0).toUpperCase() + r.agent_slug.slice(1)).trim(),
    role: r.name && String(r.name).includes(' - ')
      ? String(r.name).split(' - ').slice(1).join(' - ').trim() : null,
    sessions: r.sessions,
    share: total ? Math.round((r.sessions / total) * 100) : 0,
    avatarPath: r.avatar_path || null,
    firstDay: r.first_day,
    lastDay: r.last_day,
  }));

  // Daily totals, gap-filled so the sparkline has no phantom continuity.
  const byDay = new Map();
  for (const r of analyticsSeriesStmt.all({ from: lo, to: hi })) {
    byDay.set(r.day, (byDay.get(r.day) || 0) + r.sessions);
  }
  const series = [];
  const d = new Date(lo + 'T00:00:00Z');
  const end = new Date(hi + 'T00:00:00Z');
  while (d <= end && series.length < 800) {
    const key = d.toISOString().slice(0, 10);
    series.push({ day: key, sessions: byDay.get(key) || 0 });
    d.setUTCDate(d.getUTCDate() + 1);
  }

  return {
    range: { from: lo, to: hi },
    bounds: { from: bounds.first_day || null, to: bounds.last_day || null, total: bounds.total || 0 },
    totals: { sessions: total, specialists: agents.length, days: series.length,
              meanPerSpecialist: agents.length ? Math.round(total / agents.length) : 0 },
    agents,
    series,
  };
}

export { ENTITY, ENTITY_SET, ENTITY_TABLES };
