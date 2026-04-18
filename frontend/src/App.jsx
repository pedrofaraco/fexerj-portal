import { useState, useEffect, useRef } from 'react'
import PropTypes from 'prop-types'

import BuildStamp from './BuildStamp'
import { buildBasicAuthHeader, buildCycleFormData, isLatin1 } from './portalApi'
import { parseRunResult } from './resultParser'
import ResultsPage from './ResultsPage'

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
  // Bumped whenever the form is cleared so file inputs remount and
  // actually drop their selected filenames (file inputs are uncontrolled).
  const [formResetKey, setFormResetKey] = useState(0)
  const [status, setStatus] = useState('idle') // idle | loading | error
  const [runErrors, setRunErrors] = useState([])
  const [validationErrors, setValidationErrors] = useState([])
  const [validationRequestError, setValidationRequestError] = useState('')
  const [validationStatus, setValidationStatus] = useState('idle') // idle | checking | done | failed
  const [loginStatus, setLoginStatus] = useState('idle') // idle | loading | error
  const [loginError, setLoginError] = useState('')
  const [runResult, setRunResult] = useState(null)
  const runFetchAbortRef = useRef(null)

  async function handleLogin(e) {
    e.preventDefault()
    const data = new FormData(e.target)
    const creds = {
      username: data.get('username'),
      password: data.get('password'),
    }
    setLoginStatus('loading')
    setLoginError('')
    if (!isLatin1(creds.username) || !isLatin1(creds.password)) {
      setLoginStatus('error')
      setLoginError('Usuário e senha não podem conter emojis ou caracteres especiais incomuns.')
      return
    }
    try {
      const res = await fetch('/me', {
        headers: { Authorization: buildBasicAuthHeader(creds) },
      })
      if (res.status === 401) {
        setLoginStatus('error')
        setLoginError('Usuário ou senha incorretos.')
        return
      }
      setLoginStatus('idle')
      setCredentials(creds)
    } catch {
      setLoginStatus('error')
      setLoginError('Não foi possível conectar ao servidor. Verifique sua conexão.')
    }
  }

  function handleLogout() {
    runFetchAbortRef.current?.abort()
    runFetchAbortRef.current = null
    setCredentials(null)
    setForm(INITIAL_FORM)
    setRunResult(null)
    setStatus('idle')
    setRunErrors([])
    setValidationErrors([])
    setValidationRequestError('')
    setValidationStatus('idle')
    setLoginStatus('idle')
    setLoginError('')
  }

  useEffect(() => {
    if (!credentials || !form.playersCsv || !form.tournamentsCsv || form.binaryFiles.length === 0) {
      let resetCancelled = false
      queueMicrotask(() => {
        if (resetCancelled) return
        setValidationErrors([])
        setValidationRequestError('')
        setValidationStatus('idle')
      })
      return () => { resetCancelled = true }
    }

    let cancelled = false
    queueMicrotask(() => {
      if (cancelled) return
      setValidationStatus('checking')
      setValidationErrors([])
      setValidationRequestError('')
    })

    const body = buildCycleFormData(form)

    const ac = new AbortController()
    ;(async () => {
      try {
        const res = await fetch('/validate', {
          method: 'POST',
          headers: {
            Authorization: buildBasicAuthHeader(credentials),
          },
          body,
          signal: ac.signal,
        })
        if (cancelled || ac.signal.aborted) return
        if (res.status === 401) {
          setCredentials(null)
          return
        }
        if (!res.ok) {
          setValidationErrors([])
          setValidationRequestError(
            `Não foi possível validar os arquivos (resposta HTTP ${res.status}). Tente novamente.`,
          )
          setValidationStatus('failed')
          return
        }
        let data
        try {
          data = await res.json()
        } catch {
          if (cancelled || ac.signal.aborted) return
          setValidationErrors([])
          setValidationRequestError('Resposta inválida do servidor ao validar. Tente novamente.')
          setValidationStatus('failed')
          return
        }
        if (cancelled || ac.signal.aborted) return
        setValidationErrors(data.errors ?? [])
        setValidationStatus('done')
      } catch (e) {
        if (cancelled || ac.signal.aborted || e?.name === 'AbortError') return
        setValidationErrors([])
        setValidationRequestError(
          'Não foi possível conectar ao servidor para validar. Verifique sua conexão e tente novamente.',
        )
        setValidationStatus('failed')
      }
    })()

    return () => {
      cancelled = true
      ac.abort()
    }
  }, [form, credentials])

  async function handleRun(e) {
    e.preventDefault()
    runFetchAbortRef.current?.abort()
    const ac = new AbortController()
    runFetchAbortRef.current = ac
    setStatus('loading')
    setRunErrors([])

    const body = buildCycleFormData(form)
    const tournamentsCsvText = form.tournamentsCsv ? await form.tournamentsCsv.text() : ''

    try {
      const response = await fetch('/run', {
        method: 'POST',
        headers: {
          Authorization: buildBasicAuthHeader(credentials),
        },
        body,
        signal: ac.signal,
      })

      if (ac.signal.aborted) return

      if (response.status === 401) {
        setCredentials(null)
        setStatus('idle')
        return
      }

      if (!response.ok) {
        const json = await response.json().catch(() => ({}))
        const detail = json.detail
        let messages
        if (typeof detail === 'string' && detail.trim()) {
          messages = [detail]
        } else if (Array.isArray(detail) && detail.length > 0) {
          if (detail.every(x => typeof x === 'string')) {
            messages = detail
          } else if (detail.every(x => x && typeof x === 'object' && typeof x.msg === 'string')) {
            messages = detail.map(x => x.msg)
          } else {
            messages = detail.map(x => (typeof x === 'string' ? x : JSON.stringify(x)))
          }
        } else {
          messages = [`Erro inesperado (HTTP ${response.status})`]
        }
        setRunErrors(messages)
        setStatus('error')
        return
      }

      if (ac.signal.aborted) return

      const blob = await response.blob()
      if (ac.signal.aborted) return

      try {
        const parsed = await parseRunResult(blob, tournamentsCsvText)
        setRunResult({
          zipBlob: parsed.zipBlob,
          zipFilename: parsed.zipFilename,
          tournaments: parsed.tournaments,
          parseError: null,
        })
      } catch (parseErr) {
        const msg = parseErr instanceof Error ? parseErr.message : String(parseErr)
        setRunResult({
          zipBlob: blob,
          zipFilename: 'rating_cycle_output.zip',
          tournaments: [],
          parseError: msg,
        })
      }
      setStatus('idle')
    } catch (e) {
      if (e?.name === 'AbortError') return
      setRunErrors(['Não foi possível conectar ao servidor. Verifique sua conexão.'])
      setStatus('error')
    } finally {
      if (runFetchAbortRef.current === ac) runFetchAbortRef.current = null
    }
  }

  if (!credentials) {
    return <LoginPage onLogin={handleLogin} loginStatus={loginStatus} loginError={loginError} />
  }

  if (runResult) {
    return (
      <ResultsPage
        runResult={runResult}
        onNewRun={() => setRunResult(null)}
        onLogout={handleLogout}
      />
    )
  }

  return (
    <RunPage
      form={form}
      setForm={setForm}
      status={status}
      runErrors={runErrors}
      validationErrors={validationErrors}
      validationRequestError={validationRequestError}
      validationStatus={validationStatus}
      onRun={handleRun}
      onLogout={handleLogout}
      onClearForm={() => {
        setForm(INITIAL_FORM)
        setValidationErrors([])
        setValidationRequestError('')
        setValidationStatus('idle')
        setRunErrors([])
        setStatus('idle')
        setFormResetKey(k => k + 1)
      }}
      formResetKey={formResetKey}
    />
  )
}

