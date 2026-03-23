import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

function mockFetch({ validateErrors = [], runResponse = null } = {}) {
  global.fetch = vi.fn((url) => {
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

function csvFile(name) {
  return new File(['id;name\n1;test'], name, { type: 'text/csv' })
}

function binaryFile(name) {
  return new File([new Uint8Array([0x00, 0x01])], name, { type: 'application/octet-stream' })
}

// ---------------------------------------------------------------------------
// Interaction helpers
// ---------------------------------------------------------------------------

async function login(user) {
  await user.type(screen.getByLabelText(/username/i), 'fexerj')
  await user.type(screen.getByLabelText(/password/i), 'changeme')
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

async function uploadAllFiles(user) {
  await user.upload(screen.getByLabelText(/players csv/i), csvFile('players.csv'))
  await user.upload(screen.getByLabelText(/tournaments csv/i), csvFile('tournaments.csv'))
  await user.upload(screen.getByLabelText(/binary files/i), binaryFile('1-99999.TURX'))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /^run$/i })).toBeEnabled()
  )
}

function submitRunForm() {
  fireEvent.submit(screen.getByRole('button', { name: /^run$/i }).closest('form'))
}

// ---------------------------------------------------------------------------
// Login page
// ---------------------------------------------------------------------------

describe('LoginPage', () => {
  it('renders the login form', () => {
    render(<App />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows the run page after login', async () => {
    const user = userEvent.setup()
    render(<App />)
    await login(user)
    expect(screen.getByRole('heading', { name: /rating cycle runner/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Run page
// ---------------------------------------------------------------------------

describe('RunPage', () => {
  let user

  beforeEach(async () => {
    mockFetch() // /validate returns no errors; /run hangs by default
    user = userEvent.setup()
    render(<App />)
    await login(user)
  })

  it('renders all upload fields and inputs', () => {
    expect(screen.getByLabelText(/players csv/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/tournaments csv/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/binary files/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/first tournament/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/count/i)).toBeInTheDocument()
  })

  it('run button is disabled when no files are selected', () => {
    expect(screen.getByRole('button', { name: /^run$/i })).toBeDisabled()
  })

  it('run button is enabled when all required fields are filled and validation passes', async () => {
    await uploadAllFiles(user)
    expect(screen.getByRole('button', { name: /^run$/i })).toBeEnabled()
  })

  it('shows "Running…" while the request is in flight', async () => {
    await uploadAllFiles(user)

    // Override fetch so /run never resolves after validation has already passed
    global.fetch = vi.fn(() => new Promise(() => {}))
    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /running/i })).toBeDisabled()
    )
  })

  it('displays the error message on a 422 response', async () => {
    await uploadAllFiles(user)

    global.fetch = vi.fn(() =>
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

  it('returns to the login page on a 401 response', async () => {
    await uploadAllFiles(user)

    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) })
    )

    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    )
  })

  it('sign out button returns to the login page', async () => {
    await user.click(screen.getByRole('button', { name: /sign out/i }))
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
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

  it('shows "Validating files…" while validation is in flight', async () => {
    global.fetch = vi.fn(() => new Promise(() => {})) // /validate never resolves

    await user.upload(screen.getByLabelText(/players csv/i), csvFile('players.csv'))
    await user.upload(screen.getByLabelText(/tournaments csv/i), csvFile('tournaments.csv'))
    await user.upload(screen.getByLabelText(/binary files/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText(/validating files/i)).toBeInTheDocument()
    )
  })

  it('shows "Files look good." when validation returns no errors', async () => {
    mockFetch()
    await user.upload(screen.getByLabelText(/players csv/i), csvFile('players.csv'))
    await user.upload(screen.getByLabelText(/tournaments csv/i), csvFile('tournaments.csv'))
    await user.upload(screen.getByLabelText(/binary files/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText(/files look good/i)).toBeInTheDocument()
    )
  })

  it('shows validation errors and keeps Run button disabled', async () => {
    mockFetch({ validateErrors: ['players.csv row 2: Id_No is required'] })

    await user.upload(screen.getByLabelText(/players csv/i), csvFile('players.csv'))
    await user.upload(screen.getByLabelText(/tournaments csv/i), csvFile('tournaments.csv'))
    await user.upload(screen.getByLabelText(/binary files/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText('players.csv row 2: Id_No is required')).toBeInTheDocument()
    )
    expect(screen.getByRole('button', { name: /^run$/i })).toBeDisabled()
  })

  it('shows multiple validation errors as a list', async () => {
    mockFetch({
      validateErrors: [
        'players.csv row 2: Id_No is required',
        'tournaments.csv row 2: Type is required',
      ],
    })

    await user.upload(screen.getByLabelText(/players csv/i), csvFile('players.csv'))
    await user.upload(screen.getByLabelText(/tournaments csv/i), csvFile('tournaments.csv'))
    await user.upload(screen.getByLabelText(/binary files/i), binaryFile('1-99999.TURX'))

    await waitFor(() =>
      expect(screen.getByText('players.csv row 2: Id_No is required')).toBeInTheDocument()
    )
    expect(screen.getByText('tournaments.csv row 2: Type is required')).toBeInTheDocument()
  })
})
