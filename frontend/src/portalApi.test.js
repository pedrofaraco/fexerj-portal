import { describe, expect, it } from 'vitest'

import { buildCycleFormData } from './portalApi'

function makeForm(overrides = {}) {
  return {
    playersCsv: new File(['a'], 'players.csv'),
    tournamentsCsv: new File(['b'], 'tournaments.csv'),
    binaryFiles: [new File(['c'], '1-99999.TURX')],
    first: '1',
    count: '1',
    mode: 'legacy',
    ...overrides,
  }
}

describe('buildCycleFormData', () => {
  it('sends the selected mode', () => {
    const body = buildCycleFormData(makeForm({ mode: 'fide' }))
    expect(body.get('mode')).toBe('fide')
  })

  it('falls back to the current model when no mode is set', () => {
    const form = makeForm()
    delete form.mode
    const body = buildCycleFormData(form)
    expect(body.get('mode')).toBe('legacy')
  })

  it('keeps the fields that were already there', () => {
    const body = buildCycleFormData(makeForm())
    expect(body.get('first')).toBe('1')
    expect(body.get('count')).toBe('1')
    expect(body.get('players_csv')).toBeInstanceOf(File)
    expect(body.get('tournaments_csv')).toBeInstanceOf(File)
    expect(body.getAll('binary_files')).toHaveLength(1)
  })
})
