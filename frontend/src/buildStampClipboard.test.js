import { describe, it, expect } from 'vitest'
import { formatBuildStampClipboard } from './buildStampClipboard'

describe('formatBuildStampClipboard', () => {
  it('returns snapshot and commit', () => {
    expect(formatBuildStampClipboard('snap1', 'abc123')).toBe('Frontend snap1 · commit abc123')
  })
})
