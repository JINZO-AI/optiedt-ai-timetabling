/**
 * FR-1 — the department data, what it is, and what the server said about it.
 *
 * SRS §3.2 Table 4 asks for *"files or forms validated by the server"* and
 * *"entities recorded and report of the rejected lines"*. This component is the
 * report; `DatasetScreen` wires it to the API.
 *
 * ⚠️ **NOT a per-entity editor, and that is a scope decision rather than an
 * omission.** SRS §4.1 lists nine user interfaces and names the administration
 * screen's contents to the item — accounts, holidays, closed half-days,
 * shortened-day period — and names no data-management form. A CRUD over
 * courses, groups, teachers and rooms would be a product requirement the
 * specification does not make.
 *
 * **Three things the design turns on.**
 *
 * 1. **Rejected lines and incompatibilities are shown apart.** A rejected line
 *    is fixed by editing the file; an incompatibility is fixed by a person
 *    withdrawing a declaration or a closure. One list would tell somebody to go
 *    and correct a file that is already correct.
 * 2. **What is in force is on screen whether the import succeeded or not.** A
 *    refused import leaves the previous dataset active, and a screen showing
 *    only the error would leave the user guessing what they still have.
 * 3. **The report says when the references have not been examined yet.** They
 *    are checked only once every line parses, so fixing the types can reveal a
 *    further round — stated in advance rather than discovered.
 */

import type { DatasetImportResult, DatasetSummary } from '@/types/domain'

/**
 * The eleven files a department dataset consists of.
 *
 * ⚠️ Eleven, not the thirteen in `data/instance/`. `constraint_catalogue.csv` is
 * the software's own rule catalogue — ADR-003 and invariant 7 — and the server
 * refuses it; `students.csv` belongs to the examination model (increment 2).
 * Named here so the screen can say what is expected before a user guesses.
 */
export const DEPARTMENT_FILES = [
  'programmes.csv',
  'promotions.csv',
  'groups.csv',
  'teachers.csv',
  'courses.csv',
  'sessions.csv',
  'rooms.csv',
  'slots.csv',
  'teacher_availability.csv',
  'holidays.csv',
  'calendar_config.csv',
]

export interface DatasetPanelProps {
  inForce: DatasetSummary | null
  outcome: DatasetImportResult | null
  chosen: number
  importing: boolean
  withdrawing: boolean
  failed: boolean
  onChoose: (files: File[]) => void
  onImport: () => void
  onWithdraw: () => void
}

export function DatasetPanel({
  inForce,
  outcome,
  chosen,
  importing,
  withdrawing,
  failed,
  onChoose,
  onImport,
  onWithdraw,
}: DatasetPanelProps) {
  return (
    <section className="screen">
      <h2>Données du département</h2>
      <p className="hint">
        Les {DEPARTMENT_FILES.length} fichiers attendus&nbsp;:{' '}
        {DEPARTMENT_FILES.join(', ')}. Le catalogue des contraintes n’en fait
        pas partie&nbsp;: il appartient à l’application.
      </p>

      {inForce ? (
        <InForce dataset={inForce} />
      ) : (
        <p className="empty">Chargement…</p>
      )}

      <div className="controls">
        <input
          type="file"
          multiple
          accept=".csv,text/csv"
          aria-label="Fichiers du département"
          data-testid="dataset-files"
          onChange={(event) => onChoose(Array.from(event.target.files ?? []))}
        />
        <button
          type="button"
          onClick={onImport}
          disabled={chosen === 0 || importing}
          data-testid="dataset-import"
        >
          {importing ? 'Vérification…' : `Charger ${chosen} fichier(s)`}
        </button>
        {inForce?.imported ? (
          <button
            type="button"
            className="secondary"
            onClick={onWithdraw}
            disabled={withdrawing}
            data-testid="dataset-withdraw"
          >
            {withdrawing ? 'Retrait…' : 'Retirer le jeu de données importé'}
          </button>
        ) : null}
      </div>

      {failed ? (
        <p className="error" role="alert">
          La requête a échoué. Vérifiez la connexion et vos droits.
        </p>
      ) : null}

      {outcome ? <Outcome result={outcome} /> : null}
    </section>
  )
}

