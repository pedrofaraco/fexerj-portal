import PropTypes from 'prop-types'

function formatDelta(d) {
  if (d === null || d === undefined || Number.isNaN(d)) return '—'
  return d > 0 ? `+${d}` : String(d)
}

export default function ComparisonSummary({ comparison }) {
  const { players, summary } = comparison

  return (
    <section className="flex flex-col gap-4">
      <div className="alert-warning-block">
        <p className="m-0">
          O modelo novo produz ratings diferentes com histórico idêntico, e isso é o objetivo. O
          comparativo existe para dimensionar a diferença, não para minimizá-la.
        </p>
      </div>

      <p className="t-muted">
        {summary.total} jogadores · {summary.up} subiu(ram) · {summary.down} caiu(ram) ·{' '}
        {summary.unchanged} sem mudança
        {summary.maxUp !== null && ` · maior alta ${formatDelta(summary.maxUp)}`}
        {summary.maxDown !== null && ` · maior queda ${formatDelta(summary.maxDown)}`}
        {summary.medianAbs !== null && ` · mediana da diferença absoluta ${summary.medianAbs}`}
      </p>

      <table className="w-full">
        <thead>
          <tr>
            <th className="text-left t-muted">Jogador</th>
            <th className="text-right t-muted">Modelo atual</th>
            <th className="text-right t-muted">Modelo FIDE</th>
            <th className="text-right t-muted">Diferença</th>
          </tr>
        </thead>
        <tbody>
          {players.map(p => (
            <tr key={p.fexerjId}>
              <td className="t-body">{p.name}</td>
              <td className="text-right t-body">{p.ratingCurrent ?? '—'}</td>
              <td className="text-right t-body">{p.ratingFide ?? '—'}</td>
              <td className="text-right t-body">{formatDelta(p.difference)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

ComparisonSummary.propTypes = {
  comparison: PropTypes.shape({
    players: PropTypes.array.isRequired,
    summary: PropTypes.object.isRequired,
  }).isRequired,
}
