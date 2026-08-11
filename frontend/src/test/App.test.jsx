import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import JSZip from 'jszip'
import App from '../App'
import ErrorBoundary from '../ErrorBoundary'
import {
  AUDIT_FILE_HEADER,
  AUDIT_PREAMBLE,
  FIDE_GAMES_PREAMBLE,
  FIDE_PERIOD_PREAMBLE,
} from '../resultParser'
import {
  FIDE_TOURNAMENTS_HEADER,
  PLAYERS_HEADER,
  TOURNAMENTS_HEADER,
} from '../csvUploadValidation'

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

function mockFetch({ validateErrors = [], runResponse = null, loginOk = true } = {}) {
  globalThis.fetch = vi.fn((url) => {
    if (url === '/me') {
      return Promise.resolve({
        ok: loginOk,
        status: loginOk ? 200 : 401,
        json: () => Promise.resolve(loginOk ? { ok: true } : {}),
      })
    }
    if (url === '/validate') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ errors: validateErrors }),
      })
    }
    // /run — use the provided response or hang forever by default
    return runResponse ?? new Promise(() => {})
  })
}

// ---------------------------------------------------------------------------
// File helpers
// ---------------------------------------------------------------------------

function csvFile(name, content = 'id;name\n1;test') {
  return new File([content], name, { type: 'text/csv' })
}

function binaryFile(name) {
  return new File([new Uint8Array([0x00, 0x01])], name, { type: 'application/octet-stream' })
}

const PLAYERS_CSV_FIXTURE = `${PLAYERS_HEADER}
3741;;;Roberto Oliveira Lima, Marcio;1500;CLUB A;01/01/1990;M;BRA;50;0;0`

function playersCsvFixtureFile() {
  return new File([PLAYERS_CSV_FIXTURE], 'players.csv', { type: 'text/csv' })
}

const TOURNAMENTS_CSV_FIXTURE = `${TOURNAMENTS_HEADER}
1;99999;Copa Fixture;2025-01-01;RR;0;1`

function tournamentsCsvFixtureFile() {
  return new File([TOURNAMENTS_CSV_FIXTURE], 'tournaments.csv', { type: 'text/csv' })
}

const FIDE_TOURNAMENTS_CSV_FIXTURE = `${FIDE_TOURNAMENTS_HEADER}
1;99999;Copa Fixture;2026-03-15;RR;0;1;STD`

function fideTournamentsCsvFixtureFile() {
  return new File([FIDE_TOURNAMENTS_CSV_FIXTURE], 'tournaments.csv', { type: 'text/csv' })
}

async function fixtureRunZipBlob() {
  const auditRow =
    '100;João Silva;1;1800;50;25;3.5;5;8750;1750;50;0.59;2.95;0.55;13.75;1823;55;0.7;NORMAL'
  const z = new JSZip()
  z.file('Audit_of_Tournament_1.csv', `${AUDIT_PREAMBLE}\n${AUDIT_FILE_HEADER}\n${auditRow}`)
  return z.generateAsync({ type: 'blob' })
}

function mockFetchWithSuccessfulRun(zipBlob) {
  globalThis.fetch = vi.fn(url => {
    if (url === '/me') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ok: true }),
      })
    }
    if (url === '/validate') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ errors: [] }),
      })
    }
    if (url === '/run') {
      return Promise.resolve({
        ok: true,
        status: 200,
        blob: () => Promise.resolve(zipBlob),
      })
    }
    return new Promise(() => {})
  })
}

// ---------------------------------------------------------------------------
// Interaction helpers
// ---------------------------------------------------------------------------

async function login(user) {
  mockFetch()
  await user.type(screen.getByLabelText(/usuário/i), 'fexerj')
  await user.type(screen.getByLabelText(/senha/i), 'changeme')
  await user.click(screen.getByRole('button', { name: /entrar/i }))
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /execução do ciclo de rating/i })).toBeInTheDocument()
  )
}

async function uploadAllFiles(user, { tournamentsFile, playersFile } = {}) {
  await user.upload(
    screen.getByLabelText(/lista de jogadores/i),
    playersFile ?? playersCsvFixtureFile(),
  )
  await user.upload(
    screen.getByLabelText(/arquivo de torneios/i),
    tournamentsFile ?? tournamentsCsvFixtureFile(),
  )
  await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeEnabled()
  )
}

function submitRunForm() {
  fireEvent.submit(screen.getByRole('button', { name: /^executar$/i }).closest('form'))
}

// ---------------------------------------------------------------------------
// Login page
// ---------------------------------------------------------------------------

