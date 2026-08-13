/** Must match backend `validator.py` `_PLAYERS_HEADER`. */
export const PLAYERS_HEADER =
  'Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints'

/** Must match backend `validator.py` `_TOURNAMENTS_HEADER`. */
export const TOURNAMENTS_HEADER = 'Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj'

// The two headers below are spelled out in full, rather than composed from
// the ones above, so `tests/test_contract.py` can catch drift by matching the
// literal string the calculator writes.

/** Must match backend `validator.py` `_FIDE_TOURNAMENTS_HEADER`. */
export const FIDE_TOURNAMENTS_HEADER = 'Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj;TimeControl'

/** Must match calculator `calculator/fide/ratinglist.py` `FIDE_HEADER`. */
export const FIDE_PLAYERS_HEADER =
  'Id_No;Id_CBX;Title;Name;ClubName;Birthday;Sex;Fed;Status;Rtg_Std;Games_Std;K_Std;FirstTrn_Std;LastPlayed_Std;RtgFide_Std;FideDate_Std;AccGames_Std;AccSumOpp_Std;AccPts_Std;AccSince_Std;Rtg_Rpd;Games_Rpd;K_Rpd;FirstTrn_Rpd;LastPlayed_Rpd;RtgFide_Rpd;FideDate_Rpd;AccGames_Rpd;AccSumOpp_Rpd;AccPts_Rpd;AccSince_Rpd;Rtg_Blz;Games_Blz;K_Blz;FirstTrn_Blz;LastPlayed_Blz;RtgFide_Blz;FideDate_Blz;AccGames_Blz;AccSumOpp_Blz;AccPts_Blz;AccSince_Blz'

const FIDE_PLAYERS_COLUMN_COUNT = 42

const VALID_TOURNAMENT_TYPES = new Set(['SS', 'RR', 'ST'])
const VALID_TIME_CONTROLS = new Set(['STD', 'RPD', 'BLZ'])

const ENCODING_ERROR_PT =
  'codificação inválida — salve o arquivo em UTF-8 (no Excel: "Salvar como" → "CSV UTF-8 (delimitado por vírgula)").'

/**
 * @typedef {Object} CsvValidationError
 * @property {string} message
 * @property {string} [rawLine] Single offending CSV row (semicolon-separated).
 * @property {string[]} [rawLines] Multiple rows (e.g. duplicate id).
 * @property {number} [highlightColumn] Zero-based column index to highlight in rawLine/rawLines.
 */

/** @param {string} message @returns {CsvValidationError} */
export function csvMessageError(message) {
  return { message }
}

/**
 * @param {string} message
 * @param {string} rawLine
 * @param {number} [highlightColumn]
 * @returns {CsvValidationError}
 */
function csvRowError(message, rawLine, highlightColumn) {
  /** @type {CsvValidationError} */
  const err = { message, rawLine }
  if (highlightColumn != null) err.highlightColumn = highlightColumn
  return err
}

/**
 * @param {string} message
 * @param {string[]} rawLines
 * @param {number} [highlightColumn]
 * @returns {CsvValidationError}
 */
function csvDuplicateError(message, rawLines, highlightColumn) {
  /** @type {CsvValidationError} */
  const err = { message, rawLines }
  if (highlightColumn != null) err.highlightColumn = highlightColumn
  return err
}

/**
 * Decode CSV upload bytes (UTF-8 with optional BOM, then Windows-1252).
 * Mirrors `backend/upload_text.py`.
 * @param {Uint8Array} bytes
 * @param {string} filename
 * @returns {string}
 */
export function decodeCsvUpload(bytes, filename) {
  let start = 0
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    start = 3
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(start))
  } catch {
    try {
      return new TextDecoder('windows-1252').decode(bytes)
    } catch {
      throw new Error(`${filename}: ${ENCODING_ERROR_PT}`)
    }
  }
}

/**
 * @param {File} file
 * @returns {Promise<string>}
 */
export async function readCsvFile(file) {
  const bytes = new Uint8Array(await file.arrayBuffer())
  return decodeCsvUpload(bytes, file.name || 'arquivo.csv')
}

/**
 * @param {string} line
 * @returns {string[]}
 */
function splitCsvLine(line) {
  return line.split(';')
}

/**
 * @param {string} raw
 * @returns {boolean}
 */
function rowHasContent(raw) {
  return splitCsvLine(raw).some(cell => cell.trim().length > 0)
}

