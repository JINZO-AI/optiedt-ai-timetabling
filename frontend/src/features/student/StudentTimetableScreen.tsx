import { useMemo } from 'react'

import { useCurrentUser, useInstance, useMyTimetable } from '@/api/queries'
import { PrintHeader } from '@/features/timetable/PrintHeader'
import { TimetableGrid } from '@/features/timetable/TimetableGrid'
import { downloadCsv, exportFilename, timetableCsv } from '@/features/timetable/export'
import { buildLookups } from '@/features/timetable/model'
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

  if (me.isLoading || instance.isLoading) return <p className="empty">Chargement…</p>
  if (!isStudent)
    return (
      <p className="warning">
        Cet écran est celui du rôle STUDENT : l’emploi du temps publié de son groupe (tableau 2 de
        la SRS).
      </p>
    )
  if (!instance.data || !lookups) return <p className="error">Instance indisponible.</p>
  if (timetable.isLoading) return <p className="empty">Chargement de l’emploi du temps…</p>
  if (timetable.isError)
    return <p className="error">Emploi du temps indisponible : {String(timetable.error)}</p>
  if (!timetable.data) return <p className="error">Emploi du temps indisponible.</p>

  const data: StudentTimetable = timetable.data
  const entries = provenanceOf(data)
  const title = `Emploi du temps — ${data.groupLabel}`

  return (
    <>
      <section className="panel no-print">
        <h1>{title}</h1>
        {data.publishedAt === null ? (
          // ⚠️ An absence, stated. "Nothing has been published yet" and "an
          // error occurred" read completely differently to a student, and only
          // the first is true — the same judgement the run report makes.
          <p className="empty" data-testid="nothing-published">
            Aucun emploi du temps n’a encore été publié pour votre groupe.
          </p>
        ) : (
          <>
            <p className="panel__note">
              Emploi du temps publié le {formatDate(data.publishedAt)} par {data.publishedBy}.
            </p>
            <div className="form-row">
              <button
                onClick={() => window.print()}
                aria-label="Imprimer l’emploi du temps"
              >
                Imprimer
              </button>
              <button
                onClick={() =>
                  downloadCsv(
                    exportFilename('Par groupe', data.groupLabel, data.candidate ?? 'publie'),
                    timetableCsv(data.placements, lookups, entries),
                  )
                }
              >
                Exporter en CSV
              </button>
            </div>
          </>
        )}
      </section>

      {data.publishedAt !== null && (
        <section className="panel">
          <PrintHeader title={title} entries={entries} printedOn={formatDate(new Date().toISOString())} />
          <TimetableGrid
            placements={data.placements}
            instance={instance.data}
            lookups={lookups}
            dimension="group"
          />
        </section>
      )}
    </>
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
  const entries: [string, string][] = [['Groupe', data.groupLabel]]
  if (data.publishedAt !== null) entries.push(['Publié le', formatDate(data.publishedAt)])
  if (data.publishedBy !== null) entries.push(['Publié par', data.publishedBy])
  if (data.candidate !== null) entries.push(['Candidat', data.candidate])
  if (data.run !== null) entries.push(['Exécution', data.run])
  return entries
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString('fr-FR')
}
