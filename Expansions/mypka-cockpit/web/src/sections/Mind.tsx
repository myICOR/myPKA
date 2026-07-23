import { useState } from 'react';
import { Brain } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from 'recharts';
import { Card, Section, ValenceChip, valenceRail } from '../components/ui';
import { ExpandableCard, Collapsible, Sheet } from '../components/disclosure';
import { ReadableBlocks } from '../components/prose';
import { mindSummary } from '../lib/summaries';
import { useCollapsed } from '../lib/useCollapsed';
import { patternValence } from '../lib/valence';
import type { JournalEntry, PsycheState, TopicCard, ValencePoint } from '../lib/types';

const MARKER = 'var(--accent-marker)';
const MUTED = 'var(--fg-subtle)';

// ---- Mood colour signal ----------------------------------------------------
// PRIMARY: `mood_valence` (1..5 integer, LANGUAGE-NEUTRAL — Silas added it to the
// journal table). Maps to the SAME calm GL-003 status tokens the rest of the
// dashboard uses, deliberately NOT alarmist (never --status-error):
//   1–2 → low      → text-warning (soft amber, "straining", not red)
//   3   → neutral  → text-fg-muted (mixed / steady, no colour)
//   4–5 → good     → text-success (calm green)
// Works for ANY language the user journals in, because it reads the number, not the word.
function valenceTone(v: number | null | undefined): string {
  if (typeof v !== 'number') return 'text-fg-muted';
  if (v <= 2) return 'text-warning';
  if (v >= 4) return 'text-success';
  return 'text-fg-muted'; // 3 → neutral / mixed
}

// FALLBACK ONLY (legacy/edge): for entries where mood_valence is NULL/absent, fall
// back to a free-text word-matcher over common English mood words. This is a
// best-effort safety net for journals that predate mood_valence; unmatched words
// simply stay neutral (muted, no colour). mood_valence is primary — extend these
// lists locally if your journal uses another language's mood vocabulary.
function moodToneFromWord(mood: string | null): string {
  if (!mood) return 'text-fg-muted';
  const m = mood.toLowerCase();
  if (/(focus|confident|clear|happy|calm|content|good|great|high|energi[sz]ed)/.test(m)) return 'text-success';
  if (/(anxious|worried|low|exhausted|tired|drained|stress|overwhelmed|panic|frustrated)/.test(m)) return 'text-warning';
  return 'text-fg-muted';
}

// Resolve the mood label's colour: mood_valence first, the word-matcher only when
// valence is absent. The free-text `mood` word is always the visible label.
function moodTone(entry: { mood: string | null; mood_valence: number | null }): string {
  return typeof entry.mood_valence === 'number'
    ? valenceTone(entry.mood_valence)
    : moodToneFromWord(entry.mood);
}

