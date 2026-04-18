import { useCallback, useEffect, useState } from 'react'
import PropTypes from 'prop-types'

import { BUILD_COMMIT, BUILD_TIME } from './buildMeta'
import { formatBuildStampClipboard } from './buildStampClipboard'
import { fetchServerDate } from './buildStampServerTime'
import { formatBuildDisplayTimeEastern, formatInstantEastern } from './buildStampTime'

function CopyIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

/** Visible build id so operators can confirm the deployed bundle without DevTools. */
export default function BuildStamp({ className = '' }) {
  const buildWhen = formatBuildDisplayTimeEastern(BUILD_TIME)
  const [serverInstant, setServerInstant] = useState(null)
  const [copyFeedback, setCopyFeedback] = useState(false)

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
    const text = formatBuildStampClipboard(BUILD_COMMIT, buildWhen, serverWhen)

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
  }, [buildWhen, serverWhen])

  return (
    <footer
      className={`build-stamp ${className}`.trim()}
      title="Commit e horários: build do bundle (ET) e relógio do servidor via cabeçalho HTTP (ET, EDT/EST)."
    >
      <div className="build-stamp-left">
        <span className="build-stamp-label">Frontend</span>{' '}
        <span className="build-stamp-mono">{BUILD_COMMIT}</span>
        <button
          type="button"
          className="build-stamp-copy-btn"
          onClick={handleCopy}
          aria-label="Copiar commit do frontend e horários (build e servidor) em ET"
        >
          <CopyIcon />
        </button>
        <span className="build-stamp-sep" aria-hidden>
          ·
        </span>
        <span className="tabular-nums">{buildWhen}</span>
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
