import { useRef, useState } from 'react'

import { buildCycleFormData, postMultipart } from '../portalApi'
import { parseRunResult } from '../resultParser'

export default function useRunCycle(form, credentials, { onAuthError } = {}) {
  const [status, setStatus] = useState('idle') // idle | loading | error
  const [runErrors, setRunErrors] = useState([])
  const [runRequestId, setRunRequestId] = useState(null)
  const [runResult, setRunResult] = useState(null)

  const runFetchAbortRef = useRef(null)

  function abort() {
    runFetchAbortRef.current?.abort()
    runFetchAbortRef.current = null
    setRunRequestId(null)
  }

  async function handleRun(e) {
    e.preventDefault()
    abort()

    const ac = new AbortController()
    runFetchAbortRef.current = ac

    setStatus('loading')
    setRunErrors([])
    setRunRequestId(null)

    const body = buildCycleFormData(form)
    const tournamentsCsvText = form.tournamentsCsv ? await form.tournamentsCsv.text() : ''

    try {
      const response = await postMultipart('/run', body, credentials, { signal: ac.signal })

      if (ac.signal.aborted) return

      const reqId = response.headers?.get?.('x-request-id') ?? null

      if (response.status === 401) {
        setRunRequestId(null)
        onAuthError?.()
        setStatus('idle')
        return
      }

      if (!response.ok) {
        const json = await response.json().catch(() => ({}))
        const detail = json.detail
        let messages
        if (typeof detail === 'string' && detail.trim()) {
          messages = [detail]
        } else if (Array.isArray(detail) && detail.length > 0) {
          if (detail.every(x => typeof x === 'string')) {
            messages = detail
          } else if (detail.every(x => x && typeof x === 'object' && typeof x.msg === 'string')) {
            messages = detail.map(x => x.msg)
          } else {
            messages = detail.map(x => (typeof x === 'string' ? x : JSON.stringify(x)))
          }
        } else {
          messages = [`Erro inesperado (HTTP ${response.status})`]
        }
        setRunErrors(messages)
        setRunRequestId(reqId)
        setStatus('error')
        return
      }

      if (ac.signal.aborted) return

      const blob = await response.blob()
      if (ac.signal.aborted) return

      try {
        const parsed = await parseRunResult(blob, tournamentsCsvText)
        setRunResult({
          zipBlob: parsed.zipBlob,
          zipFilename: parsed.zipFilename,
          tournaments: parsed.tournaments,
          parseError: null,
          requestId: reqId ?? undefined,
        })
      } catch (parseErr) {
        const msg = parseErr instanceof Error ? parseErr.message : String(parseErr)
        setRunResult({
          zipBlob: blob,
          zipFilename: 'rating_cycle_output.zip',
          tournaments: [],
          parseError: msg,
          requestId: reqId ?? undefined,
        })
      }
      setRunRequestId(null)
      setStatus('idle')
    } catch (e) {
      if (e?.name === 'AbortError') return
      setRunErrors(['Não foi possível conectar ao servidor. Verifique sua conexão.'])
      setRunRequestId(null)
      setStatus('error')
    } finally {
      if (runFetchAbortRef.current === ac) runFetchAbortRef.current = null
    }
  }

  function clearRunResult() {
    setRunResult(null)
    setRunRequestId(null)
  }

  return { handleRun, status, runErrors, runRequestId, runResult, clearRunResult, abort }
}
