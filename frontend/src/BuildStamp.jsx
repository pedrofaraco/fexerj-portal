import { useCallback, useEffect, useState } from 'react'
import PropTypes from 'prop-types'

import CopyIcon from './components/CopyIcon'
import { BUILD_COMMIT } from './buildMeta'
import { formatBuildStampClipboard } from './buildStampClipboard'
import { fetchServerDate } from './buildStampServerTime'
import { formatInstantEastern } from './buildStampTime'

/** Visible build id so operators can confirm the deployed bundle without DevTools. */
export default function BuildStamp({ className = '' }) {
  const [serverInstant, setServerInstant] = useState(null)
  const [copyFeedback, setCopyFeedback] = useState(false)

  // One BuildStamp per page: each mount starts a 60s /health polling loop (server clock).
  useEffect(() => {
    let cancelled = false

    async function refresh() {
      const d = await fetchServerDate()
      if (!cancelled && d) setServerInstant(d)
    }

    refresh()
    const id = window.setInterval(refresh, 60_000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  const serverWhen = serverInstant ? formatInstantEastern(serverInstant) : '—'

  const handleCopy = useCallback(async () => {
    const text = formatBuildStampClipboard(BUILD_COMMIT)

    try {
      await navigator.clipboard.writeText(text)
    } catch {
      try {
        const ta = document.createElement('textarea')
        ta.value = text
        ta.setAttribute('readonly', '')
        ta.style.position = 'fixed'
        ta.style.left = '-9999px'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      } catch {
        return
      }
    }
    setCopyFeedback(true)
    window.setTimeout(() => setCopyFeedback(false), 2000)
  }, [])

  return (
    <footer
      className={`build-stamp ${className}`.trim()}
      title="Identificador do código do frontend (commit Git curto). O mesmo valor em UAT e prod indica o mesmo bundle. Server Time = cabeçalho HTTP Date (ET)."
    >
      <div className="build-stamp-left">
        <span className="build-stamp-label">Frontend</span>{' '}
        <span className="build-stamp-mono">{BUILD_COMMIT}</span>
        <button
          type="button"
          className="build-stamp-copy-btn"
          onClick={handleCopy}
          aria-label="Copiar identificador do frontend (hash do commit)"
        >
          <CopyIcon />
        </button>
        {copyFeedback && (
          <span className="build-stamp-copied" role="status">
            Copiado
          </span>
        )}
      </div>
      <div className="build-stamp-right tabular-nums">
        Server Time {serverWhen}
      </div>
    </footer>
  )
}

BuildStamp.propTypes = {
  className: PropTypes.string,
}
