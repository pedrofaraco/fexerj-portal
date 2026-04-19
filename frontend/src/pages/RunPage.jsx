import PropTypes from 'prop-types'

import BuildStamp from '../BuildStamp'
import Field from '../components/Field'
import HelpSection from '../components/HelpSection'
import RequestIdLine from '../components/RequestIdLine'

export default function RunPage({
  form,
  setForm,
  status,
  runErrors,
  validationErrors,
  validationRequestError,
  validationRequestId,
  validationStatus,
  runRequestId,
  onRun,
  onLogout,
  onClearForm,
  formResetKey,
}) {
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
              {validationRequestId && <RequestIdLine requestId={validationRequestId} />}
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
              {runRequestId && <RequestIdLine requestId={runRequestId} />}
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
  validationRequestId: PropTypes.string,
  validationStatus: PropTypes.oneOf(['idle', 'checking', 'done', 'failed']).isRequired,
  runRequestId: PropTypes.string,
  onRun: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
  onClearForm: PropTypes.func.isRequired,
  formResetKey: PropTypes.number.isRequired,
}

