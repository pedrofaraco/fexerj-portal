import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BuildStamp from './BuildStamp'

describe('BuildStamp', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: {
            get: name => (name.toLowerCase() === 'date' ? 'Sat, 18 Apr 2026 19:12:00 GMT' : null),
          },
        }),
      ),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows Server time after /health Date header resolves', async () => {
    render(<BuildStamp />)
    await waitFor(() => {
      expect(screen.getByText(/Server Time/)).toHaveTextContent(/EDT|EST/)
    })
  })

  it('copy button shows Copiado feedback after click', async () => {
    const user = userEvent.setup()
    render(<BuildStamp />)
    await waitFor(() => {
      expect(screen.getByText(/Server Time/)).not.toHaveTextContent(/^Server Time —$/)
    })

    await user.click(
      screen.getByRole('button', { name: /copiar commit do frontend e horários/i }),
    )

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('Copiado')
    })
  })
})
