import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import SelectedFilesLine from './SelectedFilesLine'

describe('SelectedFilesLine', () => {
  it('renders nothing when no files are selected', () => {
    const { container } = render(<SelectedFilesLine files={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows a single selected filename', () => {
    render(<SelectedFilesLine files={{ name: 'players.csv' }} />)
    expect(screen.getByText('Arquivo selecionado: players.csv')).toBeInTheDocument()
  })

  it('shows multiple selected filenames', () => {
    render(
      <SelectedFilesLine
        files={[{ name: '1-1.TUNX' }, { name: '2-2.TURX' }]}
      />,
    )
    expect(screen.getByText('Arquivos selecionados: 1-1.TUNX, 2-2.TURX')).toBeInTheDocument()
  })
})
