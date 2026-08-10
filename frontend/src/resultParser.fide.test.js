import JSZip from 'jszip'
import { describe, expect, it } from 'vitest'

import {
  COMPARISON_PREAMBLE,
  FIDE_GAMES_PREAMBLE,
  FIDE_PERIOD_PREAMBLE,
  parseComparisonCsv,
  parseFidePeriodAudit,
  parseRunResult,
  summarizeDeltas,
} from './resultParser'

// Headers must match `calculator/fide/audit.py` and `calculator/compare.py`.
const PERIOD_CSV =
  `${FIDE_PERIOD_PREAMBLE}\n` +
  'Tournaments;PlayerId;PlayerName;TimeControl;InitialRating;Games;SumDeltaR;Variation;' +
  'RoundedVariation;FinalRating;Path;AccumSumOpp;AccumPoints;AccumGames;AccumSince\n' +
  '1;3741;Carlos Mendes;STD;1800;5;0.36;7.2;7;1807;RATED;0;0;0;\n' +
  '1;643;Roberto Faria;STD;1900;5;-0.20;-4.0;-4;1896;RATED;0;0;0;\n' +
  '1;5400;Bruno Teixeira;RPD;;3;0;0;0;;ACCUMULATING;5100;1.5;3;2026-03\n'

const GAMES_CSV =
  `${FIDE_GAMES_PREAMBLE}\n` +
  'Tournament;TimeControl;PlayerId;PlayerName;OpponentId;OpponentRating;D;DiffCapped;PD;Score;DeltaR;K\n' +
  '1;STD;3741;Carlos Mendes;643;1900;-100;0;0.36;1;0.64;20\n'

const COMPARISON_CSV =
  `${COMPARISON_PREAMBLE}\n` +
  'PlayerId;PlayerName;RatingCurrent;RatingFide;Difference\n' +
  '3741;Carlos Mendes;1810;1807;-3\n' +
  '643;Roberto Faria;1893;1896;3\n' +
  '1979;Andre Nunes;1700;1700;0\n'

const LEGACY_AUDIT_CSV =
  '# audit_v1\n' +
  'Id_Fexerj;Name;No;Ro;Ind;K;PG;N;Erm;Rm;Dif;We;Nwe;Dw;kDw;Rn;Nind;P;Calc_Rule\n' +
  '3741;Carlos Mendes;1;1800;50;25;3;5;8500;1700;100;0.5;2.5;0.5;12.5;1813;55;0.6;NORMAL\n'

async function zipOf(files) {
  const zip = new JSZip()
  for (const [name, content] of Object.entries(files)) zip.file(name, content)
  return zip.generateAsync({ type: 'blob' })
}

const FIDE_ZIP_FILES = {
  'RatingList.csv': 'x',
  'Audit_Period.csv': PERIOD_CSV,
  'Audit_Games.csv': GAMES_CSV,
}

describe('parseFidePeriodAudit', () => {
  it('reads one row per player and modality', () => {
    expect(parseFidePeriodAudit(PERIOD_CSV)).toHaveLength(3)
  })

  it('keeps the modalities apart', () => {
    const rows = parseFidePeriodAudit(PERIOD_CSV)
    expect(rows.filter(r => r.modality === 'STD')).toHaveLength(2)
    expect(rows.filter(r => r.modality === 'RPD')).toHaveLength(1)
  })

  it('reads an empty rating as unrated', () => {
    const row = parseFidePeriodAudit(PERIOD_CSV).find(r => r.modality === 'RPD')
    expect(row.initialRating).toBeNull()
    expect(row.finalRating).toBeNull()
    expect(row.delta).toBeNull()
  })

  it('computes the period delta for a rated player', () => {
    const row = parseFidePeriodAudit(PERIOD_CSV).find(r => r.fexerjId === 643)
    expect(row.delta).toBe(-4)
    expect(row.roundedVariation).toBe(-4)
  })

  it('rejects an unknown preamble', () => {
    expect(() => parseFidePeriodAudit('# outra_coisa\nA;B\n1;2\n')).toThrow(/não reconhecid/i)
  })
})

describe('parseComparisonCsv', () => {
  it('reads the difference between the models', () => {
    const rows = parseComparisonCsv(COMPARISON_CSV)
    expect(rows.map(r => r.difference)).toEqual([-3, 3, 0])
  })

  it('rejects an unknown preamble', () => {
    expect(() => parseComparisonCsv('# outra_coisa\nA;B\n1;2\n')).toThrow(/não reconhecid/i)
  })
})

describe('summarizeDeltas', () => {
  it('counts rises, falls and ties', () => {
    const s = summarizeDeltas([-3, 3, 0, 5])
    expect(s.total).toBe(4)
    expect(s.up).toBe(2)
    expect(s.down).toBe(1)
    expect(s.unchanged).toBe(1)
  })

  it('finds the extremes', () => {
    const s = summarizeDeltas([-3, 3, 0, 5])
    expect(s.maxUp).toBe(5)
    expect(s.maxDown).toBe(-3)
  })

  it('takes the median of the absolute variation', () => {
    expect(summarizeDeltas([-3, 3, 0, 5]).medianAbs).toBe(3)
    expect(summarizeDeltas([1, 3]).medianAbs).toBe(2)
  })

  it('survives an empty list', () => {
    const s = summarizeDeltas([])
    expect(s.total).toBe(0)
    expect(s.medianAbs).toBeNull()
  })
})

describe('parseRunResult dispatches on the shape of the output', () => {
  it('recognizes the per-game model output', async () => {
    const result = await parseRunResult(await zipOf(FIDE_ZIP_FILES), '', '')
    expect(result.kind).toBe('fide')
    expect(result.zipFilename).toBe('rating_cycle_fide.zip')
    expect(result.modalities.map(m => m.modality)).toEqual(['STD', 'RPD'])
  })

  it('summarizes each modality on its own', async () => {
    const result = await parseRunResult(await zipOf(FIDE_ZIP_FILES), '', '')
    const std = result.modalities.find(m => m.modality === 'STD')
    expect(std.summary.total).toBe(2)
    expect(std.summary.up).toBe(1)
    expect(std.summary.down).toBe(1)
  })

  it('leaves an unrated player out of the summary but keeps the row', async () => {
    const result = await parseRunResult(await zipOf(FIDE_ZIP_FILES), '', '')
    const rpd = result.modalities.find(m => m.modality === 'RPD')
    expect(rpd.players).toHaveLength(1)
    expect(rpd.summary.total).toBe(0)
  })

  it('recognizes the compare output', async () => {
    const blob = await zipOf({
      ...FIDE_ZIP_FILES,
      'Comparison.csv': COMPARISON_CSV,
      'RatingList_after_1.csv': 'y',
    })
    const result = await parseRunResult(blob, '', '')
    expect(result.kind).toBe('compare')
    expect(result.zipFilename).toBe('rating_cycle_comparison.zip')
    expect(result.comparison.summary.total).toBe(3)
    expect(result.modalities.map(m => m.modality)).toEqual(['STD', 'RPD'])
  })

  it('still reads the current model output', async () => {
    const blob = await zipOf({
      'RatingList_after_1.csv': 'x',
      'Audit_of_Tournament_1.csv': LEGACY_AUDIT_CSV,
    })
    const result = await parseRunResult(blob, '', '')
    expect(result.kind).toBe('legacy')
    expect(result.zipFilename).toBe('rating_cycle_output.zip')
    expect(result.tournaments).toHaveLength(1)
  })
})
