import { useEffect, useState } from 'react'

import { buildCycleFormData, postMultipart } from '../portalApi'

export default function useCycleValidation(form, credentials, { onAuthError, debounceMs = 300 } = {}) {
  const [validationErrors, setValidationErrors] = useState([])
  const [validationRequestError, setValidationRequestError] = useState('')
  const [validationRequestId, setValidationRequestId] = useState(null)
  const [validationStatus, setValidationStatus] = useState('idle') // idle | checking | done | failed

  useEffect(() => {
    if (!credentials || !form.playersCsv || !form.tournamentsCsv || form.binaryFiles.length === 0) {
      let resetCancelled = false
      queueMicrotask(() => {
        if (resetCancelled) return
        setValidationErrors([])
        setValidationRequestError('')
        setValidationRequestId(null)
        setValidationStatus('idle')
      })
      return () => { resetCancelled = true }
    }

    let cancelled = false
    queueMicrotask(() => {
      if (cancelled) return
      setValidationStatus('checking')
      setValidationErrors([])
      setValidationRequestError('')
      setValidationRequestId(null)
    })

    const body = buildCycleFormData(form)
    const ac = new AbortController()
    const timer = setTimeout(() => {
      ;(async () => {
        try {
          const res = await postMultipart('/validate', body, credentials, { signal: ac.signal })
          if (cancelled || ac.signal.aborted) return
          const reqId = res.headers?.get?.('x-request-id') ?? null
          if (res.status === 401) {
            setValidationRequestId(null)
            onAuthError?.()
            return
          }
          if (!res.ok) {
            setValidationErrors([])
            setValidationRequestError(
              `Não foi possível validar os arquivos (resposta HTTP ${res.status}). Tente novamente.`,
            )
            setValidationRequestId(reqId)
            setValidationStatus('failed')
            return
          }
          let data
          try {
            data = await res.json()
          } catch {
            if (cancelled || ac.signal.aborted) return
            setValidationErrors([])
            setValidationRequestError('Resposta inválida do servidor ao validar. Tente novamente.')
            setValidationRequestId(reqId)
            setValidationStatus('failed')
            return
          }
          if (cancelled || ac.signal.aborted) return
          setValidationErrors(data.errors ?? [])
          setValidationRequestId(null)
          setValidationStatus('done')
        } catch (e) {
          if (cancelled || ac.signal.aborted || e?.name === 'AbortError') return
          setValidationErrors([])
          setValidationRequestError(
            'Não foi possível conectar ao servidor para validar. Verifique sua conexão e tente novamente.',
          )
          setValidationRequestId(null)
          setValidationStatus('failed')
        }
      })()
    }, debounceMs)

    return () => {
      cancelled = true
      clearTimeout(timer)
      ac.abort()
    }
  }, [form, credentials, onAuthError, debounceMs])

  return { validationErrors, validationRequestError, validationRequestId, validationStatus }
}
