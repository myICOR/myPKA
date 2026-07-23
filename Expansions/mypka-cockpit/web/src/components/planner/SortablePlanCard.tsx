// SortablePlanCard.tsx — dnd-kit wrappers around PlanCard.
//
//   * SortableTaskCard  — a draggable task placement (in a lane) or sidebar task.
//   * MeetingAnchor     — a meeting card present in the lane's sortable list as a
//                         DISABLED item, so insertion indices around it are correct,
//                         but it itself is never draggable (it holds its time slot).
//   * MoveNextDayButton — the small per-card "shed to next day" action (README
//                         "capacity = stack length": shedding an overwhelmed lane is
//                         one motion — drag to the next day, OR this button).
//
// MOTION (Vivi 03 wired into Iris's hooks):
//   - FLIP reorder / neighbor shift (§2.5): the `transition` from useSortable is set
//     to `easeFollow` (cubic-bezier(0.22,0.61,0.36,1)) over 280ms — neighbors lead.
//     We override dnd-kit's default `ease` with that string.
//   - Pick-up lift / drop-settle / 1:1 follow live on the DragOverlay (PlannerView),
//     not here — the in-flow sortable item becomes a quiet ghost during drag.
//   - prefers-reduced-motion: the global collapse in index.css neutralises the
//     transition automatically; we additionally suppress the transition string when
//     reduced motion is set (so neighbors re-layout instantly, Vivi §6 row 2.5).

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { DraggableSyntheticListeners } from '@dnd-kit/core';
import type { ReactNode } from 'react';
import { ChevronRight, GripVertical } from 'lucide-react';
import { PlanCard } from './PlanCard';
import type { PlanCardStatus } from '../../lib/plannerTypes';
import { prefersReducedMotion } from '../../lib/plannerMotion';

// Vivi §2.5 `easeFollow`: no-overshoot decelerate; neighbors lead the gap (280ms).
const REFLOW_TRANSITION = 'transform 280ms cubic-bezier(0.22, 0.61, 0.36, 1)';

export function SortableTaskCard({
  id, title, meta, glyphSource, badge, onOpenDetail, faded, status, moveNext,
  isHighlight, onToggleHighlight, completedLocal, onToggleComplete, sourceLabel,
}: {
  id: string;                 // namespaced draggable id (source:taskId)
  title: string;
  meta?: string | null;
  glyphSource: string;        // connector id (open — SourceMark has a generic fallback)
  badge?: ReactNode;
  onOpenDetail?: () => void;  // open the card DETAIL MODAL (external link lives inside)
  faded?: boolean;
  // Iris spec 18: reconciliation status of a PLACED card (done = check + strike; stale =
  // fade-only; live = normal). Omitted for sidebar/unscheduled cards (no plan row).
  status?: PlanCardStatus;
  // When present, renders the small "→ next day" shed action on the card.
  moveNext?: { label: string; onClick: () => void } | null;
  // Iris 20 (weekly goals): teal highlight treatment + the promote Star toggle. A
  // placed weekly goal renders teal (a highlight of its day); a pinned sidebar weekly
  // goal renders teal in the Weekly Goals section. onToggleHighlight fires the write.
  isHighlight?: boolean;
  onToggleHighlight?: () => void;
  // Iris 20 §7 (complete-a-task): the planner-LOCAL completion flag + the toggle. Source-
  // done (status==='done') is derived sticky/read-only inside PlanCard; local-complete is
  // toggleable. sourceLabel feeds the sticky-source-done "reopen at {source}" tooltip.
  completedLocal?: boolean;
  onToggleComplete?: () => void;
  sourceLabel?: string;
}) {
  const {
    attributes, listeners, setNodeRef, transform, transition, isDragging,
  } = useSortable({ id });

  const reduced = prefersReducedMotion();
  const style = {
    transform: CSS.Transform.toString(transform),
    // Override dnd-kit's default `ease` with Vivi's easeFollow; drop entirely under
    // reduced motion so neighbors snap to position (no animated translate).
    transition: reduced ? undefined : (transition ? REFLOW_TRANSITION : undefined),
    // The in-flow item fades to a quiet ghost while its overlay clone is dragged
    // (Vivi §2.5 — the lifted card is the overlay; this is the placeholder).
    opacity: isDragging ? 0.4 : undefined,
  };

  // M1 (WCAG 4.1.2 nested-interactive): the card BODY carries ONLY dnd-kit's
  // `listeners` (the pointer/keyboard EVENT HANDLERS) — so a pointer-grab on the
  // whole card still lifts it (the natural kanban feel Tom wants), but the article
  // gets NO `role="button"`/`tabindex`/`aria-roledescription`. Those `attributes`
  // (the semantic drag-button role) live on the GRIP handle only, so the
  // drag-button is a leaf control, NOT a container wrapping the inner open / move-
  // next buttons. The 6px PointerSensor activation constraint (PlannerView) means a
  // click that doesn't move never lifts; inner buttons stopPropagation on
  // pointerdown so a click on them can't drag. Keyboard DnD: focus the grip (it
  // holds attributes → it's the tabbable role="button" + listeners) → Space picks
  // up → arrows move → Space drops → Esc cancels. This is dnd-kit's documented
  // handle split: listeners on the body for pointer, attributes+listeners on the
  // handle for the accessible activator.
  const bodyActivator = { ...listeners };

  return (
    <div className="relative">
      <PlanCard
        ref={setNodeRef}
        kind="task"
        title={title}
        meta={meta}
        glyphSource={glyphSource}
        badge={badge}
        onOpenDetail={onOpenDetail}
        faded={faded}
        status={status}
        isHighlight={isHighlight}
        onToggleHighlight={onToggleHighlight}
        completedLocal={completedLocal}
        onToggleComplete={onToggleComplete}
        sourceLabel={sourceLabel}
        dragging={isDragging}
        style={style}
        dragActivator={bodyActivator}
        dragHandle={<DragHandle title={title} listeners={listeners} attributes={attributes} />}
      />
      {moveNext && (
        <MoveNextDayButton label={moveNext.label} onClick={moveNext.onClick} />
      )}
    </div>
  );
}

