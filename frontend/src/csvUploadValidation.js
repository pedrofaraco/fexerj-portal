/** Must match backend `validator.py` `_PLAYERS_HEADER`. */
export const PLAYERS_HEADER =
  'Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints'

/** Must match backend `validator.py` `_TOURNAMENTS_HEADER`. */
export const TOURNAMENTS_HEADER = 'Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj'

const VALID_TOURNAMENT_TYPES = new Set(['SS', 'RR', 'ST'])

const ENCODING_ERROR_PT =
  'codificação inválida — salve o arquivo em UTF-8 (no Excel: "Salvar como" → "CSV UTF-8 (delimitado por vírgula)").'

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
 * @param {{ required?: boolean }} [opts]
 * @returns {string[]}
 */
function validateIdCell(value, field, rowNum, prefix, { required = false } = {}) {
  const errors = []
  const trimmed = (value ?? '').trim()
  if (!trimmed) {
    if (required) errors.push(`${prefix} linha ${rowNum}: ${field} é obrigatório`)
    return errors
  }
  const raw = String(value ?? '')
  if (raw.includes('\uFFFD')) {
    errors.push(
      `${prefix} linha ${rowNum}: ${field} contém caractere inválido — ${ENCODING_ERROR_PT}`,
    )
    return errors
  }
  if (raw.includes('\u00a0')) {
    errors.push(
      `${prefix} linha ${rowNum}: ${field} contém espaço não separável (NBSP) — corrija a célula no Excel`,
    )
    return errors
  }
  if (!/^\d+$/.test(trimmed)) {
    errors.push(`${prefix} linha ${rowNum}: ${field} deve ser um número inteiro`)
  }
  return errors
}

/**
 * @param {string} content
 * @returns {string[]}
 */
export function validatePlayersCsv(content) {
  const prefix = 'players.csv'
  const errors = []
  const lines = content.split(/\r?\n/)

  if (lines.length === 0 || !lines.some(line => line.length > 0)) {
    return [`${prefix}: arquivo vazio`]
  }

  if (lines[0].trim() !== PLAYERS_HEADER) {
    return [`${prefix}: cabeçalho inválido — esperado '${PLAYERS_HEADER}'`]
  }

  /** @type {Map<string, number>} */
  const idNoSeen = new Map()
  /** @type {Map<string, number>} */
  const idCbxSeen = new Map()

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i]
    const rowNum = i + 1
    if (!rowHasContent(line)) continue

    const row = splitCsvLine(line)
    if (row.length !== 12) {
      errors.push(`${prefix} linha ${rowNum}: esperadas 12 colunas, encontradas ${row.length}`)
      continue
    }

    const idNo = row[0].trim()
    const idCbx = row[1].trim()
    const name = row[3].trim()
    const rtgNat = row[4].trim()
    const totalGames = row[9].trim()
    const sumOppon = row[10].trim()
    const totalPoints = row[11].trim()

    errors.push(...validateIdCell(row[0], 'Id_No', rowNum, prefix, { required: true }))
    if (idCbx) errors.push(...validateIdCell(row[1], 'Id_CBX', rowNum, prefix))

    if (!name) errors.push(`${prefix} linha ${rowNum}: Name é obrigatório`)
    if (!rtgNat) errors.push(`${prefix} linha ${rowNum}: Rtg_Nat é obrigatório`)
    if (!totalGames) errors.push(`${prefix} linha ${rowNum}: TotalNumGames é obrigatório`)
    if (!sumOppon) errors.push(`${prefix} linha ${rowNum}: SumOpponRating é obrigatório`)
    if (!totalPoints) errors.push(`${prefix} linha ${rowNum}: TotalPoints é obrigatório`)

    if (rtgNat && !/^-?\d+$/.test(rtgNat)) {
      errors.push(`${prefix} linha ${rowNum}: Rtg_Nat deve ser um número inteiro`)
    }
    if (totalGames && !/^-?\d+$/.test(totalGames)) {
      errors.push(`${prefix} linha ${rowNum}: TotalNumGames deve ser um número inteiro`)
    }
    if (sumOppon && !/^-?\d+$/.test(sumOppon)) {
      errors.push(`${prefix} linha ${rowNum}: SumOpponRating deve ser um número inteiro`)
    }
    if (totalPoints) {
      const n = Number.parseFloat(totalPoints.replace(',', '.'))
      if (Number.isNaN(n)) {
        errors.push(`${prefix} linha ${rowNum}: TotalPoints deve ser um número válido`)
      }
    }

    if (idNo) {
      const prev = idNoSeen.get(idNo)
      if (prev != null) {
        errors.push(`${prefix}: Id_No duplicado: ${idNo} (linhas ${prev} e ${rowNum})`)
      } else {
        idNoSeen.set(idNo, rowNum)
      }
    }

    if (idCbx) {
      const prev = idCbxSeen.get(idCbx)
      if (prev != null) {
        errors.push(`${prefix}: Id_CBX duplicado: ${idCbx} (linhas ${prev} e ${rowNum})`)
      } else {
        idCbxSeen.set(idCbx, rowNum)
      }
    }
  }

  return errors
}

