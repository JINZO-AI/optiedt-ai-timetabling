import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { PreAnalysisReport } from '@/features/generation/PreAnalysisReport'
import type { CheckResult } from '@/types/domain'

/**
 * FR-12 on screen.
 *
 * The backend tests prove the arithmetic and prove the API sends it. Neither
 * can prove what a reader sees, and for this report that gap is the whole
 * risk: a component that rendered five green ticks would pass every backend
 * test and still reproduce the C-13 reading error, where a comfortable
 * headline figure hid the bound that actually determines whether a timetable
 * exists.
 *
 * So these assert on rendered text, read back out of the DOM:
 *
 *  - the figures are displayed even when a check PASSES;
 *  - a failing check shows the resource and the quantity missing;
 *  - an EMPTY report reads as "not run", never as "verified, nothing wrong".
 */

afterEach(cleanup)

function check(overrides: Partial<CheckResult> = {}): CheckResult {
  return {
    name: 'SLOT_COVERAGE',
    passed: true,
    resource: null,
    missingQuantity: null,
    detail: 'Lab_Info 160/224 periods = 71.4%, 80/88 2-period windows = 90.9%',
    ...overrides,
  }
}

describe('the report shows figures, not verdicts', () => {
  it('displays the detail of a check that passed', () => {
    render(<PreAnalysisReport checks={[check()]} />)

    // ⚠️ The binding figure is the WINDOW percentage, not the period one, and
    // this check passes. If the component ever collapses to a tick, this fails.
    expect(screen.getByText(/90\.9%/)).toBeTruthy()
    expect(screen.getByText(/71\.4%/)).toBeTruthy()
    expect(screen.getByText('OK')).toBeTruthy()
  })

  it('names the resource and the quantity missing when a check fails', () => {
    render(
      <PreAnalysisReport
        checks={[
          check({
            passed: false,
            resource: 'Lab_Info',
            missingQuantity: 14,
            detail:
              'Lab_Info is short by 14 2-period windows (6 rooms). This is a pigeonhole argument.',
          }),
        ]}
      />,
    )

    expect(screen.getByText('ÉCHEC')).toBeTruthy()
    expect(screen.getByText('Lab_Info')).toBeTruthy()
    expect(screen.getByText('14')).toBeTruthy()
    expect(screen.getByText(/pigeonhole/)).toBeTruthy()
  })

  it('shows a zero quantity rather than an em dash', () => {
    /** 0 is a measurement; `??` on a number would turn it into "—". */
    render(<PreAnalysisReport checks={[check({ passed: false, missingQuantity: 0 })]} />)
    expect(screen.getByText('0')).toBeTruthy()
  })

  it('labels each of the five checks in French but keeps an unknown code visible', () => {
    render(
      <PreAnalysisReport
        checks={[check({ name: 'TEACHER_LOAD' }), check({ name: 'FUTURE_CHECK' })]}
      />,
    )
    expect(screen.getByText('Charge maximale par grade')).toBeTruthy()
    // A code with no label must show as itself rather than disappear.
    expect(screen.getByText('FUTURE_CHECK')).toBeTruthy()
  })
})

describe('an empty report means the stage did not run', () => {
  it('says so, and does not read as a clean result', () => {
    render(<PreAnalysisReport checks={[]} />)

    expect(screen.getByText(/non exécutée/)).toBeTruthy()
    // The failure mode this guards: an empty list rendering as reassurance.
    expect(screen.queryByText('OK')).toBeNull()
    expect(screen.queryByText(/vérifications passent/)).toBeNull()
  })
})
