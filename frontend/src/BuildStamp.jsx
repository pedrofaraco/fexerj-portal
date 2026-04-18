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
      className={`border-t border-gray-200 bg-gray-50 px-4 py-2 text-center text-[11px] text-gray-400 tabular-nums select-all ${className}`.trim()}
      title="Commit e horário do build do frontend (compare com git no servidor)."
    >
      Frontend <span className="font-mono text-gray-600">{BUILD_COMMIT}</span>
      <span className="mx-1.5 text-gray-300">·</span>
      <span>{when}</span>
    </footer>
  )
}

BuildStamp.propTypes = {
  className: PropTypes.string,
}
