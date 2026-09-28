import type { Signal } from '../types'

const ACTION_COLOR: Record<Signal['action'], string> = {
  BUY: 'text-emerald-400',
  SELL: 'text-red-400',
  HOLD: 'text-amber-400',
}

export function HistoryTable({ history }: { history: Signal[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full text-left text-xs" data-testid="history-table">
        <thead className="bg-slate-900/80 uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-3 py-2">Time</th>
            <th className="px-3 py-2">Symbol</th>
            <th className="px-3 py-2">Action</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">Conf</th>
            <th className="px-3 py-2 text-right">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {history.map((s, idx) => (
            <tr key={`${s.symbol}-${s.generated_at}-${idx}`} className="hover:bg-slate-900/50">
              <td className="px-3 py-1.5 tabular-nums text-slate-400">
                {new Date(s.generated_at).toLocaleTimeString()}
              </td>
              <td className="px-3 py-1.5 font-medium text-slate-200">{s.symbol}</td>
              <td className={`px-3 py-1.5 font-bold ${ACTION_COLOR[s.action]}`}>{s.action}</td>
              <td className="px-3 py-1.5 text-right tabular-nums text-slate-300">
                {s.price > 0 ? s.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}
              </td>
              <td className="px-3 py-1.5 text-right tabular-nums text-slate-300">
                {Math.round(s.confidence * 100)}%
              </td>
              <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                {s.score.toFixed(3)}
              </td>
            </tr>
          ))}
          {history.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                No history yet — waiting for the worker to generate signals…
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