/**
 * @param {string} value
 * @param {string} field
 * @param {number} rowNum
 * @param {string} prefix
 * @param {number} columnIndex
 * @param {string} rawLine
 * @param {{ required?: boolean }} [opts]
 * @returns {CsvValidationError[]}
 */
function validateIdCell(
  value,
  field,
  rowNum,
  prefix,
  columnIndex,
  rawLine,
  { required = false } = {},
) {
  /** @type {CsvValidationError[]} */
  const errors = []
  const trimmed = (value ?? '').trim()
  if (!trimmed) {
    if (required) {
      errors.push(
        csvRowError(`${prefix} linha ${rowNum}: ${field} é obrigatório`, rawLine, columnIndex),
      )
    }
    return errors
  }
  const raw = String(value ?? '')
  if (raw.includes('\uFFFD')) {
    errors.push(
      csvRowError(
        `${prefix} linha ${rowNum}: ${field} contém caractere inválido — ${ENCODING_ERROR_PT}`,
        rawLine,
        columnIndex,
      ),
    )
    return errors
  }
  if (raw.includes('\u00a0')) {
    errors.push(
      csvRowError(
        `${prefix} linha ${rowNum}: ${field} contém espaço não separável (NBSP) — corrija a célula no Excel`,
        rawLine,
        columnIndex,
      ),
    )
    return errors
  }
  if (!/^\d+$/.test(trimmed)) {
    errors.push(
      csvRowError(
        `${prefix} linha ${rowNum}: ${field} deve ser um número inteiro`,
        rawLine,
        columnIndex,
      ),
    )
  }
  return errors
}

/**
 * Structural checks for the 42-column format of the per-game model. The
 * per-modality rules (rating floor, accumulator columns, birthday) stay with
 * the server: this pass exists for immediate feedback on the offending row,
 * not to be a second implementation of the model.
 *
 * @param {string[]} lines
 * @returns {CsvValidationError[]}
 */
