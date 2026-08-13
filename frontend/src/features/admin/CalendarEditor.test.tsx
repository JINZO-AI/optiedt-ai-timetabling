import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CalendarEditor } from '@/features/admin/CalendarEditor'
import type { CalendarData, Slot } from '@/types/domain'

/**
 * FR-9 — the administration screen's display half.
 *
 *     Acceptance criterion (SRS §8.6 Table 35):
 *     "Close a half-day in configuration → those slots disappear from every
 *     timetable, with no code change."
 *
 * ⚠️ **The criterion itself is verified in `acceptance/test_fr09.py`**, through
 * the API and against the solver. What only a rendering test can establish is
 * the half that lives here: that an administrator can *see* what they are about
 * to change and what it costs. A screen that saved the right payload while
 * showing the wrong week would pass every backend test in the repository.
 *
 * Three things are pinned, and each corresponds to a way the screen could be
 * wrong while looking right:
 *
 * 1. A slot the loaded files open and the stated calendar closes is marked as a
 *    change, not merely drawn closed.
 * 2. The open-slot count follows the edit **before** it is saved — this
 *    instance has 8 spare two-period windows in the whole week (C-13), so a
 *    count that only updated after saving would show the margin too late.
 * 3. The holiday note says plainly that a holiday closes nothing by itself
 *    (ADR-003), because that is the assumption a reader makes unprompted.
 */

const HOURS: [string, string][] = [
  ['08:30', '10:00'],
  ['10:10', '11:40'],
]

function hours(period: number): [string, string] {
  return HOURS[period % HOURS.length] ?? ['00:00', '00:00']
}

/** One day of two periods. slot = dayIndex * 2 + periodIndex. */
function slots(closed: number[] = []): Slot[] {
  return [0, 1].map((period) => ({
    index: period,
    dayIndex: 0,
    periodIndex: period,
    startHour: hours(period)[0],
    endHour: hours(period)[1],
    isOpen: !closed.includes(period),
  }))
}

/** The payload of the one call `onSave` received. */
function savedBy(onSave: ReturnType<typeof vi.fn>) {
  expect(onSave).toHaveBeenCalledTimes(1)
  return onSave.mock.calls[0]?.[0] as {
    slots: { slot: number; isOpen: boolean }[]
    holidays: unknown
  }
}

function calendar(overrides: Partial<CalendarData> = {}): CalendarData {
  return {
    slots: slots(),
    loadedOpenSlots: [0, 1],
    holidays: [],
    holidaysStated: false,
    shortenedDay: null,
    shiftedHours: [],
    openSlotCount: 2,
    editedAt: null,
    editedBy: null,
    ...overrides,
  }
}

function renderEditor(data: CalendarData, onSave = vi.fn()) {
  render(
    <CalendarEditor
      calendar={data}
      onSave={onSave}
      onReset={vi.fn()}
      saving={false}
      error={null}
    />,
  )
  return onSave
}

afterEach(cleanup)

describe('the week an administrator sees', () => {
  it('draws each slot as open or closed from the calendar in force', () => {
    renderEditor(calendar({ slots: slots([1]), loadedOpenSlots: [0, 1] }))

    expect(screen.getByTestId('calendar-slot-0').getAttribute('aria-checked')).toBe('true')
    expect(screen.getByTestId('calendar-slot-1').getAttribute('aria-checked')).toBe('false')
  })

  it('marks a slot the loaded files open and the stated calendar closes', () => {
    // ⚠️ Without this an administrator cannot tell a half-day their predecessor
    // closed from one the institution's own files never opened - and
    // "Réinitialiser" becomes a button whose effect has to be guessed.
    renderEditor(calendar({ slots: slots([1]), loadedOpenSlots: [0, 1] }))

    expect(within(screen.getByTestId('calendar-slot-1')).getByText('changed')).toBeTruthy()
    expect(within(screen.getByTestId('calendar-slot-0')).queryByText('changed')).toBeNull()
  })

  it('does not mark a slot the loaded files themselves close', () => {
    // A Saturday afternoon the institution closed is a fact, not a decision
    // this administrator took.
    renderEditor(calendar({ slots: slots([1]), loadedOpenSlots: [0] }))

    expect(within(screen.getByTestId('calendar-slot-1')).queryByText('changed')).toBeNull()
  })
})

