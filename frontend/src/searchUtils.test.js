import { describe, it, expect } from 'vitest'
import {
  normalizeForSearch,
  filterTournamentsForSearch,
  filterPlayersForSearch,
} from './searchUtils'

describe('normalizeForSearch', () => {
  it('handles null and undefined', () => {
    expect(normalizeForSearch(null)).toBe('')
    expect(normalizeForSearch(undefined)).toBe('')
  })

  it('folds accents case-insensitively', () => {
    expect(normalizeForSearch('José')).toBe('jose')
    expect(normalizeForSearch('SÃO')).toBe('sao')
  })
})

describe('filterTournamentsForSearch', () => {
  const base = [
    { ord: 1, name: 'Copa Alpha', crId: 11111 },
    { ord: 2, name: 'Copa Beta', crId: 22222 },
    { ord: 10, name: 'Gamma Open', crId: 0 },
  ]

  it('returns full list for empty string', () => {
    expect(filterTournamentsForSearch(base, '')).toEqual(base)
  })

  it('returns full list for whitespace-only query', () => {
    expect(filterTournamentsForSearch(base, '   ')).toEqual(base)
    expect(filterTournamentsForSearch(base, '\t\n')).toEqual(base)
  })

  it('matches name substring (accent-insensitive)', () => {
    const r = filterTournamentsForSearch(base, 'alpha')
    expect(r.map(t => t.ord)).toEqual([1])
    const r2 = filterTournamentsForSearch(base, 'são')
    expect(r2.map(t => t.ord)).toEqual([])
  })

  it('matches ord via digit substring', () => {
    expect(filterTournamentsForSearch(base, '10').map(t => t.ord)).toEqual([10])
    expect(filterTournamentsForSearch(base, '1').map(t => t.ord)).toEqual([1, 10])
  })

  it('matches crId when non-zero', () => {
    expect(filterTournamentsForSearch(base, '1111').map(t => t.ord)).toEqual([1])
  })

  it('does not use crId when crId is 0 for ID matching', () => {
    const onlyGamma = [{ ord: 5, name: 'No Chess Id', crId: 0 }]
    expect(filterTournamentsForSearch(onlyGamma, '0')).toEqual([])
    expect(filterTournamentsForSearch(onlyGamma, '5').map(t => t.ord)).toEqual([5])
  })

  it('combines name OR id (digit run)', () => {
    expect(filterTournamentsForSearch(base, 'Copa 99999')).toEqual([])
    expect(filterTournamentsForSearch(base, 'cop 11111').map(t => t.ord)).toEqual([1])
  })

  it('handles null tournament name', () => {
    const rows = [{ ord: 3, name: null, crId: 33333 }]
    expect(filterTournamentsForSearch(rows, 'zzz')).toEqual([])
    expect(filterTournamentsForSearch(rows, '333').map(t => t.ord)).toEqual([3])
  })
})

describe('filterPlayersForSearch', () => {
  const players = [
    { groupKey: 'id:100', fexerjId: 100, name: 'João Silva' },
    { groupKey: 'id:200', fexerjId: 200, name: 'Ana Costa' },
    { groupKey: 'name:X', fexerjId: null, name: 'Sem ID' },
  ]

  it('passthrough empty and whitespace-only', () => {
    expect(filterPlayersForSearch(players, '')).toEqual(players)
    expect(filterPlayersForSearch(players, '  \t')).toEqual(players)
  })

  it('matches name', () => {
    expect(filterPlayersForSearch(players, 'ana').map(p => p.fexerjId)).toEqual([200])
  })

  it('matches fexerjId digit substring', () => {
    expect(filterPlayersForSearch(players, '100').map(p => p.fexerjId)).toEqual([100])
  })

  it('null fexerjId matches only by name', () => {
    expect(filterPlayersForSearch(players, '100').some(p => p.fexerjId == null)).toBe(false)
    expect(filterPlayersForSearch(players, 'sem').map(p => p.name)).toEqual(['Sem ID'])
  })

  it('mixed text+digits uses OR (João 100 finds id 100)', () => {
    expect(filterPlayersForSearch(players, 'João 100').map(p => p.fexerjId)).toEqual([100])
  })
})
