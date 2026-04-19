import { describe, it, expect } from 'vitest'
import { formatBuildStampClipboard } from './buildStampClipboard'

describe('formatBuildStampClipboard', () => {
  it('returns Frontend label and commit', () => {
    expect(formatBuildStampClipboard('abc123')).toBe('Frontend abc123')
  })
})
