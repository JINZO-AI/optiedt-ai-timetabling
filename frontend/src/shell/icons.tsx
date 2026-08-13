/**
 * The icon set.
 *
 * ⚠️ **Every icon here is drawn from the product's own subject** — a week of
 * slots, a placed session, a ranked pair, a sealed sheet. None of them is a
 * generic dashboard pictogram, because the rail is the one place a reader
 * sees the whole product at once and it should look like this product.
 *
 * They are decorative in the accessibility sense: every one sits beside its
 * own text label, so each carries `aria-hidden` and nothing is conveyed by
 * the glyph alone.
 */

type IconProps = { className?: string }

function Svg({ children, className }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className ?? 'rail__icon'}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

/** Generate — a week of slots with one placed. */
export function IconGenerate(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="1.75" y="1.75" width="12.5" height="12.5" />
      <path d="M1.75 5.75h12.5M5.75 5.75v8.5M10.25 5.75v8.5M1.75 10h12.5" />
      <rect x="6" y="6" width="4" height="4" fill="currentColor" stroke="none" />
    </Svg>
  )
}

/** Timetables — the weekly grid, read rather than produced. */
export function IconGrid(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="1.75" y="2.75" width="12.5" height="11.5" />
      <path d="M1.75 6.25h12.5M6 6.25v8M10 6.25v8M1.75 10.25h12.5M4.5 1v2.5M11.5 1v2.5" />
    </Svg>
  )
}

/** Compare — two candidates of unequal score, side by side. */
export function IconCompare(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="2" y="6" width="4.5" height="8.25" />
      <rect x="9.5" y="2.5" width="4.5" height="11.75" />
    </Svg>
  )
}

/** Examinations — a sheet with a seat plan. */
export function IconExam(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3.25 1.75h9.5v12.5h-9.5z" />
      <path d="M5.75 5.25h4.5M5.75 8h4.5M5.75 10.75h2.5" />
    </Svg>
  )
}

/** Published — a sheet that has left the building. */
export function IconPublished(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2 9.5v4.75h12V9.5" />
      <path d="M8 1.75v8.5M4.75 5L8 1.75 11.25 5" />
    </Svg>
  )
}

/** Department data — the thirteen files, stacked. */
export function IconData(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 1.75 14.25 5 8 8.25 1.75 5z" />
      <path d="M1.75 8 8 11.25 14.25 8M1.75 11 8 14.25 14.25 11" />
    </Svg>
  )
}

/** Availability — hours a teacher can or cannot be given. */
export function IconClock(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.25" />
      <path d="M8 4.5V8l2.75 1.75" />
    </Svg>
  )
}

/** Administration — the calendar and the accounts, set by hand. */
export function IconSliders(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2 4.5h5M11 4.5h3M2 11.5h3M9 11.5h5" />
      <rect x="7" y="2.5" width="4" height="4" />
      <rect x="5" y="9.5" width="4" height="4" />
    </Svg>
  )
}

/** The brand mark — a week, two sessions placed in it.
 *
 * ⚠️ **The mark IS the product.** A timetable is a grid of slots most of which
 * stay empty; what OptiEDT does is choose which ones do not. Two filled cells
 * on a four-by-four field says that and nothing else. */
export function BrandMark({ size = 26 }: { size?: number }) {
  return (
    <svg
      className="rail__mark"
      width={size}
      height={size}
      viewBox="0 0 28 28"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="0.5" y="0.5" width="27" height="27" rx="6" fill="var(--ink)" />
      <g fill="rgba(255,255,255,0.20)">
        <rect x="5" y="5" width="4.5" height="4.5" rx="1" />
        <rect x="11.75" y="5" width="4.5" height="4.5" rx="1" />
        <rect x="18.5" y="5" width="4.5" height="4.5" rx="1" />
        <rect x="5" y="11.75" width="4.5" height="4.5" rx="1" />
        <rect x="18.5" y="11.75" width="4.5" height="4.5" rx="1" />
        <rect x="5" y="18.5" width="4.5" height="4.5" rx="1" />
        <rect x="11.75" y="18.5" width="4.5" height="4.5" rx="1" />
      </g>
      <rect x="11.75" y="11.75" width="4.5" height="4.5" rx="1" fill="var(--accent-lo)" />
      <rect x="18.5" y="18.5" width="4.5" height="4.5" rx="1" fill="var(--td)" />
    </svg>
  )
}
