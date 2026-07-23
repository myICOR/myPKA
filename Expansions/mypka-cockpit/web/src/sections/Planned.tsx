import { useState } from 'react';
import { Compass, CalendarClock, CheckCircle2, Utensils, Repeat, ArrowUpRight } from 'lucide-react';
import { Card, Section, StatusChip, Chip } from '../components/ui';
import { Sheet } from '../components/disclosure';
import { ReadableBlocks } from '../components/prose';
import { plannedSummary } from '../lib/summaries';
import { navigate } from '../lib/router';
import type { HabitCard, NoteLink, OpenQuestion, PersonalTask, ReadableBlock } from '../lib/types';

// v3 #1 — "open the actual plan / more detail" for any PLANNED item that resolves
// to a real note. Routes through the SAME internal router as NoteView (button ->
// #/note/:type/:slug), never a raw anchor — so it opens in-app, no new tab.
function OpenNoteLink({ note, label = 'Open plan' }: { note: NoteLink; label?: string }) {
  return (
    <button
      type="button"
      onClick={() => navigate({ name: 'note', type: note.type, slug: note.slug })}
      className="mt-[2px] inline-flex w-fit items-center gap-xs text-caption text-marker-text hover:underline focus-visible:underline"
    >
      {label}
      <ArrowUpRight size={13} strokeWidth={1.5} aria-hidden="true" />
    </button>
  );
}

