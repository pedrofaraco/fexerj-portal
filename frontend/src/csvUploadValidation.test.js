import { describe, expect, it } from 'vitest'

import {
  FIDE_PLAYERS_HEADER,
  FIDE_TOURNAMENTS_HEADER,
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

/** @param {import('./csvUploadValidation').CsvValidationError | string} error */
function errorMessage(error) {
  return typeof error === 'string' ? error : error.message
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
    expect(errorMessage(validatePlayersCsv('')[0])).toBe('players.csv: arquivo vazio')
    expect(validatePlayersCsv('')[0].rawLine).toBeUndefined()
  })

  it('rejects wrong header', () => {
    const errors = validatePlayersCsv('Id_No;Name\n1;Test\n')
    expect(errorMessage(errors[0])).toMatch(/cabeçalho inválido/)
    expect(errors[0].rawLine).toBeUndefined()
  })

  it('rejects wrong column count', () => {
    const row = '1;Player One'
    const errors = validatePlayersCsv(playersCsv(row))
    expect(errorMessage(errors[0])).toMatch(/esperadas 12 colunas/)
    expect(errors[0].rawLine).toBe(row)
  })

  it('skips blank lines', () => {
    expect(validatePlayersCsv(playersCsv(VALID_PLAYER_ROW, '', '   ;;;   '))).toEqual([])
  })

  it('rejects missing Id_No', () => {
    const row = ';;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(validatePlayersCsv(playersCsv(row)).some(e => errorMessage(e).includes('Id_No é obrigatório'))).toBe(
      true,
    )
  })

  it('rejects duplicate Id_No', () => {
    const errors = validatePlayersCsv(playersCsv(VALID_PLAYER_ROW, VALID_PLAYER_ROW))
    expect(errors.some(e => errorMessage(e).includes('Id_No duplicado'))).toBe(true)
  })

  it('rejects NBSP in Id_CBX with the offending line and column', () => {
    const row = `5304;\u00a095178;;CALEB ELIAS;1446;CLUB;01/01/1990;M;BRA;51;0;0`
    const errors = validatePlayersCsv(playersCsv(row))
    const err = errors.find(e => errorMessage(e).includes('NBSP'))
    expect(err?.rawLine).toBe(row)
    expect(err?.highlightColumn).toBe(1)
  })

  it('rejects non-integer Rtg_Nat', () => {
    const row = '3741;;;Roberto;abc;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(validatePlayersCsv(playersCsv(row)).some(e => errorMessage(e).includes('Rtg_Nat'))).toBe(true)
  })

  it('rejects invalid Id_No characters', () => {
    const row = 'abc;;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    expect(
      validatePlayersCsv(playersCsv(row)).some(e =>
        errorMessage(e).includes('Id_No deve ser um número inteiro'),
      ),
    ).toBe(true)
  })

  it('rejects replacement character in Id_No', () => {
    const row = `\uFFFD123;;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;0`
    expect(
      validatePlayersCsv(playersCsv(row)).some(e =>
        errorMessage(e).includes('Id_No contém caractere inválido'),
      ),
    ).toBe(true)
  })

  it('rejects missing Name and numeric fields', () => {
    const row = '3741;;; ;1500;CLUB;01/01/1990;M;BRA;;;'
    const errors = validatePlayersCsv(playersCsv(row))
    expect(errors.some(e => errorMessage(e).includes('Name é obrigatório'))).toBe(true)
    expect(errors.some(e => errorMessage(e).includes('TotalNumGames é obrigatório'))).toBe(true)
    expect(errors.some(e => errorMessage(e).includes('SumOpponRating é obrigatório'))).toBe(true)
    expect(errors.some(e => errorMessage(e).includes('TotalPoints é obrigatório'))).toBe(true)
  })

  it('rejects invalid TotalPoints', () => {
    const row = '3741;;;Roberto;1500;CLUB;01/01/1990;M;BRA;50;0;not-a-number'
    expect(
      validatePlayersCsv(playersCsv(row)).some(e =>
        errorMessage(e).includes('TotalPoints deve ser um número'),
      ),
    ).toBe(true)
  })

  it('rejects duplicate Id_CBX with both lines', () => {
    const rowA = '3741;90107;;Player A;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    const rowB = '3742;90107;;Player B;1500;CLUB;01/01/1990;M;BRA;50;0;0'
    const errors = validatePlayersCsv(playersCsv(rowA, rowB))
    const err = errors.find(e => errorMessage(e).includes('Id_CBX duplicado'))
    expect(err?.rawLines).toEqual([rowA, rowB])
    expect(err?.highlightColumn).toBe(1)
  })
})