describe('the margin being spent', () => {
  it('counts the open slots of the calendar in force', () => {
    renderEditor(calendar({ slots: slots([1]) }))

    expect(screen.getByTestId('open-slot-count').textContent).toBe('1')
  })

  it('follows an edit before it is saved', () => {
    // ⚠️ This instance has 8 spare two-period windows in the whole week (C-13).
    // A count that only moved after saving would show the cost of a closure
    // after it had been made.
    renderEditor(calendar())
    expect(screen.getByTestId('open-slot-count').textContent).toBe('2')

    fireEvent.click(screen.getByTestId('calendar-slot-1'))

    expect(screen.getByTestId('open-slot-count').textContent).toBe('1')
  })
})

describe('what is saved', () => {
  it('sends the whole week, not the cells that changed', () => {
    // A calendar is one statement about a year: a slot reopened must clear a
    // closure a previous save recorded, which a patch could not express.
    const onSave = renderEditor(calendar())

    fireEvent.click(screen.getByTestId('calendar-slot-0'))
    fireEvent.click(screen.getByText('Save calendar'))

    expect(savedBy(onSave).slots).toEqual([
      { slot: 0, isOpen: false },
      { slot: 1, isOpen: true },
    ])
  })

  it('marks the form as unsaved while an edit is pending', () => {
    renderEditor(calendar())
    expect(screen.queryByText('unsaved')).toBeNull()

    fireEvent.click(screen.getByTestId('calendar-slot-0'))

    expect(screen.getByText('unsaved')).toBeTruthy()
  })
})

describe('holidays', () => {
  it('says plainly that a holiday closes no slot by itself', () => {
    // ⚠️ ADR-003 routes a holiday through slot closure. A reader who adds "Aïd"
    // and expects the week to change would find out only after a run.
    renderEditor(calendar())

    expect(screen.getByText(/does not close a slot on its own/i)).toBeTruthy()
  })

  it('distinguishes an unstated list from one stating there are none', () => {
    // `null` is "nobody has said", `[]` is "there are none". Collapsing them
    // would make the second impossible to express.
    const { unmount } = render(
      <CalendarEditor
        calendar={calendar({ holidaysStated: false })}
        onSave={vi.fn()}
        onReset={vi.fn()}
        saving={false}
        error={null}
      />,
    )
    expect(screen.getByTestId('holidays-not-stated')).toBeTruthy()
    unmount()

    render(
      <CalendarEditor
        calendar={calendar({ holidaysStated: true })}
        onSave={vi.fn()}
        onReset={vi.fn()}
        saving={false}
        error={null}
      />,
    )
    expect(screen.queryByTestId('holidays-not-stated')).toBeNull()
  })

  it('adds a holiday to what will be saved', () => {
    const onSave = renderEditor(calendar({ holidaysStated: true }))

    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-03-20' } })
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Aid el-Fitr' } })
    fireEvent.click(screen.getByText('Add'))
    fireEvent.click(screen.getByText('Save calendar'))

    expect(savedBy(onSave).holidays).toEqual([
      { date: '2026-03-20', label: 'Aid el-Fitr', lunar: false, approximate: false, blocking: true },
    ])
  })
})

describe('the shortened-day window', () => {
  it('shows the hours the window produces rather than asserting them', () => {
    // ⚠️ ADR-003's second effect is displayed hours and nothing else. Showing
    // the result is what lets an administrator check a shift before saving it.
    renderEditor(
      calendar({
        shortenedDay: { start: '2026-02-18', end: '2026-03-19', shiftMinutes: 60 },
        shiftedHours: [{ slot: 0, startHour: '09:30', endHour: '11:00' }],
      }),
    )

    expect(within(screen.getByTestId('shifted-preview')).getByText('09:30–11:00')).toBeTruthy()
  })

  it('shows no preview when no window is configured', () => {
    renderEditor(calendar())

    expect(screen.queryByTestId('shifted-preview')).toBeNull()
  })
})
