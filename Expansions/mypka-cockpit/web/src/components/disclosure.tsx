// disclosure.tsx — accessible disclosure primitives (Sheet, Dialog, Collapsible).
//
// Built from the shadcn/Radix anatomy (shadcn.io MCP: get_component "sheet" +
// "collapsible") — same data-state model, same trigger/overlay/content structure,
// same focus + Escape + scroll-lock contract — but styled with GL-003 tokens and
// implemented with ZERO new npm dependencies. The canonical shadcn primitives
// assume Tailwind v4 token names (bg-background), `@/lib/utils` cn(), and Radix;
// none of which this Vite + Tailwind v3 + GL-003 codebase ships. So we mirror the
// behaviour, not the package. (Same call the README documents for FadeTruncate.)
//
// Accessibility: role=dialog, aria-modal, labelled title, focus trap, Escape to
// close, click-scrim to close, body scroll-lock, focus returned to the opener.
// Motion: Tailwind keyframes whose easing came from Motion Studio MCP (see config).
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react';
import { createPortal } from 'react-dom';
import { X, ChevronDown, Maximize2 } from 'lucide-react';

// ---- focus-trap + scroll-lock shared by Sheet and Dialog --------------------

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])';

function useOverlay(open: boolean, onClose: () => void) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  // Remember who opened it, lock scroll, focus the panel; restore on close.
  useEffect(() => {
    if (!open) return;
    openerRef.current = (document.activeElement as HTMLElement) ?? null;
    document.body.classList.add('overlay-open');

    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    return () => {
      document.body.classList.remove('overlay-open');
      openerRef.current?.focus?.();
    };
  }, [open]);

  const onKeyDown = useCallback(
    (e: ReactKeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const panel = panelRef.current;
      if (!panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null
      );
      if (items.length === 0) {
        e.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    },
    [onClose]
  );

  return { panelRef, onKeyDown };
}

// ---- Sheet (right-side panel) -----------------------------------------------

