import { TrendingUp, Activity } from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { Card, Section, ModuleEmptyState } from '../components/ui';
import { trendsSummary } from '../lib/summaries';
import type { SleepPoint, StepPoint, WeightPoint } from '../lib/types';

const MARKER = 'var(--accent-marker)';
const MARKER_DEEP = 'var(--accent-marker-muted)';
const MUTED = 'var(--fg-subtle)';
const GRID = 'var(--border)';

const axis = { fontSize: 11, fill: MUTED } as const;

function shortDate(d: string): string {
  return d.slice(5); // MM-DD
}

// Compact step counts: 11398 -> "11k", 3298 -> "3,3k". Keeps the Y-axis narrow
// without clipping thousands (a wide axis steals chart width).
function compactSteps(n: number): string {
  if (n >= 1000) return `${(n / 1000).toLocaleString('en-US', { maximumFractionDigits: 1 })}k`;
  return String(Math.round(n));
}

export function Trends({
  weight,
  steps,
  sleep,
  open,
  onToggle,
}: {
  weight: WeightPoint[];
  steps: StepPoint[];
  sleep: SleepPoint[];
  open: boolean;
  onToggle: () => void;
}) {
  // No health time-series at all — a bare scaffold whose mirror has no
  // health_metric / health_sleep tables (the server returns empty arrays, not an
  // error). Guard BEFORE the Math.min/max below: Math.min(...[]) === Infinity and
  // Math.max(...[]) === -Infinity would feed the weight YAxis an inverted
  // [Infinity, -Infinity] domain and render a broken axis. Show an honest, calm
  // empty-state instead.
  const hasAnyTrend = weight.length > 0 || steps.length > 0 || sleep.length > 0;
  if (!hasAnyTrend) {
    return (
      <Section
        id="trends"
        icon={<TrendingUp size={22} strokeWidth={1.5} />}
        title="Weight trend & trends"
        hint="The calm long-term view"
        summary="no health data yet"
        open={open}
        onToggle={onToggle}
      >
        <ModuleEmptyState title="No health trends yet" icon={Activity}>
          Your mirror has no Apple Health time-series (weight, steps, sleep) yet. Run the SQLite
          upgrade to populate the <span className="font-mono">health_*</span> tables (see{' '}
          <span className="font-mono">sqlite-extension/DATA-CONTRACT.md</span>), then re-run the
          mirror regen to bring your readings in.
        </ModuleEmptyState>
      </Section>
    );
  }

  const weightMin = weight.length ? Math.min(...weight.map((w) => w.kg)) : 0;
  const weightMax = weight.length ? Math.max(...weight.map((w) => w.kg)) : 0;
  const sleepData = sleep.map((s) => ({ ...s, date: shortDate(s.local_date) }));
  const stepData = steps.map((s) => ({ ...s, date: shortDate(s.local_date) }));

  return (
    <Section
      id="trends"
      icon={<TrendingUp size={22} strokeWidth={1.5} />}
      title="Weight trend & trends"
      hint="The calm long-term view"
      summary={trendsSummary(weight, steps, sleep)}
      open={open}
      onToggle={onToggle}
    >
      <Card className="mb-md">
        <div className="mb-sm flex items-baseline justify-between">
          <h3 className="text-h3 font-[520] text-fg">Weight · 180 days</h3>
          <span className="font-mono text-caption text-fg-muted">
            {weight.length ? `${weightMin.toFixed(1)}–${weightMax.toFixed(1)} kg` : '—'}
          </span>
        </div>
        <div className="h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={weight} margin={{ top: 6, right: 8, bottom: 0, left: -12 }}>
              <defs>
                <linearGradient id="weightFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={MARKER} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={MARKER_DEEP} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="local_date" tickFormatter={shortDate} tick={axis} minTickGap={48} stroke={MUTED} />
              <YAxis domain={[Math.floor(weightMin - 1), Math.ceil(weightMax + 1)]} tick={axis} stroke={MUTED} width={42} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                labelStyle={{ color: MUTED }}
                formatter={(v: number) => [`${v.toFixed(1)} kg`, 'Weight']}
              />
              <Area type="monotone" dataKey="kg" stroke={MARKER} strokeWidth={1.75} fill="url(#weightFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid gap-md lg:grid-cols-2">
        <Card>
          <h3 className="mb-sm text-h3 font-[520] text-fg">Steps · 30 days</h3>
          <p className="mb-sm text-caption text-fg-subtle">Apple Watch source · daily total</p>
          <div className="h-[180px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stepData} margin={{ top: 4, right: 8, bottom: 0, left: -4 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="date" tick={axis} minTickGap={28} stroke={MUTED} />
                <YAxis tick={axis} stroke={MUTED} width={40} tickFormatter={compactSteps} />
                <Tooltip
                  contentStyle={{ fontSize: 12 }}
                  labelStyle={{ color: MUTED }}
                  formatter={(v: number) => [v.toLocaleString('en-US'), 'Steps']}
                />
                <Bar dataKey="steps" fill={MARKER} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h3 className="mb-sm text-h3 font-[520] text-fg">Sleep · 30 days</h3>
          <p className="mb-sm text-caption text-fg-subtle">Apple Watch · total hours</p>
          <div className="h-[180px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sleepData} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="date" tick={axis} minTickGap={28} stroke={MUTED} />
                <YAxis
                  tick={axis}
                  stroke={MUTED}
                  width={32}
                  domain={[0, 12]}
                  ticks={[0, 4, 8, 12]}
                  tickFormatter={(v: number) => `${v}h`}
                />
                <Tooltip
                  contentStyle={{ fontSize: 12 }}
                  labelStyle={{ color: MUTED }}
                  formatter={(v: number, name) => [`${Number(v).toFixed(1)} h`, name === 'total_hr' ? 'Total' : name === 'deep_hr' ? 'Deep' : 'REM']}
                />
                <Line type="monotone" dataKey="total_hr" stroke={MARKER} strokeWidth={1.75} dot={false} />
                <Line type="monotone" dataKey="deep_hr" stroke={MUTED} strokeWidth={1.25} strokeDasharray="3 3" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-sm text-caption text-fg-subtle">
            Solid: total sleep. Dashed: deep sleep. Geometry distinguishes the
            series, not color.
          </p>
        </Card>
      </div>
    </Section>
  );
}
