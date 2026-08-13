import { useCurrentUser, usePublications } from '@/api/queries'
import { userMessage } from '@/api/errors'
import { TraceTable } from '@/features/publication/TraceTable'
import { Page } from '@/shell/Page'

/**
 * Published timetables and their provenance — FR-19's acceptance criterion.
 *
 * ⚠️ **Reading this screen is the person in charge's right** (SRS Table 2).
 * The API refuses anyone else with 403 regardless of what this component
 * renders; hiding the screen is a convenience, not the protection.
 */
export function PublicationScreen() {
  const me = useCurrentUser()
  const published = usePublications()

  if (me.data && me.data.role !== 'PERSON_IN_CHARGE') {
    return (
      <Page title="Published timetables">
        <p className="warning">
          Publishing and reviewing publications belongs to the Timetable Officer role. Your account
          does not hold it.
        </p>
      </Page>
    )
  }

  const entries = published.data ?? []

  return (
    <Page
      title="Published timetables"
      subtitle={
        entries.length === 1
          ? '1 publication, traceable to the run that produced it'
          : entries.length > 1
            ? `${entries.length} publications, each traceable to the run that produced it`
            : 'Each publication carries the run, seed, weights and model version that produced it'
      }
      actions={
        entries.length > 0 && (
          <button className="secondary" onClick={() => window.print()}>
            Print
          </button>
        )
      }
    >
      {published.isPending && <p className="empty">Loading…</p>}
      {published.isError && (
        <p className="error" role="alert">
          {userMessage(published.error, 'load')}
        </p>
      )}

      {published.data?.length === 0 && (
        <p className="empty">
          Nothing has been published yet. Publish a candidate from the Generate screen and it will
          appear here with its full provenance.
        </p>
      )}

      {/* FR-10. The trace is the part of a publication worth having on paper:
          it is what makes a printed timetable answerable to the run that
          produced it rather than to whoever is holding it. */}
      {entries.map((entry) => (
        <section
          key={`${entry.run}:${entry.candidate.id}`}
          className="panel panel--printable"
        >
          <div className="section__head">
            <h2 className="section__title">
              <span className="code">{entry.candidate.id}</span>
              <span className="section__code">FR-19 · Provenance</span>
            </h2>
            <div className="stat">
              <span className="stat__label">Score</span>
              <span className="stat__value">{entry.candidate.score.toFixed(2)} / 100</span>
            </div>
          </div>
          <TraceTable published={entry} />
        </section>
      ))}
    </Page>
  )
}
