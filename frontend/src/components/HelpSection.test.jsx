import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import HelpSection from './HelpSection'

async function openHelp() {
  render(<HelpSection />)
  await userEvent.click(screen.getByRole('button', { name: /como usar/i }))
}

describe('HelpSection', () => {
  it('explains the three calculation models', async () => {
    await openHelp()
    expect(screen.getByText(/modelo atual \(oficial\)/i)).toBeInTheDocument()
    expect(screen.getByText(/modelo fide \(por partida\)/i)).toBeInTheDocument()
    expect(screen.getByText(/comparar os dois/i)).toBeInTheDocument()
  })

  it('names the TimeControl column the per-game model needs', async () => {
    await openHelp()
    expect(screen.getByText('TimeControl')).toBeInTheDocument()
  })

  it('warns that the birth date becomes mandatory', async () => {
    await openHelp()
    expect(screen.getByText(/data de nascimento/i)).toBeInTheDocument()
  })

  it('explains that the interval is the whole rating period in the new model', async () => {
    await openHelp()
    expect(screen.getByText(/período de cálculo/i)).toBeInTheDocument()
  })

  it('keeps the walkthrough it already had', async () => {
    await openHelp()
    expect(screen.getByText(/preparar os arquivos/i)).toBeInTheDocument()
    expect(screen.getByText(/executar o ciclo/i)).toBeInTheDocument()
  })
})
