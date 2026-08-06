import { useState } from 'react'

import { useAskAssistant, useExplanation } from '@/api/queries'
import type { AssistantAnswer } from '@/types/domain'

/**
 * FR-22 and FR-24 on screen.
 *
 * ⚠️ **The one thing this panel must never do is let generated text pass for
 * computed text.** Every answer is labelled, and the label is not a badge in a
 * corner — a reader deciding whether to trust a sentence needs to know who
 * wrote it before they read it, so it goes above.
 *
 * The computed form is the HONEST one: its figures come straight from the
 * analysis layer. So the labelling runs in the direction that protects the
 * reader — "calculé" is presented as a normal, complete answer rather than as a
 * degraded one, because that is what it is (invariant 5: only text disappears).
 *
 * ⚠️ **`fallbackReason` is shown, not swallowed.** Of the four reasons, one
 * matters more than the rest: *the answer contained a figure absent from the
 * context and was discarded*. A reader who never learns that happened cannot
 * know the service is unreliable on their data, and an operator cannot know
 * either. Hiding it would make a broken model look like a model nobody
 * switched on.
 */
export function AssistantPanel({
  runId,
  candidateId,
}: {
  runId: string
  candidateId: string | null
}) {
  const explanation = useExplanation(runId, candidateId)
  const ask = useAskAssistant(runId)
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState<string | null>(null)

  return (
    <>
      <p className="panel__note">
        Le service de langage <b>explique</b> des chiffres déjà calculés. Il ne place aucune séance,
        ne calcule aucun score et ne décide aucun classement. Chaque chiffre d’une réponse rédigée
        est vérifié contre le contexte fourni ; une réponse contenant un chiffre absent de ce
        contexte est <b>rejetée</b> et remplacée par la forme calculée.
      </p>

      <h3>Explication du candidat</h3>
      {explanation.isLoading && <p className="empty">Chargement…</p>}
      {candidateId === null && <p className="empty">Choisissez un candidat.</p>}
      {explanation.data && <Answer answer={explanation.data} />}

      <h3>Poser une question</h3>
      <div className="form-row">
        <div className="field">
          <label htmlFor="assistant-question">Question</label>
          <input
            id="assistant-question"
            type="text"
            value={question}
            placeholder="Pourquoi ce candidat est-il en tête ?"
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>
        <div className="field">
          <span className="field__label-spacer" aria-hidden="true" />
          <button
            type="button"
            disabled={ask.isPending || question.trim() === ''}
            onClick={() => {
              const text = question.trim()
              if (text === '') return
              setAsked(text)
              ask.mutate(text)
            }}
          >
            {ask.isPending ? 'Envoi…' : 'Demander'}
          </button>
        </div>
      </div>

      {asked !== null && !ask.isPending && ask.data && (
        <>
          <p className="panel__note">
            Question posée : <i>{asked}</i>
          </p>
          <Answer answer={ask.data} />
        </>
      )}
    </>
  )
}

/**
 * One answer, labelled by origin.
 *
 * ⚠️ The label comes FIRST. A reader who reaches the end of a paragraph before
 * learning a language model wrote it has already read it as fact.
 */
export function Answer({ answer }: { answer: AssistantAnswer }) {
  return (
    <>
      <p
        className={
          answer.generated ? 'assistant__origin assistant__origin--generated' : 'assistant__origin'
        }
      >
        {answer.generated ? (
          <>
            <b>Texte rédigé par le service de langage.</b> Tous ses chiffres ont été vérifiés
            présents dans le contexte fourni.
          </>
        ) : (
          <>
            <b>Forme calculée par l’application.</b> Aucun texte n’a été rédigé ; les chiffres
            ci-dessous sont ceux de la couche d’analyse.
          </>
        )}
      </p>

      <pre className="assistant__answer">{answer.text}</pre>

      {answer.fallbackReason !== null && (
        <p className="panel__note">
          Raison : {answer.fallbackReason}
        </p>
      )}
    </>
  )
}
