/**
 * Fetch current server clock from the HTTP `Date` header (GET /health).
 * Same-origin; no auth required.
 *
 * Design: intended for a **single** UI consumer (e.g. one BuildStamp per page). Multiple
 * simultaneous pollers duplicate traffic — callers should not mount several stamps at once.
 *
 * @returns {Promise<Date | null>}
 */
export async function fetchServerDate() {
  try {
    const res = await fetch('/health', { method: 'GET', cache: 'no-store' })
    if (!res.ok) return null
    const raw = res.headers.get('Date')
    if (!raw) return null
    const d = new Date(raw)
    return Number.isNaN(d.getTime()) ? null : d
  } catch {
    return null
  }
}