describe('LoginPage', () => {
  it('renders the login form', () => {
    render(<App />)
    expect(screen.getByLabelText(/usuário/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
  })

  it('sends UTF-8 safe Basic auth for Latin-1 credentials (accents)', async () => {
    globalThis.fetch = vi.fn((url, init) => {
      expect(url).toBe('/me')
      expect(init?.headers?.Authorization).toBe('Basic ZmV4ZXJqOnBhw6dzd2Q=')
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ok: true }),
      })
    })

    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText(/usuário/i), 'fexerj')
    await user.type(screen.getByLabelText(/senha/i), 'paçswd')
    await user.click(screen.getByRole('button', { name: /entrar/i }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /execução do ciclo de rating/i })).toBeInTheDocument()
    )
  })

  it('shows the run page after successful login', async () => {
    const user = userEvent.setup()
    render(<App />)
    await login(user)
    expect(screen.getByRole('heading', { name: /execução do ciclo de rating/i })).toBeInTheDocument()
  })

  it('shows error message on wrong credentials', async () => {
    mockFetch({ loginOk: false })
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText(/usuário/i), 'wrong')
    await user.type(screen.getByLabelText(/senha/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /entrar/i }))
    await waitFor(() =>
      expect(screen.getByText(/usuário ou senha incorretos/i)).toBeInTheDocument()
    )
  })

  it('stays on login page after wrong credentials', async () => {
    mockFetch({ loginOk: false })
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText(/usuário/i), 'wrong')
    await user.type(screen.getByLabelText(/senha/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /entrar/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
    )
    expect(screen.queryByRole('heading', { name: /execução do ciclo de rating/i })).not.toBeInTheDocument()
  })
  it('shows error message on server error during login', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })
    )
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText(/usuário/i), 'fexerj')
    await user.type(screen.getByLabelText(/senha/i), 'changeme')
    await user.click(screen.getByRole('button', { name: /entrar/i }))
    await waitFor(() =>
      expect(
        screen.getByText(/não foi possível conectar ao servidor/i),
      ).toBeInTheDocument()
    )
  })

  it('stays on login page on server error during login', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })
    )
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText(/usuário/i), 'fexerj')
    await user.type(screen.getByLabelText(/senha/i), 'changeme')
    await user.click(screen.getByRole('button', { name: /entrar/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
    )
    expect(
      screen.queryByRole('heading', { name: /execução do ciclo de rating/i }),
    ).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Run page
// ---------------------------------------------------------------------------

describe('RunPage', () => {
  let user

  beforeEach(async () => {
    user = userEvent.setup()
    render(<App />)
    await login(user)
    mockFetch() // /validate returns no errors; /run hangs by default
  })

  it('renders all upload fields and inputs', () => {
    expect(screen.getByLabelText(/lista de jogadores/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/arquivo de torneios/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/arquivos binários/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/primeiro torneio/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/quantidade/i)).toBeInTheDocument()
  })

  it('run button is disabled when no files are selected', () => {
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
  })

  it('run button is enabled when all required fields are filled and validation passes', async () => {
    await uploadAllFiles(user)
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeEnabled()
  })

  it('shows "Executando…" while the request is in flight', async () => {
    await uploadAllFiles(user)

    // Override fetch so /run never resolves after validation has already passed
    globalThis.fetch = vi.fn(() => new Promise(() => {}))
    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /executando/i })).toBeDisabled()
    )
  })

  it('displays the error message on a 422 response', async () => {
    await uploadAllFiles(user)

    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: 'Binary file not found' }),
      })
    )

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByText('Binary file not found')).toBeInTheDocument()
    )
  })

  it('displays multiple 422 error lines when detail is an array', async () => {
    await uploadAllFiles(user)

    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        json: () =>
          Promise.resolve({
            detail: ['First problem from server', 'Second problem from server'],
          }),
      })
    )

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByText(/o servidor rejeitou a execução/i)).toBeInTheDocument()
    )
    expect(screen.getByText('First problem from server')).toBeInTheDocument()
    expect(screen.getByText('Second problem from server')).toBeInTheDocument()
  })

  it('displays 422 errors when detail is FastAPI-style objects with msg', async () => {
    await uploadAllFiles(user)

    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        json: () =>
          Promise.resolve({
            detail: [{ msg: 'campo inválido: first' }, { msg: 'campo inválido: count' }],
          }),
      })
    )

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByText(/o servidor rejeitou a execução/i)).toBeInTheDocument()
    )
    expect(screen.getByText('campo inválido: first')).toBeInTheDocument()
    expect(screen.getByText('campo inválido: count')).toBeInTheDocument()
  })

  it('returns to the login page on a 401 response', async () => {
    await uploadAllFiles(user)

    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) })
    )

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
    )
  })

  it('sign out during run does not show a connection error', async () => {
    await uploadAllFiles(user)

    globalThis.fetch = vi.fn((url, init) => {
      if (url === '/me') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true }),
        })
      }
      if (url === '/validate') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ errors: [] }),
        })
      }
      if (url === '/run') {
        const signal = init?.signal
        return new Promise((_resolve, reject) => {
          const onAbort = () => {
            reject(Object.assign(new Error('Aborted'), { name: 'AbortError' }))
          }
          if (signal?.aborted) {
            onAbort()
            return
          }
          signal?.addEventListener('abort', onAbort)
        })
      }
      return new Promise(() => {})
    })

    submitRunForm()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /executando/i })).toBeDisabled()
    )
    await user.click(screen.getByRole('button', { name: /sair/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
    )
    expect(screen.queryByText(/não foi possível conectar ao servidor/i)).not.toBeInTheDocument()
  })

  it('sign out button returns to the login page', async () => {
    await user.click(screen.getByRole('button', { name: /sair/i }))
    expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Results page flow
// ---------------------------------------------------------------------------

describe('Results page flow', () => {
  it('shows results summary after successful run (no auto-download)', async () => {
    const zipBlob = await fixtureRunZipBlob()

    const user = userEvent.setup()
    render(<App />)
    await login(user)
    mockFetchWithSuccessfulRun(zipBlob)

    await uploadAllFiles(user, { tournamentsFile: tournamentsCsvFixtureFile() })

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /resultado do ciclo de rating/i })).toBeInTheDocument(),
    )
    expect(screen.getByText(/Copa Fixture/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /baixar zip/i })).toBeInTheDocument()
  })

  it('Nova execução returns to upload page with files preserved', async () => {
    const zipBlob = await fixtureRunZipBlob()

    const user = userEvent.setup()
    render(<App />)
    await login(user)
    mockFetchWithSuccessfulRun(zipBlob)

    await uploadAllFiles(user, { tournamentsFile: tournamentsCsvFixtureFile() })

    submitRunForm()
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /resultado do ciclo de rating/i })).toBeInTheDocument(),
    )

    await user.click(screen.getByRole('button', { name: /nova execução/i }))

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /execução do ciclo de rating/i })).toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeEnabled()
    expect(screen.getByText(/arquivo selecionado: players\.csv/i)).toBeInTheDocument()
    expect(screen.getByText(/arquivo selecionado: tournaments\.csv/i)).toBeInTheDocument()
    expect(screen.getByText(/arquivo selecionado: 1-99999\.turx/i)).toBeInTheDocument()
  })

  it('the form is still submittable after Nova execução, with the files it kept', async () => {
    // Coming back remounts the form, and a file input cannot be repopulated by
    // JavaScript, so the three widgets are empty while the files are still in
    // state. With `required` on those widgets the browser refuses the submit
    // ("Please select a file") and the run is impossible without re-picking
    // files that were never lost. `fireEvent.submit` bypasses that check, so
    // this asserts what the browser actually evaluates.
    const zipBlob = await fixtureRunZipBlob()

    const user = userEvent.setup()
    render(<App />)
    await login(user)
    mockFetchWithSuccessfulRun(zipBlob)

    await uploadAllFiles(user, { tournamentsFile: tournamentsCsvFixtureFile() })
    submitRunForm()
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /resultado do ciclo de rating/i })).toBeInTheDocument(),
    )

    await user.click(screen.getByRole('button', { name: /nova execução/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /^executar$/i })).toBeEnabled(),
    )

    const form = screen.getByRole('button', { name: /^executar$/i }).closest('form')
    expect(form.checkValidity()).toBe(true)
  })

  it('still requires a file the first time, when nothing is in state yet', async () => {
    mockFetch()
    const user = userEvent.setup()
    render(<App />)
    await login(user)

    const form = screen.getByRole('button', { name: /^executar$/i }).closest('form')
    expect(form.checkValidity()).toBe(false)
  })

  it('Limpar formulário resets inputs and disables run', async () => {
    mockFetch()
    const user = userEvent.setup()
    render(<App />)
    await login(user)
    await uploadAllFiles(user, { tournamentsFile: tournamentsCsvFixtureFile() })

    const playersInput = screen.getByLabelText(/lista de jogadores/i)
    const tournamentsInput = screen.getByLabelText(/arquivo de torneios/i)
    const binariesInput = screen.getByLabelText(/arquivos binários/i)
    expect(playersInput.files).toHaveLength(1)
    expect(tournamentsInput.files).toHaveLength(1)
    expect(binariesInput.files).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: /limpar formulário/i }))

    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
    expect(screen.getByLabelText(/lista de jogadores/i).files).toHaveLength(0)
    expect(screen.getByLabelText(/arquivo de torneios/i).files).toHaveLength(0)
    expect(screen.getByLabelText(/arquivos binários/i).files).toHaveLength(0)
    expect(screen.queryByText(/arquivo selecionado:/i)).not.toBeInTheDocument()
  })

  it('runs the per-game model end to end and shows the period summary', async () => {
    // Covers the whole chain in one go: the mode reaches the request, the
    // browser-side check accepts the per-game formats, and the period audit
    // becomes the on-screen summary instead of the per-tournament view.
    const z = new JSZip()
    z.file('RatingList.csv', 'x')
    z.file('Audit_Games.csv', `${FIDE_GAMES_PREAMBLE}\nTournament\n`)
    z.file(
      'Audit_Period.csv',
      `${FIDE_PERIOD_PREAMBLE}\n` +
        'Tournaments;PlayerId;PlayerName;TimeControl;InitialRating;Games;SumDeltaR;Variation;' +
        'RoundedVariation;FinalRating;Path;AccumSumOpp;AccumPoints;AccumGames;AccumSince\n' +
        '1;3741;Carlos Mendes;STD;1800;5;0.36;7.2;7;1807;RATED;0;0;0;\n',
    )
    const zipBlob = await z.generateAsync({ type: 'blob' })

    const user = userEvent.setup()
    render(<App />)
    await login(user)
    mockFetchWithSuccessfulRun(zipBlob)

    await user.selectOptions(screen.getByLabelText(/modelo de cálculo/i), 'fide')
    await uploadAllFiles(user, {
      tournamentsFile: fideTournamentsCsvFixtureFile(),
    })

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /resultado do ciclo de rating/i })).toBeInTheDocument(),
    )
    expect(screen.getByText(/clássico/i)).toBeInTheDocument()
    expect(screen.getByText('Carlos Mendes')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /por torneio/i })).not.toBeInTheDocument()

    const runCall = globalThis.fetch.mock.calls.find(([url]) => url === '/run')
    expect(runCall[1].body.get('mode')).toBe('fide')
  })

  it('shows parse error banner when ZIP cannot be summarized but still allows download', async () => {
    const emptyZipBlob = await new JSZip().generateAsync({ type: 'blob' })

    const user = userEvent.setup()
    render(<App />)
    await login(user)
    mockFetchWithSuccessfulRun(emptyZipBlob)

    await uploadAllFiles(user, { tournamentsFile: tournamentsCsvFixtureFile() })

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByText(/não foi possível exibir o resumo/i)).toBeInTheDocument(),
    )
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /baixar zip/i })).toBeEnabled(),
    )
  })
})

