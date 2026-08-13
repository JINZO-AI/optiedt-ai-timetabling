import { useState, type ComponentType } from 'react'
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
import { Page } from '@/shell/Page'
import {
  BrandMark,
  IconClock,
  IconCompare,
  IconData,
  IconExam,
  IconGenerate,
  IconGrid,
  IconPublished,
  IconSliders,
} from '@/shell/icons'

/**
 * The shell.
 *
 * ⚠️ **What is hidden here is not what is forbidden.** The rail offers only
 * what the signed-in role can use, but every endpoint checks the role for
 * itself (FR-11): a client that hides a control has not prevented the request.
 * If this component and the API ever disagree, the API is right.
 *
 * ⚠️ **The rail replaced a flat row of eight links, and the grouping is not
 * cosmetic.** It answers "where am I" and "what is this product for" at the
 * same time: the three groups are the three things a department does — produce
 * a timetable, supply what goes into one, and configure the institution. A row
 * of eight equal links said only that there were eight of them.
 */
export function App() {
  const [token, setToken] = useState<string | null>(storedToken)
  const queryClient = useQueryClient()
  const me = useCurrentUser()

  function signedIn() {
    setToken(storedToken())
    void queryClient.invalidateQueries()
  }

  if (token === null) {
    return (
      <div className="app app--bare">
        <LoginScreen onSignedIn={signedIn} />
      </div>
    )
  }

  // A stored token that the API rejects — expired, forged, or belonging to an
  // account that no longer exists. Signing out is the only useful response;
  // leaving it in place would give 401s on every screen with no way out.
  if (me.isError) {
    clearToken()
    if (token !== null) setToken(null)
    return (
      <div className="app app--bare">
        <LoginScreen onSignedIn={signedIn} expired />
      </div>
    )
  }

  // ⚠️ **Wait for the identity before rendering the shell.** The `/` route
  // redirects to `landingFor(user?.role)`, and while the query is in flight
  // `user` is undefined — so the redirect fired on the fallback and a timetable
  // officer landed on the availability screen, which is precisely the U1
  // complaint the role-aware landing exists to answer. Caught by driving the
  // real application, not by a test: every test renders `landingFor` directly
  // and never observes the loading tick.
  if (me.isLoading) {
    return (
      <div className="app app--bare">
        <div className="boot">
          <BrandMark size={34} />
          <p className="boot__text">Signing you in…</p>
        </div>
      </div>
    )
  }

  const user = me.data
  const role = user?.role

  function signOut() {
    clearToken()
    setToken(null)
    queryClient.clear()
  }

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <aside className="rail">
        <div className="rail__brand">
          <BrandMark />
          <span>
            <span className="rail__word">OptiEDT</span>
            <span className="rail__tag">Academic Scheduling</span>
          </span>
        </div>

        <nav className="rail__nav" aria-label="Main">
          {NAV.map((group) => {
            const items = group.items.filter((item) => item.roles.includes(role ?? ''))
            if (items.length === 0) return null
            return (
              <div className="rail__group" key={group.label}>
                <div className="rail__group-label">{group.label}</div>
                {items.map((item) => (
                  <NavLink key={item.to} to={item.to} className="rail__link">
                    <item.icon />
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>

        <div className="rail__foot">
          {user && (
            <div className="rail__who">
              <span className="rail__user">{user.username}</span>
              <span className="role-badge">{roleLabel(user.role)}</span>
            </div>
          )}
          <button className="secondary button--sm rail__signout" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="workspace">
        <Routes>
          <Route path="/" element={<Navigate to={landingFor(role)} replace />} />
          <Route path="/availability" element={<AvailabilityScreen />} />
          <Route path="/data" element={<DatasetScreen />} />
          <Route path="/generate" element={<GenerationScreen />} />
          <Route path="/examinations" element={<ExaminationScreen />} />
          <Route path="/timetables" element={<TimetableScreen />} />
          <Route path="/compare" element={<ComparisonScreen />} />
          <Route path="/publications" element={<PublicationScreen />} />
          <Route path="/administration" element={<AdminScreen />} />
          <Route path="/my-timetable" element={<StudentTimetableScreen />} />
          <Route
            path="*"
            element={
              <Page title="Not found" subtitle="This address does not match a screen">
                <p className="empty">
                  Nothing lives at this address. Use the navigation to reach a screen you can open.
                </p>
              </Page>
            }
          />
        </Routes>
      </div>
    </div>
  )
}

/**
 * What the rail offers, per role.
 *
 * ⚠️ **This is a DISPLAY decision and never an authorisation.** The roles
 * beside each entry mirror SRS Table 2 so a user is not shown a door they
 * cannot open — the door is locked by the API either way (FR-11).
 *
 * ⚠️ **A student is offered ONE entry, and that is Table 2 rather than a
 * simplification**: a run carries every group's drafts, so the rest is closed
 * to that role by the API too.
 */
const OFFICER = 'PERSON_IN_CHARGE'
const ADMIN = 'ADMINISTRATOR'
const TEACHER = 'TEACHER'
const STUDENT = 'STUDENT'

type NavItem = {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  roles: readonly string[]
}

const NAV: readonly { label: string; items: readonly NavItem[] }[] = [
  {
    label: 'Timetabling',
    items: [
      { to: '/generate', label: 'Generate', icon: IconGenerate, roles: [OFFICER] },
      { to: '/my-timetable', label: 'My Timetable', icon: IconGrid, roles: [STUDENT] },
      { to: '/timetables', label: 'Timetables', icon: IconGrid, roles: [OFFICER, ADMIN, TEACHER] },
      { to: '/compare', label: 'Compare', icon: IconCompare, roles: [OFFICER, ADMIN, TEACHER] },
      // FR-20 — generating a timetable is the person in charge's right,
      // weekly or examination (SRS Table 2, C-8).
      { to: '/examinations', label: 'Examinations', icon: IconExam, roles: [OFFICER] },
      { to: '/publications', label: 'Published', icon: IconPublished, roles: [OFFICER] },
    ],
  },
  {
    label: 'Inputs',
    items: [
      // FR-1 — SRS Table 2 gives the person in charge "read and write on all
      // the data"; C-8 settled that Table 2 wins where the flow prose names
      // the administrator instead.
      { to: '/data', label: 'Department Data', icon: IconData, roles: [OFFICER] },
      {
        to: '/availability',
        label: 'Availability',
        icon: IconClock,
        roles: [OFFICER, ADMIN, TEACHER],
      },
    ],
  },
  {
    label: 'Institution',
    items: [
      { to: '/administration', label: 'Administration', icon: IconSliders, roles: [ADMIN] },
    ],
  },
]

/**
 * How a role is named to the user.
 *
 * ⚠️ **Four roles, not three, and `PERSON_IN_CHARGE` is not the
 * administrator.** SRS Table 2 gives the person in charge every piece of data
 * and every run, and limits the administrator to accounts and the calendar
 * (C-8). Presenting the two as one would hide the actor who actually produces
 * a timetable — which is the actor a demonstration is about.
 */
export function roleLabel(role: string | undefined): string {
  switch (role) {
    case 'PERSON_IN_CHARGE':
      return 'Timetable Officer'
    case 'ADMINISTRATOR':
      return 'Administrator'
    case 'TEACHER':
      return 'Teacher'
    case 'STUDENT':
      return 'Student'
    default:
      return 'Signed in'
  }
}

/**
 * Where each role lands.
 *
 * ⚠️ A student landing on the availability screen would meet a 403 as their
 * first impression of the application, on a screen SRS Table 2 never gave
 * them. An administrator lands on the surface Table 2 does give them.
 */
export function landingFor(role: string | undefined): string {
  if (role === 'STUDENT') return '/my-timetable'
  if (role === 'ADMINISTRATOR') return '/administration'
  if (role === 'PERSON_IN_CHARGE') return '/generate'
  return '/availability'
}
