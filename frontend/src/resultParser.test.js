import JSZip from 'jszip'
import { describe, it, expect } from 'vitest'
import {
  AUDIT_FILE_HEADER,
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
