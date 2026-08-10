import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import PeriodSummary from './PeriodSummary'

const MODALITIES = [
  {
    modality: 'STD',
    players: [
      {
        fexerjId: 3741,
        name: 'Carlos Mendes',
        initialRating: 1800,
        finalRating: 1807,
        delta: 7,
        games: 5,
        path: 'RATED',
      },
      {
        fexerjId: 643,
        name: 'Roberto Faria',
        initialRating: 1900,
        finalRating: 1896,
        delta: -4,
        games: 5,
        path: 'RATED',
      },
    ],
    summary: { total: 2, up: 1, down: 1, unchanged: 0, maxUp: 7, maxDown: -4, medianAbs: 5.5 },
  },
]

const UNRATED_MODALITY = [
  {
    modality: 'RPD',
    players: [
      {
        fexerjId: 5400,
        name: 'Bruno Teixeira',
        initialRating: null,
        finalRating: null,
        delta: null,
        games: 3,
        path: 'ACCUMULATING',
      },
    ],
    summary: { total: 0, up: 0, down: 0, unchanged: 0, maxUp: null, maxDown: null, medianAbs: null },
  },
]

describe('PeriodSummary', () => {
  it('names the modality in Portuguese', () => {
    render(<PeriodSummary modalities={MODALITIES} />)
    expect(screen.getByText(/clássico/i)).toBeInTheDocument()
  })

  it('says how many went up and how many went down', () => {
    render(<PeriodSummary modalities={MODALITIES} />)
    expect(screen.getByText(/1 subiu/i)).toBeInTheDocument()
    expect(screen.getByText(/1 caiu/i)).toBeInTheDocument()
  })

  it('lists the players with their variation', () => {
    render(<PeriodSummary modalities={MODALITIES} />)
    expect(screen.getByText('Carlos Mendes')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
    expect(screen.getByText('-4')).toBeInTheDocument()
  })

  it('shows a player who is still unrated as such, instead of as a zero', () => {
    render(<PeriodSummary modalities={UNRATED_MODALITY} />)
    expect(screen.getByText('Bruno Teixeira')).toBeInTheDocument()
    expect(screen.getAllByText(/não-rated/i).length).toBeGreaterThan(0)
  })

  it('warns when the period moved nobody', () => {
    render(<PeriodSummary modalities={[]} />)
    expect(screen.getByText(/nenhum jogador/i)).toBeInTheDocument()
  })
})
