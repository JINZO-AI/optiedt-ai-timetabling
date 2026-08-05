import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { DominanceNotice } from '@/features/comparison/DominanceNotice'
import type { Candidate, DominanceVerdict } from '@/types/domain'

/**
 * FR-17 on screen, and the reason it took until Phase 6 M1 to exist.
 *
 * The backend proves the verdicts are correct. What no backend test can prove
 * is what the reader concludes from them, and this notice has three ways to
 * mislead while being accurate:
 *
 *  - showing NOTHING when nothing is dominated, so the reader cannot tell
 *    "checked, none found" from "this screen does not do that";
 *  - implying the check depends on the WEIGHTS, when its whole value as a
 *    complement to the weighted sum (ADR-002) is that it does not;
 *  - letting the permanently-silent top rank read as a result — the state the
 *    specification originally asked for is arithmetically unreachable (C-14),
 *    so silence there is not evidence of anything.
 *
 * Each gets a test.
 */

afterEach(cleanup)

function candidate(id: string): Candidate {
  return {
    id,
    run: 'run-1',
    profileName: 'balanced',
    cost: 0,
    score: 80,
    placements: [],
    subScores: [],
  }
}

const CANDIDATES = [candidate('cand-1'), candidate('cand-2'), candidate('cand-3')]

function renderNotice(
  verdicts: DominanceVerdict[],
  compared: [string, string] = ['cand-1', 'cand-2'],
) {
  render(<DominanceNotice verdicts={verdicts} candidates={CANDIDATES} compared={compared} />)
}

describe('DominanceNotice', () => {
  it('states that nothing is dominated rather than rendering nothing', () => {
    renderNotice([
      { candidate: 'cand-1', dominatedBy: null },
      { candidate: 'cand-2', dominatedBy: null },
      { candidate: 'cand-3', dominatedBy: null },
    ])

    // The finding itself, not blank space. A reader must be able to tell that
    // the check ran and returned nothing.
    expect(screen.getByText(/Aucun candidat de cette exécution n’est dominé/)).toBeTruthy()
  })

  it('states the rule, in both the empty and the non-empty case', () => {
    renderNotice([{ candidate: 'cand-1', dominatedBy: null }])
    expect(screen.getByText(/au moins aussi bien sur/)).toBeTruthy()
    expect(screen.getByText(/strictement mieux sur au moins un/)).toBeTruthy()

    cleanup()

    renderNotice([{ candidate: 'cand-2', dominatedBy: 'cand-1' }])
    expect(screen.getByText(/strictement mieux sur au moins un/)).toBeTruthy()
  })

  it('says the test uses no weights, because that is what makes it a complement', () => {
    renderNotice([{ candidate: 'cand-1', dominatedBy: null }])

    expect(screen.getByText(/n’utilise aucun poids/)).toBeTruthy()
  })

  it('names the dominated candidate and its dominator, with their ranks', () => {
    renderNotice([
      { candidate: 'cand-1', dominatedBy: null },
      { candidate: 'cand-2', dominatedBy: 'cand-1' },
      { candidate: 'cand-3', dominatedBy: null },
    ])

    expect(screen.getByText(/cand-2 \(rang 2\)/)).toBeTruthy()
    expect(screen.getByText(/cand-1 \(rang 1\)/)).toBeTruthy()
    expect(screen.getByText(/1 candidat est dominé/)).toBeTruthy()
  })

  it('warns that the top rank can never be dominated, so its silence is not a result', () => {
    renderNotice([{ candidate: 'cand-2', dominatedBy: 'cand-1' }])

    // The clause the specification asked for is unreachable (C-14). If the
    // screen stayed quiet about that, a reader would take "the winner is not
    // flagged" as evidence the winner is sound.
    expect(screen.getByText(/Le candidat de tête n’est jamais dominé/)).toBeTruthy()
  })

  it('says when the finding concerns candidates other than the two on screen', () => {
    renderNotice([{ candidate: 'cand-3', dominatedBy: 'cand-1' }], ['cand-1', 'cand-2'])

    expect(screen.getByText(/Aucun des deux candidats comparés ici n’est concerné/)).toBeTruthy()
  })

  it('does not add that remark when a compared candidate is the dominated one', () => {
    renderNotice([{ candidate: 'cand-2', dominatedBy: 'cand-1' }], ['cand-1', 'cand-2'])

    expect(screen.queryByText(/Aucun des deux candidats comparés ici n’est concerné/)).toBeNull()
    expect(screen.getByText(/affiché ci-dessous/)).toBeTruthy()
  })

  it('never phrases an empty result as reassurance about the timetable', () => {
    renderNotice([
      { candidate: 'cand-1', dominatedBy: null },
      { candidate: 'cand-2', dominatedBy: null },
    ])

    // "No candidate is dominated" says the weighted sum is arbitrating a real
    // trade-off. It says nothing about whether the timetable is good, and the
    // notice must not let those be read as the same claim.
    expect(screen.queryByText(/aucun problème/i)).toBeNull()
    expect(screen.queryByText(/tout est correct/i)).toBeNull()
    expect(screen.queryByText(/meilleur emploi du temps/i)).toBeNull()
  })
})
