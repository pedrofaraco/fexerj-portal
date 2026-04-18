import { useEffect, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'

import BuildStamp from './BuildStamp'
import { buildPlayerIndex } from './resultParser'
import { filterPlayersForSearch, filterTournamentsForSearch } from './searchUtils'

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

/** Audited player row — same shape as `mapAuditRowToPlayer` output (plus optional tournament meta keys). */
export function CalculationGrid({ player }) {
  return (
    <div className="text-sm text-gray-700 space-y-1.5 border-t border-gray-100 mt-0.5 pt-2 px-3 pb-3">
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
  )
}

CalculationGrid.propTypes = {
  player: PropTypes.object.isRequired,
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
        className="accordion-row-btn w-full flex items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-800 transition-colors"
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
    <div className="results-accordion-card rounded-md border border-gray-100">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="accordion-row-btn accordion-row-btn--nested w-full text-left px-3 py-2.5 text-sm transition-colors rounded-md"
      >
        <span className="flex items-start justify-between gap-2">
          {summary}
          <span className="text-gray-400 shrink-0">{open ? '▼' : '▶'}</span>
        </span>
      </button>
      {open && (
        <div id={contentId}>
          <CalculationGrid player={player} />
        </div>
      )}
    </div>
  )
}

PlayerRow.propTypes = {
  player: PropTypes.object.isRequired,
  index: PropTypes.number.isRequired,
}

/** One tournament appearance for a player (audit row + tournament meta from `buildPlayerIndex`). */
export function TournamentDetailRow({ round, rowIndex }) {
  const [open, setOpen] = useState(false)
  const contentId = `tournament-detail-${round.ord}-${rowIndex}-${round.fexerjId ?? rowIndex}`

  const summary = (
    <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className="font-medium text-gray-900 tabular-nums">{round.ord}</span>
      <span className="text-gray-800">— {round.tournamentName || '—'}</span>
      <span className="text-gray-600 tabular-nums">
        {formatRating(round.oldRating)} → {formatRating(round.newRating)}
      </span>
      <span className="text-gray-600 tabular-nums">({formatDelta(round.delta)})</span>
      <span className="text-gray-700">{round.calcRule ?? '—'}</span>
    </span>
  )

  return (
    <div className="results-accordion-card rounded-md border border-gray-100">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="accordion-row-btn accordion-row-btn--nested w-full text-left px-3 py-2.5 text-sm transition-colors rounded-md"
      >
        <span className="flex items-start justify-between gap-2">
          {summary}
          <span className="text-gray-400 shrink-0">{open ? '▼' : '▶'}</span>
        </span>
      </button>
      {open && (
        <div id={contentId}>
          <CalculationGrid player={round} />
        </div>
      )}
    </div>
  )
}

TournamentDetailRow.propTypes = {
  round: PropTypes.object.isRequired,
  rowIndex: PropTypes.number.isRequired,
}

/** Grouped player row with nested tournaments (Por jogador tab). */
export function PlayerAccordion({ player }) {
  const [open, setOpen] = useState(false)
  const contentId = `player-group-${player.groupKey}`
  const nTor = player.tournaments?.length ?? 0

  const summary = (
    <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className="font-medium text-gray-900 tabular-nums">{player.fexerjId ?? '—'}</span>
      <span className="text-gray-800">— {player.name || '—'}</span>
      <span className="text-gray-600 tabular-nums">
        {formatRating(player.initialRating)} → {formatRating(player.finalRating)}
      </span>
      <span className="text-gray-600 tabular-nums">({formatDelta(player.netDelta)})</span>
      <span className="text-gray-500">
        {nTor} {nTor === 1 ? 'torneio' : 'torneios'}
      </span>
    </span>
  )

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="accordion-row-btn w-full flex items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-800 transition-colors"
      >
        <span className="min-w-0">{summary}</span>
        <span className="text-gray-400 shrink-0 ml-2">{open ? '▼' : '▶'}</span>
      </button>
      {open && (
        <div id={contentId} className="border-t border-gray-100 px-2 pb-3 pt-1 space-y-1">
          {(player.tournaments ?? []).map((r, i) => (
            <TournamentDetailRow key={`${r.ord}-${i}`} round={r} rowIndex={i} />
          ))}
        </div>
      )}
    </div>
  )
}

