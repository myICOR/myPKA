// router.ts — a tiny hash router (zero deps). The cockpit is a local
// single-server SPA; hash routing keeps deep-linking + back-button working
// without react-router.
//
// Routes:
//   #/  (or #/hub)              -> the Hub — the cockpit's landing dashboard
//   #/journal                   -> journal browser
//   #/roster                    -> team roster (your specialists)
//   #/connections               -> connect task/PM/calendar tools (local key vault)
//   #/notes                     -> Fleeting Notes (capture + WIP docs)
//   #/notes/:slug               -> open one fleeting note (outliner editor)
//   #/board/:slug               -> a whiteboard (fleeting notes on a canvas)
//   #/type/:type                -> browse one entity type
//   #/note/:type/:slug          -> open a PKM note by explicit type+slug
//   #/resolve/:slug             -> resolve a [[wikilink]] slug (collision-aware)
//   #/file/:src                 -> routed reading page for a raw file (FileView)
//   #/<module-slug>             -> a drop-in extension module (see moduleRegistry)
//
// File-route src encoding (the `src` of { name: 'file' }):
//   The cockpit serves raw files through two jailed API routes, so `src` is the
//   repo-relative path with a compact source discriminator prefix:
//     'Deliverables/2026-…/notes.md'   -> /api/cockpit/file?path=…       (the
//        default; NO prefix — this route serves both Deliverables/ paths and
//        PKM document paths, so the path alone is the src)
//     'inbox:Team Inbox/photo.png'     -> /api/cockpit/inbox-file?path=…
//   In the hash the whole src rides as ONE segment via encodeURIComponent
//   ('/' -> %2F), e.g. #/file/Deliverables%2F2026-…%2Fnotes.md. parseHash is
//   lenient and also accepts hand-typed unencoded slashes (#/file/a/b/c.md)
//   by re-joining the trailing segments. Build src with fileRouteSrc(); turn it
//   back into { path, fileUrl } with parseFileSrc().
import { useEffect, useState } from 'react';
import { moduleForSlug } from './moduleRegistry';

export type Route =
  | { name: 'hub' }
  | { name: 'journal' }
  // "My AI Team" family. The fly-out under the sidebar's "My AI Team" row routes
  // to one of these full pages. `roster` (the team grid) and `session-log` split
  // the old combined RosterView into two distinct pages; `workstreams` / `sops` /
  // `guidelines` list the three Team-Knowledge doc families from mypka.db.
  | { name: 'roster' }
  | { name: 'session-log' | 'team-analytics' }
  | { name: 'workstreams' }
  | { name: 'sops' }
  | { name: 'guidelines' }
  | { name: 'connections' }
  | { name: 'settings' }
  | { name: 'notes' }
  | { name: 'notes-doc'; slug: string }
  | { name: 'board'; slug: string }
  // Drop-in extension modules resolve to ONE generic variant carrying their
  // registry slug. The slug is the deep-link key; the registry maps it to nav
  // metadata + the view component. A gated-off / uninstalled module's slug
  // never matches here → falls through to the default view.
  | { name: 'module'; slug: string }
  | { name: 'type'; type: string }
  | { name: 'note'; type: string; slug: string }
  | { name: 'resolve'; slug: string }
  // Library foundation (DATA-CONTRACT §11). #/library = the library surface
  // (pick a library); #/library/:lib = one library's card grid; #/library/:lib/
  // :item = an item opened in the large detail view. Deep-linkable; the Library
  // nav row (moduleRegistry) targets the bare #/library.
  | { name: 'library'; lib?: string; item?: string }
  // Outer World module (DATA-CONTRACT §14). #/outer-world = the mymind-style card
  // grid; #/outer-world/:slug = one saved item opened in the large detail view
  // (the embed header + tom_context body + linked entities). Deep-linkable; the
  // Outer World nav row (moduleRegistry) targets the bare #/outer-world.
  | { name: 'outer-world'; slug?: string }
  // A raw file rendered as a routed in-app reading page (FileView). See the
  // "File-route src encoding" note in the header comment.
  | { name: 'file'; src: string };

// ---- file-route src codec ---------------------------------------------------
// Which jailed server route serves the file's bytes.
export type FileSource = 'file' | 'inbox-file';

/** Build the `src` for a { name: 'file' } route from a serving route + path. */
export function fileRouteSrc(source: FileSource, path: string): string {
  return source === 'inbox-file' ? `inbox:${path}` : path;
}

/** Decode a file-route `src` back into the display path + jailed serving URL. */
export function parseFileSrc(src: string): { path: string; fileUrl: string } {
  if (src.startsWith('inbox:')) {
    const path = src.slice('inbox:'.length);
    return { path, fileUrl: `/api/cockpit/inbox-file?path=${encodeURIComponent(path)}` };
  }
  return { path: src, fileUrl: `/api/cockpit/file?path=${encodeURIComponent(src)}` };
}

