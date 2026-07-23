// CardDetailModal.tsx — the click-a-card detail view. ONE centered dialog renders
// BOTH a task and a meeting/event detail, and is the SINGLE home for the "open in
// source" affordance (which used to live inline on the card; moved here per Tom's
// request so the card body is purely a click-target + drag-activator and carries no
// nested interactive control).
//
// WHY a centered modal (not a side sheet): a detail read is a focal, transient act —
// a centered dialog reads calmer for "here is everything about this one card" than an
// edge-anchored drawer. It reuses the SettingsSheet anatomy verbatim (portal, scrim,
// focus trap, Esc + scrim-click close, scroll-lock, focus-return) and the EXACT Iris
// surface tokens (.detail-modal mirrors .settings-panel: --settings-panel-bg/-border/
// -radius/-pad; scrim is the same .settings-panel-scrim element).
//
// MOTION (Vivi 03 §2.8): open = `dialog-in` (springOpen ~6.6% overshoot, MCP-cited in
// tailwind.config keyframes), close = `dialog-out` (brisk ease-out, 300ms, 25% rule).
// The global prefers-reduced-motion collapse in index.css neutralises both to a static
// state; the scrim's opacity fade stays (it's the only motion under reduce).
//
// a11y: role=dialog, aria-modal, labelled by the title, focus trap, Esc + scrim-click
// to close, body scroll-lock, focus returns to the CARD that opened it (the opener
// captured at mount via document.activeElement — Enter on a focused card → opener is
// that card → focus returns there on close).

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  X, ArrowUpRight, CalendarClock, CheckSquare, Briefcase, MapPin, Repeat, Tag,
} from 'lucide-react';
import { StatusChip } from '../ui';
import type { NormalizedTask, NormalizedEvent, PlanCardStatus } from '../../lib/plannerTypes';

// The detail payload — a discriminated union over the two card kinds. Scheduled task
// cards carry the reconciliation extras (note + status); sidebar tasks pass them null.
export type CardDetail =
  | {
      kind: 'task';
      task: NormalizedTask | null;   // null when the source task no longer resolves
      // last-known title carried by the server when the live task is gone (stale/done)
      lastKnownTitle: string | null;
      note: string | null;
      reconStatus: PlanCardStatus | null;  // 'live' | 'done' | 'stale' | null (sidebar)
      sourceLabel: string;           // 'Todoist' | 'ClickUp'
    }
  | { kind: 'event'; event: NormalizedEvent; tz: string };

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])';

// open in a new tab, http(s) only, rel=noopener (matches PlannerView.openUrl posture).
function safeHref(url: string | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.protocol === 'https:' || u.protocol === 'http:' ? u.toString() : null;
  } catch {
    return null;
  }
}

const DUE_BUCKET_LABEL: Record<NonNullable<NormalizedTask['dueBucket']>, string> = {
  overdue: 'Overdue',
  today: 'Today',
  upcoming: 'Upcoming',
  none: 'No due date',
};

const PRIORITY_LABEL: Record<number, string> = {
  1: 'P1 · important',
  2: 'P2',
  3: 'P3',
  4: 'P4',
  5: 'None',
};

