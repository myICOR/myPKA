import { useState } from 'react';
import { Activity, ArrowRight } from 'lucide-react';
import {
  Card,
  Section,
  SeverityChip,
  Chip,
  Mono,
  DeltaArrow,
  severityRail,
  ModuleEmptyState,
} from '../components/ui';
import { Sheet } from '../components/disclosure';
import { ReadableBlocks } from '../components/prose';
import { buildMetricViews, bodySummary } from '../lib/status';
import type { DiagnosisChip, BodyMetrics, LabPanel, ReadableBlock } from '../lib/types';

export function Body({
  metrics,
  diagnoses,
  labs,
  open,
  onToggle,
}: {
  metrics: BodyMetrics;
  diagnoses: { confirmed: { name: string; icd: string | null; confirmed: string | null }[]; chips: DiagnosisChip[] };
  labs: { panels: LabPanel[] };
  open: boolean;
  onToggle: () => void;
}) {
  const views = buildMetricViews(metrics);

  // Nothing to show — a bare scaffold whose mirror has no health readings, no
  // recorded diagnoses, and no lab panels (the server returns empty/undefined, not
  // an error). Without this guard the grid renders nine "—" cards plus an empty
  // "Diagnoses" card, which reads as broken rather than not-yet-populated. Show an
  // honest empty-state naming what's missing + the fix instead.
  const hasAnyReading = views.some((v) => v.value !== null && v.value !== undefined);
  const hasDiagnoses = diagnoses.chips.length > 0;
  const hasLabs = labs.panels.some((p) => p.table || p.note);
  if (!hasAnyReading && !hasDiagnoses && !hasLabs) {
    return (
      <Section
        id="body"
        icon={<Activity size={22} strokeWidth={1.5} />}
        title="Body"
        hint="Apple Health · latest reading"
        summary="no readings yet"
        open={open}
        onToggle={onToggle}
      >
        <ModuleEmptyState title="No body readings yet" icon={Activity}>
          Your mirror has no Apple Health metrics, diagnoses, or lab values yet. Run the SQLite
          upgrade to populate the <span className="font-mono">health_*</span> tables (see{' '}
          <span className="font-mono">sqlite-extension/DATA-CONTRACT.md</span>) and keep your
          readings in <span className="font-mono">health.md</span>; they appear here after the next
          mirror regen.
        </ModuleEmptyState>
      </Section>
    );
  }

  return (
    <Section
      id="body"
      icon={<Activity size={22} strokeWidth={1.5} />}
      title="Body"
      hint="Apple Health · latest reading"
      summary={bodySummary(views)}
      open={open}
      onToggle={onToggle}
    >
      {/* Metric grid — red/amber/green rail + chip, trend arrow vs prior value,
          and every RED metric still carries its "→ Planned" plan link. */}
      <div className="grid grid-cols-2 gap-md sm:grid-cols-3 lg:grid-cols-4">
        {views.map((v) => (
          <Card
            key={v.key}
            as="article"
            className={`flex flex-col gap-xs ${severityRail(v.severity)}`}
          >
            <div className="flex items-center justify-between gap-xs">
              <span className="text-meta text-fg-muted">{v.label}</span>
              <SeverityChip severity={v.severity}>{v.toneLabel}</SeverityChip>
            </div>
            <div className="flex items-baseline gap-xs">
              <span className="text-bignum font-[600] leading-none text-fg">
                <Mono>{v.display}</Mono>
              </span>
              {v.unit && <span className="text-caption text-fg-muted">{v.unit}</span>}
            </div>
            {/* Trend arrow + delta vs the prior reference window. */}
            {v.trend && <DeltaArrow trend={v.trend} />}
            <span className="text-caption text-fg-subtle">{v.reference}</span>
            {v.sub && <span className="text-caption text-fg-subtle">{v.sub}</span>}
            {/* The health-anxiety-aware guarantee: a red value always shows its plan. */}
            {v.plan && (
              <span
                className={`mt-xs inline-flex items-center gap-xs text-caption ${
                  v.severity === 'red' ? 'font-[500] text-error' : 'text-marker-text'
                }`}
              >
                <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
                Planned: {v.plan}
              </span>
            )}
          </Card>
        ))}
      </div>

      {/* Diagnoses — neutral chips, never red. */}
      <Card className="mt-md">
        <h3 className="mb-sm text-h3 font-[520] text-fg">Diagnoses & history</h3>
        <div className="flex flex-wrap gap-sm">
          {diagnoses.chips.map((c) => (
            <Chip key={c.label} title={c.note}>
              <span className="text-fg">{c.label}</span>
              <span className="text-fg-subtle">· {c.code}</span>
            </Chip>
          ))}
        </div>
      </Card>

      {/* Lab tables — rendered from health.md markdown. Each panel's assessment
          prose is now click-to-expand (full text in a Sheet), never cut. */}
      {labs.panels.some((p) => p.table) && (
        <div className="mt-md">
          <h3 className="mb-sm text-h3 font-[520] text-fg">Lab values · history</h3>
          <p className="mb-md text-caption leading-relaxed text-fg-subtle">
            From the 2022–2025 results, as recorded in <span className="font-mono">health.md</span>.
            Each row is an assessment, not a finding.
          </p>
          <div className="grid gap-md md:grid-cols-2">
            {labs.panels
              .filter((p) => p.table)
              .map((p) => (
                <LabPanelCard key={p.title} panel={p} />
              ))}
          </div>

          {labs.panels.some((p) => !p.table && p.note) && (
            <Card className="mt-md">
              <h4 className="mb-sm text-meta font-[460] text-fg-muted">
                Open data points & notes
              </h4>
              <ul className="flex flex-col gap-sm">
                {labs.panels
                  .filter((p) => !p.table && p.note)
                  .map((p) => (
                    <li key={p.title} className="flex flex-col gap-[2px]">
                      <span className="text-caption font-[460] text-fg">{p.title}</span>
                      <span className="text-caption leading-relaxed text-fg-muted">{p.note}</span>
                    </li>
                  ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </Section>
  );
}

// A lab panel: the table stays visible; the assessment prose is previewed (one
// line) and the whole assessment opens in a Sheet — nothing permanently cut.
function LabPanelCard({ panel }: { panel: LabPanel }) {
  const hasFull = panel.full && panel.full.length > 0;
  return (
    <Card as="article">
      <h4 className="mb-sm text-body font-[520] text-fg">{panel.title}</h4>
      {panel.table ? <LabTable table={panel.table} /> : null}
      {panel.assessment && (
        <div className="mt-sm border-t border-border-subtle pt-sm">
          <p className="line-clamp-2 text-caption leading-relaxed text-fg-muted">
            {panel.assessment}
          </p>
          {hasFull && (
            <ExpandableLink title={`${panel.title} · assessment`} blocks={panel.full} />
          )}
        </div>
      )}
    </Card>
  );
}

// Small "Read full text" link that opens a Sheet with the full readable blocks.
function ExpandableLink({ title, blocks }: { title: string; blocks: ReadableBlock[] }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        className="mt-xs inline-flex items-center gap-xs text-caption text-marker-text hover:underline focus-visible:underline"
      >
        Read full text →
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} title={title} subtitle="From health.md · assessment, not a finding">
        <ReadableBlocks blocks={blocks} />
      </Sheet>
    </>
  );
}

function LabTable({ table }: { table: { headers: string[]; rows: string[][] } }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-caption">
        <thead>
          <tr>
            {table.headers.map((h, i) => (
              <th
                key={i}
                className="border-b border-border-subtle py-xs pr-sm text-left font-[460] text-fg-muted"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className={`border-b border-border-subtle py-xs pr-sm ${
                    ci === 0 ? 'text-fg' : 'font-mono tabular-nums text-fg-muted'
                  }`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
