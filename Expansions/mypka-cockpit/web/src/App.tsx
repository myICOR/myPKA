// App.tsx — the myPKA Cockpit shell. Left sidebar + routed content area.
// The cockpit is a navigable, wikilink-aware viewer over your myPKA: the Hub
// (landing dashboard), journal, universal note viewer, type browsers, the team
// roster, Fleeting Notes (capture + WIP docs) and their whiteboards.
// Hash-routed, local-only.
import { lazy, Suspense, useEffect, useState } from 'react';
import { Menu } from 'lucide-react';
import { useFetch } from './lib/useCockpit';
import { useRoute } from './lib/router';
import { useTheme } from './lib/theme';
import type { NavType } from './lib/cockpitTypes';
import { Sidebar } from './components/Sidebar';
import { CommandPalette } from './components/CommandPalette';
import { HubView } from './views/HubView';
import { JournalView } from './views/JournalView';
import { RosterView } from './views/RosterView';
import { SessionLogView } from './views/SessionLogView';
import { TeamAnalyticsView } from './views/TeamAnalyticsView';
import { TeamKnowledgeListView } from './views/TeamKnowledgeListView';
import { ConnectionsView } from './views/ConnectionsView';
import { SettingsView } from './views/SettingsView';
import { TypeListView } from './views/TypeListView';
import { NoteView } from './views/NoteView';
import { DocumentsView } from './views/DocumentsView';
import { FileView } from './views/FileView';
import { moduleForSlug } from './lib/moduleRegistry';

// The editor (TipTap outliner) and the whiteboard (ReactFlow) are the two heavy
// chunks — both stay behind lazy boundaries so they never enter the eager bundle.
const WorkbenchListView = lazy(() =>
  import('./views/WorkbenchListView').then((m) => ({ default: m.WorkbenchListView })),
);
const WorkbenchDocView = lazy(() =>
  import('./views/WorkbenchDocView').then((m) => ({ default: m.WorkbenchDocView })),
);
const BoardView = lazy(() =>
  import('./views/BoardView').then((m) => ({ default: m.BoardView })),
);
// Library surface (DATA-CONTRACT §11) — lazy so the picker/grid/detail code +
// WikiMarkdown's markdown chunk never enter the eager bundle.
const LibraryView = lazy(() =>
  import('./views/LibraryView').then((m) => ({ default: m.LibraryView })),
);
// Outer World module (DATA-CONTRACT §14) — lazy so the card-grid/detail code +
// WikiMarkdown's markdown chunk never enter the eager bundle.
const OuterWorldView = lazy(() =>
  import('./views/OuterWorldView').then((m) => ({ default: m.OuterWorldView })),
);

interface NavResponse { types: NavType[] }

function useSidebarOpen() {
  // Default open on desktop, closed on mobile; remember the user's choice.
  const [open, setOpen] = useState(() => {
    const stored = window.localStorage.getItem('cockpit-sidebar');
    if (stored != null) return stored === '1';
    return window.matchMedia('(min-width: 768px)').matches;
  });
  useEffect(() => {
    window.localStorage.setItem('cockpit-sidebar', open ? '1' : '0');
  }, [open]);
  return [open, () => setOpen((o) => !o), () => setOpen(false)] as const;
}

