import PropTypes from 'prop-types'

/**
 * @param {{ rawLine: string, highlightColumn?: number }} props
 */
function CsvErrorLine({ rawLine, highlightColumn }) {
  const cells = rawLine.split(';')
  return (
    <code className="csv-error-line">
      {cells.map((cell, index) => (
        <span key={index}>
          {index > 0 ? ';' : null}
          <span className={index === highlightColumn ? 'csv-error-cell-bad' : undefined}>
            {cell}
          </span>
        </span>
      ))}
    </code>
  )
}

CsvErrorLine.propTypes = {
  rawLine: PropTypes.string.isRequired,
  highlightColumn: PropTypes.number,
}

/**
 * @param {{ message: string, rawLine?: string, rawLines?: string[], highlightColumn?: number }} error
 */
function CsvValidationErrorItem({ error }) {
  const lines = error.rawLines ?? (error.rawLine ? [error.rawLine] : [])
  return (
    <li className="csv-validation-error-item">
      <span>{error.message}</span>
      {lines.map((rawLine, index) => (
        <CsvErrorLine
          key={index}
          rawLine={rawLine}
          highlightColumn={error.highlightColumn}
        />
      ))}
    </li>
  )
}

CsvValidationErrorItem.propTypes = {
  error: PropTypes.shape({
    message: PropTypes.string.isRequired,
    rawLine: PropTypes.string,
    rawLines: PropTypes.arrayOf(PropTypes.string),
    highlightColumn: PropTypes.number,
  }).isRequired,
}

export default function CsvValidationErrors({ errors, checking = false }) {
  if (checking) {
    return <p className="status-muted m-0 mt-2">Verificando formato do arquivo…</p>
  }
  if (!errors?.length) return null
  return (
    <div className="alert-error mt-2" role="alert">
      <ul className="csv-validation-error-list m-0 pl-0">
        {errors.map((err, i) => (
          <CsvValidationErrorItem key={i} error={typeof err === 'string' ? { message: err } : err} />
        ))}
      </ul>
    </div>
  )
}

CsvValidationErrors.propTypes = {
  errors: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        message: PropTypes.string.isRequired,
        rawLine: PropTypes.string,
        rawLines: PropTypes.arrayOf(PropTypes.string),
        highlightColumn: PropTypes.number,
      }),
    ]),
  ).isRequired,
  checking: PropTypes.bool,
}