export function CardDetailModal({
  open, detail, onClose,
}: {
  open: boolean;
  detail: CardDetail | null;
  onClose: () => void;
}) {
  // Keep mounted through the close animation, then unmount (same pattern as the sheet).
  const [mounted, setMounted] = useState(open);
  const [closing, setClosing] = useState(false);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const titleId = useId();

  useEffect(() => {
    if (open) {
      setMounted(true);
      setClosing(false);
    } else if (mounted) {
      setClosing(true);
      const t = window.setTimeout(() => setMounted(false), 320); // ≥ dialog-out 300ms
      return () => window.clearTimeout(t);
    }
  }, [open, mounted]);

  // Capture the opener (the card), trap focus, lock scroll while open; restore on close.
  useEffect(() => {
    if (!mounted || closing) return;
    openerRef.current = (document.activeElement as HTMLElement) ?? null;
    document.body.classList.add('overlay-open');
    const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panelRef.current)?.focus();
    return () => {
      document.body.classList.remove('overlay-open');
      openerRef.current?.focus?.();
    };
  }, [mounted, closing]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const panel = panelRef.current;
      if (!panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      );
      if (items.length === 0) {
        e.preventDefault();
        return;
      }
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      const active = document.activeElement as HTMLElement;
      if (e.shiftKey && active === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && active === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    },
    [onClose],
  );

  if (!mounted || !detail) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-md" onKeyDown={onKeyDown}>
      {/* Reuse the EXACT settings scrim element/token; opacity fade survives reduce. */}
      <div
        className={`settings-panel-scrim ${closing ? '' : 'is-open'}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`relative z-40 outline-none ${closing ? 'animate-dialog-out' : 'animate-dialog-in'}`}
      >
        <div className="detail-modal">
          {detail.kind === 'task'
            ? <TaskDetail detail={detail} titleId={titleId} onClose={onClose} />
            : <EventDetail event={detail.event} tz={detail.tz} titleId={titleId} onClose={onClose} />}
        </div>
      </div>
    </div>,
    document.body,
  );
}

// ---- shared chrome ----------------------------------------------------------

function ModalHeader({
  titleId, title, glyph, onClose,
}: {
  titleId: string;
  title: string;
  glyph: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-md">
      <div className="flex items-start gap-sm">
        <span className="mt-[2px] text-marker-text" aria-hidden="true">{glyph}</span>
        {/* Full, UNtruncated title — the whole point of the detail view. */}
        <h2 id={titleId} className="text-h3 font-[520] leading-snug text-fg">{title}</h2>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close details"
        className="-mr-xs -mt-xs shrink-0 rounded-card p-xs text-fg-muted transition-colors hover:bg-surface-3 hover:text-fg"
      >
        <X size={18} strokeWidth={1.5} aria-hidden="true" />
      </button>
    </div>
  );
}

// One label/value row — calm two-column meta, --fg-muted label per the board's posture.
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-sm">
      <span className="w-[88px] shrink-0 text-caption text-fg-muted">{label}</span>
      <span className="text-meta text-fg">{children}</span>
    </div>
  );
}

// The task/event body. Rendered ONLY when non-empty (empty → the whole section is
// omitted, no orphan caption). Newlines are preserved (whitespace-pre-wrap) so
// ClickUp plaintext + Todoist light-markdown read as their authored shape; v1
// renders as PLAIN TEXT (no markdown dep). Long bodies break words and ride the
// modal's own `.detail-modal` max-height + overflow-y scroll, so a wall of notes
// never blows the modal up. Caption header mirrors the "Last known" section style.
function DescriptionBlock({ description }: { description: string }) {
  const body = description.trim();
  if (!body) return null;
  return (
    <div className="flex flex-col gap-xs">
      <span className="text-caption text-fg-muted">Notes</span>
      <p className="whitespace-pre-wrap break-words text-meta leading-relaxed text-fg-muted">
        {body}
      </p>
    </div>
  );
}

function SourceLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-xs rounded-card border border-border bg-surface-bg px-sm py-xs text-meta font-[460] text-fg transition-colors hover:border-marker hover:text-marker-text focus-visible:border-marker"
    >
      {label}
      <ArrowUpRight size={14} strokeWidth={1.5} aria-hidden="true" />
    </a>
  );
}

// ---- task detail ------------------------------------------------------------

function TaskDetail({
  detail, titleId, onClose,
}: {
  detail: Extract<CardDetail, { kind: 'task' }>;
  titleId: string;
  onClose: () => void;
}) {
  const { task, lastKnownTitle, note, reconStatus, sourceLabel } = detail;
  const resolved = task?.title ?? (lastKnownTitle && lastKnownTitle.trim() ? lastKnownTitle.trim() : null);
  const isStale = !task && reconStatus !== 'live';
  const title = resolved ?? `Task no longer in ${sourceLabel}`;
  const Glyph = sourceLabel === 'ClickUp' ? Briefcase : CheckSquare;
  const href = safeHref(task?.url ?? null);

  return (
    <>
      <ModalHeader
        titleId={titleId}
        title={title}
        glyph={<Glyph size={18} strokeWidth={1.5} />}
        onClose={onClose}
      />

      {/* Calm stale note — never red; explains why the row reads as residue. */}
      {isStale && (
        <p className="text-caption leading-relaxed text-fg-subtle">
          This card’s source task is no longer in {sourceLabel}
          {reconStatus === 'done' ? ' — it looks completed or closed.' : ' right now.'}
          {' '}It’s kept here as a quiet placeholder; nothing to fix.
        </p>
      )}

      <div className="flex flex-col gap-xs">
        <Row label="Source">{sourceLabel}</Row>
        {task && (
          <>
            <Row label="Due">
              <span className="tabular-nums">
                {task.due ? `${task.due} · ` : ''}
                {DUE_BUCKET_LABEL[task.dueBucket]}
              </span>
            </Row>
            <Row label="Priority">{PRIORITY_LABEL[task.priorityRank] ?? `P${task.priorityRank}`}</Row>
            {task.status && <Row label="Status">{task.status}</Row>}
          </>
        )}
        {reconStatus && (
          <Row label="On board">
            {reconStatus === 'live' ? (
              <StatusChip tone="good">live</StatusChip>
            ) : reconStatus === 'done' ? (
              <StatusChip tone="neutral">done</StatusChip>
            ) : (
              <StatusChip tone="watch">check source</StatusChip>
            )}
          </Row>
        )}
      </div>

      {/* Tags — only if present. */}
      {task && task.tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-fg-muted" aria-hidden="true">
            <Tag size={13} strokeWidth={1.5} />
          </span>
          {task.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-surface-2 px-sm py-[2px] text-caption text-fg-muted"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* The task body/notes — rendered under the meta as the context block. Omitted
          entirely when empty. */}
      {task && <DescriptionBlock description={task.description} />}

      {/* Last-known note for a stale card (the server-carried snapshot). */}
      {!task && note && note.trim() && (
        <div className="flex flex-col gap-xs">
          <span className="text-caption text-fg-muted">Last known</span>
          <p className="text-meta leading-relaxed text-fg-subtle">{note.trim()}</p>
        </div>
      )}

      {/* The external-source link — now lives HERE, not on the card. */}
      {href && <SourceLink href={href} label={`Open in ${sourceLabel}`} />}
    </>
  );
}

// ---- event / meeting detail -------------------------------------------------

function EventDetail({
  event, tz, titleId, onClose,
}: {
  event: NormalizedEvent;
  tz: string;            // display tz from planner settings (matches eventTimeLabel)
  titleId: string;
  onClose: () => void;
}) {
  const dateFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: tz, weekday: 'long', day: 'numeric', month: 'long',
  });
  const timeFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false,
  });
  const dateLabel = dateFmt.format(new Date(event.start));
  const timeLabel = event.allDay
    ? 'All day'
    : `${timeFmt.format(new Date(event.start))}–${timeFmt.format(new Date(event.end))}`;
  const href = safeHref(event.url);

  return (
    <>
      <ModalHeader
        titleId={titleId}
        title={event.title}
        glyph={<CalendarClock size={18} strokeWidth={1.5} />}
        onClose={onClose}
      />

      <div className="flex flex-col gap-xs">
        <Row label="Date">{dateLabel}</Row>
        <Row label="Time">
          <span className="tabular-nums">{timeLabel}</span>
          {!event.allDay && event.half && (
            <span className="text-fg-muted"> · {event.half}</span>
          )}
        </Row>
        {event.location && (
          <Row label="Location">
            <span className="inline-flex items-center gap-xs">
              <span className="text-fg-muted" aria-hidden="true">
                <MapPin size={13} strokeWidth={1.5} />
              </span>
              {event.location}
            </span>
          </Row>
        )}
        {event.recurring && (
          <Row label="Repeats">
            <span className="inline-flex items-center gap-xs text-fg-muted">
              <Repeat size={13} strokeWidth={1.5} aria-hidden="true" />
              Recurring event
            </span>
          </Row>
        )}
      </div>

      {/* The event body/notes from the VEVENT — under the meta, omitted when empty. */}
      <DescriptionBlock description={event.description} />

      {href && <SourceLink href={href} label="Open event" />}
    </>
  );
}
