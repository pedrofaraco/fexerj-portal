# Migração do modelo de rating — portal (plano 2 de 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expor os três modos de execução no portal, ler as saídas novas e mostrar o comparativo que a federação usa para comunicar a mudança.

**Architecture:** O formulário ganha um seletor de modo que acompanha `/validate` e `/run`. O `resultParser` passa a despachar pela forma da saída — hoje ele assume auditoria por torneio, que deixa de existir no modelo novo. A tela de resultado ganha um resumo por modo, sem mexer no que já existe para o modelo atual.

**Tech Stack:** React 19, Vite, Vitest, Testing Library, JSZip.

**Depende de:** [`2026-08-09-migracao-modelo-rating-motor.md`](2026-08-09-migracao-modelo-rating-motor.md) — a API precisa aceitar `mode` antes deste plano começar.

**Spec:** [`docs/superpowers/specs/2026-08-09-migracao-modelo-rating-design.md`](../specs/2026-08-09-migracao-modelo-rating-design.md) §5

## Global Constraints

- **Chrome 109 no Windows 7 é o piso de suporte.** O Tailwind v4 emite `oklch()` e `color-mix()`, que o Chrome 109 ignora. Toda cor vem das classes nomeadas de `frontend/src/index.css` (`.t-fg`, `.t-body`, `.t-muted`, `.btn-primary`, `.input`, `.alert-error`, …). **Nunca** usar utilitário de cor do Tailwind no JSX (`text-gray-700`, `bg-blue-600`). Utilitários de espaçamento e layout (`flex`, `gap-4`, `px-4`) são seguros.
- **O código é todo em inglês** — identificadores, comentários, nomes de teste e de componente. **A exceção é o texto que o operador lê na tela**, que segue em português, como já acontece hoje.
- **Os blocos de código deste plano têm comentários e nomes de teste em português.** Isso é um erro de redação do plano, não uma instrução: ao implementar, escreva-os em inglês. O **texto de interface** dos blocos (rótulos, ajuda, mensagens) é para copiar verbatim em português.
- **Nomes de jogadores em teste são placeholders genéricos.**
- **Rodar os testes:** `cd frontend && npx vitest run`
- **Lint:** `cd frontend && npm run lint`
- **O padrão do seletor é o modelo atual, e ele não é lembrado entre sessões.** Uma seleção esquecida é o modo de falha que interessa evitar.

---

## Task 1: Seletor de modo no formulário

**Files:**
- Modify: `frontend/src/App.jsx:10-15` (`INITIAL_FORM`)
- Modify: `frontend/src/portalApi.js:12-20` (`buildCycleFormData`)
- Modify: `frontend/src/pages/RunPage.jsx` (campo novo + propTypes)
- Test: `frontend/src/pages/RunPage.test.jsx` (criar), `frontend/src/portalApi.test.js` (criar)

**Interfaces:**
- Consumes: nada de tasks anteriores
- Produces: `form.mode` com valores `'legacy' | 'fide' | 'compare'`, enviado como campo `mode` no multipart

- [ ] **Step 1: Escrever o teste do `portalApi`**

```javascript
import { describe, expect, it } from 'vitest'

import { buildCycleFormData } from './portalApi'

function makeForm(overrides = {}) {
  return {
    playersCsv: new File(['a'], 'players.csv'),
    tournamentsCsv: new File(['b'], 'tournaments.csv'),
    binaryFiles: [new File(['c'], '1-99999.TURX')],
    first: '1',
    count: '1',
    mode: 'legacy',
    ...overrides,
  }
}

describe('buildCycleFormData', () => {
  it('envia o modo escolhido', () => {
    const body = buildCycleFormData(makeForm({ mode: 'fide' }))
    expect(body.get('mode')).toBe('fide')
  })

  it('usa o modelo atual quando o modo não foi definido', () => {
    const form = makeForm()
    delete form.mode
    const body = buildCycleFormData(form)
    expect(body.get('mode')).toBe('legacy')
  })

  it('mantém os campos que já existiam', () => {
    const body = buildCycleFormData(makeForm())
    expect(body.get('first')).toBe('1')
    expect(body.get('count')).toBe('1')
    expect(body.get('players_csv')).toBeInstanceOf(File)
  })
})
```

- [ ] **Step 2: Escrever o teste do `RunPage`**

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import RunPage from './RunPage'