// PLANNED — the path forward. This is the section that keeps the dashboard from
// reading as a verdict: every off-range body signal has its next step living here.
export function Planned({
  habits,
  openQuestions,
  tasks,
  nutritionPlan,
  open,
  onToggle,
}: {
  habits: HabitCard[];
  openQuestions: OpenQuestion[];
  tasks: PersonalTask[];
  nutritionPlan: { exists: boolean; path: string; note?: NoteLink | null };
  open: boolean;
  onToggle: () => void;
}) {
  // Open exams: answered items drop to the back; overdue/deadline rise to the front,
  // but framed calmly as "next step", never as alarm.
  const exams = [...openQuestions].sort((a, b) => {
    const rank = (q: OpenQuestion) => (q.answered ? 2 : q.overdue || q.deadline ? 0 : 1);
    return rank(a) - rank(b);
  });

  return (
    <Section
      id="planned"
      icon={<Compass size={22} strokeWidth={1.5} />}
      title="Planned"
      hint="What's being done · the path forward"
      summary={plannedSummary(openQuestions, tasks)}
      open={open}
      onToggle={onToggle}
    >
      <div className="grid gap-md lg:grid-cols-3">
        {/* Habits — the small, owned actions. Each opens its full "why" in a Sheet. */}
        <Card className="lg:col-span-1">
          <h3 className="mb-sm flex items-center gap-xs text-h3 font-[520] text-fg">
            <Repeat size={18} strokeWidth={1.5} className="text-marker-text" aria-hidden="true" />
            Habits
          </h3>
          <div className="flex flex-col gap-md">
            {habits.map((h) =>
              h.missing ? null : (
                <article key={h.slug} className="flex flex-col gap-xs">
                  <div className="flex items-baseline justify-between gap-sm">
                    {/* The habit name opens the actual habit note in the viewer
                        (habits ARE in v_notes), routed through the internal router. */}
                    <button
                      type="button"
                      onClick={() => navigate({ name: 'note', type: 'habits', slug: h.slug })}
                      className="text-left text-body font-[520] text-fg hover:text-marker-text focus-visible:text-marker-text"
                      title="Open habit"
                    >
                      {h.name}
                    </button>
                    <StatusChip tone="good">
                      {h.cadence === 'daily' ? 'daily' : h.cadence ?? 'active'}
                    </StatusChip>
                  </div>
                  {h.lead && (
                    <p className="line-clamp-3 text-caption leading-relaxed text-fg-muted">{h.lead}</p>
                  )}
                  <OpenNoteLink note={{ type: 'habits', slug: h.slug }} label="Open habit" />
                  {h.full && h.full.length > 0 && (
                    <FullTextLink title={h.name} subtitle="Why this habit" blocks={h.full} />
                  )}
                  {h.started && (
                    <span className="font-mono text-caption text-fg-subtle">since {h.started}</span>
                  )}
                </article>
              )
            )}
          </div>

          {/* Nutrition plan link — a calm pointer, not a CTA shout. */}
          <div className="mt-md border-t border-border-subtle pt-sm">
            <h4 className="mb-xs flex items-center gap-xs text-meta font-[460] text-fg-muted">
              <Utensils size={15} strokeWidth={1.5} aria-hidden="true" />
              Nutrition plan
            </h4>
            {nutritionPlan.exists ? (
              <div className="flex flex-col gap-xs">
                <p className="text-caption leading-relaxed text-fg-muted">Available.</p>
                {nutritionPlan.note ? (
                  <OpenNoteLink note={nutritionPlan.note} label="Open nutrition plan" />
                ) : (
                  <span className="font-mono text-caption text-fg-subtle break-all">
                    {nutritionPlan.path}
                  </span>
                )}
              </div>
            ) : (
              <p className="text-caption text-fg-subtle">Not set up yet.</p>
            )}
          </div>
        </Card>

        {/* Open exams / next steps — the medical follow-ups, calmly ranked. Each
            opens its full detail (incl. sub-bullets) in a Sheet — nothing cut. */}
        <Card className="lg:col-span-2">
          <h3 className="mb-sm flex items-center gap-xs text-h3 font-[520] text-fg">
            <CalendarClock size={18} strokeWidth={1.5} className="text-marker-text" aria-hidden="true" />
            Open examinations & next steps
          </h3>
          <ul className="flex flex-col divide-y divide-[var(--border-subtle)]">
            {exams.map((q) => (
              <ExamRow key={q.num} q={q} />
            ))}
          </ul>

          {/* Personal tasks read straight from the markdown task files. */}
          {tasks.length > 0 && (
            <div className="mt-md border-t border-border-subtle pt-sm">
              <h4 className="mb-sm text-meta font-[460] text-fg-muted">Personal tasks</h4>
              <ul className="flex flex-col gap-sm">
                {tasks.map((t) => (
                  <li key={t.file} className="flex items-start justify-between gap-sm">
                    <span className="min-w-0 text-caption leading-relaxed text-fg-muted">{t.title}</span>
                    <span className="flex shrink-0 items-center gap-xs">
                      {t.due && <Chip>due {t.due}</Chip>}
                      <StatusChip tone={t.status === 'in-progress' ? 'watch' : 'neutral'}>
                        {t.status === 'in-progress' ? 'in progress' : 'open'}
                      </StatusChip>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>
    </Section>
  );
}

// One exam/next-step row. The preview text is clamped; the full detail (which can
// run 500+ chars with sub-bullets) opens in a Sheet.
function ExamRow({ q }: { q: OpenQuestion }) {
  const hasFull = q.full && q.full.length > 0;
  return (
    <li className="flex items-start gap-sm py-sm">
      <span className="mt-[2px]">
        {q.answered ? (
          <CheckCircle2 size={16} strokeWidth={1.5} className="text-success" aria-hidden="true" />
        ) : (
          <span
            className="block h-[7px] w-[7px] rounded-full bg-[var(--accent-marker)]"
            aria-hidden="true"
          />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-xs">
          <span
            className={`text-body font-[460] ${q.answered ? 'text-fg-muted line-through' : 'text-fg'}`}
          >
            {q.title}
          </span>
          {q.answered && <StatusChip tone="good">resolved</StatusChip>}
          {!q.answered && q.overdue && <StatusChip tone="attn">up next</StatusChip>}
          {!q.answered && q.deadline && <StatusChip tone="watch">deadline {q.deadline}</StatusChip>}
        </div>
        {!q.answered && q.text && (
          <p className="mt-[2px] line-clamp-2 text-caption leading-relaxed text-fg-muted">{q.text}</p>
        )}
        <div className="flex flex-wrap items-center gap-md">
          {/* If the exam maps to a real note (HNO project, PKV/BMI project, …),
              offer a click into the actual plan; otherwise the full text opens in
              the Sheet — the honest fallback for text-only items. */}
          {q.note && <OpenNoteLink note={q.note} label="Go to case" />}
          {hasFull && <FullTextLink title={q.title} subtitle="Details & next steps" blocks={q.full} />}
        </div>
      </div>
    </li>
  );
}

// Reusable "Read full text →" that opens a Sheet with the full readable blocks.
function FullTextLink({
  title,
  subtitle,
  blocks,
}: {
  title: string;
  subtitle?: string;
  blocks: ReadableBlock[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        className="mt-[2px] inline-flex w-fit items-center gap-xs text-caption text-marker-text hover:underline focus-visible:underline"
      >
        Read full text →
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} title={title} subtitle={subtitle}>
        <ReadableBlocks blocks={blocks} />
      </Sheet>
    </>
  );
}
