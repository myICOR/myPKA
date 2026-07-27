// server.js — local-only Express server for the myPKA Cockpit.
// Serves read-only JSON from mypka.db plus the built React app.
// Binds to 127.0.0.1 (loopback) by default; LAN exposure is opt-in and PIN-gated.
//
// Write surface (the ONLY writes this server can perform):
//   * Fleeting Notes create/save/attach — real markdown files under
//     PKM/Fleeting Notes/, behind WORKBENCH_WRITE_ENABLED + session + CSRF guards.
//   * Fleeting-Notes sidecars (pin/status meta + whiteboard layouts) — JSON
//     files inside the same jail, same guard stack.
// Everything else is a read-only GET. mypka.db is opened read-only (db.js);
// markdown stays canonical.
import express from 'express';
import path from 'node:path';
import fs from 'node:fs';
import https from 'node:https';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { DB_PATH, REPO_ROOT } from './db.js';
import {
  getNavCounts, listByType, resolveNote, getNote, listAgents, searchNotes, globalSearch,
  teamAnalytics
} from './cockpit.js';
import { getNeighborhood } from './graph.js';
import {
  readWorkbenchDoc,
  createWorkbenchDoc,
  saveWorkbenchDoc,
  deleteWorkbenchDoc,
  writeWorkbenchAttachment,
} from './workbench.js';
import {
  listNotes, patchNoteMeta,
  listBoards, readBoard, createBoard, saveBoard, deleteBoard,
} from './fleeting.js';
import {
  createJournalEntry, listRawManualEntries, resolveJournalEntryPath,
} from './journalEntries.js';
import { describeRegistry, taskConnectors, labelForSource } from './connectors/registry.js';
import { setEnvKey, clearEnvKey, getAgenda, listStoredKeyNames } from './connectorAdmin.js';
import { registerPlannerRoutes } from './plannerRoutes.js';
import { registerWellnessRoutes } from './wellness.js';
import { registerFileTreeRoutes } from './filetree.js';
import { registerDocumentsRoutes } from './documentsApi.js';
import { registerJournalFeed } from './journalFeed.js';
import { registerInvoicesRoutes } from './invoicesApi.js';
import { registerSerendipityRoutes } from './serendipityApi.js';
import { registerLibraryRoutes } from './libraryApi.js';
import { registerOuterWorldRoutes } from './outerWorldApi.js';
import { registerAgentRoutes } from './agentApi.js';
import { registerSessionLogsRoutes } from './sessionLogsApi.js';
import { registerTeamKnowledgeRoutes } from './teamKnowledgeApi.js';
import { registerCockpitSettingsRoutes } from './cockpitSettingsRoutes.js';
import {
  isPinConfigured, resolvePinHash, verifyPin,
  createSession, isValidSession, destroySession, readSessionCookie,
  buildSessionCookie, buildClearCookie,
  checkLock, recordFailure, recordSuccess, loginDelay,
  MIN_PIN_LENGTH,
} from './auth.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 4317;

// Cockpit version (from package.json) + boot time — exposed on /api/health so a
// stale instance is detectable at a glance.
const PKG = JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', 'package.json'), 'utf8'));
const STARTED_AT = new Date().toISOString();

// ---- Bind decision (fail-closed LAN exposure) -------------------------------
// Default: loopback only (127.0.0.1). LAN bind (0.0.0.0) is opt-in via
// COCKPIT_BIND_LAN=1 AND is HARD-GATED on a configured PIN: the cockpit serves
// your whole second brain (journal / CRM / documents), so it refuses to start
// over the network without a gate. Fail-closed, always.
const BIND_LAN = process.env.COCKPIT_BIND_LAN === '1';
const HOST = BIND_LAN ? '0.0.0.0' : '127.0.0.1';

// TLS flag — single switch. Flipping COCKPIT_USE_TLS=1 (with a cert/key) makes
// the session cookie `Secure` and serves HTTPS.
const USE_TLS = process.env.COCKPIT_USE_TLS === '1';
const COOKIE_OPTS = { secure: USE_TLS };

if (BIND_LAN && !isPinConfigured()) {
  console.error('\n  ✗ Refusing to start.');
  console.error('  COCKPIT_BIND_LAN=1 requests LAN exposure, but no PIN is configured.');
  console.error('  The cockpit serves sensitive data (journal / CRM / documents)');
  console.error('  and will NOT bind the LAN without a PIN gate.\n');
  console.error('  Set a PIN first:   npm run set-pin');
  console.error('  Then relaunch in LAN mode.\n');
  process.exit(1);
}

const app = express();

app.use((req, res, next) => {
  res.set('Cache-Control', 'no-store');
  next();
});

// JSON body parsing is scoped TIGHTLY per write route — we do NOT
// app.use(express.json()) globally, so the read surface keeps zero body-parsing
// attack surface.
const writeJson = express.json({ limit: '4kb' });

// ---- CSRF / local-write guard for the write surface --------------------------
//   1. Custom header `X-Cockpit: 1` — a cross-site <form>/fetch from another
//      origin CANNOT set a custom request header without a CORS preflight, and we
//      send no permissive CORS headers. Same-origin cockpit JS sets it.
//   2. Origin/Referer, when present, must match the cockpit's own origin.
//   Either check failing -> 403.
const COCKPIT_LOOPBACK_ORIGIN = `http://127.0.0.1:${PORT}`;

function requireSession(req, res, next) {
  if (isValidSession(readSessionCookie(req))) return next();
  return res.status(401).json({ error: 'unauthorized', auth: 'pin-required' });
}

function localWriteGuard(req, res, next) {
  if (req.get('X-Cockpit') !== '1') {
    return res.status(403).json({ error: 'forbidden: missing cockpit header' });
  }
  const proto = (req.get('X-Forwarded-Proto') || req.protocol || 'http').split(',')[0].trim();
  const selfOrigin = `${proto}://${req.get('Host')}`;
  const allowed = (o) => o === selfOrigin || o === COCKPIT_LOOPBACK_ORIGIN;

  const origin = req.get('Origin');
  let ok = false;
  if (origin) {
    ok = allowed(origin);
  } else {
    const referer = req.get('Referer');
    if (referer) {
      try {
        ok = allowed(new URL(referer).origin);
      } catch {
        ok = false;
      }
    } else {
      // No Origin and no Referer — accept (header + cookie carry the defense).
      ok = true;
    }
  }
  if (!ok) {
    return res.status(403).json({ error: 'forbidden: bad origin' });
  }
  return next();
}

function safe(handler) {
  return (req, res) => {
    try {
      res.json(handler(req));
    } catch (err) {
      console.error(`[${req.path}]`, err);
      res.status(500).json({ error: err.message });
    }
  };
}

// Async twin of safe() — awaits the handler so async route bodies (the planner
// reads, the task-source reads) get the same calm catch → 500 envelope.
function safeAsync(handler) {
  return async (req, res) => {
    try {
      res.json(await handler(req));
    } catch (err) {
      console.error(`[${req.path}]`, err);
      res.status(500).json({ error: err.message });
    }
  };
}

// ---- Auth: PIN login + session gate -----------------------------------------
// POST /api/auth/login {pin} -> on success a httpOnly session cookie; an auth
// middleware then gates EVERY /api/* route except the login route itself and the
// health probe.
//
// LOOPBACK CONVENIENCE: when no PIN is configured AND the server is loopback-only,
// the auth middleware passes everything through — a single-user local app on
// 127.0.0.1 needs no login screen. The moment a PIN is configured (or LAN mode is
// on, which REQUIRES one), the gate is fully active.
const loginJson = express.json({ limit: '1kb' });

// DNS-rebinding guard for the PIN-less loopback convenience: a hostile page can
// point its own domain at 127.0.0.1 and fetch with a non-loopback Host header.
// Honouring the convenience ONLY for genuine loopback Hosts closes that door.
function isLoopbackHost(req) {
  const host = String(req.get('Host') || '').toLowerCase();
  return host.startsWith('127.0.0.1') || host.startsWith('localhost') || host.startsWith('[::1]');
}

const AUTH_PUBLIC = new Set(['/auth/login', '/health']);
app.use('/api', (req, res, next) => {
  if (AUTH_PUBLIC.has(req.path)) return next();
  if (!BIND_LAN && !isPinConfigured() && isLoopbackHost(req)) return next(); // loopback, no PIN set
  const sid = readSessionCookie(req);
  if (isValidSession(sid)) return next();
  return res.status(401).json({ error: 'unauthorized', auth: 'pin-required' });
});