function renderRunPage(overrides = {}) {
  const setForm = vi.fn()
  const props = {
    form: {
      playersCsv: null,
      tournamentsCsv: null,
      binaryFiles: [],
      first: '1',
      count: '1',
      mode: 'legacy',
    },
    setForm,
    status: 'idle',
    runErrors: [],
    playersCsvErrors: [],
    tournamentsCsvErrors: [],
    playersCsvStatus: 'idle',
    tournamentsCsvStatus: 'idle',
    csvFilesValid: false,
    csvFilesChecking: false,
    validationErrors: [],
    validationRequestError: '',
    validationStatus: 'idle',
    onRun: vi.fn(),
    onLogout: vi.fn(),
    onClearForm: vi.fn(),
    formResetKey: 0,
    ...overrides,
  }
  render(<RunPage {...props} />)
  return { setForm }
}

describe('seletor de modelo', () => {
  it('começa no modelo atual', () => {
    renderRunPage()
    expect(screen.getByLabelText(/modelo de cálculo/i)).toHaveValue('legacy')
  })

  it('oferece os três modos', () => {
    renderRunPage()
    const options = screen.getAllByRole('option').map(o => o.value)
    expect(options).toEqual(['legacy', 'fide', 'compare'])
  })

  it('marca o modelo atual como o oficial', () => {
    renderRunPage()
    expect(screen.getByRole('option', { name: /oficial/i })).toHaveValue('legacy')
  })

  it('propaga a escolha para o formulário', async () => {
    const { setForm } = renderRunPage()
    await userEvent.selectOptions(screen.getByLabelText(/modelo de cálculo/i), 'fide')
    expect(setForm).toHaveBeenCalled()
  })

  it('avisa que o intervalo é o período no modelo FIDE', () => {
    renderRunPage({
      form: {
        playersCsv: null, tournamentsCsv: null, binaryFiles: [],
        first: '1', count: '1', mode: 'fide',
      },
    })
    expect(screen.getByText(/o intervalo selecionado é o período de cálculo/i)).toBeInTheDocument()
  })

  it('não mostra esse aviso no modelo atual', () => {
    renderRunPage()
    expect(screen.queryByText(/o intervalo selecionado é o período de cálculo/i)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `cd frontend && npx vitest run src/portalApi.test.js src/pages/RunPage.test.jsx`
Expected: FAIL — `body.get('mode')` devolve `null` e o `<select>` não existe

- [ ] **Step 4: Implementar**

Em `frontend/src/portalApi.js`, dentro de `buildCycleFormData`, antes do `return`:

```javascript
  body.append('mode', form.mode ?? 'legacy')
```

Em `frontend/src/App.jsx`, acrescentar a `INITIAL_FORM`:

```javascript
const INITIAL_FORM = {
  playersCsv: null,
  tournamentsCsv: null,
  binaryFiles: [],
  first: '1',
  count: '1',
  // O modo não é lembrado entre sessões: uma seleção esquecida seria o pior
  // modo de falha, já que muda qual motor gera o rating.
  mode: 'legacy',
}
```

Em `frontend/src/pages/RunPage.jsx`, acrescentar o campo logo depois de `<HelpSection />` e antes do primeiro `<Field>` de arquivo — antes dos uploads porque o modo decide quais regras de validação valem:

```jsx
          <Field
            label="Modelo de cálculo"
            hint="O modelo atual é o oficial. Os demais são para avaliação."
          >
            <select
              id="mode"
              value={form.mode}
              onChange={e => setForm(f => ({ ...f, mode: e.target.value }))}
              className="input"
            >
              <option value="legacy">Modelo atual (oficial)</option>
              <option value="fide">Modelo FIDE (por partida)</option>
              <option value="compare">Comparar os dois</option>
            </select>
          </Field>
```

`Field` precisa associar o rótulo ao controle. Se ele ainda não faz isso, passe `htmlFor` — confira `frontend/src/components/Field.jsx` e, se necessário, acrescente o atributo ao `<label>` com o mesmo `id` do `<select>`.

Logo abaixo dos campos "Primeiro torneio" e "Quantidade", acrescentar o aviso de período:

```jsx
          {form.mode !== 'legacy' && (
            <p className="field-hint">
              O intervalo selecionado é o período de cálculo: todas as partidas usam o rating do
              início do período e o rating é arredondado uma única vez, no fim. Rodar cinco
              torneios de uma vez e rodar cinco vezes um torneio dão resultados diferentes.
            </p>
          )}
```

Acrescentar `mode` ao `propTypes.form`:

```javascript
    mode: PropTypes.oneOf(['legacy', 'fide', 'compare']).isRequired,
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd frontend && npx vitest run src/portalApi.test.js src/pages/RunPage.test.jsx && npm run lint`
Expected: PASS, lint limpo

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/portalApi.js frontend/src/pages/RunPage.jsx \
        frontend/src/pages/RunPage.test.jsx frontend/src/portalApi.test.js frontend/src/components/Field.jsx
git commit -m "feat(portal): seletor de modelo de cálculo no formulário"
```

---

## Task 2: Ler as saídas do modelo novo

O `resultParser` de hoje exige `Audit_of_Tournament_<n>.csv` e joga erro quando não acha. No modelo novo esse arquivo não existe.

**Files:**
- Modify: `frontend/src/resultParser.js`
- Test: `frontend/src/resultParser.fide.test.js` (criar)

**Interfaces:**
- Consumes: os arquivos gerados pelas Tasks 13 e 14 do plano do motor
- Produces:
  - `FIDE_PERIOD_PREAMBLE`, `FIDE_GAMES_PREAMBLE`, `COMPARISON_PREAMBLE`
  - `parseFidePeriodAudit(text) -> rows[]`
  - `parseComparisonCsv(text) -> rows[]`
  - `summarizeDeltas(deltas) -> { total, up, down, unchanged, maxUp, maxDown, medianAbs }`
  - `parseRunResult(...)` passa a devolver `{ kind: 'legacy' | 'fide' | 'compare', ... }`

- [ ] **Step 1: Escrever o teste**

```javascript
import JSZip from 'jszip'
import { describe, expect, it } from 'vitest'

import {
  COMPARISON_PREAMBLE,
  FIDE_PERIOD_PREAMBLE,
  parseComparisonCsv,
  parseFidePeriodAudit,
  parseRunResult,
  summarizeDeltas,
} from './resultParser'

const PERIOD_CSV =
  `${FIDE_PERIOD_PREAMBLE}\n` +
  'Tournaments;PlayerId;PlayerName;TimeControl;InitialRating;Games;SumDeltaR;Variation;RoundedVariation;FinalRating;Path\n' +
  '1;3741;Carlos Mendes;STD;1800;5;0.36;7.2;7;1807;RATED\n' +
  '1;643;Roberto Faria;STD;1900;5;-0.20;-4.0;-4;1896;RATED\n' +
  '1;5400;Bruno Teixeira;RPD;;3;0;0;0;;ACUMULANDO\n'

const COMPARISON_CSV =
  `${COMPARISON_PREAMBLE}\n` +
  'PlayerId;PlayerName;RatingCurrent;RatingFide;Difference\n' +
  '3741;Carlos Mendes;1810;1807;-3\n' +
  '643;Roberto Faria;1893;1896;3\n' +
  '1979;Andre Nunes;1700;1700;0\n'

async function zipOf(files) {
  const zip = new JSZip()
  for (const [name, content] of Object.entries(files)) zip.file(name, content)
  return zip.generateAsync({ type: 'blob' })
}

describe('parseFidePeriodAudit', () => {
  it('lê uma linha por jogador e modalidade', () => {
    expect(parseFidePeriodAudit(PERIOD_CSV)).toHaveLength(3)
  })

  it('separa as modalidades', () => {
    const rows = parseFidePeriodAudit(PERIOD_CSV)
    expect(rows.filter(r => r.modality === 'STD')).toHaveLength(2)
    expect(rows.filter(r => r.modality === 'RPD')).toHaveLength(1)
  })

  it('trata rating vazio como não-rated', () => {
    const row = parseFidePeriodAudit(PERIOD_CSV).find(r => r.modality === 'RPD')
    expect(row.initialRating).toBeNull()
    expect(row.finalRating).toBeNull()
  })

  it('rejeita preâmbulo desconhecido', () => {
    expect(() => parseFidePeriodAudit('# outra_coisa\nA;B\n1;2\n')).toThrow(/não reconhecid/i)
  })
})

describe('parseComparisonCsv', () => {
  it('lê a diferença entre os modelos', () => {
    const rows = parseComparisonCsv(COMPARISON_CSV)
    expect(rows.map(r => r.difference)).toEqual([-3, 3, 0])
  })
})

describe('summarizeDeltas', () => {
  it('conta subidas, quedas e empates', () => {
    const s = summarizeDeltas([-3, 3, 0, 5])
    expect(s.total).toBe(4)
    expect(s.up).toBe(2)
    expect(s.down).toBe(1)
    expect(s.unchanged).toBe(1)
  })

  it('acha os extremos', () => {
    const s = summarizeDeltas([-3, 3, 0, 5])
    expect(s.maxUp).toBe(5)
    expect(s.maxDown).toBe(-3)
  })

  it('calcula a mediana da variação absoluta', () => {
    expect(summarizeDeltas([-3, 3, 0, 5]).medianAbs).toBe(3)
    expect(summarizeDeltas([1, 3]).medianAbs).toBe(2)
  })

  it('aguenta lista vazia', () => {
    const s = summarizeDeltas([])
    expect(s.total).toBe(0)
    expect(s.medianAbs).toBeNull()
  })
})

describe('parseRunResult despacha pela forma da saída', () => {
  it('reconhece a saída do modelo FIDE', async () => {
    const blob = await zipOf({
      'RatingList.csv': 'x',
      'Audit_Period.csv': PERIOD_CSV,
      'Audit_Games.csv': '# fide_games_v1\nA\n',
    })
    const result = await parseRunResult(blob, '', '')
    expect(result.kind).toBe('fide')
    expect(result.zipFilename).toBe('rating_cycle_fide.zip')
    expect(result.modalities.map(m => m.modality)).toEqual(['STD', 'RPD'])
  })

  it('resume cada modalidade separadamente', async () => {
    const blob = await zipOf({
      'RatingList.csv': 'x',
      'Audit_Period.csv': PERIOD_CSV,
      'Audit_Games.csv': '# fide_games_v1\nA\n',
    })
    const result = await parseRunResult(blob, '', '')
    const std = result.modalities.find(m => m.modality === 'STD')
    expect(std.summary.total).toBe(2)
    expect(std.summary.up).toBe(1)
    expect(std.summary.down).toBe(1)
  })

  it('reconhece a saída do modo comparar', async () => {
    const blob = await zipOf({
      'Comparison.csv': COMPARISON_CSV,
      'RatingList.csv': 'x',
      'RatingList_after_1.csv': 'y',
      'Audit_Period.csv': PERIOD_CSV,
      'Audit_Games.csv': '# fide_games_v1\nA\n',
    })
    const result = await parseRunResult(blob, '', '')
    expect(result.kind).toBe('compare')
    expect(result.zipFilename).toBe('rating_cycle_comparison.zip')
    expect(result.comparison.summary.total).toBe(3)
  })

  it('segue lendo a saída do modelo atual', async () => {
    const legacyAudit =
      '# audit_v1\n' +
      'Id_Fexerj;Name;No;Ro;Ind;K;PG;N;Erm;Rm;Dif;We;Nwe;Dw;kDw;Rn;Nind;P;Calc_Rule\n' +
      '3741;Carlos Mendes;1;1800;50;25;3;5;8500;1700;100;0.5;2.5;0.5;12.5;1813;55;0.6;NORMAL\n'
    const blob = await zipOf({
      'RatingList_after_1.csv': 'x',
      'Audit_of_Tournament_1.csv': legacyAudit,
    })
    const result = await parseRunResult(blob, '', '')
    expect(result.kind).toBe('legacy')
    expect(result.tournaments).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npx vitest run src/resultParser.fide.test.js`
Expected: FAIL com `SyntaxError` de export inexistente (`FIDE_PERIOD_PREAMBLE`)

- [ ] **Step 3: Implementar**

Em `frontend/src/resultParser.js`, acrescentar depois das constantes existentes:

```javascript
/** Must match `calculator/fide/audit.py` `PERIOD_AUDIT_PREAMBLE` */
export const FIDE_PERIOD_PREAMBLE = '# fide_period_v1'

/** Must match `calculator/fide/audit.py` `GAMES_AUDIT_PREAMBLE` */
export const FIDE_GAMES_PREAMBLE = '# fide_games_v1'

/** Must match `calculator/compare.py` `COMPARISON_PREAMBLE` */
export const COMPARISON_PREAMBLE = '# fide_comparison_v1'

const ZIP_NAME_BY_KIND = {
  legacy: 'rating_cycle_output.zip',
  fide: 'rating_cycle_fide.zip',
  compare: 'rating_cycle_comparison.zip',
}

function splitPreambleAndBody(text, expectedPreamble) {
  const lines = stripUtf8Bom(text)
    .split(/\r?\n/)
    .map(l => l.trimEnd())
    .filter(line => line.length > 0)
  const actual = lines[0] ?? ''
  if (actual !== expectedPreamble) {
    const shown = actual.length > 80 ? `${actual.slice(0, 80)}…` : actual
    throw new Error(
      `Versão de arquivo não reconhecida. Esperado "${expectedPreamble}"; encontrado "${shown}".\n` +
        'O ZIP pode ser baixado normalmente; o resumo na tela não está disponível.',
    )
  }
  return parseSemicolonCsv(lines.slice(1).join('\n'))
}

function cellsByHeader(headers, row) {
  const out = {}
  headers.forEach((h, i) => { out[h.trim()] = row[i] })
  return out
}

/** @param {string} text conteúdo de Audit_Period.csv */
export function parseFidePeriodAudit(text) {
  const { headers, rows } = splitPreambleAndBody(text, FIDE_PERIOD_PREAMBLE)
  return rows
    .filter(row => !row.every(c => c === '' || c === undefined))
    .map(row => {
      const c = cellsByHeader(headers, row)
      const initialRating = parseNumericCell(c.InitialRating)
      const finalRating = parseNumericCell(c.FinalRating)
      return {
        tournaments: (c.Tournaments ?? '').trim(),
        fexerjId: parseIntCell(c.PlayerId),
        name: c.PlayerName ?? '',
        modality: (c.TimeControl ?? '').trim(),
        initialRating,
        games: parseIntCell(c.Games),
        sumDelta: parseNumericCell(c.SumDeltaR),
        variation: parseNumericCell(c.Variation),
        roundedVariation: parseIntCell(c.RoundedVariation),
        finalRating,
        delta:
          initialRating !== null && finalRating !== null ? finalRating - initialRating : null,
        path: (c.Path ?? '').trim(),
      }
    })
}

/** @param {string} text conteúdo de Comparison.csv */
export function parseComparisonCsv(text) {
  const { headers, rows } = splitPreambleAndBody(text, COMPARISON_PREAMBLE)
  return rows
    .filter(row => !row.every(c => c === '' || c === undefined))
    .map(row => {
      const c = cellsByHeader(headers, row)
      return {
        fexerjId: parseIntCell(c.PlayerId),
        name: c.PlayerName ?? '',
        ratingCurrent: parseNumericCell(c.RatingCurrent),
        ratingFide: parseNumericCell(c.RatingFide),
        difference: parseNumericCell(c.Difference) ?? 0,
      }
    })
}

/**
 * Estatísticas de variação para o resumo na tela.
 * @param {number[]} deltas
 */
export function summarizeDeltas(deltas) {
  const values = deltas.filter(d => d !== null && d !== undefined && !Number.isNaN(d))
  if (values.length === 0) {
    return { total: 0, up: 0, down: 0, unchanged: 0, maxUp: null, maxDown: null, medianAbs: null }
  }
  const sortedAbs = values.map(Math.abs).sort((a, b) => a - b)
  const mid = Math.floor(sortedAbs.length / 2)
  const medianAbs =
    sortedAbs.length % 2 === 1 ? sortedAbs[mid] : (sortedAbs[mid - 1] + sortedAbs[mid]) / 2
  return {
    total: values.length,
    up: values.filter(d => d > 0).length,
    down: values.filter(d => d < 0).length,
    unchanged: values.filter(d => d === 0).length,
    maxUp: Math.max(...values),
    maxDown: Math.min(...values),
    medianAbs,
  }
}

function groupByModality(periodRows) {
  const byModality = new Map()
  for (const row of periodRows) {
    if (!byModality.has(row.modality)) byModality.set(row.modality, [])
    byModality.get(row.modality).push(row)
  }
  return [...byModality.entries()].map(([modality, players]) => ({
    modality,
    players,
    summary: summarizeDeltas(players.map(p => p.delta).filter(d => d !== null)),
  }))
}
```

Substituir o corpo de `parseRunResult` por um despacho, preservando o caminho atual:

```javascript
export async function parseRunResult(zipBlob, tournamentsCsvText, playersCsvText = '') {
  const zip = await JSZip.loadAsync(zipBlob)
  const names = new Set(
    Object.entries(zip.files)
      .filter(([, entry]) => !entry.dir)
      .map(([path]) => (path.includes('/') ? path.slice(path.lastIndexOf('/') + 1) : path)),
  )

  if (names.has('Comparison.csv')) {
    return parseComparisonResult(zip, zipBlob)
  }
  if (names.has('Audit_Period.csv')) {
    return parseFideResult(zip, zipBlob)
  }
  return parseLegacyResult(zip, zipBlob, tournamentsCsvText, playersCsvText)
}

async function parseFideResult(zip, zipBlob) {
  const periodRows = parseFidePeriodAudit(await zip.file('Audit_Period.csv').async('string'))
  return {
    kind: 'fide',
    zipBlob,
    zipFilename: ZIP_NAME_BY_KIND.fide,
    modalities: groupByModality(periodRows),
    tournaments: [],
  }
}

async function parseComparisonResult(zip, zipBlob) {
  const comparisonRows = parseComparisonCsv(await zip.file('Comparison.csv').async('string'))
  const periodEntry = zip.file('Audit_Period.csv')
  const periodRows = periodEntry ? parseFidePeriodAudit(await periodEntry.async('string')) : []
  return {
    kind: 'compare',
    zipBlob,
    zipFilename: ZIP_NAME_BY_KIND.compare,
    comparison: {
      players: comparisonRows,
      summary: summarizeDeltas(comparisonRows.map(r => r.difference)),
    },
    modalities: groupByModality(periodRows),
    tournaments: [],
  }
}
```

Renomear o corpo atual de `parseRunResult` para `parseLegacyResult(zip, zipBlob, tournamentsCsvText, playersCsvText)`, removendo dele o `JSZip.loadAsync` (o zip já vem aberto) e acrescentando `kind: 'legacy'` ao objeto devolvido.

Em `frontend/src/hooks/useRunCycle.js`, no `catch` do parse, trocar o `zipFilename` fixo por um que respeite o modo:

```javascript
        const fallbackName = {
          fide: 'rating_cycle_fide.zip',
          compare: 'rating_cycle_comparison.zip',
        }[form.mode] ?? 'rating_cycle_output.zip'
        setRunResult({
          zipBlob: blob,
          zipFilename: fallbackName,
          kind: form.mode === 'legacy' ? 'legacy' : form.mode,
          tournaments: [],
          parseError: msg,
          requestId: reqId ?? undefined,
        })
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd frontend && npx vitest run src/resultParser.fide.test.js src/resultParser.test.js`
Expected: PASS nos dois — o parser do modelo atual não pode ter regredido

- [ ] **Step 5: Commit**

```bash
git add frontend/src/resultParser.js frontend/src/resultParser.fide.test.js frontend/src/hooks/useRunCycle.js
git commit -m "feat(portal): leitura das saídas do modelo FIDE e do comparativo"
```

---

## Task 3: Resumo na tela de resultado

**Files:**
- Create: `frontend/src/components/PeriodSummary.jsx`
- Create: `frontend/src/components/ComparisonSummary.jsx`
- Modify: `frontend/src/ResultsPage.jsx` (despacho por `kind`)
- Test: `frontend/src/components/PeriodSummary.test.jsx`, `frontend/src/components/ComparisonSummary.test.jsx`

**Interfaces:**
- Consumes: `runResult.kind`, `runResult.modalities`, `runResult.comparison` da Task 2
- Produces: componentes de resumo; `ResultsPage` passa a aceitar os três formatos

- [ ] **Step 1: Escrever os testes**

`frontend/src/components/PeriodSummary.test.jsx`:

```javascript
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import PeriodSummary from './PeriodSummary'

const MODALITIES = [
  {
    modality: 'STD',
    players: [
      { fexerjId: 3741, name: 'Carlos Mendes', initialRating: 1800, finalRating: 1807, delta: 7, games: 5, path: 'RATED' },
      { fexerjId: 643, name: 'Roberto Faria', initialRating: 1900, finalRating: 1896, delta: -4, games: 5, path: 'RATED' },
    ],
    summary: { total: 2, up: 1, down: 1, unchanged: 0, maxUp: 7, maxDown: -4, medianAbs: 5.5 },
  },
]

describe('PeriodSummary', () => {
  it('mostra o nome da modalidade', () => {
    render(<PeriodSummary modalities={MODALITIES} />)
    expect(screen.getByText(/clássico/i)).toBeInTheDocument()
  })

  it('mostra quantos subiram e quantos caíram', () => {
    render(<PeriodSummary modalities={MODALITIES} />)
    expect(screen.getByText(/1 subiu/i)).toBeInTheDocument()
    expect(screen.getByText(/1 caiu/i)).toBeInTheDocument()
  })

  it('lista os jogadores com a variação', () => {
    render(<PeriodSummary modalities={MODALITIES} />)
    expect(screen.getByText('Carlos Mendes')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
    expect(screen.getByText('-4')).toBeInTheDocument()
  })

  it('avisa quando o período não moveu ninguém', () => {
    render(<PeriodSummary modalities={[]} />)
    expect(screen.getByText(/nenhum jogador/i)).toBeInTheDocument()
  })
})
```

`frontend/src/components/ComparisonSummary.test.jsx`:

```javascript
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ComparisonSummary from './ComparisonSummary'

const COMPARISON = {
  players: [
    { fexerjId: 3741, name: 'Carlos Mendes', ratingCurrent: 1810, ratingFide: 1807, difference: -3 },
    { fexerjId: 643, name: 'Roberto Faria', ratingCurrent: 1893, ratingFide: 1896, difference: 3 },
    { fexerjId: 1979, name: 'Andre Nunes', ratingCurrent: 1700, ratingFide: 1700, difference: 0 },
  ],
  summary: { total: 3, up: 1, down: 1, unchanged: 1, maxUp: 3, maxDown: -3, medianAbs: 3 },
}

describe('ComparisonSummary', () => {
  it('mostra os dois ratings lado a lado', () => {
    render(<ComparisonSummary comparison={COMPARISON} />)
    expect(screen.getByText('1810')).toBeInTheDocument()
    expect(screen.getByText('1807')).toBeInTheDocument()
  })

  it('resume a diferença entre os modelos', () => {
    render(<ComparisonSummary comparison={COMPARISON} />)
    expect(screen.getByText(/3 jogadores/i)).toBeInTheDocument()
    expect(screen.getByText(/mediana/i)).toBeInTheDocument()
  })

  it('diz que a diferença é esperada', () => {
    render(<ComparisonSummary comparison={COMPARISON} />)
    expect(screen.getByText(/ratings diferentes.*histórico idêntico/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npx vitest run src/components/PeriodSummary.test.jsx src/components/ComparisonSummary.test.jsx`
Expected: FAIL — os módulos não existem

- [ ] **Step 3: Implementar `PeriodSummary.jsx`**

```jsx
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
            {summary.total} jogador(es) · {summary.up} subiu(ram) · {summary.down} caiu(ram) ·{' '}
            {summary.unchanged} sem mudança
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
```

- [ ] **Step 4: Implementar `ComparisonSummary.jsx`**

```jsx
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
```

- [ ] **Step 5: Ligar no `ResultsPage`**

Em `frontend/src/ResultsPage.jsx`, importar os dois componentes e, no lugar onde hoje o conteúdo por torneio é montado, despachar por `runResult.kind` — mantendo o caminho atual intocado para `'legacy'`:

```jsx
      {runResult.kind === 'fide' && <PeriodSummary modalities={runResult.modalities} />}
      {runResult.kind === 'compare' && <ComparisonSummary comparison={runResult.comparison} />}
      {(runResult.kind === undefined || runResult.kind === 'legacy') && (
        /* conteúdo atual, por torneio, sem alteração */
      )}
```

O botão de download já usa `runResult.zipFilename`, que a Task 2 passou a variar por modo — confira que nenhum literal `rating_cycle_output.zip` sobrou no arquivo.

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `cd frontend && npx vitest run && npm run lint`
Expected: PASS, incluindo `ResultsPage.test.jsx`, e lint limpo

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/PeriodSummary.jsx frontend/src/components/ComparisonSummary.jsx \
        frontend/src/components/PeriodSummary.test.jsx frontend/src/components/ComparisonSummary.test.jsx \
        frontend/src/ResultsPage.jsx
git commit -m "feat(portal): resumo do período e do comparativo na tela de resultado"
```

---

## Task 4: Ajuda e documentação

**Files:**
- Modify: `frontend/src/components/HelpSection.jsx`
- Modify: `README.md`
- Test: `frontend/src/components/HelpSection.test.jsx` (criar)

**Interfaces:**
- Consumes: nada
- Produces: texto de ajuda cobrindo os três modos e as colunas novas

- [ ] **Step 1: Escrever o teste**

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import HelpSection from './HelpSection'

async function openHelp() {
  render(<HelpSection />)
  await userEvent.click(screen.getByRole('button', { name: /ajuda|como/i }))
}

describe('HelpSection', () => {
  it('explica os três modos', async () => {
    await openHelp()
    expect(screen.getByText(/modelo atual/i)).toBeInTheDocument()
    expect(screen.getByText(/modelo fide/i)).toBeInTheDocument()
    expect(screen.getByText(/comparar/i)).toBeInTheDocument()
  })

  it('avisa que a coluna TimeControl é necessária no modelo FIDE', async () => {
    await openHelp()
    expect(screen.getByText(/TimeControl/)).toBeInTheDocument()
  })

  it('avisa que a data de nascimento passa a ser obrigatória', async () => {
    await openHelp()
    expect(screen.getByText(/data de nascimento/i)).toBeInTheDocument()
  })

  it('explica que o intervalo é o período no modelo novo', async () => {
    await openHelp()
    expect(screen.getByText(/período de cálculo/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npx vitest run src/components/HelpSection.test.jsx`
Expected: FAIL — os textos ainda não existem

- [ ] **Step 3: Implementar**

Acrescentar ao corpo de `HelpSection.jsx`, dentro do bloco que já é exibido quando a ajuda está aberta:

```jsx
        <h3 className="portal-heading">Modelo de cálculo</h3>
        <ul className="list-disc list-inside space-y-1 m-0 pl-0">
          <li>
            <strong>Modelo atual (oficial)</strong> — o cálculo por torneio que a federação usa
            hoje. É o padrão, e é o que gera a lista oficial.
          </li>
          <li>
            <strong>Modelo FIDE (por partida)</strong> — o cálculo por partida, com as adaptações
            do Art. 68. Exige a coluna <code>TimeControl</code> (STD, RPD ou BLZ) e a coluna{' '}
            <code>EndDate</code> preenchidas no arquivo de torneios, e a{' '}
            <strong>data de nascimento</strong> preenchida no arquivo de jogadores.
          </li>
          <li>
            <strong>Comparar os dois</strong> — roda os dois modelos sobre o mesmo envio e gera o
            comparativo. Aceita apenas o arquivo de jogadores de 12 colunas e torneios de Clássico.
          </li>
        </ul>

        <h3 className="portal-heading">O intervalo no modelo novo</h3>
        <p className="help-body">
          No modelo atual, o intervalo processa um torneio de cada vez, em cadeia. No modelo FIDE,
          o intervalo selecionado é o <strong>período de cálculo</strong>: todas as partidas usam o
          rating do início do período e o arredondamento acontece uma única vez, no fim. Rodar
          cinco torneios de uma vez e rodar cinco vezes um torneio dão resultados diferentes — os
          dois estão certos, são períodos diferentes.
        </p>
```

- [ ] **Step 4: Rodar toda a suíte do frontend**

Run: `cd frontend && npx vitest run && npm run lint`
Expected: PASS, lint limpo

- [ ] **Step 5: Atualizar o README**

Em `README.md`, na seção que descreve a tela de execução, documentar o seletor de modelo, os três nomes de ZIP e os arquivos de saída de cada modo.

- [ ] **Step 6: Rodar a suíte completa dos dois lados**

Run: `.venv/bin/pytest -q && cd frontend && npx vitest run && npm run lint`
Expected: PASS em tudo

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/HelpSection.jsx frontend/src/components/HelpSection.test.jsx README.md
git commit -m "docs(portal): ajuda cobrindo os três modelos e o conceito de período"
```

---

## O que os dois planos não cobrem

**O documento de comunicação da §7 da spec, item 2.** O `Comparison.csv` e o
resumo na tela são código e estão nos planos; o documento curto que a federação
manda aos filiados — quantos mudaram, para que lado, os extremos explicados um a
um — não é. Ele depende de rodar o modo comparar sobre um ciclo real e olhar os
números. Fica como passo seguinte, depois de o portal estar de pé, e é trabalho
de escrita, não de implementação.

**A data de aposentadoria do modelo atual.** Decisão da federação, não do
código. Enquanto o modelo atual for o padrão do seletor, ele é o oficial.

## Depois dos dois planos

Com o motor e o portal estáveis, drenar a fila do Dependabot (#207 a #211). A
#209 (`jsdom` 29→30) e a #211 (`@testing-library/jest-dom` 6→7) são major e
mexem no ambiente de teste — por isso ficaram para depois, e não antes.
