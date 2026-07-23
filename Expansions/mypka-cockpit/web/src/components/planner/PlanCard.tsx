// PlanCard.tsx — the universal planner card. ONE component renders BOTH a meeting
// and a task at the equal 72px box (Iris's .planner-card). The only differences:
//   - the source rail (data-source='meeting' → brass | 'task' → neutral, via ::before)
//   - the glyph + time/meta line
//   - draggability (meetings are fixed anchors; tasks drag)
//
// Visual styling is 100% Iris's .planner-card / -title / -meta classes (no inline
// hex/px). Motion (lift/drop/dragging) is wired by the sortable wrappers via the
// [data-dragging] hook Iris left; this component only renders the static card.
//
// Accessibility: the card is an <article> with a meaningful aria-label; the title
// is a real <button> only for tasks/meetings that can deep-link (read navigation).

import { forwardRef, useRef } from 'react';
import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';
import { CheckCircle2, Circle, Star } from 'lucide-react';
import type { CardKind, GlyphSource, PlanCardStatus } from '../../lib/plannerTypes';
import { SourceMark, sourceLabelFor } from './SourceMark';

export interface PlanCardProps {
  kind: CardKind;
  title: string;
  // meetings: "10:00–11:00"; tasks: a due/priority meta line or null
  meta?: string | null;
  // The connector id (open string — 'calendar' for events, any active task
  // connector id for tasks). Drives the source logo (the SourceMark that leads
  // the meta row, with a generic fallback for unknown ids) and, for events, the
  // oxblood mark tint.
  glyphSource: GlyphSource;
  // Iris 11 §2: the rail/surface treatment. 'meeting' = brass, 'task' = neutral,
  // 'event' = oxblood category hue. When omitted, derived from `kind` (task/meeting).
  // Calendar events pass 'event' explicitly so they read oxblood, not brass.
  dataSource?: 'meeting' | 'task' | 'event';
  badge?: ReactNode;            // StatusChip (e.g. "important") for high-priority tasks
  // Open the DETAIL MODAL for this card. Fired on a plain click of the card BODY
  // (NOT a drag — see the pointer-movement guard below) and on Enter when focused.
  // The external "open in source" link now lives INSIDE that modal, so the card
  // body itself stays the single click-target + drag-activator (no nested control).
  onOpenDetail?: () => void;
  dragging?: boolean;          // toggles Iris's [data-dragging] lifted look
  // The keyboard-accessible drag handle (a GripVertical button carrying dnd-kit's
  // KEYBOARD activator). Rendered as the FIRST focusable element so keyboard tab
  // order is grip → title → move-next. Pointer dragging happens on the card BODY
  // (see dragActivator) — the grip is the keyboard affordance, not the only one.
  dragHandle?: ReactNode;
  // dnd-kit pointer drag activator (attributes + listeners) spread onto the card
  // ARTICLE so the whole card body is the natural grab target (the kanban feel).
  // The inner title-open / move-next buttons stopPropagation on pointerdown so a
  // click on them never starts a drag. Pure pointer dragging — keyboard DnD stays
  // on the focusable grip handle so we don't nest a drag-role on a container with
  // interactive children (WCAG 4.1.2 / H2 stays intact: the article has no role).
  dragActivator?: HTMLAttributes<HTMLElement>;
  style?: CSSProperties;        // dnd-kit transform/transition
  className?: string;
  // A muted treatment for reconciled 'done'/'stale' cards (calm, never red).
  faded?: boolean;
  // Iris spec 18 (Planned/Done state): the reconciliation status of a PLACED task card.
  // 'live' = normal; 'done' = CheckCircle2 lead + title strikethrough + fade; 'stale' =
  // fade-only (no check, no strike). Omitted for meetings, the overlay clone, and
  // sidebar (unscheduled) cards, which have no plan-row status. Neutral, no green.
  status?: PlanCardStatus;
  // Iris 20 §1/§2 (weekly goals): when true, the card wears the teal HIGHLIGHT
  // treatment (data-highlight → teal rail + tint + filled star). For a PLACED card this
  // IS a highlight-of-the-day; for a pinned SIDEBAR weekly goal it is the teal pin look.
  isHighlight?: boolean;
  // The promote-to-highlight Star toggle (Iris 20 §2). Present ⇒ the top-right star
  // button renders (every task card, sidebar AND placed). Absent ⇒ no star (meetings,
  // the overlay clone). Fires the POST/DELETE weekly-goal write via PlannerView.
  onToggleHighlight?: () => void;
  // Iris 20 §7 (complete-a-task): the leading round complete check on the title row.
  // Present ⇒ the interactive check renders (placed task cards only). Absent ⇒ no check
  // (meetings, sidebar/unscheduled cards, the overlay clone). Fires the POST
  // /api/planner/complete write via PlannerView (optimistic).
  onToggleComplete?: () => void;
  // Iris 20 §7: the planner-LOCAL completion flag (the toggleable kind). Combined with
  // `status==='done'` (the SOURCE-done kind) it yields the done state. Source-done is
  // sticky/read-only; local-complete toggles back to incomplete.
  completedLocal?: boolean;
  // The source tool label for the sticky-source-done tooltip ("reopen at Todoist").
  sourceLabel?: string;
}