// Brute-force throttle: 5 failures -> 15-min lockout; every attempt incurs a
// random 200..500ms delay. Success resets the counter.
app.post('/api/auth/login', loginJson, async (req, res) => {
  const lock = checkLock();
  if (lock.locked) {
    const retryAfterS = Math.ceil(lock.retryAfterMs / 1000);
    res.set('Retry-After', String(retryAfterS));
    return res.status(429).json({
      error: 'locked',
      retryAfterSeconds: retryAfterS,
      message: 'Too many attempts. Please wait 15 minutes.',
    });
  }

  await loginDelay();

  const stored = resolvePinHash();
  if (!stored) {
    return res.status(503).json({ error: 'no-pin-configured' });
  }

  const pin = req.body && typeof req.body === 'object' ? req.body.pin : undefined;
  if (typeof pin !== 'string' || pin.length < MIN_PIN_LENGTH) {
    recordFailure();
    return res.status(401).json({ error: 'invalid-pin' });
  }

  if (!verifyPin(pin, stored)) {
    recordFailure();
    return res.status(401).json({ error: 'invalid-pin' });
  }

  recordSuccess();
  const sid = createSession();
  res.set('Set-Cookie', buildSessionCookie(sid, COOKIE_OPTS));
  return res.json({ ok: true });
});

app.post('/api/auth/logout', (req, res) => {
  const sid = readSessionCookie(req);
  destroySession(sid);
  res.set('Set-Cookie', buildClearCookie(COOKIE_OPTS));
  return res.json({ ok: true });
});

// Cheap "am I logged in?" probe for the frontend on boot.
app.get('/api/auth/status', (req, res) => res.json({ ok: true }));

// Health/identity probe (public, carries no sensitive data).
app.get('/api/health', (req, res) => {
  res.json({
    ok: true,
    db: DB_PATH,
    dbMtime: fs.existsSync(DB_PATH) ? fs.statSync(DB_PATH).mtime.toISOString() : null,
    port: PORT,
    startedAt: STARTED_AT,
    cockpitVersion: PKG.version,
  });
});

// ---- Cockpit: universal note layer ------------------------------------------

// Sidebar nav counts: SELECT type, COUNT(*) FROM v_notes GROUP BY type.
app.get('/api/cockpit/nav', safe(() => ({ types: getNavCounts() })));

// Browse one entity type (paginated list of {slug,title,subtitle,date}).
app.get('/api/cockpit/type/:type', safe((req) =>
  listByType(req.params.type, {
    limit: Math.min(500, Number(req.query.limit) || 200),
    offset: Number(req.query.offset) || 0,
  })
));

// Title/slug search for the editor's [[ autocomplete (and anything else).
// UNCHANGED — the cheap LIKE over titles/slugs. Do not fold the FTS search into
// this route; the [[ autocomplete wants title/slug prefix ranking, not BM25.
app.get('/api/cockpit/search', safe((req) =>
  searchNotes(String(req.query.q || ''), Number(req.query.limit) || 12)
));

// Global full-text search (DATA-CONTRACT §13) — the ⌘K command palette. FTS5
// BM25 over note titles AND bodies. Inherits the same /api read-gate
// (loopback/PIN/CSRF) as every other cockpit route. Returns { available, items }
// — available:false when the `notes_fts` index hasn't been built by a regen yet.
app.get('/api/cockpit/search/global', safe((req) =>
  globalSearch(String(req.query.q || ''), Number(req.query.limit) || 30)
));

// Resolve a [[wikilink]] slug -> primary note (+ "also:" secondary matches).
app.get('/api/cockpit/resolve/:slug', safe((req) =>
  resolveNote(req.params.slug, req.query.type || null)
));

// Fetch a single note by explicit type+slug (skips the collision resolver).
app.get('/api/cockpit/note/:type/:slug', safe((req) => {
  const note = getNote(req.params.type, req.params.slug);
  return note ? { found: true, note, secondary: [] } : { found: false, slug: req.params.slug };
}));

// Knowledge-graph mini-graph — a note's 2-hop neighborhood (read-only).
// Params clamped: depth ∈ {1,2} (default 2), cap ∈ [1..50] (default 12).
app.get('/api/cockpit/graph/neighborhood/:type/:slug', safe((req) => {
  const depth = Number(req.query.depth) === 1 ? 1 : 2;
  let cap = Number(req.query.cap);
  if (!Number.isInteger(cap) || cap < 1) cap = 12;
  if (cap > 50) cap = 50;
  return getNeighborhood(req.params.type, req.params.slug, { depth, cap });
}));

// Team roster — read-only list of the active specialists (slug, "Name - Role",
// bio, avatar_path, owner). The client renders avatars via /api/cockpit/avatar.
app.get('/api/cockpit/agents', safe(() => listAgents()));

// Team analytics — specialist session load across a selectable range (read-only).
app.get('/api/cockpit/analytics/team', safe((req) =>
  teamAnalytics({ from: req.query.from, to: req.query.to })));

// ---- Read-only file containment ----------------------------------------------
// path.relative() is the containment check (NOT a string prefix — a sibling dir
// like `PKM-secrets/` would fool startsWith). A result that escapes upward or
// resolves absolute is "outside the jail". Never writes.
const PKM_DIR = path.resolve(REPO_ROOT, 'PKM');
function containedPkmPath(rel) {
  if (!rel || rel.includes('\0')) return null;
  const abs = path.resolve(PKM_DIR, rel);
  const relToPkm = path.relative(PKM_DIR, abs);
  if (relToPkm === '' || relToPkm.startsWith('..') || path.isAbsolute(relToPkm)) return null;
  return abs;
}

// Second jail: Deliverables/ (inline preview of produced artifacts). Input is
// repo-relative ("Deliverables/2026-…/brief.md"). NO other root is reachable:
// the repo root, Team Knowledge/, and any .env file fall through both
// path.relative() checks -> 403.
const DELIVERABLES_DIR = path.resolve(REPO_ROOT, 'Deliverables');
function containedDeliverablesPath(rel) {
  if (!rel || rel.includes('\0')) return null;
  const abs = path.resolve(REPO_ROOT, rel);
  const relToDeliverables = path.relative(DELIVERABLES_DIR, abs);
  if (relToDeliverables === '' || relToDeliverables.startsWith('..') || path.isAbsolute(relToDeliverables)) return null;
  return abs;
}

// Third jail: Team Knowledge/ (inline preview of the Workstreams / SOPs /
// Guidelines markdown the "My AI Team" fly-out lists link to). Input is repo-
// relative ("Team Knowledge/Workstreams/WS-001-….md"). Same containment posture as
// the Deliverables jail — read-only, path.relative() bounded, inline-MIME gated by
// the route — and NO other root is reachable: the repo root, PKM/, and any .env
// file all fall through path.relative() -> 403.
const TEAM_KNOWLEDGE_DIR = path.resolve(REPO_ROOT, 'Team Knowledge');
function containedTeamKnowledgePath(rel) {
  if (!rel || rel.includes('\0')) return null;
  const abs = path.resolve(REPO_ROOT, rel);
  const relToTk = path.relative(TEAM_KNOWLEDGE_DIR, abs);
  if (relToTk === '' || relToTk.startsWith('..') || path.isAbsolute(relToTk)) return null;
  return abs;
}

// ---- LLM CLI command (configurable) ------------------------------------------
// Which CLI the "Discuss with AI" / wire-assistant / quick-launch-terminal buttons
// launch. Defaults to `claude`. A Codex/Gemini/other user sets COCKPIT_LLM_CMD=codex
// (or `gemini`, etc.) to launch their CLI instead. Documented in .env.example and
// launcher/GENERATE-LAUNCHER.md.
//
// SAFETY: this string is interpolated into a spawned `osascript`/Terminal command.
// We constrain it to a bare command token (letters, digits, _ . - and an OPTIONAL
// single absolute/relative path, no spaces, no shell metacharacters) so it can
// never carry an injection payload. An invalid value falls back to `claude` with a
// one-line log — fail safe, never fail open. The arguments to the CLI (the prompt)
// keep their existing single-quote escaping; this only governs the command token.
const LLM_CMD_DEFAULT = 'claude';
function resolveLlmCmd() {
  const raw = process.env.COCKPIT_LLM_CMD;
  if (raw === undefined || raw === null || String(raw).trim() === '') return LLM_CMD_DEFAULT;
  const v = String(raw).trim();
  // Allow a plain command name or a path to a binary; reject anything with shell
  // metacharacters / whitespace that could break out of the command position.
  if (/^[A-Za-z0-9_./-]+$/.test(v)) return v;
  console.error(
    `  server: COCKPIT_LLM_CMD="${raw}" contains disallowed characters — ` +
    `falling back to "${LLM_CMD_DEFAULT}". Use a bare command name or a path ` +
    `(letters, digits, _ . - / only).`
  );
  return LLM_CMD_DEFAULT;
}
// Resolved once at boot. The `--model` flag is Claude-specific: it is only added
// when the resolved command is exactly `claude` (see the discuss block). Other
// CLIs (codex/gemini/…) get the prompt with no Claude-only flags.
const LLM_CMD = resolveLlmCmd();
const LLM_IS_CLAUDE = LLM_CMD === LLM_CMD_DEFAULT;