// ---------------------------------------------------------------------------
// Login page
// ---------------------------------------------------------------------------

function LoginPage({ onLogin, loginStatus, loginError }) {
  return (
    <div className="portal-page flex flex-col">
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="surface-card surface-card--login">
          <h1 className="text-2xl font-semibold t-fg mb-1">Portal FEXERJ</h1>
          <p className="text-sm t-muted mb-6">Acesso restrito à equipe</p>

          <form onSubmit={onLogin} className="flex flex-col gap-4">
            <Field label="Usuário">
              <input name="username" type="text" required autoFocus className="input" />
            </Field>

            <Field label="Senha">
              <input name="password" type="password" required className="input" />
            </Field>

            {loginStatus === 'error' && loginError && (
              <p className="login-error">{loginError}</p>
            )}

            <button
              type="submit"
              disabled={loginStatus === 'loading'}
              className="btn-primary mt-2 w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loginStatus === 'loading' ? 'Entrando…' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
      <BuildStamp />
    </div>
  )
}

LoginPage.propTypes = {
  onLogin: PropTypes.func.isRequired,
  loginStatus: PropTypes.oneOf(['idle', 'loading', 'error']).isRequired,
  loginError: PropTypes.string.isRequired,
}

// ---------------------------------------------------------------------------
// Run page
// ---------------------------------------------------------------------------

