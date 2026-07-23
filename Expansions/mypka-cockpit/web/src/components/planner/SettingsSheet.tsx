// SettingsSheet.tsx — the gear-opened work-hours panel (shadcn `sheet` anatomy,
// MCP-cited in Felix 02 §5). Side="right". Token-styled via Iris's .settings-panel /
// .settings-panel-scrim. Persists via PUT /api/planner/settings with a graceful
// localStorage fallback when the write path is dormant (usePlannerSettings).
//
// MOTION (Vivi 03 §2.8): open = `sheet-in` (translateX in + fade, ~400ms spirit,
// springOpen family), close = `sheet-out` (translateX out + fade, 300ms, brisk —
// 25% rule). We DELIBERATELY do NOT use Tailwind's `animate-in`/`slide-in` (Felix's
// contract + GL-003 §6.6 ban on Tailwind transitions for Sheet/Dialog). Exit runs
// before unmount via a closing flag. prefers-reduced-motion: the global index.css
// collapse neutralises the slide to a fade automatically.
//
// a11y: role=dialog, aria-modal, labelled title, focus trap, Esc + scrim-click to
// close, body scroll-lock, focus returns to the gear button on close.

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Settings } from 'lucide-react';
import type { PlannerSettings } from '../../lib/plannerTypes';
import { WEEKDAY_FULL, WEEKDAY_LABELS, DEFAULT_DAY_HOURS } from '../../lib/plannerLogic';

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])';

