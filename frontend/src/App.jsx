import { useState } from 'react'

const INITIAL_FORM = {
  playersCsv: null,
  tournamentsCsv: null,
  binaryFiles: [],
  first: '1',
  count: '1',
}

export default function App() {
  const [credentials, setCredentials] = useState(null)
  const [form, setForm] = useState(INITIAL_FORM)
  const [status, setStatus] = useState('idle') // idle | loading | error
  const [errorMessage, setErrorMessage] = useState('')

  function handleLogin(e) {
    e.preventDefault()
    const data = new FormData(e.target)
    setCredentials({
      username: data.get('username'),
      password: data.get('password'),
    })
  }

  function handleLogout() {
    setCredentials(null)
    setForm(INITIAL_FORM)
    setStatus('idle')
    setErrorMessage('')
  }

  async function handleRun(e) {
    e.preventDefault()
    setStatus('loading')
    setErrorMessage('')

    const body = new FormData()
    body.append('players_csv', form.playersCsv)
    body.append('tournaments_csv', form.tournamentsCsv)
    for (const file of form.binaryFiles) {
      body.append('binary_files', file)
    }
    body.append('first', form.first)
    body.append('count', form.count)

    try {
      const response = await fetch('/run', {
        method: 'POST',
        headers: {
          Authorization: 'Basic ' + btoa(`${credentials.username}:${credentials.password}`),
        },
        body,
      })

      if (response.status === 401) {
        setCredentials(null)
        setStatus('idle')
        return
      }

      if (!response.ok) {
        const json = await response.json().catch(() => ({}))
        setErrorMessage(json.detail ?? `Unexpected error (HTTP ${response.status})`)
        setStatus('error')
        return
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'rating_cycle_output.zip'
      a.click()
      URL.revokeObjectURL(url)
      setStatus('idle')
    } catch {
      setErrorMessage('Could not reach the server. Please check your connection.')
      setStatus('error')
    }
  }

  if (!credentials) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <RunPage
      form={form}
      setForm={setForm}
      status={status}
      errorMessage={errorMessage}
      onRun={handleRun}
      onLogout={handleLogout}
    />
  )
}

// ---------------------------------------------------------------------------
// Login page
// ---------------------------------------------------------------------------

function LoginPage({ onLogin }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-gray-900 mb-1">FEXERJ Portal</h1>
        <p className="text-sm text-gray-500 mb-6">Staff access only</p>

        <form onSubmit={onLogin} className="flex flex-col gap-4">
          <Field label="Username">
            <input name="username" type="text" required autoFocus className="input" />
          </Field>

          <Field label="Password">
            <input name="password" type="password" required className="input" />
          </Field>

          <button type="submit" className="btn-primary mt-2">
            Sign in
          </button>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Run page
// ---------------------------------------------------------------------------

function RunPage({ form, setForm, status, errorMessage, onRun, onLogout }) {
  const isReady =
    form.playersCsv &&
    form.tournamentsCsv &&
    form.binaryFiles.length > 0 &&
    Number(form.first) >= 1 &&
    Number(form.count) >= 1

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">FEXERJ Portal</h1>
        <button
          onClick={onLogout}
          className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          Sign out
        </button>
      </header>

      <main className="max-w-xl mx-auto px-4 py-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Rating Cycle Runner</h2>
        <p className="text-sm text-gray-500 mb-8">
          Upload the input files, set the range, and download the updated rating lists.
        </p>

        <form onSubmit={onRun} className="flex flex-col gap-6">
          <Field label="Players CSV" hint="players.csv — initial rating list">
            <input
              type="file"
              accept=".csv"
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, playersCsv: e.target.files[0] ?? null }))}
            />
          </Field>

          <Field label="Tournaments CSV" hint="tournaments.csv — list of tournaments to process">
            <input
              type="file"
              accept=".csv"
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, tournamentsCsv: e.target.files[0] ?? null }))}
            />
          </Field>

          <Field label="Binary files" hint=".TUNX / .TURX / .TUMX — one or more files">
            <input
              type="file"
              accept=".TUNX,.TURX,.TUMX"
              multiple
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, binaryFiles: Array.from(e.target.files) }))}
            />
          </Field>

          <div className="flex gap-4">
            <Field label="First tournament" className="flex-1">
              <input
                type="number"
                min="1"
                required
                value={form.first}
                onChange={e => setForm(f => ({ ...f, first: e.target.value }))}
                className="input"
              />
            </Field>

            <Field label="Count" className="flex-1">
              <input
                type="number"
                min="1"
                required
                value={form.count}
                onChange={e => setForm(f => ({ ...f, count: e.target.value }))}
                className="input"
              />
            </Field>
          </div>

          {status === 'error' && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={!isReady || status === 'loading'}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'loading' ? 'Running…' : 'Run'}
          </button>
        </form>
      </main>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared components
// ---------------------------------------------------------------------------

function Field({ label, hint, className = '', children }) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {hint && <span className="text-xs text-gray-400">{hint}</span>}
      {children}
    </label>
  )
}