function validateFidePlayersRows(lines) {
  const prefix = 'players.csv'
  /** @type {CsvValidationError[]} */
  const errors = []
  /** @type {Map<string, { rowNum: number, rawLine: string }>} */
  const idNoSeen = new Map()
  /** @type {Map<string, { rowNum: number, rawLine: string }>} */
  const idCbxSeen = new Map()

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i]
    const rowNum = i + 1
    if (!rowHasContent(line)) continue

    const row = splitCsvLine(line)
    if (row.length !== FIDE_PLAYERS_COLUMN_COUNT) {
      errors.push(
        csvRowError(
          `${prefix} linha ${rowNum}: esperadas ${FIDE_PLAYERS_COLUMN_COUNT} colunas, encontradas ${row.length}`,
          line,
        ),
      )
      continue
    }

    const idNo = row[0].trim()
    const idCbx = row[1].trim()

    errors.push(
      ...validateIdCell(row[0], 'Id_No', rowNum, prefix, 0, line, { required: true }),
    )
    if (idCbx) errors.push(...validateIdCell(row[1], 'Id_CBX', rowNum, prefix, 1, line))
    if (!row[3].trim()) {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: Name é obrigatório`, line, 3))
    }

    if (idNo) {
      const prev = idNoSeen.get(idNo)
      if (prev != null) {
        errors.push(
          csvDuplicateError(
            `${prefix}: Id_No duplicado: ${idNo} (linhas ${prev.rowNum} e ${rowNum})`,
            [prev.rawLine, line],
            0,
          ),
        )
      } else {
        idNoSeen.set(idNo, { rowNum, rawLine: line })
      }
    }

    if (idCbx) {
      const prev = idCbxSeen.get(idCbx)
      if (prev != null) {
        errors.push(
          csvDuplicateError(
            `${prefix}: Id_CBX duplicado: ${idCbx} (linhas ${prev.rowNum} e ${rowNum})`,
            [prev.rawLine, line],
            1,
          ),
        )
      } else {
        idCbxSeen.set(idCbx, { rowNum, rawLine: line })
      }
    }
  }

  return errors
}

/**
 * @param {string} content
 * @param {'legacy' | 'fide' | 'compare'} [mode] Which formats are acceptable.
 * @returns {CsvValidationError[]}
 */
export function validatePlayersCsv(content, mode = 'legacy') {
  const prefix = 'players.csv'
  /** @type {CsvValidationError[]} */
  const errors = []
  const lines = content.split(/\r?\n/)

  if (lines.length === 0 || !lines.some(line => line.length > 0)) {
    return [csvMessageError(`${prefix}: arquivo vazio`)]
  }

  // Only the current model is single-format. The per-game model reads both,
  // and which of the two a given mode accepts is the server's call — saying
  // "invalid" here would stop the file before the server can explain why.
  if (mode !== 'legacy' && lines[0].trim() === FIDE_PLAYERS_HEADER) {
    return validateFidePlayersRows(lines)
  }

  if (lines[0].trim() !== PLAYERS_HEADER) {
    if (mode !== 'legacy') {
      return [
        csvMessageError(
          `${prefix}: cabeçalho inválido — aceito o formato de 12 colunas ou o de ` +
            `${FIDE_PLAYERS_COLUMN_COUNT} colunas do modelo por partida.`,
        ),
      ]
    }
    return [csvMessageError(`${prefix}: cabeçalho inválido — esperado '${PLAYERS_HEADER}'`)]
  }

  /** @type {Map<string, { rowNum: number, rawLine: string }>} */
  const idNoSeen = new Map()
  /** @type {Map<string, { rowNum: number, rawLine: string }>} */
  const idCbxSeen = new Map()

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i]
    const rowNum = i + 1
    if (!rowHasContent(line)) continue

    const row = splitCsvLine(line)
    if (row.length !== 12) {
      errors.push(
        csvRowError(
          `${prefix} linha ${rowNum}: esperadas 12 colunas, encontradas ${row.length}`,
          line,
        ),
      )
      continue
    }

    const idNo = row[0].trim()
    const idCbx = row[1].trim()
    const name = row[3].trim()
    const rtgNat = row[4].trim()
    const totalGames = row[9].trim()
    const sumOppon = row[10].trim()
    const totalPoints = row[11].trim()

    errors.push(
      ...validateIdCell(row[0], 'Id_No', rowNum, prefix, 0, line, { required: true }),
    )
    if (idCbx) errors.push(...validateIdCell(row[1], 'Id_CBX', rowNum, prefix, 1, line))

    if (!name) {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: Name é obrigatório`, line, 3))
    }
    if (!rtgNat) {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: Rtg_Nat é obrigatório`, line, 4))
    }
    if (!totalGames) {
      errors.push(
        csvRowError(`${prefix} linha ${rowNum}: TotalNumGames é obrigatório`, line, 9),
      )
    }
    if (!sumOppon) {
      errors.push(
        csvRowError(`${prefix} linha ${rowNum}: SumOpponRating é obrigatório`, line, 10),
      )
    }
    if (!totalPoints) {
      errors.push(
        csvRowError(`${prefix} linha ${rowNum}: TotalPoints é obrigatório`, line, 11),
      )
    }

    if (rtgNat && !/^-?\d+$/.test(rtgNat)) {
      errors.push(
        csvRowError(`${prefix} linha ${rowNum}: Rtg_Nat deve ser um número inteiro`, line, 4),
      )
    }
    if (totalGames && !/^-?\d+$/.test(totalGames)) {
      errors.push(
        csvRowError(
          `${prefix} linha ${rowNum}: TotalNumGames deve ser um número inteiro`,
          line,
          9,
        ),
      )
    }
    if (sumOppon && !/^-?\d+$/.test(sumOppon)) {
      errors.push(
        csvRowError(
          `${prefix} linha ${rowNum}: SumOpponRating deve ser um número inteiro`,
          line,
          10,
        ),
      )
    }
    if (totalPoints) {
      const n = Number.parseFloat(totalPoints.replace(',', '.'))
      if (Number.isNaN(n)) {
        errors.push(
          csvRowError(
            `${prefix} linha ${rowNum}: TotalPoints deve ser um número válido`,
            line,
            11,
          ),
        )
      }
    }

    if (idNo) {
      const prev = idNoSeen.get(idNo)
      if (prev != null) {
        errors.push(
          csvDuplicateError(
            `${prefix}: Id_No duplicado: ${idNo} (linhas ${prev.rowNum} e ${rowNum})`,
            [prev.rawLine, line],
            0,
          ),
        )
      } else {
        idNoSeen.set(idNo, { rowNum, rawLine: line })
      }
    }

    if (idCbx) {
      const prev = idCbxSeen.get(idCbx)
      if (prev != null) {
        errors.push(
          csvDuplicateError(
            `${prefix}: Id_CBX duplicado: ${idCbx} (linhas ${prev.rowNum} e ${rowNum})`,
            [prev.rawLine, line],
            1,
          ),
        )
      } else {
        idCbxSeen.set(idCbx, { rowNum, rawLine: line })
      }
    }
  }

  return errors
}

/**
 * @param {string} content
 * @param {'legacy' | 'fide' | 'compare'} [mode] Which header the file must carry.
 * @returns {CsvValidationError[]}
 */
export function validateTournamentsCsv(content, mode = 'legacy') {
  const prefix = 'tournaments.csv'
  /** @type {CsvValidationError[]} */
  const errors = []
  const lines = content.split(/\r?\n/)
  const perGameModel = mode !== 'legacy'
  const expectedColumns = perGameModel ? 8 : 7

  if (lines.length === 0 || !lines.some(line => line.length > 0)) {
    return [csvMessageError(`${prefix}: arquivo vazio`)]
  }

  if (lines[0].trim() !== (perGameModel ? FIDE_TOURNAMENTS_HEADER : TOURNAMENTS_HEADER)) {
    return [
      csvMessageError(
        perGameModel
          ? `${prefix}: cabeçalho inválido — o modelo por partida precisa da coluna TimeControl. ` +
              `Esperado '${FIDE_TOURNAMENTS_HEADER}'`
          : `${prefix}: cabeçalho inválido — esperado '${TOURNAMENTS_HEADER}'`,
      ),
    ]
  }

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i]
    const rowNum = i + 1
    if (!rowHasContent(line)) continue

    const row = splitCsvLine(line)
    if (row.length !== expectedColumns) {
      errors.push(
        csvRowError(
          `${prefix} linha ${rowNum}: esperadas ${expectedColumns} colunas, encontradas ${row.length}`,
          line,
        ),
      )
      continue
    }

    const name = row[2].trim()
    const type = row[4].trim()
    const isIrt = row[5].trim()
    const isFex = row[6].trim()

    errors.push(...validateIdCell(row[0], 'Ord', rowNum, prefix, 0, line, { required: true }))
    errors.push(...validateIdCell(row[1], 'CrId', rowNum, prefix, 1, line, { required: true }))

    if (!name) errors.push(csvRowError(`${prefix} linha ${rowNum}: Name é obrigatório`, line, 2))
    if (!type) errors.push(csvRowError(`${prefix} linha ${rowNum}: Type é obrigatório`, line, 4))
    if (!isIrt) {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: IsIrt é obrigatório`, line, 5))
    }
    if (!isFex) {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: IsFexerj é obrigatório`, line, 6))
    }

    if (type && !VALID_TOURNAMENT_TYPES.has(type)) {
      errors.push(
        csvRowError(
          `${prefix} linha ${rowNum}: Type '${type}' inválido; deve ser SS, RR ou ST`,
          line,
          4,
        ),
      )
    }
    if (isIrt && isIrt !== '0' && isIrt !== '1') {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: IsIrt deve ser 0 ou 1`, line, 5))
    }
    if (isFex && isFex !== '0' && isFex !== '1') {
      errors.push(csvRowError(`${prefix} linha ${rowNum}: IsFexerj deve ser 0 ou 1`, line, 6))
    }

    if (perGameModel) {
      const timeControl = row[7].trim()
      if (!timeControl) {
        errors.push(csvRowError(`${prefix} linha ${rowNum}: TimeControl é obrigatório`, line, 7))
      } else if (!VALID_TIME_CONTROLS.has(timeControl.toUpperCase())) {
        errors.push(
          csvRowError(
            `${prefix} linha ${rowNum}: TimeControl '${timeControl}' inválido; deve ser STD, RPD ou BLZ`,
            line,
            7,
          ),
        )
      }
    }
  }

  return errors
}

/**
 * @param {File} file
 * @param {'legacy' | 'fide' | 'compare'} [mode]
 * @returns {Promise<CsvValidationError[]>}
 */
export async function validatePlayersCsvFile(file, mode = 'legacy') {
  try {
    const content = await readCsvFile(file)
    return validatePlayersCsv(content, mode)
  } catch (e) {
    return [csvMessageError(e instanceof Error ? e.message : String(e))]
  }
}

/**
 * @param {File} file
 * @param {'legacy' | 'fide' | 'compare'} [mode]
 * @returns {Promise<CsvValidationError[]>}
 */
export async function validateTournamentsCsvFile(file, mode = 'legacy') {
  try {
    const content = await readCsvFile(file)
    return validateTournamentsCsv(content, mode)
  } catch (e) {
    return [csvMessageError(e instanceof Error ? e.message : String(e))]
  }
}