function RunPage({ form, setForm, status, runErrors, validationErrors, validationRequestError, validationStatus, onRun, onLogout, onClearForm, formResetKey }) {
  const isReady =
    form.playersCsv &&
    form.tournamentsCsv &&
    form.binaryFiles.length > 0 &&
    Number(form.first) >= 1 &&
    Number(form.count) >= 1 &&
    validationStatus === 'done' &&
    validationErrors.length === 0

  return (
    <div className="portal-page">
      <header className="portal-header">
        <h1 className="portal-title-lg">Portal FEXERJ</h1>
        <button type="button" onClick={onLogout} className="portal-nav-btn">
          Sair
        </button>
      </header>

      <main className="max-w-xl mx-auto px-4 py-10">
        <h2 className="portal-heading">Execução do Ciclo de Rating</h2>
        <p className="portal-lede">
          Carregue os arquivos de entrada, defina o intervalo e execute o ciclo. Depois da execução,
          você verá um resumo na tela e poderá baixar o arquivo ZIP com as listas e auditorias.
        </p>

        <HelpSection />

        <form onSubmit={onRun} className="flex flex-col gap-6">
          <Field label="Lista de Jogadores" hint="players.csv — lista de rating inicial">
            <input
              key={`players-${formResetKey}`}
              type="file"
              accept=".csv"
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, playersCsv: e.target.files[0] ?? null }))}
            />
          </Field>

          <Field label="Arquivo de Torneios" hint="tournaments.csv — lista de torneios a processar">
            <input
              key={`tournaments-${formResetKey}`}
              type="file"
              accept=".csv"
              required
              className="file-input"
              onChange={e => setForm(f => ({ ...f, tournamentsCsv: e.target.files[0] ?? null }))}
            />
          </Field>

          <Field label="Arquivos Binários" hint=".TUNX / .TURX / .TUMX — um ou mais arquivos">
            <input
              key={`binaries-${formResetKey}`}
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
            <p className="status-muted">Validando arquivos…</p>
          )}

          {validationStatus === 'failed' && validationRequestError && (
            <div className="alert-error" role="alert">
              <p className="alert-title">Não foi possível validar os arquivos</p>
              <p className="m-0">{validationRequestError}</p>
            </div>
          )}

          {validationStatus === 'done' && validationErrors.length > 0 && (
            <div className="alert-error" role="alert">
              <p className="alert-title">Corrija os erros abaixo antes de executar:</p>
              <ul className="list-disc list-inside space-y-0.5 m-0 pl-0">
                {validationErrors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            </div>
          )}

          {validationStatus === 'done' && validationErrors.length === 0 && (
            <p className="alert-success">Arquivos validados com sucesso.</p>
          )}

          {status === 'error' && runErrors.length > 0 && (
            <div className="alert-error" role="alert">
              {runErrors.length === 1 ? (
                <p className="m-0">{runErrors[0]}</p>
              ) : (
                <>
                  <p className="alert-title">O servidor rejeitou a execução:</p>
                  <ul className="list-disc list-inside space-y-0.5 m-0">
                    {runErrors.map((err, i) => <li key={i}>{err}</li>)}
                  </ul>
                </>
              )}
            </div>
          )}

          <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <button
              type="submit"
              disabled={!isReady || status === 'loading'}
              className="btn-primary box-border min-h-[2.75rem] w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === 'loading' ? 'Executando…' : 'Executar'}
            </button>
            <button
              type="button"
              onClick={onClearForm}
              disabled={status === 'loading'}
              className="btn-secondary box-border min-h-[2.75rem] disabled:opacity-50 disabled:cursor-not-allowed sm:w-auto sm:min-h-0"
            >
              Limpar formulário
            </button>
          </div>
        </form>
      </main>
      <BuildStamp />
    </div>
  )
}

