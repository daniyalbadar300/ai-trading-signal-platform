import type { WorkerStatus } from '../types'

export function Header({
  connected,
  worker,
}: {
  connected: boolean
  worker: WorkerStatus | null
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-6 py-4">
      <div>
        <h1 className="text-lg font-bold text-slate-50">🤖 AI Trading Signals</h1>
        <p className="text-xs text-slate-500">Binance data · indicators + LLM · DevOps demo</p>
      </div>
      <div className="flex items-center gap-4 text-xs" data-testid="header-status">
        <span className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${connected ? 'animate-pulse bg-emerald-500' : 'bg-red-500'}`}
            data-testid="ws-dot"
          />
          <span className="text-slate-400">{connected ? 'live' : 'offline'}</span>
        </span>
        {worker && (
          <span className="text-slate-400" data-testid="worker-cycles">
            worker: {worker.cycles} cycles · {worker.signals_generated} signals
          </span>
        )}
      </div>
    </header>
  )
}