export function parseHash(hash: string): Route {
  const clean = hash.replace(/^#\/?/, '');
  const parts = clean.split('/').filter(Boolean).map(decodeURIComponent);
  if (parts.length === 0 || parts[0] === 'hub') return { name: 'hub' };
  if (parts[0] === 'journal') return { name: 'journal' };
  if (parts[0] === 'roster') return { name: 'roster' };
  if (parts[0] === 'session-log') return { name: 'session-log' };
  if (parts[0] === 'team-analytics') return { name: 'team-analytics' };
  if (parts[0] === 'workstreams') return { name: 'workstreams' };
  if (parts[0] === 'sops') return { name: 'sops' };
  if (parts[0] === 'guidelines') return { name: 'guidelines' };
  if (parts[0] === 'connections') return { name: 'connections' };
  if (parts[0] === 'settings') return { name: 'settings' };
  // Fleeting Notes + boards MUST be matched BEFORE the module-registry check,
  // so a drop-in module slug can never shadow a core route.
  if (parts[0] === 'notes' && parts[1]) return { name: 'notes-doc', slug: parts[1] };
  if (parts[0] === 'notes') return { name: 'notes' };
  if (parts[0] === 'board' && parts[1]) return { name: 'board', slug: parts[1] };
  // File reading page. Matched before the module-registry check (core route).
  // Canonically the src is ONE encoded segment, but hand-typed hashes with raw
  // slashes split into several decoded parts — re-join them.
  if (parts[0] === 'file' && parts.length > 1) return { name: 'file', src: parts.slice(1).join('/') };
  // Library surface. Matched BEFORE the module-registry check so the parameterized
  // forms (#/library/:lib, #/library/:lib/:item) are never shadowed by a same-named
  // module slug. Bare #/library is the library picker.
  if (parts[0] === 'library') {
    if (parts[1] && parts[2]) return { name: 'library', lib: parts[1], item: parts[2] };
    if (parts[1]) return { name: 'library', lib: parts[1] };
    return { name: 'library' };
  }
  // Outer World module. Matched BEFORE the module-registry check so the
  // parameterized detail form (#/outer-world/:slug) is never shadowed by the
  // same-named module slug. Bare #/outer-world is the card grid.
  if (parts[0] === 'outer-world') {
    if (parts[1]) return { name: 'outer-world', slug: parts[1] };
    return { name: 'outer-world' };
  }
  // Extension-module slugs resolve through the registry (gate-aware). Checked
  // before the parameterized core routes so a module slug can't be shadowed.
  if (parts[0] && moduleForSlug(parts[0])) return { name: 'module', slug: parts[0] };
  if (parts[0] === 'type' && parts[1]) return { name: 'type', type: parts[1] };
  if (parts[0] === 'note' && parts[1] && parts[2]) return { name: 'note', type: parts[1], slug: parts[2] };
  if (parts[0] === 'resolve' && parts[1]) return { name: 'resolve', slug: parts[1] };
  return { name: 'hub' };
}

export function hrefFor(route: Route): string {
  switch (route.name) {
    case 'hub': return '#/hub';
    case 'journal': return '#/journal';
    case 'roster': return '#/roster';
    case 'session-log': return '#/session-log';
    case 'team-analytics': return '#/team-analytics';
    case 'workstreams': return '#/workstreams';
    case 'sops': return '#/sops';
    case 'guidelines': return '#/guidelines';
    case 'connections': return '#/connections';
    case 'settings': return '#/settings';
    case 'notes': return '#/notes';
    case 'notes-doc': return `#/notes/${encodeURIComponent(route.slug)}`;
    case 'board': return `#/board/${encodeURIComponent(route.slug)}`;
    case 'module': return `#/${encodeURIComponent(route.slug)}`;
    case 'type': return `#/type/${encodeURIComponent(route.type)}`;
    case 'note': return `#/note/${encodeURIComponent(route.type)}/${encodeURIComponent(route.slug)}`;
    case 'resolve': return `#/resolve/${encodeURIComponent(route.slug)}`;
    case 'file': return `#/file/${encodeURIComponent(route.src)}`;
    case 'library':
      if (route.lib && route.item)
        return `#/library/${encodeURIComponent(route.lib)}/${encodeURIComponent(route.item)}`;
      if (route.lib) return `#/library/${encodeURIComponent(route.lib)}`;
      return '#/library';
    case 'outer-world':
      if (route.slug) return `#/outer-world/${encodeURIComponent(route.slug)}`;
      return '#/outer-world';
  }
}

export function navigate(route: Route): void {
  const href = hrefFor(route);
  if (window.location.hash !== href) window.location.hash = href;
  else window.dispatchEvent(new HashChangeEvent('hashchange')); // re-open same note
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const onChange = () => {
      setRoute(parseHash(window.location.hash));
      // Scrolling the content region to top on navigation is handled by the view.
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}
