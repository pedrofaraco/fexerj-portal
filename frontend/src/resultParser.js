import JSZip from 'jszip'

/** Must match calculator `calculator/classes.py` `_AUDIT_FILE_HEADER` */
export const AUDIT_FILE_HEADER =
  'Id_Fexerj;Name;No;Ro;Ind;K;PG;N;Erm;Rm;Dif;We;Nwe;Dw;kDw;Rn;Nind;P;Calc_Rule'

const AUDIT_FILENAME_RE = /^Audit_of_Tournament_(\d+)\.csv$/i

/** @param {string} text */
export function stripUtf8Bom(text) {
  return text.startsWith('\ufeff') ? text.slice(1) : text
}

/**
 * Parse semicolon CSV with header row; returns { headers, rows } rows are string[][].
 * @param {string} text
 */
export function parseSemicolonCsv(text) {
  const lines = stripUtf8Bom(text)
    .split(/\r?\n/)
    .map(l => l.trimEnd())
    .filter(line => line.length > 0)
  if (lines.length === 0) return { headers: [], rows: [] }
  const rows = lines.map(line => line.split(';'))
  const headers = rows[0] ?? []
  const body = rows.slice(1)
  return { headers, rows: body }
}

/**
 * @param {string} tournamentsCsvText
 * @returns {Map<number, { ord: number, crId: number, name: string, endDate: string, type: string, isIrt: boolean, isFexerj: boolean }>}
 */
export function parseTournamentsCsv(tournamentsCsvText) {
  const { headers, rows } = parseSemicolonCsv(tournamentsCsvText)
  const idx = name => headers.findIndex(h => h.trim().toLowerCase() === name.toLowerCase())
  const iOrd = idx('Ord')
  const iCrId = idx('CrId')
  const iName = idx('Name')
  const iEnd = idx('EndDate')
  const iType = idx('Type')
  const iIrt = idx('IsIrt')
  const iFex = idx('IsFexerj')
  const map = new Map()
  for (const row of rows) {
    if (row.every(c => c === '' || c === undefined)) continue
    const ord = Number.parseInt(row[iOrd], 10)
    if (Number.isNaN(ord)) continue
    map.set(ord, {
      ord,
      crId: Number.parseInt(row[iCrId], 10) || 0,
      name: (row[iName] ?? '').trim() || `Torneio ${ord}`,
      endDate: (row[iEnd] ?? '').trim(),
      type: (row[iType] ?? '').trim(),
      isIrt: row[iIrt] === '1',
      isFexerj: row[iFex] === '1',
    })
  }
  return map
}

/**
 * @param {string} text RatingList_after_*.csv body
 * @returns {Map<number, number>} Id_No -> Rtg_Nat
 */
export function parseRatingListAfterCsv(text) {
  const { headers, rows } = parseSemicolonCsv(text)
  const iId = headers.findIndex(h => h.trim() === 'Id_No')
  const iRtg = headers.findIndex(h => h.trim() === 'Rtg_Nat')
  const map = new Map()
  if (iId < 0 || iRtg < 0) return map
  for (const row of rows) {
    const id = Number.parseInt(row[iId], 10)
    if (Number.isNaN(id)) continue
    const rtg = Number.parseFloat(String(row[iRtg]).replace(',', '.'))
    if (!Number.isNaN(rtg)) map.set(id, rtg)
  }
  return map
}

function parseNumericCell(raw) {
  if (raw === undefined || raw === null || raw === '') return null
  const s = String(raw).trim()
  if (s === 'None') return null
  const n = Number.parseFloat(s.replace(',', '.'))
  return Number.isNaN(n) ? null : n
}

function parseIntCell(raw) {
  if (raw === undefined || raw === null || raw === '') return null
  const s = String(raw).trim()
  if (s === 'None') return null
  const n = Number.parseInt(s, 10)
  return Number.isNaN(n) ? null : n
}

/**
 * Map one audit CSV row (array of 19 strings) to player object for UI.
 * @param {string[]} cells
 */
export function mapAuditRowToPlayer(cells) {
  if (cells.length < 19) {
    throw new Error(`Linha de auditoria inválida: esperado 19 colunas, obtido ${cells.length}.`)
  }
  const id = Number.parseInt(cells[0], 10)
  const name = cells[1] ?? ''
  const oldRating = parseNumericCell(cells[3])
  const newRating = parseNumericCell(cells[15])
  let delta = null
  if (oldRating !== null && newRating !== null) delta = newRating - oldRating
  const calcRuleRaw = String(cells[18] ?? '').trim()

  return {
    fexerjId: Number.isNaN(id) ? null : id,
    name,
    oldRating,
    newRating,
    delta,
    calcRule: calcRuleRaw === 'None' || calcRuleRaw === '' ? null : calcRuleRaw,

    gamesBefore: parseIntCell(cells[4]),
    validGames: parseIntCell(cells[7]),
    k: parseNumericCell(cells[5]),
    pointsScored: parseNumericCell(cells[6]),
    erm: parseNumericCell(cells[8]),
    avgOpponRating: parseNumericCell(cells[9]),
    dif: parseNumericCell(cells[10]),
    we: parseNumericCell(cells[11]),
    expectedPoints: parseNumericCell(cells[12]),
    pointsAboveExpected: parseNumericCell(cells[13]),
    kDw: parseNumericCell(cells[14]),
    newTotalGames: parseIntCell(cells[16]),
    pRatio: parseNumericCell(cells[17]),
    boardNo: parseIntCell(cells[2]),
  }
}

/**
 * @param {string} auditCsvText
 */
