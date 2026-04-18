import { describe, it, expect } from 'vitest'
import { formatBuildStampClipboard } from './buildStampClipboard'

describe('formatBuildStampClipboard', () => {
  it('joins three labeled lines', () => {
    expect(formatBuildStampClipboard('abc123', '01/01/2026, 12:00 EDT', '02/01/2026, 13:00 EST'))
      .toBe(
        'Frontend abc123\nBuild (ET): 01/01/2026, 12:00 EDT\nServer Time (ET): 02/01/2026, 13:00 EST',
      )
  })
})