// Read-only journal image route. journal_media.file_path is relative to PKM/.
app.get('/api/cockpit/media', (req, res) => {
  const abs = containedPkmPath(String(req.query.path || ''));
  if (!abs) return res.status(403).json({ error: 'forbidden' });
  if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
    return res.status(404).json({ error: 'not found' });
  }
  res.sendFile(abs);
});

// Read-only document/file preview route. Serves preview-safe types INLINE with a
// conservative Content-Type and a tight no-script CSP. Never writes.
const INLINE_MIME = {
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  // Markdown is served as TEXT, never as HTML — the client renders it through
  // the sanitized markdown component; the strict embed CSP below means nothing
  // executes even if a browser tried to interpret it.
  '.md': 'text/markdown; charset=utf-8',
  // Audio attached to journal entries streams through the same jail + gate
  // (sendFile honours Range, so seeking works).
  '.mp3': 'audio/mpeg',
  '.m4a': 'audio/mp4',
  '.aac': 'audio/aac',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.oga': 'audio/ogg',
};
app.get('/api/cockpit/file', (req, res) => {
  const rel = String(req.query.path || '');
  // Three jails with DIFFERENT base conventions, routed by the path's own root so
  // none shadows the others: Deliverables/ and Team Knowledge/ paths are
  // REPO_ROOT-relative; everything else is PKM/-relative.
  const norm = rel.replace(/\\/g, '/');
  let abs;
  if (norm === 'Deliverables' || norm.startsWith('Deliverables/')) {
    abs = containedDeliverablesPath(rel);
  } else if (norm === 'Team Knowledge' || norm.startsWith('Team Knowledge/')) {
    abs = containedTeamKnowledgePath(rel);
  } else {
    abs = containedPkmPath(rel);
  }
  if (!abs) return res.status(403).json({ error: 'forbidden' });
  if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
    return res.status(404).json({ error: 'not found' });
  }
  const ext = path.extname(abs).toLowerCase();
  const mime = INLINE_MIME[ext];
  if (!mime) return res.status(415).json({ error: 'no inline preview for this type', ext });
  res.set('Content-Type', mime);
  res.set('Content-Disposition', 'inline');
  res.set('Content-Security-Policy', "default-src 'none'; img-src 'self'; object-src 'self'; style-src 'unsafe-inline'");
  res.set('X-Content-Type-Options', 'nosniff');
  res.sendFile(abs);
});

// ---- Fleeting Notes (jailed under PKM/Fleeting Notes/) -----------------------
// The capture surface: frontmatter-free markdown docs + two cockpit-owned JSON
// sidecars (_meta.json for pin/status/color, _boards/*.json for whiteboards).
// Containment lives in workbench.js / fleeting.js: slug whitelist BEFORE any FS
// call, path.relative() jails, symlink rejection, atomic writes, hard caps.

// GET /api/cockpit/notes — doc list with meta merged (pinned first, then mtime).
app.get('/api/cockpit/notes', (req, res) => {
  const docs = listNotes();
  if (docs === null) {
    return res.json({ ok: false, reason: 'notes-unavailable', docs: [] });
  }
  res.json({ ok: true, docs });
});

// GET /api/cockpit/notes/:slug — open one doc.
app.get('/api/cockpit/notes/:slug', (req, res) => {
  const doc = readWorkbenchDoc(req.params.slug);
  if (doc.ok === 'bad') {
    return res.status(400).json({ ok: false, reason: 'bad-slug' });
  }
  if (doc.ok === 'missing') {
    return res.status(404).json({ ok: false, reason: 'not-found' });
  }
  res.json({
    ok: true,
    slug: doc.slug,
    title: doc.title,
    markdown: doc.markdown,
    mtime: doc.mtime,
  });
});

// ---- Fleeting Notes writes — the cockpit's only write surface.
// Gated behind WORKBENCH_WRITE_ENABLED (the launcher sets it to 1 by default;
// set it to anything else to run fully read-only).
//   Stack: writeGate -> session (or loopback w/o PIN) -> CSRF guard -> parser
function workbenchWriteGate(req, res, next) {
  if (process.env.WORKBENCH_WRITE_ENABLED !== '1') {
    return res.status(503).json({
      ok: false, reason: 'disabled',
      message: 'Fleeting Notes writes are disabled (WORKBENCH_WRITE_ENABLED is not 1).',
    });
  }
  return next();
}

// Dedicated parser for the doc routes ONLY — a document can run to ~200 KB of
// markdown. The independent 200 KB content-byte cap lives in workbench.js (-> 413).
const workbenchWriteJson = express.json({ limit: '256kb' });

// Loopback-without-PIN convenience mirrors the /api middleware: requireSession
// would 401 every write when no PIN exists, so swap it for a pass-through there.
function sessionOrLoopback(req, res, next) {
  if (!BIND_LAN && !isPinConfigured() && isLoopbackHost(req)) return next();
  return requireSession(req, res, next);
}

const WORKBENCH_WRITE_STACK = [workbenchWriteGate, sessionOrLoopback, localWriteGuard, workbenchWriteJson];

// Shared body-object guard: must be a plain object, strict key allow-list.
function readWorkbenchBody(req, res, allowed) {
  const body = req.body;
  if (body === null || typeof body !== 'object' || Array.isArray(body)) {
    res.status(400).json({ ok: false, error: 'body must be a JSON object' });
    return null;
  }
  const extras = Object.keys(body).filter((k) => !allowed.has(k));
  if (extras.length) {
    res.status(400).json({ ok: false, error: `unexpected field(s): ${extras.join(', ')}` });
    return null;
  }
  return body;
}

// POST /api/cockpit/notes   body { title: string, markdown?: string }
app.post('/api/cockpit/notes', ...WORKBENCH_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['title', 'markdown']));
  if (body === null) return;
  if (typeof body.title !== 'string' || !body.title.trim()) {
    return res.status(400).json({ ok: false, error: 'title is required (non-empty string)' });
  }
  if ('markdown' in body && typeof body.markdown !== 'string') {
    return res.status(400).json({ ok: false, error: 'markdown must be a string when present' });
  }
  let out;
  try {
    out = createWorkbenchDoc(body.title, 'markdown' in body ? body.markdown : '');
  } catch (err) {
    console.error('[POST /api/cockpit/notes]', err.message);
    return res.status(500).json({ ok: false, error: 'note create failed' });
  }
  switch (out.ok) {
    case 'bad-title': return res.status(400).json({ ok: false, error: 'title produced an empty slug' });
    case 'reserved':  return res.status(400).json({ ok: false, error: 'title resolves to a reserved name' });
    case 'too-large': return res.status(413).json({ ok: false, error: 'content exceeds the size limit' });
    case 'collision': return res.status(409).json({ ok: false, error: 'a note with that slug already exists', slug: out.slug });
    case 'created':   return res.status(201).json({ ok: true, slug: out.slug, title: out.title, mtime: out.mtime });
    default:          return res.status(500).json({ ok: false, error: 'unexpected create result' });
  }
});

