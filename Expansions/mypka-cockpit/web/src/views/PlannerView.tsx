// PlannerView.tsx — the cockpit day-planner (replaces ActionsView at #/actions).
//
// A simplified-but-improved Sunsama: a weekly kanban of EQUAL cards (meetings +
// tasks), each day split AM/PM, with a right sidebar of unscheduled tasks (from
// EVERY active task connector — the planner is tool-blind, like the backend)
// you drag in to SEQUENCE relative to meetings. Two AM/PM PURE
// COUNTDOWN timers per day (no capacity meter — the stack length is the signal).
// A gear opens work-hours settings.
//
// ARCHITECTURE (Felix 02): PlannerView → DndContext → WeekBoard (DayColumn × AM/PM
// HalfLane) + UnscheduledSidebar + SettingsSheet. One PlanCard for BOTH kinds.
//
// STATE (no new lib): useReducer (plan placements, optimistic) + useFetch (reads).
//   reads:  GET /api/cockpit/calendar?week=  (NormalizedEvent[])
//           GET /api/cockpit/sources         (TOOL-BLIND: one group per ACTIVE task
//                                             connector, NormalizedTask items — group
//                                             order + labels come from the response)
//           GET /api/planner/week?week_start= (placements + settings + reconciliation)
//   writes: POST /api/planner/assign | reorder · DELETE assign · PUT settings
//           (behind PLAN_WRITE_ENABLED → 503 disabled handled gracefully)
//
// UNIFIED-SPACE DROP (2026-06-23): a lane is ONE comparable position space spanning
// events (deterministic, time-derived, read-only anchors — never plan rows) AND tasks
// (stored REAL position in the same scale). A task dropped into a lane resolves to an
// insertion index in the UNIFIED ordered list; we compute the target numeric position
// (midpoint of the unified neighbours) and send THAT. This is what lets a task sit
// ABOVE an event and persist there — the old task-only before/after id scheme could
// not name an event as a neighbour, so a task could never order before an event.
//
// CALM NOT-CONNECTED POSTURE (preserved): when calendar isn't connected the board
// degrades to tasks-only (lanes still work); when a task source isn't connected the
// sidebar shows that source's calm connect-hint, never an error.

import { memo, useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  DndContext, DragOverlay, PointerSensor, KeyboardSensor, useSensor, useSensors,
  pointerWithin, closestCenter, MeasuringStrategy,
  type CollisionDetection,
  type DragStartEvent, type DragEndEvent, type DragOverEvent, type UniqueIdentifier,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown, Settings, Focus } from 'lucide-react';
import { useFetch } from '../lib/useCockpit';
import { StatusChip } from '../components/ui';
import type {
  CalendarResponse, NormalizedEvent, NormalizedTask, PlannerWeekResponse,
  PlannerSettings, Half, Weekday, SourceGroup, SourcesResponse,
} from '../lib/plannerTypes';
import { taskKey, eventKey, parseTaskKey, isEventKey } from '../lib/plannerTypes';
import {
  planReducer, emptyPlanState, laneItems, findPlacement, unifiedPositionAt,
  type PlanItem,
} from '../lib/plannerReducer';
import {
  mondayOf, todayInTz, weekDays, weekdayOf, weekDaysLabelFor, WEEKDAY_FULL, WEEKDAY_LABELS,
  isWorkday, addDays, currentHalf, monthDayLabel, dayRelation,
  hoursForWeekday, tzMinutesOfDay, hhmmToMinutes,
  remainingWorkMinutes, timerState, formatRemaining,
  eventPosition, EVENT_FLOOR,
} from '../lib/plannerLogic';
import { usePlannerSettings } from '../lib/usePlannerSettings';
import { usePersistedBool, useGroupCollapsed, SIDEBAR_COLLAPSED_KEY, SIDEBAR_GROUPED_KEY, AM_COLLAPSED_KEY, FOCUS_MODE_KEY } from '../lib/useSidebarPrefs';
import { assignPlacement, reorderPlacement, unassignPlacement, setWeeklyGoal, unsetWeeklyGoal, completePlacement, type WriteOutcome } from '../lib/plannerApi';
import { dropAnimationFor, prefersReducedMotion } from '../lib/plannerMotion';
import { buildAnnouncements } from '../lib/plannerAnnouncements';
import { PlanCard } from '../components/planner/PlanCard';
import { SortableTaskCard, MeetingAnchor } from '../components/planner/SortablePlanCard';
import { HalfLane, parseLaneDroppableId, type LaneRenderItem } from '../components/planner/HalfLane';
import { UnscheduledSidebar, SIDEBAR_DROPPABLE_ID, type SidebarGroup } from '../components/planner/UnscheduledSidebar';
import { SettingsSheet } from '../components/planner/SettingsSheet';
import { CardDetailModal, type CardDetail } from '../components/planner/CardDetailModal';

// A meeting's time chip, "10:00–11:00" in display tz, or "all day".
function eventTimeLabel(e: NormalizedEvent, tz: string): string {
  if (e.allDay) return 'all day';
  const fmt = (iso: string) =>
    new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso));
  return `${fmt(e.start)}–${fmt(e.end)}`;
}

// A task's calm meta line: due bucket (never an alarm) — same tone as ActionsView.
function taskMetaLabel(t: NormalizedTask): string | null {
  if (!t.due) return null;
  if (t.dueBucket === 'overdue') return `overdue · ${t.due}`;
  if (t.dueBucket === 'today') return 'due today';
  return t.due;
}

// H1 collision: resolve the droppable under the POINTER, not under the dragged
// card's geometric center. Bare closestCenter ranked every lane + card by distance
// from the OVERLAY's center; a wide card grabbed off-center put that center over a
// neighbouring lane even when the pointer sat squarely inside the intended lane —
// so a drop "inside Wed AM" persisted into Thu PM (off by one column + wrong half).
// pointerWithin returns only droppables the pointer is literally inside, so the lane
// the user sees under their cursor is the lane that resolves. We fall back to
// closestCenter ONLY when the pointer is over no droppable — chiefly keyboard DnD,
// which has no pointer coordinate (the KeyboardSensor drives selection by rect, so
// closestCenter is correct there) and the rare pointer-in-the-gutter frame.
const plannerCollision: CollisionDetection = (args) => {
  const byPointer = pointerWithin(args);
  if (byPointer.length > 0) return byPointer;
  return closestCenter(args);
};