// M1: the grip is the accessible drag activator. It carries BOTH dnd-kit's
// `listeners` (so the KEYBOARD sensor activates from it: focus → Space picks up →
// arrows move → Space drops → Esc cancels) AND dnd-kit's `attributes` (the
// `tabindex`/`aria-roledescription="sortable"`/`aria-disabled`/`role` that name this
// as the drag control). Because the grip is a LEAF <button>, putting the drag-button
// role here — rather than on the <article> that wraps the open / move-next buttons —
// keeps the card free of nested interactive controls (WCAG 4.1.2). The card body
// still drags by pointer via its own `listeners` (no role), so the kanban feel is
// preserved. We spread `attributes` first, then our own props, so our explicit
// `type="button"` / `aria-label` win over dnd-kit's generic defaults.
function DragHandle({
  title, listeners, attributes,
}: {
  title: string;
  listeners: DraggableSyntheticListeners;
  attributes: ReturnType<typeof useSortable>['attributes'];
}): ReactNode {
  return (
    <button
      {...attributes}
      type="button"
      aria-label={`Reorder ${title}`}
      className="planner-card-grip absolute left-[3px] top-[6px] inline-flex h-[20px] w-[14px] cursor-grab touch-none items-center justify-center text-fg-subtle opacity-0 transition-opacity hover:text-marker-text focus-visible:opacity-100 group-hover:opacity-100 active:cursor-grabbing"
      {...listeners}
    >
      <GripVertical size={14} strokeWidth={1.5} aria-hidden="true" />
    </button>
  );
}

// A meeting card sits in the lane's sortable list as a disabled anchor: it occupies
// an index (so tasks can drop before/between/after it) but is never itself dragged.
export function MeetingAnchor({
  id, title, meta, onOpenDetail,
}: {
  id: string;
  title: string;
  meta?: string | null;
  onOpenDetail?: () => void;  // open the meeting DETAIL MODAL
}) {
  // `disabled` makes the item non-draggable but still measured for index math.
  const { setNodeRef, transform, transition } = useSortable({ id, disabled: true });
  const reduced = prefersReducedMotion();
  const style = {
    transform: CSS.Transform.toString(transform),
    transition: reduced ? undefined : (transition ? REFLOW_TRANSITION : undefined),
  };
  return (
    <PlanCard
      ref={setNodeRef}
      kind="meeting"
      title={title}
      meta={meta}
      glyphSource="calendar"
      // Iris 11 §2 + open-Q1 (fold meeting→event): all calendar items read OXBLOOD,
      // not brass — so the Google Calendar source mark + rail/surface pick up the
      // --planner-event category hue, leaving brass purely for today/live signals.
      dataSource="event"
      onOpenDetail={onOpenDetail}
      style={style}
    />
  );
}

// The per-card "shed to next day" affordance — one motion to push an overwhelmed
// lane forward without a drag. Calm, quiet; only meaningful for placed task cards.
function MoveNextDayButton({ label, onClick }: { label: string; onClick: () => void }): ReactNode {
  return (
    <button
      type="button"
      onPointerDown={(e) => e.stopPropagation()}
      onClick={onClick}
      aria-label={label}
      title={label}
      // Iris 20 §2: the promote Star now occupies the top-right corner (right:8px,
      // ~18px wide). Shift the shed button left of it (right:30px) so the two card
      // actions sit side by side instead of stacking. Both stay hover-revealed.
      className="absolute right-[30px] top-[6px] inline-flex h-[20px] w-[20px] items-center justify-center rounded-card text-fg-subtle opacity-0 transition-opacity hover:bg-surface-3 hover:text-marker-text focus-visible:opacity-100 group-hover:opacity-100"
    >
      <ChevronRight size={14} strokeWidth={1.5} aria-hidden="true" />
    </button>
  );
}
