import { describe, it, expect } from 'vitest'
import { formatBuildDisplayTimeEastern, formatInstantEastern } from './buildStampTime'

describe('formatInstantEastern', () => {
  it('returns em dash for invalid Date', () => {
    expect(formatInstantEastern(new Date('bad'))).toBe('—')
  })

  it('matches eastern formatting for valid Date', () => {
    const d = new Date('2026-07-15T18:00:00.000Z')
    expect(formatInstantEastern(d)).toBe(formatBuildDisplayTimeEastern(d.toISOString()))
  })
})

describe('formatBuildDisplayTimeEastern', () => {
  it('returns raw string when date is invalid', () => {
    expect(formatBuildDisplayTimeEastern('not-a-date')).toBe('not-a-date')
  })

  it('uses America/New_York and ends with EDT in July (DST)', () => {
    const s = formatBuildDisplayTimeEastern('2026-07-15T18:00:00.000Z')
    expect(s).toMatch(/EDT$/)
    expect(s).toMatch(/^(\d{2})\/(\d{2})\/(\d{4}), \d{2}:\d{2} EDT$/)
  })

  it('uses America/New_York and ends with EST in January (standard)', () => {
    const s = formatBuildDisplayTimeEastern('2026-01-15T18:00:00.000Z')
    expect(s).toMatch(/EST$/)
  })
})
