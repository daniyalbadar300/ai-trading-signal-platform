/** Thin typed client over the backend REST API (proxied in dev). */

import type { Candle, Signal, Stats, WorkerStatus } from './types'

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`${url} -> ${resp.status}`)
  return resp.json() as Promise<T>
}

export const api = {
  symbols: () => getJson<{ symbols: string[]; interval: string }>('/api/v1/symbols'),

  candles: (symbol: string, limit = 180) =>
    getJson<Candle[]>(`/api/v1/candles/${symbol}?limit=${limit}`),

  signals: () => getJson<Signal[]>('/api/v1/signals'),

  signal: (symbol: string) => getJson<Signal>(`/api/v1/signals/${symbol}`),

  history: (limit = 50, symbol?: string) =>
    getJson<Signal[]>(
      `/api/v1/history?limit=${limit}${symbol ? `&symbol=${symbol}` : ''}`,
    ),

  stats: () => getJson<Stats>('/api/v1/stats'),

  workerStatus: () => getJson<WorkerStatus>('/worker/status'),

  health: () => getJson<{ status: string; provider: string; upstream_ok: boolean }>('/health'),
}