PlayerAccordion.propTypes = {
  player: PropTypes.shape({
    groupKey: PropTypes.string.isRequired,
    fexerjId: PropTypes.number,
    name: PropTypes.string.isRequired,
    initialRating: PropTypes.number,
    finalRating: PropTypes.number,
    netDelta: PropTypes.number,
    tournaments: PropTypes.array.isRequired,
  }).isRequired,
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

const TAB_IDS = ['tab-results-tournament', 'tab-results-player']
const RESULTS_FILTER_INPUT_ID = 'results-filter-q'

export default function ResultsPage({ runResult, onNewRun, onLogout }) {
  const [blobUrl, setBlobUrl] = useState('')
  const [activeTab, setActiveTab] = useState('tournament')
  const [resultsFilter, setResultsFilter] = useState('')
  const tabRefs = useRef([null, null])

  const playersByPlayer = useMemo(
    () => buildPlayerIndex(runResult.tournaments ?? []),
    [runResult.tournaments],
  )

  const filteredTournaments = useMemo(
    () => filterTournamentsForSearch(runResult.tournaments ?? [], resultsFilter),
    [runResult.tournaments, resultsFilter],
  )

  const filteredPlayers = useMemo(
    () => filterPlayersForSearch(playersByPlayer, resultsFilter),
    [playersByPlayer, resultsFilter],
  )

  const filterHasTerm = resultsFilter.trim().length > 0

  useEffect(() => {
    const blob = runResult?.zipBlob
    if (!blob) return undefined
    const url = URL.createObjectURL(blob)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- URL is external; state mirrors it for render
    setBlobUrl(url)
    return () => {
      URL.revokeObjectURL(url)
    }
  }, [runResult?.zipBlob])

  const { zipFilename, parseError } = runResult

  function handleDownloadClick() {
    if (!blobUrl) return
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = zipFilename
    a.click()
  }

  function focusTab(nextIndex) {
    const clamped = ((nextIndex % 2) + 2) % 2
    setActiveTab(clamped === 0 ? 'tournament' : 'player')
    window.requestAnimationFrame(() => {
      tabRefs.current[clamped]?.focus()
    })
  }

  function handleTabKeyDown(event, tabIndex) {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      focusTab(tabIndex + 1)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      focusTab(tabIndex - 1)
    } else if (event.key === 'Home') {
      event.preventDefault()
      focusTab(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      focusTab(1)
    }
  }

  const tabIndexForActive = activeTab === 'tournament' ? 0 : 1

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
            className="btn-primary w-full sm:w-auto"
          >
            Baixar ZIP
          </button>
          <button
            type="button"
            onClick={onNewRun}
            className="btn-secondary"
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
          <>
            <div
              className="flex flex-wrap gap-2 mb-4"
              role="tablist"
              aria-label="Visualização dos resultados"
            >
              <button
                ref={el => {
                  tabRefs.current[0] = el
                }}
                type="button"
                id={TAB_IDS[0]}
                role="tab"
                aria-selected={activeTab === 'tournament'}
                aria-controls="panel-results-tournament"
                tabIndex={tabIndexForActive === 0 ? 0 : -1}
                className="results-tab"
                onClick={() => {
                  setActiveTab('tournament')
                  tabRefs.current[0]?.focus()
                }}
                onKeyDown={e => handleTabKeyDown(e, 0)}
              >
                Por torneio
              </button>
              <button
                ref={el => {
                  tabRefs.current[1] = el
                }}
                type="button"
                id={TAB_IDS[1]}
                role="tab"
                aria-selected={activeTab === 'player'}
                aria-controls="panel-results-player"
                tabIndex={tabIndexForActive === 1 ? 0 : -1}
                className="results-tab"
                onClick={() => {
                  setActiveTab('player')
                  tabRefs.current[1]?.focus()
                }}
                onKeyDown={e => handleTabKeyDown(e, 1)}
              >
                Por jogador
              </button>
            </div>

            <div className="mb-4">
              <label
                htmlFor={RESULTS_FILTER_INPUT_ID}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Filtrar por nome ou ID
              </label>
              <input
                id={RESULTS_FILTER_INPUT_ID}
                type="search"
                className="input"
                value={resultsFilter}
                onChange={e => setResultsFilter(e.target.value)}
                autoComplete="off"
              />
            </div>

            <div
              id="panel-results-tournament"
              role="tabpanel"
              aria-labelledby={TAB_IDS[0]}
              hidden={activeTab !== 'tournament'}
              className="space-y-3"
            >
              {filterHasTerm && filteredTournaments.length === 0 ? (
                <p className="text-sm text-gray-600 py-2">Nenhum resultado encontrado.</p>
              ) : (
                filteredTournaments.map(t => <TournamentAccordion key={t.ord} tournament={t} />)
              )}
            </div>

            <div
              id="panel-results-player"
              role="tabpanel"
              aria-labelledby={TAB_IDS[1]}
              hidden={activeTab !== 'player'}
              className="space-y-3"
            >
              {filterHasTerm && filteredPlayers.length === 0 ? (
                <p className="text-sm text-gray-600 py-2">Nenhum resultado encontrado.</p>
              ) : (
                filteredPlayers.map(p => <PlayerAccordion key={p.groupKey} player={p} />)
              )}
            </div>
          </>
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
