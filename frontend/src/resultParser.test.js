import JSZip from 'jszip'
import { describe, it, expect } from 'vitest'
import {
  AUDIT_FILE_HEADER,
  buildPlayerIndex,
  mapAuditRowToPlayer,
  parseAuditCsv,
  parseRatingListAfterCsv,
  parseRunResult,
  parseSemicolonCsv,
  parseTournamentsCsv,
  stripUtf8Bom,
} from './resultParser'

const SAMPLE_AUDIT_ROW =
  '100;João Silva;1;1800;50;25;3.5;5;8750;1750;50;0.59;2.95;0.55;13.75;1823;55;0.7;NORMAL'

const TOURNAMENTS_CSV = `Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
1;99999;Copa Teste;2025-01-01;RR;0;1`

const RATING_LIST_HEADER =
  'Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints'

async function zipFromEntries(entries) {
  const z = new JSZip()
  for (const [name, content] of Object.entries(entries)) z.file(name, content)
  return z.generateAsync({ type: 'blob' })
}

describe('stripUtf8Bom', () => {
  it('removes BOM', () => {
    expect(stripUtf8Bom(`\ufeff${AUDIT_FILE_HEADER}`)).toBe(AUDIT_FILE_HEADER)
  })
})

describe('parseSemicolonCsv', () => {
  it('parses BOM-prefixed header', () => {
    const text = `\ufeff${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}`
    const { headers, rows } = parseSemicolonCsv(text)
    expect(headers[0]).toBe('Id_Fexerj')
    expect(rows).toHaveLength(1)
    expect(rows[0][0]).toBe('100')
  })
})

describe('parseTournamentsCsv', () => {
  it('maps Ord to metadata', () => {
    const m = parseTournamentsCsv(TOURNAMENTS_CSV)
    expect(m.get(1).name).toBe('Copa Teste')
    expect(m.get(1).type).toBe('RR')
    expect(m.get(1).isFexerj).toBe(true)
  })
})

describe('mapAuditRowToPlayer', () => {
  it('computes delta from Ro and Rn', () => {
    const cells = SAMPLE_AUDIT_ROW.split(';')
    const p = mapAuditRowToPlayer(cells)
    expect(p.oldRating).toBe(1800)
    expect(p.newRating).toBe(1823)
    expect(p.delta).toBe(23)
    expect(p.calcRule).toBe('NORMAL')
    expect(p.fexerjId).toBe(100)
  })

  it('throws when row has fewer than 19 columns', () => {
    expect(() => mapAuditRowToPlayer(['1', '2', '3'])).toThrow(/19 colunas/)
  })

  it('maps None and invalid Id to null fields', () => {
    const base = SAMPLE_AUDIT_ROW.split(';')
    base[0] = 'not-an-id'
    base[18] = 'None'
    const p = mapAuditRowToPlayer(base)
    expect(p.fexerjId).toBe(null)
    expect(p.calcRule).toBe(null)
  })

  it('leaves delta null when Ro or Rn is missing', () => {
    const base = SAMPLE_AUDIT_ROW.split(';')
    base[3] = ''
    base[15] = '1823'
    const p = mapAuditRowToPlayer(base)
    expect(p.delta).toBe(null)
  })
})

describe('parseAuditCsv', () => {
  it('accepts a header that matches Id_Fexerj prefix but not the strict calculator header', () => {
    const looseHeader = `${AUDIT_FILE_HEADER}X`
    const text = `${looseHeader}\n${SAMPLE_AUDIT_ROW}`
    const players = parseAuditCsv(text)
    expect(players).toHaveLength(1)
    expect(players[0].fexerjId).toBe(100)
  })

  it('skips rows that are entirely empty cells', () => {
    const emptyRow = Array(19).fill('').join(';')
    const text = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}\n${emptyRow}`
    const players = parseAuditCsv(text)
    expect(players).toHaveLength(1)
  })

  it('preserves row order', () => {
    const row2 =
      '101;Maria;2;1650;40;20;2;4;7200;1800;-150;0.5;2.0;-0.25;-5;1658;44;0.5;NORMAL'
    const text = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}\n${row2}`
    const players = parseAuditCsv(text)
    expect(players).toHaveLength(2)
    expect(players[0].fexerjId).toBe(100)
    expect(players[1].fexerjId).toBe(101)
  })

  it('allows header-only audit', () => {
    const players = parseAuditCsv(`${AUDIT_FILE_HEADER}\n`)
    expect(players).toHaveLength(0)
  })
})

describe('parseRatingListAfterCsv', () => {
  it('maps Id_No to Rtg_Nat', () => {
    const text = `${RATING_LIST_HEADER}\n100;;M;João;1823;;;;;;55;;;`
    const m = parseRatingListAfterCsv(text)
    expect(m.get(100)).toBe(1823)
  })

  it('returns empty map when required columns are missing', () => {
    const m = parseRatingListAfterCsv('Foo;Bar\n1;2')
    expect(m.size).toBe(0)
  })
})

