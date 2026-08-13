import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import OperatorChecks from './OperatorChecks'

const K10 = {
  playerId: '3741',
  playerName: 'Jogador Um',
  timeControl: 'STD',
  check: 'K10_BELOW_2200',
  detail: '1500',
}
const DECEASED = {
  playerId: '643',
  playerName: 'Jogador Dois',
  timeControl: 'RPD',
  check: 'CALCULATED_WHILE_DECEASED',
  detail: '5',
}

describe('OperatorChecks', () => {
  it('renders nothing when the cycle raised nothing', () => {
    const { container } = render(<OperatorChecks checks={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when the result predates the checks file', () => {
    const { container } = render(<OperatorChecks checks={undefined} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('counts the cases in the singular and the plural', () => {
    const { rerender } = render(<OperatorChecks checks={[K10]} />)
    expect(screen.getByText('1 caso para conferência')).toBeInTheDocument()
    rerender(<OperatorChecks checks={[K10, DECEASED]} />)
    expect(screen.getByText('2 casos para conferência')).toBeInTheDocument()
  })

  it('says these are not errors', () => {
    render(<OperatorChecks checks={[K10]} />)
    expect(screen.getByText(/não são erros/)).toBeInTheDocument()
  })

  it('names the player, the modality and the detail', () => {
    render(<OperatorChecks checks={[K10]} />)
    expect(screen.getByText(/Jogador Um \(3741\)/)).toBeInTheDocument()
    expect(screen.getByText(/Clássico/)).toBeInTheDocument()
    expect(screen.getByText(/Rating: 1500/)).toBeInTheDocument()
  })

  it('groups by check, explaining each once', () => {
    render(<OperatorChecks checks={[K10, { ...K10, playerId: '9', playerName: 'Jogador Três' }]} />)
    expect(screen.getAllByText(/Fator K de 10 em jogador abaixo de 2\.200/)).toHaveLength(1)
    expect(screen.getByText(/Jogador Três \(9\)/)).toBeInTheDocument()
  })

  it('shows a code it does not know rather than hiding the row', () => {
    render(<OperatorChecks checks={[{ ...K10, check: 'ALGO_NOVO', detail: '' }]} />)
    expect(screen.getByText('ALGO_NOVO')).toBeInTheDocument()
    expect(screen.getByText(/Jogador Um \(3741\)/)).toBeInTheDocument()
  })

  it('omits the detail when there is none', () => {
    render(<OperatorChecks checks={[{ ...K10, detail: '' }]} />)
    expect(screen.queryByText(/Rating:/)).not.toBeInTheDocument()
  })
})
