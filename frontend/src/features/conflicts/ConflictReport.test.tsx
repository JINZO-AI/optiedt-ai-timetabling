import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConflictReport } from '@/features/conflicts/ConflictReport'
import type { ConstraintDefinition, DiagnosisResult } from '@/types/domain'

/**
 * FR-8 on screen.
 *
 * The backend proves the conflict set is correct. What no backend test can
 * prove is what the reader concludes from it, and this report has three ways
 * to mislead while being accurate:
 *
 *  - claiming the set is the SMALLEST one (it is heuristically reduced);
 *  - reading as a REPAIR LIST (it is an unsat core — relaxing those rules need
 *    not make the instance solvable);
 *  - showing an empty set as REASSURANCE (it means either "no relaxable rule
 *    explains it" or "the solver could not prove it" — never "nothing wrong").
 *
 * Each gets a test.
 */

afterEach(cleanup)

const CATALOGUE = new Map<string, ConstraintDefinition>([
  [
    'H1',
    { code: 'H1', name: 'Un enseignant a au plus une séance par créneau', kind: 'HARD', defaultWeight: 0, xhsttReference: null },
  ],
])

function diagnosis(overrides: Partial<DiagnosisResult> = {}): DiagnosisResult {
  return {
    conflictingCodes: ['H1', 'H3'],
    isMinimal: false,
    isConclusive: true,
    detail: 'H1, H3 are together SUFFICIENT to explain the conflict.',
    ...overrides,
  }
}

function renderReport(d: DiagnosisResult) {
  render(<ConflictReport diagnosis={d} catalogue={CATALOGUE} />)
}

describe('a named conflict', () => {
  it('lists the codes and names the rule from the catalogue', () => {
    renderReport(diagnosis())
    expect(screen.getByText('H1')).toBeTruthy()
    expect(screen.getByText('H3')).toBeTruthy()
    expect(screen.getByText(/au plus une séance par créneau/)).toBeTruthy()
  })

  it('says the set is sufficient, never the smallest', () => {
    renderReport(diagnosis())
    // Exact match: the word is emphasised on its own, and the surrounding
    // paragraph also contains "suffisant" in "nécessairement suffisant".
    expect(screen.getByText('suffisant')).toBeTruthy()
    expect(screen.getByText(/sans garantie de minimalité/)).toBeTruthy()
    expect(screen.queryByText(/plus petit ensemble/)).toBeNull()
  })

  it('does not present the codes as a repair list', () => {
    /** An unsat core, not a fix. Relaxing these need not make it solvable. */
    renderReport(diagnosis())
    expect(screen.getByText(/nécessaire, pas nécessairement suffisant/)).toBeTruthy()
  })
})

describe('an empty conflict set is not reassurance', () => {
  it('conclusive and empty points at the data and the pre-analysis', () => {
    renderReport(diagnosis({ conflictingCodes: [] }))
    expect(screen.getByText(/Aucune règle relaxable/)).toBeTruthy()
    expect(screen.getByText(/vérification préalable/)).toBeTruthy()
  })

  it('inconclusive says the instance is NOT thereby sound', () => {
    /** The C-13 inference, guarded on screen. */
    renderReport(diagnosis({ conflictingCodes: [], isConclusive: false }))
    expect(screen.getByText(/non concluant/)).toBeTruthy()
    expect(screen.getByText(/n’établit pas que l’instance est saine/)).toBeTruthy()
    expect(screen.getByText(/budget déterministe plus élevé/)).toBeTruthy()
  })

  it('never shows an empty set as a clean result', () => {
    for (const conclusive of [true, false]) {
      cleanup()
      renderReport(diagnosis({ conflictingCodes: [], isConclusive: conclusive }))
      expect(screen.queryByText(/aucun conflit/i)).toBeNull()
      expect(screen.queryByText(/aucun problème/i)).toBeNull()
    }
  })
})
