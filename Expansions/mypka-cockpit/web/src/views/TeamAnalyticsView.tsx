// TeamAnalyticsView.tsx — "Team Analytics": specialist session load over a
// selectable time range. The interactive twin of the Week in Ink deck's
// "team at work" slide, unbounded by the weekly window.
//
// Source: /api/cockpit/analytics/team?from&to over session_logs (one row per run).
// Read-only, loopback posture like every other view. Avatars come from the
// Team/-jailed /api/cockpit/avatar route; an absent path OR a failed load falls
// back to initials rather than a broken image (Marcus has no avatar on disk).
//
// Every value is a GL-003 token; no hardcoded colours.
import { useMemo, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { useFetch } from '../lib/useCockpit';
import './team.css';
import './analytics.css';

interface AgentRow {
  slug: string;
  name: string;
  sessions: number;
  share: number;
  role: string | null;
  avatarPath: string | null;
  firstDay: string;
  lastDay: string;
}
interface Analytics {
  range: { from: string; to: string };
  bounds: { from: string | null; to: string | null; total: number };
  totals: { sessions: number; specialists: number; days: number; meanPerSpecialist: number };
  agents: AgentRow[];
  series: { day: string; sessions: number }[];
}

function avatarUrl(path: string | null): string | null {
  return path ? `/api/cockpit/avatar?path=${encodeURIComponent(path)}` : null;
}

function isoDaysAgo(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

const PRESETS = [
  { key: '7d', label: '7 days', days: 7 },
  { key: '30d', label: '30 days', days: 30 },
  { key: '90d', label: '90 days', days: 90 },
  { key: 'all', label: 'All time', days: null as number | null },
];

function Face({ agent, size }: { agent: AgentRow; size: 'row' | 'hero' }) {
  const [failed, setFailed] = useState(false);
  const url = avatarUrl(agent.avatarPath);
  const cls = size === 'hero' ? 'an-hero-img' : 'an-face';
  if (!url || failed) {
    return (
      <span className={`${cls} an-initials`} aria-label={agent.name}>
        {agent.slug.slice(0, 2).toUpperCase()}
      </span>
    );
  }
  return (
    <img
      className={cls}
      src={url}
      alt={agent.name}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

export function TeamAnalyticsView() {
  const [preset, setPreset] = useState('90d');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const url = useMemo(() => {
    if (preset === 'custom' && customFrom && customTo) {
      return `/api/cockpit/analytics/team?from=${customFrom}&to=${customTo}`;
    }
    const p = PRESETS.find((x) => x.key === preset);
    if (!p || p.days === null) return '/api/cockpit/analytics/team';
    return `/api/cockpit/analytics/team?from=${isoDaysAgo(p.days)}&to=${isoDaysAgo(0)}`;
  }, [preset, customFrom, customTo]);

  const { data, loading, error } = useFetch<Analytics>(url);

  const max = data?.agents.length ? Math.max(...data.agents.map((a) => a.sessions)) : 1;
  const peak = data?.series.length ? Math.max(...data.series.map((s) => s.sessions), 1) : 1;
  const top = data?.agents[0];

  return (
    <section className="team-page-view team-solo-view animate-fade-rise">
      <PageHeader
        title="Team Analytics"
        icon={BarChart3}
        subtitle="Specialist session load across a time range"
      />

      <div className="an-controls" role="group" aria-label="Time range">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            className={`an-chip${preset === p.key ? ' on' : ''}`}
            aria-pressed={preset === p.key}
            onClick={() => setPreset(p.key)}
          >
            {p.label}
          </button>
        ))}
        <span className="an-sep" aria-hidden="true" />
        <label className="an-date">
          <span>From</span>
          <input
            type="date"
            value={customFrom}
            min={data?.bounds.from ?? undefined}
            max={data?.bounds.to ?? undefined}
            onChange={(e) => { setCustomFrom(e.target.value); setPreset('custom'); }}
          />
        </label>
        <label className="an-date">
          <span>To</span>
          <input
            type="date"
            value={customTo}
            min={data?.bounds.from ?? undefined}
            max={data?.bounds.to ?? undefined}
            onChange={(e) => { setCustomTo(e.target.value); setPreset('custom'); }}
          />
        </label>
        {preset === 'custom' && (!customFrom || !customTo) && (
          <span className="an-hint">pick both dates</span>
        )}
      </div>

      {loading && <p className="an-msg">Loading…</p>}
      {error && <p className="an-msg an-err">{error}</p>}

      {data && !loading && (
        <div className="an-grid">
          <section className="an-card" aria-label="Session load by specialist">
            <h2 className="an-ct">Session load by specialist</h2>
            <p className="an-cs">
              {data.totals.specialists} specialists · {data.totals.sessions} runs ·{' '}
              {data.range.from} to {data.range.to}
            </p>
            <div className="an-scroll">
              {data.agents.length === 0 && (
                <p className="an-msg">No sessions recorded in this range.</p>
              )}
              {data.agents.map((a) => (
                <div className="an-row" key={a.slug}>
                  <span className="an-nm" title={a.name}>{a.slug}</span>
                  <span className="an-track">
                    <i className="an-fill" style={{ width: `${(a.sessions / max) * 100}%` }} />
                    <span
                      className="an-face-pos"
                      style={{
                        left: `max(15px, min(calc(100% - 15px), ${(a.sessions / max) * 100}%))`,
                      }}
                    >
                      <Face agent={a} size="row" />
                    </span>
                  </span>
                  <span className="an-n">{a.sessions}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="an-card" aria-label="Summary">
            <h2 className="an-ct">Who carried the range</h2>
            <p className="an-cs">share of all runs</p>
            <div className="an-scroll">
              {top && (
                <div className="an-hero">
                  <Face agent={top} size="hero" />
                  <span className="an-hero-nm">{top.name}</span>
                  {top.role && <span className="an-hero-role">{top.role}</span>}
                  <span className="an-hero-sub">
                    busiest · {top.sessions} runs · {top.share}%
                  </span>
                </div>
              )}
              <div className="an-kpi"><b>{data.totals.sessions}</b><span>sessions</span></div>
              <div className="an-kpi"><b>{data.totals.specialists}</b><span>specialists</span></div>
              <div className="an-kpi"><b>{data.totals.meanPerSpecialist}</b><span>mean each</span></div>
              <div className="an-kpi"><b>{data.totals.days}</b><span>days in range</span></div>

              <h3 className="an-sub">Daily volume</h3>
              <div className="an-spark" role="img"
                   aria-label={`Daily session volume, peak ${peak}`}>
                {data.series.map((s) => (
                  <i
                    key={s.day}
                    title={`${s.day}: ${s.sessions}`}
                    style={{ height: `${Math.max(2, (s.sessions / peak) * 100)}%` }}
                    className={s.sessions === 0 ? 'zero' : undefined}
                  />
                ))}
              </div>
              <p className="an-cs">peak {peak} runs in a day</p>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
