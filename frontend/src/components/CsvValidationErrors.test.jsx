import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import CsvValidationErrors from './CsvValidationErrors'

describe('CsvValidationErrors', () => {
  it('renders nothing when there are no errors', () => {
    const { container } = render(<CsvValidationErrors errors={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows checking message while validating', () => {
    render(<CsvValidationErrors errors={[]} checking />)
    expect(screen.getByText(/verificando formato do arquivo/i)).toBeInTheDocument()
  })

  it('lists validation messages without a line for file-level errors', () => {
    render(<CsvValidationErrors errors={[{ message: 'players.csv: arquivo vazio' }]} />)
    expect(screen.getByText('players.csv: arquivo vazio')).toBeInTheDocument()
    expect(screen.queryByRole('code')).not.toBeInTheDocument()
  })

  it('shows the offending CSV line and highlights the bad cell', () => {
    render(
      <CsvValidationErrors
        errors={[
          {
            message: 'players.csv linha 2: Id_CBX contém NBSP',
            rawLine: '5304;\u00a095178;;CALEB;1446',
            highlightColumn: 1,
          },
        ]}
      />,
    )
    expect(screen.getByText('players.csv linha 2: Id_CBX contém NBSP')).toBeInTheDocument()
    const badCell = screen.getByRole('code').querySelector('.csv-error-cell-bad')
    expect(badCell).not.toBeNull()
    expect(badCell?.textContent).toContain('95178')
  })

  it('shows both duplicate rows', () => {
    render(
      <CsvValidationErrors
        errors={[
          {
            message: 'players.csv: Id_CBX duplicado',
            rawLines: ['3741;90107;;A', '3742;90107;;B'],
            highlightColumn: 1,
          },
        ]}
      />,
    )
    expect(screen.getAllByRole('code')).toHaveLength(2)
  })
})
