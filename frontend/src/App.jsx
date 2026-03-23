import { useState, useEffect } from 'react'

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
  const [validationErrors, setValidationErrors] = useState([])
  const [validationStatus, setValidationStatus] = useState('idle') // idle | checking | done

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
    setValidationErrors([])
    setValidationStatus('idle')
  }

  useEffect(() => {
    if (!credentials || !form.playersCsv || !form.tournamentsCsv || form.binaryFiles.length === 0) {
      setValidationErrors([])
      setValidationStatus('idle')
      return
    }

    let cancelled = false
    setValidationStatus('checking')
    setValidationErrors([])

    const body = new FormData()
    body.append('players_csv', form.playersCsv)
    body.append('tournaments_csv', form.tournamentsCsv)
    for (const file of form.binaryFiles) body.append('binary_files', file)
    body.append('first', form.first)
    body.append('count', form.count)

    fetch('/validate', {
      method: 'POST',
      headers: {
        Authorization: 'Basic ' + btoa(`${credentials.username}:${credentials.password}`),
      },
      body,
    })
      .then(res => {
        if (cancelled) return null
        if (res.status === 401) { setCredentials(null); return null }
        return res.ok ? res.json() : null
      })
      .then(json => {
        if (cancelled || !json) return
        setValidationErrors(json.errors ?? [])
        setValidationStatus('done')
      })
      .catch(() => {
        if (cancelled) return
        // On network error during validation, allow the user to try running anyway
        setValidationStatus('done')
      })

    return () => { cancelled = true }
  }, [form.playersCsv, form.tournamentsCsv, form.binaryFiles, form.first, form.count, credentials])

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
      setErrorMessage('Não foi possível conectar ao servidor. Verifique sua conexão.')
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
      validationErrors={validationErrors}
      validationStatus={validationStatus}
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
        <p className="text-sm text-gray-500 mb-6">Acesso restrito à equipe</p>

        <form onSubmit={onLogin} className="flex flex-col gap-4">
          <Field label="Usuário">
            <input name="username" type="text" required autoFocus className="input" />
          </Field>

          <Field label="Senha">
            <input name="password" type="password" required className="input" />
          </Field>

          <button type="submit" className="btn-primary mt-2">
            Entrar
          </button>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Run page
// ---------------------------------------------------------------------------

function RunPage({ form, setForm, status, errorMessage, validationErrors, validationStatus, onRun, onLogout }) {
  const isReady =
    form.playersCsv &&
    form.tournamentsCsv &&
    form.binaryFiles.length > 0 &&
    Number(form.first) >= 1 &&
    Number(form.count) >= 1 &&
    validationStatus === 'done' &&
    validationErrors.length === 0

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">FEXERJ Portal</h1>
        <button
          onClick={onLogout}
          className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          Sair
        </button>
      </header>

      <main className="max-w-xl mx-auto px-4 py-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Execução do Ciclo de Rating</h2>
        <p className="text-sm text-gray-500 mb-6">
          Carregue os arquivos de entrada, defina o intervalo e faça o download das listas de rating atualizadas.
        </p>

        <HelpSection />

        <form onSubmit={onRun} className="flex flex-col gap-6">
          <Field label="Lista de Jogadores" hint="players.csv — lista de rating inicial">
            <input
              type="file"
              accept=".csv"
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, playersCsv: e.target.files[0] ?? null }))}
            />
          </Field>

          <Field label="Arquivo de Torneios" hint="tournaments.csv — lista de torneios a processar">
            <input
              type="file"
              accept=".csv"
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, tournamentsCsv: e.target.files[0] ?? null }))}
            />
          </Field>

          <Field label="Arquivos Binários" hint=".TUNX / .TURX / .TUMX — um ou mais arquivos">
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
            <Field label="Primeiro torneio" className="flex-1">
              <input
                type="number"
                min="1"
                required
                value={form.first}
                onChange={e => setForm(f => ({ ...f, first: e.target.value }))}
                className="input"
              />
            </Field>

            <Field label="Quantidade" className="flex-1">
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

          {validationStatus === 'checking' && (
            <p className="text-sm text-gray-500">Validando arquivos…</p>
          )}

          {validationStatus === 'done' && validationErrors.length > 0 && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              <p className="font-medium mb-1">Corrija os erros abaixo antes de executar:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {validationErrors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            </div>
          )}

          {validationStatus === 'done' && validationErrors.length === 0 && (
            <p className="text-sm text-green-600">Arquivos validados com sucesso.</p>
          )}

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
            {status === 'loading' ? 'Executando…' : 'Executar'}
          </button>
        </form>
      </main>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Help section
// ---------------------------------------------------------------------------

function HelpSection() {
  const [open, setOpen] = useState(false)

  return (
    <div className="mb-8 rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors rounded-lg"
      >
        <span>Como usar</span>
        <span className="text-gray-400">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 text-sm text-gray-600 space-y-4 border-t border-gray-100 pt-4">
          <Section title="1. Acesso">
            Informe o usuário e senha fornecidos pelo administrador e clique em <strong>Entrar</strong>.
          </Section>

          <Section title="2. Preparar os arquivos">
            <p className="mb-2">Você precisará dos seguintes arquivos:</p>
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Lista de jogadores</strong> (<code>players.csv</code>) — lista de rating atual</li>
              <li><strong>Arquivo de torneios</strong> (<code>tournaments.csv</code>) — cabeçalho: <code>Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj</code></li>
              <li><strong>Arquivos binários</strong> — um por torneio, no formato <code>&lt;Ord&gt;-&lt;CrId&gt;.&lt;Tipo&gt;</code> (ex: <code>1-99999.TURX</code>)</li>
            </ul>
          </Section>

          <Section title="3. Carregar os arquivos">
            <p className="mb-2">Selecione cada arquivo no campo correspondente.</p>
            <p className="rounded bg-yellow-50 border border-yellow-200 px-3 py-2 text-yellow-800">
              ⚠️ <strong>Atenção:</strong> Informe o <strong>número do primeiro torneio</strong> a processar e a <strong>quantidade de torneios</strong>.
              Esses dois campos determinam quais torneios serão processados. Valores incorretos resultarão em processamento errado ou ausência de resultados.
            </p>
          </Section>

          <Section title="4. Validação">
            O sistema valida automaticamente os arquivos ao carregá-los. Se houver erros, eles serão listados na tela — corrija os arquivos e carregue novamente.
          </Section>

          <Section title="5. Executar o ciclo">
            Se a validação for bem-sucedida, clique em <strong>Executar</strong>. O sistema fará o download de um arquivo <code>.zip</code> com a nova lista de rating e os arquivos de auditoria de cada torneio.
          </Section>

          <Section title="6. Sair">
            Clique em <strong>Sair</strong> para encerrar a sessão.
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <p className="font-semibold text-gray-700 mb-1">{title}</p>
      <div>{children}</div>
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
