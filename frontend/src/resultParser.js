import JSZip from 'jszip'

/** Must match calculator `calculator/classes.py` `_AUDIT_FILE_HEADER` */
export const AUDIT_FILE_HEADER =
  'Id_Fexerj;Name;No;Ro;Ind;K;PG;N;Erm;Rm;Dif;We;Nwe;Dw;kDw;Rn;Nind;P;Calc_Rule'

/** Must match calculator `calculator/classes.py` `_AUDIT_FILE_PREAMBLE` */
export const AUDIT_PREAMBLE = '# audit_v1'

const AUDIT_FILENAME_RE = /^Audit_of_Tournament_(\d+)\.csv$/i

/** Must match calculator `calculator/fide/audit.py` `PERIOD_AUDIT_PREAMBLE` */
export const FIDE_PERIOD_PREAMBLE = '# fide_period_v1'

/** Must match calculator `calculator/fide/audit.py` `GAMES_AUDIT_PREAMBLE` */
export const FIDE_GAMES_PREAMBLE = '# fide_games_v1'

/** Must match calculator `calculator/compare.py` `COMPARISON_PREAMBLE` */
export const COMPARISON_PREAMBLE = '# fide_comparison_v1'

/** Must match backend `main.py` `_ZIP_NAME_BY_MODE` */
const ZIP_NAME_BY_KIND = {
  legacy: 'rating_cycle_output.zip',
  fide: 'rating_cycle_fide.zip',
  compare: 'rating_cycle_comparison.zip',
}

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
 * @param {string} playersCsvText Initial players.csv (same file uploaded to /run).
 * @returns {{ fexerjNames: Map<number, string>, cbxToFexerj: Map<number, number> }}
 */
export function parsePlayersCsv(playersCsvText) {
  const { headers, rows } = parseSemicolonCsv(playersCsvText ?? '')
  const iId = headers.findIndex(h => h.trim() === 'Id_No')
  const iCbx = headers.findIndex(h => h.trim() === 'Id_CBX')
  const iName = headers.findIndex(h => h.trim() === 'Name')
  /** @type {Map<number, string>} */
  const fexerjNames = new Map()
  /** @type {Map<number, number>} */
  const cbxToFexerj = new Map()
  if (iId < 0) return { fexerjNames, cbxToFexerj }

  for (const row of rows) {
    if (row.every(c => c === '' || c === undefined)) continue
    const fexerjId = parseIdCell(row[iId])
    if (fexerjId == null) continue
    const name = (row[iName] ?? '').trim()
    if (name) fexerjNames.set(fexerjId, name)
    if (iCbx >= 0) {
      const cbxId = parseIdCell(row[iCbx])
      if (cbxId != null) cbxToFexerj.set(cbxId, fexerjId)
    }
  }
  return { fexerjNames, cbxToFexerj }
}

/**
 * Resolve FEXERJ id and canonical name from players.csv for one audit row.
 * @param {ReturnType<typeof mapAuditRowToPlayer>} player
 * @param {{ isIrt: boolean }} tournament
 * @param {{ fexerjNames: Map<number, string>, cbxToFexerj: Map<number, number> }} lookups
 */