// PUT /api/cockpit/notes/:slug   body { markdown: string, baseMtime?: number }
app.put('/api/cockpit/notes/:slug', ...WORKBENCH_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['markdown', 'baseMtime']));
  if (body === null) return;
  if (typeof body.markdown !== 'string') {
    return res.status(400).json({ ok: false, error: 'markdown is required (string)' });
  }
  if ('baseMtime' in body && body.baseMtime !== null && typeof body.baseMtime !== 'number') {
    return res.status(400).json({ ok: false, error: 'baseMtime must be a number or null when present' });
  }
  let out;
  try {
    out = saveWorkbenchDoc(req.params.slug, body.markdown, 'baseMtime' in body ? body.baseMtime : undefined);
  } catch (err) {
    console.error(`[PUT /api/cockpit/notes/${req.params.slug}]`, err.message);
    return res.status(500).json({ ok: false, error: 'note save failed' });
  }
  switch (out.ok) {
    case 'bad':       return res.status(400).json({ ok: false, error: 'bad slug or body' });
    case 'too-large': return res.status(413).json({ ok: false, error: 'content exceeds the size limit' });
    case 'missing':   return res.status(404).json({ ok: false, error: 'not-found' });
    case 'stale':     return res.status(412).json({ ok: false, error: 'file changed under the editor; reload before saving', mtime: out.mtime });
    case 'saved':     return res.status(200).json({ ok: true, slug: out.slug, mtime: out.mtime });
    default:          return res.status(500).json({ ok: false, error: 'unexpected save result' });
  }
});

// PATCH /api/cockpit/notes/:slug/meta   body { pinned?, status?, color? }
// Pin/unpin, move through capture -> working -> ready, recolor. Sidecar-only —
// the markdown file is untouched.
app.patch('/api/cockpit/notes/:slug/meta', ...WORKBENCH_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['pinned', 'status', 'color']));
  if (body === null) return;
  const out = patchNoteMeta(req.params.slug, body);
  if (!out) return res.status(400).json({ ok: false, error: 'bad slug or meta patch' });
  return res.json({ ok: true, ...out });
});

// DELETE /api/cockpit/fleeting/:slug — delete one fleeting note (Feature #10).
// Same write stack as the create/save routes (gate → session/loopback → CSRF).
// The path-jail lives in workbench.deleteWorkbenchDoc: slug whitelist BEFORE any
// FS call, realpath-anchored containment to PKM/Fleeting Notes/ ONLY, symlink/
// non-regular-target rejection right before the unlink. Anything resolving
// outside the jail returns 'bad' → 400. No request body.
app.delete('/api/cockpit/fleeting/:slug', workbenchWriteGate, sessionOrLoopback, localWriteGuard, (req, res) => {
  let out;
  try {
    out = deleteWorkbenchDoc(req.params.slug);
  } catch (err) {
    console.error(`[DELETE /api/cockpit/fleeting/${req.params.slug}]`, err.message);
    return res.status(500).json({ ok: false, error: 'note delete failed' });
  }
  switch (out.ok) {
    case 'bad':     return res.status(400).json({ ok: false, error: 'bad slug' });
    case 'missing': return res.status(404).json({ ok: false, error: 'not-found' });
    case 'deleted': return res.status(200).json({ ok: true, slug: out.slug });
    default:        return res.status(500).json({ ok: false, error: 'unexpected delete result' });
  }
});

// ---- Whiteboards (Fleeting-Notes boards, _boards/*.json) ---------------------
app.get('/api/cockpit/boards', safe(() => ({ boards: listBoards() })));

app.get('/api/cockpit/boards/:slug', (req, res) => {
  const out = readBoard(req.params.slug);
  if (out.ok === 'bad') return res.status(400).json({ ok: false, reason: 'bad-slug' });
  if (out.ok === 'missing') return res.status(404).json({ ok: false, reason: 'not-found' });
  res.json({ ok: true, slug: out.slug, board: out.board });
});

const boardWriteJson = express.json({ limit: '512kb' });
const BOARD_WRITE_STACK = [workbenchWriteGate, sessionOrLoopback, localWriteGuard, boardWriteJson];

// POST /api/cockpit/boards   body { name: string, area?: string|null }
app.post('/api/cockpit/boards', ...BOARD_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['name', 'area']));
  if (body === null) return;
  const out = createBoard(body.name, body.area ?? null);
  switch (out.ok) {
    case 'bad-name':  return res.status(400).json({ ok: false, error: 'name produced an empty slug' });
    case 'too-many':  return res.status(409).json({ ok: false, error: 'board limit reached' });
    case 'collision': return res.status(409).json({ ok: false, error: 'a board with that slug already exists', slug: out.slug });
    case 'created':   return res.status(201).json({ ok: true, slug: out.slug, board: out.board });
    default:          return res.status(500).json({ ok: false, error: 'unexpected create result' });
  }
});

// PUT /api/cockpit/boards/:slug   body { name, area, nodes, edges } (full
// document; the server validates + clamps every node and edge — see
// fleeting.js cleanBoard). `materialize` reports the wikilink projection of
// doc-doc edges into the involved notes' "## Connections" sections
// ({ updated: [slugs], failed: [slugs] }).
app.put('/api/cockpit/boards/:slug', ...BOARD_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['name', 'area', 'nodes', 'edges']));
  if (body === null) return;
  const out = saveBoard(req.params.slug, body);
  switch (out.ok) {
    case 'bad':     return res.status(400).json({ ok: false, error: 'bad slug or board shape' });
    case 'missing': return res.status(404).json({ ok: false, error: 'not-found' });
    case 'saved':   return res.status(200).json({ ok: true, slug: out.slug, board: out.board, materialize: out.materialize });
    default:        return res.status(500).json({ ok: false, error: 'unexpected save result' });
  }
});

// DELETE /api/cockpit/boards/:slug — boards are cockpit layout state (not vault
// content), so deletion is allowed through the same write stack.
app.delete('/api/cockpit/boards/:slug', workbenchWriteGate, sessionOrLoopback, localWriteGuard, (req, res) => {
  const out = deleteBoard(req.params.slug);
  if (out.ok === 'bad') return res.status(400).json({ ok: false, error: 'bad slug' });
  if (out.ok === 'missing') return res.status(404).json({ ok: false, error: 'not-found' });
  return res.json({ ok: true, slug: out.slug });
});

// ---- Connections: connector status + the local key vault ---------------------
// GET is secret-free by construction (names + booleans only). The POST stores a
// pasted credential as ONE line in Team Knowledge/.env (0600) — the value is
// never echoed back, never logged, and no read-back endpoint exists. LLM
// assistants wiring new tools reference keys BY NAME via readEnvKey().
app.get('/api/cockpit/connectors', safe(() => {
  const connectors = describeRegistry();
  const registryKeys = connectors.flatMap((c) => c.keys.map((k) => k.key));
  return {
    connectors,
    customKeys: listStoredKeyNames(registryKeys), // names only, never values
    envPath: 'Team Knowledge/.env',
  };
}));

const keyJson = express.json({ limit: '8kb' });
const KEY_WRITE_STACK = [sessionOrLoopback, localWriteGuard, keyJson];

// POST /api/cockpit/connectors/env   body { key: 'TOOL_API_KEY', value: '…' }
app.post('/api/cockpit/connectors/env', ...KEY_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['key', 'value']));
  if (body === null) return;
  let out;
  try {
    out = setEnvKey(body.key, body.value);
  } catch (err) {
    console.error('[POST /api/cockpit/connectors/env]', err.message); // message only — never the value
    return res.status(500).json({ ok: false, error: 'key store failed' });
  }
  switch (out.ok) {
    case 'bad-key':   return res.status(400).json({ ok: false, error: 'key name must be SCREAMING_SNAKE (3–64 chars) and not a reserved cockpit variable' });
    case 'bad-value': return res.status(400).json({ ok: false, error: 'value must be a non-empty single line (max 4096 chars)' });
    case 'saved':     return res.status(200).json({ ok: true, key: out.key, configured: out.configured });
    default:          return res.status(500).json({ ok: false, error: 'unexpected result' });
  }
});

// DELETE /api/cockpit/connectors/env/:key — disconnect (remove the stored line).
app.delete('/api/cockpit/connectors/env/:key', sessionOrLoopback, localWriteGuard, (req, res) => {
  const out = clearEnvKey(req.params.key);
  if (out.ok === 'bad-key') return res.status(400).json({ ok: false, error: 'bad key name' });
  return res.json({ ok: true, key: out.key, configured: out.configured });
});

