import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, within, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import JSZip from 'jszip'
import ResultsPage from './ResultsPage'
import { AUDIT_FILE_HEADER, AUDIT_PREAMBLE, parseRunResult } from './resultParser'

const TOURNAMENTS_CSV = `Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
1;11111;Copa A;2025-01-01;RR;0;1
2;22222;Copa B;2025-02-01;RR;0;1`

const ROW_100_T1 =
  '100;João Silva;1;1800;50;25;3.5;5;8750;1750;50;0.59;2.95;0.55;13.75;1823;55;0.7;NORMAL'
const ROW_100_T2 =
  '100;João Silva;1;1823;55;25;3.0;4;8000;1800;20;0.55;2.2;0.1;1.5;1840;59;0.75;NORMAL'
const ROW_200_T2 =
  '200;Ana Costa;2;1700;30;20;2.0;4;7000;1750;0;0.5;2.0;0;0;1710;34;0.5;NORMAL'

async function runResultFromZips() {
  const z = new JSZip()
  z.file('Audit_of_Tournament_1.csv', `${AUDIT_PREAMBLE}\n${AUDIT_FILE_HEADER}\n${ROW_100_T1}`)
  z.file('Audit_of_Tournament_2.csv', `${AUDIT_PREAMBLE}\n${AUDIT_FILE_HEADER}\n${ROW_100_T2}\n${ROW_200_T2}`)
  const blob = await z.generateAsync({ type: 'blob' })
  return parseRunResult(blob, TOURNAMENTS_CSV)
}