RunPage.propTypes = {
  form: PropTypes.shape({
    playersCsv: PropTypes.object,
    tournamentsCsv: PropTypes.object,
    binaryFiles: PropTypes.array.isRequired,
    first: PropTypes.string.isRequired,
    count: PropTypes.string.isRequired,
  }).isRequired,
  setForm: PropTypes.func.isRequired,
  status: PropTypes.oneOf(['idle', 'loading', 'error']).isRequired,
  runErrors: PropTypes.arrayOf(PropTypes.string).isRequired,
  validationErrors: PropTypes.arrayOf(PropTypes.string).isRequired,
  validationRequestError: PropTypes.string.isRequired,
  validationStatus: PropTypes.oneOf(['idle', 'checking', 'done', 'failed']).isRequired,
  onRun: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
  onClearForm: PropTypes.func.isRequired,
  formResetKey: PropTypes.number.isRequired,
}

// ---------------------------------------------------------------------------
// Help section
// ---------------------------------------------------------------------------

function HelpSection() {
  const [open, setOpen] = useState(false)
  const contentId = 'help-section-content'

  return (
    <div className="help-shell">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="help-toggle"
      >
        <span>Como usar</span>
        <span className="t-soft">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div id={contentId} className="help-body space-y-4">
          <Section title="1. Acesso">
            Informe o usuário e senha fornecidos pelo administrador e clique em <strong>Entrar</strong>.
            <p className="mt-2 text-xs t-muted">
              Observação: devido ao uso de autenticação HTTP Basic, <strong>evite emojis</strong> ou caracteres especiais incomuns na senha.
            </p>
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
            <p className="alert-warning-block">
              ⚠️ <strong>Atenção:</strong> Informe o <strong>número do primeiro torneio</strong> a processar e a <strong>quantidade de torneios</strong>.
              Esses dois campos determinam quais torneios serão processados. Valores incorretos resultarão em processamento errado ou ausência de resultados.
            </p>
          </Section>

          <Section title="4. Validação">
            O sistema valida automaticamente os arquivos ao carregá-los. Se houver erros, eles serão listados na tela — corrija os arquivos e carregue novamente.
          </Section>

          <Section title="5. Executar o ciclo">
            Se a validação for bem-sucedida, clique em <strong>Executar</strong>. Será exibido um resumo dos torneios processados;
            use <strong>Baixar ZIP</strong> na tela seguinte para obter a nova lista de rating e os arquivos de auditoria de cada torneio.
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
      <p className="section-title">{title}</p>
      <div>{children}</div>
    </div>
  )
}

Section.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
}

// ---------------------------------------------------------------------------
// Shared components
// ---------------------------------------------------------------------------

function Field({ label, hint, className = '', children }) {
  return (
    <label className={`flex flex-col gap-1.5 ${className}`}>
      <span className="field-label">{label}</span>
      {hint && <span className="field-hint">{hint}</span>}
      {children}
    </label>
  )
}

Field.propTypes = {
  label: PropTypes.string.isRequired,
  hint: PropTypes.string,
  className: PropTypes.string,
  children: PropTypes.node.isRequired,
}