export function Sheet({
  open,
  onClose,
  title,
  subtitle,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const { panelRef, onKeyDown } = useOverlay(open, onClose);
  const titleId = useId();
  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50" onKeyDown={onKeyDown}>
      <div
        className="absolute inset-0 animate-overlay-in bg-[var(--scrim)]"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="absolute inset-y-0 right-0 flex h-full w-full max-w-[min(36rem,92vw)] animate-sheet-in flex-col border-l border-border bg-surface-2 shadow-[-8px_0_40px_var(--shadow-strong-color)] outline-none"
      >
        <SheetHeader id={titleId} title={title} subtitle={subtitle} onClose={onClose} />
        <div className="prose-readable min-h-0 flex-1 overflow-y-auto px-lg py-md text-body text-fg-muted">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}

function SheetHeader({
  id,
  title,
  subtitle,
  onClose,
}: {
  id: string;
  title: string;
  subtitle?: string;
  onClose: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-md border-b border-border-subtle px-lg py-md">
      <div className="min-w-0">
        <h2 id={id} className="text-h3 font-[520] leading-snug text-fg">
          {title}
        </h2>
        {subtitle && <p className="mt-[2px] text-caption text-fg-subtle">{subtitle}</p>}
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close"
        className="-mr-xs -mt-xs shrink-0 rounded-card p-xs text-fg-muted transition-colors hover:bg-surface-3 hover:text-fg"
      >
        <X size={18} strokeWidth={1.5} aria-hidden="true" />
      </button>
    </div>
  );
}

// ---- Dialog (centered modal) ------------------------------------------------

export function Dialog({
  open,
  onClose,
  title,
  subtitle,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const { panelRef, onKeyDown } = useOverlay(open, onClose);
  const titleId = useId();
  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-md" onKeyDown={onKeyDown}>
      <div
        className="absolute inset-0 animate-overlay-in bg-[var(--scrim)]"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative flex max-h-[86vh] w-full max-w-[min(40rem,94vw)] animate-dialog-in flex-col rounded-hero border border-border bg-surface-3 shadow-[0_24px_60px_var(--shadow-strong-color)] outline-none"
      >
        <SheetHeader id={titleId} title={title} subtitle={subtitle} onClose={onClose} />
        <div className="prose-readable min-h-0 flex-1 overflow-y-auto px-lg py-md text-body text-fg-muted">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}

// ---- Collapsible (section with quick-stats when collapsed) ------------------
// Mirrors Radix Collapsible: a trigger toggles a content region; the trigger keeps
// aria-expanded + aria-controls; the content keeps role=region. Height animates via
// a measured CSS var so it can animate height:auto (Motion Codex "accordion" pattern).

export function Collapsible({
  open,
  onToggle,
  summary,
  children,
  id,
}: {
  open: boolean;
  onToggle: () => void;
  summary: ReactNode; // the quick-stats line shown when collapsed (and as a sub-line when open)
  children: ReactNode;
  id?: string;
}) {
  const reactId = useId();
  const regionId = id ?? reactId;
  const contentRef = useRef<HTMLDivElement | null>(null);
  const innerRef = useRef<HTMLDivElement | null>(null);
  const [maxH, setMaxH] = useState<string>(open ? 'none' : '0px');
  const firstRender = useRef(true);

  // Measure the inner height and drive a max-height transition (height:auto is
  // not animatable; max-height to the measured value is the canonical workaround).
  useEffect(() => {
    const inner = innerRef.current;
    if (!inner) return;
    if (firstRender.current) {
      // No open/close animation on the very first paint — just set the end state.
      firstRender.current = false;
      setMaxH(open ? 'none' : '0px');
      return;
    }
    if (open) {
      const h = inner.scrollHeight;
      setMaxH(`${h}px`);
      // After the transition, release to `none` so nested content can grow.
      const t = window.setTimeout(() => setMaxH('none'), 300);
      return () => window.clearTimeout(t);
    } else {
      // From `none` we must first pin to a pixel height, then collapse to 0.
      const h = inner.scrollHeight;
      setMaxH(`${h}px`);
      // Force a reflow frame so the browser registers the start height.
      requestAnimationFrame(() => requestAnimationFrame(() => setMaxH('0px')));
    }
  }, [open]);

  return (
    <div>
      {/* Trigger row: chevron + the section is rendered by the caller as the
          SectionHeader; here we only need the toggle button to wrap it. */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={regionId}
        className="group flex w-full items-center gap-sm rounded-panel px-xs py-xs text-left transition-colors hover:bg-surface-1/60 focus-visible:bg-surface-1/60"
      >
        <ChevronDown
          size={18}
          strokeWidth={1.5}
          aria-hidden="true"
          className={`shrink-0 text-fg-muted transition-transform duration-200 ${open ? '' : '-rotate-90'}`}
        />
        <div className="min-w-0 flex-1">{summary}</div>
      </button>

      <div
        ref={contentRef}
        id={regionId}
        role="region"
        hidden={!open && maxH === '0px'}
        style={{
          maxHeight: maxH,
          overflow: maxH === 'none' ? 'visible' : 'hidden',
          // Felix (Vivi motion audit B1, 2026-06-03): the SHARED collapse primitive — every
          // Section/disclosure consumer (Mind/Dashboard/Tracking/Actions/SocialReview) plus
          // A2 (source-group) and B2 (chat-artifact diff) route through this ONE box, so the
          // standardized curve+timing applies app-wide from here. Aligned to the audit §0
          // tokens: --ease-collapse (overshoot-free decelerate) on both, but CLOSE is faster
          // than OPEN (durCollapse 260/220), and opacity is asymmetric — it LEADS on exit
          // (content gone before the gap shuts) and TRAILS on enter (space opens, then content
          // fades up). These literals fall back if the var is unset; the values match the
          // tokens added to index.css. CSS-only → reduced-motion neutralised globally.
          transition: open
            ? 'max-height var(--dur-collapse-open, 260ms) var(--ease-collapse, cubic-bezier(0.22,1,0.36,1)), opacity 200ms ease-out 40ms'
            : 'max-height var(--dur-collapse-close, 220ms) var(--ease-collapse, cubic-bezier(0.22,1,0.36,1)), opacity 140ms ease-out',
          opacity: open ? 1 : 0,
        }}
      >
        <div ref={innerRef} className="pt-sm">
          {children}
        </div>
      </div>
    </div>
  );
}

// ---- CollapseRows (measurement-free height:auto collapse) -------------------
// Felix (Vivi motion audit B2, 2026-06-03): a sibling to <Collapsible> for cases where
// the body's height isn't known up front and can grow AFTER mount (async-loaded content,
// virtualized lists) — there the measured-max-height <Collapsible> would pin too short.
// Uses the modern grid-template-rows 0fr↔1fr technique: a 1-row grid whose track animates,
// inner overflow:hidden. No JS measurement, so it tracks late-arriving content for free.
// Shares the one calm --ease-collapse curve (close faster than open). The caller owns the
// trigger + aria; this only animates the region. Keeps children mounted through the exit
// animation, then unmounts on transitionend so collapsed bodies hold no fetch/render cost.
// CSS-only transition → reduced-motion neutralised by the global index.css block.
export function CollapseRows({
  open,
  id,
  children,
}: {
  open: boolean;
  id?: string;
  children: ReactNode;
}) {
  const [mounted, setMounted] = useState(open);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open) { setMounted(true); return; }
    const el = wrapRef.current;
    if (!el) { setMounted(false); return; }
    let done = false;
    const finish = () => { if (done) return; done = true; setMounted(false); };
    const onEnd = (e: TransitionEvent) => {
      if (e.target === el && e.propertyName === 'grid-template-rows') finish();
    };
    el.addEventListener('transitionend', onEnd);
    const t = window.setTimeout(finish, 320); // safety net if no transitionend fires
    return () => { el.removeEventListener('transitionend', onEnd); window.clearTimeout(t); };
  }, [open]);

  return (
    <div
      ref={wrapRef}
      id={id}
      role="region"
      className="collapse-rows"
      data-open={open ? 'true' : undefined}
      hidden={!open && !mounted}
    >
      <div className="collapse-rows-inner">
        {mounted && children}
      </div>
    </div>
  );
}