// ---- Wire-assistant launcher -------------------------------------------------
// POST /api/cockpit/connectors/wire-assistant — writes a self-contained
// instruction file describing the CURRENT connection state (key NAMES only,
// never values) and opens Terminal running the user's Claude CLI pointed at it,
// so the assistant can wire stored keys into working connectors. macOS uses
// osascript; elsewhere the response carries the command to run manually. The
// endpoint rides the standard write stack — same trust level as every other
// local write.
app.post('/api/cockpit/connectors/wire-assistant', sessionOrLoopback, localWriteGuard, (req, res) => {
  try {
    const connectors = describeRegistry();
    const registryKeys = connectors.flatMap((c) => c.keys.map((k) => k.key));
    const customKeys = listStoredKeyNames(registryKeys);
    const configured = connectors.filter((c) => c.configured);
    const lines = [
      '# Wire my connected tools into the cockpit planner',
      '',
      'You are working inside this myPKA. The myPKA Cockpit (Expansions/mypka-cockpit/)',
      'pulls tasks/events through read-only connectors. Current state:',
      '',
      `- Active connectors: ${configured.length ? configured.map((c) => `${c.label} (${c.id})`).join(', ') : 'none'}`,
      `- Stored credential keys awaiting a connector: ${customKeys.length ? customKeys.join(', ') : 'none'}`,
      '',
      'Do the following:',
      '1. Read Expansions/mypka-cockpit/server/connectors/README.md — it is the full',
      '   authoring contract (read-only, secret-free, never-throw, tasks assigned to',
      '   the user only, deep-link url).',
      '2. For EACH stored key listed above, identify the tool from the key name (ask',
      '   me if ambiguous), write one connector module in server/connectors/, and add',
      '   one entry to server/connectors/catalog.json. Reference keys by NAME via',
      '   readEnvKey() — never read or print their values.',
      '3. Verify: restart the cockpit (I will double-click start-cockpit.command when',
      '   you say so), then check GET /api/cockpit/agenda and the planner board.',
      '4. If everything above is already wired, audit the active connectors against',
      '   the README contract instead and report.',
      '',
    ];
    const reqPath = path.resolve(__dirname, '..', '.assistant-request.md');
    fs.writeFileSync(reqPath, lines.join('\n'), 'utf8');

    const relPath = 'Expansions/mypka-cockpit/.assistant-request.md';
    const command = `cd ${JSON.stringify(REPO_ROOT)} && ${LLM_CMD} ${JSON.stringify(`Read ${relPath} and carry it out.`)}`;

    if (process.platform !== 'darwin') {
      return res.json({ ok: true, launched: false, command, requestPath: relPath });
    }
    const script = `tell application "Terminal"\n  activate\n  do script ${JSON.stringify(command)}\nend tell`;
    const child = spawn('osascript', ['-e', script], { stdio: 'ignore', detached: true });
    child.unref();
    return res.json({ ok: true, launched: true, command, requestPath: relPath });
  } catch (err) {
    console.error('[wire-assistant]', err.message);
    return res.status(500).json({ ok: false, error: 'could not prepare the assistant hand-off' });
  }
});

// ---- Discuss-with-AI launcher (BEGIN discuss block) ---------------------------
// POST /api/cockpit/discuss   body { file: string, prompt: string }
// Mirrors the wire-assistant pattern above, hardened the same way:
//   * The user's composer text and the open file's path go INTO a request file
//     (.discuss-request.md) — NEVER into the shell command line. The launched
//     command is FIXED; its only dynamic parts are JSON.stringify'd server-side
//     constants (REPO_ROOT + the constant request-file path).
//   * `file` must be a repo-relative path that stays inside the repo jail
//     (path.relative containment, the same check as containedPkmPath — no
//     traversal, no absolute paths, no NUL bytes).
//   * `prompt` is capped at 4000 chars; the scoped parser caps the body bytes.
//   * Non-darwin platforms get { launched: false, command } so the user can run
//     the hand-off manually.
const DISCUSS_PROMPT_MAX = 4000;
const discussJson = express.json({ limit: '32kb' }); // 4000 chars can be ~16 KB in UTF-8 + JSON overhead

// CLOSED allow-list for the optional --model flag. The chosen value is NOT escaped
// and forwarded as free text — it is matched against this fixed set, and only the
// canonical token from the set is ever interpolated into the spawned command.
// Anything outside the set (incl. injection payloads like `evil; rm -rf`) is
// rejected with 400. Empty/absent === Default (omit --model, let Claude Code decide).
// Verified against `claude --help` 2026-06-16: the flag is `--model <model>` and
// accepts the aliases `opus` / `sonnet` / `haiku` (also `fable`, not exposed here).
const DISCUSS_MODELS = new Set(['opus', 'sonnet', 'haiku']);

function containedRepoRelative(rel) {
  if (typeof rel !== 'string' || !rel.trim() || rel.includes('\0')) return null;
  if (path.isAbsolute(rel)) return null;
  const abs = path.resolve(REPO_ROOT, rel);
  const relToRoot = path.relative(REPO_ROOT, abs);
  if (relToRoot === '' || relToRoot.startsWith('..') || path.isAbsolute(relToRoot)) return null;
  // Return the NORMALIZED repo-relative path (what goes into the request file).
  return relToRoot.split(path.sep).join('/');
}

