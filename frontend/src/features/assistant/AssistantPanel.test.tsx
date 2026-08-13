/**
 * "Ask OptiEDT AI" — the two states a demonstration can be in.
 *
 * ⚠️ **The property under test is that the two are never confused.** The
 * computed form is complete and honest; a written answer has been checked
 * figure by figure. A reader must be able to tell which one they are reading
 * BEFORE they read it, which is why the label goes above the text and why the
 * AI-off banner exists at all: a panel that showed computed prose with no
 * explanation looks like a broken integration rather than a configured one.
 */

import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AssistantPanel } from '@/features/assistant/AssistantPanel'
import type { AssistantAnswer } from '@/types/domain'

const explanation = vi.hoisted(() => vi.fn())

vi.mock('@/api/queries', () => ({
  useExplanation: () => explanation(),
  useAskAssistant: () => ({ mutate: vi.fn(), isPending: false, isError: false, error: null, data: undefined }),
  useRunReport: () => ({ isLoading: false, isError: false, error: null, data: undefined }),
}))

function answer(over: Partial<AssistantAnswer> = {}): AssistantAnswer {
  return { text: 'Candidate c1, score 80.87/100.', generated: true, fallbackReason: null, ...over }
}

function panel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AssistantPanel runId="run-1" candidateId="c1" />
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('with the language service switched off', () => {
  it('says so, and says the figures below are still complete', () => {
    // Invariant 5: everything works with it off — only text disappears. The
    // banner is what stops "off" from reading as "broken".
    explanation.mockReturnValue({
      isLoading: false,
      isError: false,
      error: null,
      data: answer({ generated: false, fallbackReason: 'the language service is switched off' }),
    })

    panel()

    expect(screen.getByText(/AI writing is currently switched off/i)).toBeTruthy()
    expect(screen.getByText(/computed answer/i)).toBeTruthy()
  })

  it('names the variable an operator would actually set', () => {
    // Telling someone it is off without telling them the switch is half a
    // message. The existing configuration mechanism, not a second one.
    explanation.mockReturnValue({
      isLoading: false, isError: false, error: null,
      data: answer({ generated: false, fallbackReason: 'off' }),
    })

    panel()

    expect(document.body.textContent).toContain('OPTIEDT_ASSISTANT_ENABLED')
  })

  it('labels the answer as the application’s own, not as a model’s', () => {
    explanation.mockReturnValue({
      isLoading: false, isError: false, error: null,
      data: answer({ generated: false, fallbackReason: 'off' }),
    })

    panel()

    expect(screen.getByText(/Computed by the application/i)).toBeTruthy()
    expect(screen.queryByText(/Written by the language service/i)).toBeNull()
  })

  it('surfaces the reason rather than swallowing it', () => {
    // ⚠️ The reason that matters most is "a figure was invented and the answer
    // discarded". A reader who never learns that cannot know the service is
    // unreliable on their data.
    explanation.mockReturnValue({
      isLoading: false, isError: false, error: null,
      data: answer({
        generated: false,
        fallbackReason: 'the answer contained figures absent from the context (4271), so it was discarded',
      }),
    })

    panel()

    expect(screen.getByText(/figures absent from the context/i)).toBeTruthy()
  })
})

describe('with the language service on', () => {
  it('shows no off-banner and labels the text as written by the model', () => {
    explanation.mockReturnValue({ isLoading: false, isError: false, error: null, data: answer() })

    panel()

    expect(screen.queryByText(/AI writing is currently switched off/i)).toBeNull()
    expect(screen.getByText(/Written by the language service/i)).toBeTruthy()
    expect(screen.getAllByText(/checked against the context/i).length).toBeGreaterThan(0)
  })
})

describe('the ask surface', () => {
  it('is offered by name, so the capability is findable in a demonstration', () => {
    explanation.mockReturnValue({ isLoading: false, isError: false, error: null, data: answer() })

    panel()

    expect(screen.getByRole('heading', { name: 'Ask OptiEDT AI' })).toBeTruthy()
    expect(screen.getByLabelText('Your question')).toBeTruthy()
  })

  it('suggests questions a first-time user would not think to ask', () => {
    explanation.mockReturnValue({ isLoading: false, isError: false, error: null, data: answer() })

    panel()

    expect(screen.getByRole('button', { name: /Why is this candidate ranked first/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /trade-offs/i })).toBeTruthy()
  })

  it('states that the assistant cannot invent a number', () => {
    // The grounding guarantee is the reason to trust the panel at all, so it
    // is said on screen rather than left in the documentation.
    explanation.mockReturnValue({ isLoading: false, isError: false, error: null, data: answer() })

    panel()

    expect(screen.getByText(/cannot invent a number/i)).toBeTruthy()
  })

  it('never claims the model computed a score or decided the ranking', () => {
    explanation.mockReturnValue({ isLoading: false, isError: false, error: null, data: answer() })

    const { container } = panel()

    expect(container.textContent).toMatch(/computes no score and decides no ranking/i)
  })
})
