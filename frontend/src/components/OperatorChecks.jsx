import PropTypes from 'prop-types'

const MODALITY_LABEL_PT = {
  STD: 'Clássico',
  RPD: 'Rápido',
  BLZ: 'Blitz',
}

/**
 * The codes `Audit_Checks.csv` emits. An unknown code still shows: a cycle
 * that raised something the portal does not recognise is exactly the case
 * the operator must not be kept from seeing.
 */
const CHECK_PT = {
  K10_BELOW_2200: {
    title: 'Fator K de 10 em jogador abaixo de 2.200',
    why:
      'O K de 10 é o registro de que o jogador já atingiu 2.200, e é permanente. ' +
      'Isto é esperado em quem chegou lá e caiu depois — e é assim que apareceria ' +
      'um 10 digitado por engano, que congelaria o fator desse jogador.',
    detailLabel: 'Rating',
  },
  CALCULATED_WHILE_DECEASED: {
    title: 'Partidas calculadas para jogador com status de falecido',
    why:
      'O cálculo está correto: a morte pode ocorrer no meio do ciclo, com torneios ' +
      'em andamento, e essas partidas foram disputadas. O que depende de decisão é a ' +
      'publicação.',
    detailLabel: 'Partidas',
  },
}

/** Cases the cycle raised for a human to look at. Nothing here is an error. */
export default function OperatorChecks({ checks }) {
  if (!checks || checks.length === 0) return null

  const byCheck = new Map()
  for (const row of checks) {
    if (!byCheck.has(row.check)) byCheck.set(row.check, [])
    byCheck.get(row.check).push(row)
  }

  return (
    <section className="alert-amber-panel" aria-labelledby="operator-checks-heading">
      <h3 id="operator-checks-heading" className="font-semibold">
        {checks.length === 1
          ? '1 caso para conferência'
          : `${checks.length} casos para conferência`}
      </h3>
      <p className="alert-muted">
        O ciclo rodou normalmente. Os casos abaixo não são erros — são situações que o
        modelo não decide sozinho. Estão também em <code>Audit_Checks.csv</code>, no ZIP.
      </p>

      {[...byCheck.entries()].map(([code, rows]) => {
        const label = CHECK_PT[code]
        return (
          <div key={code} className="mt-3">
            <p className="font-semibold">{label ? label.title : code}</p>
            {label && <p className="alert-muted">{label.why}</p>}
            <ul className="mt-2">
              {rows.map(row => (
                <li key={`${row.playerId}-${row.timeControl}`}>
                  {row.playerName} ({row.playerId}) ·{' '}
                  {MODALITY_LABEL_PT[row.timeControl] ?? row.timeControl}
                  {row.detail !== '' &&
                    ` · ${label ? label.detailLabel : 'Detalhe'}: ${row.detail}`}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </section>
  )
}

OperatorChecks.propTypes = {
  checks: PropTypes.arrayOf(
    PropTypes.shape({
      playerId: PropTypes.string,
      playerName: PropTypes.string,
      timeControl: PropTypes.string,
      check: PropTypes.string,
      detail: PropTypes.string,
    }),
  ),
}