// ---- ExpandableCard (truncated preview -> click opens the full text in a Sheet)
// The v2 contract: nothing is permanently cut. A card shows a short preview; the
// whole card is a button that opens a right-side Sheet with the FULL content.

export function ExpandableCard({
  title,
  preview,
  sheetTitle,
  sheetSubtitle,
  children,
  className = '',
  footer,
}: {
  title: ReactNode; // the card heading (stays visible)
  preview: ReactNode; // the truncated preview body
  sheetTitle: string;
  sheetSubtitle?: string;
  children: ReactNode; // FULL content rendered inside the Sheet
  className?: string;
  footer?: ReactNode; // optional small line under the preview (e.g. a date)
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <article
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen(true);
          }
        }}
        className={`disclosure-card group relative flex flex-col gap-xs rounded-panel border border-border bg-surface-1 p-md ${className}`}
      >
        <div className="flex items-start justify-between gap-sm">
          <div className="min-w-0 flex-1">{title}</div>
          <Maximize2
            size={14}
            strokeWidth={1.5}
            aria-hidden="true"
            className="mt-[2px] shrink-0 text-fg-subtle transition-colors group-hover:text-marker-text"
          />
        </div>
        {preview}
        {footer}
        <span className="mt-auto pt-xs text-caption text-marker-text opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
          Read full text →
        </span>
      </article>
      <Sheet open={open} onClose={() => setOpen(false)} title={sheetTitle} subtitle={sheetSubtitle}>
        {children}
      </Sheet>
    </>
  );
}
