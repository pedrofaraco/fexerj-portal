import PropTypes from 'prop-types'

export default function Field({ label, hint, className = '', children }) {
  return (
    <label className={`flex flex-col gap-1.5 ${className}`}>
      <span className="field-label">{label}</span>
      {hint && <span className="field-hint">{hint}</span>}
      {children}
    </label>
  )
}

Field.propTypes = {
  label: PropTypes.string.isRequired,
  hint: PropTypes.string,
  className: PropTypes.string,
  children: PropTypes.node.isRequired,
}
