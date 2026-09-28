import type { Signal } from '../types'

const ACTION_STYLES = {
  BUY: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40',
  SELL: 'bg-red-500/15 text-red-400 border-red-500/40',
  HOLD: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
} as const

const METER_COLOR = {
  BUY: 'bg-emerald-500',
  SELL: 'bg-red-500',
  HOLD: 'bg-amber-500',
} as const

export function SignalCard({ signal }: { signal: Signal }) {
  const confidencePct = Math.round(signal.confidence * 100)
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-slate-100">{signal.symbol}</span>
        <span
          className={`rounded-md border px-2 py-0.5 text-xs font-bold ${ACTION_STYLES[signal.action]}`}
          data-testid={`action-${signal.symbol}`}
        >
          {signal.action}
        </span>
      </div>
      <div className="flex items-baseline justify-between">
        <span className="text-2xl font-bold tabular-nums text-slate-50">
          {signal.price > 0
            ? signal.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
            : '—'}
        </span>
        <span className="text-xs text-slate-400">conf {confidencePct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-800">
        <div
          className={`h-1.5 rounded-full ${METER_COLOR[signal.action]}`}
          style={{ width: `${Math.max(4, confidencePct)}%` }}
          data-testid={`meter-${signal.symbol}`}
        />
      </div>
      <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-400">
        <span>
          RSI <span className="tabular-nums text-slate-200">{signal.indicators.rsi_14.toFixed(1)}</span>
        </span>
        <span>
          MACD-h{' '}
          <span className="tabular-nums text-slate-200">{signal.indicators.macd_hist.toFixed(3)}</span>
        </span>
        <span>
          Vol{' '}
          <span className="tabular-nums text-slate-200">{signal.indicators.volume_ratio.toFixed(2)}x</span>
        </span>
      </div>
    </div>
  )
}