// data-source maps to Iris's RAIL: meeting=brass, task=neutral, event=oxblood.
// Default fallback from kind; callers pass `dataSource='event'` for calendar events
// (Iris 11 §2 — events read oxblood, distinct from brass meetings & neutral tasks).
function railSource(kind: CardKind): 'meeting' | 'task' {
  return kind === 'meeting' ? 'meeting' : 'task';
}

// A click that moves more than this many px between pointerdown and click is treated
// as the tail of a drag, never an open. Belt-and-suspenders ON TOP of dnd-kit's own
// post-drag click suppression (PointerSensor distance:6) and the inner buttons'
// stopPropagation — so the modal can NEVER open as a side effect of a drag.
const CLICK_MOVE_TOLERANCE = 6;

export const PlanCard = forwardRef<HTMLElement, PlanCardProps>(function PlanCard(
  { kind, title, meta, glyphSource, dataSource, badge, onOpenDetail, dragging, dragHandle, dragActivator, style, className = '', faded, status, isHighlight, onToggleHighlight, onToggleComplete, completedLocal, sourceLabel },
  ref,
) {
  const source = dataSource ?? railSource(kind);
  const openable = !!onOpenDetail;
  // Iris 20 §7: SOURCE-done (the source closed it upstream) is sticky + read-only — the
  // planner never re-opens a source task. LOCAL-complete (the user ticked it here) is
  // toggleable. A card is DONE when EITHER holds. The spec-18 done treatment (title
  // strikethrough + mute) keys off the combined flag.
  const sourceDone = status === 'done';
  const isDone = sourceDone || !!completedLocal;
  const ariaLabel = `${kind === 'meeting' ? 'Meeting' : 'Task'}: ${title}${meta ? `, ${meta}` : ''}`;
  // Only the card body is a pointer-drag activator (cursor:grab) when there's an
  // activator AND a keyboard grip — i.e. for draggable task cards. Meeting anchors
  // and the static overlay clone get neither, so they don't claim a grab cursor.
  const isDraggable = !!dragActivator;

  // Pointer-movement guard on the BODY: remember where the pointer went down; if it
  // moved past the tolerance by click time, it was a drag — swallow the open. This is
  // belt-and-suspenders ON TOP of dnd-kit's post-drag click suppression (distance:6).
  const downPos = useRef<{ x: number; y: number } | null>(null);
  const handleBodyPointerDown = (e: React.PointerEvent) => {
    downPos.current = { x: e.clientX, y: e.clientY };
  };
  const handleBodyClick = (e: React.MouseEvent) => {
    if (!onOpenDetail) return;
    const start = downPos.current;
    downPos.current = null;
    if (start && Math.hypot(e.clientX - start.x, e.clientY - start.y) > CLICK_MOVE_TOLERANCE) {
      return; // tail of a drag — not an open
    }
    onOpenDetail();
  };

  // WCAG 4.1.2 (preserved from the drag rounds): the <article> stays a plain container
  // with NO role/tabindex — so the grip <button> (keyboard drag activator, Space) and
  // the move-next <button> are NOT nested inside an interactive ancestor. The card BODY
  // still opens the detail modal on a plain POINTER click (a bare onClick on a non-role
  // element is not an interactive role — it adds no nesting), while the KEYBOARD open
  // affordance is the focusable title <button> below (Enter/Space activate it natively;
  // it stopPropagation on pointerdown so it never starts a drag). Tab order stays
  // grip → title → move-next. Space on the grip = pick-up; Enter on the title = open.
  return (
    <article
      ref={ref}
      className={`planner-card ${dragHandle ? 'planner-card--draggable' : ''} ${isDraggable ? 'planner-card--grab' : ''} ${openable ? 'planner-card--openable' : ''} ${faded ? 'opacity-60' : ''} ${className}`}
      data-source={source}
      data-status={status}
      // Iris 20 §1: the teal highlight treatment (rail + tint + border + star tint) is
      // driven entirely by this attr in cockpit.css. Orthogonal to data-source: it wins
      // the rail by cascade (the highlight ::before rule is authored after the source ones).
      data-highlight={isHighlight ? 'true' : undefined}
      data-dragging={dragging ? 'true' : undefined}
      aria-label={ariaLabel}
      style={style}
      {...dragActivator}
      onPointerDownCapture={openable ? handleBodyPointerDown : undefined}
      onClick={openable ? handleBodyClick : undefined}
    >
      {dragHandle}
      {/* Iris 20 §2: promote-to-highlight Star (top-right card action). Idle = outline,
          hover-revealed, teal on its own hover; active = filled teal, always shown (a
          status mark). aria-pressed + a state-specific label. stopPropagation on
          pointerdown so a grab on the star never starts a drag, and on click so it never
          opens the detail modal. The teal hue + the rail are the one "this is a highlight"
          signal; the star SHAPE carries the meaning when the hue can't (colour-blind). */}
      {onToggleHighlight && (
        <button
          type="button"
          className="planner-card-star"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onToggleHighlight(); }}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') e.stopPropagation(); }}
          aria-pressed={!!isHighlight}
          aria-label={isHighlight ? 'Remove highlight' : 'Mark as highlight of the day'}
          title={isHighlight ? 'Remove highlight' : 'Mark as highlight'}
        >
          <Star size={14} strokeWidth={1.75} fill={isHighlight ? 'currentColor' : 'none'} aria-hidden="true" />
        </button>
      )}
      <div className="planner-card-meta flex items-center gap-xs">
        {/* Iris 11 §1: the source-tool logo leads the meta row (replaces the generic
            Lucide category glyph). Monochrome --fg-muted; oxblood on event cards via
            the card's data-source CSS scope. Vera LOW / WCAG 1.1.1: the mark carries an
            aria-label of the source tool name so the SVG is announced, not silent. */}
        <SourceMark source={glyphSource} label={sourceLabel ?? sourceLabelFor(glyphSource)} />
        {meta && <span className="tabular-nums">{meta}</span>}
        {badge}
      </div>
      {/* Iris 20 §7 — the title ROW: a leading interactive complete check + the title.
          The check sits opposite the top-right Star (don't crowd the SourceMark logo or
          move-next). `items-start` keeps the 20px check aligned to the title's first
          line when the title wraps. */}
      <div className="planner-card-titlerow flex items-start gap-xs">
        {onToggleComplete && (
          /* The interactive complete check. Circle (incomplete, --fg-subtle) → filled
             CheckCircle2 (complete, --fg-muted, NO green), --planner-card-check-size
             (20px). Clicking toggles complete via POST /api/planner/complete (optimistic;
             PlannerView shows the calm read-only hint on 503). stopPropagation on
             pointerdown (never starts a drag) AND on click (never opens the modal). The
             old decorative meta CheckCircle2 collapses into THIS one interactive control.
             SOURCE-done ⇒ filled + DISABLED with a "reopen at {source}" tooltip
             (sticky/read-only); LOCAL-complete ⇒ toggles back to incomplete. */
          <button
            type="button"
            className="planner-card-check"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              if (sourceDone) return; // sticky: the planner never re-opens a source task
              onToggleComplete();
            }}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') e.stopPropagation(); }}
            role="checkbox"
            aria-checked={isDone}
            disabled={sourceDone}
            aria-disabled={sourceDone || undefined}
            aria-label={
              sourceDone
                ? `Completed at ${sourceLabel ?? 'source'} — reopen it there`
                : isDone
                  ? 'Mark as not complete'
                  : 'Mark as complete'
            }
            title={
              sourceDone
                ? `Completed at ${sourceLabel ?? 'source'}. Reopen it at ${sourceLabel ?? 'the source'}.`
                : isDone
                  ? 'Mark as not complete'
                  : 'Mark as complete'
            }
          >
            {isDone
              ? <CheckCircle2 size={20} strokeWidth={1.5} aria-hidden="true" />
              : <Circle size={20} strokeWidth={1.5} aria-hidden="true" />}
          </button>
        )}
      {openable ? (
        <button
          type="button"
          // Stop pointerdown from starting a drag when the user means to open via the
          // title (keyboard focuses here; pointer users mostly click the body).
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onOpenDetail?.(); }}
          // Vera HIGH / WCAG 2.1.1 keyboard parity: the card BODY spreads dnd-kit's
          // pointer+keyboard `listeners` (dragActivator) onto the <article>, and that
          // ancestor onKeyDown swallows the focused button's native Enter→click
          // synthesis (keydown/keyup fire but no `click`, so the modal never opened).
          // We restore Enter-to-open explicitly here, stopPropagation so the key never
          // reaches the article's dnd-kit listener. The GRIP owns Space for drag
          // pickup; the title is NOT a drag activator, so Space here safely also opens
          // (and preventDefault stops the page from scrolling on Space). Enter is the
          // hard requirement; Space is the harmless bonus the spec permits.
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
              e.preventDefault();
              e.stopPropagation();
              onOpenDetail?.();
            }
          }}
          className={`planner-card-title truncate-fade block min-w-0 flex-1 text-left transition-colors hover:text-marker-text focus-visible:text-marker-text ${isDone ? 'line-through' : ''}`}
          title={title}
          aria-label={`Open details for ${title}`}
        >
          {title}
        </button>
      ) : (
        // LOW: full-text hover tooltip for the truncated title.
        <span className={`planner-card-title truncate-fade block min-w-0 flex-1 ${isDone ? 'line-through' : ''}`} title={title}>{title}</span>
      )}
      </div>
    </article>
  );
});