describe('ResultsPage', () => {
  let runResult

  beforeEach(async () => {
    runResult = await runResultFromZips()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('defaults to Por torneio tab and shows tournament accordions', () => {
    const onNew = vi.fn()
    const onOut = vi.fn()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={onNew}
        onLogout={onOut}
      />,
    )

    const t1 = screen.getByRole('tab', { name: /por torneio/i })
    const t2 = screen.getByRole('tab', { name: /por jogador/i })
    expect(t1).toHaveAttribute('aria-selected', 'true')
    expect(t2).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByText(/1 — Copa A/)).toBeInTheDocument()
    expect(screen.getByText(/2 — Copa B/)).toBeInTheDocument()
  })

  it('switches to Por jogador and shows player summary with rating span and torneios count', async () => {
    const user = userEvent.setup()
    const onNew = vi.fn()
    const onOut = vi.fn()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={onNew}
        onLogout={onOut}
      />,
    )

    await user.click(screen.getByRole('tab', { name: /por jogador/i }))

    expect(screen.getByRole('tab', { name: /por jogador/i })).toHaveAttribute('aria-selected', 'true')
    // João: 1800 → 1840, 2 torneios; name sort: Ana before João
    expect(screen.getByText(/2 torneios/)).toBeInTheDocument()
    expect(screen.getByText(/1800/)).toBeInTheDocument()
    expect(screen.getByText(/1840/)).toBeInTheDocument()
  })

  it('arrow keys move between tabs', async () => {
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    const tabT = screen.getByRole('tab', { name: /por torneio/i })
    const tabP = screen.getByRole('tab', { name: /por jogador/i })
    tabT.focus()
    fireEvent.keyDown(tabT, { key: 'ArrowRight', code: 'ArrowRight' })
    await waitFor(() => {
      expect(tabP).toHaveFocus()
      expect(tabP).toHaveAttribute('aria-selected', 'true')
    })
    fireEvent.keyDown(tabP, { key: 'ArrowLeft', code: 'ArrowLeft' })
    await waitFor(() => {
      expect(tabT).toHaveFocus()
      expect(tabT).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('nested expand shows same calculation labels as tournament view', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('tab', { name: /por jogador/i }))

    const joaoBtn = screen
      .getAllByRole('button', { expanded: false })
      .find(btn => btn.textContent.includes('João Silva') && btn.textContent.includes('torneios'))
    expect(joaoBtn).toBeTruthy()
    await user.click(joaoBtn)

    const playerPanel = screen.getByRole('tabpanel', { name: /por jogador/i })
    const copaA = within(playerPanel).getByRole('button', { name: /Copa A.*1823/s })
    await user.click(copaA)

    const contentId = copaA.getAttribute('aria-controls')
    expect(contentId).toBeTruthy()
    const grid = document.getElementById(contentId)
    expect(grid).toBeTruthy()
    expect(within(grid).getByText(/Jogos anteriores/)).toBeInTheDocument()
    // "Pontos esperados" also appears as prefix of "Pontos esperados por partida (We)" — use a unique line.
    expect(within(grid).getByText(/Diferença \(obtido/)).toBeInTheDocument()
    expect(within(grid).getByText(/Número no torneio \(Chess Results\)/)).toBeInTheDocument()
  })

  it('Por torneio: expanding first tournament toggles aria-expanded and lists players', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    const copaHeader = screen.getByRole('button', { name: /Copa A/i })
    expect(copaHeader).toHaveAttribute('aria-expanded', 'false')
    await user.click(copaHeader)
    expect(copaHeader).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /João Silva.*1823/i })).toBeInTheDocument()
  })

  it('Por torneio: expanded player row shows non-integer ratings in summary', async () => {
    const decimalRow =
      '100;João Silva;1;1800.25;50;25;3.5;5;8750;1750;50;0.59;2.95;0.55;13.75;1823.75;55;0.7;NORMAL'
    const z = new JSZip()
    z.file('Audit_of_Tournament_1.csv', `${AUDIT_PREAMBLE}\n${AUDIT_FILE_HEADER}\n${decimalRow}`)
    const blob = await z.generateAsync({ type: 'blob' })
    const rr = await parseRunResult(blob, TOURNAMENTS_CSV.split('\n').slice(0, 2).join('\n'))
    const user = userEvent.setup()
    render(
      <ResultsPage runResult={{ ...rr, parseError: undefined, zipFilename: 'x.zip' }} onNewRun={vi.fn()} onLogout={vi.fn()} />,
    )

    const tournamentPanel = document.getElementById('panel-results-tournament')
    await user.click(within(tournamentPanel).getByRole('button', { name: /Copa A/i }))
    const playerBtn = within(tournamentPanel).getByRole('button', { name: /João Silva/i })
    await user.click(playerBtn)
    expect(within(tournamentPanel).getAllByText(/1800\.25/).length).toBeGreaterThanOrEqual(1)
    expect(within(tournamentPanel).getAllByText(/1823\.75/).length).toBeGreaterThanOrEqual(1)
  })

  it('Home and End keys move focus and selection to first and last tab', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    const tabT = screen.getByRole('tab', { name: /por torneio/i })
    const tabP = screen.getByRole('tab', { name: /por jogador/i })
    await user.click(tabP)
    tabP.focus()
    fireEvent.keyDown(tabP, { key: 'Home', code: 'Home' })
    await waitFor(() => {
      expect(tabT).toHaveFocus()
      expect(tabT).toHaveAttribute('aria-selected', 'true')
    })
    fireEvent.keyDown(tabT, { key: 'End', code: 'End' })
    await waitFor(() => {
      expect(tabP).toHaveFocus()
      expect(tabP).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('Baixar ZIP triggers download via temporary anchor when blob URL exists', async () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'rating_cycle_output.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /baixar zip/i })).not.toBeDisabled()
    })
    await user.click(screen.getByRole('button', { name: /baixar zip/i }))
    expect(clickSpy).toHaveBeenCalled()
    clickSpy.mockRestore()
  })

  it('filters Por torneio accordions via shared search input', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    const tournamentPanel = document.getElementById('panel-results-tournament')
    const filter = screen.getByLabelText(/filtrar por nome ou ID/i)
    await user.type(filter, 'Copa B')
    expect(within(tournamentPanel).getByText(/2 — Copa B/)).toBeInTheDocument()
    expect(within(tournamentPanel).queryByText(/1 — Copa A/)).not.toBeInTheDocument()
  })

  it('filters Por jogador accordions via same search input', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('tab', { name: /por jogador/i }))
    const playerPanel = document.getElementById('panel-results-player')
    const filter = screen.getByLabelText(/filtrar por nome ou ID/i)
    await user.type(filter, 'Ana')
    expect(within(playerPanel).getByText(/Ana Costa/)).toBeInTheDocument()
    expect(within(playerPanel).queryByText(/João Silva/)).not.toBeInTheDocument()
  })

  it('shows empty state inside each tabpanel when filter matches nothing', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    const filter = screen.getByLabelText(/filtrar por nome ou ID/i)
    await user.type(filter, '__nomatch__')
    const tournamentPanel = document.getElementById('panel-results-tournament')
    const playerPanel = document.getElementById('panel-results-player')
    expect(within(tournamentPanel).getByText(/nenhum resultado encontrado/i)).toBeInTheDocument()
    expect(within(playerPanel).getByText(/nenhum resultado encontrado/i)).toBeInTheDocument()
  })

  it('keeps search text when switching tabs', async () => {
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...runResult, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )

    const filter = screen.getByLabelText(/filtrar por nome ou ID/i)
    await user.type(filter, 'Copa B')
    await user.click(screen.getByRole('tab', { name: /por jogador/i }))
    expect(filter).toHaveValue('Copa B')
    await user.click(screen.getByRole('tab', { name: /por torneio/i }))
    expect(filter).toHaveValue('Copa B')
  })

  it('shows 1 torneio singular when player has one tournament only', async () => {
    const z = new JSZip()
    z.file('Audit_of_Tournament_1.csv', `${AUDIT_PREAMBLE}\n${AUDIT_FILE_HEADER}\n${ROW_100_T1}`)
    const blob = await z.generateAsync({ type: 'blob' })
    const single = await parseRunResult(
      blob,
      `Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;1;Solo;;RR;0;1`,
    )
    const user = userEvent.setup()
    render(
      <ResultsPage
        runResult={{ ...single, parseError: undefined, zipFilename: 'x.zip' }}
        onNewRun={vi.fn()}
        onLogout={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /por jogador/i }))
    expect(screen.getByText(/1 torneio/)).toBeInTheDocument()
    expect(screen.queryByText(/1 torneios/)).not.toBeInTheDocument()
  })
})
