// Shared design-system primitives. Tokens only, no hardcoded colors/sizes.
// Grounded in shadcn card/badge/separator anatomy (shadcn.io MCP consulted).
import type { ReactNode } from 'react';
import { ArrowDownRight, ArrowUpRight, Database, Minus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Collapsible } from './disclosure';
import type { Severity, Tone, TrendView } from '../lib/status';

export function Card({
  children,
  className = '',
  as: As = 'section',
}: {
  children: ReactNode;
  className?: string;
  as?: 'section' | 'article' | 'div';
}) {
  return (
    <As
      className={`rounded-panel border border-border bg-surface-1 p-md transition-colors duration-150 ${className}`}
    >
      {children}
    </As>
  );
}

export function SectionHeader({
  icon,
  title,
  hint,
}: {
  icon: ReactNode;
  title: string;
  hint?: string;
}) {
  return (
    <div className="mb-md flex items-baseline gap-sm">
      <span className="text-marker-text" aria-hidden="true">
        {icon}
      </span>
      <h2 className="text-h2 font-[520] tracking-tight text-fg">{title}</h2>
      {hint && <span className="text-meta text-fg-muted">{hint}</span>}
    </div>
  );
}

// Collapsible section scaffold (v2 #2): a header that toggles, with a quick-stats
// summary line that stays visible whether the section is open or closed. The body
// animates open/closed. Built on the Collapsible primitive (Radix-anatomy, 0 deps).
export function Section({
  icon,
  title,
  hint,
  summary,
  open,
  onToggle,
  id,
  children,
}: {
  icon: ReactNode;
  title: string;
  hint?: string;
  summary: string;
  open: boolean;
  onToggle: () => void;
  id: string;
  children: ReactNode;
}) {
  return (
    <section className="animate-fade-rise">
      <Collapsible
        open={open}
        onToggle={onToggle}
        id={`section-${id}`}
        summary={
          <div className="flex flex-wrap items-baseline gap-x-sm gap-y-[2px]">
            <span className="text-marker-text" aria-hidden="true">
              {icon}
            </span>
            <h2 className="text-h2 font-[520] tracking-tight text-fg">{title}</h2>
            {hint && <span className="text-meta text-fg-muted">{hint}</span>}
            {/* Quick-stats: the scan line. Always present; reads even when collapsed. */}
            <span className="ml-auto text-meta text-fg-muted">{summary}</span>
          </div>
        }
      >
        <div className="mt-md">{children}</div>
      </Collapsible>
    </section>
  );
}

const TONE_CLASS: Record<Tone, string> = {
  good: 'text-success',
  watch: 'text-warning',
  attn: 'text-marker-text',
  neutral: 'text-fg-muted',
};

const TONE_DOT: Record<Tone, string> = {
  good: 'bg-[var(--status-success)]',
  watch: 'bg-[var(--status-warning)]',
  attn: 'bg-[var(--accent-marker)]',
  neutral: 'bg-[var(--fg-muted)]',
};

const TONE_CHIP_BG: Record<Tone, string> = {
  good: 'bg-[var(--status-success-soft)]',
  watch: 'bg-[var(--status-warning-soft)]',
  attn: 'bg-[var(--accent-marker-soft)]',
  neutral: 'bg-surface-2',
};

// A calm status chip — dot + label, soft tinted background. Never a solid red block.
export function StatusChip({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-xs rounded-full px-sm py-[3px] text-caption font-[460] ${TONE_CHIP_BG[tone]} ${TONE_CLASS[tone]}`}
    >
      <span className={`h-[6px] w-[6px] rounded-full ${TONE_DOT[tone]}`} aria-hidden="true" />
      {children}
    </span>
  );
}

// ---- Severity (red / amber / green) — v2 -----------------------------------
// Tom's explicit override: the metric status light must be unmistakable. Red maps
// to the GL-003 functional --status-error token (never decorative; here it's the
// "discuss with doctor" signal that always travels with a plan link).
const SEV_TEXT: Record<Severity, string> = {
  green: 'text-success',
  amber: 'text-warning',
  red: 'text-error',
  neutral: 'text-fg-muted',
};
const SEV_DOT: Record<Severity, string> = {
  green: 'bg-[var(--status-success)]',
  amber: 'bg-[var(--status-warning)]',
  red: 'bg-[var(--status-error)]',
  neutral: 'bg-[var(--fg-muted)]',
};
const SEV_CHIP_BG: Record<Severity, string> = {
  green: 'bg-[var(--status-success-soft)]',
  amber: 'bg-[var(--status-warning-soft)]',
  red: 'bg-[var(--status-error-soft)]',
  neutral: 'bg-surface-2',
};

// Severity chip — same calm anatomy as StatusChip, but red is genuinely red.
export function SeverityChip({ severity, children }: { severity: Severity; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-xs rounded-full px-sm py-[3px] text-caption font-[500] ${SEV_CHIP_BG[severity]} ${SEV_TEXT[severity]}`}
    >
      <span className={`h-[6px] w-[6px] rounded-full ${SEV_DOT[severity]}`} aria-hidden="true" />
      {children}
    </span>
  );
}

// A thin left status rail — gives each metric card a readable red/amber/green
// edge without flooding the card in colour (calm, but unmistakable).
export function severityRail(severity: Severity): string {
  const RAIL: Record<Severity, string> = {
    green: 'border-l-[3px] border-l-[var(--status-success)]',
    amber: 'border-l-[3px] border-l-[var(--status-warning)]',
    red: 'border-l-[3px] border-l-[var(--status-error)]',
    neutral: 'border-l-[3px] border-l-transparent',
  };
  return RAIL[severity];
}

