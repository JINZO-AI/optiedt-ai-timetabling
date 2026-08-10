import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { PrintHeader } from '@/features/timetable/PrintHeader'
import { provenanceEntries } from '@/features/timetable/export'
import type { Candidate, Run } from '@/types/domain'

/**
 * FR-10 — a printed sheet has to say what it is.
 *
 * The stylesheet is not what these test; a `@media print` rule is not
 * observable in jsdom. What is observable, and what actually decides whether a
 * printed timetable is usable, is whether the identity of the thing reaches the
 * page at all. A sheet showing five columns of course codes and nothing naming
 * the group or the candidate is a correct print of an unidentifiable document,
 * and two candidates of one run would be indistinguishable on paper.
 */

afterEach(cleanup)

const run: Run = {
  id: 'RUN-0001',
  createdAt: '2026-08-10T09:00:00Z',
  seed: 20260807,
  deterministicBudget: 90,
  state: 'COMPLETED',
  modelVersion: 'optiedt-1.0',
  weights: { S2: 0.2 },
  preAnalysis: [],
  diagnosis: null,
  candidates: [],
  duplicatesRemoved: [],
  deterministicTimeUsed: 89.4,
  wallClockSeconds: 148,
  error: null,
  origin: null,
  overrides: { lockedPlacements: [], excludedSlots: [], excludedRooms: [] },
}

const candidate: Candidate = {
  id: 'CAND-0003',
  run: 'RUN-0001',
  profileName: 'teacher-favouring',
  cost: 42,
  score: 81.1,
  placements: [],
  subScores: [],
}

function renderHeader() {
  return render(
    <PrintHeader
      title="Par groupe — L2-A1"
      entries={provenanceEntries(run, candidate, 'Par groupe', 'L2-A1')}
      printedOn="10/08/2026"
    />,
  )
}

describe('the printed sheet identifies itself', () => {
  it('names the view and the resource', () => {
    renderHeader()
    expect(screen.getByText('Par groupe — L2-A1')).toBeTruthy()
  })

  it('carries the run and the candidate, so two sheets are tellable apart', () => {
    renderHeader()
    expect(screen.getByText('RUN-0001')).toBeTruthy()
    expect(screen.getByText('CAND-0003')).toBeTruthy()
    expect(screen.getByText('teacher-favouring')).toBeTruthy()
  })

  it('carries the seed and the model version', () => {
    renderHeader()
    expect(screen.getByText('20260807')).toBeTruthy()
    expect(screen.getByText('optiedt-1.0')).toBeTruthy()
  })

  it('says when it was printed', () => {
    renderHeader()
    expect(screen.getByText(/10\/08\/2026/)).toBeTruthy()
  })
})

describe('the sheet and the exported file cannot disagree', () => {
  it('renders every provenance entry the export writes, and nothing else', () => {
    // One list, two renderings. If a later change gives the header its own
    // formatting, a printed sheet and a spreadsheet of the same view could name
    // different runs — which is worse than either of them omitting the run.
    renderHeader()
    const entries = provenanceEntries(run, candidate, 'Par groupe', 'L2-A1')

    for (const [label, value] of entries) {
      expect(screen.getByText(label)).toBeTruthy()
      expect(screen.getByText(value)).toBeTruthy()
    }
    expect(document.querySelectorAll('.print-header__trace dt')).toHaveLength(entries.length)
  })
})

describe('it belongs to the paper, not to the screen', () => {
  it('is marked print-only, since the same facts are already in the selectors', () => {
    const { container } = renderHeader()
    expect(container.querySelector('.print-only')).toBeTruthy()
  })
})