export function enrichPlayerFromPlayersCsv(player, tournament, lookups) {
  let fexerjId = player.fexerjId
  if (tournament.isIrt && fexerjId != null) {
    const mapped = lookups.cbxToFexerj.get(fexerjId)
    if (mapped != null) fexerjId = mapped
  }
  const canonicalName =
    fexerjId != null && lookups.fexerjNames.has(fexerjId)
      ? lookups.fexerjNames.get(fexerjId)
      : player.name
  return { ...player, fexerjId, name: canonicalName ?? player.name }
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

/** Parse FEXERJ/CBX id cells; tolerates NBSP/garbage prefixes from Excel cp1252 exports. */
function parseIdCell(raw) {
  if (raw === undefined || raw === null || raw === '') return null
  const digits = String(raw).replace(/\D/g, '')
  if (!digits) return null
  const n = Number.parseInt(digits, 10)
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
  const rawLines = stripUtf8Bom(auditCsvText)
    .split(/\r?\n/)
    .map(l => l.trimEnd())
    .filter(line => line.length > 0)

  const actual = rawLines[0] ?? ''
  if (actual !== AUDIT_PREAMBLE) {
    const shown = actual.length > 80 ? `${actual.slice(0, 80)}…` : actual
    throw new Error(
      `Versão do arquivo de auditoria não reconhecida. Esperado "${AUDIT_PREAMBLE}"; encontrado "${shown}".\n` +
        'O ZIP pode ser baixado normalmente; o resumo na tela não está disponível.',
    )
  }

  // Parse the semicolon CSV starting at the header line (line 1), so `parseSemicolonCsv` stays unchanged.
  const { headers, rows } = parseSemicolonCsv(rawLines.slice(1).join('\n'))
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

/**
 * Split "preamble line + CSV" the way `parseAuditCsv` does, but for the
 * per-game model's files, whose version marker is their own preamble.
 * @param {string} text
 * @param {string} expectedPreamble
 */
function splitPreambleAndBody(text, expectedPreamble) {
  const lines = stripUtf8Bom(text)
    .split(/\r?\n/)
    .map(l => l.trimEnd())
    .filter(line => line.length > 0)
  const actual = lines[0] ?? ''
  if (actual !== expectedPreamble) {
    const shown = actual.length > 80 ? `${actual.slice(0, 80)}…` : actual
    throw new Error(
      `Versão de arquivo não reconhecida. Esperado "${expectedPreamble}"; encontrado "${shown}".\n` +
        'O ZIP pode ser baixado normalmente; o resumo na tela não está disponível.',
    )
  }
  return parseSemicolonCsv(lines.slice(1).join('\n'))
}

/**
 * Cells by header name, so a column added to the audit shifts nothing here.
 * @param {string[]} headers
 * @param {string[]} row
 */
function cellsByHeader(headers, row) {
  /** @type {Record<string, string>} */
  const out = {}
  headers.forEach((h, i) => {
    out[h.trim()] = row[i]
  })
  return out
}

function isBlankRow(row) {
  return row.every(c => c === '' || c === undefined)
}

/**
 * @param {string} text Audit_Period.csv contents
 */
export function parseFidePeriodAudit(text) {
  const { headers, rows } = splitPreambleAndBody(text, FIDE_PERIOD_PREAMBLE)
  return rows
    .filter(row => !isBlankRow(row))
    .map(row => {
      const c = cellsByHeader(headers, row)
      const initialRating = parseNumericCell(c.InitialRating)
      const finalRating = parseNumericCell(c.FinalRating)
      return {
        tournaments: (c.Tournaments ?? '').trim(),
        fexerjId: parseIntCell(c.PlayerId),
        name: c.PlayerName ?? '',
        modality: (c.TimeControl ?? '').trim(),
        initialRating,
        games: parseIntCell(c.Games),
        sumDelta: parseNumericCell(c.SumDeltaR),
        variation: parseNumericCell(c.Variation),
        roundedVariation: parseIntCell(c.RoundedVariation),
        finalRating,
        // Null on the unrated paths: a player without a rating on either side
        // of the period has no variation to report, and counting them as zero
        // would pad the "unchanged" bucket with people who never moved.
        delta:
          initialRating !== null && finalRating !== null ? finalRating - initialRating : null,
        path: (c.Path ?? '').trim(),
      }
    })
}

/**
 * @param {string} text Comparison.csv contents
 */
export function parseComparisonCsv(text) {
  const { headers, rows } = splitPreambleAndBody(text, COMPARISON_PREAMBLE)
  return rows
    .filter(row => !isBlankRow(row))
    .map(row => {
      const c = cellsByHeader(headers, row)
      return {
        fexerjId: parseIntCell(c.PlayerId),
        name: c.PlayerName ?? '',
        ratingCurrent: parseNumericCell(c.RatingCurrent),
        ratingFide: parseNumericCell(c.RatingFide),
        difference: parseNumericCell(c.Difference) ?? 0,
      }
    })
}

/**
 * Variation statistics for the on-screen summary.
 * @param {Array<number|null|undefined>} deltas
 */
export function summarizeDeltas(deltas) {
  const values = deltas.filter(d => d !== null && d !== undefined && !Number.isNaN(d))
  if (values.length === 0) {
    return { total: 0, up: 0, down: 0, unchanged: 0, maxUp: null, maxDown: null, medianAbs: null }
  }
  const sortedAbs = values.map(Math.abs).sort((a, b) => a - b)
  const mid = Math.floor(sortedAbs.length / 2)
  const medianAbs =
    sortedAbs.length % 2 === 1 ? sortedAbs[mid] : (sortedAbs[mid - 1] + sortedAbs[mid]) / 2
  return {
    total: values.length,
    up: values.filter(d => d > 0).length,
    down: values.filter(d => d < 0).length,
    unchanged: values.filter(d => d === 0).length,
    maxUp: Math.max(...values),
    maxDown: Math.min(...values),
    medianAbs,
  }
}

/** @param {ReturnType<typeof parseFidePeriodAudit>} periodRows */
function groupByModality(periodRows) {
  /** @type {Map<string, object[]>} */
  const byModality = new Map()
  for (const row of periodRows) {
    if (!byModality.has(row.modality)) byModality.set(row.modality, [])
    byModality.get(row.modality).push(row)
  }
  return [...byModality.entries()].map(([modality, players]) => ({
    modality,
    players,
    summary: summarizeDeltas(players.map(p => p.delta)),
  }))
}

const TYPE_LABEL_PT = {
  SS: 'Suíço individual',
  RR: 'Round-robin',
  ST: 'Suíço por equipes',
}

/**
 * @param {Blob} zipBlob
 * @param {string} tournamentsCsvText
 * @param {string} [playersCsvText]
 */
export async function parseRunResult(zipBlob, tournamentsCsvText, playersCsvText = '') {
  const zip = await JSZip.loadAsync(zipBlob)
  const names = new Set(
    Object.entries(zip.files)
      .filter(([, entry]) => !entry.dir)
      .map(([path]) => (path.includes('/') ? path.slice(path.lastIndexOf('/') + 1) : path)),
  )

  // Dispatch on the shape of the output, not on the mode the operator picked:
  // the zip is what actually came back.
  if (names.has('Comparison.csv')) return parseComparisonResult(zip, zipBlob)
  if (names.has('Audit_Period.csv')) return parseFideResult(zip, zipBlob)
  return parseLegacyResult(zip, zipBlob, tournamentsCsvText, playersCsvText)
}

async function parseFideResult(zip, zipBlob) {
  const periodRows = parseFidePeriodAudit(await zip.file('Audit_Period.csv').async('string'))
  return {
    kind: 'fide',
    zipBlob,
    zipFilename: ZIP_NAME_BY_KIND.fide,
    modalities: groupByModality(periodRows),
    tournaments: [],
  }
}

async function parseComparisonResult(zip, zipBlob) {
  const comparisonRows = parseComparisonCsv(await zip.file('Comparison.csv').async('string'))
  const periodEntry = zip.file('Audit_Period.csv')
  const periodRows = periodEntry ? parseFidePeriodAudit(await periodEntry.async('string')) : []
  return {
    kind: 'compare',
    zipBlob,
    zipFilename: ZIP_NAME_BY_KIND.compare,
    comparison: {
      players: comparisonRows,
      summary: summarizeDeltas(comparisonRows.map(r => r.difference)),
    },
    modalities: groupByModality(periodRows),
    tournaments: [],
  }
}

async function parseLegacyResult(zip, zipBlob, tournamentsCsvText, playersCsvText) {
  const tournamentMap = parseTournamentsCsv(tournamentsCsvText)
  const playerLookups = parsePlayersCsv(playersCsvText)

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
    let players
    try {
      players = parseAuditCsv(csvText)
    } catch (e) {
      throw new Error(
        `Erro ao ler Audit_of_Tournament_${ord}.csv: ${e instanceof Error ? e.message : String(e)}`,
        { cause: e },
      )
    }

    const typeCode = meta?.type ?? ''
    const isIrt = meta?.isIrt ?? false
    const enrichedPlayers = players.map(p =>
      enrichPlayerFromPlayersCsv(p, { isIrt }, playerLookups),
    )
    tournaments.push({
      ord,
      crId: meta?.crId ?? null,
      name: meta?.name ?? `Torneio ${ord}`,
      type: typeCode,
      typeLabelPt: TYPE_LABEL_PT[typeCode] ?? typeCode,
      endDate: meta?.endDate ?? '',
      isFexerj: meta?.isFexerj ?? false,
      isIrt,
      players: enrichedPlayers,
    })
  }

  return {
    kind: 'legacy',
    zipBlob,
    zipFilename: ZIP_NAME_BY_KIND.legacy,
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
    const ida = a.fexerjId
    const idb = b.fexerjId
    if (ida != null && idb != null) return ida - idb
    if (ida != null) return -1
    if (idb != null) return 1
    const cmp = (a.name || '').localeCompare(b.name || '', 'pt-BR', { sensitivity: 'base' })
    if (cmp !== 0) return cmp
    return a.groupKey.localeCompare(b.groupKey)
  })

  return out
}
