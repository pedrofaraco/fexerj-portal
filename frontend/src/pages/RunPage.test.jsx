import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import RunPage from './RunPage'

function renderRunPage(formOverrides = {}) {
  const setForm = vi.fn()
  render(
    <RunPage
      form={{
        playersCsv: null,
        tournamentsCsv: null,
        binaryFiles: [],
        first: '1',
        count: '1',
        mode: 'legacy',
        ...formOverrides,
      }}
      setForm={setForm}
      status="idle"
      runErrors={[]}
      playersCsvErrors={[]}
      tournamentsCsvErrors={[]}
      playersCsvStatus="idle"
      tournamentsCsvStatus="idle"
      csvFilesValid={false}
      csvFilesChecking={false}
      validationErrors={[]}
      validationRequestError=""
      validationStatus="idle"
      onRun={vi.fn()}
      onLogout={vi.fn()}
      onClearForm={vi.fn()}
      formResetKey={0}
    />,
  )
  return { setForm }
}

const PERIOD_NOTICE = /o intervalo selecionado é o período de cálculo/i

describe('calculation model selector', () => {
  it('starts on the current model', () => {
    renderRunPage()
    expect(screen.getByLabelText(/modelo de cálculo/i)).toHaveValue('legacy')
  })

  it('offers the three modes', () => {
    renderRunPage()
    const options = screen.getAllByRole('option').map(o => o.value)
    expect(options).toEqual(['legacy', 'fide', 'compare'])
  })

  it('marks the current model as the official one', () => {
    renderRunPage()
    expect(screen.getByRole('option', { name: /oficial/i })).toHaveValue('legacy')
  })

  it('propagates the choice to the form', async () => {
    const { setForm } = renderRunPage()
    await userEvent.selectOptions(screen.getByLabelText(/modelo de cálculo/i), 'fide')
    expect(setForm).toHaveBeenCalled()
  })

  it('warns that the interval is the whole rating period in the FIDE model', () => {
    renderRunPage({ mode: 'fide' })
    expect(screen.getByText(PERIOD_NOTICE)).toBeInTheDocument()
  })

  it('warns in compare mode too, which runs the same period', () => {
    renderRunPage({ mode: 'compare' })
    expect(screen.getByText(PERIOD_NOTICE)).toBeInTheDocument()
  })

  it('does not show that warning for the current model', () => {
    renderRunPage()
    expect(screen.queryByText(PERIOD_NOTICE)).not.toBeInTheDocument()
  })
})
