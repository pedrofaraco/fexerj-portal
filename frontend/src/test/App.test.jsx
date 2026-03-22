import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function csvFile(name) {
  return new File(['id;name\n1;test'], name, { type: 'text/csv' })
}

function binaryFile(name) {
  return new File([new Uint8Array([0x00, 0x01])], name, { type: 'application/octet-stream' })
}

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

  it('run button is enabled when all required fields are filled', async () => {
    await uploadAllFiles(user)
    expect(screen.getByRole('button', { name: /^run$/i })).toBeEnabled()
  })

  it('shows "Running…" while the request is in flight', async () => {
    global.fetch = vi.fn(() => new Promise(() => {})) // never resolves

    await uploadAllFiles(user)
    submitRunForm()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /running/i })).toBeDisabled()
    )
  })

  it('displays the error message on a 422 response', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: 'Binary file not found' }),
      })
    )

    await uploadAllFiles(user)
    submitRunForm()

    await waitFor(() =>
      expect(screen.getByText('Binary file not found')).toBeInTheDocument()
    )
  })

  it('returns to the login page on a 401 response', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) })
    )

    await uploadAllFiles(user)
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