// ---------------------------------------------------------------------------
// Help section
// ---------------------------------------------------------------------------

describe('HelpSection', () => {
  beforeEach(async () => {
    mockFetch()
    const user = userEvent.setup()
    render(<App />)
    await login(user)
  })

  it('is collapsed by default', () => {
    expect(screen.queryByText(/preparar os arquivos/i)).not.toBeInTheDocument()
  })

  it('expands when the toggle button is clicked', async () => {
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /como usar/i }))
    expect(screen.getByText(/preparar os arquivos/i)).toBeInTheDocument()
  })

  it('collapses again when the toggle button is clicked a second time', async () => {
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /como usar/i }))
    await user.click(screen.getByRole('button', { name: /como usar/i }))
    expect(screen.queryByText(/preparar os arquivos/i)).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Validation UX
// ---------------------------------------------------------------------------

describe('Validation', () => {
  let user

  beforeEach(async () => {
    user = userEvent.setup()
    render(<App />)
    await login(user)
  })

  it('shows "Validando arquivos…" while validation is in flight', async () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {})) // /validate never resolves

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText(/validando arquivos/i)).toBeInTheDocument()
    )
  })

  it('sign out during validation does not show a false connection error', async () => {
    globalThis.fetch = vi.fn((url, init) => {
      if (url === '/me') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true }),
        })
      }
      if (url === '/validate') {
        const signal = init?.signal
        return new Promise((_resolve, reject) => {
          const onAbort = () => {
            reject(Object.assign(new Error('Aborted'), { name: 'AbortError' }))
          }
          if (signal?.aborted) {
            onAbort()
            return
          }
          signal?.addEventListener('abort', onAbort)
        })
      }
      return new Promise(() => {})
    })

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText(/validando arquivos/i)).toBeInTheDocument()
    )
    await user.click(screen.getByRole('button', { name: /sair/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
    )
    expect(
      screen.queryByText(/não foi possível conectar ao servidor para validar/i),
    ).not.toBeInTheDocument()
  })

  it('shows frontend CSV errors when tournaments file has wrong column count', async () => {
    mockFetch()
    await user.upload(
      screen.getByLabelText(/arquivo de torneios/i),
      csvFile('bad-tournaments.csv', `${TOURNAMENTS_HEADER}\n1;99999;Copa\n`),
    )
    await waitFor(() =>
      expect(screen.getByText(/tournaments.csv linha 2: esperadas 7 colunas/)).toBeInTheDocument(),
    )
  })

  it('shows frontend CSV errors when players file has invalid header', async () => {
    mockFetch()
    await user.upload(
      screen.getByLabelText(/lista de jogadores/i),
      csvFile('bad-players.csv', 'Id_No;Name\n1;Test\n'),
    )
    await waitFor(() =>
      expect(screen.getByText(/players.csv: cabeçalho inválido/)).toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
  })

  it('shows "Arquivos validados com sucesso." when validation returns no errors', async () => {
    mockFetch()
    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText(/arquivos validados com sucesso/i)).toBeInTheDocument()
    )
  })

  it('shows validation errors and keeps run button disabled', async () => {
    mockFetch({ validateErrors: ['players.csv row 2: Id_No is required'] })

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText('players.csv row 2: Id_No is required')).toBeInTheDocument()
    )
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
  })

  it('shows multiple validation errors as a list', async () => {
    mockFetch({
      validateErrors: [
        'players.csv row 2: Id_No is required',
        'tournaments.csv row 2: Type is required',
      ],
    })

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() => {
      expect(screen.getByText('players.csv row 2: Id_No is required')).toBeInTheDocument()
      expect(screen.getByText('tournaments.csv row 2: Type is required')).toBeInTheDocument()
    })
  })

  it('shows request error when validate returns non-OK and keeps run disabled', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url === '/me') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true }),
        })
      }
      if (url === '/validate') {
        return Promise.resolve({ ok: false, status: 502 })
      }
      return new Promise(() => {})
    })

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() => {
      expect(screen.getByText(/resposta HTTP 502/i)).toBeInTheDocument()
      expect(screen.queryByText(/validando arquivos/i)).not.toBeInTheDocument()
    })
    expect(screen.queryByText(/arquivos validados com sucesso/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
  })

  it('shows request error when validate request fails (network)', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url === '/me') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true }),
        })
      }
      if (url === '/validate') {
        return Promise.reject(new Error('network'))
      }
      return new Promise(() => {})
    })

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() => {
      expect(screen.getByText(/não foi possível conectar ao servidor para validar/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
  })

  it('shows request error when validate returns invalid JSON', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url === '/me') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true }),
        })
      }
      if (url === '/validate') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.reject(new SyntaxError('invalid json')),
        })
      }
      return new Promise(() => {})
    })

    await user.upload(screen.getByLabelText(/lista de jogadores/i), playersCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivo de torneios/i), tournamentsCsvFixtureFile())
    await user.upload(screen.getByLabelText(/arquivos binários/i), binaryFile('1-99999.TURX'))

    await waitFor(() => {
      expect(screen.getByText(/resposta inválida do servidor ao validar/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /^executar$/i })).toBeDisabled()
  })
})

// ---------------------------------------------------------------------------
// ErrorBoundary
// ---------------------------------------------------------------------------

function ThrowingComponent() {
  throw new Error('test error')
}

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(<ErrorBoundary><p>conteúdo</p></ErrorBoundary>)
    expect(screen.getByText('conteúdo')).toBeInTheDocument()
  })

  it('shows the fallback UI when a child throws', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(<ErrorBoundary><ThrowingComponent /></ErrorBoundary>)
    expect(screen.getByText(/algo deu errado/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /recarregar/i })).toBeInTheDocument()
    spy.mockRestore()
  })

  it('does not render children when a child throws', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(<ErrorBoundary><ThrowingComponent /><p>nunca renderizado</p></ErrorBoundary>)
    expect(screen.queryByText('nunca renderizado')).not.toBeInTheDocument()
    spy.mockRestore()
  })
})
