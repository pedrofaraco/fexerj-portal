import PropTypes from 'prop-types'

function fileNames(files) {
  if (Array.isArray(files)) {
    return files.map(f => f?.name).filter(Boolean)
  }
  return files?.name ? [files.name] : []
}

export default function SelectedFilesLine({ files }) {
  const names = fileNames(files)
  if (names.length === 0) return null

  const label = names.length === 1 ? 'Arquivo selecionado' : 'Arquivos selecionados'

  return (
    <p className="file-selection">
      {label}: {names.join(', ')}
    </p>
  )
}

SelectedFilesLine.propTypes = {
  files: PropTypes.oneOfType([
    PropTypes.shape({ name: PropTypes.string }),
    PropTypes.arrayOf(PropTypes.shape({ name: PropTypes.string })),
  ]),
}