describe('validateTournamentsCsv', () => {
  it('accepts a valid file', () => {
    expect(validateTournamentsCsv(tournamentsCsv('1;99999;Copa;2025-01-01;RR;0;1'))).toEqual([])
  })

  it('rejects empty file', () => {
    expect(errorMessage(validateTournamentsCsv('')[0])).toBe('tournaments.csv: arquivo vazio')
  })

  it('rejects wrong header', () => {
    expect(errorMessage(validateTournamentsCsv('Ord;Name\n1;Test\n')[0])).toMatch(/cabeçalho inválido/)
  })

  it('rejects wrong column count', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa'))
    expect(errorMessage(errors[0])).toMatch(/esperadas 7 colunas/)
  })

  it('rejects invalid Type', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa;;XX;0;1'))
    expect(errors.some(e => errorMessage(e).includes("Type 'XX' inválido"))).toBe(true)
  })

  it('rejects invalid IsIrt', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa;;RR;2;1'))
    expect(errors.some(e => errorMessage(e).includes('IsIrt deve ser 0 ou 1'))).toBe(true)
  })

  it('rejects invalid IsFexerj and missing required fields', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;;Copa;;RR;0;9'))
    expect(errors.some(e => errorMessage(e).includes('CrId é obrigatório'))).toBe(true)
    expect(errors.some(e => errorMessage(e).includes('IsFexerj deve ser 0 ou 1'))).toBe(true)
  })

  it('rejects invalid CrId', () => {
    const errors = validateTournamentsCsv(tournamentsCsv('1;abc;Copa;;RR;0;1'))
    expect(errors.some(e => errorMessage(e).includes('CrId deve ser um número inteiro'))).toBe(true)
  })
})

// The per-game model's file formats. Without these, the browser-side check
// rejects the very files the FIDE and compare modes require, the "Executar"
// button never enables, and the server never gets to say anything.
describe('the per-game model formats, by mode', () => {
  const FIDE_TOURNAMENT_ROW = '1;99999;Copa;2026-03-15;RR;0;1;STD'

  function fideTournamentsCsv(...rows) {
    return [FIDE_TOURNAMENTS_HEADER, ...rows].join('\n')
  }

  function fidePlayersCsv(...rows) {
    return [FIDE_PLAYERS_HEADER, ...rows].join('\n')
  }

  const FIDE_PLAYER_ROW =
    '3741;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;'

  describe('tournaments.csv', () => {
    it('accepts the TimeControl header in fide mode', () => {
      expect(validateTournamentsCsv(fideTournamentsCsv(FIDE_TOURNAMENT_ROW), 'fide')).toEqual([])
    })

    it('accepts it in compare mode too', () => {
      expect(validateTournamentsCsv(fideTournamentsCsv(FIDE_TOURNAMENT_ROW), 'compare')).toEqual([])
    })

    it('still rejects it in the current model, which reads seven columns', () => {
      const errors = validateTournamentsCsv(fideTournamentsCsv(FIDE_TOURNAMENT_ROW), 'legacy')
      expect(errorMessage(errors[0])).toMatch(/cabeçalho inválido/)
    })

    it('rejects the seven-column header in fide mode, naming the missing column', () => {
      const errors = validateTournamentsCsv(tournamentsCsv('1;99999;Copa;2026-03-15;RR;0;1'), 'fide')
      expect(errorMessage(errors[0])).toMatch(/TimeControl/)
    })

    it('keeps checking the columns the two formats share', () => {
      const errors = validateTournamentsCsv(fideTournamentsCsv('1;99999;Copa;2026-03-15;XX;2;1;STD'), 'fide')
      expect(errors.some(e => errorMessage(e).includes("Type 'XX' inválido"))).toBe(true)
      expect(errors.some(e => errorMessage(e).includes('IsIrt deve ser 0 ou 1'))).toBe(true)
    })

    it('rejects an unknown TimeControl', () => {
      const errors = validateTournamentsCsv(fideTournamentsCsv('1;99999;Copa;2026-03-15;RR;0;1;RAPIDO'), 'fide')
      expect(errors.some(e => errorMessage(e).includes("TimeControl 'RAPIDO' inválido"))).toBe(true)
    })

    it('rejects a row with the wrong column count', () => {
      const errors = validateTournamentsCsv(fideTournamentsCsv('1;99999;Copa;2026-03-15;RR;0;1'), 'fide')
      expect(errorMessage(errors[0])).toMatch(/esperadas 8 colunas/)
    })
  })

  describe('players.csv', () => {
    it('accepts the 29-column format in fide mode', () => {
      expect(validatePlayersCsv(fidePlayersCsv(FIDE_PLAYER_ROW), 'fide')).toEqual([])
    })

    it('still accepts the 12-column format in fide mode', () => {
      expect(validatePlayersCsv(playersCsv(VALID_PLAYER_ROW), 'fide')).toEqual([])
    })

    it('rejects the 29-column format in the current model', () => {
      const errors = validatePlayersCsv(fidePlayersCsv(FIDE_PLAYER_ROW), 'legacy')
      expect(errorMessage(errors[0])).toMatch(/cabeçalho inválido/)
    })

    it('checks the column count of a 29-column row', () => {
      const errors = validatePlayersCsv(fidePlayersCsv('3741;;;Carlos Mendes;CLUB A'), 'fide')
      expect(errorMessage(errors[0])).toMatch(/esperadas 29 colunas/)
    })

    it('catches a duplicate id in the 29-column format', () => {
      const errors = validatePlayersCsv(fidePlayersCsv(FIDE_PLAYER_ROW, FIDE_PLAYER_ROW), 'fide')
      expect(errors.some(e => errorMessage(e).includes('Id_No duplicado'))).toBe(true)
    })
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