function InForce({ dataset }: { dataset: DatasetSummary }) {
  return (
    <div className="panel" data-testid="dataset-in-force">
      <h3>
        {dataset.imported
          ? 'Jeu de données importé'
          : 'Jeu de données de référence (aucun import)'}
      </h3>
      {dataset.imported ? (
        <p className="hint" data-testid="dataset-provenance">
          Chargé par {dataset.importedBy ?? '—'}
          {dataset.importedAt
            ? ` le ${new Date(dataset.importedAt).toLocaleString('fr-FR')}`
            : ''}
          .
        </p>
      ) : (
        <p className="hint">
          Les fichiers livrés avec l’application sont en vigueur. Charger un jeu
          de données les remplace&nbsp;; le retrait les rétablit.
        </p>
      )}
      <dl className="figures">
        <Figure label="Séances" value={dataset.sessions} />
        <Figure label="Groupes" value={dataset.groups} />
        <Figure label="Enseignants" value={dataset.teachers} />
        <Figure label="Matières" value={dataset.courses} />
        <Figure label="Salles" value={dataset.rooms} />
        <Figure label="Créneaux" value={dataset.slots} />
        <Figure label="Jours fériés" value={dataset.holidays} />
      </dl>
    </div>
  )
}

function Figure({ label, value }: { label: string; value: number }) {
  return (
    <div className="figure">
      <dt>{label}</dt>
      <dd data-testid={`dataset-count-${label}`}>{value}</dd>
    </div>
  )
}

function Outcome({ result }: { result: DatasetImportResult }) {
  if (result.accepted) {
    return (
      <p className="ok" role="status" data-testid="dataset-accepted">
        Données enregistrées. Elles sont désormais celles que les écrans et les
        générations utilisent.
      </p>
    )
  }

  return (
    <div data-testid="dataset-refused">
      <p className="error" role="alert">
        Rien n’a été enregistré. Le jeu de données précédent reste en vigueur.
      </p>
      {result.incompatibilities.length > 0 ? (
        <Incompatibilities result={result} />
      ) : null}
      {result.rejectedLines.length > 0 ? (
        <RejectedLines result={result} />
      ) : null}
    </div>
  )
}

function Incompatibilities({ result }: { result: DatasetImportResult }) {
  return (
    <div className="panel" data-testid="dataset-incompatibilities">
      <h3>Déclarations et calendrier existants</h3>
      <p className="hint">
        Ces fichiers sont corrects. Le remplacement laisserait sans objet des
        données déjà enregistrées, qui ne sont jamais supprimées
        automatiquement.
      </p>
      <table>
        <thead>
          <tr>
            <th>Origine</th>
            <th>Concerne</th>
            <th>Raison</th>
            <th>Que faire</th>
          </tr>
        </thead>
        <tbody>
          {result.incompatibilities.map((found) => (
            <tr key={`${found.overlay}-${found.subject}`}>
              <td>
                {found.overlay === 'calendar' ? 'Calendrier' : 'Disponibilités'}
              </td>
              <td>{found.subject}</td>
              <td>{found.reason}</td>
              <td>{found.remedy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RejectedLines({ result }: { result: DatasetImportResult }) {
  return (
    <div className="panel" data-testid="dataset-rejected">
      <h3>Lignes refusées ({result.rejectedLines.length})</h3>
      {!result.referencesChecked ? (
        <p className="hint" data-testid="dataset-references-pending">
          Les références entre fichiers n’ont pas encore été vérifiées&nbsp;:
          elles le sont une fois que toutes les lignes se lisent. Corriger ces
          lignes peut donc en révéler d’autres.
        </p>
      ) : null}
      <table>
        <thead>
          <tr>
            <th>Fichier</th>
            <th>Ligne</th>
            <th>Colonne</th>
            <th>Valeur</th>
            <th>Raison</th>
          </tr>
        </thead>
        <tbody>
          {result.rejectedLines.map((rejected, index) => (
            <tr
              key={`${rejected.file}-${rejected.line ?? 'file'}-${rejected.field ?? index}`}
            >
              <td>{rejected.file}</td>
              <td>{rejected.line ?? '—'}</td>
              <td>{rejected.field ?? '—'}</td>
              <td>{rejected.value ?? '—'}</td>
              <td>{rejected.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
