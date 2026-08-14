/**
 * What the colours on the weekly grid mean.
 *
 * ⚠️ **The key exists because the colour is redundant, not because it is the
 * encoding.** Every cell also prints `CM`, `TD` or `TP` as text, so a reader
 * who cannot separate the three hues loses nothing. The key is here so that a
 * reader who *can* does not have to work the mapping out from context — and
 * because the domain vocabulary is kept verbatim in French (docs/domain-model.md),
 * a visitor who has never met "Amphi" or "TD" needs it said once.
 */
export function GridKey() {
  return (
    <div className="grid-key no-print">
      <span className="grid-key__item">
        <span className="grid-key__swatch grid-key__swatch--cm" />
        <b>CM</b> Lecture — the whole promotion
      </span>
      <span className="grid-key__item">
        <span className="grid-key__swatch grid-key__swatch--td" />
        <b>TD</b> Tutorial — one TD group
      </span>
      <span className="grid-key__item">
        <span className="grid-key__swatch grid-key__swatch--tp" />
        <b>TP</b> Practical — one TP group, in a laboratory
      </span>
      <span className="grid-key__item">
        <span className="grid-key__swatch grid-key__swatch--closed" />
        Closed by the academic calendar
      </span>
    </div>
  )
}
