import { describe, expect, it } from 'vitest'

import { landingFor } from '@/App'
import { provenanceOf } from '@/features/student/StudentTimetableScreen'
import type { StudentTimetable } from '@/types/domain'

/**
 * The student's surface — SRS Table 2, *"read the timetable of their group"*.
 *
 * ⚠️ **The right itself is verified in `acceptance/test_student_view.py`**,
 * through the API: which placements a student receives, and which surfaces
 * refuse them. What is pinned here is the display-layer half — what a printed
 * sheet says about itself, and where each role lands — because a component that
 * rendered the correct placements under a sheet naming no group would pass
 * every backend test in the repository.
 *
 * ⚠️ **Why the provenance is built here and not by `provenanceEntries`.** That
 * helper needs a `Run`, and a student is deliberately given a publication and
 * no run record: the run carries every other group's drafts. So the entries are
 * assembled from what a student legitimately holds, and this is the test that
 * says which fields those are.
 */

function timetable(overrides: Partial<StudentTimetable> = {}): StudentTimetable {
  return {
    group: '3',
    groupLabel: 'INFO-L1-G1.1',
    placements: [{ session: 'S0001', slot: 0, room: 'R01' }],
    publishedAt: '2026-08-11T09:00:00Z',
    publishedBy: 'responsable',
    run: 'run-1',
    candidate: 'cand-1',
    ...overrides,
  }
}

describe('what a printed sheet says about itself', () => {
  it('names the group, the publication and the candidate', () => {
    // ⚠️ A printed grid with nothing naming the group is anonymous: two sheets
    // for two groups are indistinguishable on paper, which is exactly the
    // confusion a printed timetable is handed out to settle (FR-10).
    const entries = provenanceOf(timetable())
    const labels = entries.map(([label]) => label)

    expect(labels).toContain('Groupe')
    expect(labels).toContain('Publié par')
    expect(labels).toContain('Candidat')
    expect(entries.find(([label]) => label === 'Groupe')?.[1]).toBe('INFO-L1-G1.1')
  })

  it('carries no publication line when nothing has been published', () => {
    // An empty "Publié le" would read as a publication with a missing date -
    // the opposite of the truth, which is that there is none.
    const labels = provenanceOf(
      timetable({ publishedAt: null, publishedBy: null, run: null, candidate: null }),
    ).map(([label]) => label)

    expect(labels).toEqual(['Groupe'])
  })

  it('never carries a run the student was not shown', () => {
    // The trace names the run that produced the published candidate, which the
    // student is entitled to; it must not grow into the run's contents.
    const values = provenanceOf(timetable()).map(([, value]) => value)

    expect(values).not.toContain('S0001')
  })
})

describe('where each role lands', () => {
  it('sends a student to their own timetable', () => {
    // ⚠️ Landing on `/disponibilites` would make a 403 a student's first
    // impression of the application, on a screen Table 2 never gave them.
    expect(landingFor('STUDENT')).toBe('/mon-emploi-du-temps')
  })

  it('sends an administrator to the surface Table 2 gives them', () => {
    expect(landingFor('ADMINISTRATOR')).toBe('/administration')
  })

  it('leaves the other two roles where they were', () => {
    expect(landingFor('PERSON_IN_CHARGE')).toBe('/generation')
    expect(landingFor('TEACHER')).toBe('/disponibilites')
    expect(landingFor(undefined)).toBe('/disponibilites')
  })
})
