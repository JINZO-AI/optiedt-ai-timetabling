import { cleanup, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  ContributionsTable,
  roundPreservingSum,
} from '@/features/comparison/ContributionsTable'
import type { Contribution, Decomposition } from '@/types/domain'

/**
 * Acceptance criterion 3: **"the sum of the displayed contributions equals the
 * score difference, to the precision of the display."**
 *
 * `tests/property/test_scoring_properties.py` already proves the identity holds
 * in the analysis layer, and `tests/integration/test_api_runs.py` proves the
 * API sends figures satisfying it. Neither can prove what a reader sees: the
 * criterion says *displayed*, and rounding happens here. A table that rounds
 * each term for display and prints an unrounded total would satisfy both
 * backend tests and fail the criterion on screen.
 *
 * So this asserts on rendered text, read back out of the DOM.
 */

function contribution(
  criterion: string,
  weight: number,
  normalisedA: number,
  normalisedB: number,
): Contribution {
  return {
    criterion,
    weight,
    normalisedA,
    normalisedB,
    value: 100 * weight * (normalisedA - normalisedB),
  }
}

function decompositionOf(contributions: Contribution[]): Decomposition {
  return {
    candidateA: 'cand-1',
    candidateB: 'cand-2',
    scoreDifference: contributions.reduce((total, c) => total + c.value, 0),
    contributions,
  }
}

const CATALOGUE = new Map()

function renderTable(decomposition: Decomposition, digits?: number) {
  render(
    <ContributionsTable
      decomposition={decomposition}
      catalogue={CATALOGUE}
      digits={digits}
    />,
  )
}

/** Read a rendered figure back as a number, sign and all. */
function shown(testId: string): number {
  return Number(screen.getByTestId(testId).textContent)
}

describe('the displayed contributions', () => {
  it('sum to the displayed score difference', () => {
    renderTable(
      decompositionOf([
        contribution('S2', 0.25 / 0.9, 0.963, 1.0),
        contribution('S3', 0.15 / 0.9, 0.979, 0.975),
        contribution('S4', 0.1 / 0.9, 0.593, 0.645),
        contribution('S5', 0.2 / 0.9, 0.55, 0.509),
        contribution('S6', 0.1 / 0.9, 0.854, 0.865),
        contribution('S7', 0.1 / 0.9, 0.761, 0.69),
        contribution('S10', 0, 0.25, 0.228),
      ]),
    )
    expect(shown('contributions-total')).toBe(shown('score-difference'))
  })

  it('still sum when every term needs rounding', () => {
    // Thirds do not round cleanly, which is where a naive total drifts.
    renderTable(
      decompositionOf([
        contribution('S2', 1 / 3, 0.1234567, 0.7654321),
        contribution('S3', 1 / 3, 0.9999999, 0.0000001),
        contribution('S7', 1 / 3, 0.3333333, 0.6666667),
      ]),
    )
    expect(shown('contributions-total')).toBe(shown('score-difference'))
  })

  it('sums at whatever precision the display uses', () => {
    const decomposition = decompositionOf([
      contribution('S2', 0.27, 0.8412, 0.7391),
      contribution('S5', 0.33, 0.5123, 0.6234),
    ])
    for (const digits of [0, 1, 2, 3, 4]) {
      // Unmount between iterations: the setup file only cleans up after each
      // `it`, so without this the queries below match every table rendered so
      // far and fail as "multiple elements" rather than as a wrong sum.
      cleanup()
      renderTable(decomposition, digits)
      expect(shown('contributions-total')).toBe(shown('score-difference'))
    }
  })

  it('shows every criterion, including one contributing nothing', () => {
    // S10 carries weight 0, so it contributes exactly 0 — and must still
    // appear. A row missing from the table is a term missing from an equation
    // the department is invited to check by hand.
    renderTable(
      decompositionOf([
        contribution('S2', 0.5, 0.9, 0.8),
        contribution('S10', 0, 0.25, 0.9),
      ]),
    )
    expect(screen.getByTestId('contribution-S10')).toBeDefined()
    expect(shown('contribution-S10')).toBe(0)
  })

  it('keeps every displayed term within one unit of its true value', () => {
    // The guard on largest-remainder rounding: making the column add up must
    // not licence moving a term anywhere it likes.
    const contributions = [
      contribution('S2', 0.27, 0.8412, 0.7391),
      contribution('S5', 0.33, 0.5123, 0.6234),
      contribution('S7', 0.4, 0.7111, 0.3222),
    ]
    const digits = 3
    const rounded = roundPreservingSum(
      contributions.map((c) => c.value),
      contributions.reduce((total, c) => total + c.value, 0),
      digits,
    )
    contributions.forEach((c, index) => {
      expect(Math.abs((rounded[index] as number) - c.value)).toBeLessThanOrEqual(10 ** -digits)
    })
  })

  it('never renders a negative zero', () => {
    // "-0.00" reads as a loss that did not happen.
    renderTable(decompositionOf([contribution('S2', 0.5, 0.5, 0.500001)]))
    expect(screen.getByTestId('contribution-S2').textContent).toBe('0.00')
  })

  it('marks the direction of each contribution', () => {
    renderTable(
      decompositionOf([
        contribution('S2', 0.5, 0.9, 0.1),
        contribution('S3', 0.5, 0.1, 0.9),
      ]),
    )
    expect(screen.getByTestId('contribution-S2').textContent?.startsWith('+')).toBe(true)
    expect(screen.getByTestId('contribution-S3').textContent?.startsWith('-')).toBe(true)
  })
})
