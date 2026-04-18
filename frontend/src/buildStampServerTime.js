/**
 * Fetch current server clock from the HTTP `Date` header (GET /health).
 * Same-origin; no auth required.
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
