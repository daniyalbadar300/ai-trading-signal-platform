import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SignalCard } from './SignalCard'
import type { Signal } from '../types'

const baseSignal: Signal = {
  symbol: 'BTCUSDT',
  action: 'BUY',
  confidence: 0.87,
  score: 0.44,
  price: 83994.01,
  indicators: {
    rsi_14: 33.4,
    macd: -48.3,
    macd_signal: -50.0,
    macd_hist: 1.7,
    ema_20: 84048,
    ema_50: 84106,
    bb_upper: 84205,
    bb_lower: 83892,
    bb_mid: 84049,
    volume_ratio: 0.29,
  },
  contributions: { rsi: 0.19, macd: 0.24, ema_cross: -0.02, bollinger: 0.05, volume: -0.02 },
  generated_at: '2026-09-26T09:26:24Z',
}

describe('SignalCard', () => {
  it('renders symbol, price and action badge', () => {
    render(<SignalCard signal={baseSignal} />)
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument()
    expect(screen.getByText('BUY')).toBeInTheDocument()
    expect(screen.getByText(/83,994/)).toBeInTheDocument()
  })

  it('shows confidence percentage', () => {
    render(<SignalCard signal={baseSignal} />)
    expect(screen.getByText('conf 87%')).toBeInTheDocument()
  })

  it('renders indicator mini-stats', () => {
    render(<SignalCard signal={baseSignal} />)
    expect(screen.getByText('33.4')).toBeInTheDocument()
    expect(screen.getByText('0.29x')).toBeInTheDocument()
  })
})