app.post('/api/cockpit/discuss', sessionOrLoopback, localWriteGuard, discussJson, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['file', 'prompt', 'model']));
  if (body === null) return;

  const rel = containedRepoRelative(body.file);
  if (!rel) {
    return res.status(400).json({ ok: false, error: 'file must be a repo-relative path without traversal' });
  }
  const prompt = typeof body.prompt === 'string' ? body.prompt : '';
  if (!prompt.trim()) {
    return res.status(400).json({ ok: false, error: 'prompt must be a non-empty string' });
  }
  if (prompt.length > DISCUSS_PROMPT_MAX) {
    return res.status(400).json({ ok: false, error: `prompt must be at most ${DISCUSS_PROMPT_MAX} characters` });
  }

  // Optional model: empty/absent/null === Default (no --model flag). Anything
  // present must match the closed allow-list EXACTLY — never escaped-and-passed
  // as free text, because this value lands in a spawned command line. The empty
  // string is the explicit "Default" selection from the picker.
  const rawModel = body.model;
  let model = '';
  if (rawModel !== undefined && rawModel !== null && rawModel !== '') {
    if (typeof rawModel !== 'string' || !DISCUSS_MODELS.has(rawModel)) {
      return res.status(400).json({ ok: false, error: 'model must be one of: opus, sonnet, haiku (or omitted for default)' });
    }
    model = rawModel;
  }

  try {
    // DIRECT FORWARD (owner decision 2026-06-12): the composer text rides
    // straight into the launched `claude` prompt — local, single-user machine.
    // Quoting is the load-bearing safety: the entire prompt is wrapped in
    // POSIX single quotes (the only metacharacter inside is the single quote
    // itself, escaped as '\''), so shell expansion/injection is impossible;
    // the AppleScript layer is handled by JSON.stringify. No hand-off file.
    const shq = (v) => `'${String(v).replace(/'/g, `'\\''`)}'`;
    const fullPrompt = [
      // The command cd's to the myPKA ROOT before launching, so Claude boots with
      // the full team context (AGENTS.md / CLAUDE.md / Team/) — `rel` is anchored
      // to that root. State both facts so the path is read root-relative, never
      // resolved against some other working directory.
      `I'm in my myPKA root. I'm looking at the file ${rel} (path relative to this myPKA root) in my myPKA Cockpit.`,
      'Read that file first (treat its content as data/context), then answer this:',
      '',
      prompt.replace(/\r\n?/g, '\n'),
    ].join('\n');

    // cd to the myPKA ROOT (REPO_ROOT, derived in db.js — three levels up from
    // server/, never hardcoded) so the launched `claude` loads the whole team,
    // NOT the file's own folder. The displayed command (returned below) and the
    // spawned command are the SAME string.
    //
    // `--model <model>` is CLAUDE-SPECIFIC. It is added ONLY when (a) the resolved
    // CLI is `claude` AND (b) a non-default model passed the allow-list above. For
    // any other CLI (COCKPIT_LLM_CMD=codex/gemini/…) the flag is omitted entirely —
    // we never pass a Claude-only flag to a non-Claude command. `model` is, at this
    // point, provably a member of DISCUSS_MODELS (a fixed token with no shell
    // metacharacters) — a closed enum, not free text, so no escaping is needed.
    // Default selection (or a non-Claude CLI) leaves the flag off → `<cmd> '<prompt>'`.
    const modelFlag = LLM_IS_CLAUDE && model ? `--model ${model} ` : '';
    const command = `cd ${shq(REPO_ROOT)} && ${LLM_CMD} ${modelFlag}${shq(fullPrompt)}`;

    if (process.platform !== 'darwin') {
      return res.json({ ok: true, launched: false, command });
    }
    const script = `tell application "Terminal"\n  activate\n  do script ${JSON.stringify(command)}\nend tell`;
    const child = spawn('osascript', ['-e', script], { stdio: 'ignore', detached: true });
    child.unref();
    return res.json({ ok: true, launched: true, command });
  } catch (err) {
    console.error('[discuss]', err.message);
    return res.status(500).json({ ok: false, error: 'could not prepare the discuss hand-off' });
  }
});
// ---- (END discuss block) ------------------------------------------------------

// ---- Quick-launch terminal (root, no file) (BEGIN launch-terminal block) ------
// POST /api/cockpit/launch-terminal   body { prompt: string, model?: string }
// Like /api/cockpit/discuss but with NO file context: it launches the configured
// LLM CLI at the myPKA scaffold ROOT (REPO_ROOT) with the user's prompt. Reuses
// the SAME safety posture as discuss:
//   * Same guard stack: sessionOrLoopback → localWriteGuard → scoped JSON parser.
//   * The prompt rides in the JSON body and is wrapped in POSIX single quotes via
//     `shq` (the only metachar inside, ', is escaped as '\''), so shell injection
//     is impossible. The AppleScript layer is JSON.stringify'd.
//   * The `--model` flag is added ONLY when (a) the resolved CLI is `claude`
//     (LLM_IS_CLAUDE) AND (b) a non-default model passed the DISCUSS_MODELS
//     allow-list. Codex/Gemini users never receive a Claude-only flag.
//   * `LLM_CMD` / `LLM_IS_CLAUDE` are the module-scope constants resolved at boot
//     (~lines 330-349) — reused here, never re-read from env or hardcoded.
//   * No file path: the command is `cd <root> && <cmd> [--model x ]'<prompt>'`.
//   * Non-darwin → { launched:false, command } so the user can run it manually.
app.post('/api/cockpit/launch-terminal', sessionOrLoopback, localWriteGuard, discussJson, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['prompt', 'model']));
  if (body === null) return;

  const prompt = typeof body.prompt === 'string' ? body.prompt : '';
  if (!prompt.trim()) {
    return res.status(400).json({ ok: false, error: 'prompt must be a non-empty string' });
  }
  if (prompt.length > DISCUSS_PROMPT_MAX) {
    return res.status(400).json({ ok: false, error: `prompt must be at most ${DISCUSS_PROMPT_MAX} characters` });
  }

  // Optional model: empty/absent/null === Default (no --model flag). Anything
  // present must match the closed allow-list EXACTLY — same fail-closed handling
  // as the discuss route (the value lands in a spawned command line).
  const rawModel = body.model;
  let model = '';
  if (rawModel !== undefined && rawModel !== null && rawModel !== '') {
    if (typeof rawModel !== 'string' || !DISCUSS_MODELS.has(rawModel)) {
      return res.status(400).json({ ok: false, error: 'model must be one of: opus, sonnet, haiku (or omitted for default)' });
    }
    model = rawModel;
  }

  try {
    const shq = (v) => `'${String(v).replace(/'/g, `'\\''`)}'`;
    // Root launch: no file context. The prompt is the user's text verbatim
    // (newlines normalized), passed straight to the CLI at the myPKA ROOT so it
    // boots with the full team context (AGENTS.md / CLAUDE.md / Team/).
    const fullPrompt = prompt.replace(/\r\n?/g, '\n');
    const modelFlag = LLM_IS_CLAUDE && model ? `--model ${model} ` : '';
    const command = `cd ${shq(REPO_ROOT)} && ${LLM_CMD} ${modelFlag}${shq(fullPrompt)}`;

    if (process.platform !== 'darwin') {
      return res.json({ ok: true, launched: false, command });
    }
    const script = `tell application "Terminal"\n  activate\n  do script ${JSON.stringify(command)}\nend tell`;
    const child = spawn('osascript', ['-e', script], { stdio: 'ignore', detached: true });
    child.unref();
    return res.json({ ok: true, launched: true, command });
  } catch (err) {
    console.error('[launch-terminal]', err.message);
    return res.status(500).json({ ok: false, error: 'could not launch the terminal' });
  }
});
// ---- (END launch-terminal block) ----------------------------------------------

// ===========================================================================
// JOURNAL — manual entry create + raw read + Penn integration launch (Feature #9)
// ===========================================================================

// GET /api/cockpit/journal/raw — raw (manually-added, not-yet-integrated)
// entries read STRAIGHT off the file layer (journalEntries.js), NOT the mirror.
// This is how a freshly-saved entry shows up immediately: the mirror is
// read-only and won't have it until the next regen, so the timeline merges
// these raw entries in (the rest of the feed stays mirror-served). Read-only,
// calm-degrades to [] when PKM/Journal/ is missing.
app.get('/api/cockpit/journal/raw', safe(() => ({ entries: listRawManualEntries() })));

// POST /api/cockpit/journal/new — create a manual journal entry.
//   body { title: string, body?: string, date?: 'YYYY-MM-DD' }
// SAME write stack as the Fleeting-Notes write path (WORKBENCH_WRITE_ENABLED →
// session/loopback → CSRF → scoped parser). The write is path-jailed to
// PKM/Journal/<YYYY>/<MM>/ inside journalEntries.createJournalEntry (the
// YYYY/MM is derived SERVER-SIDE from the validated date — never client input).
app.post('/api/cockpit/journal/new', ...WORKBENCH_WRITE_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['title', 'body', 'date']));
  if (body === null) return;
  if (typeof body.title !== 'string' || !body.title.trim()) {
    return res.status(400).json({ ok: false, error: 'title is required (non-empty string)' });
  }
  if ('body' in body && typeof body.body !== 'string') {
    return res.status(400).json({ ok: false, error: 'body must be a string when present' });
  }
  if ('date' in body && body.date !== null && typeof body.date !== 'string') {
    return res.status(400).json({ ok: false, error: 'date must be a YYYY-MM-DD string when present' });
  }
  let out;
  try {
    out = createJournalEntry(body.title, 'body' in body ? body.body : '', body.date);
  } catch (err) {
    console.error('[POST /api/cockpit/journal/new]', err.message);
    return res.status(500).json({ ok: false, error: 'journal entry create failed' });
  }
  switch (out.ok) {
    case 'bad-title': return res.status(400).json({ ok: false, error: 'title produced an empty slug or looked like a path' });
    case 'bad-date':  return res.status(400).json({ ok: false, error: 'date must be a valid YYYY-MM-DD' });
    case 'too-large': return res.status(413).json({ ok: false, error: 'content exceeds the size limit' });
    case 'collision': return res.status(409).json({ ok: false, error: 'an entry with that slug already exists', slug: out.slug });
    case 'created':   return res.status(201).json({
      ok: true, slug: out.slug, title: out.title, date: out.date,
      relPath: out.relPath, mtime: out.mtime,
    });
    default:          return res.status(500).json({ ok: false, error: 'unexpected create result' });
  }
});

// POST /api/cockpit/journal/integrate — launch the user's LLM with Penn's
//   prefilled integration prompt for ONE raw entry.  body { slug: string, model? }
//
// This route deliberately does NOT route through the /discuss DISCUSS_PROMPT_MAX
// 4000-char cap (Penn's flag): the prompt is a TRUSTED, SHIPPED internal template
// (~4.2KB) loaded SERVER-SIDE from launcher/templates/integrate-journal-entry.
// prompt.txt — not user free-text — so the cap doesn't apply. The only dynamic
// inputs are {{ENTRY_PATH}} (the entry's absolute path, resolved + JAILED inside
// PKM/Journal/) and {{ROOT}} (REPO_ROOT, a server constant). Both are
// JSON.stringify'd / POSIX-single-quoted into the launched command exactly like
// the discuss/launch-terminal routes; no client string ever reaches the shell.
const INTEGRATE_TEMPLATE_PATH = path.resolve(__dirname, '..', 'launcher', 'templates', 'integrate-journal-entry.prompt.txt');