describe('buildPlayerIndex', () => {
  function mkTournament(ord, players, overrides = {}) {
    return {
      ord,
      crId: ord * 1000,
      name: `Torneio ${ord}`,
      type: 'RR',
      typeLabelPt: 'Round-robin',
      endDate: '',
      isFexerj: true,
      isIrt: false,
      players,
      ...overrides,
    }
  }

  it('groups one player from one tournament', () => {
    const cells = SAMPLE_AUDIT_ROW.split(';')
    const p = mapAuditRowToPlayer(cells)
    const idx = buildPlayerIndex([mkTournament(1, [p])])
    expect(idx).toHaveLength(1)
    expect(idx[0].groupKey).toBe('id:100')
    expect(idx[0].initialRating).toBe(1800)
    expect(idx[0].finalRating).toBe(1823)
    expect(idx[0].netDelta).toBe(23)
    expect(idx[0].tournaments).toHaveLength(1)
    expect(idx[0].tournaments[0].ord).toBe(1)
    expect(idx[0].tournaments[0].tournamentName).toBe('Torneio 1')
  })

  it('sorts players alphabetically by name (pt-BR), tiebreak by fexerjId', () => {
    const rowAna =
      '200;Ana Costa;1;1700;30;15;2;4;6800;1700;0;0.5;2;0;0;1710;34;0.5;NORMAL'
    const rowJoao = SAMPLE_AUDIT_ROW
    const pAna = mapAuditRowToPlayer(rowAna.split(';'))
    const pJoao = mapAuditRowToPlayer(rowJoao.split(';'))
    const idx = buildPlayerIndex([
      mkTournament(1, [pJoao]),
      mkTournament(2, [pAna]),
    ])
    expect(idx.map(x => x.fexerjId)).toEqual([200, 100])
  })

  it('aggregates initial/final across non-contiguous tournament ords', () => {
    const rowT1 =
      '300;Beta;1;1600;10;15;1;3;5100;1700;-100;0.33;1;-0.5;-7;1610;13;0.33;NORMAL'
    const rowT3 =
      '300;Beta;1;1610;13;15;2;4;6800;1705;-100;0.5;2;0;0;1625;17;0.5;NORMAL'
    const p1 = mapAuditRowToPlayer(rowT1.split(';'))
    const p3 = mapAuditRowToPlayer(rowT3.split(';'))
    const idx = buildPlayerIndex([
      mkTournament(1, [p1]),
      mkTournament(3, [p3]),
    ])
    const one = idx.find(x => x.fexerjId === 300)
    expect(one).toBeDefined()
    expect(one.initialRating).toBe(1600)
    expect(one.finalRating).toBe(1625)
    expect(one.netDelta).toBe(25)
    expect(one.tournaments.map(t => t.ord)).toEqual([1, 3])
  })

  it('uses name fallback key when fexerjId is null', () => {
    const cells = SAMPLE_AUDIT_ROW.split(';')
    cells[0] = 'not-an-id'
    const p = mapAuditRowToPlayer(cells)
    expect(p.fexerjId).toBe(null)
    const idx = buildPlayerIndex([mkTournament(1, [p])])
    expect(idx).toHaveLength(1)
    expect(idx[0].groupKey).toBe('name:João Silva')
  })

  it('telescoping: sum of per-tournament deltas equals netDelta when all deltas defined', () => {
    const row1 =
      '400;Chain;1;1500;5;15;1;2;3000;1500;0;0.5;1;0;0;1520;7;0.5;NORMAL'
    const row2 =
      '400;Chain;1;1520;7;15;2;4;6000;1520;0;0.5;2;0;0;1545;11;0.5;NORMAL'
    const p1 = mapAuditRowToPlayer(row1.split(';'))
    const p2 = mapAuditRowToPlayer(row2.split(';'))
    const idx = buildPlayerIndex([mkTournament(1, [p1]), mkTournament(2, [p2])])
    const pl = idx.find(x => x.fexerjId === 400)
    expect(pl).toBeDefined()
    const sumDelta = pl.tournaments.reduce((s, t) => s + (t.delta ?? 0), 0)
    expect(pl.netDelta).toBe(sumDelta)
    expect(pl.netDelta).toBe(pl.finalRating - pl.initialRating)
  })

  it('leaves netDelta null when initial or final rating is missing', () => {
    const cells = SAMPLE_AUDIT_ROW.split(';')
    cells[3] = ''
    const p = mapAuditRowToPlayer(cells)
    const idx = buildPlayerIndex([mkTournament(1, [p])])
    expect(idx[0].initialRating).toBe(null)
    expect(idx[0].netDelta).toBe(null)
  })

  it('when names compare equal and both lack fexerjId, breaks tie with groupKey', () => {
    const a = 'xx;Silva;1;1500;5;15;1;2;3000;1500;0;0.5;1;0;0;1510;7;0.5;NORMAL'.split(';')
    const b = 'yy;SILVA;1;1510;7;15;1;2;3100;1510;0;0.5;1;0;0;1520;9;0.5;NORMAL'.split(';')
    const pa = mapAuditRowToPlayer(a)
    const pb = mapAuditRowToPlayer(b)
    expect(pa.fexerjId).toBe(null)
    expect(pb.fexerjId).toBe(null)
    const idx = buildPlayerIndex([mkTournament(1, [pa]), mkTournament(2, [pb])])
    expect(idx).toHaveLength(2)
    const keysInOrder = idx.map(x => x.groupKey)
    expect(keysInOrder).toEqual([...keysInOrder].sort((a, b) => a.localeCompare(b)))
    expect('Silva'.localeCompare('SILVA', 'pt-BR', { sensitivity: 'base' })).toBe(0)
  })
})

