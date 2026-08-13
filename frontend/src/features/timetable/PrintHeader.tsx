/**
 * FR-10 — what a printed sheet says about itself.
 *
 * ⚠️ **This is the reason a print stylesheet alone is not sufficient.** Hiding
 * the navigation and printing the grid produces a correct but anonymous page:
 * five columns of course codes with nothing on it naming the teacher, the
 * candidate or the run. Two such sheets from two candidates of the same run are
 * indistinguishable on paper, which is precisely the confusion a printed
 * timetable is handed out to settle.
 *
 * So the header carries the same `provenanceEntries` the exported file carries
 * — one list, two renderings — and a sheet and a spreadsheet can never disagree
 * about which run produced them.
 *
 * It is `print-only`: on screen the same facts are already on the page, in the
 * selectors above the grid.
 */
export function PrintHeader({
  title,
  entries,
  printedOn,
}: {
  title: string
  entries: [string, string][]
  /** Passed in rather than read from the clock, so the component stays pure. */
  printedOn: string
}) {
  return (
    <header className="print-only print-header">
      <div className="print-header__top">
        <span className="print-header__brand">OptiEDT</span>
        <span className="print-header__date">Printed {printedOn}</span>
      </div>
      <h2 className="print-header__title">{title}</h2>
      <dl className="print-header__trace">
        {entries.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </header>
  )
}
