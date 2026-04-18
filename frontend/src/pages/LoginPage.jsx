import PropTypes from 'prop-types'

import BuildStamp from '../BuildStamp'
import Field from '../components/Field'

export default function LoginPage({ onLogin, loginStatus, loginError }) {
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

