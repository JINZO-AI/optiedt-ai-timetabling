import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Answer } from '@/features/assistant/AssistantPanel'
import type { AssistantAnswer } from '@/types/domain'

/**
 * FR-22 and FR-24's display half — and the one thing no backend test can check.
 *
 * The backend proves an ungrounded answer is discarded. What it cannot prove is
 * what the reader concludes from what is left, and this component has three
 * ways to mislead while being accurate:
 *
 *  - showing generated text and computed text identically, so a reader cannot
 *    tell who wrote the sentence they are about to trust;
 *  - presenting the computed form as a FAILURE, when it is a complete answer
 *    whose figures came straight from the analysis layer (invariant 5 says only
 *    text disappears — not correctness);
 *  - swallowing `fallbackReason`, so nobody ever learns that a model invented a
 *    figure on their data. A broken service would then look exactly like a
 *    service nobody switched on.
 */

const GENERATED: AssistantAnswer = {
  text: 'Ce candidat obtient 79.816 sur 100.',
  generated: true,
  fallbackReason: null,
}

const COMPUTED: AssistantAnswer = {
  text: 'Candidat c1, profil « balanced », score 79.816/100.',
  generated: false,
  fallbackReason: 'the language service is switched off in configuration',
}

const DISCARDED: AssistantAnswer = {
  text: 'Candidat c1, profil « balanced », score 79.816/100.',
  generated: false,
  fallbackReason: 'the answer contained figures absent from the context (4271.0), so it was discarded',
}

describe('Answer', () => {
  afterEach(cleanup)

  it('says a generated sentence was written by the language service', () => {
    render(<Answer answer={GENERATED} />)
    expect(screen.getByText(/rédigé par le service de langage/i)).toBeTruthy()
  })

  it('says a generated sentence had its figures checked', () => {
    /** Otherwise "written by a language model" reads as a warning with no
     * mitigation, and a reader has no reason to believe any of it. */
    render(<Answer answer={GENERATED} />)
    expect(screen.getByText(/vérifiés présents dans le contexte/i)).toBeTruthy()
  })

  it('says the computed form was produced by the application, not by a model', () => {
    render(<Answer answer={COMPUTED} />)
    expect(screen.getByText(/Forme calculée par l’application/i)).toBeTruthy()
    expect(screen.queryByText(/rédigé par le service de langage/i)).toBeNull()
  })

  it('presents the computed form as an answer rather than as a failure', () => {
    /** ⚠️ It IS an answer: the figures come from the analysis layer either way.
     * Invariant 5 says only TEXT disappears - not correctness - so wording it
     * as an error would misdescribe a working application. */
    render(<Answer answer={COMPUTED} />)
    expect(screen.getByText(/les chiffres ci-dessous sont ceux de la couche d’analyse/i)).toBeTruthy()
    expect(screen.queryByText(/erreur/i)).toBeNull()
    expect(screen.queryByText(/échec/i)).toBeNull()
  })

  it('shows the text of either kind', () => {
    render(<Answer answer={GENERATED} />)
    expect(screen.getByText(/79\.816 sur 100/)).toBeTruthy()
  })

  it('marks the two origins differently, not only in words', () => {
    /** A reader scanning a page should not have to read the label to notice
     * which kind of text they are looking at. */
    const { container } = render(<Answer answer={GENERATED} />)
    expect(container.querySelector('.assistant__origin--generated')).toBeTruthy()
    cleanup()

    const computed = render(<Answer answer={COMPUTED} />)
    expect(computed.container.querySelector('.assistant__origin--generated')).toBeNull()
    expect(computed.container.querySelector('.assistant__origin')).toBeTruthy()
  })

  it('surfaces the reason a fallback happened', () => {
    render(<Answer answer={COMPUTED} />)
    expect(screen.getByText(/switched off in configuration/i)).toBeTruthy()
  })

  it('surfaces a DISCARDED answer, naming the figure that was invented', () => {
    /** ⚠️ The reason that matters most. A reader who never learns this happened
     * cannot know the service is unreliable on their data, and neither can an
     * operator. */
    render(<Answer answer={DISCARDED} />)
    expect(screen.getByText(/absent from the context \(4271\.0\), so it was discarded/i)).toBeTruthy()
  })

  it('shows no reason at all on a generated answer', () => {
    render(<Answer answer={GENERATED} />)
    expect(screen.queryByText(/^Raison/)).toBeNull()
  })

  it('never shows the invented figure itself, only that one existed', () => {
    /** The discarded text is gone; what remains is the computed form. If the
     * figure reappeared here the discard would have achieved nothing. */
    render(<Answer answer={DISCARDED} />)
    const body = screen.getByText(/Candidat c1/)
    expect(body.textContent).not.toContain('4271')
  })
})
