import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HistoryTable } from './HistoryTable'
import type { Signal } from '../types'

function row(overrides: Partial<Signal>): Signal {
  return {
    symbol: 'ETHUSDT',
    action: 'SELL',
    confidence: 0.5,
    score: -0.2,
    price: 2682.14,
    indicators: {
      rsi_14: 50, macd: 0, macd_signal: 0, macd_hist: 0, ema_20: 0,
      ema_50: 0, bb_upper: 0, bb_lower: 0, bb_mid: 0, volume_ratio: 1,
    },
    contributions: {},
    generated_at: '2026-09-26T10:00:00Z',
    ...overrides,
  }
}

describe('HistoryTable', () => {
  it('renders signal rows with colored actions', () => {
    render(
      <HistoryTable
        history={[
          row({ symbol: 'BTCUSDT', action: 'BUY' }),
          row({ symbol: 'ETHUSDT', action: 'SELL' }),
        ]}
      />,
    )
    const table = screen.getByTestId('history-table')
    expect(table).toBeInTheDocument()
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument()
    expect(screen.getByText('SELL')).toBeInTheDocument()
  })

  it('shows empty state when history is empty', () => {
    render(<HistoryTable history={[]} />)
    expect(screen.getByText(/No history yet/)).toBeInTheDocument()
  })
})
