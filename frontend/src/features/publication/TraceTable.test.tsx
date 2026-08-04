import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TraceTable } from '@/features/publication/TraceTable'
import type { PublishedTimetable } from '@/types/domain'

/**
 * The acceptance criterion, on screen:
 *
 *     Every published timetable traces back to its run, seed and weights.
 *
 * The backend proves the API returns the trace. What no backend test can prove
 * is that a reader can *see* it — and the criterion is about someone
 * establishing provenance, not about a field existing in a payload. A component
 * that rendered "Publié le 4 août par responsable" would satisfy every backend
 * test and leave the criterion unmet.
 */

afterEach(cleanup)

function published(overrides: Partial<PublishedTimetable> = {}): PublishedTimetable {
  return {
    candidate: {
      id: 'run-1-cand-0',
      run: 'run-1',
      profileName: 'balanced',
      cost: 42,
      score: 79.82,
      placements: [],
      subScores: [],
    },
    run: 'run-1',
    seed: 7,
    weights: { S2: 0.25, S3: 0.15, S10: 0 },
    modelVersion: 'weekly.h1-h12.s2-s10',
    deterministicBudget: 90,
    publishedAt: '2026-08-04T12:00:00Z',
    publishedBy: 'responsable',
    ...overrides,
  }
}

describe('the trace is complete', () => {
  it('shows the run, the seed and the model version', () => {
    render(<TraceTable published={published()} />)

    expect(screen.getByText('run-1')).toBeTruthy()
    expect(screen.getByText('7')).toBeTruthy()
    expect(screen.getByText('weekly.h1-h12.s2-s10')).toBeTruthy()
  })

  it('shows the WHOLE weight vector, not a summary', () => {
    /** ⚠️ A score is only recomputable by hand from every weight. Showing
     *  "3 criteria" or the top one would break exactly that. */
    render(<TraceTable published={published()} />)
    const weights = screen.getByText(/S10 0/)

    expect(weights.textContent).toContain('S2 0.25')
    expect(weights.textContent).toContain('S3 0.15')
    // A zero-weight criterion is part of the vector and must not be dropped.
    expect(weights.textContent).toContain('S10 0')
  })

  it('names who published it and when', () => {
    render(<TraceTable published={published()} />)
    expect(screen.getByText(/responsable/)).toBeTruthy()
    expect(screen.getByText(/2026-08-04/)).toBeTruthy()
  })

  it('does not present the deterministic budget as a duration', () => {
    /** ⚠️ ADR-011: it is a unit of WORK. Rendering "90 s" would state a
     *  promise the system does not make — the wall-clock cost of one unit is
     *  machine-dependent. */
    render(<TraceTable published={published()} />)
    expect(screen.getByText(/pas des secondes/)).toBeTruthy()
    expect(screen.queryByText('90 s')).toBeNull()
  })

  it('shows the candidate and the profile that produced it', () => {
    render(<TraceTable published={published()} />)
    expect(screen.getByText(/run-1-cand-0 — profil balanced/)).toBeTruthy()
  })
})
