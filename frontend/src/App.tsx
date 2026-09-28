import { useMemo, useState } from 'react'
import { api } from './api'
import { CommentaryPanel } from './components/CommentaryPanel'
import { Header } from './components/Header'
import { HistoryTable } from './components/HistoryTable'
import { PriceChart } from './components/PriceChart'
import { SignalCard } from './components/SignalCard'
import { usePolling } from './hooks/usePolling'
import { useWebSocket } from './hooks/useWebSocket'

export default function App() {
  const [selected, setSelected] = useState<string | null>(null)

  const symbols = usePolling(() => api.symbols(), 0)
  const watchlist = symbols.data?.symbols ?? []

  const symbol = selected ?? watchlist[0] ?? 'BTCUSDT'

  const candles = usePolling(() => api.candles(symbol, 180), 15000, [symbol])
  const worker = usePolling(() => api.workerStatus(), 5000)
  const stats = usePolling(() => api.stats(), 5000)
  const history = usePolling(() => api.history(25), 5000)

  const { latest, connected } = useWebSocket()
  const signal = latest[symbol] ?? null

  const historyForTable = useMemo(
    () => history.data ?? [],
    [history.data],
  )

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col">
      <Header connected={connected} worker={worker.data} />

      <main className="flex flex-1 flex-col gap-4 p-6">
        {/* Watchlist tabs */}
        <nav className="flex gap-2" data-testid="symbol-tabs">
          {watchlist.map((s) => (
            <button
              key={s}
              onClick={() => setSelected(s)}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                s === symbol
                  ? 'border-sky-500/60 bg-sky-500/10 text-sky-300'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
              }`}
            >
              {s}
            </button>
          ))}
        </nav>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Chart column */}
          <section className="flex flex-col gap-4 lg:col-span-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-200">
                  {symbol} · 1m candles
                </h2>
                {candles.error && (
                  <span className="text-xs text-red-400">chart data unavailable</span>
                )}
              </div>
              <PriceChart candles={candles.data} />
            </div>

            {/* Signal cards row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {watchlist.map((s) => {
                const sig = latest[s]
                return sig ? (
                  <SignalCard key={s} signal={sig} />
                ) : (
                  <div
                    key={s}
                    className="rounded-xl border border-dashed border-slate-800 p-4 text-xs text-slate-500"
                  >
                    waiting for {s} signal…
                  </div>
                )
              })}
            </div>
          </section>

          {/* Right column */}
          <aside className="flex flex-col gap-4">
            <CommentaryPanel commentary={signal?.commentary ?? null} />
            {stats.data && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-400">
                <h3 className="mb-2 text-sm font-semibold text-slate-200">📊 Stats</h3>
                <div className="flex justify-between">
                  <span>total signals</span>
                  <span className="tabular-nums text-slate-200">{stats.data.total}</span>
                </div>
                <div className="flex justify-between">
                  <span>BUY / SELL / HOLD</span>
                  <span className="tabular-nums text-slate-200">
                    {stats.data.actions['BUY'] ?? 0} / {stats.data.actions['SELL'] ?? 0} /{' '}
                    {stats.data.actions['HOLD'] ?? 0}
                  </span>
                </div>
              </div>
            )}
          </aside>
        </div>

        {/* History */}
        <section>
          <h2 className="mb-2 text-sm font-semibold text-slate-200">Signal history</h2>
          <HistoryTable history={historyForTable} />
        </section>
      </main>
    </div>
  )
}
