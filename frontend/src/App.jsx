import { useCallback, useState } from 'react'

import { buildBasicAuthHeader } from './portalApi'
import ResultsPage from './ResultsPage'
import LoginPage from './pages/LoginPage'
import RunPage from './pages/RunPage'
import useCycleValidation from './hooks/useCycleValidation'
import useRunCycle from './hooks/useRunCycle'

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
  const [loginStatus, setLoginStatus] = useState('idle') // idle | loading | error
  const [loginError, setLoginError] = useState('')

  const clearCredentials = useCallback(() => setCredentials(null), [])

  const {
    validationErrors,
    validationRequestError,
    validationRequestId,
    validationStatus,
  } = useCycleValidation(form, credentials, {
    onAuthError: clearCredentials,
    debounceMs: import.meta.env.MODE === 'test' ? 0 : 300,
  })

  const { handleRun, status, runErrors, runRequestId, runResult, clearRunResult, abort } = useRunCycle(
    form,
    credentials,
    { onAuthError: clearCredentials },
  )

  async function handleLogin(e) {
    e.preventDefault()
    const data = new FormData(e.target)
    const creds = {
      username: data.get('username'),
      password: data.get('password'),
    }
    setLoginStatus('loading')
    setLoginError('')
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
    abort()
    clearCredentials()
    setForm(INITIAL_FORM)
    clearRunResult()
    setLoginStatus('idle')
    setLoginError('')
  }

  if (!credentials) {
    return <LoginPage onLogin={handleLogin} loginStatus={loginStatus} loginError={loginError} />
  }

  if (runResult) {
    return (
      <ResultsPage
        runResult={runResult}
        onNewRun={clearRunResult}
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
      validationRequestId={validationRequestId ?? undefined}
      validationStatus={validationStatus}
      runRequestId={runRequestId ?? undefined}
      onRun={handleRun}
      onLogout={handleLogout}
      onClearForm={() => {
        setForm(INITIAL_FORM)
        clearRunResult()
        setFormResetKey(k => k + 1)
      }}
      formResetKey={formResetKey}
    />
  )
}

