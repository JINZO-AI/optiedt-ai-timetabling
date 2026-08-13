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
    <>
      {inForce ? <InForce dataset={inForce} /> : <p className="empty">Loading…</p>}

      <section className="section">
        <div className="section__head">
          <h2 className="section__title">
            Replace the dataset<span className="section__code">FR-1</span>
          </h2>
        </div>
        <p className="panel__note">
          The {DEPARTMENT_FILES.length} files expected: {DEPARTMENT_FILES.join(', ')}. The
          constraint catalogue is not among them: it belongs to the application, not to a
          department. Every line is verified before anything is recorded, and a file that would
          orphan an existing declaration or closure is refused rather than allowed to delete one.
        </p>

        <div className="controls">
          <input
            type="file"
            multiple
            accept=".csv,text/csv"
            aria-label="Department data files"
            data-testid="dataset-files"
            onChange={(event) => onChoose(Array.from(event.target.files ?? []))}
          />
          <button
            type="button"
            onClick={onImport}
            disabled={chosen === 0 || importing}
            data-testid="dataset-import"
          >
            {importing
              ? 'Verifying…'
              : chosen === 0
                ? 'Upload files'
                : `Upload ${chosen} ${chosen === 1 ? 'file' : 'files'}`}
          </button>
          {inForce?.imported ? (
            <button
              type="button"
              className="danger"
              onClick={onWithdraw}
              disabled={withdrawing}
              data-testid="dataset-withdraw"
            >
              {withdrawing ? 'Withdrawing…' : 'Withdraw the imported dataset'}
            </button>
          ) : null}
        </div>

        {failed ? (
          <p className="error" role="alert">
            The request failed. Check your connection and that you have permission to load data.
          </p>
        ) : null}
      </section>

      {outcome ? <Outcome result={outcome} /> : null}
    </>
  )
}

function InForce({ dataset }: { dataset: DatasetSummary }) {
  return (
    <div className="section" data-testid="dataset-in-force">
      <div className="section__head">
        <h2 className="section__title">
          {dataset.imported ? 'Imported dataset' : 'Reference dataset'}
        </h2>
        <span className={`badge badge--${dataset.imported ? 'ok' : 'idle'}`}>
          {dataset.imported ? 'Department supplied' : 'Shipped with the application'}
        </span>
      </div>
      {dataset.imported ? (
        <p className="hint" data-testid="dataset-provenance">
          Uploaded by {dataset.importedBy ?? '—'}
          {dataset.importedAt
            ? ` on ${new Date(dataset.importedAt).toLocaleString('en-GB')}`
            : ''}
          .
        </p>
      ) : (
        <p className="hint">
          The files shipped with the application are in force. Uploading a
          dataset replaces them; withdrawing it restores them.
        </p>
      )}
      <dl className="figures">
        <Figure label="Sessions" value={dataset.sessions} />
        <Figure label="Groups" value={dataset.groups} />
        <Figure label="Teachers" value={dataset.teachers} />
        <Figure label="Courses" value={dataset.courses} />
        <Figure label="Rooms" value={dataset.rooms} />
        <Figure label="Slots" value={dataset.slots} />
        <Figure label="Holidays" value={dataset.holidays} />
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
        Data recorded. Every screen and every new run now uses it.
      </p>
    )
  }

  return (
    <div data-testid="dataset-refused">
      <p className="error" role="alert">
        Nothing was recorded. The previous dataset stays in force.
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
    <div className="section" data-testid="dataset-incompatibilities">
      <h3>Existing declarations and calendar</h3>
      <p className="hint">
        These files are correct. Replacing the dataset would leave already
        recorded data with nothing to refer to, and nothing is ever deleted
        automatically.
      </p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Source</th>
            <th>Concerns</th>
            <th>Reason</th>
            <th>What to do</th>
          </tr>
        </thead>
        <tbody>
          {result.incompatibilities.map((found) => (
            <tr key={`${found.overlay}-${found.subject}`}>
              <td>
                {found.overlay === 'calendar' ? 'Calendar' : 'Availability'}
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
    <div className="section" data-testid="dataset-rejected">
      <h3>Rejected lines ({result.rejectedLines.length})</h3>
      {!result.referencesChecked ? (
        <p className="hint" data-testid="dataset-references-pending">
          References between files have not been checked yet: they are checked
          once every line parses. Fixing these lines may therefore reveal
          others.
        </p>
      ) : null}
      <table className="data-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Line</th>
            <th>Column</th>
            <th>Value</th>
            <th>Reason</th>
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
