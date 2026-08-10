import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ComparisonSummary from './ComparisonSummary'

const COMPARISON = {
  players: [
    { fexerjId: 3741, name: 'Carlos Mendes', ratingCurrent: 1810, ratingFide: 1807, difference: -3 },
    { fexerjId: 643, name: 'Roberto Faria', ratingCurrent: 1893, ratingFide: 1896, difference: 3 },
    { fexerjId: 1979, name: 'Andre Nunes', ratingCurrent: 1700, ratingFide: 1700, difference: 0 },
  ],
  summary: { total: 3, up: 1, down: 1, unchanged: 1, maxUp: 3, maxDown: -3, medianAbs: 3 },
}

describe('ComparisonSummary', () => {
  it('shows both ratings side by side', () => {
    render(<ComparisonSummary comparison={COMPARISON} />)
    expect(screen.getByText('1810')).toBeInTheDocument()
    expect(screen.getByText('1807')).toBeInTheDocument()
  })

  it('summarizes the difference between the models', () => {
    render(<ComparisonSummary comparison={COMPARISON} />)
    expect(screen.getByText(/3 jogadores/i)).toBeInTheDocument()
    expect(screen.getByText(/mediana/i)).toBeInTheDocument()
  })

  it('says the difference is the point, not a defect', () => {
    render(<ComparisonSummary comparison={COMPARISON} />)
    expect(screen.getByText(/ratings diferentes.*histórico idêntico/i)).toBeInTheDocument()
  })
})