export function Mind({
  psyche,
  topics,
  mood,
  open,
  onToggle,
}: {
  psyche: PsycheState;
  topics: TopicCard[];
  mood: { journal: JournalEntry[]; valence: ValencePoint[] };
  open: boolean;
  onToggle: () => void;
}) {
  const valence = mood.valence.filter((v) => typeof v.valence === 'number');
  const [patternsOpen, togglePatterns] = useCollapsed('mind-patterns', true);

  return (
    <Section
      id="mind"
      icon={<Brain size={22} strokeWidth={1.5} />}
      title="Mind"
      hint="Patterns · mood · profile"
      summary={mindSummary(topics, mood.journal)}
      open={open}
      onToggle={onToggle}
    >
      {/* v3 #1 — patterns moved to the TOP of Mind so they sit directly
          after the Body values (Tom's explicit ask). Each card is valence-coloured
          (good / watch / straining) and opens its FULL text in a Sheet. */}
      <div className="mb-md">
        <Collapsible
          open={patternsOpen}
          onToggle={togglePatterns}
          summary={
            <div className="flex flex-wrap items-baseline gap-x-sm">
              <h3 className="text-h3 font-[520] text-fg">Patterns</h3>
              <span className="ml-auto text-meta text-fg-muted">
                {topics.filter((t) => !t.missing).length} patterns · tap to read
              </span>
            </div>
          }
        >
          <div className="grid gap-md sm:grid-cols-2 lg:grid-cols-4">
            {topics.map((t) => {
              const v = patternValence(t.slug);
              return t.missing || !t.full ? (
                <Card key={t.slug} as="article" className={`flex flex-col gap-xs ${valenceRail(v.tone)}`}>
                  <div className="flex items-start justify-between gap-xs">
                    <h4 className="text-body font-[520] text-fg">{t.name}</h4>
                    <ValenceChip tone={v.tone}>{v.label}</ValenceChip>
                  </div>
                  <p className="text-caption text-fg-subtle">Not captured yet.</p>
                </Card>
              ) : (
                <ExpandableCard
                  key={t.slug}
                  sheetTitle={t.name}
                  sheetSubtitle="Lived pattern · health.md / Topics"
                  className={valenceRail(v.tone)}
                  title={
                    <div className="flex items-start justify-between gap-xs">
                      <h4 className="text-body font-[520] text-fg">{t.name}</h4>
                      <ValenceChip tone={v.tone}>{v.label}</ValenceChip>
                    </div>
                  }
                  preview={
                    <p className="line-clamp-5 text-caption leading-relaxed text-fg-muted">
                      {t.lead}
                    </p>
                  }
                >
                  <ReadableBlocks blocks={t.full} />
                </ExpandableCard>
              );
            })}
          </div>
        </Collapsible>
      </div>

      <div className="grid gap-md lg:grid-cols-3">
        {/* Psyche profile — stub state rendered honestly. */}
        <Card className="lg:col-span-1">
          <h3 className="mb-sm text-h3 font-[520] text-fg">Psychological profile</h3>
          {psyche.present && psyche.isStub ? (
            <div className="flex flex-col gap-sm">
              <p className="text-body text-fg-muted">Profile in progress.</p>
              <p className="text-caption leading-relaxed text-fg-subtle">
                Anima fills the synthesis layer from the patterns and journal entries.
              </p>
              <p className="text-caption leading-relaxed text-fg-subtle">
                Gated — only on a durable pattern. Until then, the four lived patterns
                below are the source.
              </p>
            </div>
          ) : (
            <p className="text-body text-fg-muted">Profile available.</p>
          )}

          {valence.length > 0 && (
            <div className="mt-md border-t border-border-subtle pt-sm">
              <div className="mb-xs flex items-baseline justify-between">
                <span className="text-meta text-fg-muted">Valence (Apple State of Mind)</span>
                <span className="text-caption text-fg-subtle">{valence.length} points · through 2025-08</span>
              </div>
              <div className="h-[44px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={valence} margin={{ top: 4, bottom: 4, left: 0, right: 0 }}>
                    <YAxis domain={[-1, 1]} hide />
                    <Tooltip
                      contentStyle={{ fontSize: 12 }}
                      labelStyle={{ color: MUTED }}
                      formatter={(v: number) => [v.toFixed(2), 'valence']}
                    />
                    <Line type="monotone" dataKey="valence" stroke={MARKER} strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-xs text-caption text-fg-subtle">
                Sparse and older — meant as calm context, not a current trend.
              </p>
            </div>
          )}
        </Card>

        {/* Recent mood/energy — free-text list, NOT a numeric line. Each entry's
            title opens (sheet) so a long journal title is never cut. */}
        <Card className="lg:col-span-2">
          <h3 className="mb-sm text-h3 font-[520] text-fg">Mood & energy · recent</h3>
          <ul className="flex flex-col divide-y divide-[var(--border-subtle)]">
            {mood.journal.map((e, i) => (
              <JournalRow key={i} entry={e} />
            ))}
          </ul>
          <p className="mt-sm text-caption text-fg-subtle">
            Free text from the journal — deliberately a list, not a score. The words carry
            more than a scale.
          </p>
        </Card>
      </div>

    </Section>
  );
}

// A journal row whose (possibly long) title opens in a Sheet — no permanent cut.
function JournalRow({ entry: e }: { entry: JournalEntry }) {
  const [open, setOpen] = useState(false);
  const hasTitle = !!e.title && e.title.length > 0;
  return (
    <li className="flex items-center gap-md py-sm">
      <time className="w-[84px] shrink-0 font-mono text-caption text-fg-subtle">{e.entry_date}</time>
      <div className="flex shrink-0 flex-wrap gap-xs">
        {e.mood && <span className={`text-caption font-[460] ${moodTone(e)}`}>{e.mood}</span>}
        {e.energy && <span className="text-caption text-fg-muted">· {e.energy}</span>}
      </div>
      {hasTitle &&
        (e.title!.length > 48 ? (
          <>
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-haspopup="dialog"
              className="truncate-fade min-w-0 flex-1 text-left text-caption text-fg-muted hover:text-fg focus-visible:text-fg"
              title="Read the full entry"
            >
              {e.title}
            </button>
            <Sheet
              open={open}
              onClose={() => setOpen(false)}
              title={`Journal · ${e.entry_date}`}
              subtitle={[e.mood, e.energy].filter(Boolean).join(' · ') || undefined}
            >
              <p>{e.title}</p>
            </Sheet>
          </>
        ) : (
          <span className="min-w-0 flex-1 text-caption text-fg-muted">{e.title}</span>
        ))}
    </li>
  );
}
