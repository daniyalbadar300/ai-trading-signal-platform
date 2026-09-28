/** Shared types mirroring the backend Pydantic models. */

export type SignalAction = 'BUY' | 'SELL' | 'HOLD'

export interface Candle {
  open_time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface IndicatorSnapshot {
  rsi_14: number
  macd: number
  macd_signal: number
  macd_hist: number
  ema_20: number
  ema_50: number
  bb_upper: number
  bb_lower: number
  bb_mid: number
  volume_ratio: number
}

export interface Commentary {
  text: string
  risk_note: string
  source: string
  generated_at: string
}

export interface Signal {
  symbol: string
  action: SignalAction
  confidence: number
  score: number
  price: number
  indicators: IndicatorSnapshot
  contributions: Record<string, number>
  generated_at: string
  commentary?: Commentary
}

/** Payloads delivered over /ws/signals */
export interface SnapshotMessage {
  type: 'snapshot'
  signals: Signal[]
}

export interface SignalMessage {
  type: 'signal'
  symbol: string
  action: SignalAction
  confidence: number
  score: number
  price: number
  indicators: IndicatorSnapshot
  contributions: Record<string, number>
  generated_at: string
  commentary: Commentary
}

export type WsMessage = SnapshotMessage | SignalMessage

export interface WorkerStatus {
  running: boolean
  interval_s: number
  cycles: number
  signals_generated: number
  last_cycle_at: string | null
  last_error: string | null
}

export interface Stats {
  total: number
  actions: Record<string, number>
}
