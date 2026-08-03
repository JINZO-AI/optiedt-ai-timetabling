import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import { GenerationScreen } from '@/features/generation/GenerationScreen'
import { TimetableScreen } from '@/features/timetable/TimetableScreen'

/**
 * The shell.
 *
 * Navigation carries only screens that exist. Links are added as milestones
 * land rather than up front — a nav item leading to an empty page teaches the
 * reader to distrust the nav.
 */
export function App() {
  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          OptiEDT
          <span className="app__tagline">
            Génération, classement et explication des emplois du temps
          </span>
        </div>
        <nav className="app__nav">
          <NavLink to="/generation">Génération</NavLink>
          <NavLink to="/emplois-du-temps">Emplois du temps</NavLink>
        </nav>
      </header>

      <main className="app__main">
        <Routes>
          <Route path="/" element={<Navigate to="/generation" replace />} />
          <Route path="/generation" element={<GenerationScreen />} />
          <Route path="/emplois-du-temps" element={<TimetableScreen />} />
          <Route path="*" element={<p className="empty">Page inconnue.</p>} />
        </Routes>
      </main>
    </div>
  )
}
