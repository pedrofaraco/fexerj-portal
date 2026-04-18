import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'

import BuildStamp from './BuildStamp'

function formatRating(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  const r = Math.round(n * 100) / 100
  if (Number.isInteger(r) || Math.abs(r - Math.round(r)) < 1e-6) return String(Math.round(r))
  return String(r)
}

function formatDelta(d) {
  if (d === null || d === undefined || Number.isNaN(d)) return '—'
  const x = Math.round(d * 100) / 100
  if (x > 0) return `+${x}`
  return String(x)
}

function formatOptionalNumber(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  const x = Math.round(n * 1000) / 1000
  return String(x)
}

export function TournamentAccordion({ tournament }) {
  const [open, setOpen] = useState(false)
  const contentId = `tournament-${tournament.ord}-players`
  const n = tournament.players?.length ?? 0

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
      >
        <span>
          {tournament.ord} — {tournament.name}{' '}
          <span className="font-normal text-gray-500">
            ({tournament.typeLabelPt}, {n} {n === 1 ? 'jogador' : 'jogadores'})
          </span>
        </span>
        <span className="text-gray-400 shrink-0 ml-2">{open ? '▼' : '▶'}</span>
      </button>
      {open && (
        <div id={contentId} className="border-t border-gray-100 px-2 pb-3 pt-1 space-y-1">
          {(tournament.players ?? []).map((p, i) => (
            <PlayerRow key={`${p.fexerjId ?? 'x'}-${i}`} player={p} index={i} />
          ))}
          {n === 0 && (
            <p className="text-sm text-gray-500 px-2 py-2">Nenhum jogador na auditoria deste torneio.</p>
          )}
        </div>
      )}
    </div>
  )
}

TournamentAccordion.propTypes = {
  tournament: PropTypes.shape({
    ord: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    typeLabelPt: PropTypes.string.isRequired,
    players: PropTypes.array,
  }).isRequired,
}

export function PlayerRow({ player, index }) {
  const [open, setOpen] = useState(false)
  const contentId = `player-detail-${index}-${player.fexerjId ?? index}`

  const summary = (
    <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className="font-medium text-gray-900 tabular-nums">{player.fexerjId ?? '—'}</span>
      <span className="text-gray-800">— {player.name || '—'}</span>
      <span className="text-gray-600 tabular-nums">
        {formatRating(player.oldRating)} → {formatRating(player.newRating)}
      </span>
      <span className="text-gray-600 tabular-nums">({formatDelta(player.delta)})</span>
      <span className="text-gray-700">{player.calcRule ?? '—'}</span>
    </span>
  )

  return (
    <div className="rounded-md border border-gray-100 bg-gray-50/80">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-100/80 transition-colors rounded-md"
      >
        <span className="flex items-start justify-between gap-2">
          {summary}
          <span className="text-gray-400 shrink-0">{open ? '▼' : '▶'}</span>
        </span>
      </button>
      {open && (
        <div
          id={contentId}
          className="px-3 pb-3 pt-0 text-sm text-gray-700 space-y-1.5 border-t border-gray-100 mt-0.5 pt-2"
        >
          <DetailLine label="Jogos anteriores" value={formatOptionalNumber(player.gamesBefore)} />
          <DetailLine label="Jogos válidos neste torneio" value={formatOptionalNumber(player.validGames)} />
          <DetailLine label="Rating médio dos adversários" value={formatOptionalNumber(player.avgOpponRating)} />
          <DetailLine label="Soma dos ratings dos adversários" value={formatOptionalNumber(player.erm)} />
          <DetailLine label="Diferença (Ro − média adversários)" value={formatOptionalNumber(player.dif)} />
          <DetailLine label="Pontos obtidos" value={formatOptionalNumber(player.pointsScored)} />
          <DetailLine label="Pontos esperados" value={formatOptionalNumber(player.expectedPoints)} />
          <DetailLine label="Diferença (obtido − esperado)" value={formatOptionalNumber(player.pointsAboveExpected)} />
          <DetailLine label="Pontos esperados por partida (We)" value={formatOptionalNumber(player.we)} />
          <DetailLine label="K" value={formatOptionalNumber(player.k)} />
          <DetailLine label="K × diferença (obtido − esperado)" value={formatOptionalNumber(player.kDw)} />
          <DetailLine label="Total de jogos após o torneio" value={formatOptionalNumber(player.newTotalGames)} />
          <DetailLine label="Pontos por partida (P)" value={formatOptionalNumber(player.pRatio)} />
          <DetailLine label="Número no torneio (Chess Results)" value={formatOptionalNumber(player.boardNo)} />
        </div>
      )}
    </div>
  )
}

PlayerRow.propTypes = {
  player: PropTypes.object.isRequired,
  index: PropTypes.number.isRequired,
}

function DetailLine({ label, value }) {
  return (
    <p>
      <span className="text-gray-500">{label}: </span>
      <span className="tabular-nums text-gray-900">{value}</span>
    </p>
  )
}

DetailLine.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
}

export default function ResultsPage({ runResult, onNewRun, onLogout }) {
  const [blobUrl, setBlobUrl] = useState('')

  useEffect(() => {
    const blob = runResult?.zipBlob
    if (!blob) return undefined
    const url = URL.createObjectURL(blob)
    // Pair object URL with zipBlob for the download button; revoke on cleanup / dependency change.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- URL is external; state mirrors it for render
    setBlobUrl(url)
    return () => {
      URL.revokeObjectURL(url)
    }
  }, [runResult?.zipBlob])

  const { zipFilename, tournaments, parseError } = runResult

  function handleDownloadClick() {
    if (!blobUrl) return
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = zipFilename
    a.click()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">Portal FEXERJ</h1>
        <button
          type="button"
          onClick={onLogout}
          className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          Sair
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Resultado do Ciclo de Rating</h2>

        <div className="flex flex-wrap gap-3 mb-6">
          <button
            type="button"
            onClick={handleDownloadClick}
            disabled={!blobUrl}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 active:bg-blue-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Baixar ZIP
          </button>
          <button
            type="button"
            onClick={onNewRun}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 active:bg-gray-100 transition-colors"
          >
            Nova execução
          </button>
        </div>

        {parseError && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900 mb-6">
            <p className="font-medium mb-1">Não foi possível exibir o resumo na tela.</p>
            <p>{parseError}</p>
            <p className="mt-2 text-amber-800">Use <strong>Baixar ZIP</strong> para obter os arquivos gerados.</p>
          </div>
        )}

        {!parseError && (
          <div className="space-y-3">
            {(tournaments ?? []).map(t => (
              <TournamentAccordion key={t.ord} tournament={t} />
            ))}
          </div>
        )}
      </main>
      <BuildStamp />
    </div>
  )
}

ResultsPage.propTypes = {
  runResult: PropTypes.shape({
    zipBlob: PropTypes.object.isRequired,
    zipFilename: PropTypes.string.isRequired,
    tournaments: PropTypes.array,
    parseError: PropTypes.string,
  }).isRequired,
  onNewRun: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
}
