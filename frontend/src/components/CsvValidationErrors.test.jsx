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

  it('lists validation errors', () => {
    render(<CsvValidationErrors errors={['players.csv: arquivo vazio']} />)
    expect(screen.getByText('players.csv: arquivo vazio')).toBeInTheDocument()
  })
})
