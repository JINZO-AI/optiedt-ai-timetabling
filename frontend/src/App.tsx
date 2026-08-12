import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

import { clearToken, storedToken } from '@/api/client'
import { useCurrentUser } from '@/api/queries'
import { AdminScreen } from '@/features/admin/AdminScreen'
import { AvailabilityScreen } from '@/features/availability/AvailabilityScreen'
import { LoginScreen } from '@/features/auth/LoginScreen'
import { ComparisonScreen } from '@/features/comparison/ComparisonScreen'
import { DatasetScreen } from '@/features/dataset/DatasetScreen'
import { ExaminationScreen } from '@/features/examination/ExaminationScreen'
import { GenerationScreen } from '@/features/generation/GenerationScreen'
import { PublicationScreen } from '@/features/publication/PublicationScreen'
import { StudentTimetableScreen } from '@/features/student/StudentTimetableScreen'
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
  // SRS Table 2's two scoped roles. ⚠️ These decide what the nav OFFERS, never
  // what is permitted: the administration endpoints admit only ADMINISTRATOR
  // and `/me/timetable` only STUDENT, whatever this component renders.
  const mayAdminister = user?.role === 'ADMINISTRATOR'
  const isStudent = user?.role === 'STUDENT'

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
          {/* ⚠️ A student is offered ONE entry, and that is SRS Table 2 rather
              than a simplification: a run carries every group's drafts, so the
              screens below are closed to that role by the API too. */}
          {isStudent ? (
            <NavLink to="/mon-emploi-du-temps">Mon emploi du temps</NavLink>
          ) : (
            <>
              <NavLink to="/disponibilites">Disponibilités</NavLink>
              {/* FR-1 — SRS Table 2 gives the person in charge "read and write
                  on all the data"; C-8 settled that Table 2 wins where the flow
                  prose names the administrator instead. */}
              {mayGenerate && <NavLink to="/donnees">Données</NavLink>}
              {mayGenerate && <NavLink to="/generation">Génération</NavLink>}
              {/* FR-20 — generating a timetable is the person in charge's
                  right, weekly or examination (SRS Table 2, C-8). */}
              {mayGenerate && <NavLink to="/examens">Examens</NavLink>}
              {mayGenerate && <NavLink to="/publications">Publications</NavLink>}
              <NavLink to="/emplois-du-temps">Emplois du temps</NavLink>
              <NavLink to="/comparaison">Comparaison</NavLink>
              {mayAdminister && <NavLink to="/administration">Administration</NavLink>}
            </>
          )}
        </nav>
      }
    >
      <Routes>
        <Route path="/" element={<Navigate to={landingFor(user?.role)} replace />} />
        <Route path="/disponibilites" element={<AvailabilityScreen />} />
        <Route path="/donnees" element={<DatasetScreen />} />
        <Route path="/generation" element={<GenerationScreen />} />
        <Route path="/examens" element={<ExaminationScreen />} />
        <Route path="/emplois-du-temps" element={<TimetableScreen />} />
        <Route path="/comparaison" element={<ComparisonScreen />} />
        <Route path="/publications" element={<PublicationScreen />} />
        <Route path="/administration" element={<AdminScreen />} />
        <Route path="/mon-emploi-du-temps" element={<StudentTimetableScreen />} />
        <Route path="*" element={<p className="empty">Page inconnue.</p>} />
      </Routes>
    </Shell>
  )
}

/**
 * Where each role lands.
 *
 * ⚠️ A student landing on `/disponibilites` would meet a 403 as their first
 * impression of the application, on a screen SRS Table 2 never gave them. An
 * administrator lands on the surface Table 2 does give them.
 */
export function landingFor(role: string | undefined): string {
  if (role === 'STUDENT') return '/mon-emploi-du-temps'
  if (role === 'ADMINISTRATOR') return '/administration'
  if (role === 'PERSON_IN_CHARGE') return '/generation'
  return '/disponibilites'
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
