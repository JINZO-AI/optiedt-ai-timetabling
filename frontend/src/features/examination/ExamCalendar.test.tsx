/**
 * FR-20's display half — SRS §5.5, "calendar of the session by group and by
 * room".
 *
 * These are display tests: they assert on what reaches the DOM, which `tsc`
 * cannot and which a backend test cannot reach. The requirement's own
 * acceptance file is `backend/tests/acceptance/test_fr20.py`; what is checked
 * here is that a correct timetable is displayed correctly — the same division
 * FR-7 and FR-10 use.
 */

import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ExamCalendar, byDay, formatDay } from '@/features/examination/ExamCalendar'
import type { ExamPlacement, ExamRun } from '@/types/domain'

function placement(over: Partial<ExamPlacement> = {}): ExamPlacement {
  return {
    examination: 'X-1',
    course: 'INFO-101',
    promotion: '1',
    supervisor: 'T001',
    candidateCount: 120,
    slot: 0,
    day: '2026-06-08',
    periodIndex: 0,
    rooms: ['1'],
    assignedCapacity: 250,
    ...over,
  }
}

function run(over: Partial<ExamRun> = {}): ExamRun {
  return {
    id: 'e1',
    state: 'COMPLETED',
    createdAt: '2026-06-01T09:00:00Z',
    seed: 42,
    deterministicBudget: 10,
    examinationCount: 1,
    slotCount: 55,
    spreadPenalty: 0,
    provenOptimal: true,
    wallClockSeconds: 33.4,
    placements: [placement()],
    error: null,
    ...over,
  }
}

describe('the examination calendar', () => {
  it('shows the examination with its day, period, rooms and supervisor', () => {
    render(<ExamCalendar run={run()} />)
    const row = screen.getByRole('row', { name: /INFO-101/ })
    expect(within(row).getByText('P1')).toBeTruthy()
    expect(within(row).getByText('120')).toBeTruthy()
    expect(within(row).getByText('T001')).toBeTruthy()
  })

  it('names EVERY room of a multi-room examination — R-6', () => {
    // ⚠️ The point of the requirement. A view showing only the first room
    // would understate what is booked and would make "one or more rooms"
    // invisible to the reader.
    render(
      <ExamCalendar
        run={run({
          placements: [
            placement({ rooms: ['4', '5', '11'], assignedCapacity: 115, candidateCount: 110 }),
          ],
        })}
      />,
    )
    expect(screen.getByText('4, 5, 11')).toBeTruthy()
    expect(screen.getByText(/3 rooms/)).toBeTruthy()
  })

  it('reports the assigned capacity so X2 can be checked on screen', () => {
    render(<ExamCalendar run={run()} />)
    expect(screen.getByText('250')).toBeTruthy()
  })

  it('groups by day, in date order, with each day named', () => {
    render(
      <ExamCalendar
        run={run({
          examinationCount: 2,
          placements: [
            placement({ examination: 'X-2', course: 'B', day: '2026-06-10', slot: 10 }),
            placement({ examination: 'X-1', course: 'A', day: '2026-06-08', slot: 0 }),
          ],
        })}
      />,
    )
    const headings = screen.getAllByRole('heading', { level: 4 }).map((h) => h.textContent)
    expect(headings).toHaveLength(2)
    expect(headings[0]).toMatch(/8 June/)
    expect(headings[1]).toMatch(/10 June/)
  })

  it('offers the room view §5.5 asks for, with one row per room occupied', () => {
    // An examination in three rooms occupies three rooms; collapsing it to one
    // row would make the room view understate what is booked.
    render(
      <ExamCalendar
        run={run({ placements: [placement({ rooms: ['4', '5', '11'] })] })}
      />,
    )
    fireEvent.click(screen.getByRole('tab', { name: 'By room' }))
    const rows = screen.getAllByRole('row').slice(1) // drop the header
    expect(rows).toHaveLength(3)
  })

  it('states what the spread penalty means rather than printing a bare number', () => {
    // A figure with no sentence beside it is the defect Phase 9 recorded for
    // the occupancy rate: a number that reaches a reader stripped of the
    // sentence saying what it measures.
    render(<ExamCalendar run={run({ spreadPenalty: 3 })} />)
    expect(screen.getByText(/Spread \(SX1\)/)).toBeTruthy()
    expect(screen.getByText(/sharing a day, beyond the first/)).toBeTruthy()
  })

  it('renders nothing when there are no placements, rather than an empty table', () => {
    const { container } = render(<ExamCalendar run={run({ placements: [] })} />)
    expect(container.innerHTML).toBe('')
  })
})

describe('byDay', () => {
  it('orders the placements of a day by period', () => {
    const grouped = byDay([
      placement({ examination: 'late', periodIndex: 3 }),
      placement({ examination: 'early', periodIndex: 0 }),
    ])
    expect(grouped).toHaveLength(1)
    expect(grouped[0]?.[1].map((p) => p.examination)).toEqual(['early', 'late'])
  })
})

describe('formatDay', () => {
  it('returns the input unchanged when it is not a date', () => {
    // Rather than "Invalid Date", which reads as a bug in the data.
    expect(formatDay('not-a-date')).toBe('not-a-date')
  })
})
