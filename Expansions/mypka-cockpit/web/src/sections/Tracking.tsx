// Tracking.tsx — the Tracking panel: habit-streak heatmaps + photo-nutrition
// gallery. Reads /api/tracking (read-only). Two collapsible sub-sections that
// reuse the cockpit's Section / Card primitives and GL-003 tokens, so it sits in
// the dashboard exactly like Body / Mind / Trends / Planned.
//
// Both halves are framed gently on purpose:
//   • Habits — gaps are neutral, the streak copy says "back at it", not "broken".
//   • Food — no numbers/scores; context tags are descriptive, never judged.
import { Flame, Repeat2, Camera } from 'lucide-react';
import { Card, Section } from '../components/ui';
import { HabitHeatmap } from '../components/HabitHeatmap';
import { FoodGallery } from '../components/FoodGallery';
import { navigate } from '../lib/router';
import type { HabitTracking, FoodLog } from '../lib/trackingTypes';

// A calm one-liner about where the streak stands. NEVER scolds a gap.
function streakLine(h: HabitTracking): string {
  const s = h.streak;
  if (!s) return 'No check-ins committed yet';
  if (s.current > 0) {
    const unit = s.current === 1 ? 'day' : 'days';
    return `${s.current} ${unit} running`;
  }
  // current === 0 → most recent committed log was a miss. Frame it forward.
  if (s.daysSinceLast != null && s.daysSinceLast <= 1) return 'Ready to pick it back up';
  return 'Pick it back up whenever';
}

function HabitStreakCard({ habit }: { habit: HabitTracking }) {
  const s = habit.streak;
  const hasCells = habit.cells.length > 0;
  return (
    <Card as="article" className="flex flex-col gap-sm">
      <div className="flex items-baseline justify-between gap-sm">
        <button
          type="button"
          onClick={() => navigate({ name: 'note', type: 'habits', slug: habit.slug })}
          className="text-left text-body font-[520] text-fg hover:text-marker-text focus-visible:text-marker-text"
          title="Open habit"
        >
          {habit.name}
        </button>
        {/* The streak count — brass when alive, muted when at rest. No red, ever. */}
        <span
          className={`inline-flex items-center gap-xs rounded-full px-sm py-[3px] text-caption font-[500] ${
            s && s.current > 0 ? 'bg-[var(--accent-marker-soft)] text-marker-text' : 'bg-surface-2 text-fg-muted'
          }`}
        >
          <Flame size={13} strokeWidth={1.5} aria-hidden="true" />
          {streakLine(habit)}
        </span>
      </div>

      {hasCells ? (
        <HabitHeatmap cells={habit.cells} />
      ) : (
        <p className="text-caption text-fg-subtle">No logs yet — the calendar fills in as you check in.</p>
      )}

      {s && (
        <div className="flex flex-wrap items-center gap-md text-caption text-fg-subtle">
          <span>{s.totalDone} done</span>
          {s.lastDate && <span className="font-mono">last · {s.lastDate}</span>}
        </div>
      )}
    </Card>
  );
}

export function Tracking({
  habits,
  food,
  habitsOpen,
  onToggleHabits,
  foodOpen,
  onToggleFood,
}: {
  habits: HabitTracking[];
  food: FoodLog[];
  habitsOpen: boolean;
  onToggleHabits: () => void;
  foodOpen: boolean;
  onToggleFood: () => void;
}) {
  const activeStreaks = habits.filter((h) => h.streak && h.streak.current > 0).length;
  const habitSummary =
    habits.length === 0
      ? 'no habits tracked'
      : `${habits.length} habit${habits.length === 1 ? '' : 's'} · ${activeStreaks} running`;

  const withPhoto = food.filter((f) => f.photoPath).length;
  const foodSummary =
    food.length === 0
      ? 'no meals yet'
      : `${food.length} meal${food.length === 1 ? '' : 's'} · ${withPhoto} with photo`;

  return (
    <>
      <Section
        id="habits"
        icon={<Repeat2 size={22} strokeWidth={1.5} />}
        title="Habit streaks"
        hint="check-ins · gaps shown gently"
        summary={habitSummary}
        open={habitsOpen}
        onToggle={onToggleHabits}
      >
        {habits.length === 0 ? (
          <Card>
            <p className="text-body text-fg-muted">No habits are being tracked yet.</p>
            <p className="mt-xs text-caption text-fg-subtle">
              Check-ins logged in your habit notes show up here as a calendar — done days filled,
              gaps kept soft.
            </p>
          </Card>
        ) : (
          <div className="grid gap-md lg:grid-cols-2">
            {habits.map((h) => (
              <HabitStreakCard key={h.slug} habit={h} />
            ))}
          </div>
        )}
        <p className="mt-md text-caption leading-relaxed text-fg-subtle">
          A gap is just a gap. The calendar never turns red — the only question it asks is how
          quickly you are back at it.
        </p>
      </Section>

      <Section
        id="food"
        icon={<Camera size={22} strokeWidth={1.5} />}
        title="Meals"
        hint="a photo record · nothing measured"
        summary={foodSummary}
        open={foodOpen}
        onToggle={onToggleFood}
      >
        <FoodGallery logs={food} />
        <p className="mt-md text-caption leading-relaxed text-fg-subtle">
          No calories, no scores, no judgement. Just what was on the plate, and the context around it.
        </p>
      </Section>
    </>
  );
}
