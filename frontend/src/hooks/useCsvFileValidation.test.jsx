import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FIDE_TOURNAMENTS_HEADER } from '../csvUploadValidation'
import useCsvFileValidation from './useCsvFileValidation'

const FIDE_TOURNAMENTS_CSV = `${FIDE_TOURNAMENTS_HEADER}\n1;99999;Copa;2026-03-15;RR;0;1;STD\n`

function csvFile(content, name) {
  return new File([content], name, { type: 'text/csv' })
}

describe('useCsvFileValidation', () => {
  it('clears the run for a per-game tournaments file when the mode asks for one', async () => {
    // The whole feature hangs off this: while the browser-side check rejects
    // the file, csvFilesValid stays false, /validate is skipped and "Executar"
    // never enables — the operator cannot run the FIDE model at all.
    const { result } = renderHook(() =>
      useCsvFileValidation(null, csvFile(FIDE_TOURNAMENTS_CSV, 'tournaments.csv'), 'fide'),
    )
    await waitFor(() => expect(result.current.tournamentsCsvStatus).toBe('done'))
    expect(result.current.tournamentsCsvErrors).toEqual([])
    expect(result.current.csvFilesValid).toBe(true)
  })

  it('still rejects that same file under the current model', async () => {
    const { result } = renderHook(() =>
      useCsvFileValidation(null, csvFile(FIDE_TOURNAMENTS_CSV, 'tournaments.csv'), 'legacy'),
    )
    await waitFor(() => expect(result.current.tournamentsCsvStatus).toBe('done'))
    expect(result.current.tournamentsCsvErrors).not.toEqual([])
    expect(result.current.csvFilesValid).toBe(false)
  })

  it('re-checks the files when the mode changes', async () => {
    const tournaments = csvFile(FIDE_TOURNAMENTS_CSV, 'tournaments.csv')
    const { result, rerender } = renderHook(
      ({ mode }) => useCsvFileValidation(null, tournaments, mode),
      { initialProps: { mode: 'legacy' } },
    )
    await waitFor(() => expect(result.current.tournamentsCsvErrors).not.toEqual([]))

    rerender({ mode: 'fide' })
    await waitFor(() => expect(result.current.tournamentsCsvErrors).toEqual([]))
  })
})
