import { useCurrentUser, usePublications } from '@/api/queries'
import { TraceTable } from '@/features/publication/TraceTable'

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
      <section className="panel">
        <h1>Emplois du temps publiés</h1>
        <p className="panel__note">
          Seul le responsable des emplois du temps peut consulter les publications.
        </p>
      </section>
    )
  }

  return (
    <section className="panel panel--printable">
      <h1>Emplois du temps publiés</h1>
      <p className="panel__note">
        Chaque publication est présentée avec ce qui l’a produite — exécution, graine, pondération
        et version du modèle — afin qu’un emploi du temps publié reste rattachable à son origine
        sans avoir à recouper plusieurs écrans.
      </p>

      {/* FR-10. The trace is the part of a publication worth having on paper:
          it is what makes a printed timetable answerable to the run that
          produced it rather than to whoever is holding it. */}
      {published.data !== undefined && published.data.length > 0 && (
        <div className="outputs">
          <button className="outputs__action" onClick={() => window.print()}>
            Imprimer
          </button>
        </div>
      )}

      {published.isPending && <p className="panel__note">Chargement…</p>}
      {published.isError && (
        <p className="error">La lecture des publications a échoué : {String(published.error)}</p>
      )}

      {published.data?.length === 0 && (
        <p className="empty">
          Aucun emploi du temps publié. Publiez un candidat depuis l’écran de génération.
        </p>
      )}

      {published.data?.map((entry) => (
        <div key={`${entry.run}:${entry.candidate.id}`} className="occupancy">
          <h3>
            {entry.candidate.id} — score {entry.candidate.score.toFixed(2)} / 100
          </h3>
          <TraceTable published={entry} />
        </div>
      ))}
    </section>
  )
}
