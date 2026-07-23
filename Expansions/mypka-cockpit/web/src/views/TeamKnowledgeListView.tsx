// TeamKnowledgeListView.tsx — the generic list page for the three Team-Knowledge
// doc families surfaced on the "My AI Team" fly-out: Workstreams, SOPs,
// Guidelines. The three tables share an identical column shape, so ONE view
// renders all three (parameterised by `family`); only the header copy + the
// fetched family vary.
//
// Each row shows the formal doc id + title, a status / owner / version meta line,
// and the summary (first prose paragraph from the doc, clamped to two lines). The
// whole row is a link to the file-reading page (the existing #/file route over the
// jailed /api/cockpit/file endpoint) when the mirror carries a file_path — so a
// click opens the actual markdown in-app, consistent with the rest of the cockpit.
// When no file_path is present the row degrades to a non-navigable card (no dead
// link). Read-only; degrades to a calm empty state when the family's table is
// absent (available:false) or holds no rows.
//
// Every value is a GL-003 token; no hardcoded colours or sizes; the `truncate`
// class is never used (a multi-line clamp is, .tk-row-summary).
import { useEffect, useRef } from 'react';
import { Repeat2, ListChecks, BookText, ArrowUpRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useFetch } from '../lib/useCockpit';
import { S } from '../lib/strings';
import { fileRouteSrc, hrefFor } from '../lib/router';
import { PageHeader } from '../components/PageHeader';
import './team.css';

type Family = 'workstreams' | 'sops' | 'guidelines';

interface TeamKnowledgeItem {
  slug: string;
  docId: string | null;
  title: string;
  status: string | null;
  owner: string | null;
  summary: string | null;
  version: string | null;
  triggeredBy: string | null;
  // domain is present on richer mirrors (e.g. a private regen) and absent on the
  // sample mirror. Optional + nullable so both schemas type-check; rendered only
  // when present (no broken chip when the column doesn't exist).
  domain?: string | null;
  filePath: string | null;
}
interface TeamKnowledgeResponse {
  available: boolean;
  family: string;
  items: TeamKnowledgeItem[];
}

const FAMILY_META: Record<Family, {
  icon: LucideIcon;
  title: string;
  sub: string;
  empty: string;
  emptySub: string;
  loadError: string;
}> = {
  workstreams: {
    icon: Repeat2,
    title: S.team.workstreams.title,
    sub: S.team.workstreams.sub,
    empty: S.team.workstreams.empty,
    emptySub: S.team.workstreams.emptySub,
    loadError: S.team.workstreams.loadError,
  },
  sops: {
    icon: ListChecks,
    title: S.team.sops.title,
    sub: S.team.sops.sub,
    empty: S.team.sops.empty,
    emptySub: S.team.sops.emptySub,
    loadError: S.team.sops.loadError,
  },
  guidelines: {
    icon: BookText,
    title: S.team.guidelines.title,
    sub: S.team.guidelines.sub,
    empty: S.team.guidelines.empty,
    emptySub: S.team.guidelines.emptySub,
    loadError: S.team.guidelines.loadError,
  },
};

// The file-reading route href for a Team-Knowledge doc, when the mirror carries a
// repo-relative file_path. The #/file route's `src` is the path with no source
// prefix (the default 'file' source over /api/cockpit/file). Null → no link.
function fileHrefFor(item: TeamKnowledgeItem): string | null {
  if (!item.filePath) return null;
  return hrefFor({ name: 'file', src: fileRouteSrc('file', item.filePath) });
}

// The stored title typically embeds the formal id ("WS-001 - Daily Journaling").
// Since the id rides in its own chip, strip a leading "<docId> - " / "<docId>: "
// from the displayed title so the badge + title don't repeat the id.
function displayTitle(item: TeamKnowledgeItem): string {
  if (!item.docId) return item.title;
  const re = new RegExp(`^${item.docId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*[:–-]\\s*`, 'i');
  const stripped = item.title.replace(re, '').trim();
  return stripped || item.title;
}

function MetaLine({ item }: { item: TeamKnowledgeItem }) {
  const bits: Array<{ k: string; v: string }> = [];
  if (item.status) bits.push({ k: 'status', v: item.status });
  if (item.owner) bits.push({ k: 'owner', v: item.owner });
  if (item.version) bits.push({ k: 'version', v: item.version });
  // domain rides as its own chip only on mirrors that carry it; empty/absent → no chip.
  if (item.domain) bits.push({ k: 'domain', v: item.domain });
  if (bits.length === 0) return null;
  return (
    <span className="tk-row-meta">
      {bits.map((b) => (
        <span key={b.k} className={`tk-meta-chip tk-meta-chip--${b.k}`}>{b.v}</span>
      ))}
    </span>
  );
}

function TeamKnowledgeRow({ item }: { item: TeamKnowledgeItem }) {
  const href = fileHrefFor(item);
  const inner = (
    <>
      <span className="tk-row-head">
        {item.docId && <span className="tk-row-id">{item.docId}</span>}
        <span className="tk-row-title">{displayTitle(item)}</span>
        {href && <ArrowUpRight size={14} strokeWidth={1.5} aria-hidden="true" className="tk-row-arrow" />}
      </span>
      <MetaLine item={item} />
      {item.summary && <span className="tk-row-summary">{item.summary}</span>}
    </>
  );

  if (href) {
    return (
      <li className="tk-row-li">
        <a href={href} className="tk-row tk-row--nav" aria-label={`Open ${item.docId ? `${item.docId} — ` : ''}${displayTitle(item)}`}>
          {inner}
        </a>
      </li>
    );
  }
  // No file_path on this row → a non-navigable card (never a dead link).
  return (
    <li className="tk-row-li">
      <div className="tk-row">{inner}</div>
    </li>
  );
}

export function TeamKnowledgeListView({ family }: { family: Family }) {
  const meta = FAMILY_META[family];
  const { data, loading, error } = useFetch<TeamKnowledgeResponse>(
    `/api/cockpit/team-knowledge/${family}`,
  );
  const topRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { topRef.current?.scrollIntoView({ block: 'start' }); }, [family]);

  const header = (
    <PageHeader
      title={meta.title}
      icon={meta.icon}
      subtitle={data?.available && data.items.length > 0
        ? `${data.items.length} ${data.items.length === 1 ? 'entry' : 'entries'} · ${meta.sub}`
        : meta.sub}
    />
  );

  let body: React.ReactNode;
  if (loading && !data) {
    body = <div className="list-skeleton" aria-busy="true"><div className="skeleton-block" /></div>;
  } else if (error) {
    body = <div role="alert" className="view-error">{meta.loadError}: {error}</div>;
  } else if (!data || !data.available || data.items.length === 0) {
    const Icon = meta.icon;
    body = (
      <div className="library-empty">
        <span className="library-empty-mark" aria-hidden="true">
          <Icon size={28} strokeWidth={1.5} />
        </span>
        <p className="library-empty-title">{meta.empty}</p>
        <p className="library-empty-sub">{meta.emptySub}</p>
      </div>
    );
  } else {
    body = (
      <div className="team-solo-scroll">
        <ul className="tk-rows">
          {data.items.map((item) => (
            <TeamKnowledgeRow key={item.slug} item={item} />
          ))}
        </ul>
      </div>
    );
  }

  return (
    <section ref={topRef} className="roster-view team-page-view team-solo-view animate-fade-rise">
      {header}
      <section className="team-solo-col">{body}</section>
    </section>
  );
}