// ---- Delta arrow (trend vs prior reference) — v2 ----------------------------
// Direction comes from the data; colour comes from `sense` (is this move
// reassuring or worth watching for THIS metric). "no prior value" renders honestly
// with no arrow and no colour.
const SENSE_CLASS = {
  better: 'text-success',
  worse: 'text-warning',
  flat: 'text-fg-muted',
  info: 'text-fg-muted',
} as const;

export function DeltaArrow({ trend }: { trend: TrendView | null }) {
  if (!trend) return null;
  if (!trend.hasPrior) {
    return (
      <span className="inline-flex items-center gap-xs text-caption text-fg-subtle">no prior value</span>
    );
  }
  const Icon = trend.direction > 0 ? ArrowUpRight : trend.direction < 0 ? ArrowDownRight : Minus;
  const cls = SENSE_CLASS[trend.sense];
  const a11y =
    trend.direction > 0 ? 'up' : trend.direction < 0 ? 'down' : 'unchanged';
  return (
    <span className={`inline-flex animate-delta-pop items-center gap-[3px] text-caption font-[500] ${cls}`}>
      <Icon size={13} strokeWidth={2} aria-hidden="true" />
      <span className="font-mono tabular-nums">{trend.display}</span>
      <span className="sr-only">{a11y},</span>
      <span className="font-[400] text-fg-subtle">{trend.window}</span>
    </span>
  );
}

// ---- Valence (MIND patterns: good / watch / straining) — v3 #1 -------------
// Colours a psyche pattern by whether it's a strength or a struggle. Maps to the
// SAME calm GL-003 status tokens as the metric severity (good→success, watch→
// warning, strain→error, neutral→muted) so the whole dashboard speaks one colour
// language. Kept soft — a struggle reads as "straining", never as an alarm block.
import type { ValenceTone } from '../lib/valence';

const VAL_TEXT: Record<ValenceTone, string> = {
  good: 'text-success',
  watch: 'text-warning',
  strain: 'text-error',
  neutral: 'text-fg-muted',
};
const VAL_DOT: Record<ValenceTone, string> = {
  good: 'bg-[var(--status-success)]',
  watch: 'bg-[var(--status-warning)]',
  strain: 'bg-[var(--status-error)]',
  neutral: 'bg-[var(--fg-muted)]',
};
const VAL_CHIP_BG: Record<ValenceTone, string> = {
  good: 'bg-[var(--status-success-soft)]',
  watch: 'bg-[var(--status-warning-soft)]',
  strain: 'bg-[var(--status-error-soft)]',
  neutral: 'bg-surface-2',
};

export function ValenceChip({ tone, children }: { tone: ValenceTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-xs rounded-full px-sm py-[3px] text-caption font-[460] ${VAL_CHIP_BG[tone]} ${VAL_TEXT[tone]}`}
    >
      <span className={`h-[6px] w-[6px] rounded-full ${VAL_DOT[tone]}`} aria-hidden="true" />
      {children}
    </span>
  );
}

// A thin left status rail for a pattern card — the same calm edge the metric cards
// use, so a strength/struggle reads at a glance without flooding the card.
export function valenceRail(tone: ValenceTone): string {
  const RAIL: Record<ValenceTone, string> = {
    good: 'border-l-[3px] border-l-[var(--status-success)]',
    watch: 'border-l-[3px] border-l-[var(--status-warning)]',
    strain: 'border-l-[3px] border-l-[var(--status-error)]',
    neutral: 'border-l-[3px] border-l-transparent',
  };
  return RAIL[tone];
}

// Neutral chip (diagnoses, tags) — surface-2, no status color.
export function Chip({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className="inline-flex items-center gap-xs rounded-full border border-border bg-surface-2 px-sm py-[3px] text-caption text-fg-muted"
    >
      {children}
    </span>
  );
}

export function Mono({ children }: { children: ReactNode }) {
  return <span className="font-mono tabular-nums">{children}</span>;
}

// ModuleEmptyState — the honest "the data behind this module isn't in your mirror
// yet" panel. A freshly-downloaded basic scaffold's mypka.db carries only the core
// tables (notes/journal/links/…); the richer surfaces (health_*, workouts,
// v_open_invoices) are absent until the SQLite upgrade is run. When that backing
// data is missing the module shows THIS instead of a crash, a wall of "—", or a
// blank: it names what's missing and points to the fix. Calm and guiding, never
// alarming — same dashed-panel + brass-glyph vocabulary as .food-empty /
// .library-empty (GL-003 §8.7 empty states). Tokens only; styling in cockpit.css
// (.module-empty*). Default glyph is a database (this is a data-availability gap).
export function ModuleEmptyState({
  title,
  children,
  icon: Icon = Database,
  hint,
}: {
  title: string;
  /** What's missing + the fix. Plain prose; keep it to a sentence or two. */
  children: ReactNode;
  icon?: LucideIcon;
  /** Optional second line — e.g. the exact doc to read. */
  hint?: ReactNode;
}) {
  return (
    <div className="module-empty" role="status">
      <span className="module-empty-mark" aria-hidden="true">
        <Icon size={24} strokeWidth={1.5} />
      </span>
      <p className="module-empty-title">{title}</p>
      <p className="module-empty-sub">{children}</p>
      {hint && <p className="module-empty-hint">{hint}</p>}
    </div>
  );
}