export default function App() {
  const route = useRoute();
  // Own the live theme listener at the shell level: 'system' re-resolves when the
  // OS theme flips, app-wide, regardless of which view is open. The inline
  // index.html bootstrap already applied the correct theme before first paint;
  // this keeps it tracking. (The Settings switch reads/writes the same hook.)
  useTheme();
  const { data: nav } = useFetch<NavResponse>('/api/cockpit/nav');
  const [sidebarOpen, toggleSidebar, closeSidebar] = useSidebarOpen();
  const navTypes = nav?.types ?? [];

  // The ⌘K / Ctrl+K global command palette (FTS5 search). The key listener is
  // mounted at the shell so the shortcut works from any view. We DON'T preempt
  // the browser's own ⌘K when focus is inside the editor's [[ autocomplete —
  // there isn't one bound here, so the global handler is safe.
  const [searchOpen, setSearchOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setSearchOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // On mobile, navigating closes the drawer; on desktop it stays as-is.
  const onNavigate = () => {
    if (!window.matchMedia('(min-width: 768px)').matches) closeSidebar();
  };

  // Full-bleed surfaces: the whiteboard always; a module when it opts in; the
  // Outer World grid (resolves to its own core route, not 'module', but its
  // registry entry opts into fullBleed — the masonry grid owns its own width).
  const fullBleed =
    route.name === 'board' ||
    (route.name === 'module' && moduleForSlug(route.slug)?.fullBleed) ||
    (route.name === 'outer-world' && !route.slug && moduleForSlug('outer-world')?.fullBleed);

  // Full-HEIGHT "My AI Team" surfaces (roster / session log / workstreams / sops /
  // guidelines). These keep the centered reading column BUT must fill the viewport
  // height so their inner panel scrolls instead of leaving a short floating card.
  // The class makes .cockpit-content a flex column that fills .cockpit-main's height
  // (cockpit.css .cockpit-content--team); the team view owns the inner scroll.
  const teamFull =
    route.name === 'roster' ||
    route.name === 'session-log' ||
    route.name === 'team-analytics' ||
    route.name === 'workstreams' ||
    route.name === 'sops' ||
    route.name === 'guidelines';

  return (
    <div className={`cockpit-shell ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      <Sidebar
        navTypes={navTypes}
        route={route}
        open={sidebarOpen}
        onToggle={toggleSidebar}
        onNavigate={onNavigate}
        onOpenSearch={() => setSearchOpen(true)}
      />

      {searchOpen && <CommandPalette onClose={() => setSearchOpen(false)} />}

      <div className="cockpit-main">
        {/* The top content bar is intentionally minimal. The brand lives in the
            sidebar header; the collapse toggle lives in the sidebar too. The only
            chrome here is the REOPEN affordance, shown when the sidebar is closed
            (so a collapsed rail is always one click away). When the sidebar is
            open the bar is empty — clean, X.com-minimal. */}
        {!sidebarOpen && (
          <div className="cockpit-topbar">
            <button type="button" className="topbar-menu" onClick={toggleSidebar} aria-label="Open navigation">
              <Menu size={20} strokeWidth={1.5} aria-hidden="true" />
            </button>
          </div>
        )}

        <div className={`cockpit-content ${fullBleed ? 'cockpit-content--full' : ''} ${teamFull ? 'cockpit-content--team' : ''}`}>
          <ContentRouter route={route} />
        </div>
      </div>
    </div>
  );
}

function ContentRouter({ route }: { route: ReturnType<typeof useRoute> }) {
  switch (route.name) {
    case 'hub': return <HubView />;
    case 'journal': return <JournalView />;
    case 'roster': return <RosterView />;
    case 'session-log': return <SessionLogView />;
    case 'team-analytics': return <TeamAnalyticsView />;
    case 'workstreams': return <TeamKnowledgeListView family="workstreams" />;
    case 'sops': return <TeamKnowledgeListView family="sops" />;
    case 'guidelines': return <TeamKnowledgeListView family="guidelines" />;
    case 'connections': return <ConnectionsView />;
    case 'settings': return <SettingsView />;
    case 'notes':
      return (
        <Suspense fallback={<LazyFallback />}>
          <WorkbenchListView />
        </Suspense>
      );
    case 'notes-doc':
      return (
        <Suspense fallback={<LazyFallback />}>
          <WorkbenchDocView route={route} />
        </Suspense>
      );
    case 'board':
      return (
        <Suspense fallback={<LazyFallback />}>
          <BoardView route={route} />
        </Suspense>
      );
    case 'module': {
      // Drop-in extension module. Gate-aware lookup; an uninstalled/gated
      // module falls through to the default view. The Suspense boundary lets a
      // registry View be a React.lazy chunk (e.g. the planner); an eager View
      // renders straight through it unchanged.
      const mod = moduleForSlug(route.slug);
      if (!mod) return <HubView />;
      const { View } = mod;
      return (
        <Suspense fallback={<LazyFallback />}>
          <View />
        </Suspense>
      );
    }
    case 'type':
      if (route.type === 'documents') return <DocumentsView />;
      return <TypeListView route={route} />;
    case 'note':
    case 'resolve': return <NoteView route={route} />;
    case 'file': return <FileView route={route} />;
    case 'library':
      // LibraryView reads the current route itself (useRoute), so it satisfies
      // both this core-route case and the zero-prop moduleRegistry View type.
      return (
        <Suspense fallback={<LazyFallback />}>
          <LibraryView />
        </Suspense>
      );
    case 'outer-world':
      // OuterWorldView reads the current route itself (useRoute), so it satisfies
      // both this core-route case and the zero-prop moduleRegistry View type.
      return (
        <Suspense fallback={<LazyFallback />}>
          <OuterWorldView />
        </Suspense>
      );
    default: return <HubView />;
  }
}

// Shown while a lazy chunk is fetched. Mirrors the codebase skeleton idiom
// (aria-busy block) so the swap to real content is visually quiet.
function LazyFallback() {
  return (
    <div className="list-skeleton" aria-busy="true">
      <div className="skeleton-block" />
    </div>
  );
}
