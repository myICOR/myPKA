/**
 * InklineMark — the myICOR INKLINE infinity mark.
 *
 * ONE CONTINUOUS STROKE that genuinely crosses itself. The geometry is the
 * canonical brand path, copied verbatim from
 * `Team Knowledge/Brand Assets/myICOR Logo INKLINE/mark-marker.svg`
 * (ratified 2026-07-09 with the INKLINE brand). Do not redraw it by hand: the
 * obvious naive version draws each lobe with matching vertical tangents at the
 * centre, so the loops merely touch and the mark reads as "OO" rather than an
 * infinity. That bug shipped once already.
 *
 * Stroke width 7 is brand-exact on the 240x110 grid. Colour is `currentColor`,
 * so the mark inherits whatever the surrounding brand block sets.
 */
export interface InklineMarkProps {
  /** Rendered width in px. Height follows the 240:110 ratio. */
  size?: number;
  className?: string;
}

const BRAND_PATH =
  'M50 55 C50 18 92 18 120 55 C148 92 190 92 190 55 ' +
  'C190 18 148 18 120 55 C92 92 50 92 50 55 Z';

export function InklineMark({ size = 24, className }: InklineMarkProps) {
  return (
    <svg
      className={className}
      width={size}
      height={Math.round((size * 110) / 240)}
      viewBox="0 0 240 110"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d={BRAND_PATH}
        stroke="currentColor"
        strokeWidth={7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
