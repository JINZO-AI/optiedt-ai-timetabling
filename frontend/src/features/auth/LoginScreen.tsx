import { useState } from 'react'

import { ApiError, signIn } from '@/api/client'

/**
 * FR-11 — signing in.
 *
 * ⚠️ **The message is the same whether the username is unknown or the password
 * is wrong**, because the API answers the same for both: telling them apart
 * tells an attacker which accounts exist. Do not "improve" this by splitting
 * the two cases; the server does not supply the distinction to display.
 *
 * Accounts come from the seed command (C-18) — there is no registration here
 * and none is planned for Phase 5.
 */
export function LoginScreen({ onSignedIn }: { onSignedIn: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await signIn(username, password)
      onSignedIn()
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 401
          ? 'Identifiant ou mot de passe incorrect.'
          : `La connexion a échoué : ${String(cause)}`,
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="panel panel--narrow">
      <h1>Connexion</h1>
      <p className="panel__note">
        Les comptes sont créés par la commande d’amorçage — il n’y a pas d’inscription.
      </p>

      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="username">Identifiant</label>
          <input
            id="username"
            value={username}
            autoComplete="username"
            onChange={(e) => setUsername(e.target.value)}
            disabled={pending}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Mot de passe</label>
          <input
            id="password"
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            disabled={pending}
          />
        </div>
        <button type="submit" disabled={pending || !username || !password}>
          {pending ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
    </section>
  )
}