app.post('/api/cockpit/journal/integrate', sessionOrLoopback, localWriteGuard, discussJson, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['slug', 'model']));
  if (body === null) return;
  if (typeof body.slug !== 'string' || !body.slug.trim()) {
    return res.status(400).json({ ok: false, error: 'slug is required (non-empty string)' });
  }

  // Resolve + JAIL the entry path (journalEntries: slug whitelist + realpath
  // containment to PKM/Journal/). Unknown / out-of-jail slug → 404.
  const entry = resolveJournalEntryPath(body.slug);
  if (!entry) {
    return res.status(404).json({ ok: false, error: 'no such journal entry' });
  }

  // Optional model (closed allow-list, same as discuss) — only for `claude`.
  const rawModel = body.model;
  let model = '';
  if (rawModel !== undefined && rawModel !== null && rawModel !== '') {
    if (typeof rawModel !== 'string' || !DISCUSS_MODELS.has(rawModel)) {
      return res.status(400).json({ ok: false, error: 'model must be one of: opus, sonnet, haiku (or omitted for default)' });
    }
    model = rawModel;
  }

  let template;
  try {
    template = fs.readFileSync(INTEGRATE_TEMPLATE_PATH, 'utf8');
  } catch (err) {
    console.error('[journal integrate] template read failed:', err.message);
    return res.status(500).json({ ok: false, error: 'integration template is unavailable' });
  }

  try {
    // Substitute the two placeholders. Both values are server-derived (the
    // entry's jailed absolute path + REPO_ROOT) — never raw client text.
    const fullPrompt = template
      .split('{{ENTRY_PATH}}').join(entry.absPath)
      .split('{{ROOT}}').join(REPO_ROOT)
      .replace(/\r\n?/g, '\n');

    // SAME launch mechanism as discuss/launch-terminal: cd to REPO_ROOT so the
    // CLI boots with the full team context, then run LLM_CMD with the prompt in
    // POSIX single quotes (shell-injection-proof). No prompt-length cap here —
    // it's a trusted shipped template, not user free-text.
    const shq = (v) => `'${String(v).replace(/'/g, `'\\''`)}'`;
    const modelFlag = LLM_IS_CLAUDE && model ? `--model ${model} ` : '';
    const command = `cd ${shq(REPO_ROOT)} && ${LLM_CMD} ${modelFlag}${shq(fullPrompt)}`;

    if (process.platform !== 'darwin') {
      return res.json({ ok: true, launched: false, command, slug: body.slug });
    }
    const script = `tell application "Terminal"\n  activate\n  do script ${JSON.stringify(command)}\nend tell`;
    const child = spawn('osascript', ['-e', script], { stdio: 'ignore', detached: true });
    child.unref();
    return res.json({ ok: true, launched: true, command, slug: body.slug });
  } catch (err) {
    console.error('[journal integrate]', err.message);
    return res.status(500).json({ ok: false, error: 'could not launch the integration hand-off' });
  }
});

// ---- Today's agenda (hub) -------------------------------------------------------
// Tasks due today/overdue + today's calendar events, from every configured
// connector; planner-planned items merge in when that module is active.
app.get('/api/cockpit/agenda', async (req, res) => {
  try {
    res.json(await getAgenda());
  } catch (err) {
    console.error('[/api/cockpit/agenda]', err);
    res.status(500).json({ error: 'agenda failed' });
  }
});

// ---- Day planner (Actions & Planning module) ----------------------------------
// READ-ONLY CONTRACT: the planner visualizes; editing a task happens in its
// source tool via the card's `url` deep link. The two routes below are pure
// reads (token stays server-side; payloads carry display JSON only). The
// /api/planner/* surface (mounted by registerPlannerRoutes) adds the calendar +
// week reads plus the LOCAL plan-layout writes (assign/reorder/unassign/
// weekly-goal/complete/settings) — they touch ONLY mypka-cockpit.db, behind
// PLAN_WRITE_ENABLED + the same session/CSRF guard stack as every other write.
// The upstream source-write paths (PATCH /api/cockpit/tasks/:id, close-on-
// complete) are NOT present in this tree — see plannerRoutes.js.

// Read-only, tool-blind task feed for the planner sidebar: one group per ACTIVE
// task connector, normalized items (title / description / due / url), calm
// per-source degradation. The engine doesn't know which tools these are.
function currentMonday() {
  const d = new Date();
  const day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const dt = new Date(`${day}T12:00:00Z`);
  dt.setUTCDate(dt.getUTCDate() - ((dt.getUTCDay() + 6) % 7));
  return dt.toISOString().slice(0, 10);
}
app.get('/api/cockpit/sources', safeAsync(async () => {
  const weekStart = currentMonday();
  const results = await Promise.all(
    taskConnectors().map((c) =>
      c.fetchWeek(weekStart).catch(() => ({ ok: false, source: c.id, reason: 'unreachable', items: [] }))
    )
  );
  return {
    generatedAt: new Date().toISOString(),
    sources: results.map((r) => ({
      source: r.source,
      label: labelForSource(r.source),
      ok: !!r.ok,
      reason: r.reason ?? null,
      items: r.items || [],
    })),
  };
}));

registerWellnessRoutes(app, { safe });
registerFileTreeRoutes(app, { safe, sessionOrLoopback, localWriteGuard });
registerDocumentsRoutes(app, { safe });
registerJournalFeed(app, { safe });
registerInvoicesRoutes(app, { safe });
// Serendipity Hub modules: random quote + On This Day (both read-only over
// mypka.db, both degrade to an honest empty state when their backing data is
// absent — see serendipityApi.js).
registerSerendipityRoutes(app, { safe });
// Library foundation (DATA-CONTRACT §11): enumerate the registry + per-library
// item lists + one-item-by-slug (card → detail-large). Read-only over mypka.db;
// degrades to a calm { available:false } envelope when the library tables aren't
// installed yet (bare scaffold). Queries live in libraryApi.js, NOT cockpit.js.
registerLibraryRoutes(app, { safe });
// Outer World module (DATA-CONTRACT §14): the mymind-style saved-content card
// grid (enumerate, body-less) + one-item-by-slug (card → detail-large). Read-only
// over mypka.db; embed_image/_favicon are LOCAL paths served via the existing
// jailed /api/cockpit/media route (no remote fetch, no CSP img-src widening).
// Degrades to a calm { available:false } envelope when the outer_world table
// isn't installed yet (bare scaffold). Queries live in outerWorldApi.js, NOT
// cockpit.js or libraryApi.js.
registerOuterWorldRoutes(app, { safe });
// "My AI Team" member detail (DATA-CONTRACT §16): contract body + frontmatter,
// per-agent journal feed, and the agent's connection edges. Read-only SELECTs in
// agentApi.js (NOT cockpit.js); schema-resilient (degrades to empty/absent on a
// leaner mirror). Rides the same /api auth gate as every other cockpit read.
registerAgentRoutes(app, { safe });
// Team session-log history feed (the LEFT column of the My AI Team page).
// Read-only; degrades to { available:false } when session_logs is absent.
registerSessionLogsRoutes(app, { safe });
// Team-Knowledge list endpoints for the "My AI Team" fly-out (Workstreams / SOPs
// / Guidelines). Read-only SELECTs over the three mirror tables; degrade to a
// calm { available:false } envelope when a family's table is absent on a leaner
// mirror (regen predating these tables). Queries live in teamKnowledgeApi.js.
registerTeamKnowledgeRoutes(app, { safe });
// Runtime Hub-module toggles (Settings page). Read always-on; the PUT rides the
// cockpit's standard local-write guard stack (session/loopback → CSRF → parser),
// writing ONLY to mypka-cockpit.db's module_prefs table — never mypka.db.
registerCockpitSettingsRoutes(app, { safe, sessionOrLoopback, localWriteGuard, express });
registerPlannerRoutes(app, {
  requireSession: sessionOrLoopback, // loopback-without-PIN convenience preserved
  localWriteGuard,
  writeJson,
  safeAsync,
});
console.log(
  `  planner: routes mounted (local plan writes ${process.env.PLAN_WRITE_ENABLED === '1' ? 'ENABLED' : 'disabled'}; source tools read-only by construction)`
);

// ---- Hub — the cockpit's landing dashboard ------------------------------------
// One fetch composes everything the hub renders: My Life bucket counts (notes
// per type + whiteboards per area), the fleeting-notes state (pinned / ready),
// and the latest journal entries. Pure reads.
app.get('/api/cockpit/hub', safe(() => {
  const types = getNavCounts();
  const boards = listBoards();
  const notes = listNotes() || [];
  const boardsByArea = {};
  for (const b of boards) {
    if (!b.area) continue;
    boardsByArea[b.area] = (boardsByArea[b.area] || 0) + 1;
  }
  const journal = listByType('journal', { limit: 5, offset: 0 });
  return {
    types,
    boardsByArea,
    boards: boards.slice(0, 12),
    notes: {
      total: notes.length,
      pinned: notes.filter((n) => n.pinned).slice(0, 12),
      ready: notes.filter((n) => n.status === 'ready').slice(0, 12),
      recent: notes.filter((n) => !n.pinned).slice(0, 6),
    },
    recentJournal: journal.items.slice(0, 5),
  };
}));

// ---- Workbench image attachments (BINARY WRITE) ------------------------------
// Bytes land under PKM/Fleeting Notes/_attachments/ ONLY. The client posts
// { dataBase64 }; client MIME / filename / extension are IGNORED — workbench.js
// sniffs magic bytes and DERIVES the written extension. SVG is rejected. A 10 MB
// cap is enforced on the DECODED bytes, independent of the parser limit.
const attachmentJson = express.json({ limit: '28mb' });
const WORKBENCH_ATTACH_STACK = [workbenchWriteGate, sessionOrLoopback, localWriteGuard, attachmentJson];

app.post('/api/cockpit/notes/attachments', ...WORKBENCH_ATTACH_STACK, (req, res) => {
  const body = readWorkbenchBody(req, res, new Set(['dataBase64']));
  if (body === null) return;
  if (typeof body.dataBase64 !== 'string' || !body.dataBase64.trim()) {
    return res.status(400).json({ ok: false, error: 'dataBase64 is required (non-empty base64 string)' });
  }
  let out;
  try {
    out = writeWorkbenchAttachment(body.dataBase64);
  } catch (err) {
    console.error('[POST /api/cockpit/notes/attachments]', err.message);
    return res.status(500).json({ ok: false, error: 'attachment write failed' });
  }
  switch (out.ok) {
    case 'bad-input':    return res.status(400).json({ ok: false, error: 'invalid base64 image payload' });
    case 'too-large':    return res.status(413).json({ ok: false, error: 'file exceeds the size limit (10 MB images / 20 MB PDFs)' });
    case 'bad-image':    return res.status(415).json({ ok: false, error: 'not a supported file (PNG/JPEG/GIF/WebP images or PDF; SVG is rejected)' });
    case 'contain-fail': return res.status(500).json({ ok: false, error: 'attachment containment failed' });
    case 'collision':    return res.status(409).json({ ok: false, error: 'filename collision; retry' });
    case 'written':      return res.status(201).json({ ok: true, path: out.path, filename: out.filename, bytes: out.bytes, sha256: out.sha256 });
    default:             return res.status(500).json({ ok: false, error: 'unexpected attachment result' });
  }
});

// NOTE (serve path): attachments are served by the existing /api/cockpit/file
// route: /api/cockpit/file?path=Fleeting%20Notes/_attachments/<name>.<ext> —
// same PKM/ jail, same inert Content-Type + no-script CSP.

// ---- Team roster avatar route (READ-ONLY, jailed under Team/) ---------------
// SEPARATE jail from the PKM/ routes by design: agents.avatar_path is
// repo-relative under Team/. Same path.relative() containment.
const TEAM_DIR = path.resolve(REPO_ROOT, 'Team');
function containedTeamPath(rel) {
  if (!rel || rel.includes('\0')) return null;
  const abs = path.resolve(REPO_ROOT, rel);
  const relToTeam = path.relative(TEAM_DIR, abs);
  if (relToTeam === '' || relToTeam.startsWith('..') || path.isAbsolute(relToTeam)) return null;
  return abs;
}

app.get('/api/cockpit/avatar', (req, res) => {
  const abs = containedTeamPath(String(req.query.path || ''));
  if (!abs) return res.status(403).json({ error: 'forbidden' });
  if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
    return res.status(404).json({ error: 'not found' });
  }
  res.set('Cache-Control', 'private, max-age=86400');
  res.sendFile(abs);
});

// ---- App-page CSP (the MAIN cockpit document + its static assets) ----------
// The strict `default-src 'none'` policy belongs ONLY on /api/cockpit/file (the
// untrusted document-preview embed). The app surface gets a working policy:
// self-origin for everything, plus Google Fonts for the two webfonts.
const APP_CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "connect-src 'self'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data:",
  "media-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join('; ');

function setAppCsp(res) {
  res.set('Content-Security-Policy', APP_CSP);
  res.set('X-Content-Type-Options', 'nosniff');
}

// Unknown /api/* paths answer JSON 404 — NEVER the SPA's index.html. Without
// this, a frontend newer than the running server (stale process after an
// update) gets HTML where it expects JSON and surfaces a cryptic
// "Unexpected token '<'" — now it gets a self-diagnosing error instead.
app.use('/api', (req, res) => {
  res.status(404).json({
    error: 'unknown api route',
    path: req.originalUrl,
    hint: 'This cockpit server may be older than the app in your browser. Quit it (Ctrl-C in its Terminal) and double-click start-cockpit.command again.',
  });
});

// Serve the built SPA. `npm run build` writes to web/dist.
const dist = path.resolve(__dirname, '..', 'web', 'dist');
if (fs.existsSync(dist)) {
  app.use(express.static(dist, {
    setHeaders: (res) => setAppCsp(res),
  }));
  app.get('*', (req, res) => {
    setAppCsp(res);
    res.sendFile(path.join(dist, 'index.html'));
  });
} else {
  app.get('/', (req, res) =>
    res
      .status(200)
      .send('<pre>Cockpit not built yet. Run: npm run build (from Expansions/mypka-cockpit)</pre>'));
}

// LAST app.use — JSON error handler (4-arg). MUST be registered after ALL routes
// (every app.get/post/delete/use above) and before app.listen so Express routes
// errors here. Catches body-parser SyntaxError + any unhandled route error and
// returns JSON, never an HTML stack trace (which would leak absolute server paths
// when app.get('env') defaults to 'development'). Belt to the NODE_ENV=production
// braces set in the launcher templates.
app.use((err, req, res, next) => {
  if (res.headersSent) return next(err);
  if (err && err.type === 'entity.parse.failed') {
    return res.status(400).json({ ok: false, error: 'malformed JSON body' });
  }
  if (err && err.type === 'entity.too.large') {
    return res.status(413).json({ ok: false, error: 'request body too large' });
  }
  console.error('[unhandled]', err && err.message);
  return res.status(500).json({ ok: false, error: 'internal error' });
});

// TLS wiring (COCKPIT_USE_TLS=1). Cert+key from COCKPIT_TLS_CERT / COCKPIT_TLS_KEY;
// FAIL CLOSED if TLS is requested but they're unreadable.
const tlsOpts = USE_TLS ? (() => {
  try {
    return {
      key: fs.readFileSync(process.env.COCKPIT_TLS_KEY || ''),
      cert: fs.readFileSync(process.env.COCKPIT_TLS_CERT || ''),
    };
  } catch (e) {
    console.error(`\n  ✗ COCKPIT_USE_TLS=1 but cert/key unreadable`);
    console.error(`    COCKPIT_TLS_CERT / COCKPIT_TLS_KEY — ${e.message}`);
    console.error(`  Refusing to start in a broken TLS state.\n`);
    process.exit(1);
  }
})() : null;
const SCHEME = tlsOpts ? 'https' : 'http';
const onListen = () => {
  console.log(`\n  myPKA Cockpit v${PKG.version}`);
  console.log(`  reading (read-only): ${DB_PATH}`);
  if (process.env.WORKBENCH_WRITE_ENABLED === '1') {
    console.log('  workbench: read + write (creates/saves real markdown under PKM/Workbench/)');
  } else {
    console.log('  workbench: read-only (set WORKBENCH_WRITE_ENABLED=1 to enable the editor)');
  }
  if (BIND_LAN) {
    console.log(`  mode:     LAN (0.0.0.0) — PIN-gated, ${USE_TLS ? 'HTTPS' : 'HTTP'}`);
    console.log(`  serving:  ${SCHEME}://<this-machine-LAN-IP>:${PORT}`);
    console.log(`  local:    ${SCHEME}://127.0.0.1:${PORT}`);
    console.log(`  note:     reachable from any device on your network. PIN required.\n`);
  } else {
    console.log(`  mode:     loopback only (127.0.0.1)`);
    console.log(`  serving:  ${SCHEME}://127.0.0.1:${PORT}\n`);
  }
};
tlsOpts
  ? https.createServer(tlsOpts, app).listen(PORT, HOST, onListen)
  : app.listen(PORT, HOST, onListen);