export function parseAuditCsv(auditCsvText) {
  const { headers, rows } = parseSemicolonCsv(auditCsvText)
  const headerLine = headers.join(';')
  if (headerLine !== AUDIT_FILE_HEADER && !headerLine.startsWith('Id_Fexerj;')) {
    throw new Error('Arquivo de auditoria com cabeçalho inesperado.')
  }
  const players = []
  // Propagate — one malformed row fails the whole tournament parse intentionally:
  // a partial player list would silently misrepresent the engine output.
  for (const row of rows) {
    if (row.every(c => c === '' || c === undefined)) continue
    players.push(mapAuditRowToPlayer(row))
  }
  return players
}

const TYPE_LABEL_PT = {
  SS: 'Suíço individual',
  RR: 'Round-robin',
  ST: 'Suíço por equipes',
}

/**
 * @param {Blob} zipBlob
 * @param {string} tournamentsCsvText
 */
export async function parseRunResult(zipBlob, tournamentsCsvText) {
  const zip = await JSZip.loadAsync(zipBlob)
  const tournamentMap = parseTournamentsCsv(tournamentsCsvText)

  const auditEntries = []
  for (const [path, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue
    const base = path.includes('/') ? path.slice(path.lastIndexOf('/') + 1) : path
    const m = base.match(AUDIT_FILENAME_RE)
    if (m) auditEntries.push({ ord: m[1], file: entry })
  }

  if (auditEntries.length === 0) {
    throw new Error(
      'O arquivo ZIP não contém nenhum Audit_of_Tournament_<n>.csv. Não foi possível montar o resumo.',
    )
  }

  auditEntries.sort((a, b) => Number.parseInt(a.ord, 10) - Number.parseInt(b.ord, 10))

  const tournaments = []

  for (const { ord: ordStr, file } of auditEntries) {
    const ord = Number.parseInt(ordStr, 10)
    const meta = tournamentMap.get(ord)
    const csvText = await file.async('string')
    let players = []
    try {
      players = parseAuditCsv(csvText)
    } catch (e) {
      throw new Error(
        `Erro ao ler Audit_of_Tournament_${ord}.csv: ${e instanceof Error ? e.message : String(e)}`,
      )
    }

    const typeCode = meta?.type ?? ''
    tournaments.push({
      ord,
      crId: meta?.crId ?? null,
      name: meta?.name ?? `Torneio ${ord}`,
      type: typeCode,
      typeLabelPt: TYPE_LABEL_PT[typeCode] ?? typeCode,
      endDate: meta?.endDate ?? '',
      isFexerj: meta?.isFexerj ?? false,
      isIrt: meta?.isIrt ?? false,
      players,
    })
  }

  return {
    zipBlob,
    zipFilename: 'rating_cycle_output.zip',
    tournaments,
  }
}

/**
 * Group audit rows by player (FEXERJ id, or name fallback) for the "Por jogador" view.
 * `tournaments` must be in `ord` ascending order (as returned by `parseRunResult`).
 *
 * @param {Array<{ ord: number, name: string, typeLabelPt: string, crId: number|null, type: string, endDate: string, isFexerj: boolean, isIrt: boolean, players: object[] }>} tournaments
 * @returns {Array<{ groupKey: string, fexerjId: number|null, name: string, initialRating: number|null, finalRating: number|null, netDelta: number|null, tournaments: object[] }>}
 */
export function buildPlayerIndex(tournaments) {
  /** @type {Map<string, { fexerjId: number|null, name: string, tournaments: object[] }>} */
  const groups = new Map()

  for (const t of tournaments ?? []) {
    const meta = {
      ord: t.ord,
      tournamentName: t.name,
      crId: t.crId ?? null,
      type: t.type ?? '',
      typeLabelPt: t.typeLabelPt ?? '',
      endDate: t.endDate ?? '',
      isFexerj: Boolean(t.isFexerj),
      isIrt: Boolean(t.isIrt),
    }

    for (const p of t.players ?? []) {
      const groupKey =
        p.fexerjId != null ? `id:${p.fexerjId}` : `name:${String(p.name ?? '').trim()}`
      let g = groups.get(groupKey)
      if (!g) {
        g = { fexerjId: p.fexerjId, name: p.name ?? '', tournaments: [] }
        groups.set(groupKey, g)
      }
      g.tournaments.push({ ...meta, ...p })
    }
  }

  /** @type {Array<{ groupKey: string, fexerjId: number|null, name: string, initialRating: number|null, finalRating: number|null, netDelta: number|null, tournaments: object[] }>} */
  const out = []

  for (const [groupKey, g] of groups) {
    const rounds = [...g.tournaments].sort((a, b) => a.ord - b.ord)
    const initialRating = rounds.length > 0 ? rounds[0].oldRating ?? null : null
    const finalRating = rounds.length > 0 ? rounds[rounds.length - 1].newRating ?? null : null
    let netDelta = null
    if (initialRating !== null && finalRating !== null) netDelta = finalRating - initialRating

    out.push({
      groupKey,
      fexerjId: g.fexerjId,
      name: g.name,
      initialRating,
      finalRating,
      netDelta,
      tournaments: rounds,
    })
  }

  out.sort((a, b) => {
    const cmp = (a.name || '').localeCompare(b.name || '', 'pt-BR', { sensitivity: 'base' })
    if (cmp !== 0) return cmp
    const ida = a.fexerjId
    const idb = b.fexerjId
    if (ida != null && idb != null) return ida - idb
    if (ida != null) return -1
    if (idb != null) return 1
    return a.groupKey.localeCompare(b.groupKey)
  })

  return out
}
