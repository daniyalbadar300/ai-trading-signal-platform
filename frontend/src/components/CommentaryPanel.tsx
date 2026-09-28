import type { Commentary } from '../types'

export function CommentaryPanel({ commentary }: { commentary: Commentary | null }) {
  if (!commentary) {
    return (
      <div
        className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-500"
        data-testid="commentary-empty"
      >
        Waiting for the first worker cycle…
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">🤖 AI Commentary</h3>
        <span
          className="rounded bg-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-400"
          data-testid="commentary-source"
        >
          {commentary.source}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-slate-300" data-testid="commentary-text">
        {commentary.text}
      </p>
      <p className="text-xs leading-relaxed text-amber-300/80">⚠ {commentary.risk_note}</p>
    </div>
  )
}
