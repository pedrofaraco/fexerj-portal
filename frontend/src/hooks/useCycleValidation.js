import { useEffect, useRef, useState } from 'react'

import { buildCycleFormData, postMultipart } from '../portalApi'

export default function useCycleValidation(form, credentials, { onAuthError, debounceMs = 300 } = {}) {
  const [validationErrors, setValidationErrors] = useState([])
  const [validationRequestError, setValidationRequestError] = useState('')
  const [validationStatus, setValidationStatus] = useState('idle') // idle | checking | done | failed

  const debounceTimerRef = useRef(null)

  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
  })

  useEffect(() => {
    if (!credentials || !form.playersCsv || !form.tournamentsCsv || form.binaryFiles.length === 0) {
      let resetCancelled = false
      queueMicrotask(() => {
        if (resetCancelled) return
        setValidationErrors([])
        setValidationRequestError('')
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
    })

    const body = buildCycleFormData(form)
    const ac = new AbortController()

    debounceTimerRef.current = setTimeout(() => {
      ;(async () => {
        try {
          const res = await postMultipart('/validate', body, credentials, { signal: ac.signal })
          if (cancelled || ac.signal.aborted) return
          if (res.status === 401) {
            onAuthError?.()
            return
          }
          if (!res.ok) {
            setValidationErrors([])
            setValidationRequestError(
              `Não foi possível validar os arquivos (resposta HTTP ${res.status}). Tente novamente.`,
            )
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
            setValidationStatus('failed')
            return
          }
          if (cancelled || ac.signal.aborted) return
          setValidationErrors(data.errors ?? [])
          setValidationStatus('done')
        } catch (e) {
          if (cancelled || ac.signal.aborted || e?.name === 'AbortError') return
          setValidationErrors([])
          setValidationRequestError(
            'Não foi possível conectar ao servidor para validar. Verifique sua conexão e tente novamente.',
          )
          setValidationStatus('failed')
        }
      })()
    }, debounceMs)

    return () => {
      cancelled = true
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
        debounceTimerRef.current = null
      }
      ac.abort()
    }
  }, [form, credentials, onAuthError, debounceMs])

  return { validationErrors, validationRequestError, validationStatus }
}

