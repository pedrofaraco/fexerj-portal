import PropTypes from 'prop-types'

import { BUILD_COMMIT, BUILD_TIME } from './buildMeta'

/** Visible build id so operators can confirm the deployed bundle without DevTools. */
export default function BuildStamp({ className = '' }) {
  const date = new Date(BUILD_TIME)
  const when = Number.isNaN(date.getTime())
    ? BUILD_TIME
    : date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

  return (
    <footer
      className={`build-stamp ${className}`.trim()}
      title="Commit e horário do build do frontend (compare com git no servidor)."
    >
      Frontend <span className="build-stamp-mono">{BUILD_COMMIT}</span>
      <span className="build-stamp-sep">·</span>
      <span>{when}</span>
    </footer>
  )
}

BuildStamp.propTypes = {
  className: PropTypes.string,
}
