import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DatasetPanel } from '@/features/dataset/DatasetPanel'
import type { DatasetImportResult, DatasetSummary } from '@/types/domain'

/**
 * FR-1 — the display half of *"entities recorded and report of the rejected
 * lines"* (SRS §3.2, Table 4).
 *
 * ⚠️ **The rules themselves are the server's**, verified through the API in
 * `acceptance/test_fr01.py`: what is refused, what is recorded and what a
 * replacement may not orphan. What only a rendering test can establish is that
 * the report reaches the DOM in a form a person can act on — the file, the
 * line, the column and the value — and that the two kinds of failure are not
 * presented as one, since they are fixed in different places.
 */

function summary(overrides: Partial<DatasetSummary> = {}): DatasetSummary {
  return {
    imported: false,
    importedAt: null,
    importedBy: null,
    files: [],
    programmes: 3,
    promotions: 6,
    groups: 51,
    teachers: 44,
    courses: 32,
    sessions: 218,
    rooms: 20,
    slots: 30,
    holidays: 18,
    ...overrides,
  }
}

function result(
  overrides: Partial<DatasetImportResult> = {},
): DatasetImportResult {
  return {
    accepted: false,
    dataset: summary(),
    rejectedLines: [],
    incompatibilities: [],
    referencesChecked: true,
    ...overrides,
  }
}

function renderPanel(
  overrides: Partial<Parameters<typeof DatasetPanel>[0]> = {},
) {
  const onChoose = vi.fn()
  const onImport = vi.fn()
  const onWithdraw = vi.fn()
  render(
    <DatasetPanel
      inForce={summary()}
      outcome={null}
      chosen={0}
      importing={false}
      withdrawing={false}
      failed={false}
      onChoose={onChoose}
      onImport={onImport}
      onWithdraw={onWithdraw}
      {...overrides}
    />,
  )
  return { onChoose, onImport, onWithdraw }
}

afterEach(cleanup)

describe('what is in force', () => {
  it('says plainly when nothing has been imported', () => {
    renderPanel()

    expect(screen.getByTestId('dataset-in-force').textContent).toContain(
      'référence',
    )
    expect(screen.queryByTestId('dataset-provenance')).toBeNull()
  })

  it('names who supplied an imported dataset', () => {
    renderPanel({
      inForce: summary({
        imported: true,
        importedBy: 'responsable',
        importedAt: '2026-08-11T09:00:00Z',
      }),
    })

    expect(screen.getByTestId('dataset-provenance').textContent).toContain(
      'responsable',
    )
  })

  it('shows the counts of what is actually loaded', () => {
    renderPanel({ inForce: summary({ sessions: 12, rooms: 3 }) })

    expect(screen.getByTestId('dataset-count-Séances').textContent).toContain(
      '12',
    )
    expect(screen.getByTestId('dataset-count-Salles').textContent).toContain(
      '3',
    )
  })

  it('offers withdrawal only when there is an import to withdraw', () => {
    renderPanel()
    expect(screen.queryByTestId('dataset-withdraw')).toBeNull()

    cleanup()
    renderPanel({ inForce: summary({ imported: true }) })
    expect(
      (screen.getByTestId('dataset-withdraw') as HTMLButtonElement).disabled,
    ).toBe(false)
  })

  it('names the files it expects, and excludes the constraint catalogue', () => {
    renderPanel()

    const hint = screen.getByText(/fichiers attendus/)
    expect(hint.textContent).toContain('sessions.csv')
    expect(hint.textContent).toContain('calendar_config.csv')
    expect(hint.textContent).not.toContain('constraint_catalogue.csv')
    expect(hint.textContent).not.toContain('students.csv')
  })
})

