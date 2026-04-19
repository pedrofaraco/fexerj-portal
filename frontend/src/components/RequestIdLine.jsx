import { useCallback, useState } from 'react'
import PropTypes from 'prop-types'

import CopyIcon from './CopyIcon'

export default function RequestIdLine({ requestId }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(requestId)
    } catch {
      try {
        const ta = document.createElement('textarea')
        ta.value = requestId
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
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }, [requestId])

  return (
    <p className="field-hint mt-1">
      ID da requisição:{' '}
      <span className="build-stamp-mono">{requestId}</span>
      <button
        type="button"
        className="build-stamp-copy-btn"
        onClick={handleCopy}
        aria-label="Copiar ID da requisição"
      >
        <CopyIcon />
      </button>
      {copied && <span className="build-stamp-copied" role="status">Copiado</span>}
    </p>
  )
}

RequestIdLine.propTypes = {
  requestId: PropTypes.string.isRequired,
}
