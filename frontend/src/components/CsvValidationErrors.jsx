import PropTypes from 'prop-types'

export default function CsvValidationErrors({ errors, checking = false }) {
  if (checking) {
    return <p className="status-muted m-0 mt-2">Verificando formato do arquivo…</p>
  }
  if (!errors?.length) return null
  return (
    <div className="alert-error mt-2" role="alert">
      <ul className="list-disc list-inside space-y-0.5 m-0 pl-0">
        {errors.map((err, i) => (
          <li key={i}>{err}</li>
        ))}
      </ul>
    </div>
  )
}

CsvValidationErrors.propTypes = {
  errors: PropTypes.arrayOf(PropTypes.string).isRequired,
  checking: PropTypes.bool,
}
