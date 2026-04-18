import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchServerDate } from './buildStampServerTime'

describe('fetchServerDate', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: {
            get: name => (name.toLowerCase() === 'date' ? 'Sat, 18 Apr 2026 19:12:00 GMT' : null),
          },
        }),
      ),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns Date from HTTP Date header when /health succeeds', async () => {
    const d = await fetchServerDate()
    expect(d).toBeInstanceOf(Date)
    expect(d?.getUTCFullYear()).toBe(2026)
    expect(fetch).toHaveBeenCalledWith('/health', { method: 'GET', cache: 'no-store' })
  })

  it('returns null when Date header missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => null },
        }),
      ),
    )
    await expect(fetchServerDate()).resolves.toBeNull()
  })

  it('returns null when response is not ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 503,
          headers: {
            get: name => (name.toLowerCase() === 'date' ? 'Sat, 18 Apr 2026 19:12:00 GMT' : null),
          },
        }),
      ),
    )
    await expect(fetchServerDate()).resolves.toBeNull()
  })

  it('returns null when fetch throws', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network'))))
    await expect(fetchServerDate()).resolves.toBeNull()
  })
})
