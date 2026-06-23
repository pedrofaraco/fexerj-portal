import { describe, expect, it } from 'vitest'

import {
  PLAYERS_HEADER,
  TOURNAMENTS_HEADER,
  decodeCsvUpload,
  validatePlayersCsv,
  validatePlayersCsvFile,
  validateTournamentsCsv,
  validateTournamentsCsvFile,
} from './csvUploadValidation'

const VALID_PLAYER_ROW =
  '3741;;;Roberto Oliveira Lima, Marcio;1500;CLUB A;01/01/1990;M;BRA;50;0;0'

function playersCsv(...rows) {
  return [PLAYERS_HEADER, ...rows].join('\n')
}

function tournamentsCsv(...rows) {
  return [TOURNAMENTS_HEADER, ...rows].join('\n')
}

describe('decodeCsvUpload', () => {
  it('decodes UTF-8 with BOM', () => {
    const bytes = new Uint8Array([0xef, 0xbb, 0xbf, ...new TextEncoder().encode('a;b')])
    expect(decodeCsvUpload(bytes, 'test.csv')).toBe('a;b')
  })

  it('falls back to Windows-1252 for cp1252 bytes', () => {
    const bytes = new Uint8Array([0xa0, 0x39, 0x35]) // NBSP + "95"
    expect(decodeCsvUpload(bytes, 'test.csv')).toBe('\u00a095')
  })
})

describe('validatePlayersCsv', () => {
  it('accepts a valid file', () => {
    expect(validatePlayersCsv(playersCsv(VALID_PLAYER_ROW))).toEqual([])
  })

  it('rejects empty file', () => {
    expect(validatePlayersCsv('')).toEqual(['players.csv: arquivo vazio'])
  })

  it('rejects wrong header', () => {
    const errors = validatePlayersCsv('Id_No;Name\n1;Test\n')
    expect(errors[0]).toMatch(/cabeçalho inválido/)
  })

  it('rejects wrong column count', () => {
    const errors = validatePlayersCsv(playersCsv('1;Player One'))
    expect(errors[0]).toMatch(/esperadas 12 colunas/)
  })

  it('skips blank lines', () => {
    expect(validatePlayersCsv(playersCsv(VALID_PLAYER_ROW, '', '   ;;;   '))).toEqual([])
  })

  it('rejects missing Id_No', () => {
    const row = ';;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(validatePlayersCsv(playersCsv(row)).some(e => e.includes('Id_No é obrigatório'))).toBe(
      true,
    )
  })

  it('rejects duplicate Id_No', () => {
    const errors = validatePlayersCsv(playersCsv(VALID_PLAYER_ROW, VALID_PLAYER_ROW))
    expect(errors.some(e => e.includes('Id_No duplicado'))).toBe(true)
  })

  it('rejects NBSP in Id_CBX', () => {
    const row = `5304;\u00a095178;;CALEB ELIAS;1446;CLUB;01/01/1990;M;BRA;51;0;0`
    const errors = validatePlayersCsv(playersCsv(row))
    expect(errors.some(e => e.includes('NBSP'))).toBe(true)
  })

  it('rejects non-integer Rtg_Nat', () => {
    const row = '3741;;;Roberto;abc;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(validatePlayersCsv(playersCsv(row)).some(e => e.includes('Rtg_Nat'))).toBe(true)
  })

  it('rejects invalid Id_No characters', () => {
    const row = 'abc;;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(
      validatePlayersCsv(playersCsv(row)).some(e => e.includes('Id_No deve ser um número inteiro')),
    ).toBe(true)
  })

  it('rejects replacement character in Id_No', () => {
    const row = `\uFFFD123;;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;0`
    expect(
      validatePlayersCsv(playersCsv(row)).some(e => e.includes('Id_No contém caractere inválido')),
    ).toBe(true)
  })

  it('rejects missing Name and numeric fields', () => {
    const row = '3741;;; ;1500;CLUB;01/01/1990;M;BRA;;;'
    const errors = validatePlayersCsv(playersCsv(row))
    expect(errors.some(e => e.includes('Name é obrigatório'))).toBe(true)
    expect(errors.some(e => e.includes('TotalNumGames é obrigatório'))).toBe(true)
    expect(errors.some(e => e.includes('SumOpponRating é obrigatório'))).toBe(true)
    expect(errors.some(e => e.includes('TotalPoints é obrigatório'))).toBe(true)
  })

  it('rejects invalid TotalPoints', () => {
    const row = '3741;;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;not-a-number'
    expect(
      validatePlayersCsv(playersCsv(row)).some(e => e.includes('TotalPoints deve ser um número')),
    ).toBe(true)
  })

  it('rejects duplicate Id_CBX', () => {
    const rowA = '3741;90107;;Player A;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    const rowB = '3742;90107;;Player B;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(validatePlayersCsv(playersCsv(rowA, rowB)).some(e => e.includes('Id_CBX duplicado'))).toBe(
      true,
    )
  })
})

describe('validateTournamentsCsv', () => {
  it('accepts a valid file', () => {
    expect(validateTournamentsCsv(tournamentsCsv('1;99999;Copa;2025-01-01;RR;0;1'))).toEqual([])
  })

  it('rejects empty file', () => {
    expect(validateTournamentsCsv('')).toEqual(['tournaments.csv: arquivo vazio'])
  })

  it('rejects wrong header', () => {
    expect(validateTournamentsCsv('Ord;Name\n1;Test\n')[0]).toMatch(/cabeçalho inválido/)
  })

  it('rejects wrong column count', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa'))
    expect(errors[0]).toMatch(/esperadas 7 colunas/)
  })

  it('rejects invalid Type', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa;;XX;0;1'))
    expect(errors.some(e => e.includes("Type 'XX' inválido"))).toBe(true)
  })

  it('rejects invalid IsIrt', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa;;RR;2;1'))
    expect(errors.some(e => e.includes('IsIrt deve ser 0 ou 1'))).toBe(true)
  })

  it('rejects invalid IsFexerj and missing required fields', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;;Copa;;RR;0;9'))
    expect(errors.some(e => e.includes('CrId é obrigatório'))).toBe(true)
    expect(errors.some(e => e.includes('IsFexerj deve ser 0 ou 1'))).toBe(true)
  })

  it('rejects invalid CrId', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;abc;Copa;;RR;0;1'))
    expect(errors.some(e => e.includes('CrId deve ser um número inteiro'))).toBe(true)
  })
})

describe('validatePlayersCsvFile', () => {
  it('validates a real File object', async () => {
    const file = new File([playersCsv(VALID_PLAYER_ROW)], 'players.csv', { type: 'text/csv' })
    await expect(validatePlayersCsvFile(file)).resolves.toEqual([])
  })
})

describe('validateTournamentsCsvFile', () => {
  it('validates a real File object', async () => {
    const file = new File(
      [tournamentsCsv('1;99999;Copa;2025-01-01;RR;0;1')],
      'tournaments.csv',
      { type: 'text/csv' },
    )
    await expect(validateTournamentsCsvFile(file)).resolves.toEqual([])
  })
})
