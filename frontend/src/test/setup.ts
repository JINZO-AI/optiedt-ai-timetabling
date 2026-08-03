import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Unmount between tests: a leaked tree makes the next test's queries match two
// documents, which reads as a flaky assertion rather than as a missing cleanup.
afterEach(() => {
  cleanup()
})
