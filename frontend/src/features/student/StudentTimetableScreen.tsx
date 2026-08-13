import { useMemo } from 'react'

import { useCurrentUser, useInstance, useMyTimetable } from '@/api/queries'
import { userMessage } from '@/api/errors'
import { GridKey } from '@/features/timetable/GridKey'
import { PrintHeader } from '@/features/timetable/PrintHeader'
import { TimetableGrid } from '@/features/timetable/TimetableGrid'
import { downloadCsv, exportFilename, timetableCsv } from '@/features/timetable/export'
import { buildLookups } from '@/features/timetable/model'
import { Page } from '@/shell/Page'
import type { StudentTimetable } from '@/types/domain'

/**
 * The student's own timetable — SRS Table 2, *"read the timetable of their
 * group"*, and the Cahier des Charges' *"consult and print"*.
 *
 * ⚠️ **There is no group selector, and its absence is the requirement.** The
 * group comes from the account, exactly as a teacher's grid comes from the
 * token; a dropdown here would be offering a choice the API refuses, which is
 * the defect Phase 5 moved off the availability screen.
 *
 * ⚠️ **What is shown is the PUBLISHED timetable, never a run's candidates.** A
 * run carries three ranked drafts of every group's week; publication is the act
 * by which the department says which one people follow. Showing a draft would
 * tell students to organise their week around a timetable nobody adopted.
 *
 * ⚠️ **No specification reference is printed at a student.** This screen used
 * to answer a wrong role with "(SRS Table 2 of SRS Table 2)" — a duplicated
 * citation, and one that means nothing to the person reading it. What a user
 * needs is what they may do, in their own words.
 *
 * Printing and CSV reuse `features/timetable` unchanged (FR-10). The exporter
 * re-serialises figures the API already sent — it computes no score and decides
 * no order, which is the boundary `docs/architecture.md` draws.
 */
export function StudentTimetableScreen() {
  const me = useCurrentUser()
  const instance = useInstance()
  const isStudent = me.data?.role === 'STUDENT'
  const timetable = useMyTimetable(isStudent)

  const lookups = useMemo(
    () => (instance.data ? buildLookups(instance.data) : null),
    [instance.data],
  )

  if (me.isLoading || instance.isLoading)
    return (
      <Page title="My timetable">
        <p className="empty">Loading…</p>
      </Page>
    )

  if (!isStudent)
    return (
      <Page title="My timetable">
        <p className="warning">
          This screen shows a student their own group’s published timetable. Your account is not a
          student account.
        </p>
      </Page>
    )

  if (!instance.data || !lookups)
    return (
      <Page title="My timetable">
        <p className="error" role="alert">
          The department data could not be loaded.
        </p>
      </Page>
    )

  if (timetable.isLoading)
    return (
      <Page title="My timetable">
        <p className="empty">Loading your timetable…</p>
      </Page>
    )

  if (timetable.isError)
    return (
      <Page title="My timetable">
        <p className="error" role="alert">
          {userMessage(timetable.error, 'load')}
        </p>
      </Page>
    )

  if (!timetable.data)
    return (
      <Page title="My timetable">
        <p className="error" role="alert">
          Your timetable could not be loaded.
        </p>
      </Page>
    )

  const data: StudentTimetable = timetable.data
  const entries = provenanceOf(data)
  const title = `Timetable — ${data.groupLabel}`
  const published = data.publishedAt !== null

  return (
    <Page
      title="My timetable"
      subtitle={
        published
          ? `${data.groupLabel} · published ${formatDate(data.publishedAt as string)} by ${data.publishedBy}`
          : data.groupLabel
      }
      status={
        published ? (
          <span className="badge badge--ok">Published</span>
        ) : (
          <span className="badge badge--idle">Not published</span>
        )
      }
      actions={
        published && (
          <>
            <button className="secondary" onClick={() => window.print()}>
              Print
            </button>
            <button
              className="secondary"
              onClick={() =>
                downloadCsv(
                  exportFilename('By group', data.groupLabel, data.candidate ?? 'published'),
                  timetableCsv(data.placements, lookups, entries),
                )
              }
            >
              Export CSV
            </button>
          </>
        )
      }
    >
      {!published ? (
        // ⚠️ An absence, stated. "Nothing has been published yet" and "an error
        // occurred" read completely differently to a student, and only the
        // first is true — the same judgement the run report makes.
        <p className="empty" data-testid="nothing-published">
          No timetable has been published for your group yet. Once your department publishes one, it
          will appear here.
        </p>
      ) : (
        <section className="panel panel--printable">
          <PrintHeader
            title={title}
            entries={entries}
            printedOn={formatDate(new Date().toISOString())}
          />
          <div className="table-scroll">
            <TimetableGrid
              placements={data.placements}
              instance={instance.data}
              lookups={lookups}
              dimension="group"
            />
          </div>
          <GridKey />
        </section>
      )}
    </Page>
  )
}

/**
 * What a printed sheet and an exported file say about themselves.
 *
 * ⚠️ Built here rather than with `provenanceEntries`, which needs a `Run`: a
 * student is given a publication and no run record, deliberately — the run
 * carries every other group's drafts. What travels is what identifies this
 * timetable: the group, the publication and the candidate it points at.
 */
export function provenanceOf(data: StudentTimetable): [string, string][] {
  const entries: [string, string][] = [['Group', data.groupLabel]]
  if (data.publishedAt !== null) entries.push(['Published on', formatDate(data.publishedAt)])
  if (data.publishedBy !== null) entries.push(['Published by', data.publishedBy])
  if (data.candidate !== null) entries.push(['Candidate', data.candidate])
  if (data.run !== null) entries.push(['Run', data.run])
  return entries
}

/** ⚠️ `en-GB` rather than `fr-FR`: the interface is English throughout, and a
 * date rendered in one locale beside prose in another is the kind of detail
 * that makes a product look assembled from parts. */
function formatDate(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString('en-GB')
}
