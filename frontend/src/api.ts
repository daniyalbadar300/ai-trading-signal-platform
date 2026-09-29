/** Thin typed client over the backend REST API. */

import type { Candle, Signal, Stats, WorkerStatus } from './types'

// Same-origin by default (vite proxy / nginx / k8s ingress); set VITE_API_BASE
// when the API lives elsewhere (e.g. Render behind a Vercel frontend).
const BASE = import.meta.env.VITE_API_BASE ?? ''

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`${url} -> ${resp.status}`)
  return resp.json() as Promise<T>
}

export const api = {
  symbols: () => getJson<{ symbols: string[]; interval: string }>(`${BASE}/api/v1/symbols`),

  candles: (symbol: string, limit = 180) =>
    getJson<Candle[]>(`${BASE}/api/v1/candles/${symbol}?limit=${limit}`),

  signals: () => getJson<Signal[]>(`${BASE}/api/v1/signals`),

  signal: (symbol: string) => getJson<Signal>(`${BASE}/api/v1/signals/${symbol}`),

  history: (limit = 50, symbol?: string) =>
    getJson<Signal[]>(
      `${BASE}/api/v1/history?limit=${limit}${symbol ? `&symbol=${symbol}` : ''}`,
    ),

  stats: () => getJson<Stats>(`${BASE}/api/v1/stats`),

  workerStatus: () => getJson<WorkerStatus>(`${BASE}/worker/status`),

  health: () =>
    getJson<{ status: string; provider: string; upstream_ok: boolean }>(`${BASE}/health`),
}