/**
 * @param {string} content
 * @returns {string[]}
 */
export function validateTournamentsCsv(content) {
  const prefix = 'tournaments.csv'
  const errors = []
  const lines = content.split(/\r?\n/)

  if (lines.length === 0 || !lines.some(line => line.length > 0)) {
    return [`${prefix}: arquivo vazio`]
  }

  if (lines[0].trim() !== TOURNAMENTS_HEADER) {
    return [`${prefix}: cabeçalho inválido — esperado '${TOURNAMENTS_HEADER}'`]
  }

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i]
    const rowNum = i + 1
    if (!rowHasContent(line)) continue

    const row = splitCsvLine(line)
    if (row.length !== 7) {
      errors.push(`${prefix} linha ${rowNum}: esperadas 7 colunas, encontradas ${row.length}`)
      continue
    }

    const name = row[2].trim()
    const type = row[4].trim()
    const isIrt = row[5].trim()
    const isFex = row[6].trim()

    errors.push(...validateIdCell(row[0], 'Ord', rowNum, prefix, { required: true }))
    errors.push(...validateIdCell(row[1], 'CrId', rowNum, prefix, { required: true }))

    if (!name) errors.push(`${prefix} linha ${rowNum}: Name é obrigatório`)
    if (!type) errors.push(`${prefix} linha ${rowNum}: Type é obrigatório`)
    if (!isIrt) errors.push(`${prefix} linha ${rowNum}: IsIrt é obrigatório`)
    if (!isFex) errors.push(`${prefix} linha ${rowNum}: IsFexerj é obrigatório`)

    if (type && !VALID_TOURNAMENT_TYPES.has(type)) {
      errors.push(
        `${prefix} linha ${rowNum}: Type '${type}' inválido; deve ser SS, RR ou ST`,
      )
    }
    if (isIrt && isIrt !== '0' && isIrt !== '1') {
      errors.push(`${prefix} linha ${rowNum}: IsIrt deve ser 0 ou 1`)
    }
    if (isFex && isFex !== '0' && isFex !== '1') {
      errors.push(`${prefix} linha ${rowNum}: IsFexerj deve ser 0 ou 1`)
    }
  }

  return errors
}

/**
 * @param {File} file
 * @returns {Promise<string[]>}
 */
export async function validatePlayersCsvFile(file) {
  try {
    const content = await readCsvFile(file)
    return validatePlayersCsv(content)
  } catch (e) {
    return [e instanceof Error ? e.message : String(e)]
  }
}

/**
 * @param {File} file
 * @returns {Promise<string[]>}
 */
export async function validateTournamentsCsvFile(file) {
  try {
    const content = await readCsvFile(file)
    return validateTournamentsCsv(content)
  } catch (e) {
    return [e instanceof Error ? e.message : String(e)]
  }
}
