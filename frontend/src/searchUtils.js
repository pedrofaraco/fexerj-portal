/** Unicode combining marks removed after NFD (accent folding). */
const COMBINING_MARK_RE = /\p{M}/gu

/**
 * Lowercase, accent-insensitive folding for substring search.
 * @param {string | null | undefined} s
 */
export function normalizeForSearch(s) {
  return String(s ?? '')
    .normalize('NFD')
    .replace(COMBINING_MARK_RE, '')
    .toLowerCase()
}

function trimmedQuery(raw) {
  return raw == null ? '' : String(raw).trim()
}

function digitPart(trimmed) {
  return trimmed.replace(/\D/g, '')
}

/**
 * @param {{ ord: number, name?: string|null, crId?: number|null }} t
 * @param {string} trimmed
 */
function tournamentMatches(t, trimmed) {
  const nameOk = normalizeForSearch(t.name).includes(normalizeForSearch(trimmed))
  const digits = digitPart(trimmed)
  if (!digits) return nameOk

  let idOk = String(t.ord).includes(digits)
  const cr = t.crId
  if (cr != null && cr !== 0) idOk = idOk || String(cr).includes(digits)

  return nameOk || idOk
}

/**
 * @param {{ fexerjId?: number|null, name?: string|null }} p
 * @param {string} trimmed
 */
function playerRowMatches(p, trimmed) {
  const nameOk = normalizeForSearch(p.name).includes(normalizeForSearch(trimmed))
  const digits = digitPart(trimmed)
  if (!digits) return nameOk

  const id = p.fexerjId
  const idOk = id != null && String(id).includes(digits)
  return nameOk || idOk
}

/**
 * @param {Array<{ ord: number, name?: string|null, crId?: number|null }>} tournaments
 * @param {string} rawQuery
 */
export function filterTournamentsForSearch(tournaments, rawQuery) {
  const q = trimmedQuery(rawQuery)
  const list = tournaments ?? []
  if (q === '') return list
  return list.filter(t => tournamentMatches(t, q))
}

/**
 * @param {Array<{ fexerjId?: number|null, name?: string|null }>} players buildPlayerIndex rows
 * @param {string} rawQuery
 */
export function filterPlayersForSearch(players, rawQuery) {
  const q = trimmedQuery(rawQuery)
  const list = players ?? []
  if (q === '') return list
  return list.filter(p => playerRowMatches(p, q))
}
