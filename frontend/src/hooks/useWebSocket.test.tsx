import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useWebSocket } from './useWebSocket'

/** Minimal WebSocket stand-in capturing instances and manual event dispatch. */
class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }
  close() {}
}

function Probe() {
  const { latest, connected, snapshotLoaded } = useWebSocket()
  return (
    <div>
      <span data-testid="connected">{String(connected)}</span>
      <span data-testid="snapshot">{String(snapshotLoaded)}</span>
      <span data-testid="action-btc">{latest['BTCUSDT'] ? latest['BTCUSDT'].action : 'none'}</span>
      <span data-testid="action-eth">{latest['ETHUSDT'] ? latest['ETHUSDT'].action : 'none'}</span>
    </div>
  )
}

describe('useWebSocket', () => {
  it('processes snapshot and live signal messages', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    MockWebSocket.instances = []

    render(<Probe />)
    const ws = MockWebSocket.instances[0]
    expect(ws.url).toContain('/ws/signals')

    // Simulate server: open + snapshot + live message
    ws.onopen?.()
    ws.onmessage?.({
      data: JSON.stringify({
        type: 'snapshot',
        signals: [{ symbol: 'BTCUSDT', action: 'HOLD', confidence: 0.4, score: 0.1,
          price: 100, indicators: {}, contributions: {}, generated_at: '2026-09-26T10:00:00Z' }],
      }),
    })
    ws.onmessage?.({
      data: JSON.stringify({
        type: 'signal', symbol: 'ETHUSDT', action: 'BUY', confidence: 0.9, score: 0.5,
        price: 200, indicators: {}, contributions: {}, generated_at: '2026-09-26T10:01:00Z',
        commentary: { text: 'x', risk_note: 'y', source: 'rule-engine', generated_at: '2026-09-26T10:01:00Z' },
      }),
    })

    await waitFor(() => {
      expect(screen.getByTestId('connected')).toHaveTextContent('true')
      expect(screen.getByTestId('snapshot')).toHaveTextContent('true')
      expect(screen.getByTestId('action-btc')).toHaveTextContent('HOLD') // from snapshot
      expect(screen.getByTestId('action-eth')).toHaveTextContent('BUY') // from live message
    })

    vi.unstubAllGlobals()
  })
})
