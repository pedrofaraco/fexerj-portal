import PropTypes from 'prop-types'

import { BUILD_COMMIT, BUILD_TIME } from './buildMeta'
import { formatBuildDisplayTimeEastern } from './buildStampTime'

/** Visible build id so operators can confirm the deployed bundle without DevTools. */
export default function BuildStamp({ className = '' }) {
  const when = formatBuildDisplayTimeEastern(BUILD_TIME)

  return (
    <footer
      className={`border-t border-gray-200 bg-gray-50 px-4 py-2 text-center text-[11px] text-gray-400 tabular-nums select-all ${className}`.trim()}
      title="Commit e horário do build do frontend em horário do leste dos EUA (ET, EDT/EST). Compare com git no servidor."
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
