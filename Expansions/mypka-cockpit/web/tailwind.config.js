/** @type {import('tailwindcss').Config} */
// Tailwind maps to GL-003 v5 INKLINE semantic tokens (CSS variables in index.css).
// No hardcoded hex / Tailwind palette colors anywhere in the app — tokens only.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // surface ladder
        'surface-bg': 'var(--surface-bg)',
        'surface-1': 'var(--surface-1)',
        'surface-2': 'var(--surface-2)',
        'surface-3': 'var(--surface-3)',
        border: 'var(--border)',
        'border-subtle': 'var(--border-subtle)',
        // foreground
        fg: 'var(--fg)',
        'fg-muted': 'var(--fg-muted)',
        'fg-subtle': 'var(--fg-subtle)',
        'border-emphasis': 'var(--border-emphasis)',
        // accent: the marker (GL-003 §2.1/§2.2). `marker` = fills, borders,
        // large-scale display, meaningful non-text. `marker-text` = small
        // marker TEXT (ruling A148: on paper it steps to #B93613 so small
        // strings clear the §2.8 4.5:1 floor; on ink both resolve the same).
        marker: 'var(--accent-marker)',
        'marker-text': 'var(--accent-marker-text)',
        'marker-soft': 'var(--accent-marker-soft)',
        'on-marker': 'var(--text-on-marker)',
        // status (§2.5: warning/success are STATES; quiet state text rides
        // the ink voice; identity rides the icon/glyph)
        success: 'var(--status-success)',
        'success-dot': 'var(--status-success-dot)',
        warning: 'var(--status-warning)',
        error: 'var(--status-error)',
        'error-text': 'var(--status-error-text)',
        info: 'var(--status-info)',
      },
      fontFamily: {
        // GL-003 §3.1 four roles, all self-hosted (@fontsource, see main.tsx)
        sans: ['"Instrument Sans Variable"', '"Instrument Sans"', 'system-ui', 'sans-serif'],
        display: ['"Bricolage Grotesque Variable"', '"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        mono: ['"Spline Sans Mono Variable"', '"Spline Sans Mono"', 'ui-monospace', 'monospace'],
        hand: ['"Caveat Variable"', 'Caveat', 'cursive'],
      },
      fontSize: {
        // GL-003 type scale (token-named, not raw tailwind text-sm/lg)
        caption: ['0.75rem', { lineHeight: '1.5' }],
        meta: ['0.8125rem', { lineHeight: '1.5' }],
        body: ['0.9375rem', { lineHeight: '1.5' }],
        h3: ['1.125rem', { lineHeight: '1.35' }],
        h2: ['1.5rem', { lineHeight: '1.25' }],
        h1: ['2rem', { lineHeight: '1.2' }],
        bignum: ['2.5rem', { lineHeight: '1.05' }],
      },
      spacing: {
        xs: '4px', sm: '8px', md: '16px', lg: '24px', xl: '32px', '2xl': '48px', '3xl': '64px',
      },
      borderRadius: {
        // GL-003 §5.2 corner ladder: 10 (chips/toasts/small wells) /
        // 16 (cards/panels/inputs) / 20 (modals/elevated sheets) / pill.
        card: '10px', panel: '16px', hero: '20px',
      },
      maxWidth: {
        page: '1100px',
      },
      keyframes: {
        'fade-rise': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // Sheet/Dialog overlay scrim — quiet fade, no movement.
        'overlay-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // Sheet panel slide-in from the right (GL-003 §6.2 sidepanel 400ms).
        'sheet-in': {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        // Dialog/Modal pop-in (GL-003 §6.2 modal 450ms, springOpen ~6.6% overshoot).
        'dialog-in': {
          '0%': { opacity: '0', transform: 'translateY(8px) scale(0.985)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        // Radix Collapsible height auto-animation (uses --radix-collapsible-* vars;
        // we mirror the pattern with a CSS var our own primitive sets).
        'collapse-down': {
          '0%': { height: '0', opacity: '0' },
          '100%': { height: 'var(--collapse-h)', opacity: '1' },
        },
        'collapse-up': {
          '0%': { height: 'var(--collapse-h)', opacity: '1' },
          '100%': { height: '0', opacity: '0' },
        },
        // Delta-arrow punctuate pop (GL-003 §6.1 springPunctuate ~5% overshoot).
        'delta-pop': {
          '0%': { opacity: '0', transform: 'translateY(2px) scale(0.9)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        // Planner Sheet close (Vivi 03 §2.8): translateX out, brisk (25% rule).
        'sheet-out': {
          '0%': { opacity: '1', transform: 'translateX(0)' },
          '100%': { opacity: '0', transform: 'translateX(16px)' },
        },
        // Centered Dialog close (Vivi 03 §2.8 close family, 25% rule — mirrors
        // `dialog-in` open as a brisk no-overshoot exit; pairs with the detail modal).
        'dialog-out': {
          '0%': { opacity: '1', transform: 'translateY(0) scale(1)' },
          '100%': { opacity: '0', transform: 'translateY(6px) scale(0.985)' },
        },
        // Felix (Vivi motion audit C1, 2026-06-03): portaled menu entrance — the
        // PriorityMenu used to appear instantly (no enter motion). Quick scale+lift from
        // the trigger edge: opacity 0→1, scale 0.98→1, translateY -4px→0. Compositor-only
        // (transform+opacity), no layout. origin top is set on the element. Per Vivi a
        // brisk ease-out is the calm choice (the §6.1 springSnappy alternative carried ~6%
        // overshoot — acceptable on a menu but ease-out reads calmer). Reduced-motion: the
        // global index.css block zeroes the duration → no scale/translate perceived.
        'menu-in': {
          '0%': { opacity: '0', transform: 'translateY(-4px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        // Planner low-time timer breath (Vivi 03 §2.7 `breathCalm`): a 2400ms
        // opacity loop, amplitude 0.18, NO scale / NO colour flash / NO red.
        // The cockpit "never turns red"; urgency is a slow breath, never an alarm.
        'breath-calm': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.82' },
        },
      },
      animation: {
        // springGentle-derived (no overshoot) — see motion notes in README.
        'fade-rise': 'fade-rise 420ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'fade-in': 'fade-in 280ms ease-out both',
        // Motion Studio MCP cited values (see README "Motion provenance"):
        //   overlay  -> simple ease fade (no spring needed for a scrim)
        //   sheet-in -> generate-css-spring bounce=0.15 dur=0.4 => 350ms linear(...)
        //   dialog-in-> springOpen family, same curve, slightly tighter
        //   delta-pop-> generate-css-spring bounce=0.05 dur=0.32 => 150ms linear(...)
        'overlay-in': 'overlay-in 200ms ease-out both',
        'sheet-in': 'sheet-in 350ms linear(0,0.3772,0.8604,1.0738,1.0846,1.0353,1.0006,0.991,0.9941,0.9985,1.0006,1) both',
        'dialog-in': 'dialog-in 350ms linear(0,0.3772,0.8604,1.0738,1.0846,1.0353,1.0006,0.991,0.9941,0.9985,1.0006,1) both',
        'collapse-down': 'collapse-down 260ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'collapse-up': 'collapse-up 200ms cubic-bezier(0.4, 0, 1, 1) both',
        'delta-pop': 'delta-pop 150ms linear(0,1.0502,0.9981,1,1) both',
        // C1 PriorityMenu entrance — brisk no-overshoot ease-out (Vivi audit §C1).
        'menu-in': 'menu-in 150ms ease-out both',
        // Planner Sheet close — `springClose`-equiv ease-out, brisk, no overshoot
        // (Vivi 03 §2.8: 300ms, ~25% faster than the 400ms-spirit `sheet-in` open).
        'sheet-out': 'sheet-out 300ms cubic-bezier(0.22, 0.61, 0.36, 1) both',
        // Centered Dialog close — same `springClose`-equiv brisk ease-out as the
        // sheet close (Vivi 03 §2.8, 25% rule), no overshoot on exit.
        'dialog-out': 'dialog-out 300ms cubic-bezier(0.22, 0.61, 0.36, 1) both',
        // Planner low-time breath — `breathCalm` loop (Vivi 03 §2.7). The global
        // prefers-reduced-motion collapse in index.css neutralises the loop to a
        // static state automatically (iteration-count:1 + duration:0.01ms).
        'breath-calm': 'breath-calm 2400ms cubic-bezier(0.37, 0, 0.63, 1) infinite',
      },
    },
  },
  plugins: [],
};
