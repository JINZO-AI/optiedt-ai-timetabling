import type { CheckResult } from '@/types/domain'

/**
 * FR-12 — the five structural checks, as the run recorded them.
 *
 * ⚠️ **The figures are shown whether or not a check passed**, and that is the
 * whole design of this component. Computer laboratories sit at 90.9 % of their
 * two-period windows — 8 spare in the entire week — while the period figure
 * reads a comfortable 71 %. Both numbers are true; only one determines whether
 * a timetable exists. A report that collapsed to five green ticks would hide
 * the one that binds, which is exactly the reading error that cost three
 * sessions on C-13.
 *
 * A failing check names the resource and the quantity missing, never a bare
 * boolean — that named detail is the content the requirement asks for.
 *
 * This component decides nothing. It renders what `GET /runs/{id}` returned;
 * the arithmetic is `optiedt.preanalysis`, server-side, and no figure here is
 * computed in the browser.
 */
export function PreAnalysisReport({ checks }: { checks: CheckResult[] }) {
  if (checks.length === 0) {
    // ⚠️ Not "everything is fine". An empty list means the stage did not run —
    // a run still PENDING, or one that failed before stage 1.
    return <p className="empty empty--inline">The data checks have not run for this run yet.</p>
  }

  const failed = checks.filter((c) => !c.passed)

  return (
    <>
      {failed.length > 0 ? (
        <p className="error">
          <b>
            {failed.length} of {checks.length} {checks.length === 1 ? 'check' : 'checks'} failed.
          </b>{' '}
          A failed slot-coverage check is a pigeonhole proof that no timetable exists — not a
          question of solver performance.
        </p>
      ) : (
        <p className="note">
          <b>
            {checks.length === 1 ? 'The check passes.' : `All ${checks.length} checks pass.`}
          </b>{' '}
          Passing is not the same as having room to spare —
          read the occupancy figures below, and read the two-period window rate rather than the
          period rate. The period bound is necessary and not sufficient.
        </p>
      )}

      <div className="table-scroll">
        <table className="checks">
          <thead>
            <tr>
              <th scope="col">Check</th>
              <th scope="col">Result</th>
              <th scope="col">Resource</th>
              <th scope="col">Short by</th>
              <th scope="col">Measured</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((check) => (
              <tr key={check.name} className={check.passed ? undefined : 'checks__row--failed'}>
                <th scope="row">{LABELS[check.name] ?? check.name}</th>
                <td>
                  <span className={`state state--${check.passed ? 'done' : 'bad'}`}>
                    {check.passed ? 'Pass' : 'Fail'}
                  </span>
                </td>
                <td>{check.resource ?? '—'}</td>
                <td className="num">{check.missingQuantity === null ? '—' : check.missingQuantity}</td>
                <td className="checks__detail">{check.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

/**
 * The five codes, in words.
 *
 * The CODE is what the API sends and what the documentation names, so it is
 * kept as the fallback rather than mapped away — an unknown code must show as
 * itself, not vanish.
 */
const LABELS: Record<string, string> = {
  ROOM_SUITABILITY: 'A suitable room exists for every session',
  SLOT_COVERAGE: 'Slot coverage by room type',
  TEACHER_LOAD: 'Teaching load within each rank’s limit',
  TEACHER_FREE_SLOTS: 'Enough free slots for every teacher',
  GROUP_HIERARCHY: 'The group hierarchy is consistent',
}