describe('parseRunResult', () => {
  it('returns tournaments from ZIP audit files', async () => {
    const audit = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}`
    const blob = await zipFromEntries({
      'Audit_of_Tournament_1.csv': audit,
    })
    const result = await parseRunResult(blob, TOURNAMENTS_CSV)
    expect(result.tournaments).toHaveLength(1)
    expect(result.tournaments[0].ord).toBe(1)
    expect(result.tournaments[0].name).toBe('Copa Teste')
    expect(result.tournaments[0].players).toHaveLength(1)
    expect(result.tournaments[0].players[0].newRating).toBe(1823)
  })

  it('sorts tournaments by Ord when filenames are out of order', async () => {
    const audit1 = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}`
    const row2 =
      '101;Maria;2;1650;40;20;2;4;7200;1800;-150;0.5;2.0;-0.25;-5;1658;44;0.5;NORMAL'
    const audit2 = `${AUDIT_FILE_HEADER}\n${row2}`
    const z = new JSZip()
    z.file('Audit_of_Tournament_2.csv', audit2)
    z.file('Audit_of_Tournament_1.csv', audit1)
    const blob = await z.generateAsync({ type: 'blob' })
    const tournamentsCsv = `${TOURNAMENTS_CSV}\n2;88888;Segundo;;SS;0;1`
    const result = await parseRunResult(blob, tournamentsCsv)
    expect(result.tournaments.map(t => t.ord)).toEqual([1, 2])
  })

  it('throws when ZIP has no audit CSVs', async () => {
    const blob = await zipFromEntries({ readme: 'x' })
    await expect(parseRunResult(blob, TOURNAMENTS_CSV)).rejects.toThrow(/nenhum Audit/)
  })

  it('finds audit files inside a nested folder in the ZIP', async () => {
    const audit = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}`
    const z = new JSZip()
    z.folder('out').file('Audit_of_Tournament_1.csv', audit)
    const blob = await z.generateAsync({ type: 'blob' })
    const result = await parseRunResult(blob, TOURNAMENTS_CSV)
    expect(result.tournaments[0].players).toHaveLength(1)
  })

  it('wraps parseAuditCsv failures with tournament context', async () => {
    const blob = await zipFromEntries({
      'Audit_of_Tournament_1.csv': 'not-a-valid-audit\n',
    })
    await expect(parseRunResult(blob, TOURNAMENTS_CSV)).rejects.toThrow(/Audit_of_Tournament_1/)
  })

  it('uses Torneio ord when tournaments.csv has no row for that Ord', async () => {
    const audit = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}`
    const blob = await zipFromEntries({ 'Audit_of_Tournament_7.csv': audit })
    const result = await parseRunResult(blob, TOURNAMENTS_CSV)
    expect(result.tournaments[0].ord).toBe(7)
    expect(result.tournaments[0].name).toBe('Torneio 7')
  })

  it('audit Rn matches RatingList_after Rtg_Nat for every player (regression guard)', async () => {
    const audit = `${AUDIT_FILE_HEADER}\n${SAMPLE_AUDIT_ROW}`
    const ratingList = `${RATING_LIST_HEADER}\n100;;M;João Silva;1823;;;;;;55;;;`
    const blob = await zipFromEntries({
      'Audit_of_Tournament_1.csv': audit,
      'RatingList_after_1.csv': ratingList,
    })
    const result = await parseRunResult(blob, TOURNAMENTS_CSV)
    const zipRead = await JSZip.loadAsync(blob)
    const rlText = await zipRead.file('RatingList_after_1.csv').async('string')
    const rtgMap = parseRatingListAfterCsv(rlText)
    for (const p of result.tournaments[0].players) {
      if (p.fexerjId == null) continue
      expect(rtgMap.get(p.fexerjId)).toBe(p.newRating)
    }
  })
})
