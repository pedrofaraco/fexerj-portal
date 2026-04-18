import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ResultsPage, { TournamentAccordion, PlayerRow } from './ResultsPage'

const RUN_RESULT_OK = {
  zipBlob: new Blob(['PK'], { type: 'application/zip' }),
  zipFilename: 'rating_cycle_output.zip',
  parseError: null,
  tournaments: [
    {
      ord: 1,
      crId: 99999,
      name: 'Copa Teste',
      type: 'RR',
      typeLabelPt: 'Round-robin',
      endDate: '2025-01-01',
      isFexerj: true,
      isIrt: false,
      players: [
        {
          fexerjId: 100,
          name: 'João Silva',
          oldRating: 1800,
          newRating: 1823,
          delta: 23,
          calcRule: 'NORMAL',
          gamesBefore: 50,
          validGames: 5,
          k: 25,
          pointsScored: 3.5,
          erm: 8750,
          avgOpponRating: 1750,
          dif: 50,
          we: 0.59,
          expectedPoints: 2.95,
          pointsAboveExpected: 0.55,
          kDw: 13.75,
          newTotalGames: 55,
          pRatio: 0.7,
          boardNo: 1,
        },
      ],
    },
  ],
}

describe('ResultsPage', () => {
  const onNewRun = vi.fn()
  const onLogout = vi.fn()

  beforeEach(() => {
    onNewRun.mockClear()
    onLogout.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders title and actions', () => {
    render(<ResultsPage runResult={RUN_RESULT_OK} onNewRun={onNewRun} onLogout={onLogout} />)
    expect(screen.getByRole('heading', { name: /resultado do ciclo de rating/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /baixar zip/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /nova execução/i })).toBeInTheDocument()
  })

  it('shows parse error banner but keeps download', () => {
    render(
      <ResultsPage
        runResult={{
          zipBlob: new Blob(['x']),
          zipFilename: 'rating_cycle_output.zip',
          tournaments: [],
          parseError: 'ZIP inválido para teste.',
        }}
        onNewRun={onNewRun}
        onLogout={onLogout}
      />,
    )
    expect(screen.getByText(/ZIP inválido para teste/i)).toBeInTheDocument()
    expect(screen.queryByText(/Copa Teste/i)).not.toBeInTheDocument()
  })

  it('Nova execução calls callback', () => {
    render(<ResultsPage runResult={RUN_RESULT_OK} onNewRun={onNewRun} onLogout={onLogout} />)
    fireEvent.click(screen.getByRole('button', { name: /nova execução/i }))
    expect(onNewRun).toHaveBeenCalledTimes(1)
  })

  it('creates object URL for download button', async () => {
    const createSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url')
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    render(<ResultsPage runResult={RUN_RESULT_OK} onNewRun={onNewRun} onLogout={onLogout} />)

    await vi.waitFor(() => expect(createSpy).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: /baixar zip/i }))
    expect(createSpy).toHaveBeenCalledWith(RUN_RESULT_OK.zipBlob)

    createSpy.mockRestore()
    revokeSpy.mockRestore()
  })
})

describe('TournamentAccordion', () => {
  it('toggle expands and sets aria-expanded', () => {
    render(
      <TournamentAccordion
        tournament={{
          ord: 1,
          name: 'X',
          typeLabelPt: 'Round-robin',
          players: [{ fexerjId: 1, name: 'A', oldRating: 1, newRating: 2, delta: 1, calcRule: 'NORMAL' }],
        }}
      />,
    )
    const btn = screen.getByRole('button', { name: /1 — X/i })
    expect(btn).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(btn)
    expect(btn).toHaveAttribute('aria-expanded', 'true')
    expect(btn).toHaveAttribute('aria-controls')
  })
})

describe('PlayerRow', () => {
  it('has aria-expanded on toggle', () => {
    const player = RUN_RESULT_OK.tournaments[0].players[0]
    render(<PlayerRow player={player} index={0} />)
    const btn = screen.getByRole('button', { name: /João Silva/i })
    expect(btn).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(btn)
    expect(btn).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/Jogos anteriores/i)).toBeInTheDocument()
  })

  it('formats non-integer ratings and non-positive deltas', () => {
    const player = {
      ...RUN_RESULT_OK.tournaments[0].players[0],
      oldRating: 1800.25,
      newRating: 1802.75,
      delta: -3.5,
      calcRule: 'NORMAL',
    }
    render(<PlayerRow player={player} index={0} />)
    expect(screen.getByText(/1800\.25/)).toBeInTheDocument()
    expect(screen.getByText(/1802\.75/)).toBeInTheDocument()
    expect(screen.getByText(/\(-3\.5\)/)).toBeInTheDocument()
  })
})
