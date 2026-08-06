import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { RegenerationPanel } from '@/features/comparison/RegenerationPanel'
import type { Candidate, ConstraintDefinition, Run } from '@/types/domain'

/**
 * FR-23's display half.
 *
 * ⚠️ **What is under test is the MEANING the screen conveys, not the markup.**
 * The requirement is that accepting a recommendation launches a new run rather
 * than editing a timetable, and a panel that got the wiring right while
 * reading as "improve this timetable" would satisfy every backend test and
 * still mislead the one reader it is built for. A reader who believes their
 * timetable was edited has no reason to trust that H1-H12 still hold in it.
 *
 * Same discipline as ConflictReport.test and DominanceNotice.test: assert what
 * the screen SAYS, because no backend test can.
 */

const RUN: Run = {
  id: 'run-1',
  createdAt: '2026-08-06T12:00:00Z',
  seed: 42,
  deterministicBudget: 90,
  state: 'COMPLETED',
  modelVersion: 'weekly.h1-h12.s2-s10',
  weights: { S2: 0.15, S3: 0.15 },
  preAnalysis: [],
  diagnosis: null,
  candidates: [],
  duplicatesRemoved: [],
  deterministicTimeUsed: 90,
  wallClockSeconds: 150,
  error: null,
  origin: null,
  overrides: { lockedPlacements: [], excludedSlots: [], excludedRooms: [] },
}

const CANDIDATE: Candidate = {
  id: 'cand-1',
  run: 'run-1',
  profileName: 'balanced',
  cost: 100,
  score: 80,
  placements: [
    { session: 'S0002', slot: 3, room: '4' },
    { session: 'S0001', slot: 7, room: '2' },
  ],
  subScores: [],
}

const CATALOGUE = new Map<string, ConstraintDefinition>([
  ['S2', { code: 'S2', name: 'Temps mort étudiant', kind: 'SOFT', defaultWeight: 0.15, xhsttReference: null }],
  ['S3', { code: 'S3', name: 'Temps mort enseignant', kind: 'SOFT', defaultWeight: 0.15, xhsttReference: null }],
])

function renderPanel(overrides: Partial<Parameters<typeof RegenerationPanel>[0]> = {}) {
  const onAccept = vi.fn()
  render(
    <RegenerationPanel
      run={RUN}
      candidate={CANDIDATE}
      catalogue={CATALOGUE}
      onAccept={onAccept}
      pending={false}
      error={null}
      launched={null}
      {...overrides}
    />,
  )
  return onAccept
}

const accept = () =>
  fireEvent.click(screen.getByRole('button', { name: /Accepter et régénérer|Lancement/i }))

describe('RegenerationPanel', () => {
  afterEach(cleanup)

  it('says in as many words that this candidate is not modified', () => {
    renderPanel()
    expect(screen.getByText(/ne modifie/i)).toBeTruthy()
    expect(screen.getByText(/nouvelle exécution/i)).toBeTruthy()
  })

  it('states why the guarantee carries over rather than only asserting it', () => {
    /** The reason H1-H12 hold in the regenerated candidate is that they are
     * DECLARED IDENTICALLY, not that something re-checked them. A reader who
     * is told only "it is still valid" has been asked to take it on trust. */
    renderPanel()
    expect(screen.getByText(/H1–H12 sont déclarées à l’identique/i)).toBeTruthy()
  })

  it('offers exactly the three catalogue actions and no free-text field', () => {
    renderPanel()
    const options = screen
      .getAllByRole('option')
      .map((o) => (o as HTMLOptionElement).value)
      .filter((v) => ['weight_delta', 'lock_session', 'exclude_slot'].includes(v))
    expect(options).toEqual(['weight_delta', 'lock_session', 'exclude_slot'])
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('sends a weight_delta with the criterion and the new weight', () => {
    const onAccept = renderPanel()
    fireEvent.change(screen.getByLabelText(/Nouveau poids/i), { target: { value: '0.3' } })
    accept()
    expect(onAccept).toHaveBeenCalledWith({
      kind: 'weight_delta',
      criterion: 'S2',
      newWeight: 0.3,
    })
  })

  it('refuses to send a negative weight rather than letting the API reject it', () => {
    const onAccept = renderPanel()
    fireEvent.change(screen.getByLabelText(/Nouveau poids/i), { target: { value: '-1' } })
    accept()
    expect(onAccept).not.toHaveBeenCalled()
  })

  it('sends a lock_session naming only the session, never a slot or room', () => {
    /** The target is read out of the candidate by the server. A panel that
     * sent its own slot/room could lock a session somewhere it is not. */
    const onAccept = renderPanel()
    fireEvent.change(screen.getByLabelText(/Action/i), { target: { value: 'lock_session' } })
    accept()
    expect(onAccept).toHaveBeenCalledWith({ kind: 'lock_session', session: 'S0001' })
  })

  it('excludes the slot the session actually occupies in this candidate', () => {
    const onAccept = renderPanel()
    fireEvent.change(screen.getByLabelText(/Action/i), { target: { value: 'exclude_slot' } })
    fireEvent.change(screen.getByLabelText(/Séance/i), { target: { value: 'S0002' } })
    accept()
    expect(onAccept).toHaveBeenCalledWith({ kind: 'exclude_slot', session: 'S0002', slot: 3 })
  })

  it('names the new run after launching, and repeats that this one is unchanged', () => {
    renderPanel({ launched: 'run-2' })
    expect(screen.getByText(/run-2/)).toBeTruthy()
    expect(screen.getByText(/inchangé/i)).toBeTruthy()
  })

  it('says when the run is itself the result of an earlier recommendation', () => {
    /** So a user reading a chain can tell that their earlier locks are still
     * in force - C-20's composing overrides, made visible. */
    renderPanel({
      run: {
        ...RUN,
        origin: {
          run: 'run-0',
          candidate: 'cand-0',
          actionKind: 'lock_session',
          actionDetail: 'session S0001 locked to its current slot and room',
        },
      },
    })
    expect(screen.getByText(/issue d’une recommandation acceptée/i)).toBeTruthy()
    expect(screen.getByText(/conservées/i)).toBeTruthy()
  })

  it('disables the control while a run is being launched', () => {
    renderPanel({ pending: true })
    expect(screen.getByRole('button', { name: /Lancement/i })).toHaveProperty("disabled", true)
  })

  it('shows a refusal from the API rather than swallowing it', () => {
    renderPanel({ error: 'criterion S9 is not one this run prices' })
    expect(screen.getByText(/S9 is not one this run prices/)).toBeTruthy()
  })
})