// Add one hour to an 'HH:MM' (clamped to 23:59) — used to keep lunch end strictly
// after start when the user drags start past it, so the PUT never round-trips a
// same/earlier end (the server rejects end <= start with a 400).
function bumpHour(hhmm: string): string {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm);
  if (!m) return hhmm;
  const mins = Math.min(Number(m[1]) * 60 + Number(m[2]) + 60, 23 * 60 + 59);
  const h = Math.floor(mins / 60);
  const mm = mins % 60;
  return `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

export function SettingsSheet({
  open, onClose, settings, onSave, writeDisabled,
}: {
  open: boolean;
  onClose: () => void;
  settings: PlannerSettings;
  onSave: (next: PlannerSettings) => void;
  writeDisabled: boolean;
}) {
  // Keep the panel mounted through its close animation, then unmount.
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
      const t = window.setTimeout(() => setMounted(false), 320); // ≥ sheet-out 300ms
      return () => window.clearTimeout(t);
    }
  }, [open, mounted]);

  // Focus management + scroll lock while open.
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

  if (!mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-50" onKeyDown={onKeyDown}>
      {/* Scrim — Iris's .settings-panel-scrim; opacity fade stays even under reduce. */}
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
        className={`absolute inset-y-0 right-0 z-40 h-full outline-none ${
          closing ? 'animate-sheet-out' : 'animate-sheet-in'
        }`}
      >
        <div className="settings-panel h-full overflow-y-auto">
          <div className="flex items-start justify-between gap-md">
            <div className="flex items-center gap-sm">
              <span className="text-marker-text" aria-hidden="true">
                <Settings size={18} strokeWidth={1.5} />
              </span>
              <h2 id={titleId} className="text-h3 font-[520] leading-snug text-fg">
                Planning settings
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close settings"
              className="-mr-xs -mt-xs shrink-0 rounded-card p-xs text-fg-muted transition-colors hover:bg-surface-3 hover:text-fg"
            >
              <X size={18} strokeWidth={1.5} aria-hidden="true" />
            </button>
          </div>

          <SettingsForm settings={settings} onSave={onSave} />

          {writeDisabled && (
            <p className="text-caption leading-relaxed text-fg-subtle">
              Planning is read-only until enabled. Your settings are saved on this
              device and will sync once the write path is turned on.
            </p>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

// ---- the form ---------------------------------------------------------------

function SettingsForm({
  settings, onSave,
}: {
  settings: PlannerSettings;
  onSave: (next: PlannerSettings) => void;
}) {
  // Edit a local draft; commit on each change so the board reflects it live.
  const commit = (next: PlannerSettings) => onSave(next);

  const toggleWorkday = (wd: number) => {
    const has = settings.workdays.includes(wd);
    const workdays = has
      ? settings.workdays.filter((d) => d !== wd)
      : [...settings.workdays, wd].sort((a, b) => a - b);
    // Ensure newly-enabled workdays have hours (fall back to the default window).
    const work_hours = { ...settings.work_hours };
    if (!has && !work_hours[String(wd)]) work_hours[String(wd)] = { ...DEFAULT_DAY_HOURS };
    commit({ ...settings, workdays, work_hours });
  };

  const setSplit = (am_pm_split: string) => commit({ ...settings, am_pm_split });

  // Iris 14 §B — lunch-break band edits. The band defaults disabled; toggling on
  // reveals the start/end times. We commit on each change so the divider/band updates
  // live (the board re-reads settings). The server validates HH:MM + end > start; the
  // time inputs only emit valid HH:MM, and we clamp end past start below so a same/
  // earlier end never round-trips to a 400.
  const lunch = settings.lunch_break;
  const setLunch = (next: Partial<typeof lunch>) =>
    commit({ ...settings, lunch_break: { ...lunch, ...next } });
  const toggleLunch = () => setLunch({ enabled: !lunch.enabled });
  const setLunchStart = (start: string) => {
    // Keep end strictly after start (server rejects end <= start). Bump end to
    // start + 1h when the new start would meet/overtake it.
    const end = start >= lunch.end ? bumpHour(start) : lunch.end;
    setLunch({ start, end });
  };
  const setLunchEnd = (end: string) => {
    if (end <= lunch.start) return; // ignore an invalid end; the input keeps its value
    setLunch({ end });
  };

  // READ-ONLY CONTRACT (this install, 2026-06-11): the upstream "Complete on source"
  // toggle (Iris 20 §7 layer B — write done back to Todoist/ClickUp) is REMOVED. The
  // server's source-write path no longer exists (see server/plannerRoutes.js), so the
  // toggle would arm nothing; surfacing it would promise an edit the cockpit refuses
  // to make. Completing a task for real happens in the source tool via the card's
  // url deep link. complete_on_source stays in the settings payload (server column
  // exists) but is never surfaced and stays false.

  const setHours = (wd: number, field: 'start' | 'end', value: string) => {
    const cur = settings.work_hours[String(wd)] ?? { ...DEFAULT_DAY_HOURS };
    commit({
      ...settings,
      work_hours: { ...settings.work_hours, [String(wd)]: { ...cur, [field]: value } },
    });
  };

  return (
    <div className="flex flex-col gap-lg">
      {/* Workdays */}
      <fieldset className="flex flex-col gap-sm">
        <legend className="text-meta font-[460] text-fg">Workdays</legend>
        <div role="group" aria-label="Workdays" className="flex flex-wrap gap-xs">
          {WEEKDAY_LABELS.map((label, wd) => {
            const active = settings.workdays.includes(wd);
            return (
              <button
                key={label}
                type="button"
                aria-pressed={active}
                onClick={() => toggleWorkday(wd)}
                className={`inline-flex h-[34px] min-w-[44px] items-center justify-center rounded-card border px-sm text-meta font-[460] transition-colors ${
                  active
                    ? 'border-transparent bg-marker-soft text-marker-text'
                    : 'border-border bg-surface-bg text-fg-subtle hover:bg-surface-2 hover:text-fg'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </fieldset>

      {/* AM/PM split */}
      <div className="flex flex-col gap-sm">
        <label htmlFor="planner-split" className="text-meta font-[460] text-fg">
          AM / PM split point
        </label>
        <input
          id="planner-split"
          type="time"
          value={settings.am_pm_split}
          onChange={(e) => setSplit(e.target.value)}
          className="w-[140px] rounded-card border border-border bg-surface-bg px-sm py-xs text-meta tabular-nums text-fg outline-none focus-visible:border-marker"
        />
        <p className="text-caption text-fg-subtle">
          Meetings before this time go to the morning lane; after, the afternoon.
        </p>
      </div>

      {/* Lunch break (Iris 14 §B) — a toggle + start/end times. When on, the board's
          single AM/PM divider grows into a band with a blocked-time hatch between the
          two times. Disabled by default; the times only matter when enabled. */}
      <fieldset className="flex flex-col gap-sm">
        <div className="flex items-center justify-between gap-md">
          <legend className="text-meta font-[460] text-fg">Lunch break</legend>
          <button
            type="button"
            role="switch"
            aria-checked={lunch.enabled}
            aria-label="Enable lunch break"
            onClick={toggleLunch}
            className={`relative inline-flex h-[22px] w-[38px] shrink-0 items-center rounded-full border transition-colors ${
              lunch.enabled
                ? 'border-transparent bg-marker-soft'
                : 'border-border bg-surface-bg hover:bg-surface-2'
            }`}
          >
            <span
              aria-hidden="true"
              className={`inline-block h-[16px] w-[16px] rounded-full transition-transform ${
                lunch.enabled ? 'translate-x-[18px] bg-marker' : 'translate-x-[3px] bg-fg-subtle'
              }`}
            />
          </button>
        </div>
        {lunch.enabled && (
          <div className="flex items-center gap-sm">
            <input
              type="time"
              aria-label="Lunch break start"
              value={lunch.start}
              onChange={(e) => setLunchStart(e.target.value)}
              className="w-[110px] rounded-card border border-border bg-surface-bg px-sm py-xs text-meta tabular-nums text-fg outline-none focus-visible:border-marker"
            />
            <span aria-hidden="true" className="text-fg-subtle">–</span>
            <input
              type="time"
              aria-label="Lunch break end"
              value={lunch.end}
              onChange={(e) => setLunchEnd(e.target.value)}
              className="w-[110px] rounded-card border border-border bg-surface-bg px-sm py-xs text-meta tabular-nums text-fg outline-none focus-visible:border-marker"
            />
          </div>
        )}
        <p className="text-caption text-fg-subtle">
          {lunch.enabled
            ? 'A blocked-time band marks lunch between the AM and PM lanes.'
            : 'Off: a single line divides morning and afternoon.'}
        </p>
      </fieldset>

      {/* "Complete on source" toggle REMOVED (read-only contract, 2026-06-11):
          completing a task here is always planner-local; the source tools are never
          written. Real completion happens in Todoist/ClickUp via the card's url
          deep link (CardDetailModal "Open in <tool>"). */}

      {/* Per-workday hours */}
      <fieldset className="flex flex-col gap-sm">
        <legend className="text-meta font-[460] text-fg">Work hours</legend>
        <div className="flex flex-col gap-xs">
          {WEEKDAY_LABELS.map((label, wd) => {
            if (!settings.workdays.includes(wd)) return null;
            const hours = settings.work_hours[String(wd)] ?? DEFAULT_DAY_HOURS;
            return (
              <div key={label} className="flex items-center gap-sm">
                <span className="w-[36px] text-meta text-fg-muted">{label}</span>
                <input
                  type="time"
                  aria-label={`${WEEKDAY_FULL[wd]} start`}
                  value={hours.start}
                  onChange={(e) => setHours(wd, 'start', e.target.value)}
                  className="w-[110px] rounded-card border border-border bg-surface-bg px-sm py-xs text-meta tabular-nums text-fg outline-none focus-visible:border-marker"
                />
                <span aria-hidden="true" className="text-fg-subtle">–</span>
                <input
                  type="time"
                  aria-label={`${WEEKDAY_FULL[wd]} end`}
                  value={hours.end}
                  onChange={(e) => setHours(wd, 'end', e.target.value)}
                  className="w-[110px] rounded-card border border-border bg-surface-bg px-sm py-xs text-meta tabular-nums text-fg outline-none focus-visible:border-marker"
                />
              </div>
            );
          })}
        </div>
      </fieldset>
    </div>
  );
}
