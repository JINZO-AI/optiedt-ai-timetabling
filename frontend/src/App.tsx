import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

import { clearToken, storedToken } from '@/api/client'
import { useCurrentUser } from '@/api/queries'
import { AvailabilityScreen } from '@/features/availability/AvailabilityScreen'
import { LoginScreen } from '@/features/auth/LoginScreen'
import { ComparisonScreen } from '@/features/comparison/ComparisonScreen'
import { GenerationScreen } from '@/features/generation/GenerationScreen'
import { PublicationScreen } from '@/features/publication/PublicationScreen'
import { TimetableScreen } from '@/features/timetable/TimetableScreen'

/**
 * The shell.
 *
 * Navigation carries only screens that exist. Links are added as milestones
 * land rather than up front — a nav item leading to an empty page teaches the
 * reader to distrust the nav.
 *
 * ⚠️ **What is hidden here is not what is forbidden.** The nav offers only what
 * the signed-in role can use, but every endpoint checks the role for itself
 * (FR-11): a client that hides a control has not prevented the request. If this
 * component and the API ever disagree, the API is right.
 */
export function App() {
  const [token, setToken] = useState<string | null>(storedToken)
  const queryClient = useQueryClient()
  const me = useCurrentUser()

  if (token === null) {
    return (
      <Shell>
        <LoginScreen
          onSignedIn={() => {
            setToken(storedToken())
            void queryClient.invalidateQueries()
          }}
        />
      </Shell>
    )
  }

  // A stored token that the API rejects — expired, forged, or belonging to an
  // account that no longer exists. Signing out is the only useful response;
  // leaving it in place would give 401s on every screen with no way out.
  if (me.isError) {
    clearToken()
    if (token !== null) setToken(null)
    return (
      <Shell>
        <p className="warning">Votre session a expiré. Veuillez vous reconnecter.</p>
        <LoginScreen
          onSignedIn={() => {
            setToken(storedToken())
            void queryClient.invalidateQueries()
          }}
        />
      </Shell>
    )
  }

  const user = me.data
  const mayGenerate = user?.role === 'PERSON_IN_CHARGE'

  function signOut() {
    clearToken()
    setToken(null)
    queryClient.clear()
  }

  return (
    <Shell
      account={
        user && (
          <div className="app__account">
            <span>
              {user.username} · {user.role}
              {user.teacher ? ` · ${user.teacher}` : ''}
            </span>
            <button className="link" onClick={signOut}>
              Se déconnecter
            </button>
          </div>
        )
      }
      nav={
        <nav className="app__nav">
          <NavLink to="/disponibilites">Disponibilités</NavLink>
          {mayGenerate && <NavLink to="/generation">Génération</NavLink>}
          {mayGenerate && <NavLink to="/publications">Publications</NavLink>}
          <NavLink to="/emplois-du-temps">Emplois du temps</NavLink>
          <NavLink to="/comparaison">Comparaison</NavLink>
        </nav>
      }
    >
      <Routes>
        <Route
          path="/"
          element={<Navigate to={mayGenerate ? '/generation' : '/disponibilites'} replace />}
        />
        <Route path="/disponibilites" element={<AvailabilityScreen />} />
        <Route path="/generation" element={<GenerationScreen />} />
        <Route path="/emplois-du-temps" element={<TimetableScreen />} />
        <Route path="/comparaison" element={<ComparisonScreen />} />
        <Route path="/publications" element={<PublicationScreen />} />
        <Route path="*" element={<p className="empty">Page inconnue.</p>} />
      </Routes>
    </Shell>
  )
}

function Shell({
  children,
  nav,
  account,
}: {
  children: React.ReactNode
  nav?: React.ReactNode
  account?: React.ReactNode
}) {
  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          OptiEDT
          <span className="app__tagline">
            Génération, classement et explication des emplois du temps
          </span>
        </div>
        {nav}
        {account}
      </header>

      <main className="app__main">{children}</main>
    </div>
  )
}