describe('sending files', () => {
  it('will not send when nothing has been chosen', () => {
    renderPanel({ chosen: 0 })

    expect(
      (screen.getByTestId('dataset-import') as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('sends what was chosen', () => {
    const { onImport } = renderPanel({ chosen: 3 })

    fireEvent.click(screen.getByTestId('dataset-import'))

    expect(onImport).toHaveBeenCalledOnce()
  })

  it('reports the files chosen back to the caller', () => {
    const { onChoose } = renderPanel()
    const file = new File(['room_id\nR1\n'], 'rooms.csv', { type: 'text/csv' })

    fireEvent.change(screen.getByTestId('dataset-files'), {
      target: { files: [file] },
    })

    expect(onChoose).toHaveBeenCalledWith([file])
  })
})

describe('the report', () => {
  it('says the data was recorded when it was', () => {
    renderPanel({
      outcome: result({ accepted: true, dataset: summary({ imported: true }) }),
    })

    expect(screen.getByTestId('dataset-accepted')).toBeTruthy()
    expect(screen.queryByTestId('dataset-refused')).toBeNull()
  })

  it('says the previous dataset is still in force when nothing was recorded', () => {
    renderPanel({
      outcome: result({
        rejectedLines: [
          {
            file: 'rooms.csv',
            line: 2,
            reason: 'expected a whole number',
            field: 'capacity',
            value: 'grand',
          },
        ],
      }),
    })

    expect(screen.getByTestId('dataset-refused').textContent).toContain(
      'Rien n’a été enregistré',
    )
    expect(screen.getByTestId('dataset-refused').textContent).toContain(
      'reste en vigueur',
    )
  })

  it('gives every rejected line its file, line, column and value', () => {
    renderPanel({
      outcome: result({
        rejectedLines: [
          {
            file: 'rooms.csv',
            line: 2,
            reason: 'expected a whole number',
            field: 'capacity',
            value: 'grand',
          },
        ],
      }),
    })

    const row = within(screen.getByTestId('dataset-rejected')).getAllByRole(
      'row',
    )[1]!
    expect(row.textContent).toContain('rooms.csv')
    expect(row.textContent).toContain('2')
    expect(row.textContent).toContain('capacity')
    expect(row.textContent).toContain('grand')
  })

  it('shows a file-level fault without inventing a line number', () => {
    renderPanel({
      outcome: result({
        rejectedLines: [
          {
            file: 'rooms.csv',
            line: null,
            reason: 'required file is missing',
            field: null,
            value: null,
          },
        ],
      }),
    })

    const row = within(screen.getByTestId('dataset-rejected')).getAllByRole(
      'row',
    )[1]!
    expect(row.textContent).toContain('required file is missing')
    expect(row.textContent).not.toContain('null')
  })

  it('warns when the references have not been examined yet', () => {
    renderPanel({
      outcome: result({
        referencesChecked: false,
        rejectedLines: [
          {
            file: 'rooms.csv',
            line: 2,
            reason: 'expected a whole number',
            field: 'capacity',
            value: 'grand',
          },
        ],
      }),
    })

    expect(screen.getByTestId('dataset-references-pending')).toBeTruthy()
  })

  it('does not warn about references once they have been examined', () => {
    renderPanel({
      outcome: result({
        referencesChecked: true,
        rejectedLines: [
          {
            file: 'sessions.csv',
            line: 2,
            reason: 'no teacher with this identifier',
            field: 'teacher_id',
            value: 'T999',
          },
        ],
      }),
    })

    expect(screen.queryByTestId('dataset-references-pending')).toBeNull()
  })
})

describe('an incompatible replacement', () => {
  /**
   * ⚠️ **The A7 project decision's display half.** A stored declaration or
   * closure a replacement would orphan is not a fault in the file, and the
   * screen must not send the user to go and edit one.
   */
  const orphaned = result({
    incompatibilities: [
      {
        overlay: 'availability',
        subject: 'T044',
        reason:
          'teacher T044 has declared availability, and the supplied dataset does not declare that teacher',
        remedy: 'keep T044 in the dataset, or clear that declaration first',
      },
    ],
  })

  it('is not presented as a rejected line', () => {
    renderPanel({ outcome: orphaned })

    expect(screen.getByTestId('dataset-incompatibilities')).toBeTruthy()
    expect(screen.queryByTestId('dataset-rejected')).toBeNull()
  })

  it('says the files are correct, so nobody goes looking for a typing error', () => {
    renderPanel({ outcome: orphaned })

    expect(
      screen.getByTestId('dataset-incompatibilities').textContent,
    ).toContain('Ces fichiers sont corrects')
  })

  it('names what is affected and what the person can do about it', () => {
    renderPanel({ outcome: orphaned })

    const row = within(
      screen.getByTestId('dataset-incompatibilities'),
    ).getAllByRole('row')[1]!
    expect(row.textContent).toContain('Disponibilités')
    expect(row.textContent).toContain('T044')
    expect(row.textContent).toContain('clear that declaration first')
  })

  it('distinguishes a calendar closure from a declaration', () => {
    renderPanel({
      outcome: result({
        incompatibilities: [
          {
            overlay: 'calendar',
            subject: '27',
            reason:
              'the calendar states slot 27 as closed, and the supplied dataset has no such slot',
            remedy: 'ask an administrator to withdraw the calendar first',
          },
        ],
      }),
    })

    const row = within(
      screen.getByTestId('dataset-incompatibilities'),
    ).getAllByRole('row')[1]!
    expect(row.textContent).toContain('Calendrier')
    expect(row.textContent).toContain('27')
  })

  it('shows both kinds together when both occur', () => {
    renderPanel({
      outcome: result({
        incompatibilities: [
          {
            overlay: 'availability',
            subject: 'T044',
            reason: 'r',
            remedy: 'm',
          },
          { overlay: 'calendar', subject: '27', reason: 'r', remedy: 'm' },
        ],
      }),
    })

    expect(
      within(screen.getByTestId('dataset-incompatibilities')).getAllByRole(
        'row',
      ),
    ).toHaveLength(3)
  })
})

describe('a request that never reached the server', () => {
  it('is distinguished from a dataset the server refused', () => {
    renderPanel({ failed: true })

    expect(screen.getByRole('alert').textContent).toContain(
      'La requête a échoué',
    )
    expect(screen.queryByTestId('dataset-refused')).toBeNull()
  })
})