export function PlannerView() {
  const topRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { topRef.current?.scrollIntoView({ block: 'start' }); }, []);
  // Iris 16 §8: the progress rail's height must MATCH THE BOARD CONTENT (not the viewport).
  // The board is a height:100% scroll container at ≥1501px, so its visible box is taller
  // than its four packed (align-content:start) content rows. We hand the rail a ref to the
  // board so it can size itself to the board's rendered content height (scrollHeight),
  // making top=work-hours start / bottom=work-hours end map onto the real content span.
  const boardRef = useRef<HTMLDivElement | null>(null);

  // ---- week state (the active Monday) --------------------------------------
  const [weekStart, setWeekStart] = useState(() => mondayOf(todayInTz()));

  // ---- reads ----------------------------------------------------------------
  const { data: cal } = useFetch<CalendarResponse>(`/api/cockpit/calendar?week=${weekStart}`);
  // ONE tool-blind task read: a group per ACTIVE task connector (0..N of anything).
  const { data: sourcesData } = useFetch<SourcesResponse>('/api/cockpit/sources');
  const { data: week } = useFetch<PlannerWeekResponse>(`/api/planner/week?week_start=${weekStart}`);

  // ---- settings (server → localStorage fallback) ---------------------------
  const serverSettings = week && week.ok ? week.settings : null;
  const { settings, update: updateSettings, writeDisabled: settingsWriteDisabled } =
    usePlannerSettings(serverSettings);

  // ---- plan state (optimistic reducer) -------------------------------------
  const [plan, dispatch] = useReducer(planReducer, undefined, emptyPlanState);
  useEffect(() => {
    if (week && week.ok) dispatch({ type: 'hydrate', days: week.days });
  }, [week]);

  // ---- weekly-goal membership (Migration 003) ------------------------------
  // ONE source of truth for "is this task a weekly goal", keyed by the namespaced task
  // key (source:id), covering BOTH placed cards AND unplaced sidebar tasks. Seeded from
  // the server's full weeklyGoals[] set on each week read; toggled optimistically by the
  // Star button. A placed weekly goal IS a highlight of its day (derived: placed ⟹ in a
  // lane); an unplaced one stays in the pinned Weekly Goals sidebar pool.
  const [weeklyGoalKeys, setWeeklyGoalKeys] = useState<Set<string>>(() => new Set());
  useEffect(() => {
    if (week && week.ok) {
      const next = new Set<string>();
      for (const g of week.weeklyGoals ?? []) next.add(taskKey(g.source, g.external_task_id));
      setWeeklyGoalKeys(next);
    }
  }, [week]);
  const isWeeklyGoalKey = useCallback((key: string) => weeklyGoalKeys.has(key), [weeklyGoalKeys]);

  // A calm, non-alarm status line (replaces a toast; the codebase uses inline
  // calm messages, never window.alert). Cleared on the next successful action.
  const [notice, setNotice] = useState<string | null>(null);
  const [writeDormant, setWriteDormant] = useState(false);

  // ---- minute tick for the timers (one interval for the whole board) -------
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const msToNextMinute = 60_000 - (Date.now() % 60_000);
    let interval: number | undefined;
    const timeout = window.setTimeout(() => {
      setNow(new Date());
      interval = window.setInterval(() => setNow(new Date()), 60_000);
    }, msToNextMinute);
    return () => { window.clearTimeout(timeout); if (interval) window.clearInterval(interval); };
  }, []);

  // ---- background refetch on window focus (events shift, tasks complete) ----
  // useFetch re-fetches on url change; we nudge it by re-pinning the same week on
  // focus via a key bump. Simpler: re-read by toggling weekStart to itself is a
  // no-op for useFetch (same url), so we instead rely on the natural refetch when
  // the user navigates. (A periodic poll is out of scope for v1 calm posture.)

  // ---- derived: events by day/half, source-agnostic ------------------------
  const tz = settings.timezone || 'Europe/Berlin';
  const events = useMemo<NormalizedEvent[]>(
    // Defend the modal's body section against a transitional/degraded payload that
    // predates the `description` field (server now sends it; '' when none).
    () => (cal && cal.ok ? cal.items.map((e) => ({ ...e, description: e.description ?? '' })) : []),
    [cal],
  );
  // H3: THREE distinct calendar states — never let a feed that is merely in-flight
  // read as "not connected." `useFetch` holds `data: null` while the request is
  // pending, so `cal === null` is the LOADING window (render nothing — no warning).
  // `cal.ok` is CONNECTED. Only a settled non-ok response (`cal !== null && !cal.ok`)
  // is genuinely NOT connected — the ONLY state allowed to show the warning. The
  // regression Tom saw was the warning flashing on every empty lane during the ~1s
  // fetch window; gating on a SETTLED non-ok response removes it entirely while a
  // valid feed (ok:true, 6 events) is configured.
  const calendarStatus: 'loading' | 'connected' | 'disconnected' =
    cal === null ? 'loading' : cal.ok ? 'connected' : 'disconnected';

  // The response's source groups, in RESPONSE ORDER (the one ordering authority —
  // grouping, labels, and notices are all data-driven over this array).
  const sourceGroups = useMemo<SourceGroup[]>(
    () => (sourcesData ? sourcesData.sources : []),
    [sourcesData],
  );
  // Human label per source id, from the response. Fallback = the id itself, so an
  // unknown/transitional source never renders blank.
  const labelForSource = useCallback(
    (source: string): string =>
      sourceGroups.find((g) => g.source === source)?.label ?? source,
    [sourceGroups],
  );

  const allTasks = useMemo<NormalizedTask[]>(
    () => sourceGroups.flatMap((g) => g.items),
    [sourceGroups],
  );
  // Fast lookup of a task by its namespaced key.
  const taskByKey = useMemo(() => {
    const m = new Map<string, NormalizedTask>();
    for (const t of allTasks) m.set(taskKey(t.source, t.id), t);
    return m;
  }, [allTasks]);
  const eventByKey = useMemo(() => {
    const m = new Map<string, NormalizedEvent>();
    for (const e of events) m.set(eventKey(e.uid), e);
    return m;
  }, [events]);

  // Placed task keys (so the sidebar can exclude them).
  const placedKeys = useMemo(() => {
    const s = new Set<string>();
    for (const it of plan.items) s.add(taskKey(it.source, it.externalTaskId));
    return s;
  }, [plan.items]);

  // Unscheduled = tasks not currently placed anywhere.
  const unscheduled = useMemo(
    () => allTasks.filter((t) => !placedKeys.has(taskKey(t.source, t.id))),
    [allTasks, placedKeys],
  );

  // Iris 20 §1/§4: split the unscheduled pool into the PINNED weekly goals (unplaced +
  // marked) and the NORMAL remainder. The pinned set renders teal in the "Weekly Goals"
  // section at the TOP of the sidebar; the rest renders in the usual flat/grouped list.
  // (Placed weekly goals are NOT here — they live on their day as highlights.)
  const pinnedGoals = useMemo(
    () => unscheduled.filter((t) => weeklyGoalKeys.has(taskKey(t.source, t.id))),
    [unscheduled, weeklyGoalKeys],
  );
  const normalUnscheduled = useMemo(
    () => unscheduled.filter((t) => !weeklyGoalKeys.has(taskKey(t.source, t.id))),
    [unscheduled, weeklyGoalKeys],
  );

  // Iris 20 §5 (Tom 2026-06-03): the pinned Weekly Goals section now lists the FULL
  // roster — the unscheduled pool (above) AND the goals already placed on a day. A
  // placed goal already exists on the board as a draggable highlight card with the same
  // dnd-kit id, so it must render here as a STATIC ledger row OUTSIDE the SortableContext
  // (re-adding the id to the sidebar sortable list would create a DUPLICATE dnd-kit id
  // and break drag). We derive each placed goal's {weekday, half} from its plan placement
  // (cross-referencing weeklyGoalKeys against plan.items) so the row can show its day
  // badge ("Wed · PM"). Title comes from the source task (taskByKey); if the task isn't
  // currently loaded (a stale source blip) we fall back to the placement's id, never crash.
  const placedGoals = useMemo(() => {
    const rows: { key: string; title: string; weekday: Weekday; half: Half }[] = [];
    for (const it of plan.items) {
      const key = taskKey(it.source, it.externalTaskId);
      if (!weeklyGoalKeys.has(key)) continue;
      const t = taskByKey.get(key);
      rows.push({
        key,
        title: t?.title ?? it.externalTaskId,
        weekday: it.weekday,
        half: it.half,
      });
    }
    // Stable order: by day, then AM before PM, then title — so the ledger scans calmly.
    rows.sort((a, b) =>
      a.weekday - b.weekday
      || (a.half === b.half ? 0 : a.half === 'AM' ? -1 : 1)
      || a.title.localeCompare(b.title));
    return rows;
  }, [plan.items, weeklyGoalKeys, taskByKey]);

  // The visible columns: workweek (Mon–Fri) always shown; Sat/Sun only when the
  // user has opted them in as workdays (D2 — workweek default, weekend opt-in).
  const days = useMemo(() => weekDays(weekStart), [weekStart]);
  const visibleDays = useMemo(
    () => days.filter((d) => {
      const wd = weekdayOf(d);
      return wd <= 4 || isWorkday(settings, wd);
    }),
    [days, settings],
  );

  // Meetings for a given day+half (sorted by start; allDay handled as a header band
  // — for v1 we route allDay meetings into the AM lane as a calm top anchor).
  const meetingsFor = (day: string, half: Half): NormalizedEvent[] =>
    events
      .filter((e) => e.day === day && (e.allDay ? half === 'AM' : e.half === half))
      .sort((a, b) => (a.allDay === b.allDay ? a.start.localeCompare(b.start) : (a.allDay ? -1 : 1)));

  // The UNIFIED ordered list for one lane (2026-06-23): events and tasks merged into
  // ONE position-sorted sequence. Each entry carries its sortId, its unified-space
  // position (event = time-derived via eventPosition; task = stored `position`), and
  // whether it is an event. This is THE single ordering authority — laneSortIds, the
  // render merge, and resolveDrop all derive from it, so a task ordered ABOVE an event
  // shows, persists, and re-reads identically. Stable sort by position, then events
  // before tasks on an exact tie (an all-day event at -1 always leads).
  function laneUnified(
    weekday: Weekday, half: Half, day: string,
  ): { sortId: string; position: number; isEvent: boolean }[] {
    const entries = [
      ...meetingsFor(day, half).map((e) => ({
        sortId: eventKey(e.uid), position: eventPosition(e, tz), isEvent: true,
      })),
      ...laneItems(plan, weekday, half).map((it) => ({
        sortId: taskKey(it.source, it.externalTaskId), position: it.position, isEvent: false,
      })),
    ];
    return entries.sort((a, b) =>
      a.position - b.position || (a.isEvent === b.isEvent ? 0 : a.isEvent ? -1 : 1));
  }

  // The ordered sortable id list for one lane (events + tasks interleaved by the
  // unified position space). dnd-kit's SortableContext consumes this verbatim.
  function laneSortIds(weekday: Weekday, half: Half, day: string): string[] {
    return laneUnified(weekday, half, day).map((x) => x.sortId);
  }

  // ---- DnD sensors ----------------------------------------------------------
  // Pointer with a 6px activation distance (Vivi §1.1) so a click-to-open never
  // accidentally lifts. Keyboard sensor for full keyboard DnD (a11y, contract).
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);
  // The lane currently under the pointer (drives Iris's [data-drop-active]).
  const [overLane, setOverLane] = useState<string | null>(null);
  // The raw over-id (card or lane droppable) — drives the live drop-line index (M1).
  const [overId, setOverId] = useState<UniqueIdentifier | null>(null);
  const reduced = prefersReducedMotion();

  // ---- announcements: speak SEMANTIC position, not raw indices --------------
  const titleOf = (id: UniqueIdentifier): string => {
    const key = String(id);
    if (isEventKey(key)) return eventByKey.get(key)?.title ?? 'meeting';
    return taskByKey.get(key)?.title ?? 'task';
  };

  // ---- resolveDrop: THE single source of truth for "where will this land" ----
  // Both onDragEnd (persistence: the unified `position`) AND positionPhrase/the
  // announcer (spoken ordinal + neighbour titles) call this, so the SPOKEN slot can
  // never disagree with the PERSISTED slot (H1). It derives ONE insertion index in
  // the UNIFIED lane list (events + tasks), then turns that into a single numeric
  // `position` in the unified space — the only thing persisted now.
  //
  // insertFull = the slot in the unified ordered list (events + tasks) where the card
  //              lands (drives the spoken ordinal + neighbour titles AND the drop-line).
  // position   = the unified-space target the client sends to the server. It is the
  //              midpoint of the unified neighbour positions straddling insertFull, so
  //              a task dropped ABOVE an event lands BELOW that event's time-position
  //              and persists there (the old task-only collapse is GONE — that was the
  //              bug). insertFull and position describe the SAME slot.
  function resolveDrop(
    activeKey: UniqueIdentifier, overId: UniqueIdentifier | null,
  ): {
    lane: { weekday: Weekday; half: Half; day: string } | null;
    insertFull: number;
    position: number;
    beforeTitle: string | null;
    afterTitle: string | null;
    dayName: string;
    halfWord: string;
  } | null {
    if (!overId) return null;
    const lane = resolveLane(String(overId));
    if (!lane) return { lane: null, insertFull: 0, position: 0, beforeTitle: null, afterTitle: null, dayName: '', halfWord: '' };
    const { weekday, half, day } = lane;
    const activeStr = String(activeKey);

    // The FULL ordered lane (events@time-pos + tasks@stored-pos), self INCLUDED —
    // needed to know whether the active card is being dragged UP or DOWN relative to
    // the over-card (the direction dnd-kit's sortable semantics require).
    const fullWithSelf = laneUnified(weekday, half, day);
    const activeOrigIdx = fullWithSelf.findIndex((x) => x.sortId === activeStr);
    // The unified ordered lane, self excluded — this is the neighbour list the target
    // position is computed against (the dragged card is in flight, not a neighbour).
    const unified = fullWithSelf.filter((x) => x.sortId !== activeStr);
    const fullIds = unified.map((x) => x.sortId);
    const overKey = String(overId);
    const overIsCard = isEventKey(overKey) || taskByKey.has(overKey);
    // Over a card → resolve the insertion slot WITH DRAG DIRECTION (dnd-kit sortable
    // semantics). overOrigIdx is the over-card's slot in the FULL list (self included).
    //   - dragging DOWN  (active above over: activeOrigIdx in [0, overOrigIdx)) → land
    //     AFTER the over-card. In the self-excluded list its index is overOrigIdx-1, so
    //     "after" = (overOrigIdx-1)+1 = overOrigIdx.
    //   - dragging UP / cross-lane / new card (no self below the over-card) → land
    //     BEFORE the over-card, i.e. at its self-excluded index = indexOf(overKey).
    // Without the direction term a DOWNWARD same-lane drag always inserted BEFORE the
    // lower sibling — but the card already sat above it, so the position never changed
    // and a reorder among tasks was impossible (Tom's "within the column doesn't work").
    let insertFull: number;
    if (!overIsCard) {
      insertFull = fullIds.length; // over the bare lane → append
    } else {
      const overOrigIdx = fullWithSelf.findIndex((x) => x.sortId === overKey);
      const draggingDown = activeOrigIdx >= 0 && activeOrigIdx < overOrigIdx;
      insertFull = draggingDown ? overOrigIdx : fullIds.indexOf(overKey);
    }

    // The unified-space target position = midpoint of the neighbours around insertFull
    // (or +/-1 at an edge). This is what makes "above an event" representable: if the
    // neighbour BELOW is an event at 600 and there is no neighbour above, position is
    // 599 (event - 1), which stores the task above that event.
    const position = unifiedPositionAt(unified.map((x) => x.position), insertFull);

    // Neighbour TITLES for the spoken phrase come from the unified list around
    // insertFull (so "before Standup" can name a meeting), keeping speech rich while
    // the ordinal reflects the exact same insertion point.
    const beforeTitle = insertFull > 0 ? titleOf(fullIds[insertFull - 1]) : null;
    const afterTitle = insertFull < fullIds.length ? titleOf(fullIds[insertFull]) : null;

    return {
      lane, insertFull, position, beforeTitle, afterTitle,
      dayName: WEEKDAY_FULL[weekday], halfWord: half === 'AM' ? 'morning' : 'afternoon',
    };
  }

  // Phrase like "before Standup, 2nd in Tuesday morning" — derived from resolveDrop
  // so the spoken slot == the persisted slot.
  const positionPhrase = (activeKey: UniqueIdentifier, overId: UniqueIdentifier | null): string => {
    if (!overId) return 'is not over a lane';
    const r = resolveDrop(activeKey, overId);
    if (!r) return 'is not over a lane';
    if (!r.lane) return 'is over the sidebar to unschedule';
    const ordinal = ordinalOf(r.insertFull + 1);
    return r.afterTitle
      ? `before ${r.afterTitle}, ${ordinal} in ${r.dayName} ${r.halfWord}`
      : `last in ${r.dayName} ${r.halfWord}`;
  };
  // True when a drop over `overId` lands on no lane (the sidebar / unschedule
  // region) — the SAME `!r.lane` condition onDragEnd fires the DELETE on (H2), so
  // the speech ("Unscheduled …") can never disagree with the persistence.
  const isUnscheduleTarget = (activeId: UniqueIdentifier, overId: UniqueIdentifier | null): boolean => {
    if (!overId) return false;
    const r = resolveDrop(activeId, overId);
    return !!r && !r.lane;
  };
  const announcements = buildAnnouncements({ titleOf, positionPhrase, isUnscheduleTarget });

  // Resolve an over-id (a lane droppable, a card sort id) into its lane context.
  function resolveLane(overId: string): { weekday: Weekday; half: Half; day: string } | null {
    // Direct lane droppable: "lane:wd:HALF".
    const laneDrop = parseLaneDroppableId(overId);
    if (laneDrop) {
      const day = days[laneDrop.weekday];
      return { weekday: laneDrop.weekday, half: laneDrop.half, day };
    }
    // Otherwise the over-id is a card; find which lane it belongs to.
    for (const day of visibleDays) {
      const wd = weekdayOf(day);
      for (const half of ['AM', 'PM'] as Half[]) {
        if (laneSortIds(wd, half, day).includes(overId)) return { weekday: wd, half, day };
      }
    }
    return null;
  }

  // ---- drag lifecycle -------------------------------------------------------
  function onDragStart(e: DragStartEvent) {
    // Meetings are anchors, not draggable — but guard anyway.
    if (isEventKey(String(e.active.id))) return;
    setActiveId(e.active.id);
  }

  function onDragOver(e: DragOverEvent) {
    const over = e.over;
    if (!over) { setOverLane(null); setOverId(null); return; }
    setOverId(over.id);
    const lane = resolveLane(String(over.id));
    // BUG 4: a past day is not a valid drop target — never light its [data-drop-active]
    // wash (the drop-line is suppressed via dropOnPast in render). The card can still be
    // dragged OUT of a past lane; this only refuses it as a DESTINATION.
    const lanePast = lane ? dayRelation(lane.day, todayInTz(now, tz)) === 'past' : false;
    setOverLane(
      lane && !lanePast
        ? `lane:${lane.weekday}:${lane.half}`
        : (String(over.id) === SIDEBAR_DROPPABLE_ID ? SIDEBAR_DROPPABLE_ID : null),
    );
  }

  function onDragEnd(e: DragEndEvent) {
    const activeKey = String(e.active.id);
    setActiveId(null);
    setOverLane(null);
    setOverId(null);
    if (isEventKey(activeKey)) return; // meetings never move

    const over = e.over;
    if (!over) return;
    const overId = String(over.id);
    const { source, id: taskId } = parseTaskKey(activeKey);

    // Resolve via the SINGLE source of truth (H1) — the same call the announcer
    // used, so the persisted slot is exactly the slot that was spoken/shown.
    const r = resolveDrop(activeKey, overId);
    if (!r) return;

    // H2: unschedule when the drop resolves to NO lane — the SAME condition the
    // announcer uses (`!r.lane` → "over the sidebar to unschedule"). Previously this
    // only fired on an exact `overId === SIDEBAR_DROPPABLE_ID` match, so a drop onto
    // a CARD inside the sidebar's sortable list (or anywhere the over-id resolved to
    // no lane) announced "unscheduled" but never fired the DELETE — a silent no-op.
    // Now both the speech and the persistence agree: no lane ⇒ unschedule.
    if (!r.lane) {
      if (findPlacement(plan, source, taskId)) unschedule(source, taskId);
      return;
    }

    // BUG 4: you cannot PLAN INTO THE PAST. If the target lane is a past day, refuse the
    // drop — leave the card exactly where it was (a fresh sidebar card stays unscheduled;
    // a placed card stays in its current lane; no reducer dispatch = the optimistic ghost
    // snaps back). Dragging OUT of a past lane is unaffected: that path resolves to a
    // future/today target lane (handled below) or to the sidebar (handled above), so an
    // undone past task can always be rescheduled. Today + future lanes accept drops normally.
    if (dayRelation(r.lane.day, today) === 'past') {
      setNotice('That day’s already past — drop into today or a future day instead.');
      return;
    }

    const { weekday, half } = r.lane;
    const self = findPlacement(plan, source, taskId);
    const selfId = self?.id ?? null;
    // BUG 5: a placed card is moving to a DIFFERENT lane when its current placement's
    // {weekday,half} differs from the target lane. The server's /reorder ONLY changes
    // position within the row's existing cell — it cannot re-lane — so a cross-lane move
    // routed through /reorder silently kept the card in its old box (snap-back on reload).
    // We pass the laneChanged flag so placeTask uses /assign (an UPSERT that moves lane +
    // sets the unified position) for cross-lane moves, /reorder only for same-lane.
    const laneChanged = self != null && (self.weekday !== weekday || self.half !== half);

    // r.position is the UNIFIED-space target (events + tasks), already self-excluded —
    // the same slot the announcer/drop-line showed. No task-only collapse anymore.
    placeTask({ source, taskId, weekday, half, position: r.position, selfId, laneChanged });
  }

  // Optimistic place + persist. New card → assign. Existing card: same lane → reorder
  // (position-only); DIFFERENT lane → assign (the UPSERT re-lanes + repositions). The
  // `position` is the UNIFIED-space target computed in resolveDrop — sent verbatim to
  // the server AND used for the optimistic reducer order, so the two never disagree.
  function placeTask({
    source, taskId, weekday, half, position, selfId, laneChanged,
  }: {
    source: string; taskId: string; weekday: Weekday; half: Half;
    position: number; selfId: number | null; laneChanged?: boolean;
  }) {
    const existing = selfId != null;
    // Reorder ONLY for an already-persisted row (positive id) staying in the SAME lane.
    // A negative (optimistic-only) id, or any lane change, must go through assign.
    const useReorder = existing && selfId! > 0 && !laneChanged;

    // 1) OPTIMISTIC reducer update (Vivi's drop-settle plays on the DragOverlay).
    dispatch({ type: 'place', source, externalTaskId: taskId, weekday, half, position });

    // 2) PERSIST — send the unified-space position; the server honors it (or
    // renormalizes the cell on a rare collision and re-derives the same rank).
    void (async () => {
      const outcome = useReorder
        ? await reorderPlacement({ id: selfId!, position })
        : await assignPlacement({
            week_start: weekStart, weekday, half, source, external_task_id: taskId,
            position,
          });
      handleOutcome(outcome, source, taskId, () => {
        // revert: remove the optimistic placement (or re-hydrate from server).
        dispatch({ type: 'remove', source, externalTaskId: taskId });
      });
    })();
  }

  function unschedule(source: string, taskId: string) {
    dispatch({ type: 'remove', source, externalTaskId: taskId });
    void (async () => {
      const outcome = await unassignPlacement({ source, external_task_id: taskId });
      handleOutcome(outcome, source, taskId, () => { /* re-hydrate on next fetch */ });
    })();
  }

  // Promote / demote a task as a WEEKLY GOAL (Iris 20 §2 Star). Optimistic: flip the
  // membership set immediately (so the teal treatment / pinned-pool move is instant),
  // then POST (set) or DELETE (unset) the weekly-goal route. Same calm posture as every
  // other write — a 503 keeps the optimistic state (the read-only hint shows once); a
  // genuine failure reverts the flip and shows the calm inline notice. Also mirror the
  // flag into the reducer so a placed card's move preserves its highlight status.
  function toggleWeeklyGoal(source: string, taskId: string) {
    const key = taskKey(source, taskId);
    const wasGoal = weeklyGoalKeys.has(key);
    const next = !wasGoal;
    setWeeklyGoalKeys((prev) => {
      const s = new Set(prev);
      if (next) s.add(key); else s.delete(key);
      return s;
    });
    // Keep the reducer's per-item flag in lockstep for placed cards (move-preservation).
    if (findPlacement(plan, source, taskId)) {
      dispatch({ type: 'weeklyGoal', source, externalTaskId: taskId, value: next });
    }
    void (async () => {
      const body = { week_start: weekStart, source, external_task_id: taskId };
      const outcome = next ? await setWeeklyGoal(body) : await unsetWeeklyGoal(body);
      if (outcome.kind === 'ok') {
        setNotice(null);
      } else if (outcome.kind === 'disabled') {
        setWriteDormant(true); // keep optimistic state; the read-only hint already shows
      } else {
        // Revert the optimistic flip + mirror back into the reducer.
        setWeeklyGoalKeys((prev) => {
          const s = new Set(prev);
          if (wasGoal) s.add(key); else s.delete(key);
          return s;
        });
        if (findPlacement(plan, source, taskId)) {
          dispatch({ type: 'weeklyGoal', source, externalTaskId: taskId, value: wasGoal });
        }
        setNotice('Couldn’t update that weekly goal just now — it’s back as it was. Try again.');
      }
    })();
  }

  // Complete / un-complete a PLACED task (Iris 20 §7). Optimistic: flip the reducer's
  // per-item completedLocal immediately (the done treatment — title strike + fade — is
  // instant), then POST /api/planner/complete. Same calm posture as every other write:
  // a 503 keeps the optimistic state (the read-only hint already shows); a genuine
  // failure reverts the flip and shows the calm inline notice. The SOURCE-done case
  // (status==='done') never reaches here — PlanCard disables the check (sticky/read-only),
  // so this only ever toggles a LOCAL completion (true sets, false un-completes).
  function toggleComplete(it: PlanItem) {
    const wasComplete = !!it.completedLocal;
    const next = !wasComplete;
    dispatch({ type: 'complete', source: it.source, externalTaskId: it.externalTaskId, value: next });
    void (async () => {
      const outcome = await completePlacement({
        weekStart, source: it.source, externalTaskId: it.externalTaskId, completed: next,
      });
      if (outcome.kind === 'ok') {
        setNotice(null);
      } else if (outcome.kind === 'disabled') {
        setWriteDormant(true); // keep optimistic state; the read-only hint already shows
      } else {
        dispatch({ type: 'complete', source: it.source, externalTaskId: it.externalTaskId, value: wasComplete });
        setNotice('Couldn’t update that just now — it’s back as it was. Try again.');
      }
    })();
  }

  // Move a placed task to the next visible day, same half (the "shed" gesture). It
  // lands at the TAIL of the next day's lane in the unified space — below every event
  // and task there. Tail position = max unified position + 1 (or EVENT_FLOOR + 1 when
  // the lane is empty), so a shed task never jumps above the day's meetings.
  function moveToNextDay(it: PlanItem) {
    const curDay = days[it.weekday];
    const nextDay = addDays(curDay, 1);
    const nextWd = weekdayOf(nextDay);
    const unified = laneUnified(nextWd, it.half, nextDay)
      .filter((x) => x.sortId !== taskKey(it.source, it.externalTaskId));
    const tailPos = unified.length
      ? Math.max(...unified.map((x) => x.position)) + 1
      : EVENT_FLOOR + 1;
    placeTask({
      source: it.source, taskId: it.externalTaskId, weekday: nextWd, half: it.half,
      position: tailPos, selfId: it.id,
      // Moving to the next day is always a lane change → assign (re-lanes), never reorder.
      laneChanged: true,
    });
  }

  function handleOutcome(
    outcome: WriteOutcome,
    source: string, taskId: string, revert: () => void,
  ) {
    if (outcome.kind === 'ok') {
      setNotice(null);
      const assignment = outcome.body.assignment;
      if (assignment) {
        dispatch({
          type: 'confirm', matchSource: source, matchTaskId: taskId,
          serverRow: {
            id: assignment.id,
            weekday: assignment.weekday as Weekday,
            half: assignment.half,
            source, externalTaskId: taskId,
            position: assignment.position, note: null, status: 'live',
          },
        });
      }
    } else if (outcome.kind === 'disabled') {
      // Calm: keep the optimistic state locally; show the read-only hint once.
      setWriteDormant(true);
    } else {
      // Genuine failure → revert + a calm inline notice (no alert/toast spam).
      revert();
      setNotice('Couldn’t save that move just now. It’s back where it was — try again.');
    }
  }

  // ---- sidebar prefs (Iris 11 §3): collapse + group-by-source, both persisted ---
  const [sidebarCollapsed, toggleSidebarCollapsed] = usePersistedBool(SIDEBAR_COLLAPSED_KEY, false);
  const [sidebarGrouped, toggleSidebarGrouped] = usePersistedBool(SIDEBAR_GROUPED_KEY, false);
  // Iris 20 §3: focus-mode filter — board shows only HIGHLIGHTS (placed weekly goals) +
  // meetings/events per day; non-highlight task cards hide from the lanes. Persisted.
  const [focusMode, toggleFocusMode] = usePersistedBool(FOCUS_MODE_KEY, false);
  // Iris 13 req 5: per-source-group collapse, persisted (localStorage, keyed by source).
  const { isCollapsed: isGroupCollapsed, toggle: toggleGroup } = useGroupCollapsed();

  // ---- render ---------------------------------------------------------------
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Card detail modal: hold the active payload + an open flag (kept separate so the
  // payload persists through the close animation, then unmounts inside the modal).
  const [detail, setDetail] = useState<CardDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const openDetail = useCallback((d: CardDetail) => { setDetail(d); setDetailOpen(true); }, []);
  const today = todayInTz(now, tz);
  // Iris 14 §A: which half is live right now (vs am_pm_split). Recomputed every
  // render — and the board re-renders on the existing per-minute `now` tick — so the
  // brass top-edge crosses AM→PM the minute the clock passes the split, no reload.
  // PlannerDay stamps data-current-half on TODAY's matching box only.
  const liveHalf = currentHalf(now, settings);

  // Iris 16 §9: COLLAPSE MORNING. Once the afternoon is reached (liveHalf==='pm') we OFFER
  // a toggle that hides the AM band so the divider + PM rise up and the user focuses on the
  // afternoon. The toggle is only shown when liveHalf==='pm' (no point collapsing the
  // morning in the morning). Persisted (localStorage, session-scoped is fine) via the same
  // usePersistedBool idiom as the sidebar prefs. When the morning is live again (next day),
  // the offer disappears and we force the AM band visible so a stale collapsed flag can
  // never hide the live morning.
  const [amCollapsedPref, toggleAmCollapsed] = usePersistedBool(AM_COLLAPSED_KEY, false);
  const canCollapseAm = liveHalf === 'pm';
  const amCollapsed = canCollapseAm && amCollapsedPref;

  // Felix (Vivi motion audit A1, 2026-06-03): smooth "Hide morning" collapse.
  // The old behaviour set the AM dayboxes to display:none → the row-2 grid track
  // dropped to 0 in ONE frame (snap). To animate it we transition the board's
  // grid-template-rows row-2 track between the measured AM-band height and 0px.
  // grid-template-rows IS animatable when both ends are concrete lengths, so we
  // pin the EXPANDED height as a px value on a CSS var (--planner-am-track) and
  // let the collapsed state resolve to 0px (in cockpit.css). We re-measure on the
  // board ResizeObserver so the expanded track always equals the live AM-band
  // height (cards loading, lane reflow, week swap). The transition itself lives in
  // CSS (.planner-board) so the global prefers-reduced-motion block neutralises it
  // for free — no JS reduced-motion branch needed here (the var is just a length).
  useEffect(() => {
    const boardEl = boardRef.current;
    if (!boardEl) return;
    // The inline --planner-am-track var DRIVES the board's row-2 track height directly (we
    // set it inline rather than via a [data-am-collapsed] CSS rule because an inline style
    // out-specifies a stylesheet rule — so the JS must own BOTH ends or the collapsed 0px
    // would never beat the last measured inline px). Collapsed → 0px. Open → the tallest
    // AM daybox's natural height (the track hugs its content). On expand the boxes are
    // visible again by the time this effect re-runs (amCollapsed dep), so scrollHeight is
    // the true height and the track animates 0px → measured-px.
    const measure = () => {
      if (amCollapsed) {
        boardEl.style.setProperty('--planner-am-track', '0px');
        return;
      }
      const amBoxes = boardEl.querySelectorAll<HTMLElement>(".planner-daybox[data-half='am']");
      let tallest = 0;
      amBoxes.forEach((box) => {
        const h = box.scrollHeight;
        if (h > tallest) tallest = h;
      });
      if (tallest > 0) boardEl.style.setProperty('--planner-am-track', `${tallest}px`);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(boardEl);
    boardEl.querySelectorAll<HTMLElement>(".planner-daybox[data-half='am']").forEach((b) => ro.observe(b));
    return () => ro.disconnect();
    // Re-arm when the morning toggles (so the just-expanded boxes get measured) and
    // when the visible week changes (different content → different AM height).
  }, [amCollapsed, visibleDays]);

  // One sidebar task card (shared by flat + grouped modes so drag behaves identically
  // in both — the same SortableTaskCard, same namespaced id, same SortableContext).
  const renderSidebarCard = useCallback((t: NormalizedTask) => {
    const key = taskKey(t.source, t.id);
    return (
      <SortableTaskCard
        key={key}
        id={key}
        title={t.title}
        meta={taskMetaLabel(t)}
        glyphSource={t.source}
        badge={t.priorityRank === 1 ? <StatusChip tone="attn">important</StatusChip> : undefined}
        onOpenDetail={() => openDetail(taskDetail(t, labelForSource(t.source)))}
        // Iris 20 §2: a sidebar task can be promoted to a weekly goal (→ teal, moves into
        // the pinned section). An unplaced weekly goal IS NOT a highlight (it's not on a
        // day), but it wears the same teal pin treatment per the spec, so isHighlight=true
        // for the visual hook. The star toggles membership; the optimistic split re-pins it.
        isHighlight={isWeeklyGoalKey(key)}
        onToggleHighlight={() => toggleWeeklyGoal(t.source, t.id)}
      />
    );
    // toggleWeeklyGoal closes over current state but is stable enough for this render path;
    // isWeeklyGoalKey changes when membership changes, re-rendering the affected cards.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openDetail, isWeeklyGoalKey, labelForSource]);

  // Grouped-mode sections (Iris 11 §3b): data-driven over the /api/cockpit/sources
  // groups — group order = RESPONSE order, labels from the response's `label` — so
  // any new connector slots in automatically once it produces tasks. Each group
  // carries its source glyph + label + count + its cards. Every card id stays in
  // the flat `sortIds` above, so dnd-kit drags work across groups unchanged.
  // Sources with nothing currently unscheduled render no group (nothing to drag).
  const sidebarGroups = useMemo<SidebarGroup[]>(() => {
    const bySource = new Map<string, NormalizedTask[]>();
    for (const t of normalUnscheduled) {
      if (!bySource.has(t.source)) bySource.set(t.source, []);
      bySource.get(t.source)!.push(t);
    }
    return sourceGroups
      .filter((g) => (bySource.get(g.source)?.length ?? 0) > 0)
      .map((g) => {
        const tasks = bySource.get(g.source)!;
        return {
          source: g.source,
          label: g.label,
          count: tasks.length,
          cards: tasks.map((t) => renderSidebarCard(t)),
        };
      });
  }, [normalUnscheduled, sourceGroups, renderSidebarCard]);

  // Live drop-line target (M1): the resolved full-list insertion index for the lane
  // currently under the drag. Same resolveDrop call as the announcer/persistence, so
  // the brass line renders at the exact slot that will be spoken AND persisted.
  const drop = activeId && overId ? resolveDrop(activeId, overId) : null;
  // BUG 4: a past day is not a valid drop target — show NO drop-line there (and below,
  // no [data-drop-active] wash) so the past lane never looks droppable, matching the
  // onDragEnd refusal. dayRelation uses the same `today` the refusal does.
  const dropOnPast = !!(drop && drop.lane && dayRelation(drop.lane.day, today) === 'past');
  const dropTarget = drop && drop.lane && !dropOnPast
    ? { weekday: drop.lane.weekday, half: drop.lane.half, index: drop.insertFull }
    : null;

  // The active overlay card (Vivi §2.1/§2.4: the lifted clone — scale/shadow/tilt).
  // P1b (Pax 09): the overlay re-renders on EVERY pointer-move frame while dragging.
  // We derive a tiny PRIMITIVE-ONLY prop bag once per drag (useMemo keyed on activeId)
  // and feed it to a React.memo'd presentational clone, so React skips re-rendering
  // the card mid-drag — heavy overlay re-renders are dnd-kit's documented #2 lag cause.
  const overlayProps = useMemo<OverlayCardProps | null>(() => {
    if (!activeId) return null;
    const t = taskByKey.get(String(activeId));
    if (!t) return null;
    return {
      title: t.title,
      meta: taskMetaLabel(t),
      glyphSource: t.source,
    };
    // taskByKey is stable per fetch; the only per-drag-frame change is activeId, and
    // the clone is fixed for the duration of a single drag. Intentionally narrow deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  return (
    <section ref={topRef} className="actions-view dashboard-view animate-fade-rise">
      {/* Iris 15 §4: the "Plan" title + subtitle header is removed; the toolbar (week-nav
          + gear) becomes the top element and the board reclaims the vertical space. The
          page-title / page-sub / dashboard-header-mark classes stay in CSS (shared by
          other views) — we simply stop rendering them here. */}
      {notice && !writeDormant && (
        <p className="rounded-panel border border-border bg-surface-bg px-md py-sm text-meta text-fg-muted" role="status">
          {notice}
        </p>
      )}
      {(writeDormant || settingsWriteDisabled) && (
        <p className="text-caption text-fg-subtle" role="status">
          Planning is read-only until enabled. Your layout is kept on this device and
          will sync once the write path is turned on.
        </p>
      )}

      {/* Iris 13 req 3 + Iris 15 §4: the week switcher + gear live in a TOOLBAR ROW that is
          now the TOP element of the view (the Plan title/subtitle above it is removed).
          Full board width, controls right-aligned; Iris's .planner-toolbar spacing
          (margin 4px 0 16px, min-height 36px) seats it close to the content top edge. */}
      <div className="planner-toolbar">
        <WeekNav weekStart={weekStart} onChange={setWeekStart} />
        {/* Iris 16 §9: collapse-morning toggle — ONLY offered once the afternoon is live
            (canCollapseAm). Hides the AM band so the divider + PM rise up; persisted. */}
        {canCollapseAm && (
          <button
            type="button"
            onClick={toggleAmCollapsed}
            aria-pressed={amCollapsed}
            aria-label={amCollapsed ? 'Show the morning' : 'Collapse the morning to focus on the afternoon'}
            title={amCollapsed ? 'Show morning' : 'Collapse morning'}
            className="inline-flex h-[36px] items-center gap-xs rounded-panel px-sm text-meta text-fg-muted transition-colors hover:bg-surface-2 hover:text-marker-text focus-visible:bg-surface-2 focus-visible:text-marker-text"
          >
            {amCollapsed
              ? <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
              : <ChevronUp size={16} strokeWidth={1.5} aria-hidden="true" />}
            <span>{amCollapsed ? 'Morning' : 'Hide morning'}</span>
          </button>
        )}
        {/* Iris 20 §3: focus-mode toggle. Idle = muted Focus glyph (matches the gear);
            active = the brass active-pill (data-active drives Iris's --planner-focus-toggle
            -*). Filters the board to highlights + meetings; the pinned Weekly Goals stay. */}
        <button
          type="button"
          onClick={toggleFocusMode}
          data-active={focusMode ? 'true' : undefined}
          aria-pressed={focusMode}
          aria-label={focusMode ? 'Exit focus mode (show all tasks)' : 'Focus mode: show only highlights and meetings'}
          title={focusMode ? 'Exit focus' : 'Focus: highlights + meetings'}
          className="planner-focus-toggle h-[36px] w-[36px]"
        >
          <Focus size={16} strokeWidth={1.75} aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          aria-label="Planning settings"
          className="inline-flex h-[36px] w-[36px] items-center justify-center rounded-panel text-fg-muted transition-colors hover:bg-surface-2 hover:text-marker-text focus-visible:bg-surface-2 focus-visible:text-marker-text"
        >
          <Settings size={18} strokeWidth={1.5} aria-hidden="true" />
        </button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={plannerCollision}
        measuring={{ droppable: { strategy: MeasuringStrategy.Always } }}
        accessibility={{ announcements }}
        onDragStart={onDragStart}
        onDragOver={onDragOver}
        onDragEnd={onDragEnd}
        onDragCancel={() => { setActiveId(null); setOverLane(null); setOverId(null); }}
      >
        {/* Iris 13 req 2: gap-lg (--space-lg / 24px) between the board and the
            Unscheduled rail. Iris 13 req 4: planner-layout fills the available content
            height so the board and sidebar can each own an independent scroll region
            (the .planner-board-scroll + .planner-tasksidebar overflow below). */}
        <div className="planner-layout flex items-start gap-lg">
          {/* Iris 15 §3: the live day-progress rail — a 16px gutter that is a flex SIBLING
              LEFT of the board, stretched to full board height. It tracks TODAY's progress
              through work_hours; it self-hides when today isn't in the visible week or
              today's work_hours are missing. The per-second update is ISOLATED inside this
              component (a ref write to --planner-now-pct), so the heavy board never
              re-renders each second. */}
          <DayProgressRail today={today} visibleDays={visibleDays} settings={settings} tz={tz} boardRef={boardRef} amCollapsed={amCollapsed} />
          {/* Iris 16 (Sunsama): the board is a 4-ROW grid — day headers / AM band /
              full-width divider / PM band. Each day is a `display:contents` wrapper
              (PlannerDay) whose header (grid-row 1, OUTSIDE the boxes, on the bare board
              ground), AM box (grid-row 2) and PM box (grid-row 4) participate DIRECTLY in
              the board grid, staying column-aligned. The divider is ONE element spanning
              all columns (grid-column 1/-1) in row 3 — one "the day splits here" line
              across the whole board. Drop lanes stay keyed by {weekday,half}
              (HalfLane.laneDroppableId) independent of this DOM nesting, so drops resolve
              to the visible band/day exactly as before. */}
          <div
            ref={boardRef}
            className="planner-board min-w-0 flex-1"
            data-am-collapsed={amCollapsed ? 'true' : undefined}
            style={{ '--planner-day-count': visibleDays.length } as React.CSSProperties}
          >
            {visibleDays.map((day) => {
              const wd = weekdayOf(day);
              const renderLane = (half: Half) => {
                // Iris 20 §3 — focus-mode filter: in focus the board lanes show ONLY
                // highlights (placed weekly goals) + meetings/events; non-highlight task
                // cards are hidden. We filter the lane's task list so dnd-kit's sortable
                // list never references a card that isn't rendered. Meetings are unaffected
                // (they stay anchors). Calm — no jarring reflow.
                const allLaneTasks = laneItems(plan, wd, half);
                const laneTasks = focusMode
                  ? allLaneTasks.filter((it) => isWeeklyGoalKey(taskKey(it.source, it.externalTaskId)))
                  : allLaneTasks;
                const laneMeetings = meetingsFor(day, half);

                // UNIFIED render order (2026-06-23): merge events + tasks into ONE
                // position-sorted sequence — NOT "meetings first, then tasks". An event's
                // unified position is time-derived (eventPosition); a task's is its stored
                // `position`. The rendered list, its sortId list (dnd-kit), and the
                // drop-line index all come from this ONE merge, so a task ordered ABOVE an
                // event renders, drags, and persists at exactly that slot. Tie-break: an
                // event leads a task at an identical position (all-day events sort first).
                const renderItems: LaneRow[] = [
                  ...laneMeetings.map((e) => ({
                    kind: 'event' as const, sortId: eventKey(e.uid), position: eventPosition(e, tz), event: e,
                  })),
                  ...laneTasks.map((it) => ({
                    kind: 'task' as const, sortId: taskKey(it.source, it.externalTaskId), position: it.position, task: it,
                  })),
                ].sort((a, b) =>
                  a.position - b.position
                  || (a.kind === b.kind ? 0 : a.kind === 'event' ? -1 : 1));
                const laneSort = renderItems.map((r) => r.sortId);
                return (
                  <LaneBody
                    day={day}
                    weekday={wd}
                    half={half}
                    rows={renderItems}
                    tasks={laneTasks}
                    taskByKey={taskByKey}
                    tz={tz}
                    overLane={overLane}
                    sortIds={laneSort}
                    dropLineIndex={dropTarget && dropTarget.weekday === wd && dropTarget.half === half ? dropTarget.index : null}
                    calendarStatus={calendarStatus}
                    labelForSource={labelForSource}
                    onMoveNext={moveToNextDay}
                    onOpenDetail={openDetail}
                    isWeeklyGoalKey={isWeeklyGoalKey}
                    onToggleHighlight={toggleWeeklyGoal}
                    onToggleComplete={toggleComplete}
                  />
                );
              };
              const isToday = day === today;
              return (
                <PlannerDay
                  key={day}
                  day={day}
                  weekday={wd}
                  isToday={isToday}
                  // Iris 15 §2: past / today / future, stamped on BOTH dayboxes so the
                  // whole column dims as one tier (Iris's CSS owns the opacity values).
                  temporal={dayRelation(day, today)}
                  tz={tz}
                  // Iris 14 §A: only TODAY's column carries the live half; non-today
                  // columns pass null so they never wear the brass top-edge.
                  currentHalf={isToday ? liveHalf : null}
                  // Iris 16 §C: the active box's countdown bar needs the live clock +
                  // hours to compute "Xh Ym left" + the calm timer state. Only the
                  // active (today × current-half) box renders the bar.
                  now={now}
                  settings={settings}
                  renderLane={renderLane}
                />
              );
            })}
            {/* Iris 14 §B: row 2 is EITHER the single AM/PM split OR — when the user
                enables lunch_break — a band (start rule · hatch fill · end rule). Both
                live in the same grid-column 1/-1 row-2 slot, so the board stays
                continuous + scroll-synced either way. Disabled is the default and
                renders exactly the single divider as before. */}
            {/* Vivi audit A3: one measured-height wrapper holds BOTH the single split and
                the lunch band, animating the height swap + hatch crossfade instead of the
                old one-frame component swap (which jumped the PM band down). */}
            <PlannerDivider
              lunchEnabled={settings.lunch_break.enabled}
              splitTime={settings.am_pm_split}
              lunchStart={settings.lunch_break.start}
              lunchEnd={settings.lunch_break.end}
            />
          </div>

          <UnscheduledSidebar
            // `count` is the NORMAL (non-goal) unscheduled list; the pinned Weekly Goals
            // pool is counted separately. sortIds lists pinned goal keys FIRST so they sort
            // ahead of the normal list in the one shared SortableContext.
            count={normalUnscheduled.length}
            sortIds={[
              ...pinnedGoals.map((t) => taskKey(t.source, t.id)),
              ...normalUnscheduled.map((t) => taskKey(t.source, t.id)),
            ]}
            isDropTarget={overLane === SIDEBAR_DROPPABLE_ID}
            allPlaced={allTasks.length > 0 && unscheduled.length === 0}
            collapsed={sidebarCollapsed}
            onToggleCollapsed={toggleSidebarCollapsed}
            grouped={sidebarGrouped}
            onToggleGrouped={toggleSidebarGrouped}
            groups={sidebarGrouped ? sidebarGroups : null}
            isGroupCollapsed={isGroupCollapsed}
            onToggleGroup={toggleGroup}
            pinnedGoalCount={pinnedGoals.length}
            pinnedGoals={pinnedGoals.map((t) => renderSidebarCard(t))}
            // Iris 20 §5: the PLACED weekly goals as static day-badged ledger rows
            // (NOT in sortIds — no duplicate dnd-kit id). dayAbbr from WEEKDAY_LABELS
            // (0=Mon), half from the placement (AM/PM), used for the "Wed · PM" badge.
            placedGoals={placedGoals.map((g) => ({
              key: g.key,
              title: g.title,
              dayAbbr: WEEKDAY_LABELS[g.weekday],
              half: g.half,
            }))}
            sourceNotices={
              <SourceNotices sources={sourceGroups} calendarStatus={calendarStatus} />
            }
          >
            {normalUnscheduled.map((t) => renderSidebarCard(t))}
          </UnscheduledSidebar>
        </div>

        {/* The lifted clone. Vivi §2.1 lift (scale 1.02 + shadow + 0.6° tilt) is
            applied via the wrapper class; §2.4 drop-settle via dropAnimation.
            P0 (Pax 09): PORTAL the overlay to document.body. dnd-kit positions the
            overlay with `position: fixed`, which resolves against the nearest ancestor
            carrying transform/filter/backdrop-filter — and this subtree has BOTH (the
            `animate-fade-rise` entrance transform on section.actions-view + the chrome's
            backdrop-filter:blur). Either re-roots the fixed box and offsets the card from
            the cursor. Portaling to <body> (no transformed/filtered ancestor) makes the
            overlay track the cursor 1:1 regardless of ancestor CSS — the correct boundary,
            not stripping the chrome. Keep <DragOverlay> mounted; render only its children
            conditionally so drop animations don't break. */}
        {/* R3.1 HARDENING (Felix): dnd-kit's <DragOverlay> renders a wrapper div that
            carries the live `translate3d` follow transform. Its computed `transition`
            currently inherits `all` — inert today (0s duration) but fragile: a non-zero
            duration anywhere up the cascade would make `transform` transition and the
            follow would rubber-band (the sluggishness Tom flagged). The inline
            style={{ transition: 'none' }} below locks transform out of any transition
            on the wrapper during the 1:1 follow. The drop-settle is dropAnimation
            (release-time), untouched by this. */}
        {createPortal(
          <DragOverlay
            dropAnimation={dropAnimationFor(reduced)}
            zIndex={50}
            style={{ transition: 'none' }}
          >
            {overlayProps ? (
              <div className={reduced ? '' : 'planner-drag-overlay'}>
                <OverlayCard {...overlayProps} />
              </div>
            ) : null}
          </DragOverlay>,
          document.body,
        )}
      </DndContext>

      <SettingsSheet
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onSave={(next) => { void updateSettings(next); }}
        writeDisabled={settingsWriteDisabled || writeDormant}
      />

      <CardDetailModal
        open={detailOpen}
        detail={detail}
        onClose={() => setDetailOpen(false)}
      />
    </section>
  );
}

// ---- live day-progress rail (Iris 15 §3) ------------------------------------
// A narrow left gutter beside the board showing TODAY's progress through work_hours.
// Iris's CSS owns ALL the visuals (track / elapsed fill / now-marker / 1s glide); this
// component owns ONLY two live values: --planner-now-pct (0..1) and data-rail-state.
//
// CRITICAL — the per-second update is ISOLATED here and writes straight to the DOM via
// a ref (el.style.setProperty / setAttribute). It NEVER calls setState, so PlannerView
// (and the whole board) does NOT re-render each second — Iris's `transition: 1000ms
// linear` smooths each step into a continuous downward glide.
//
// prefers-reduced-motion: drop the continuous glide (Iris's CSS already neutralises the
// transition) AND slow the tick to per-minute so there's no constant motion — the marker
// just snaps to its current position at each step.
//
// Self-hides (renders null) when:
//   • today isn't in the visible week (past/future navigation — no live "now" to show), or
//   • today's work_hours are missing / zero-span (nothing to map a fraction onto).
function DayProgressRail({
  today, visibleDays, settings, tz, boardRef, amCollapsed,
}: {
  today: string;
  visibleDays: string[];
  settings: PlannerSettings;
  tz: string;
  // Iris 16 §8: ref to the board so the rail can size itself to the board's RENDERED
  // CONTENT height (not the viewport-tall scroll-container box).
  boardRef: React.RefObject<HTMLDivElement | null>;
  // Felix fix (2026-06-03): collapse-morning state — when the AM band hides the block is
  // shorter, so the rail re-measures on this flag.
  amCollapsed: boolean;
}) {
  const railRef = useRef<HTMLDivElement | null>(null);
  // The live "now" time digits (e.g. "14:00") shown at the marker — Iris 16 §B. Held in
  // state so the chip text re-renders; the heavy --planner-now-pct top stays a ref write.
  const [nowLabel, setNowLabel] = useState<string>('');
  const reduced = prefersReducedMotion();

  // Today must be visible AND a workday with a non-zero work_hours span, else no rail.
  const todayVisible = visibleDays.includes(today);
  const wd = weekdayOf(today);
  const hours = hoursForWeekday(settings, wd);
  const startMin = hhmmToMinutes(hours.start);
  const endMin = hhmmToMinutes(hours.end);
  const hasSpan = isWorkday(settings, wd) && endMin > startMin;
  const active = todayVisible && hasSpan;

  useEffect(() => {
    if (!active) return;
    const el = railRef.current;
    if (!el) return;

    // pct = progress of current wall-clock time through [start,end], clamped 0..1.
    // state: 'before' (clamped 0, day not started), 'after' (clamped 1, day ended),
    // else 'live'. Uses the planner's display tz (not the browser zone), matching how
    // the board buckets the day.
    let lastLabel = '';
    const apply = () => {
      const nowMin = tzMinutesOfDay(new Date(), tz);
      const raw = (nowMin - startMin) / (endMin - startMin);
      const pct = raw < 0 ? 0 : raw > 1 ? 1 : raw;
      const state = nowMin < startMin ? 'before' : nowMin > endMin ? 'after' : 'live';
      el.style.setProperty('--planner-now-pct', String(pct));
      el.setAttribute('data-rail-state', state);
      // Iris 16 §B: the chip shows the current wall-clock HH:MM. Only setState when the
      // displayed minute actually changes (the 1s glide tick must NOT thrash React).
      const hh = String(Math.floor(nowMin / 60)).padStart(2, '0');
      const mm = String(nowMin % 60).padStart(2, '0');
      const next = `${hh}:${mm}`;
      if (next !== lastLabel) { lastLabel = next; setNowLabel(next); }
    };
    apply();

    // Reduced motion → per-minute tick (no constant motion, marker snaps). Otherwise a
    // 1s tick that Iris's CSS smooths into a continuous glide. The --planner-now-pct write
    // is a pure ref write (no board re-render); only a MINUTE rollover triggers setState.
    const periodMs = reduced ? 60_000 : 1_000;
    const id = window.setInterval(apply, periodMs);
    return () => window.clearInterval(id);
    // startMin/endMin/tz/active/reduced fully capture the inputs; re-arm on any change.
  }, [active, startMin, endMin, tz, reduced]);

  // Felix fix (2026-06-03): size the rail to the rendered BLOCK AREA, not the board's
  // scrollHeight. The board is clamped to ~viewport height for the ≥1501px independent-
  // scroll feature, so when content is short its scrollHeight ≈ the viewport → the rail
  // ran to the bottom of the screen. Instead we measure the true content extent: from the
  // TOP of the board content (the day-header row / first rendered child) down to the
  // BOTTOM of the lowest rendered .planner-daybox, via getBoundingClientRect(). The rail
  // ends where the boxes end; the empty space below stays blank. top=work-hours start /
  // bottom=work-hours end then map onto the real block span. Pure ref/style writes; no
  // board re-render. Re-measures via a ResizeObserver on the board (catches resize, cards
  // loading, lane reflow) and re-runs when amCollapsed / visibleDays change (the AM band
  // hides → shorter block; week navigation swaps content).
  useEffect(() => {
    if (!active) return;
    const railEl = railRef.current;
    const boardEl = boardRef.current;
    if (!railEl || !boardEl) return;
    const sync = () => {
      const boxes = boardEl.querySelectorAll<HTMLElement>('.planner-daybox');
      if (boxes.length === 0) {
        // No boxes rendered yet — fall back to the content extent so the track still shows.
        railEl.style.height = `${boardEl.scrollHeight}px`;
        return;
      }
      // contentTop = top of the board's first rendered child (the day-header row sits on
      // the bare board ground above the AM band); when the morning is collapsed the first
      // visible box is the PM band — either way getBoundingClientRect() reflects reality.
      const contentTop = boardEl.getBoundingClientRect().top;
      let lowestBottom = contentTop;
      boxes.forEach((box) => {
        const r = box.getBoundingClientRect();
        if (r.bottom > lowestBottom) lowestBottom = r.bottom;
      });
      const blockHeight = lowestBottom - contentTop;
      railEl.style.height = `${blockHeight}px`;
    };
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(boardEl);
    boardEl.querySelectorAll<HTMLElement>('.planner-daybox').forEach((box) => ro.observe(box));

    // Felix (Vivi motion audit A1, 2026-06-03): rail-in-lockstep guard. The AM-band
    // collapse animates the board's grid-template-rows track; the PM boxes only MOVE
    // (no size change), so a ResizeObserver on them won't fire — and a RO on the board
    // can coalesce frames and lag the rail behind the closing gap. To keep the rail
    // glued to the band as it animates, we pump sync() on every animation frame for the
    // duration of the grid-template-rows transition: start on transitionrun, stop on
    // transitionend/cancel. This is a measurement re-run only (no React re-render). The
    // rail also carries its own `transition: height var(--ease-collapse)` in CSS as a
    // belt-and-braces smoother, so even a single late RO tick eases rather than jumps.
    let rafId = 0;
    const pump = () => { sync(); rafId = requestAnimationFrame(pump); };
    const onRun = (e: TransitionEvent) => {
      if (e.target === boardEl && e.propertyName === 'grid-template-rows' && !rafId) {
        rafId = requestAnimationFrame(pump);
      }
    };
    const onEnd = (e: TransitionEvent) => {
      if (e.target === boardEl && e.propertyName === 'grid-template-rows' && rafId) {
        cancelAnimationFrame(rafId); rafId = 0; sync();
      }
    };
    boardEl.addEventListener('transitionrun', onRun);
    boardEl.addEventListener('transitionend', onEnd);
    boardEl.addEventListener('transitioncancel', onEnd);
    return () => {
      ro.disconnect();
      if (rafId) cancelAnimationFrame(rafId);
      boardEl.removeEventListener('transitionrun', onRun);
      boardEl.removeEventListener('transitionend', onEnd);
      boardEl.removeEventListener('transitioncancel', onEnd);
    };
  }, [active, boardRef, visibleDays, amCollapsed]);

  if (!active) return null;
  return (
    <div ref={railRef} className="planner-progress-rail" aria-hidden="true">
      <div className="planner-progress-elapsed" />
      <div className="planner-progress-now" />
      {/* Iris 16 §B: the current-time chip riding the marker. aria-hidden inherited from
          the rail wrapper; the time is announced elsewhere. */}
      <div className="planner-progress-now-label">{nowLabel}</div>
    </div>
  );
}

// ---- the lifted overlay clone (P1b: memoized, primitive props only) ----------
// A presentational, handler-free clone so React.memo can skip re-rendering it on
// every pointer-move frame. It reads NO context and takes only primitives, so its
// props are referentially stable for the duration of a single drag.
type OverlayCardProps = {
  title: string;
  meta: string | null;
  glyphSource: string; // connector id (open — SourceMark has a generic fallback)
};
const OverlayCard = memo(function OverlayCard({ title, meta, glyphSource }: OverlayCardProps) {
  return <PlanCard kind="task" title={title} meta={meta} glyphSource={glyphSource} dragging />;
});

// ---- build a CardDetail payload for a sidebar (unscheduled) task ------------
// Sidebar tasks carry no plan-row reconciliation, so note/reconStatus are null. The
// modal renders the full detail + the "Open in <source>" link from task.url itself.
// `sourceLabel` is the response-provided human label for t.source (data-driven).
function taskDetail(t: NormalizedTask, sourceLabel: string): CardDetail {
  return {
    kind: 'task',
    task: t,
    lastKnownTitle: null,
    note: null,
    reconStatus: null,
    sourceLabel,
  };
}

// ---- week navigation --------------------------------------------------------
function WeekNav({ weekStart, onChange }: { weekStart: string; onChange: (w: string) => void }) {
  const isThisWeek = weekStart === mondayOf(todayInTz());
  const label = isThisWeek ? 'This week' : weekDaysLabelFor(weekStart);
  return (
    <div role="group" aria-label="Week navigation" className="inline-flex items-center gap-xs rounded-panel border border-border bg-surface-bg p-[2px]">
      <button
        type="button" aria-label="Previous week" onClick={() => onChange(addDays(weekStart, -7))}
        className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-card text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:bg-surface-2"
      >
        <ChevronLeft size={16} strokeWidth={1.5} aria-hidden="true" />
      </button>
      <button
        type="button" onClick={() => onChange(mondayOf(todayInTz()))}
        className="min-w-[88px] px-xs text-center text-meta font-[460] text-fg"
      >
        {label}
      </button>
      <button
        type="button" aria-label="Next week" onClick={() => onChange(addDays(weekStart, 7))}
        className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-card text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:bg-surface-2"
      >
        <ChevronRight size={16} strokeWidth={1.5} aria-hidden="true" />
      </button>
    </div>
  );
}

// ---- day (two half-boxes spanning the board's AM + PM bands) -----------------
// Iris 12 (option B): a day is no longer one tall column with a line through it; it is
// TWO house-panel boxes — an AM box that drops into the board grid's AM band (row 1)
// and a PM box that drops into the PM band (row 3), kept column-aligned by the
// `display:contents` wrapper (the wrapper itself draws nothing; its two box children
// become direct grid items of .planner-board). The day header + the single brass
// today-edge ride the AM box only (one brass moment, Iris 12 §"today marker").
function PlannerDay({
  day, weekday, isToday, temporal, tz, currentHalf, now, settings, renderLane,
}: {
  day: string;
  weekday: Weekday;
  isToday: boolean;
  // Iris 15 §2: the day's relation to today; stamped on BOTH boxes via data-temporal
  // so Iris's column-level opacity tier dims the whole column (header + cards) as one.
  temporal: 'past' | 'today' | 'future';
  tz: string;
  // The live half on TODAY's column ('am' | 'pm'), or null on every other column.
  // The matching box stamps data-current-half so Iris's brass top-edge (Iris 14 §A)
  // caps whichever half is live; exactly one box per day carries it (single brass).
  currentHalf: 'am' | 'pm' | null;
  // Iris 16 §C: live clock + settings to compute the active box's countdown bar.
  now: Date;
  settings: PlannerSettings;
  renderLane: (half: Half) => React.ReactNode;
}) {
  return (
    // `display:contents` (Tailwind `contents`): the wrapper is transparent to layout, so
    // its THREE children — the day header, the AM box, the PM box — are placed by
    // .planner-board's grid directly into rows 1, 2 and 4 of the same column track. The
    // full-width divider (row 3) sits between the AM and PM boxes.
    <div className="contents">
      {/* Iris 16 §1 (Sunsama): the day header now sits OUTSIDE the boxes — a true column
          HEADER in row 1, on the bare board ground (no border/panel), ABOVE the AM box.
          data-today drives the one brass moment (weekday name) and data-temporal dims it
          with the same tier as the boxes below, so the whole column reads as one. */}
      <header
        className="planner-column-head"
        data-today={isToday ? 'true' : undefined}
        data-temporal={temporal}
      >
        <span className="planner-dayname">{WEEKDAY_FULL[weekday]}</span>
        <span className="planner-daydate">{monthDayLabel(day, tz)}</span>
      </header>
      <section
        className="planner-daybox"
        data-half="am"
        data-today={isToday ? 'true' : undefined}
        data-temporal={temporal}
        data-current-half={currentHalf === 'am' ? 'am' : undefined}
        aria-label={`${WEEKDAY_FULL[weekday]} ${day}, morning`}
      >
        {renderLane('AM')}
        {/* Iris 16 §C: the full-width sticky countdown bar — ONLY on the active box
            (today × current half). Past = hatch (no bar), future = clean/dashed (no bar). */}
        {currentHalf === 'am' && (
          <PlannerCountdownBar half="AM" day={day} now={now} settings={settings} />
        )}
      </section>
      <section
        className="planner-daybox"
        data-half="pm"
        data-today={isToday ? 'true' : undefined}
        data-temporal={temporal}
        data-current-half={currentHalf === 'pm' ? 'pm' : undefined}
        aria-label={`${WEEKDAY_FULL[weekday]} ${day}, afternoon`}
      >
        {renderLane('PM')}
        {currentHalf === 'pm' && (
          <PlannerCountdownBar half="PM" day={day} now={now} settings={settings} />
        )}
      </section>
    </div>
  );
}

// Iris 16 §C — the active box's COUNTDOWN BOTTOM BAR. Replaces the old top-right timer
// chip (now removed from HalfLane). A full-width band pinned to the box floor
// (position:sticky; bottom:0 + negative-margin bleed, per Iris's .planner-countdown-bar)
// showing "Xh Ym left". It reuses the EXACT timer threshold logic (remainingWorkMinutes /
// timerState / formatRemaining) and the EXACT timer state palette via data-state — the
// same calm doctrine as .planner-timer (ample → brass/soft, low → muted, elapsed →
// subtle). No red, no blink, no scale. Rendered ONLY on the active box, so remaining is
// always a live "in this block" countdown (never the future budget or a past 0).
function PlannerCountdownBar({
  half, day, now, settings,
}: {
  half: Half;
  day: string;
  now: Date;
  settings: PlannerSettings;
}) {
  const remaining = remainingWorkMinutes(half, day, now, settings);
  const state = timerState(half, day, now, settings);
  // formatRemaining yields "Xh Ym left" (active) — split the digits from the trailing
  // " left" so the mono digits get .planner-countdown-bar-digits per Iris's markup. For
  // an elapsed active block ("AM done"/"PM done") show the calm done phrase whole.
  const label = formatRemaining(remaining, state, half);
  const digits = state === 'elapsed' ? null : label.replace(/\s*left$/, '');
  return (
    <div className="planner-countdown-bar" data-state={state} role="status" aria-label={label}>
      {digits ? (
        <>
          <span className="planner-countdown-bar-digits">{digits}</span> left
        </>
      ) : (
        label
      )}
    </div>
  );
}

// Iris 12 §3.3 — the single full-width AM/PM split. ONE element spanning the entire
// board (grid-column 1/-1, row 2): the ::before/::after rules grow from each end to a
// centred masking pill carrying the split time (settings.am_pm_split), reading
// `———— 12:00 ————` across the whole board. aria-hidden: the lane group labels already
// announce morning vs afternoon (HalfLane), so this is purely a visual divide.
// (PlannerSplit / PlannerBreakBand were inlined into PlannerDivider below — Vivi audit
//  A3, 2026-06-03 — so both states can co-exist in one measured-height slot and the
//  swap animates instead of snapping. Their markup is reproduced verbatim inside the
//  PlannerDivider wrapper.)

// Iris 14 §B — the lunch-break BAND that replaces the single split when enabled. ONE
// full-width row-2 element (grid-column 1/-1, same slot as PlannerSplit, so it stays
// continuous + scroll-synced for free) holding: a TOP .planner-split-row (chip =
// lunch.start), the patterned .planner-break-fill ("blocked time" hatch), and a BOTTOM
// .planner-split-row (chip = lunch.end). The two edge rules reuse the EXACT existing
// rule+chip recipe verbatim — same masking pill, same tabular time — only the fill
// between is new. aria-hidden like the single divider: the lane group labels already
// announce morning vs afternoon, so the band is purely the visual divide.
// Felix (Vivi motion audit A3, 2026-06-03): the AM/PM divider SLOT. Previously the view
// conditionally rendered <PlannerSplit/> (a ~1px rule) OR <PlannerBreakBand/> (a ~28px+
// band) — toggling lunch_break swapped one for the other in ONE frame, so the row-3 track
// jumped and the whole PM band below it snapped down. Now BOTH live inside one
// measured-height wrapper that occupies the row-3 slot: the active state is in normal flow
// and sets the wrapper's height; the wrapper transitions between the split height and the
// band height (measured-height technique, per Vivi), and the hatch fill crossfades in/out.
// The PM band slides as a natural consequence of the row height — no separate animation.
// CSS-only transition on the wrapper → reduced-motion neutralised by the global block.
function PlannerDivider({
  lunchEnabled, splitTime, lunchStart, lunchEnd,
}: {
  lunchEnabled: boolean;
  splitTime: string;
  lunchStart: string;
  lunchEnd: string;
}) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const splitRef = useRef<HTMLDivElement | null>(null);
  const bandRef = useRef<HTMLDivElement | null>(null);

  // Drive the wrapper height to whichever child is active. We measure on every relevant
  // change (toggle, time edits, week-layout reflow via ResizeObserver) and write the px
  // height; the CSS transition on the wrapper eases the change. The inactive child is
  // faded out (CSS, keyed off data-lunch) and ignored for height.
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const measure = () => {
      const activeEl = lunchEnabled ? bandRef.current : splitRef.current;
      if (!activeEl) return;
      wrap.style.height = `${activeEl.scrollHeight}px`;
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (splitRef.current) ro.observe(splitRef.current);
    if (bandRef.current) ro.observe(bandRef.current);
    return () => ro.disconnect();
  }, [lunchEnabled, splitTime, lunchStart, lunchEnd]);

  return (
    <div
      ref={wrapRef}
      className="planner-divider-slot"
      data-lunch={lunchEnabled ? 'true' : undefined}
      aria-hidden="true"
    >
      {/* Single split — present always; faded out + collapsed (height ignored) when lunch on. */}
      <div ref={splitRef} className="planner-divider-state planner-divider-split">
        <div className="planner-split-row">
          <span className="planner-split-time tabular-nums">{formatSplitTime(splitTime)}</span>
        </div>
      </div>
      {/* Band — present always; faded out when lunch off. The hatch fill crossfades via CSS. */}
      <div ref={bandRef} className="planner-divider-state planner-divider-band">
        <div className="planner-split-band">
          <div className="planner-split-row">
            <span className="planner-split-time tabular-nums">{formatSplitTime(lunchStart)}</span>
          </div>
          <div className="planner-break-fill" />
          <div className="planner-split-row">
            <span className="planner-split-time tabular-nums">{formatSplitTime(lunchEnd)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Render the split time cleanly. settings.am_pm_split is 'HH:MM' (e.g. '12:00');
// trim any stray seconds and guard a malformed value back to a sane default.
function formatSplitTime(raw: string): string {
  const m = /^(\d{1,2}):(\d{2})/.exec(raw ?? '');
  if (!m) return '12:00';
  return `${m[1].padStart(2, '0')}:${m[2]}`;
}

// One row in a lane's UNIFIED render order (events + tasks merged by position). The
// kind discriminates the node builder; `position` is the unified-space sort key.
type LaneRow =
  | { kind: 'event'; sortId: string; position: number; event: NormalizedEvent }
  | { kind: 'task'; sortId: string; position: number; task: PlanItem };

// ---- lane body: builds the meeting anchors + task cards for HalfLane ---------
function LaneBody({
  day, weekday, half, rows, tasks, taskByKey, tz, overLane, sortIds, dropLineIndex, calendarStatus, labelForSource, onMoveNext, onOpenDetail, isWeeklyGoalKey, onToggleHighlight, onToggleComplete,
}: {
  day: string;
  weekday: Weekday;
  half: Half;
  // UNIFIED render order: events + tasks already merged + position-sorted upstream.
  rows: LaneRow[];
  // The lane's task placements (still passed for the empty-state check below).
  tasks: PlanItem[];
  taskByKey: Map<string, NormalizedTask>;
  tz: string;
  overLane: string | null;
  sortIds: string[];
  dropLineIndex: number | null;
  calendarStatus: 'loading' | 'connected' | 'disconnected';
  // Human label per source id (from the /api/cockpit/sources response; id fallback).
  labelForSource: (source: string) => string;
  onMoveNext: (it: PlanItem) => void;
  onOpenDetail: (d: CardDetail) => void;
  // Iris 20: a placed task that is a weekly goal renders as a teal HIGHLIGHT; the Star
  // toggles its weekly-goal membership (POST/DELETE via PlannerView's toggleWeeklyGoal).
  isWeeklyGoalKey: (key: string) => boolean;
  onToggleHighlight: (source: string, taskId: string) => void;
  // Iris 20 §7: the leading complete check fires this with the placed item (the LOCAL
  // completion POST). Source-done cards disable the check inside PlanCard (read-only).
  onToggleComplete: (it: PlanItem) => void;
}) {
  // Build the render items in the UNIFIED order handed down (events + tasks interleaved
  // by position) — NOT meetings-first. Each row becomes a MeetingAnchor or a
  // SortableTaskCard; the sortId order matches `sortIds` exactly (both come from the
  // same upstream merge), so dnd-kit's sortable list and the DOM agree.
  const items: LaneRenderItem[] = rows.map((row) => {
    if (row.kind === 'event') {
      const e = row.event;
      return {
        sortId: row.sortId,
        node: (
          <MeetingAnchor
            id={eventKey(e.uid)}
            title={e.title}
            meta={eventTimeLabel(e, tz)}
            onOpenDetail={() => onOpenDetail({ kind: 'event', event: e, tz })}
          />
        ),
      };
    }
    const it = row.task;
    const key = taskKey(it.source, it.externalTaskId);
    const t = taskByKey.get(key);
    // Reconciled 'done'/'stale' cards read faded + calm (never red). Iris 20 §7: a
    // LOCALLY-completed card (status still 'live', completedLocal:true) gets the same
    // calm mute — the spec-18 done treatment now also covers local completion.
    const faded = it.status === 'done' || it.status === 'stale' || !!it.completedLocal;

    // A placement whose source task no longer resolves must NEVER render as a bare
    // "(task)". Recovery order: (1) the live task title; (2) a last-known title the
    // server carried in `note`; (3) a calm "Task no longer in <Source>" — explains
    // why the row is empty without an alarm. The card de-emphasises (faded) so a
    // dropped/orphaned row reads as residue, not a problem to fix right now.
    const sourceLabel = labelForSource(it.source);
    const resolved = t?.title ?? (it.note && it.note.trim() ? it.note.trim() : null);
    const unresolved = !resolved;
    const title = resolved ?? `Task no longer in ${sourceLabel}`;
    const meta = t
      ? taskMetaLabel(t)
      : it.status === 'stale'
        ? 'check source'
        : it.status === 'done'
          ? 'done'
          : unresolved
            ? 'removed at source'
            : null;
    return {
      sortId: key,
      node: (
        <SortableTaskCard
          id={key}
          title={title}
          meta={meta}
          glyphSource={it.source}
          // Iris 20 §1/§3: a placed weekly goal IS a highlight of its day (teal). The Star
          // promotes/demotes; in focus-mode only these highlights (+ meetings) render.
          isHighlight={isWeeklyGoalKey(key)}
          onToggleHighlight={() => onToggleHighlight(it.source, it.externalTaskId)}
          // Iris 20 §7: the LOCAL completion flag + the toggle. status==='done' (source-
          // done) is derived sticky/read-only inside PlanCard; this is the toggleable
          // local kind. sourceLabel feeds the sticky-source-done "reopen at {source}" tip.
          completedLocal={it.completedLocal}
          onToggleComplete={() => onToggleComplete(it)}
          sourceLabel={sourceLabel}
          faded={faded || unresolved}
          // Iris spec 18: stamp the reconciliation status so DONE gets the check + strike
          // (live = normal, stale = the existing fade-only). It.status is 'live'|'done'|'stale'.
          status={it.status}
          onOpenDetail={() => onOpenDetail({
            kind: 'task',
            task: t ?? null,
            lastKnownTitle: it.note && it.note.trim() ? it.note.trim() : null,
            note: it.note,
            reconStatus: it.status,
            sourceLabel,
          })}
          moveNext={{ label: `Move ${title} to the next day`, onClick: () => onMoveNext(it) }}
        />
      ),
    };
  });

  // H3: the empty-lane treatment depends on the THREE calendar states.
  //   • loading      → render nothing (no warning, no skeleton flash) while the feed
  //                    is in flight; the lane fills in when the data settles ~1s later.
  //   • connected    → a connected feed with no meetings in THIS half is simply empty
  //                    (the calm "nothing scheduled" reading) — never a warning.
  //   • disconnected → the ONLY state that shows "No calendar connected." and only
  //                    once per column (the AM lane), only when no tasks fill it.
  // When tasks already occupy the lane, there is nothing to say at all.
  const empty = tasks.length > 0
    ? null
    : calendarStatus === 'disconnected' && half === 'AM' && day
      ? <p className="px-xs py-sm text-caption text-fg-subtle">No calendar connected.</p>
      : null;

  const isDropTarget = overLane === `lane:${weekday}:${half}`;

  return (
    <HalfLane
      weekday={weekday}
      half={half}
      day={day}
      items={items}
      sortIds={sortIds}
      dropLineIndex={dropLineIndex}
      isDropTarget={isDropTarget}
      empty={empty}
    />
  );
}

// ---- calm not-connected source notices (data-driven, tool-blind) ------------
// One quiet notice per source group that is ok:false (label + reason), in response
// order — never an error, never a tool hardcode. The calendar status line keeps
// its three-state lineage (H3): loading = "syncing" (calm, not "not connected");
// only a settled disconnect reads "not connected."
function SourceNotices({
  sources, calendarStatus,
}: {
  sources: SourceGroup[];
  calendarStatus: 'loading' | 'connected' | 'disconnected';
}) {
  const okLabels = sources.filter((g) => g.ok).map((g) => g.label);
  const degraded = sources.filter((g) => !g.ok);
  const meetingsPhrase =
    calendarStatus === 'connected' ? 'live from your calendar'
      : calendarStatus === 'loading' ? 'syncing'
        : 'not connected';
  return (
    <div className="mt-auto flex flex-col gap-xs pt-md">
      {degraded.map((g) => (
        <p key={g.source} className="text-caption text-fg-subtle">
          {g.label}: {g.reason ?? 'unavailable'} — its tasks will return when it reconnects.
        </p>
      ))}
      <p className="text-caption text-fg-subtle">
        Tasks are live from {okLabels.join(' + ') || 'your sources'} ·
        meetings {meetingsPhrase} · read-only.
        Your plan layout is saved separately.
      </p>
    </div>
  );
}

// ---- tiny helpers -----------------------------------------------------------
function ordinalOf(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] ?? s[v] ?? s[0]);
}
