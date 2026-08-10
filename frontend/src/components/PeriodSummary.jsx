import PropTypes from 'prop-types'

const MODALITY_LABEL_PT = {
  STD: 'Clássico',
  RPD: 'Rápido',
  BLZ: 'Blitz',
}

function formatDelta(d) {
  if (d === null || d === undefined || Number.isNaN(d)) return '—'
  return d > 0 ? `+${d}` : String(d)
}

function formatRating(r) {
  return r === null || r === undefined ? 'não-rated' : String(r)
}

/** One section per modality: each has its own rating, game count and K factor. */
export default function PeriodSummary({ modalities }) {
  if (!modalities || modalities.length === 0) {
    return <p className="status-muted">Nenhum jogador teve rating alterado no período.</p>
  }

  return (
    <div className="flex flex-col gap-6">
      {modalities.map(({ modality, players, summary }) => (
        <section key={modality} className="results-outline-card px-4 py-3">
          <h3 className="portal-heading">{MODALITY_LABEL_PT[modality] ?? modality}</h3>
          <p className="t-muted">
            {summary.total} jogador(es) com rating · {summary.up} subiu(ram) ·{' '}
            {summary.down} caiu(ram) · {summary.unchanged} sem mudança
            {summary.medianAbs !== null && ` · mediana da variação absoluta ${summary.medianAbs}`}
          </p>
          <table className="w-full mt-3">
            <thead>
              <tr>
                <th className="text-left t-muted">Jogador</th>
                <th className="text-right t-muted">Antes</th>
                <th className="text-right t-muted">Depois</th>
                <th className="text-right t-muted">Variação</th>
                <th className="text-right t-muted">Partidas</th>
              </tr>
            </thead>
            <tbody>
              {players.map(p => (
                <tr key={`${p.fexerjId}-${modality}`}>
                  <td className="t-body">{p.name}</td>
                  <td className="text-right t-body">{formatRating(p.initialRating)}</td>
                  <td className="text-right t-body">{formatRating(p.finalRating)}</td>
                  <td className="text-right t-body">{formatDelta(p.delta)}</td>
                  <td className="text-right t-body">{p.games}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  )
}

PeriodSummary.propTypes = {
  modalities: PropTypes.arrayOf(
    PropTypes.shape({
      modality: PropTypes.string.isRequired,
      players: PropTypes.array.isRequired,
      summary: PropTypes.object.isRequired,
    }),
  ).isRequired,
}
